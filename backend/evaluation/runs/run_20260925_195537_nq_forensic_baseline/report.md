# RAISE Baseline Evaluation Report — Run `run_20260925_195537_nq_forensic_baseline`

**Benchmark**: nq  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-25T19:57:18.370613+00:00  
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
| **QA Correctness** | Token F1 | `1.29%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `40.00%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `76.67%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `100.00%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `100.00%` | Refusals on answerable queries |
| **System** | Latency p50 | `23685.7 ms` | Median per-query latency |
| **System** | Latency p95 | `26016.3 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `0.31 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **5**

### Failure Card: `NQ_89789a4d443f42ccb2412b85a8c23da0` (UNNECESSARY_ABSTENTION)
- **Question**: what is non controlling interest on balance sheet
- **Expected Answer**: the portion of a subsidiary corporation 's stock that is not owned by the parent corporation
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `NQ_6357c3655b524feb8d0e398ff61dfabf` (UNNECESSARY_ABSTENTION)
- **Question**: how many episodes are in chicago fire season 4
- **Expected Answer**: 23
- **Generated Answer**: The provided documents **do not contain any information** regarding the number of episodes in *Chicago Fire* Season 4 or any related television series. The uploaded files pertain exclusively to institutional research reports, annual collaborations, and scientific advancements, with no mention of media, entertainment, or television programming.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `NQ_44e059927ac841d489d580a29222683b` (UNNECESSARY_ABSTENTION)
- **Question**: how many episodes are in chicago fire season 4
- **Expected Answer**: 23
- **Generated Answer**: The provided documents **do not contain any information** regarding the number of episodes in *Chicago Fire* Season 4 or any related television series. The uploaded files pertain exclusively to annual reports, research collaborations, and scientific advancements at an academic/research institute. No details about media content are included.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `NQ_16cde46eb3004809b2bf4b90abde9946` (UNNECESSARY_ABSTENTION)
- **Question**: who sings love will keep us alive by the eagles
- **Expected Answer**: Timothy B. Schmit
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `NQ_fdffe88d90f74dd88781e3843a4d3ef0` (UNNECESSARY_ABSTENTION)
- **Question**: how many episodes are in chicago fire season 4
- **Expected Answer**: 23
- **Generated Answer**: The provided documents **do not contain any information** regarding the number of episodes in *Chicago Fire* Season 4 or any related television series. The uploaded files discuss institutional research collaborations, agricultural advancements, and scientific studies, with no mention of media content like TV episodes.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.
