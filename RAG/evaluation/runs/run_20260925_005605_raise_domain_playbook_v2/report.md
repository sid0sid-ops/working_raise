# RAISE Baseline Evaluation Report — Run `run_20260925_005605_raise_domain_playbook_v2`

**Benchmark**: raise-domain  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-25T01:01:20.753224+00:00  
**Total Evaluated Cases**: 16 | **Passed**: 14 | **Failed**: 2  

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
| **QA Correctness** | Token F1 | `26.27%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `87.50%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `93.36%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `87.50%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `12.50%` | Refusals on answerable queries |
| **System** | Latency p50 | `11340.0 ms` | Median per-query latency |
| **System** | Latency p95 | `38211.8 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `1243.23 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **2**

### Failure Card: `Q301` (UNNECESSARY_ABSTENTION)
- **Question**: Compare the 'Earmarked / Endowment Funds' of NIPGR between the Balance Sheets as of 31st March 2023 (in 2022-23 report) and 31st March 2024 (in 2023-24 report). Did the fund increase or decrease, and what is the exact difference in Rupees?
- **Expected Answer**: - **31st March 2023**: **Rs. 11,40,23,933**
- **31st March 2024**: **Rs. 14,27,83,599**
- **Trend**: **Increased**
- **Exact Difference**: **Rs. 2,87,59,666** (Rs. 14,27,83,599 - Rs. 11,40,23,933)
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `Q303` (UNNECESSARY_ABSTENTION)
- **Question**: In NIPGR's Income & Expenditure account for the year ended 31st March 2024 (Page 156), compare the recurring Grants and Subsidies received in the Current Year (2023-24) against the Previous Year (2022-23). What was the increase in recurring grants?
- **Expected Answer**: - **Recurring Grants Current Year (2023-24)**: **Rs. 53,55,00,000**
- **Recurring Grants Previous Year (2022-23)**: **Rs. 48,50,00,000**
- **Increase**: **Rs. 5,05,00,000** (an increase of Rs. 5.05 Crore)
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.
