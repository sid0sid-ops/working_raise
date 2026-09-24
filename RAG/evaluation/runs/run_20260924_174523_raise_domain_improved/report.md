# RAISE Baseline Evaluation Report — Run `run_20260924_174523_raise_domain_improved`

**Benchmark**: raise-domain  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-24T17:50:56.289039+00:00  
**Total Evaluated Cases**: 16 | **Passed**: 9 | **Failed**: 7  

---

## 1. Multi-Dimensional Scorecard

| Layer | Metric | Score | Unit / Notes |
| :--- | :--- | :---: | :--- |
| **Retrieval** | Recall@1 | `62.50%` | Top-1 gold candidate discovery |
| **Retrieval** | Recall@4 | `62.50%` | Standard synthesis context cutoff |
| **Retrieval** | Recall@8 | `68.75%` | Extended expert context cutoff |
| **Retrieval** | nDCG@10 | `1.2137` | Normalized discounted cumulative gain |
| **Retrieval** | MRR@10 | `0.6339` | Mean reciprocal rank of gold evidence |
| **QA Correctness** | Exact Match (EM) | `0.00%` | Normalized string equivalence |
| **QA Correctness** | Token F1 | `17.51%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `62.50%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `55.25%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `56.25%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `43.75%` | Refusals on answerable queries |
| **System** | Latency p50 | `21200.4 ms` | Median per-query latency |
| **System** | Latency p95 | `22749.3 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `81.51 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **7**

### Failure Card: `Q104` (UNNECESSARY_ABSTENTION)
- **Question**: In the National Institute of Plant Genome Research (NIPGR) Balance Sheet as on 31st March 2022 (Page 131), what are the exact figures reported for 'Corpus/Capital Fund' for both the Current Year (2021-22) and the Previous Year (2020-21)?
- **Expected Answer**: - **Current Year (2021-22)**: **Rs. 1,24,28,61,303**
- **Previous Year (2020-21)**: **Rs. 1,24,91,58,426**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `Q202` (UNNECESSARY_ABSTENTION)
- **Question**: Under which central government department was the Biotechnology Research and Innovation Council (BRIC) established as an apex institutional framework, and what specific council/agency collaborated with BRIC to launch the Post-Doctoral Entrepreneur-in-Residence (EIR) program?
- **Expected Answer**: - **Central Government Department**: **Department of Biotechnology (DBT)**, Government of India
- **Collaborating Agency**: **Biotechnology Industry Research Assistance Council (BIRAC)**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `Q204` (UNNECESSARY_ABSTENTION)
- **Question**: According to the BRIC Annual Report 2025 (Page 15), on what exact dates were the four 'Chintan Shivirs' organized to deliberate on research priorities and administrative harmonization, and how many research ideas were submitted through the portal?
- **Expected Answer**: - **Chintan Shivir Dates**:
  1. **26-27 May 2023**
  2. **7-8 September 2023**
  3. **16 March 2024**
  4. **28 September 2024**
- **Research Ideas Submitted**: **over 175 research ideas** (with profiles of more than 320 scientists registered)
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

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
