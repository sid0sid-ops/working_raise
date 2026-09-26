# RAISE Baseline Evaluation Report — Run `run_20260925_194013_raise_domain_forensic_baseline`

**Benchmark**: raise-domain  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-25T19:47:01.633814+00:00  
**Total Evaluated Cases**: 16 | **Passed**: 16 | **Failed**: 0  

---

## 1. Multi-Dimensional Scorecard

| Layer | Metric | Score | Unit / Notes |
| :--- | :--- | :---: | :--- |
| **Retrieval** | Recall@1 | `62.50%` | Top-1 gold candidate discovery |
| **Retrieval** | Recall@4 | `62.50%` | Standard synthesis context cutoff |
| **Retrieval** | Recall@8 | `68.75%` | Extended expert context cutoff |
| **Retrieval** | nDCG@10 | `1.2533` | Normalized discounted cumulative gain |
| **Retrieval** | MRR@10 | `0.6354` | Mean reciprocal rank of gold evidence |
| **QA Correctness** | Exact Match (EM) | `0.00%` | Normalized string equivalence |
| **QA Correctness** | Token F1 | `34.35%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `93.75%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `98.96%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `100.00%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `0.00%` | Refusals on answerable queries |
| **System** | Latency p50 | `26861.0 ms` | Median per-query latency |
| **System** | Latency p95 | `42311.8 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `0.31 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **0**
