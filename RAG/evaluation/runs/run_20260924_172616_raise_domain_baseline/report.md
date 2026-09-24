# RAISE Baseline Evaluation Report — Run `run_20260924_172616_raise_domain_baseline`

**Benchmark**: raise-domain  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-24T17:27:34.876926+00:00  
**Total Evaluated Cases**: 16 | **Passed**: 0 | **Failed**: 16  

---

## 1. Multi-Dimensional Scorecard

| Layer | Metric | Score | Unit / Notes |
| :--- | :--- | :---: | :--- |
| **Retrieval** | Recall@1 | `56.25%` | Top-1 gold candidate discovery |
| **Retrieval** | Recall@4 | `56.25%` | Standard synthesis context cutoff |
| **Retrieval** | Recall@8 | `56.25%` | Extended expert context cutoff |
| **Retrieval** | nDCG@10 | `1.0870` | Normalized discounted cumulative gain |
| **Retrieval** | MRR@10 | `0.5625` | Mean reciprocal rank of gold evidence |
| **QA Correctness** | Exact Match (EM) | `0.00%` | Normalized string equivalence |
| **QA Correctness** | Token F1 | `7.96%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `56.25%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `21.88%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `25.00%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `25.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `0.00%` | Refusals on answerable queries |
| **System** | Latency p50 | `4212.9 ms` | Median per-query latency |
| **System** | Latency p95 | `14478.2 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `72.00 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **16**

### Failure Card: `Q101` (NUMERIC_ERROR)
- **Question**: In the National Institute of Plant Genome Research (NIPGR) Balance Sheet as on 31st March 2024 (Page 155), what are the exact figures reported for 'Corpus/Capital Fund', 'Reserves and Surplus', and 'Earmarked / Endowment Funds' for the Current Year (2023-24)?
- **Expected Answer**: - **Corpus/Capital Fund**: **Rs. 1,23,92,56,765**
- **Reserves and Surplus**: **Rs. (7,01,72,084)**
- **Earmarked / Endowment Funds**: **Rs. 14,27,83,599**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `NUMERIC_ERROR` | **Affected Component**: `DeterministicMathEngine / Table Engine`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Generated answer misread table numbers or financial statement currency units.
- **Proposed Fix**: Route financial/tabular queries through DeterministicMathEngine with cell coordinate locking.

### Failure Card: `Q102` (NUMERIC_ERROR)
- **Question**: According to the BRIC Annual Report 2025 (Page 17), under the doctoral research program details, what are the exact counts for 'ongoing networked interdisciplinary research programs', 'total students currently enrolled', 'first batch students who completed immersion training', and 'number of partner agencies' involved in immersion training?
- **Expected Answer**: - **Ongoing networked interdisciplinary research programs**: **47**
- **Total students currently enrolled**: **122**
- **First batch students pursuing doctoral research after immersion training**: **57**
- **Number of partner agencies for immersion training**: **13**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `NUMERIC_ERROR` | **Affected Component**: `DeterministicMathEngine / Table Engine`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Generated answer misread table numbers or financial statement currency units.
- **Proposed Fix**: Route financial/tabular queries through DeterministicMathEngine with cell coordinate locking.

### Failure Card: `Q103` (CITATION_ERROR)
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
- **Root Cause**: `CITATION_ERROR` | **Affected Component**: `CitationValidator`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Inline citations [Page N] did not match verified source page metadata.
- **Proposed Fix**: Bind citation tags strictly to verified physical page indices before synthesis.

### Failure Card: `Q104` (NUMERIC_ERROR)
- **Question**: In the National Institute of Plant Genome Research (NIPGR) Balance Sheet as on 31st March 2022 (Page 131), what are the exact figures reported for 'Corpus/Capital Fund' for both the Current Year (2021-22) and the Previous Year (2020-21)?
- **Expected Answer**: - **Current Year (2021-22)**: **Rs. 1,24,28,61,303**
- **Previous Year (2020-21)**: **Rs. 1,24,91,58,426**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `NUMERIC_ERROR` | **Affected Component**: `DeterministicMathEngine / Table Engine`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Generated answer misread table numbers or financial statement currency units.
- **Proposed Fix**: Route financial/tabular queries through DeterministicMathEngine with cell coordinate locking.

### Failure Card: `Q201` (RERANKER_ERROR)
- **Question**: Who is the Director of the National Institute of Plant Genome Research (NIPGR) who signed the Balance Sheet as on 31st March 2024, and what are the names and designations of the Finance Officer and Controller of Administration who co-signed the financial statements on August 24, 2024?
- **Expected Answer**: - **Director**: **Dr. Subhra Chakraborty**
- **Finance Officer**: **Vineeta Sharma**
- **Controller of Administration**: **Sandeep Datta**
- **Auditor**: **Parul Goyal (Chartered Accountant)**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `RERANKER_ERROR` | **Affected Component**: `CrossEncoderReranker (BAAI/bge-reranker-large)`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Gold passage ranked #1 after fusion but was suppressed to #-1 by cross-encoder.
- **Proposed Fix**: Calibrate cross-encoder score normalization or lower threshold.

### Failure Card: `Q202` (RERANKER_ERROR)
- **Question**: Under which central government department was the Biotechnology Research and Innovation Council (BRIC) established as an apex institutional framework, and what specific council/agency collaborated with BRIC to launch the Post-Doctoral Entrepreneur-in-Residence (EIR) program?
- **Expected Answer**: - **Central Government Department**: **Department of Biotechnology (DBT)**, Government of India
- **Collaborating Agency**: **Biotechnology Industry Research Assistance Council (BIRAC)**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `RERANKER_ERROR` | **Affected Component**: `CrossEncoderReranker (BAAI/bge-reranker-large)`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Gold passage ranked #1 after fusion but was suppressed to #-1 by cross-encoder.
- **Proposed Fix**: Calibrate cross-encoder score normalization or lower threshold.

### Failure Card: `Q203` (CITATION_ERROR)
- **Question**: In the research programs of NIPGR detailed in the 2023-24 Annual Report, which fungal pathogen was identified as causing devastating dry root rot (DRR) in chickpea exacerbated by drought, and who was the Principal Investigator (PI) leading this project?
- **Expected Answer**: - **Fungal Pathogen**: **Macrophomina phaseolina**
- **Disease**: **Dry root rot (DRR)** in chickpea
- **Principal Investigator (PI)**: **Dr. Muthappa Senthil-Kumar**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `CITATION_ERROR` | **Affected Component**: `CitationValidator`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Inline citations [Page N] did not match verified source page metadata.
- **Proposed Fix**: Bind citation tags strictly to verified physical page indices before synthesis.

### Failure Card: `Q204` (NUMERIC_ERROR)
- **Question**: According to the BRIC Annual Report 2025 (Page 15), on what exact dates were the four 'Chintan Shivirs' organized to deliberate on research priorities and administrative harmonization, and how many research ideas were submitted through the portal?
- **Expected Answer**: - **Chintan Shivir Dates**:
  1. **26-27 May 2023**
  2. **7-8 September 2023**
  3. **16 March 2024**
  4. **28 September 2024**
- **Research Ideas Submitted**: **over 175 research ideas** (with profiles of more than 320 scientists registered)
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `NUMERIC_ERROR` | **Affected Component**: `DeterministicMathEngine / Table Engine`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Generated answer misread table numbers or financial statement currency units.
- **Proposed Fix**: Route financial/tabular queries through DeterministicMathEngine with cell coordinate locking.

### Failure Card: `Q301` (NUMERIC_ERROR)
- **Question**: Compare the 'Earmarked / Endowment Funds' of NIPGR between the Balance Sheets as of 31st March 2023 (in 2022-23 report) and 31st March 2024 (in 2023-24 report). Did the fund increase or decrease, and what is the exact difference in Rupees?
- **Expected Answer**: - **31st March 2023**: **Rs. 11,40,23,933**
- **31st March 2024**: **Rs. 14,27,83,599**
- **Trend**: **Increased**
- **Exact Difference**: **Rs. 2,87,59,666** (Rs. 14,27,83,599 - Rs. 11,40,23,933)
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `NUMERIC_ERROR` | **Affected Component**: `DeterministicMathEngine / Table Engine`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Generated answer misread table numbers or financial statement currency units.
- **Proposed Fix**: Route financial/tabular queries through DeterministicMathEngine with cell coordinate locking.

### Failure Card: `Q302` (RERANKER_ERROR)
- **Question**: What was the reported figure for 'Corpus/Capital Fund' of NIPGR on 31st March 2022 compared to 31st March 2023?
- **Expected Answer**: - **31st March 2022**: **Rs. 1,24,28,61,303**
- **31st March 2023**: **Rs. 1,24,28,61,303**
- **Comparison**: The Corpus/Capital Fund remained unchanged at **Rs. 1,24,28,61,303** across both fiscal year-ends.
- **Generated Answer**: The provided documents do not contain the reported figures for the 'Corpus/Capital Fund' of NIPGR for either 31st March 2022 or 31st March 2023. The available excerpts focus on audit observations regarding sponsored fellowship payables, asset ownership, prior period income/expense, and interest remittances, but do not include the specific balance sheet line item for the Corpus/Capital Fund.
- **Root Cause**: `RERANKER_ERROR` | **Affected Component**: `CrossEncoderReranker (BAAI/bge-reranker-large)`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Gold passage ranked #1 after fusion but was suppressed to #-1 by cross-encoder.
- **Proposed Fix**: Calibrate cross-encoder score normalization or lower threshold.

### Failure Card: `Q303` (NUMERIC_ERROR)
- **Question**: In NIPGR's Income & Expenditure account for the year ended 31st March 2024 (Page 156), compare the recurring Grants and Subsidies received in the Current Year (2023-24) against the Previous Year (2022-23). What was the increase in recurring grants?
- **Expected Answer**: - **Recurring Grants Current Year (2023-24)**: **Rs. 53,55,00,000**
- **Recurring Grants Previous Year (2022-23)**: **Rs. 48,50,00,000**
- **Increase**: **Rs. 5,05,00,000** (an increase of Rs. 5.05 Crore)
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `NUMERIC_ERROR` | **Affected Component**: `DeterministicMathEngine / Table Engine`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Generated answer misread table numbers or financial statement currency units.
- **Proposed Fix**: Route financial/tabular queries through DeterministicMathEngine with cell coordinate locking.

### Failure Card: `Q304` (NUMERIC_ERROR)
- **Question**: In NIPGR's Income & Expenditure account for the year ended 31st March 2024 (Page 156), what were the Establishment Expenses for the Current Year (2023-24) and the Previous Year (2022-23), and by how much did they change?
- **Expected Answer**: - **Establishment Expenses Current Year (2023-24)**: **Rs. 18,14,41,812**
- **Establishment Expenses Previous Year (2022-23)**: **Rs. 15,90,67,160**
- **Net Change / Increase**: **Rs. 2,23,74,652**
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `NUMERIC_ERROR` | **Affected Component**: `DeterministicMathEngine / Table Engine`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Generated answer misread table numbers or financial statement currency units.
- **Proposed Fix**: Route financial/tabular queries through DeterministicMathEngine with cell coordinate locking.

### Failure Card: `Q401` (UNSUPPORTED_ANSWER)
- **Question**: According to the attached reports, what was the total expenditure allocated to quantum computing laboratory infrastructure at the Indian Institute of Science (IISc) Bangalore in 2024?
- **Expected Answer**: INSUFFICIENT_EVIDENCE: The attached institutional reports (BRIC and NIPGR annual reports) do not contain records or budget allocations for quantum computing laboratories at IISc Bangalore.
- **Generated Answer**: The provided documents do not contain information regarding the total expenditure allocated to quantum computing laboratory infrastructure at the Indian Institute of Science (IISc) Bangalore in 2024. The available excerpts focus on BRIC institutions, neuroscience research, and BSL-3 laboratory infrastructure, but do not mention IISc Bangalore or quantum computing expenditures.
- **Root Cause**: `UNSUPPORTED_ANSWER` | **Affected Component**: `Quality Gate / Faithfulness Filter`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Pipeline answered an unanswerable or unsupported question instead of safely refusing.
- **Proposed Fix**: Enforce strict refusal threshold when evidence similarity is below cutoff.

### Failure Card: `Q402` (UNSUPPORTED_ANSWER)
- **Question**: What are the audited financial figures and total corpus balance reported for the fiscal year 2034-35 in the NIPGR annual report?
- **Expected Answer**: INSUFFICIENT_EVIDENCE: The document library contains reports up to the 2024-25 fiscal period. Financial data for the future year 2034-35 is not available.
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNSUPPORTED_ANSWER` | **Affected Component**: `Quality Gate / Faithfulness Filter`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Pipeline answered an unanswerable or unsupported question instead of safely refusing.
- **Proposed Fix**: Enforce strict refusal threshold when evidence similarity is below cutoff.

### Failure Card: `Q403` (UNSUPPORTED_ANSWER)
- **Question**: What was the total revenue earned by NIPGR from commercial space rocket launch vehicle licensing in 2023-24?
- **Expected Answer**: INSUFFICIENT_EVIDENCE: NIPGR is a plant genome and agricultural biotechnology research institute. The report contains no records or revenue related to space rocket launch vehicles.
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNSUPPORTED_ANSWER` | **Affected Component**: `Quality Gate / Faithfulness Filter`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Pipeline answered an unanswerable or unsupported question instead of safely refusing.
- **Proposed Fix**: Enforce strict refusal threshold when evidence similarity is below cutoff.

### Failure Card: `Q404` (UNSUPPORTED_ANSWER)
- **Question**: According to the internal admissions manual of IIT Bombay, what is the cutoff rank for Computer Science engineering?
- **Expected Answer**: INSUFFICIENT_EVIDENCE: The document 'internal admissions manual of IIT Bombay' is not registered in the active document library or attached to the drawer.
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNSUPPORTED_ANSWER` | **Affected Component**: `Quality Gate / Faithfulness Filter`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Pipeline answered an unanswerable or unsupported question instead of safely refusing.
- **Proposed Fix**: Enforce strict refusal threshold when evidence similarity is below cutoff.
