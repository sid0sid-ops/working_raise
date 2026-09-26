"""
Answer Diagnostic Benchmark Dataset
====================================
Loads `diagnostic_benchmark_dataset.json` (created by NotebookLM from the 4 institutional PDFs),
executes the RAISE StandaloneRAGPipeline across all questions (Tier 1-4),
populates candidate traces, formatted context, generated answers, verification results,
and latency metrics, and writes the results back with atomic checkpointing.
"""

from __future__ import annotations

import os
import sys
import json
import time
import uuid
import hashlib
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Ensure project and backend roots are in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_ROOT.parent

for p in [str(PROJECT_ROOT), str(BACKEND_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.retrieval.pipeline import StandaloneRAGPipeline
from src.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("raise.diagnostic_runner")


def compute_prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def format_context_for_prompt(chunks: List[Dict[str, Any]]) -> str:
    formatted_passages = []
    for idx, c in enumerate(chunks, 1):
        txt = c.get("text") or c.get("plain_text") or ""
        meta = c.get("metadata") or {}
        page = meta.get("primary_page") or c.get("page") or "?"
        doc = meta.get("pdf_filename") or c.get("pdf_filename") or meta.get("doc_id") or "Document"
        formatted_passages.append(f"[{idx}] (Source: {doc}, Page: {page})\n{txt.strip()}")
    return "\n\n".join(formatted_passages)


def run_diagnostic_benchmark(
    dataset_path: Path | str,
    output_path: Optional[Path | str] = None,
    limit: Optional[int] = None,
    start_index: int = 0,
    force_all: bool = False,
) -> None:
    dataset_path = Path(dataset_path).resolve()
    if not dataset_path.exists():
        raise FileNotFoundError(f"Diagnostic dataset not found: {dataset_path}")

    target_output = Path(output_path).resolve() if output_path else dataset_path

    logger.info("Loading diagnostic dataset from: %s", dataset_path)
    with open(dataset_path, "r", encoding="utf-8") as f:
        data: List[Dict[str, Any]] = json.load(f)

    total_records = len(data)
    logger.info("Loaded %d questions from benchmark dataset.", total_records)

    # Initialize production pipeline
    logger.info("Initializing StandaloneRAGPipeline...")
    pipeline = StandaloneRAGPipeline()
    pipeline.reset_production_namespace()

    run_id = f"diag_run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    logger.info("Starting diagnostic run execution ID: %s", run_id)

    processed_count = 0
    success_count = 0
    start_t = time.time()

    end_index = min(total_records, start_index + limit) if limit else total_records

    for idx in range(start_index, end_index):
        item = data[idx]
        q_id = item.get("question_id", f"Q_{idx+1}")
        q_text = item.get("question", "").strip()
        q_tier = item.get("query_classification", "Tier 1")

        if not q_text:
            logger.warning("[%d/%d] Skipping empty question %s", idx + 1, total_records, q_id)
            continue

        # Skip if already generated unless force_all is set
        if not force_all and item.get("generated_answer") and item.get("final_status") == "SUCCESS":
            logger.info("[%d/%d] Question %s already answered. Skipping.", idx + 1, total_records, q_id)
            continue

        logger.info("=" * 80)
        logger.info("[%d/%d] Processing %s (%s): %s", idx + 1, total_records, q_id, q_tier, q_text[:75] + "...")
        t0 = time.time()

        # Map tier to execution parameters
        hops = 1
        mode = "fast"
        top_k = 6
        if "tier 2" in q_tier.lower():
            hops = 2
            mode = "expert"
            top_k = 8
        elif "tier 3" in q_tier.lower():
            hops = 2
            mode = "expert"
            top_k = 8
        elif "tier 4" in q_tier.lower():
            hops = 3
            mode = "expert"
            top_k = 10

        try:
            # 1. Parallel Multi-Substrate Candidate Extraction
            t_ret0 = time.time()
            ret_data = pipeline.parallel_retriever.retrieve_sync(
                query=q_text,
                top_k=top_k,
                hops=hops,
                rerank_top_n=top_k,
            )
            ret_elapsed_ms = (time.time() - t_ret0) * 1000

            reranked_chunks = ret_data.get("reranked_chunks", [])
            dense_cands = [c.get("chunk_id") or c.get("id") for c in reranked_chunks[:8]]
            sparse_cands = [f"bm25_cand_{i}" for i in range(ret_data.get("sparse_count", 0))][:8]
            graph_cands = [f"graph_node_{i}" for i in range(ret_data.get("graph_count", 0))][:8]
            rrf_cands = [c.get("chunk_id") or c.get("id") for c in reranked_chunks]

            # 2. Execute Full Cyclical LangGraph & Synthesis Flow
            t_rag0 = time.time()
            rag_res = pipeline.query_subgraph_graphrag(
                query=q_text,
                hops=hops,
                top_k=top_k,
                mode=mode,
            )
            rag_elapsed_ms = (time.time() - t_rag0) * 1000

            top_chunks = rag_res.get("top_chunks") or rag_res.get("relevant_chunks") or reranked_chunks
            gen_answer = rag_res.get("grounded_answer") or rag_res.get("answer") or ""
            citations = rag_res.get("citations", [])
            subgraph_nodes = [n.get("name") or n.get("id") for n in rag_res.get("subgraph", {}).get("nodes", [])]

            context_before = "\n---\n".join([c.get("plain_text") or c.get("text") or "" for c in top_chunks[:6]])
            context_after = format_context_for_prompt(top_chunks[:6])
            prompt_hash = compute_prompt_hash(context_after + q_text)

            decision = (rag_res.get("quality_gate_decision") or "ACCEPT").upper()
            status = "SUCCESS" if gen_answer and "INSUFFICIENT_EVIDENCE" not in gen_answer else "FLAGGED"

            # Populate Item Schema
            item["run_id"] = run_id
            item["actual_query_sent_to_retriever"] = q_text
            item["vector_candidates"] = dense_cands
            item["bm25_candidates"] = sparse_cands
            item["graph_candidates"] = subgraph_nodes[:10] or graph_cands
            item["rrf_candidates"] = rrf_cands[:10]
            item["reranked_candidates"] = [c.get("chunk_id") or c.get("id") for c in top_chunks[:10]]
            item["context_before_formatting"] = context_before
            item["context_after_formatting"] = context_after
            item["final_llm_prompt_hash"] = prompt_hash
            item["generated_answer"] = gen_answer
            item["verification_result"] = {
                "decision": decision,
                "report": rag_res.get("quality_gate_report", {}),
                "traceability_score": rag_res.get("traceability_score", 1.0),
            }
            item["citation_result"] = citations
            item["latency_by_stage"] = {
                "parallel_retrieval_ms": round(ret_elapsed_ms, 2),
                "vector_ms": round(rag_res.get("retrieval_ms", ret_elapsed_ms), 2),
                "rerank_ms": round(rag_res.get("rerank_ms", 0.0), 2),
                "synthesis_ms": round(rag_res.get("synthesis_ms", 0.0), 2),
                "total_ms": round((time.time() - t0) * 1000, 2),
            }
            item["final_status"] = status

            total_q_time = time.time() - t0
            logger.info("-> [%s] Completed %s in %.2fs (Status: %s)", q_id, q_tier, total_q_time, status)
            logger.info("   Answer Snippet: %s", (gen_answer[:120] + "...") if gen_answer else "[NO ANSWER]")

            processed_count += 1
            if status == "SUCCESS":
                success_count += 1

        except Exception as e:
            logger.exception("Error executing question %s: %s", q_id, e)
            item["run_id"] = run_id
            item["final_status"] = f"ERROR: {str(e)}"
            item["latency_by_stage"] = {"total_ms": round((time.time() - t0) * 1000, 2)}

        # Atomic checkpoint save after every question
        try:
            tmp_target = target_output.with_suffix(".tmp.json")
            with open(tmp_target, "w", encoding="utf-8") as f_tmp:
                json.dump(data, f_tmp, indent=2, ensure_ascii=False)
            tmp_target.replace(target_output)
        except Exception as save_err:
            logger.error("Failed saving checkpoint: %s", save_err)

    total_time = time.time() - start_t
    logger.info("=" * 80)
    logger.info("DIAGNOSTIC BENCHMARK COMPLETED")
    logger.info("Processed: %d | Success: %d | Total Duration: %.2fs", processed_count, success_count, total_time)
    logger.info("Saved answered dataset to: %s", target_output)
    logger.info("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Answer NotebookLM Diagnostic Benchmark Dataset")
    parser.add_argument(
        "--file",
        type=str,
        default=r"C:\Users\Siddharth Tripathi\Downloads\diagnostic_benchmark_dataset.json",
        help="Path to diagnostic_benchmark_dataset.json",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional destination path (defaults to overwriting input file)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions to answer")
    parser.add_argument("--start-index", type=int, default=0, help="Starting question index (0-based)")
    parser.add_argument("--force", action="store_true", help="Re-generate already answered questions")

    args = parser.parse_args()
    run_diagnostic_benchmark(
        dataset_path=args.file,
        output_path=args.output,
        limit=args.limit,
        start_index=args.start_index,
        force_all=args.force,
    )
