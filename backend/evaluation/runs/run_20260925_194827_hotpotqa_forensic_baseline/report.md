# RAISE Baseline Evaluation Report — Run `run_20260925_194827_hotpotqa_forensic_baseline`

**Benchmark**: hotpotqa  
**Ablation**: `ABL-G` (Full Verified RAG (Production Default))  
**Date**: 2026-09-25T19:50:30.340475+00:00  
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
| **QA Correctness** | Exact Match (EM) | `20.00%` | Normalized string equivalence |
| **QA Correctness** | Token F1 | `1.76%` | Precision / Recall harmonic mean |
| **QA Correctness** | Numeric Accuracy | `100.00%` | Exact financial numbers / table cells |
| **Grounding** | Faithfulness | `60.00%` | FineCat NLI verified claims ratio |
| **Provenance** | Citation Accuracy | `100.00%` | Verified physical page numbers |
| **Safety** | Unsupported Answer Rate | `0.00%` | Hallucinated answers on unanswerable traps |
| **Safety** | Unnecessary Abstentions | `100.00%` | Refusals on answerable queries |
| **System** | Latency p50 | `26058.7 ms` | Median per-query latency |
| **System** | Latency p95 | `29486.3 ms` | 95th percentile latency |
| **Memory** | Full Memory Recall | `100.0%` | PostgreSQL 16 + Redis 7 3-turn recall |
| **Memory** | Read Latency | `0.32 ms` | Redis sub-millisecond session lookup |

---

## 2. Failure Diagnostics Breakdown

Total Failed Cases Analyzed: **5**

### Failure Card: `HOTPOT_5a8b57f25542995d1e6f1371` (UNNECESSARY_ABSTENTION)
- **Question**: Were Scott Derrickson and Ed Wood of the same nationality?
- **Expected Answer**: yes
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `HOTPOT_5a8c7595554299585d9e36b6` (UNNECESSARY_ABSTENTION)
- **Question**: What government position was held by the woman who portrayed Corliss Archer in the film Kiss and Tell?
- **Expected Answer**: Chief of Protocol
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `HOTPOT_5a85ea095542994775f606a8` (UNNECESSARY_ABSTENTION)
- **Question**: What science fantasy young adult series, told in first person, has a set of companion books narrating the stories of enslaved worlds and alien species?
- **Expected Answer**: Animorphs
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `HOTPOT_5adbf0a255429947ff17385a` (UNNECESSARY_ABSTENTION)
- **Question**: Are the Laleli Mosque and Esma Sultan Mansion located in the same neighborhood?
- **Expected Answer**: no
- **Generated Answer**: I could not verify this answer against the uploaded academic sources. Please upload additional relevant material or refine the question.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.

### Failure Card: `HOTPOT_5a8e3ea95542995a26add48d` (UNNECESSARY_ABSTENTION)
- **Question**: The director of the romantic comedy "Big Stone Gap" is based in what New York city?
- **Expected Answer**: Greenwich Village, New York City
- **Generated Answer**: The provided documents **do not contain any information** regarding the director of the romantic comedy *"Big Stone Gap"* or their affiliation with a New York city. The excerpts pertain exclusively to academic seminars, institutional leadership (e.g., Dr. Subhra Chakraborty as Director of NIPGR), and scientific events at the National Institute of Plant Genome Research (NIPGR). No mention of film directors, movies, or New York locations appears in the uploaded documents.
- **Root Cause**: `UNNECESSARY_ABSTENTION` | **Affected Component**: `Quality Gate / Unverified Responder`
- **Evidence Rank**: Highest rank: #1 (Vec:1, BM25:1, Graph:1, RRF:1, Rerank:-1)
- **Why Failed**: Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims.
- **Proposed Fix**: Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection.
