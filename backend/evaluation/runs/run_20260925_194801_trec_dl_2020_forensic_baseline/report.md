# RAISE Baseline Evaluation Report — Run `run_20260925_194801_trec_dl_2020_forensic_baseline`

**Benchmark**: trec-dl-2020  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-25T19:48:27.629065+00:00  
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
| **System** | Latency p50 | `1620.0 ms` | Median per-query latency |
| **System** | Latency p95 | `1864.4 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `0.31 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **5**

### Failure Card: `TREC_DL_2020_1030303` (RETRIEVAL_MISS)
- **Question**: who is aziz hashim
- **Expected Answer**: 
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `TREC_DL_2020_1037496` (RETRIEVAL_MISS)
- **Question**: who is rep scalise?
- **Expected Answer**: 
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `TREC_DL_2020_1043135` (RETRIEVAL_MISS)
- **Question**: who killed nicholas ii of russia
- **Expected Answer**: 
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `TREC_DL_2020_1045109` (RETRIEVAL_MISS)
- **Question**: who owns barnhart crane
- **Expected Answer**: 
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `TREC_DL_2020_1049519` (RETRIEVAL_MISS)
- **Question**: who said no one can make you feel inferior
- **Expected Answer**: 
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.
