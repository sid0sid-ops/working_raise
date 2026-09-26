# RAISE Baseline Evaluation Report — Run `run_20260925_195718_triviaqa_forensic_baseline`

**Benchmark**: triviaqa  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-25T19:59:03.277125+00:00  
**Total Evaluated Cases**: 5 | **Passed**: 0 | **Failed**: 5  

---

## 1. Multi-Dimensional Scorecard

| Layer | Metric | Score | Unit / Notes |
| :--- | :--- | :---: | :--- |
| **Retrieval** | Recall@1 | `20.00%` | Top-1 gold candidate discovery |
| **Retrieval** | Recall@4 | `20.00%` | Standard synthesis context cutoff |
| **Retrieval** | Recall@8 | `20.00%` | Extended expert context cutoff |
| **Retrieval** | nDCG@10 | `0.4123` | Normalized discounted cumulative gain |
| **Retrieval** | MRR@10 | `0.2000` | Mean reciprocal rank of gold evidence |
| **QA Correctness** | Exact Match (EM) | `20.00%` | Normalized string equivalence |
| **QA Correctness** | Token F1 | `0.80%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `100.00%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `80.00%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `100.00%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `100.00%` | Refusals on answerable queries |
| **System** | Latency p50 | `24161.9 ms` | Median per-query latency |
| **System** | Latency p95 | `25486.6 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `0.37 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **5**

### Failure Card: `TRIVIA_tc_2` (UNNECESSARY_ABSTENTION)
- **Question**: Who was the man behind The Chipmunks?
- **Expected Answer**: David Seville
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `TRIVIA_tc_33` (UNNECESSARY_ABSTENTION)
- **Question**: Which Lloyd Webber musical premiered in the US on 10th December 1993?
- **Expected Answer**: Sunset Boulevard
- **Generated Answer**: The provided documents do not contain information regarding which Lloyd Webber musical premiered in the US on 10th December 1993. The attached excerpts focus on institutional annual reports, study tours, and scientific research activities, with no mention of theatrical productions or Andrew Lloyd Webber.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `TRIVIA_tc_40` (UNNECESSARY_ABSTENTION)
- **Question**: Who was the next British Prime Minister after Arthur Balfour?
- **Expected Answer**: Campbell-Bannerman
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `TRIVIA_tc_49` (UNNECESSARY_ABSTENTION)
- **Question**: Who had a 70s No 1 hit with Kiss You All Over?
- **Expected Answer**: Exile
- **Generated Answer**: The provided documents **do not contain any information** regarding a 70s No 1 hit with the song *"Kiss You All Over"* or any related musical artists, performers, or chart achievements. The excerpts only reference academic research projects, institutional events, and personnel details at NIPGR.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `TRIVIA_tc_56` (UNNECESSARY_ABSTENTION)
- **Question**: What claimed the life of singer Kathleen Ferrier?
- **Expected Answer**: Cancer
- **Generated Answer**: The provided documents **do not contain any information** regarding the cause of death of singer Kathleen Ferrier. The excerpts pertain exclusively to breast cancer trends, pancreatic cancer research, and institutional reports from the Biotechnology Research and Innovation Council (BRIC). No mention of Kathleen Ferrier or her cause of death appears in the uploaded files.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.
