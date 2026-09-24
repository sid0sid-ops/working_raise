# RAISE Benchmarking & Evaluation Specification

**Version**: 2.5.0  
**Status**: CANONICAL & AUTHORITATIVE  
**Verification Date**: 2026-09-14  

---

## 1. Overview

RAISE enforces strict separation between code regression test health and semantic RAG factual correctness. Evaluated performance is validated across three independent benchmark protocols:
1. **Grounding Verifier 1,000-Claim Baseline Benchmark** (Milestone 1)
2. **Formal 11-Point System Readiness Gate** (Milestone 3 Pre-requisite)
3. **Google Research FRAMES 100-Question Multi-Hop Benchmark** (Milestone 3)

---

## 2. Milestone 1: Grounding Verifier Baseline (1,000 Claims)

Evaluates the heuristic baseline verifier against 1,000 standardized claims (400 entailed, 300 contradictory, 300 unsupported) derived from processed document chunks (Seed 42).

- **Execution**: `python RAG/evaluation/benchmark_baseline_verifier.py`
- **Certificate**: `Artifacts/benchmarks/BASELINE_VERIFIER_METRICS.json`

| Metric | Baseline Empirical Value | Interpretation |
| :--- | :--- | :--- |
| **Accuracy** | **77.80%** | Overall classification accuracy |
| **Precision** | **64.31%** | Precision on authentic entailed claims |
| **Recall** | **100.00%** | Zero false rejections of authentic claims |
| **False Acceptance Rate (FAR)** | **37.00%** | 222 false positives on non-entailed claims (proves need for FineCat-NLI) |
| **False Rejection Rate (FRR)** | **0.00%** | 0 false negatives |
| **Median Latency (p50)** | **0.56 ms** | Sub-millisecond fast-path resolution |
| **Tier Breakdown** | Tier 1: 258 claims, Tier 2: 569 claims, Tier 3: 123 claims, Tier 4: 50 claims | 82.7% resolved in Tiers 1 and 2 |

---

## 3. Milestone 3: Formal 11-Point System Readiness Gate

Automated release gate verifying that all 11 foundational subsystems are operational:

- **Execution**: `python RAG/evaluation/verify_readiness_gate.py`
- **Certificate**: `Artifacts/benchmarks/SYSTEM_READINESS_GATE_VERIFICATION.json`
- **Status**: **`CERTIFIED_PASS`** (11/11 criteria passed, 100.0%)

| # | Dimension | Passing Criterion | Score | Status |
| :- | :--- | :--- | :--- | :--- |
| 1 | Intent Routing | 100% accuracy on campus queries vs persona greetings | 6/6 queries correct | PASS |
| 2 | Retrieval Correctness | Zero empty retrievals on registered document vault | 4/4 queries non-empty | PASS |
| 3 | Citation Binding | In-line citations [N] resolve to active doc/page | 2/2 citations bound | PASS |
| 4 | Claim Grounding | Grounded claims verified via Tier 1, 2, or NLI | NLI_ENTAILED, Faithfulness: 1.00 | PASS |
| 5 | Numerical Verification | Exact match or verified arithmetic derivation | Exact: True, Derived: True | PASS |
| 6 | Contradiction Detection | Contradictory claims reliably blocked | Blocked: NUMERICAL_MISMATCH | PASS |
| 7 | Gate Consistency | Zero discrepancy between claim audit and gate score | Unsupported: 0, Decision: accept | PASS |
| 8 | Telemetry Consistency | Strict MetricValue typing with zero fabrication | 4 MetricValue fields verified | PASS |
| 9 | Latency Accounting | Instrumentation coverage >= 90% | 98.1% accounted for | PASS |
| 10 | Page Provenance | Physical PDF page and printed page mapped | Provenance present: True | PASS |
| 11 | Reproducibility | Deterministic seed produces identical metrics | 1000/1000 claims bitwise identical | PASS |

---

## 4. Google Research FRAMES 100-Question Multi-Hop Benchmark

The Factuality, Retrieval, And reasoning MEasurement Set (FRAMES) benchmark evaluates multi-hop, multi-document reasoning across Wikipedia articles against local vLLM (`Qwen2.5-14B-Instruct-GPTQ-Int4`).

- **Execution**:
  ```bash
  python -m evaluation.benchmarks.frames.runner     --data evaluation/benchmarks/frames/data/frames_100_qwen14b_benchmark.json     --max-questions 100     --output evaluation/benchmarks/frames/frames_100_qwen14b_results.json
  ```
- **Ledger**: `Artifacts/benchmarks/frames/frames_100_qwen14b_results.json`
- **Audit Report**: `Artifacts/convo/2026-09-14_FRAMES_BENCHMARK_AND_GROUNDING_LAYER_AUDIT_REPORT.md`

### Official 100-Question Scorecard

| Metric | Score | Industrial Target | Description |
| :--- | :--- | :--- | :--- |
| **Answer Correctness (Exact Match)** | **32.00% (32/100)** | > 25.0% | Strict ground truth factual matches |
| **Partially Correct Answers** | **5.00% (5/100)** | N/A | Sub-clause / candidate entity intersection |
| **Controlled Safe Abstentions** | **41.00% (41/100)** | > 30.0% | Safe `INSUFFICIENT REASONING PATH` emitted when reasoning chain could not be definitively established. Zero text dumping. |
| **Incorrect Deductions** | **22.00% (22/100)** | < 30.0% | False conclusions under ambiguous multi-hop evidence |
| **Unsupported Claims (Hallucinations)** | **0.00% (0/100)** | < 2.0% | Zero fabricated facts released to user |
| **Evidence Retrieval Coverage** | **81.68%** | > 70.0% | Mean gold-chunk lexical overlap across hops |
| **Evidence Hit Rate** | **100.00%** | > 90.0% | 100/100 questions retrieved at least 1 relevant evidence article |
| **Overall Harmonic Benchmark Score** | **55.25%** | > 50.0% | Harmonic mean of correctness, grounding, and retrieval |
