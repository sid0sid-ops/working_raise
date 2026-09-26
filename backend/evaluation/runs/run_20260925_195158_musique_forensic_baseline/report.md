# RAISE Baseline Evaluation Report — Run `run_20260925_195158_musique_forensic_baseline`

**Benchmark**: musique  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-25T19:54:05.141703+00:00  
**Total Evaluated Cases**: 5 | **Passed**: 2 | **Failed**: 3  

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
| **QA Correctness** | Token F1 | `0.91%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `100.00%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `83.33%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `100.00%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `20.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `40.00%` | Refusals on answerable queries |
| **System** | Latency p50 | `25672.4 ms` | Median per-query latency |
| **System** | Latency p95 | `28230.6 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `0.30 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **3**

### Failure Card: `MUSIQUE_4hop1__129721_32392_823060_610794` (UNSUPPORTED_ANSWER)
- **Question**: What county is the city that shares a border with the state capital of the state where Zubly Cemetery is located in?
- **Expected Answer**: Richland County
- **Generated Answer**: The provided documents do **not** contain any information about **Zubly Cemetery** or its location, nor do they reference a state capital, city, or county bordering it.

No relevant facts or geographic details about Zubly Cemetery or its associated state/county are present in the uploaded documents.
- **Root Cause**: `UNSUPPORTED_ANSWER` | **Affected Component**: `Quality Gate / Faithfulness Filter`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Pipeline answered an unanswerable or unsupported question instead of safely refusing.
- **Proposed Fix**: Enforce strict refusal threshold when evidence similarity is below cutoff.

### Failure Card: `MUSIQUE_3hop1__241001_568433_47686` (UNNECESSARY_ABSTENTION)
- **Question**: Where do Greyhound buses leave from in the city where Arna Selznick's employer is headquartered?
- **Expected Answer**: Toronto Coach Terminal
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `MUSIQUE_2hop__231890_595414` (UNNECESSARY_ABSTENTION)
- **Question**: Which county does Lloyd Dane's birthplace belong to?
- **Expected Answer**: Miller County
- **Generated Answer**: No information regarding **Lloyd Dane** or his birthplace is present in the provided documents. The uploaded files do not contain any mention of Lloyd Dane, his affiliation, research, or personal details.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.
