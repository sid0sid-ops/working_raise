"""
Milestone 1: FineCat-NLI vs Baseline Grounding Verifier Benchmark
================================================================
Head-to-head empirical comparison over the standardized 1,000-claim testbed:
  - 400 Entailed claims (Authentic academic facts with verifiable figures)
  - 300 Contradictory claims (Altered figures, inverted semantic assertions)
  - 300 Unsupported claims (Out-of-scope synthetic assertions)

Evaluator 1: CURRENT BASELINE (Tier 1 Numeric + Tier 2 Lexical Fast-Path + Tier 4 Fallback)
Evaluator 2: FINECAT-NLI AUGMENTED (Tier 1 Numeric + Tier 2 Lexical + Tier 3 FineCat-NLI ModernBERT + Tier 4 Fallback)

Tracks:
  - Accuracy, Precision, Recall, F1 Score
  - False Acceptance Rate (FAR) & False Rejection Rate (FRR)
  - Median & p95 Latency (ms)
  - Peak VRAM Consumption (MB)
  - Tier Resolution Breakdown
"""

import json
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
import random
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

RAG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAG_ROOT))

import torch

from src.core.config import settings
from src.features.evaluation.engine import (
    ClaimLevelVerifier,
    StructuredEvidence,
    NumericalClaimVerifier,
)
from src.features.evaluation.nli_verifier import FineCatNLIVerifier


def load_chunks_pool() -> List[Dict[str, Any]]:
    """Loads all extracted chunks from data/processed/chunks/."""
    chunks_dir = settings.processed_dir / "chunks"
    all_chunks = []
    seen_ids = set()
    for pattern in ["*_parent_chunks.json", "*_chunks.json"]:
        for f in chunks_dir.glob(pattern):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        cid = item.get("chunk_id")
                        if cid and cid not in seen_ids:
                            seen_ids.add(cid)
                            all_chunks.append(item)
                        elif not cid:
                            all_chunks.append(item)
            except Exception:
                pass
    return all_chunks


def generate_1000_claims_testbed(chunks: List[Dict[str, Any]], seed: int = 42) -> List[Dict[str, Any]]:
    """Generates 1,000 deterministic claims with balanced ground truth labels."""
    random.seed(seed)
    testbed = []

    # 1. 400 Entailed Claims (Label: 1 / ENTAILED)
    entailed_candidates = []
    for c in chunks:
        txt = c.get("text") or c.get("plain_text") or ""
        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', txt) if len(s.strip()) > 35]
        for s in sents:
            if re.search(r'\d+', s):
                entailed_candidates.append({
                    "claim_text": s,
                    "evidence_chunk": c,
                    "ground_truth_label": 1,
                    "category": "ENTAILED_NUMERIC_FACT",
                })
            elif len(s) > 50:
                entailed_candidates.append({
                    "claim_text": s,
                    "evidence_chunk": c,
                    "ground_truth_label": 1,
                    "category": "ENTAILED_TEXT_FACT",
                })

    random.shuffle(entailed_candidates)
    entailed_claims = entailed_candidates[:400]
    testbed.extend(entailed_claims)

    # 2. 300 Contradictory Claims (Label: 0 / CONTRADICTION)
    contradictory_claims = []
    for item in entailed_claims[:300]:
        orig_s = item["claim_text"]
        def corrupt_num(match):
            val = match.group(0)
            try:
                if "." in val:
                    f = float(val.replace(",", ""))
                    return f"{f * 2.5:.2f}"
                else:
                    i = int(val.replace(",", ""))
                    return str(i + 987)
            except Exception:
                return "99999"

        corrupted = re.sub(r'\b\d+(?:,\d+)*(?:\.\d+)?\b', corrupt_num, orig_s)
        if corrupted == orig_s:
            corrupted = f"It is completely false that {orig_s.lower()}"

        contradictory_claims.append({
            "claim_text": corrupted,
            "evidence_chunk": item["evidence_chunk"],
            "ground_truth_label": 0,
            "category": "CONTRADICTORY_FACT",
        })
    testbed.extend(contradictory_claims)

    # 3. 300 Unsupported / Out-of-scope Claims (Label: 0 / UNSUPPORTED)
    unsupported_templates = [
        "The institute invested $45 million into deep sea mining submarines in 2024.",
        "A total of 14,000 quantum computing patents were granted to the aerospace division.",
        "The annual report confirms the complete shutdown of all undergraduate degree programs.",
        "Over 98% of all operational budgets were redirected to Mars exploration vehicles.",
        "The Board of Governors unanimously dissolved the Department of Computer Science.",
        "Extramural funding dropped to exactly zero rupees due to nationwide budget cancellations.",
        "The university acquired a commercial airline fleet for student travel.",
        "Synthetic intelligence units replaced 100% of the active faculty workforce.",
        "All historical research archives prior to 2025 were permanently erased.",
        "The campus was relocated to a 100-acre floating platform in the Pacific Ocean."
    ]

    unsupported_claims = []
    chunk_count = len(chunks)
    for idx in range(300):
        template = unsupported_templates[idx % len(unsupported_templates)]
        assigned_chunk = chunks[(idx * 7) % chunk_count] if chunk_count > 0 else {}
        unsupported_claims.append({
            "claim_text": f"{template} (Reference index: {idx+1})",
            "evidence_chunk": assigned_chunk,
            "ground_truth_label": 0,
            "category": "UNSUPPORTED_OUT_OF_SCOPE",
        })
    testbed.extend(unsupported_claims)

    random.shuffle(testbed)
    return testbed


def evaluate_claim_with_verifier(
    claim_item: Dict[str, Any],
    nli_engine: Any = None,
    enable_nli: bool = False
) -> Dict[str, Any]:
    """Runs a single claim through the verifier and records latency and tier."""
    chunk = claim_item["evidence_chunk"]
    chunk_text = chunk.get("text") or chunk.get("plain_text") or ""
    metadata = chunk.get("metadata", {})
    ev = StructuredEvidence(
        vector_chunks=[{
            "chunk_id": chunk.get("chunk_id") or chunk.get("id") or "test_chunk",
            "plain_text": chunk_text,
            "metadata": {"doc_id": metadata.get("doc_id") or chunk.get("doc_id") or "test_doc", "primary_page": metadata.get("primary_page", 1)}
        }]
    )

    t0 = time.perf_counter()
    claims_list, faithfulness, num_mismatches, cit_errors = ClaimLevelVerifier.verify_claims(
        answer=claim_item["claim_text"],
        evidence=ev,
        nli_engine=nli_engine,
        enable_nli=enable_nli
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if claims_list:
        res = claims_list[0]
        status = res.status.upper()
        accepted = res.is_supported
        tier = res.verification_tier
    else:
        status = "UNSUPPORTED"
        accepted = False
        tier = "TIER4_FALLBACK"

    return {
        "accepted": accepted,
        "status": status,
        "latency_ms": elapsed_ms,
        "tier": tier,
        "ground_truth": claim_item["ground_truth_label"],
    }


def compute_metrics(eval_results: List[Dict[str, Any]], vram_start_mb: float, vram_peak_mb: float) -> Dict[str, Any]:
    """Computes precision, recall, FAR, FRR, accuracy, F1, and latency percentiles."""
    tp = sum(1 for r in eval_results if r["accepted"] and r["ground_truth"] == 1)
    fp = sum(1 for r in eval_results if r["accepted"] and r["ground_truth"] == 0)
    tn = sum(1 for r in eval_results if not r["accepted"] and r["ground_truth"] == 0)
    fn = sum(1 for r in eval_results if not r["accepted"] and r["ground_truth"] == 1)

    total = len(eval_results)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    # False Acceptance Rate (FAR) = FP / (FP + TN)
    far = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    # False Rejection Rate (FRR) = FN / (TP + FN)
    frr = fn / (tp + fn) if (tp + fn) > 0 else 0.0

    latencies = sorted(r["latency_ms"] for r in eval_results)
    p50 = statistics.median(latencies)
    p90 = latencies[int(len(latencies) * 0.90)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    tier_counts = {}
    for r in eval_results:
        t = r["tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_acceptance_rate_far": round(far, 4),
        "false_rejection_rate_frr": round(frr, 4),
        "confusion_matrix": {"true_positives": tp, "true_negatives": tn, "false_positives": fp, "false_negatives": fn},
        "latency_ms": {"median": round(p50, 2), "p90": round(p90, 2), "p95": round(p95, 2), "p99": round(p99, 2), "mean": round(statistics.mean(latencies), 2)},
        "vram_mb": {"start": round(vram_start_mb, 1), "peak": round(vram_peak_mb, 1), "delta": round(vram_peak_mb - vram_start_mb, 1)},
        "tier_breakdown": tier_counts
    }


def run_comparison_benchmark():
    print("=" * 75)
    print(" 🔬 RAISE MILESTONE 1: FINECAT-NLI VS BASELINE COMPARISON BENCHMARK")
    print(" 1,000 Claims: 400 Entailed, 300 Contradictory, 300 Unsupported")
    print("=" * 75)

    chunks = load_chunks_pool()
    print(f"Loaded {len(chunks)} processed chunks.")
    testbed = generate_1000_claims_testbed(chunks, seed=42)
    print(f"Generated standardized testbed: {len(testbed)} claims.")

    # -------------------------------------------------------------
    # Pass 1: Baseline Heuristic Verifier
    # -------------------------------------------------------------
    print("\n--- [1/2] RUNNING BASELINE HEURISTIC VERIFIER ---")
    baseline_results = []
    for idx, item in enumerate(testbed, 1):
        if idx % 200 == 0:
            print(f"  Processed {idx}/1000 claims (Baseline)...")
        r = evaluate_claim_with_verifier(item, nli_engine=None, enable_nli=False)
        baseline_results.append(r)

    baseline_metrics = compute_metrics(baseline_results, 0.0, 0.0)

    # -------------------------------------------------------------
    # Pass 2: FineCat-NLI Augmented Verifier
    # -------------------------------------------------------------
    print("\n--- [2/2] RUNNING FINECAT-NLI AUGMENTED VERIFIER ---")
    finecat_engine = FineCatNLIVerifier()
    vram_start = torch.cuda.memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else 0.0
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    neural_results = []
    for idx, item in enumerate(testbed, 1):
        if idx % 200 == 0:
            print(f"  Processed {idx}/1000 claims (FineCat-NLI)...")
        r = evaluate_claim_with_verifier(item, nli_engine=finecat_engine, enable_nli=True)
        neural_results.append(r)

    vram_peak = torch.cuda.max_memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else 0.0
    neural_metrics = compute_metrics(neural_results, vram_start, vram_peak)

    # Comparative Summary
    comparison = {
        "benchmark_name": "FINECAT_VS_BASELINE_GROUNDING_VERIFIER_1000",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_claims": len(testbed),
        "testbed_composition": {"entailed": 400, "contradictory": 300, "unsupported": 300},
        "baseline": baseline_metrics,
        "finecat_nli": neural_metrics,
        "delta": {
            "accuracy_delta": round(neural_metrics["accuracy"] - baseline_metrics["accuracy"], 4),
            "precision_delta": round(neural_metrics["precision"] - baseline_metrics["precision"], 4),
            "far_reduction": round(baseline_metrics["false_acceptance_rate_far"] - neural_metrics["false_acceptance_rate_far"], 4),
            "median_latency_overhead_ms": round(neural_metrics["latency_ms"]["median"] - baseline_metrics["latency_ms"]["median"], 2),
            "p95_latency_overhead_ms": round(neural_metrics["latency_ms"]["p95"] - baseline_metrics["latency_ms"]["p95"], 2),
            "vram_delta_mb": round(neural_metrics["vram_mb"]["delta"], 1),
        },
        "verdict": {
            "far_reduced_significantly": neural_metrics["false_acceptance_rate_far"] < baseline_metrics["false_acceptance_rate_far"],
            "recommendation": (
                "Deploy FINECAT-NLI: Effectively eliminates false acceptance on ambiguous and contradictory claims."
                if neural_metrics["false_acceptance_rate_far"] <= 0.10
                else "Maintain HYBRID GATING: Escalation gating safely confines neural latency to ambiguous claims."
            )
        }
    }

    print("\n" + "=" * 80)
    print(" 📊 HEAD-TO-HEAD VERIFIER COMPARISON (1,000 CLAIMS)")
    print("=" * 80)
    print(f"{'Metric':<30} | {'Baseline':<18} | {'FineCat-NLI':<18} | {'Delta':<15}")
    print("-" * 80)
    print(f"{'Accuracy':<30} | {baseline_metrics['accuracy']:<18.2%} | {neural_metrics['accuracy']:<18.2%} | {comparison['delta']['accuracy_delta']:+0.2%}")
    print(f"{'Precision':<30} | {baseline_metrics['precision']:<18.2%} | {neural_metrics['precision']:<18.2%} | {comparison['delta']['precision_delta']:+0.2%}")
    print(f"{'Recall':<30} | {baseline_metrics['recall']:<18.2%} | {neural_metrics['recall']:<18.2%} | {neural_metrics['recall'] - baseline_metrics['recall']:+0.2%}")
    print(f"{'False Acceptance Rate (FAR)':<30} | {baseline_metrics['false_acceptance_rate_far']:<18.2%} | {neural_metrics['false_acceptance_rate_far']:<18.2%} | {-comparison['delta']['far_reduction']:+0.2%}")
    print(f"{'Median Latency':<30} | {baseline_metrics['latency_ms']['median']:<15.2f} ms | {neural_metrics['latency_ms']['median']:<15.2f} ms | {comparison['delta']['median_latency_overhead_ms']:+0.2f} ms")
    print(f"{'p95 Latency':<30} | {baseline_metrics['latency_ms']['p95']:<15.2f} ms | {neural_metrics['latency_ms']['p95']:<15.2f} ms | {comparison['delta']['p95_latency_overhead_ms']:+0.2f} ms")
    print(f"{'Peak VRAM Allocated':<30} | {baseline_metrics['vram_mb']['peak']:<15.1f} MB | {neural_metrics['vram_mb']['peak']:<15.1f} MB | {comparison['delta']['vram_delta_mb']:+0.1f} MB")
    print("-" * 80)
    print(f"Architectural Verdict: {comparison['verdict']['recommendation']}")
    print("=" * 80)

    # Export to Artifacts
    output_path = RAG_ROOT.parent / "Artifacts" / "benchmarks" / "FINECAT_VS_BASELINE_COMPARISON.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)
    print(f"\n [✓] Comparative results exported to: {output_path}")

    return comparison


if __name__ == "__main__":
    run_comparison_benchmark()
