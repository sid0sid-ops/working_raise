# RAISE Baseline Evaluation Report — Run `run_20260925_194701_beir_forensic_baseline`

**Benchmark**: beir  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-25T19:47:33.174188+00:00  
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
| **System** | Latency p50 | `2045.7 ms` | Median per-query latency |
| **System** | Latency p95 | `3972.8 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `0.31 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **5**

### Failure Card: `BEIR_SCIFACT_1` (RETRIEVAL_MISS)
- **Question**: 0-dimensional biomaterials show inductive properties.
- **Expected Answer**: 
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `BEIR_SCIFACT_3` (GENERATION_ERROR)
- **Question**: 1,000 genomes project enables mapping of genetic sequence variation consisting of rare variants with larger penetrance effects than common variants.
- **Expected Answer**: 
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `BEIR_SCIFACT_5` (GENERATION_ERROR)
- **Question**: 1/2000 in UK have abnormal PrP positivity.
- **Expected Answer**: 
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `BEIR_SCIFACT_13` (RETRIEVAL_MISS)
- **Question**: 5% of perinatal mortality is due to low birth weight.
- **Expected Answer**: 
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `BEIR_SCIFACT_36` (RETRIEVAL_MISS)
- **Question**: A deficiency of vitamin B12 increases blood levels of homocysteine.
- **Expected Answer**: 
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.
