# RAISE Baseline Evaluation Report — Run `run_20260924_172142_raise_domain_baseline`

**Benchmark**: raise-domain  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-24T17:22:35.937407+00:00  
**Total Evaluated Cases**: 16 | **Passed**: 9 | **Failed**: 7  

---

## 1. Multi-Dimensional Scorecard

| Layer | Metric | Score | Unit / Notes |
| :--- | :--- | :---: | :--- |
| **Retrieval** | Recall@1 | `56.25%` | Top-1 gold candidate discovery |
| **Retrieval** | Recall@4 | `56.25%` | Standard synthesis context cutoff |
| **Retrieval** | Recall@8 | `56.25%` | Extended expert context cutoff |
| **Retrieval** | nDCG@10 | `1.0935` | Normalized discounted cumulative gain |
| **Retrieval** | MRR@10 | `0.5625` | Mean reciprocal rank of gold evidence |
| **QA Correctness** | Exact Match (EM) | `56.25%` | Normalized string equivalence |
| **QA Correctness** | Token F1 | `56.25%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `100.00%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `100.00%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `100.00%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `0.00%` | Refusals on answerable queries |
| **System** | Latency p50 | `2678.0 ms` | Median per-query latency |
| **System** | Latency p95 | `14523.9 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `55.46 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **7**

### Failure Card: `Q201` (RERANKER_ERROR)
- **Question**: Who is the Director of the National Institute of Plant Genome Research (NIPGR) who signed the Balance Sheet as on 31st March 2024, and what are the names and designations of the Finance Officer and Controller of Administration who co-signed the financial statements on August 24, 2024?
- **Expected Answer**: - **Director**: **Dr. Subhra Chakraborty**
- **Finance Officer**: **Vineeta Sharma**
- **Controller of Administration**: **Sandeep Datta**
- **Auditor**: **Parul Goyal (Chartered Accountant)**
- **Generated Answer**: 
- **Root Cause**: `RERANKER_ERROR` | **Affected Component**: `CrossEncoderReranker (BAAI/bge-reranker-large)`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:-1, Graph:-1, RRF:3, Rerank:-1)
- **Why Failed**: Gold passage ranked #3 after fusion but was suppressed to #-1 by cross-encoder.
- **Proposed Fix**: Calibrate cross-encoder score normalization or lower threshold.

### Failure Card: `Q202` (RETRIEVAL_MISS)
- **Question**: Under which central government department was the Biotechnology Research and Innovation Council (BRIC) established as an apex institutional framework, and what specific council/agency collaborated with BRIC to launch the Post-Doctoral Entrepreneur-in-Residence (EIR) program?
- **Expected Answer**: - **Central Government Department**: **Department of Biotechnology (DBT)**, Government of India
- **Collaborating Agency**: **Biotechnology Industry Research Assistance Council (BIRAC)**
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `Q302` (RERANKER_ERROR)
- **Question**: What was the reported figure for 'Corpus/Capital Fund' of NIPGR on 31st March 2022 compared to 31st March 2023?
- **Expected Answer**: - **31st March 2022**: **Rs. 1,24,28,61,303**
- **31st March 2023**: **Rs. 1,24,28,61,303**
- **Comparison**: The Corpus/Capital Fund remained unchanged at **Rs. 1,24,28,61,303** across both fiscal year-ends.
- **Generated Answer**: 
- **Root Cause**: `RERANKER_ERROR` | **Affected Component**: `CrossEncoderReranker (BAAI/bge-reranker-large)`
- **Evidence Rank**: Highest rank: #1 (Vec:10, BM25:1, Graph:1, RRF:8, Rerank:-1)
- **Why Failed**: Gold passage ranked #8 after fusion but was suppressed to #-1 by cross-encoder.
- **Proposed Fix**: Calibrate cross-encoder score normalization or lower threshold.

### Failure Card: `Q401` (GENERATION_ERROR)
- **Question**: According to the attached reports, what was the total expenditure allocated to quantum computing laboratory infrastructure at the Indian Institute of Science (IISc) Bangalore in 2024?
- **Expected Answer**: INSUFFICIENT_EVIDENCE: The attached institutional reports (BRIC and NIPGR annual reports) do not contain records or budget allocations for quantum computing laboratories at IISc Bangalore.
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `Q402` (GENERATION_ERROR)
- **Question**: What are the audited financial figures and total corpus balance reported for the fiscal year 2034-35 in the NIPGR annual report?
- **Expected Answer**: INSUFFICIENT_EVIDENCE: The document library contains reports up to the 2024-25 fiscal period. Financial data for the future year 2034-35 is not available.
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `Q403` (GENERATION_ERROR)
- **Question**: What was the total revenue earned by NIPGR from commercial space rocket launch vehicle licensing in 2023-24?
- **Expected Answer**: INSUFFICIENT_EVIDENCE: NIPGR is a plant genome and agricultural biotechnology research institute. The report contains no records or revenue related to space rocket launch vehicles.
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `Q404` (RETRIEVAL_MISS)
- **Question**: According to the internal admissions manual of IIT Bombay, what is the cutoff rank for Computer Science engineering?
- **Expected Answer**: INSUFFICIENT_EVIDENCE: The document 'internal admissions manual of IIT Bombay' is not registered in the active document library or attached to the drawer.
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.
