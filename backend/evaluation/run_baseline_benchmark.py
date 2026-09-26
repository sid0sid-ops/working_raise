"""
RAISE Grounding Verifier: Pure Baseline Benchmark (1,000 Claims)
================================================================
Executes empirical baseline evaluation on the standardized 1,000-claim testbed
BEFORE activating the FineCat-NLI neural model.

Evaluator:
  - Tier 1: Deterministic Numerical & Currency Range Checks
  - Tier 2: Lexical Fast-Path (Exact quote / Token + N-gram overlap >= 0.70)
  - Tier 4: Soft Containment Fallback (Without Neural NLI Escalation)

Metrics:
  - Accuracy, Precision, Recall, F1
  - False Acceptance Rate (FAR)
  - False Rejection Rate (FRR)
  - Latency (Median, p90, p95, p99)
  - Tier Breakdown

Exports to: Artifacts/benchmarks/BASELINE_VERIFIER_METRICS.json
"""

import json
import os
import random
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

RAG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAG_ROOT))

from src.core.config import settings
from src.features.evaluation.engine import (
    ClaimLevelVerifier,
    StructuredEvidence,
    NumericalClaimVerifier,
)
try:
    from evaluation.benchmark_finecat_vs_baseline import (
        load_chunks_pool,
        generate_1000_claims_testbed,
        evaluate_claim_with_verifier,
        compute_metrics,
    )
except ImportError:
    from benchmark_finecat_vs_baseline import (
        load_chunks_pool,
        generate_1000_claims_testbed,
        evaluate_claim_with_verifier,
        compute_metrics,
    )


def run_baseline_evaluation() -> Dict[str, Any]:
    print("=" * 75)
    print(" 📏 RAISE GROUNDING VERIFIER: PURE BASELINE BENCHMARK (1,000 CLAIMS)")
    print(" System: Research Assessment Intelligence & Semantic Extraction (RAISE)")
    print(" Configuration: Baseline (Tier 1 Numeric + Tier 2 Lexical + Tier 4 Fallback)")
    print("=" * 75)

    chunks = load_chunks_pool()
    print(f"[1/3] Loaded {len(chunks)} chunks from document vault.")
    testbed = generate_1000_claims_testbed(chunks, seed=42)
    print(f"[2/3] Generated standardized 1,000-claim testbed (Seed=42).")

    print("[3/3] Evaluating 1,000 claims across baseline verifier...")
    baseline_results = []
    t_start = time.perf_counter()

    for idx, item in enumerate(testbed, 1):
        if idx % 250 == 0:
            print(f"      Processed {idx}/1000 claims ({(time.perf_counter()-t_start):.1f}s elapsed)...")
        r = evaluate_claim_with_verifier(item, nli_engine=None, enable_nli=False)
        baseline_results.append(r)

    total_time_s = time.perf_counter() - t_start
    print(f"      Completed 1,000 claims in {total_time_s:.2f}s ({total_time_s/1000*1000:.2f} ms/claim avg).")

    baseline_metrics = compute_metrics(baseline_results, 0.0, 0.0)

    report = {
        "benchmark_name": "BASELINE_GROUNDING_VERIFIER_1000",
        "system_name": "Research Assessment Intelligence & Semantic Extraction (RAISE)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_claims": len(testbed),
        "testbed_composition": {
            "entailed": 400,
            "contradictory": 300,
            "unsupported": 300,
        },
        "metrics": baseline_metrics,
        "evaluation_duration_seconds": round(total_time_s, 2),
    }

    print("\n" + "=" * 75)
    print(" 📊 BASELINE VERIFIER BENCHMARK SCORECARD")
    print("=" * 75)
    print(f" Total Claims Evaluated       : {len(testbed)}")
    print(f" Accuracy                     : {baseline_metrics['accuracy']:.2%}")
    print(f" Precision                    : {baseline_metrics['precision']:.2%}")
    print(f" Recall                       : {baseline_metrics['recall']:.2%}")
    print(f" F1 Score                     : {baseline_metrics['f1_score']:.4f}")
    print(f" False Acceptance Rate (FAR)  : {baseline_metrics['false_acceptance_rate_far']:.2%}")
    print(f" False Rejection Rate (FRR)   : {baseline_metrics['false_rejection_rate_frr']:.2%}")
    print(f" Median Latency (p50)         : {baseline_metrics['latency_ms']['median']:.2f} ms")
    print(f" p90 Latency                  : {baseline_metrics['latency_ms']['p90']:.2f} ms")
    print(f" p95 Latency                  : {baseline_metrics['latency_ms']['p95']:.2f} ms")
    print(f" p99 Latency                  : {baseline_metrics['latency_ms']['p99']:.2f} ms")
    print(f" Mean Latency                 : {baseline_metrics['latency_ms']['mean']:.2f} ms")
    print(f" Tier Resolution Breakdown    : {baseline_metrics['tier_breakdown']}")
    print(f" Confusion Matrix             : {baseline_metrics['confusion_matrix']}")
    print("=" * 75)

    out_path = RAG_ROOT.parent / "Artifacts" / "benchmarks" / "BASELINE_VERIFIER_METRICS.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n [✓] Baseline metrics exported to: {out_path}")

    return report


if __name__ == "__main__":
    run_baseline_evaluation()
