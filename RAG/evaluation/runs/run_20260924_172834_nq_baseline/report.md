# RAISE Baseline Evaluation Report — Run `run_20260924_172834_nq_baseline`

**Benchmark**: nq  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-24T17:29:11.120089+00:00  
**Total Evaluated Cases**: 10 | **Passed**: 0 | **Failed**: 10  

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
| **System** | Latency p50 | `2603.5 ms` | Median per-query latency |
| **System** | Latency p95 | `15464.0 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `97.98 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **10**

### Failure Card: `NQ_DEV_00001` (RETRIEVAL_MISS)
- **Question**: who won the premier league in 2016
- **Expected Answer**: Leicester City
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `NQ_DEV_00002` (GENERATION_ERROR)
- **Question**: what is the capital of australia
- **Expected Answer**: Canberra
- **Generated Answer**: 
- **Root Cause**: `GENERATION_ERROR` | **Affected Component**: `LLM Generation Node`
- **Evidence Rank**: Highest rank: #1 (Vec:-1, BM25:-1, Graph:1, RRF:-1, Rerank:-1)
- **Why Failed**: Model synthesized an inaccurate answer despite retrieved evidence.
- **Proposed Fix**: Refine synthesis prompt guidelines and verify table cell alignment.

### Failure Card: `NQ_DEV_00003` (RETRIEVAL_MISS)
- **Question**: when did apollo 11 land on the moon
- **Expected Answer**: July 20, 1969
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `NQ_DEV_00004` (RETRIEVAL_MISS)
- **Question**: who wrote the novel to kill a mockingbird
- **Expected Answer**: Harper Lee
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `NQ_DEV_00005` (RETRIEVAL_MISS)
- **Question**: what is the speed of light in vacuum
- **Expected Answer**: 299,792,458 metres per second
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `NQ_DEV_00006` (RETRIEVAL_MISS)
- **Question**: what year did the titanic sink in
- **Expected Answer**: 1912
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `NQ_DEV_00007` (RETRIEVAL_MISS)
- **Question**: who discovered penicillin
- **Expected Answer**: Alexander Fleming
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `NQ_DEV_00008` (RETRIEVAL_MISS)
- **Question**: what is the largest desert in the world
- **Expected Answer**: Antarctic Desert
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `NQ_DEV_00009` (RETRIEVAL_MISS)
- **Question**: who plays iron man in the marvel cinematic universe
- **Expected Answer**: Robert Downey Jr.
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.

### Failure Card: `NQ_DEV_00010` (RETRIEVAL_MISS)
- **Question**: what is the currency used in japan
- **Expected Answer**: Japanese yen
- **Generated Answer**: 
- **Root Cause**: `RETRIEVAL_MISS` | **Affected Component**: `ChromaDB / BM25 / Neo4j Retriever`
- **Evidence Rank**: Highest rank: #-1 (Vec:-1, BM25:-1, Graph:-1, RRF:-1, Rerank:-1)
- **Why Failed**: Zero candidate retrieval substrates matched the required gold evidence.
- **Proposed Fix**: Expand subquery decomposition and index coverage.
