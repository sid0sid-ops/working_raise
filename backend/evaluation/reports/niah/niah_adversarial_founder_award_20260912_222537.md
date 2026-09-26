# 🔬 RAISE NIAH Benchmark Evaluation Report
**Experiment**: `niah_adversarial_founder_award`  
**Executed At**: `2026-09-12T22:25:37.374260`  
**Total Tests**: `6` | **End-to-End Passed**: `6/6` (`100.0%`) | **Retrieval Recall**: `6/6` (`100.0%`)

---

## 🗺️ 2D Retrieval Robustness Heatmap (Depth vs Context Length)

| Depth (%) | 1,000 words | 5,000 words |
| --- | --- | --- |
| **0%** | 🟩 PASS (r=1) | 🟩 PASS (r=1) |
| **50%** | 🟩 PASS (r=2) | 🟩 PASS (r=1) |
| **100%** | 🟩 PASS (r=1) | 🟩 PASS (r=2) |

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
| `SUCCESS` | 6 | 100.0% |

---

## 📝 Detailed Test Execution Log

### Test #1: Needle `adversarial_founder_award` | Depth 0.0 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8785`)
- **Query**: "Who was awarded the 2024 Distinguished Bioengineering Pioneer Award?"
- **Expected Answer**: `Dr. Evelyn Thorne`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #2: Needle `adversarial_founder_award` | Depth 0.0 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8497`)
- **Query**: "Who was awarded the 2024 Distinguished Bioengineering Pioneer Award?"
- **Expected Answer**: `Dr. Evelyn Thorne`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #3: Needle `adversarial_founder_award` | Depth 0.5 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `2`, Sim: `0.7847`)
- **Query**: "Who was awarded the 2024 Distinguished Bioengineering Pioneer Award?"
- **Expected Answer**: `Dr. Evelyn Thorne`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #4: Needle `adversarial_founder_award` | Depth 0.5 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8019`)
- **Query**: "Who was awarded the 2024 Distinguished Bioengineering Pioneer Award?"
- **Expected Answer**: `Dr. Evelyn Thorne`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #5: Needle `adversarial_founder_award` | Depth 1.0 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8142`)
- **Query**: "Who was awarded the 2024 Distinguished Bioengineering Pioneer Award?"
- **Expected Answer**: `Dr. Evelyn Thorne`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #6: Needle `adversarial_founder_award` | Depth 1.0 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `2`, Sim: `0.7823`)
- **Query**: "Who was awarded the 2024 Distinguished Bioengineering Pioneer Award?"
- **Expected Answer**: `Dr. Evelyn Thorne`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

