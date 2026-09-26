"""
FRAMES Benchmark Master Runner
CLI and programmatic entry point for executing the FRAMES benchmark across:
  - Mode A: Vector-Only RAG
  - Mode B: Graph-Only Retrieval
  - Mode C: Hybrid GraphRAG (Default)
Guarantees 100% database isolation, strict anti-leakage protection, and reproducible experiment logging.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ..data.loader import FramesDatasetLoader
from ..data.schema import FramesQuestion
from ..isolation.harness import IsolatedFramesHarness
from ..evaluators.factuality import FactualityEvaluator
from ..evaluators.reasoning import ReasoningEvaluator
from ..evaluators.retrieval import RetrievalEvaluator
from ..evaluators.diagnostician import FailureDiagnostician
from .reporter import FramesReporter

logger = logging.getLogger("raise.frames.runner")



def parse_wikitables_to_markdown(
    html_content: str,
    max_tables: int = 4,
    slice_size: int = 40,
    max_total_slices: int = 8,
    max_rows: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Extracts wikitables from Wikipedia HTML and formats them into clean, structured Markdown tables.
    Preserves caption, column headers, and partitions large tables into sliced chunks to avoid truncation.
    Maintains backward compatibility with max_rows.
    """
    if max_rows is not None:
        slice_size = max_rows

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all("table", class_=lambda c: c and any(k in c for k in ["wikitable", "infobox"]))
    parsed: List[Dict[str, Any]] = []

    for t_idx, table in enumerate(tables[:max_tables]):
        classes = table.get("class", [])
        is_infobox = any("infobox" in c for c in classes)

        caption = table.find("caption")
        if caption:
            cap_text = caption.get_text().strip()
        elif is_infobox:
            cap_text = "Infobox Summary"
        else:
            prev_heading = table.find_previous(["h2", "h3", "h4"])
            cap_text = prev_heading.get_text().strip() if prev_heading else f"Table {t_idx+1}"
        cap_text = re.sub(r"\[.*?\]", "", cap_text).strip() or f"Table {t_idx+1}"

        rows = table.find_all("tr")
        if not rows:
            continue

        if is_infobox:
            headers = ["Attribute", "Value"]
            valid_rows = []
            for row in rows:
                cells = row.find_all(["th", "td"])
                if len(cells) == 2:
                    k = re.sub(r"\[.*?\]", "", cells[0].get_text().strip()).replace("\n", " ")
                    v = re.sub(r"\[.*?\]", "", cells[1].get_text().strip()).replace("\n", " ")
                    if k and v:
                        valid_rows.append([k, v])
                elif len(cells) == 1 and not valid_rows:
                    first_txt = re.sub(r"\[.*?\]", "", cells[0].get_text().strip())
                    if first_txt:
                        cap_text = first_txt
        else:
            header_cells = rows[0].find_all(["th", "td"])
            headers = [re.sub(r"\[.*?\]", "", h.get_text().strip()).replace("\n", " ").strip() for h in header_cells]
            headers = [h if h else f"Col_{i+1}" for i, h in enumerate(headers)]
            if not headers:
                continue

            valid_rows = []
            for row in rows[1:]:
                cells = row.find_all(["th", "td"])
                if not cells:
                    continue
                row_vals = [re.sub(r"\[.*?\]", "", c.get_text().strip()).replace("\n", " ").strip() for c in cells]
                if not any(row_vals):
                    continue
                if len(row_vals) < len(headers):
                    row_vals.extend([""] * (len(headers) - len(row_vals)))
                elif len(row_vals) > len(headers):
                    row_vals = row_vals[:len(headers)]
                valid_rows.append(row_vals)

        if not valid_rows:
            continue

        # Partition large tables into row slices of slice_size, repeating headers
        for s_idx in range(0, min(len(valid_rows), 160), slice_size):
            slice_rows = valid_rows[s_idx : s_idx + slice_size]
            slice_label = f" (Part {s_idx//slice_size + 1}, rows {s_idx+1}-{s_idx+len(slice_rows)})" if len(valid_rows) > slice_size else ""
            md_lines = [f"### Table: {cap_text}{slice_label}"]
            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for rvals in slice_rows:
                md_lines.append("| " + " | ".join(rvals) + " |")

            parsed.append({
                "caption": f"{cap_text}{slice_label}",
                "headers": headers,
                "markdown": "\n".join(md_lines),
                "row_count": len(slice_rows),
            })
            if len(parsed) >= max_total_slices:
                break
        if len(parsed) >= max_total_slices:
            break

    return parsed


def resolve_default_graph_backend(requested_backend: Optional[str] = None) -> str:
    """Resolves graph backend: if 'auto' or unspecified, uses live Neo4j if available, else networkx."""
    if requested_backend and requested_backend.lower() in ("neo4j", "networkx"):
        return requested_backend.lower()
    try:
        from src.infrastructure.graph.neo4j import Neo4jDatabase
        db = Neo4jDatabase()
        if db.connected:
            return "neo4j"
    except Exception:
        pass
    return "networkx"


class FramesBenchmarkRunner:
    """
    Executes controlled, reproducible evaluations of the RAISE pipeline against FRAMES.
    """

    def __init__(
        self,
        mode: str = "hybrid",
        output_dir: Optional[Path | str] = None,
        experiment_name: Optional[str] = None,
        seed: int = 42,
        throttle_ms: int = 150,
        use_cpu_embeddings: bool = False,
        graph_backend: Optional[str] = "auto",
    ):
        self.mode = mode.lower()
        if self.mode not in ["vector", "graph", "hybrid"]:
            raise ValueError(f"Invalid mode: '{mode}'. Must be 'vector', 'graph', or 'hybrid'")

        self.graph_backend = resolve_default_graph_backend(graph_backend)

        default_out = PROJECT_ROOT.parent / "Artifacts" / "benchmarks" / "frames"
        self.output_dir = Path(output_dir or default_out).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.experiment_id = experiment_name or f"frames_{self.mode}_{self.graph_backend}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.seed = seed
        random.seed(seed)
        self.throttle_ms = max(0, throttle_ms)
        self.use_cpu_embeddings = use_cpu_embeddings

        # Components
        self.loader = FramesDatasetLoader()
        self.factuality_evaluator = FactualityEvaluator()
        self.reasoning_evaluator = ReasoningEvaluator()
        self.retrieval_evaluator = RetrievalEvaluator()
        self.diagnostician = FailureDiagnostician()
        self.reporter = FramesReporter(self.output_dir)

    def _fetch_wikipedia_passages(self, wiki_url: str, max_chunks_per_article: int = 25) -> List[Dict[str, Any]]:
        """
        Fetches full Wikipedia article text and chunks it into section-oriented passages.
        Uses local disk caching for instant subsequent retrievals.
        Strict anti-leakage guarantee: never accesses benchmark ground truth answers.
        """
        slug = wiki_url.split("/")[-1].split("#")[0]
        title_decoded = urllib.parse.unquote(slug).replace("_", " ")
        if not title_decoded:
            return []

        # 1. Check local cache
        cache_dir = Path(self.output_dir).parent / "cache" / "wiki"
        cache_dir.mkdir(parents=True, exist_ok=True)
        safe_slug = re.sub(r"[^\w\-_\.]", "_", slug)
        cache_file = cache_dir / f"{safe_slug}.json"
        table_cache_file = cache_dir / f"{safe_slug}_tables.json"

        extract_text = None
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as cf:
                    cached_data = json.load(cf)
                    extract_text = cached_data.get("extract")
            except Exception:
                pass

        # 2. If not cached, fetch via MediaWiki Action API
        if not extract_text:
            try:
                api_url = (
                    f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts"
                    f"&redirects=1&explaintext=1&titles={urllib.parse.quote(title_decoded)}&format=json"
                )
                req = urllib.request.Request(
                    api_url,
                    headers={"User-Agent": "RAISE-Frames-Benchmark/1.0 (Academic Research; https://github.com/semanticClimate/RAISE)"}
                )
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    raw_data = json.loads(resp.read().decode("utf-8"))
                    pages = raw_data.get("query", {}).get("pages", {})
                    if pages:
                        first_page = list(pages.values())[0]
                        extract_text = first_page.get("extract", "")
                        resolved_title = first_page.get("title", title_decoded)
                        if extract_text:
                            with open(cache_file, "w", encoding="utf-8") as cf:
                                json.dump({"url": wiki_url, "title": resolved_title, "extract": extract_text}, cf)
            except Exception as e:
                logger.debug(f"MediaWiki API fetch failed for {title_decoded} ({e}), trying REST fallback")

        # 3. Fallback to summary REST endpoint if extract still empty
        if not extract_text:
            try:
                rest_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(slug)}"
                req = urllib.request.Request(rest_url, headers={"User-Agent": "RAISE-Frames-Benchmark/1.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    sdata = json.loads(resp.read().decode("utf-8"))
                    extract_text = sdata.get("extract", "")
            except Exception:
                pass

        # 4. Fetch and Cache HTML Wikitables for tabular reasoning
        tables_data: List[Dict[str, Any]] = []
        if table_cache_file.exists():
            try:
                with open(table_cache_file, "r", encoding="utf-8") as tf:
                    tables_data = json.load(tf)
            except Exception:
                tables_data = []

        if not tables_data:
            try:
                html_url = f"https://en.wikipedia.org/api/rest_v1/page/html/{urllib.parse.quote(slug)}"
                req = urllib.request.Request(html_url, headers={"User-Agent": "RAISE-Frames-Benchmark/1.0"})
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    html_content = resp.read().decode("utf-8", errors="ignore")
                    tables_data = parse_wikitables_to_markdown(html_content, max_tables=6, slice_size=40, max_total_slices=10)
                    if tables_data:
                        with open(table_cache_file, "w", encoding="utf-8") as tf:
                            json.dump(tables_data, tf)
            except Exception as e:
                logger.debug(f"HTML table extraction notice for {title_decoded}: {e}")

        chunks: List[Dict[str, Any]] = []
        import hashlib
        h_sfx = hashlib.md5(wiki_url.encode("utf-8")).hexdigest()[:6]
        clean_slug = re.sub(r"[^\w]", "_", slug)[:20]

        # Ingest parsed wikitables as first-class structured table chunks
        for t_idx, tbl in enumerate(tables_data[:4]):
            cap = tbl.get("caption", f"Data Table {t_idx+1}")
            md = tbl.get("markdown", "")
            if md:
                formatted_tbl = f"[Document: {title_decoded} | Section: Table | Table: {cap}]\n{md}"
                chunks.append({
                    "chunk_id": f"wiki_tbl_{clean_slug}_{h_sfx}_{t_idx}",
                    "title": title_decoded,
                    "document": title_decoded,
                    "section": f"Table: {cap}",
                    "heading": f"Table: {cap}",
                    "text": formatted_tbl,
                    "plain_text": formatted_tbl,
                    "source_url": wiki_url,
                    "entities": [title_decoded],
                    "is_table": True,
                    "metadata": {
                        "is_table": "true",
                        "table_caption": cap,
                        "row_count": str(tbl.get("row_count", 0)),
                        "document": title_decoded,
                        "section": f"Table: {cap}",
                        "heading": f"Table: {cap}",
                        "page": 1,
                    },
                })

        # 5. If completely offline and uncached, generate synthetic informative stub
        if not extract_text and not chunks:
            stub_txt = f"[Document: {title_decoded} | Section: Overview]\nArticle subject: {title_decoded}. Overview details regarding {title_decoded} and related biographical, historical, and institutional context."
            return [{
                "chunk_id": f"wiki_stub_{slug[:16]}_{hash(slug) % 10000}",
                "title": title_decoded,
                "document": title_decoded,
                "section": "Overview",
                "heading": "Overview",
                "text": stub_txt,
                "plain_text": stub_txt,
                "source_url": wiki_url,
                "entities": [title_decoded],
                "metadata": {
                    "document": title_decoded,
                    "section": "Overview",
                    "heading": "Overview",
                    "page": 1,
                },
            }]

        # 6. Chunk prose extract into section-aware passages (~400-1000 chars)
        if extract_text:
            lines = extract_text.split("\n")
            current_section = "Overview"
            buffer: List[str] = []
            buf_len = 0
            skip_sections = {"references", "see also", "external links", "further reading", "notes", "sources"}

            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue
                sec_m = re.match(r"^={2,4}\s*(.+?)\s*={2,4}$", line_str)
                if sec_m:
                    # Flush remaining buffer for the previous section before transitioning
                    if buffer and current_section != "SKIP" and len(chunks) < max_chunks_per_article:
                        p_text = " ".join(buffer).strip()
                        if p_text:
                            formatted_p = f"[Document: {title_decoded} | Section: {current_section}]\n{p_text}"
                            chunks.append({
                                "chunk_id": f"wiki_{clean_slug}_{h_sfx}_{len(chunks)}",
                                "title": title_decoded,
                                "document": title_decoded,
                                "section": current_section,
                                "heading": current_section,
                                "text": formatted_p,
                                "plain_text": formatted_p,
                                "source_url": wiki_url,
                                "entities": [title_decoded],
                                "metadata": {
                                    "document": title_decoded,
                                    "section": current_section,
                                    "heading": current_section,
                                    "page": 1,
                                },
                            })
                    buffer = []
                    buf_len = 0

                    sec_name = sec_m.group(1).strip()
                    if sec_name.lower() in skip_sections:
                        current_section = "SKIP"
                    else:
                        current_section = sec_name
                    continue
                if current_section == "SKIP":
                    continue

                buffer.append(line_str)
                buf_len += len(line_str)
                if buf_len >= 500:
                    p_text = " ".join(buffer)
                    formatted_p = f"[Document: {title_decoded} | Section: {current_section}]\n{p_text}"
                    chunks.append({
                        "chunk_id": f"wiki_{clean_slug}_{h_sfx}_{len(chunks)}",
                        "title": title_decoded,
                        "document": title_decoded,
                        "section": current_section,
                        "heading": current_section,
                        "text": formatted_p,
                        "plain_text": formatted_p,
                        "source_url": wiki_url,
                        "entities": [title_decoded],
                        "metadata": {
                            "document": title_decoded,
                            "section": current_section,
                            "heading": current_section,
                            "page": 1,
                        },
                    })
                    buffer = []
                    buf_len = 0
                    if len(chunks) >= max_chunks_per_article:
                        break

            if buffer and len(chunks) < max_chunks_per_article:
                p_text = " ".join(buffer)
                formatted_p = f"[Document: {title_decoded} | Section: {current_section}]\n{p_text}"
                chunks.append({
                    "chunk_id": f"wiki_{clean_slug}_{h_sfx}_{len(chunks)}",
                    "title": title_decoded,
                    "document": title_decoded,
                    "section": current_section,
                    "heading": current_section,
                    "text": formatted_p,
                    "plain_text": formatted_p,
                    "source_url": wiki_url,
                    "entities": [title_decoded],
                    "metadata": {
                        "document": title_decoded,
                        "section": current_section,
                        "heading": current_section,
                        "page": 1,
                    },
                })

        return chunks

    def prepare_evaluation_corpus(
        self,
        questions: List[FramesQuestion],
        harness: IsolatedFramesHarness,
    ) -> int:
        """
        Gathers Wikipedia source passages for the target benchmark questions
        and indexes them into the isolated evaluation stores.
        Enforces strict anti-leakage: asserts that reference answers are NEVER indexed.
        """
        all_urls: Set[str] = set()
        quarantined_answers: Set[str] = set()

        for q in questions:
            quarantined_answers.add(q.reference_answer.strip())
            for url in q.wiki_links:
                if url:
                    all_urls.add(url)

        logger.info(f"Gathering evaluation corpus for {len(all_urls)} unique Wikipedia source links (ThreadPool concurrent fetch)...")
        passages: List[Dict[str, Any]] = []

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(self._fetch_wikipedia_passages, url): url for url in all_urls}
            for future in as_completed(future_to_url):
                try:
                    p_list = future.result()
                    if p_list:
                        passages.extend(p_list)
                except Exception as e:
                    logger.debug(f"Failed fetching passages for {future_to_url[future]}: {e}")

        # Build cross-article entity connections for GraphRAG multi-hop traversal
        all_titles = {p.get("title") for p in passages if p.get("title")}
        for p in passages:
            cur_title = p.get("title", "")
            txt_lower = p.get("text", "").lower()
            cross_refs = set(p.get("entities", []))
            for other_t in all_titles:
                if other_t and other_t != cur_title and len(other_t) > 3 and other_t.lower() in txt_lower:
                    cross_refs.add(other_t)
            p["entities"] = list(cross_refs)

        # Ingest into harness with strict anti-leakage verification
        count = harness.ingest_evaluation_passages(
            passages=passages,
            verify_no_answer_leakage=quarantined_answers,
        )
        return count

    def run(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        reasoning_type: Optional[str] = None,
        resume: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes the benchmark evaluation run with crash-resilient checkpointing.
        """
        t_start = time.perf_counter()
        logger.info(f"=== Starting FRAMES Benchmark Run [{self.experiment_id} | Mode: {self.mode}] ===")

        # 1. Load Questions
        questions = self.loader.get_questions(reasoning_type=reasoning_type, limit=limit, offset=offset)
        logger.info(f"Selected {len(questions)} questions for evaluation (Filter: {reasoning_type or 'All'}).")

        # Prepare Checkpoint Ledger
        ckpt_dir = self.output_dir / "checkpoints"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        ckpt_file = ckpt_dir / f"{self.experiment_id}_checkpoint.jsonl"

        results: List[Dict[str, Any]] = []
        latencies: List[float] = []
        completed_ids: Set[str] = set()

        if resume and ckpt_file.exists():
            try:
                with open(ckpt_file, "r", encoding="utf-8", errors="ignore") as cf:
                    for line in cf:
                        line = line.strip()
                        if line and not line.startswith("\x00"):
                            try:
                                rec = json.loads(line)
                                qid = str(rec.get("question_id"))
                                if qid not in completed_ids:
                                    completed_ids.add(qid)
                                    results.append(rec)
                                    latencies.append(rec.get("total_latency_ms", 0.0))
                            except Exception:
                                continue
                logger.info(f"✨ [CHECKPOINT RESUME]: Loaded {len(completed_ids)} previously evaluated questions from {ckpt_file.name}.")
            except Exception as e:
                logger.warning(f"Failed reading checkpoint file {ckpt_file}: {e}")

        # 2. Instantiate Isolated Sandbox Harness
        harness = IsolatedFramesHarness(
            session_id=self.experiment_id,
            device="cpu" if self.use_cpu_embeddings else None,
            graph_backend=self.graph_backend,
        )

        try:
            # 3. Prepare Sandboxed Corpus (for pending questions if resuming, avoiding redundant re-fetching)
            pending_questions = [q for q in questions if str(q.question_id) not in completed_ids] if completed_ids else questions
            corpus_count = self.prepare_evaluation_corpus(pending_questions, harness)
            logger.info(f"Isolated evaluation store populated with {corpus_count} passages for {len(pending_questions)} questions.")

            # 4. Execute Questions
            for idx, q in enumerate(questions):
                if str(q.question_id) in completed_ids:
                    continue

                logger.info(f"Evaluating Question {idx+1}/{len(questions)} [ID: {q.question_id}] ({len(results)+1}/{len(questions)})...")
                trace = harness.execute_question(q, mode=self.mode, top_k=18)
                latencies.append(trace["total_latency_ms"])

                # Run Evaluators
                chunks = trace.get("retrieval_trace", {}).get("retrieved_chunks", [])
                context = trace.get("full_context") or "\n\n".join(c.get("text", "") for c in chunks) or trace.get("context_preview", "")
                gen_ans = trace.get("generated_answer", "")

                fact_res = self.factuality_evaluator.evaluate(q, gen_ans, context)
                reas_res = self.reasoning_evaluator.evaluate(q, gen_ans, context)
                ret_res = self.retrieval_evaluator.evaluate(q, chunks)
                diag_res = self.diagnostician.diagnose(q, fact_res, reas_res, ret_res, trace)

                record = {
                    "question_id": q.question_id,
                    "prompt": q.prompt,
                    "reference_answer": q.reference_answer,
                    "reasoning_types": q.reasoning_types,
                    "wiki_links": q.wiki_links,
                    "generated_answer": gen_ans,
                    "factuality_score": fact_res.reference_correctness_score,
                    "answer_status": fact_res.answer_status,
                    "generation_mode": trace.get("generation_mode"),
                    "reasoning_trace": trace.get("reasoning_trace", ""),
                    "total_latency_ms": trace.get("total_latency_ms"),
                    "stage_latencies": trace.get("stage_latencies", {}),
                    "multihop_plan": trace.get("multihop_plan", {}),
                    "proof_ledger": trace.get("proof_ledger", {}),
                    "audit": trace.get("audit", {}),
                    "factuality": fact_res.model_dump(),
                    "reasoning": reas_res.model_dump(),
                    "retrieval": ret_res.model_dump(),
                    "diagnosis": diag_res.model_dump(),
                    "retrieved_sources": trace.get("retrieved_sources", []),
                    "retrieved_chunks_count": trace.get("retrieved_chunks_count", 0),
                    "context_tokens_estimate": trace.get("context_tokens_estimate", 0),
                    "transition_trace": trace.get("transition_trace", []),
                }
                results.append(record)
                completed_ids.add(str(q.question_id))

                # Detailed informative per-question logging
                verdict_icon = "🟢" if fact_res.reference_correctness_score >= 0.8 else ("🛡️" if "insufficient" in str(gen_ans).lower() else "🔴")
                logger.info(
                    f"{verdict_icon} [{len(results)}/{len(questions)}] Q{q.question_id} [{fact_res.answer_status.upper()}]: "
                    f"Score={fact_res.reference_correctness_score:.2f} ({trace.get('total_latency_ms', 0):.0f}ms) | "
                    f"Pred: '{gen_ans[:45]}' | Ref: '{q.reference_answer[:35]}'"
                )

                # Immediately commit to checkpoint file
                try:
                    with open(ckpt_file, "a", encoding="utf-8") as cf:
                        cf.write(json.dumps(record, ensure_ascii=False) + "\n")
                        cf.flush()
                        os.fsync(cf.fileno())
                except Exception as ce:
                    logger.warning(f"Error appending to checkpoint file: {ce}")

                # Periodic progress logging
                if len(results) % 10 == 0 or len(results) == len(questions):
                    pct = (len(results) / len(questions)) * 100
                    acc = sum(1 for r in results if r.get("factuality_score", 0) >= 0.8) / max(1, len(results)) * 100
                    logger.info(f"📊 [BENCHMARK PROGRESS]: {len(results)}/{len(questions)} ({pct:.1f}%) | Running Accuracy: {acc:.1f}%")

                # Duty-cycle pause between questions to allow GPU thermals to stabilize
                if self.throttle_ms > 0:
                    time.sleep(self.throttle_ms / 1000.0)

            # 5. Compute Aggregate Metrics
            agg_metrics = self._aggregate_metrics(results, latencies)

            # 6. Failure Analysis
            failure_summary = self._analyze_failures(results)

            # 7. Experiment Config with Authoritative Run Metadata Snapshot
            run_metadata = self._build_run_metadata(harness)
            exp_config = {
                "experiment_id": self.experiment_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pipeline_version": "2.5.0",
                "retrieval_mode": self.mode,
                "dataset_version": self.loader.ensure_dataset().stat().st_size,
                "sample_count": len(results),
                "embedding_model": harness.vector_engine.model_key,
                "vector_dimension": harness.dimension,
                "seed": self.seed,
                "runtime_seconds": round(time.perf_counter() - t_start, 2),
                "run_metadata": run_metadata,
            }

            # 8. Generate Reports
            report_files = self.reporter.generate_all_reports(
                experiment_config=exp_config,
                raw_results=results,
                aggregate_metrics=agg_metrics,
                failure_analysis=failure_summary,
            )

            logger.info(f"=== Completed FRAMES Benchmark Run [{self.experiment_id}] in {exp_config['runtime_seconds']}s ===")
            return {
                "experiment_config": exp_config,
                "run_metadata": run_metadata,
                "aggregate_metrics": agg_metrics,
                "failure_analysis": failure_summary,
                "reports": {k: str(v) for k, v in report_files.items()},
            }

        finally:
            harness.teardown()

    def _build_run_metadata(self, harness: IsolatedFramesHarness) -> Dict[str, Any]:
        """Collects exhaustive run-level telemetry, environment, git, and storage snapshot."""
        # VCS metadata
        git_info = {"commit": "unknown", "branch": "unknown", "is_dirty": False}
        try:
            res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
            if res.returncode == 0:
                git_info["commit"] = res.stdout.strip()
            res_b = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
            if res_b.returncode == 0:
                git_info["branch"] = res_b.stdout.strip()
            res_s = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
            if res_s.returncode == 0:
                git_info["is_dirty"] = bool(res_s.stdout.strip())
        except Exception:
            pass

        # Environment metadata
        env_meta: Dict[str, Any] = {
            "os": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count(),
        }
        try:
            import torch
            env_meta["pytorch_version"] = torch.__version__
            env_meta["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                env_meta["cuda_device_name"] = torch.cuda.get_device_name(0)
                env_meta["cuda_device_count"] = torch.cuda.device_count()
        except Exception:
            pass

        # Storage & Substrate snapshot
        chroma_count = 0
        try:
            chroma_count = harness.vector_engine.count()
        except Exception:
            pass

        neo4j_stats = {"nodes": 0, "edges": 0, "connected": False}
        try:
            if getattr(harness, "neo4j_driver", None):
                with harness.neo4j_driver.session() as s:
                    nr = s.run("MATCH (n) RETURN count(n) AS c").single()
                    er = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()
                    neo4j_stats["nodes"] = nr["c"] if nr else 0
                    neo4j_stats["edges"] = er["c"] if er else 0
                    neo4j_stats["connected"] = True
        except Exception:
            pass

        return {
            "vcs": git_info,
            "environment": env_meta,
            "storage_snapshot": {
                "chroma_vectors": chroma_count,
                "neo4j": neo4j_stats,
                "collection_name": getattr(harness.vector_engine, "collection_name", "ephemeral"),
            },
            "models": {
                "embedding_model": harness.vector_engine.model_key,
                "vector_dimension": harness.dimension,
                "generation_mode": self.mode,
            },
        }

    def _aggregate_metrics(
        self,
        results: List[Dict[str, Any]],
        latencies: List[float],
    ) -> Dict[str, Any]:
        """Calculates honest metric scores across factuality, reasoning, retrieval, and latencies."""
        total = len(results)
        if total == 0:
            return {}

        fact_scores = [r["factuality"]["factuality_score"] for r in results]
        ref_scores = [r["factuality"]["reference_correctness_score"] for r in results]
        grounding_scores = [r["factuality"]["grounding_score"] for r in results]
        reas_scores = [r["reasoning"]["overall_reasoning_score"] for r in results]
        cov_scores = [r["retrieval"]["evidence_coverage"] for r in results]
        hit_rates = [r["retrieval"]["hit_rate"] for r in results]

        sorted_lat = sorted(latencies)
        p50 = sorted_lat[int(len(sorted_lat) * 0.50)] if sorted_lat else 0.0
        p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else 0.0

        retrieval_lats = [r.get("stage_latencies", {}).get("retrieval_ms", 0.0) for r in results]
        generation_lats = [r.get("stage_latencies", {}).get("generation_ms", 0.0) for r in results]
        med_retrieval_ms = sorted(retrieval_lats)[int(len(retrieval_lats) * 0.5)] if retrieval_lats else 0.0
        med_generation_ms = sorted(generation_lats)[int(len(generation_lats) * 0.5)] if generation_lats else 0.0

        correct_count = sum(1 for r in results if r["factuality"]["answer_status"] == "correct")
        partial_count = sum(1 for r in results if r["factuality"]["answer_status"] == "partially_correct")
        incorrect_count = sum(1 for r in results if r["factuality"]["answer_status"] == "incorrect")
        abstained_count = sum(1 for r in results if r["factuality"]["answer_status"] == "abstained")
        unanswerable_count = sum(1 for r in results if r["factuality"]["answer_status"] == "unanswerable")
        unsupported_count = sum(
            1 for r in results
            if r["factuality"]["answer_status"] == "unsupported"
            or r["diagnosis"]["primary_failure"] in ["UNSUPPORTED_CLAIM", "HALLUCINATION"]
        )
        fallback_count = sum(
            1 for r in results
            if r.get("generation_mode") in ["controlled_abstention", "deterministic_fallback"]
            or r.get("diagnosis", {}).get("primary_failure") == "FALLBACK_FAILURE"
        )

        answer_correctness_rate = round(correct_count / total, 4)
        abstention_rate = round(abstained_count / total, 4)
        non_answer_rate = round((abstained_count + unanswerable_count) / total, 4)
        unsupported_claim_rate = round(unsupported_count / total, 4)

        mean_fact = sum(fact_scores) / total
        mean_reas = sum(reas_scores) / total
        mean_cov = sum(cov_scores) / total
        mean_hit = sum(hit_rates) / total

        # Overall Harmonic Benchmark Score
        overall = round((mean_fact * 0.40) + (mean_reas * 0.35) + (mean_cov * 0.25), 4)

        # Breakdown by Reasoning Type
        by_reasoning: Dict[str, Any] = {}
        for r in results:
            for rtype in r["reasoning_types"]:
                if rtype not in by_reasoning:
                    by_reasoning[rtype] = {"scores": [], "count": 0}
                by_reasoning[rtype]["scores"].append(r["reasoning"]["overall_reasoning_score"])
                by_reasoning[rtype]["count"] += 1

        reasoning_summary = {}
        for rtype, data in by_reasoning.items():
            scs = data["scores"]
            reasoning_summary[rtype] = {
                "count": data["count"],
                "mean_score": round(sum(scs) / len(scs), 4),
                "pass_rate": round(sum(1 for s in scs if s >= 0.70) / len(scs), 4),
            }

        return {
            "total_questions": total,
            "overall_score": overall,
            "correct_count": correct_count,
            "partially_correct_count": partial_count,
            "incorrect_count": incorrect_count,
            "abstained_count": abstained_count,
            "unanswerable_count": unanswerable_count,
            "fallback_count": fallback_count,
            "answer_correctness_rate": answer_correctness_rate,
            "abstention_rate": abstention_rate,
            "non_answer_rate": non_answer_rate,
            "unsupported_claim_rate": unsupported_claim_rate,
            "hallucination_rate": unsupported_claim_rate,
            "mean_factuality": round(mean_fact, 4),
            "mean_reference_correctness": round(sum(ref_scores) / total, 4),
            "mean_grounding": round(sum(grounding_scores) / total, 4),
            "mean_reasoning": round(mean_reas, 4),
            "mean_retrieval_coverage": round(mean_cov, 4),
            "hit_rate": round(mean_hit, 4),
            "latency_p50_ms": round(p50, 2),
            "latency_p95_ms": round(p95, 2),
            "latency_median_retrieval_ms": round(med_retrieval_ms, 2),
            "latency_median_generation_ms": round(med_generation_ms, 2),
            "by_reasoning_type": reasoning_summary,
        }

    def _analyze_failures(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorizes failures according to the 13-category taxonomy."""
        counts: Dict[str, int] = {cat: 0 for cat in FailureDiagnostician.TAXONOMY}
        failed_records: List[Dict[str, Any]] = []

        for r in results:
            diag = r.get("diagnosis", {})
            if diag.get("is_failure"):
                pf = diag.get("primary_failure") or "UNKNOWN_FAILURE"
                counts[pf] = counts.get(pf, 0) + 1
                failed_records.append({
                    "question_id": r["question_id"],
                    "prompt": r["prompt"][:80],
                    "primary_failure": pf,
                    "probable_cause": diag.get("probable_cause"),
                })

        total_failures = len(failed_records)
        return {
            "total_failures": total_failures,
            "failure_rate": round(total_failures / max(1, len(results)), 4),
            "failure_counts": counts,
            "failed_samples": failed_records[:10],
        }


def main():
    parser = argparse.ArgumentParser(description="RAISE FRAMES Benchmark Runner")
    parser.add_argument("--mode", choices=["vector", "graph", "hybrid"], default="hybrid", help="Retrieval mode to evaluate")
    parser.add_argument("--limit", type=int, default=None, help="Number of questions to evaluate")
    parser.add_argument("--offset", type=int, default=0, help="Starting index of questions")
    parser.add_argument("--reasoning-type", type=str, default=None, help="Filter by reasoning category")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory")
    parser.add_argument("--experiment-name", type=str, default=None, help="Custom experiment tag")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--resume", dest="resume", action="store_true", default=True, help="Resume from existing checkpoint if available")
    parser.add_argument("--no-resume", dest="resume", action="store_false", help="Ignore existing checkpoint and start fresh")
    parser.add_argument("--throttle-ms", type=int, default=150, help="Duty-cycle sleep in milliseconds between questions (default: 150ms)")
    parser.add_argument("--cpu-embeddings", action="store_true", default=False, help="Run embedding computations on CPU to reduce peak GPU power and VRAM load")
    parser.add_argument("--graph-backend", choices=["networkx", "neo4j", "auto"], default="auto", help="Graph substrate: 'auto' (detects live Neo4j, fallback to networkx), 'neo4j', or 'networkx'")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    runner = FramesBenchmarkRunner(
        mode=args.mode,
        output_dir=args.output_dir,
        experiment_name=args.experiment_name,
        seed=args.seed,
        throttle_ms=args.throttle_ms,
        use_cpu_embeddings=args.cpu_embeddings,
        graph_backend=args.graph_backend,
    )
    res = runner.run(limit=args.limit, offset=args.offset, reasoning_type=args.reasoning_type, resume=args.resume)

    metrics = res.get("aggregate_metrics", {})
    print("\n" + "=" * 78)
    print(f" 🏁 FRAMES EVALUATION COMPLETE: {res['experiment_config']['experiment_id']}")
    print(f" Mode: {args.mode.upper()} | Evaluated: {metrics.get('total_questions')} questions")
    print(f" Overall Score      : {metrics.get('overall_score', 0.0)*100:.2f}%")
    print(f" Factuality Score   : {metrics.get('mean_factuality', 0.0)*100:.2f}%")
    print(f" Reasoning Score    : {metrics.get('mean_reasoning', 0.0)*100:.2f}%")
    print(f" Evidence Coverage  : {metrics.get('mean_retrieval_coverage', 0.0)*100:.2f}%")
    print(f" Median Latency     : {metrics.get('latency_p50_ms', 0.0):.2f} ms")
    print(f" Reports Generated  : {res['reports'].get('markdown_report')}")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
