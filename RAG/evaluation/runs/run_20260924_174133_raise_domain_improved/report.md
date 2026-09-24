# RAISE Baseline Evaluation Report — Run `run_20260924_174133_raise_domain_improved`

**Benchmark**: raise-domain  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-24T17:42:55.300496+00:00  
**Total Evaluated Cases**: 16 | **Passed**: 4 | **Failed**: 12  

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
| **QA Correctness** | Token F1 | `6.93%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `56.25%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `13.54%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `37.50%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `62.50%` | Refusals on answerable queries |
| **System** | Latency p50 | `4684.3 ms` | Median per-query latency |
| **System** | Latency p95 | `14317.5 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `56.13 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **12**

### Failure Card: `Q101` (GENERATION_ERROR)
- **Question**: In the National Institute of Plant Genome Research (NIPGR) Balance Sheet as on 31st March 2024 (Page 155), what are the exact figures reported for 'Corpus/Capital Fund', 'Reserves and Surplus', and 'Earmarked / Endowment Funds' for the Current Year (2023-24)?
- **Expected Answer**: - **Corpus/Capital Fund**: **Rs. 1,23,92,56,765**
- **Reserves and Surplus**: **Rs. (7,01,72,084)**
- **Earmarked / Endowment Funds**: **Rs. 14,27,83,599**
- **Generated Answer**: Based on the National Institute of Plant Genome Research (NIPGR) Balance Sheet as on 31st March 2024, the exact figures reported for the Current Year (2023-24) are:

• **Corpus/Capital Fund**: ₹1,23,92,56,765 [1, 2]

• **Reserves and Surplus**: ₹(7,01,72,084) [1, 2]

• **Earmarked / Endowment Funds**: ₹14,27,83,599 [1, 2]
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `Q102` (UNNECESSARY_ABSTENTION)
- **Question**: According to the BRIC Annual Report 2025 (Page 17), under the doctoral research program details, what are the exact counts for 'ongoing networked interdisciplinary research programs', 'total students currently enrolled', 'first batch students who completed immersion training', and 'number of partner agencies' involved in immersion training?
- **Expected Answer**: - **Ongoing networked interdisciplinary research programs**: **47**
- **Total students currently enrolled**: **122**
- **First batch students pursuing doctoral research after immersion training**: **57**
- **Number of partner agencies for immersion training**: **13**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `Q103` (GENERATION_ERROR)
- **Question**: In the BRIC Annual Report 2025 (Page 17), under Section 2.1.4 'Entrepreneur in Residence (EIR) program', what are the exact numbers for 'technology submissions solicited', 'technologies shortlisted across sectors', 'duration of salary funding (in months)', and 'technologies selected for funding and mentoring in the first phase'?
- **Expected Answer**: - **Technology submissions solicited**: **38**
- **Technologies shortlisted across sectors**: **9**
- **Duration of salary funding**: **18-month** salary (jointly funded by BIRAC and VCs)
- **Technologies selected for funding and mentoring in the first phase**: **5**
- **Generated Answer**: Based on the BRIC Annual Report 2025, the exact figures for the Entrepreneur in Residence (EIR) program are as follows:

• **Technology submissions solicited**: 38 [1, 2, 3]

• **Technologies shortlisted across sectors**: 9 [1, 2, 3]

• **Duration of salary funding**: 18 months [1, 3]

• **Technologies selected for funding and mentoring in the first phase**: 5 [4, 1, 3]
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `Q104` (UNNECESSARY_ABSTENTION)
- **Question**: In the National Institute of Plant Genome Research (NIPGR) Balance Sheet as on 31st March 2022 (Page 131), what are the exact figures reported for 'Corpus/Capital Fund' for both the Current Year (2021-22) and the Previous Year (2020-21)?
- **Expected Answer**: - **Current Year (2021-22)**: **Rs. 1,24,28,61,303**
- **Previous Year (2020-21)**: **Rs. 1,24,91,58,426**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `Q201` (UNNECESSARY_ABSTENTION)
- **Question**: Who is the Director of the National Institute of Plant Genome Research (NIPGR) who signed the Balance Sheet as on 31st March 2024, and what are the names and designations of the Finance Officer and Controller of Administration who co-signed the financial statements on August 24, 2024?
- **Expected Answer**: - **Director**: **Dr. Subhra Chakraborty**
- **Finance Officer**: **Vineeta Sharma**
- **Controller of Administration**: **Sandeep Datta**
- **Auditor**: **Parul Goyal (Chartered Accountant)**
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

### Failure Card: `Q203` (UNNECESSARY_ABSTENTION)
- **Question**: In the research programs of NIPGR detailed in the 2023-24 Annual Report, which fungal pathogen was identified as causing devastating dry root rot (DRR) in chickpea exacerbated by drought, and who was the Principal Investigator (PI) leading this project?
- **Expected Answer**: - **Fungal Pathogen**: **Macrophomina phaseolina**
- **Disease**: **Dry root rot (DRR)** in chickpea
- **Principal Investigator (PI)**: **Dr. Muthappa Senthil-Kumar**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
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
