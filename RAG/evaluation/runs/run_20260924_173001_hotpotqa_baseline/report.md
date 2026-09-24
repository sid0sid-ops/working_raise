# RAISE Baseline Evaluation Report — Run `run_20260924_173001_hotpotqa_baseline`

**Benchmark**: hotpotqa  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-24T17:30:29.555959+00:00  
**Total Evaluated Cases**: 5 | **Passed**: 0 | **Failed**: 5  

---

## 1. Multi-Dimensional Scorecard

| Layer | Metric | Score | Unit / Notes |
| :--- | :--- | :---: | :--- |
| **Retrieval** | Recall@1 | `0.00%` | Top-1 gold candidate discovery |
| **Retrieval** | Recall@4 | `0.00%` | Standard synthesis context cutoff |
| **Retrieval** | Recall@8 | `0.00%` | Extended expert context cutoff |
| **Retrieval** | nDCG@10 | `0.0000` | Normalized discounted cumulative gain |
| **Retrieval** | MRR@10 | `0.0000` | Mean reciprocal rank of gold evidence |
| **QA Correctness** | Exact Match (EM) | `0.00%` | Normalized string equivalence |
| **QA Correctness** | Token F1 | `0.00%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `100.00%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `100.00%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `100.00%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `0.00%` | Refusals on answerable queries |
| **System** | Latency p50 | `2593.4 ms` | Median per-query latency |
| **System** | Latency p95 | `15331.2 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `60.79 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **5**

### Failure Card: `HOTPOT_5a8b57f25542995d1e6f1371` (GENERATION_ERROR)
- **Question**: Were Scott Derrickson and Ed Wood of the same nationality?
- **Expected Answer**: yes
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `HOTPOT_5a8c7595554299585d9e36b6` (GENERATION_ERROR)
- **Question**: What government position was held by the woman who portrayed Corliss Archer in the film Kiss and Tell?
- **Expected Answer**: Chief of Protocol
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `HOTPOT_5a85b3b5554299385d9e36b7` (GENERATION_ERROR)
- **Question**: What science fantasy young adult series, told in first person, has a protagonist named Katniss Everdeen?
- **Expected Answer**: The Hunger Games
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `HOTPOT_5a88a44655429974249a859e` (GENERATION_ERROR)
- **Question**: Which magazine was started first, Arthur's Magazine or First for Women?
- **Expected Answer**: Arthur's Magazine
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `HOTPOT_5a76100255429910d54032d8` (GENERATION_ERROR)
- **Question**: The actor who played the role of the father in 'Finding Nemo' also appeared in which American comedy film released in 2004?
- **Expected Answer**: Anchorman: The Legend of Ron Burgundy
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.
