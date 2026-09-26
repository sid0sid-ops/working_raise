# 🔬 RAISE NIAH Benchmark Evaluation Report
**Experiment**: `niah_quant_photonic_grant`  
**Executed At**: `2026-09-05T15:38:00.263634`  
**Total Tests**: `6` | **End-to-End Passed**: `5/6` (`83.3%`) | **Retrieval Recall**: `6/6` (`100.0%`)

---

## 🗺️ 2D Retrieval Robustness Heatmap (Depth vs Context Length)

| Depth (%) | 1,000 words | 5,000 words |
| --- | --- | --- |
| **0%** | 🟩 PASS (r=1) | 🟩 PASS (r=1) |
| **50%** | 🟩 PASS (r=1) | 🟫 GEN (r=1) |
| **100%** | 🟩 PASS (r=1) | 🟩 PASS (r=1) |

**Legend**:
* `🟩 PASS` : Needle successfully retrieved and verified in generated answer.
* `🟥 RETR` : Retrieval Failure (Needle missing from vector top-k candidates).
* `🟨 RANK` : Reranker Failure (Needle demoted outside top candidates by Cross-Encoder).
* `🟦 EMBED`: Embedding Failure (Distractor paragraphs had higher cosine similarity than the needle).
* `🟪 GRAPH`: Knowledge Graph Failure (Multi-hop relational path not found in Neo4j / NetworkX).
* `🟧 CTX`  : Context Budget Failure (Needle retrieved but truncated during prompt assembly).
* `🟫 GEN`  : Generation Failure (Needle in context, but LLM failed to extract or refused).

---

## 📊 Diagnostic Failure Breakdown

| Failure Stage | Count | Percentage |
| :--- | :--- | :--- |
| `SUCCESS` | 5 | 83.3% |
| `GENERATION_FAILURE` | 1 | 16.7% |

---

## 📝 Detailed Test Execution Log

### Test #1: Needle `quant_photonic_grant` | Depth 0.0 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8802`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #2: Needle `quant_photonic_grant` | Depth 0.0 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8802`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #3: Needle `quant_photonic_grant` | Depth 0.5 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8266`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #4: Needle `quant_photonic_grant` | Depth 0.5 | Size 5000w
- **Status**: `GENERATION_FAILURE`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8063`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: Generation error: LLM failed to extract exact needle answer despite presence in context. Output: 'The provided evidence does not contain any information regarding the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY ...'

### Test #5: Needle `quant_photonic_grant` | Depth 1.0 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8216`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #6: Needle `quant_photonic_grant` | Depth 1.0 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8492`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

