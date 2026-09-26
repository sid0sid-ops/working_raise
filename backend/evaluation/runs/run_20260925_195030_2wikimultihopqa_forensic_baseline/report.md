# RAISE Baseline Evaluation Report — Run `run_20260925_195030_2wikimultihopqa_forensic_baseline`

**Benchmark**: 2wikimultihopqa  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-25T19:51:58.371035+00:00  
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
| **QA Correctness** | Token F1 | `0.87%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `80.00%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `76.67%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `100.00%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `60.00%` | Refusals on answerable queries |
| **System** | Latency p50 | `7611.9 ms` | Median per-query latency |
| **System** | Latency p95 | `26093.8 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `0.40 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **3**

### Failure Card: `2WIKI_8813f87c0bdd11eba7f7acde48001122` (UNNECESSARY_ABSTENTION)
- **Question**: Who is the mother of the director of film Polish-Russian War (Film)?
- **Expected Answer**: Małgorzata Braunek
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `2WIKI_61a46987092f11ebbdaeac1f6bf848b6` (UNNECESSARY_ABSTENTION)
- **Question**: Which film came out first, Blind Shaft or The Mask Of Fu Manchu?
- **Expected Answer**: The Mask Of Fu Manchu
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `2WIKI_e2a3bf2a0bdd11eba7f7acde48001122` (UNNECESSARY_ABSTENTION)
- **Question**: When did John V, Prince Of Anhalt-Zerbst's father die?
- **Expected Answer**: 12 June 1516
- **Generated Answer**: No information regarding **John V, Prince of Anhalt-Zerbst** or his father’s death date is present in the provided documents. The uploaded files do not contain any details about historical figures, royal lineages, or biographical data.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.
