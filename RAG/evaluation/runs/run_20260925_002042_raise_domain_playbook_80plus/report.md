# RAISE Baseline Evaluation Report — Run `run_20260925_002042_raise_domain_playbook_80plus`

**Benchmark**: raise-domain  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-25T00:27:36.135647+00:00  
**Total Evaluated Cases**: 16 | **Passed**: 12 | **Failed**: 4  

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
| **QA Correctness** | Token F1 | `25.35%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `81.25%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `85.92%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `81.25%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `18.75%` | Refusals on answerable queries |
| **System** | Latency p50 | `23070.4 ms` | Median per-query latency |
| **System** | Latency p95 | `93002.5 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `72.41 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **4**

### Failure Card: `Q301` (GENERATION_ERROR)
- **Question**: Compare the 'Earmarked / Endowment Funds' of NIPGR between the Balance Sheets as of 31st March 2023 (in 2022-23 report) and 31st March 2024 (in 2023-24 report). Did the fund increase or decrease, and what is the exact difference in Rupees?
- **Expected Answer**: - **31st March 2023**: **Rs. 11,40,23,933**
- **31st March 2024**: **Rs. 14,27,83,599**
- **Trend**: **Increased**
- **Exact Difference**: **Rs. 2,87,59,666** (Rs. 14,27,83,599 - Rs. 11,40,23,933)
- **Generated Answer**: ### Comparison of Earmarked / Endowment Funds of NIPGR

The Earmarked / Endowment Funds of NIPGR as of 31st March 2023 (in 2022-23 report) and 31st March 2024 (in 2023-24 report) are as follows:

• **31st March 2023 (2022-23 report)**: ₹11,40,23,933 [1]

• **31st March 2024 (2023-24 report)**: ₹14,27,83,599 [1]

The Earmarked / Endowment Funds of NIPGR increased by ₹3,87,59,666 from ₹11,40,23,933 to ₹14,27,83,599.

### Breakdown of Earmarked / Endowment Funds

The breakdown of Earmarked / Endowment Funds as of 31st March 2024 is as follows:

• **Additions to the fund**: ₹13,02,98,346 [2]

• **Utilization/Expenditure towards objectives of fund**: ₹1,25,14,747 [2]

• **Total**: ₹14,27,83,599 [2]

• **### Verified Institutional Knowledge Graph Facts**

• Endowment Fund transferred to NIPGR Fund --[PARTNERED_WITH]--> National Institute of Plant Genome Research (NIPGR) [3, 4, 5]
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `Q302` (UNNECESSARY_ABSTENTION)
- **Question**: What was the reported figure for 'Corpus/Capital Fund' of NIPGR on 31st March 2022 compared to 31st March 2023?
- **Expected Answer**: - **31st March 2022**: **Rs. 1,24,28,61,303**
- **31st March 2023**: **Rs. 1,24,28,61,303**
- **Comparison**: The Corpus/Capital Fund remained unchanged at **Rs. 1,24,28,61,303** across both fiscal year-ends.
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

### Failure Card: `Q304` (UNNECESSARY_ABSTENTION)
- **Question**: In NIPGR's Income & Expenditure account for the year ended 31st March 2024 (Page 156), what were the Establishment Expenses for the Current Year (2023-24) and the Previous Year (2022-23), and by how much did they change?
- **Expected Answer**: - **Establishment Expenses Current Year (2023-24)**: **Rs. 18,14,41,812**
- **Establishment Expenses Previous Year (2022-23)**: **Rs. 15,90,67,160**
- **Net Change / Increase**: **Rs. 2,23,74,652**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.
