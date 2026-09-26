# 🔬 RAISE NIAH Benchmark Evaluation Report
**Experiment**: `comprehensive_pipeline_evaluation`  
**Executed At**: `2026-09-05T17:05:01.727197`  
**Total Tests**: `40` | **End-to-End Passed**: `40/40` (`100.0%`) | **Retrieval Recall**: `40/40` (`100.0%`)

---

## 🗺️ 2D Retrieval Robustness Heatmap (Depth vs Context Length)

| Depth (%) | 1,000 words | 3,000 words | 4,000 words | 5,000 words | 6,000 words | 10,000 words |
| --- | --- | --- | --- | --- | --- | --- |
| **0%** | 🟩 PASS (r=1) | 🟩 PASS (r=1) | ⬜ N/A | 🟩 PASS (r=1) | 🟩 PASS (r=1) | 🟩 PASS (r=1) |
| **25%** | 🟩 PASS (r=2) | 🟩 PASS (r=1) | ⬜ N/A | ⬜ N/A | 🟩 PASS (r=1) | 🟩 PASS (r=1) |
| **50%** | 🟩 PASS (r=1) | 🟩 PASS (r=1) | 🟩 PASS (r=1) | 🟩 PASS (r=1) | 🟩 PASS (r=1) | 🟩 PASS (r=1) |
| **75%** | 🟩 PASS (r=1) | 🟩 PASS (r=1) | ⬜ N/A | ⬜ N/A | 🟩 PASS (r=10) | 🟩 PASS (r=1) |
| **100%** | 🟩 PASS (r=1) | 🟩 PASS (r=1) | ⬜ N/A | 🟩 PASS (r=1) | 🟩 PASS (r=1) | 🟩 PASS (r=1) |

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
| `SUCCESS` | 40 | 100.0% |

---

## 📝 Detailed Test Execution Log

### Test #1: Needle `fact_quantum_crypt` | Depth 0.0 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8586`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #2: Needle `fact_quantum_crypt` | Depth 0.0 | Size 3000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8586`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #3: Needle `fact_quantum_crypt` | Depth 0.0 | Size 6000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8586`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #4: Needle `fact_quantum_crypt` | Depth 0.0 | Size 10000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8586`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #5: Needle `fact_quantum_crypt` | Depth 0.25 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `2`, Sim: `0.772`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #6: Needle `fact_quantum_crypt` | Depth 0.25 | Size 3000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8016`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #7: Needle `fact_quantum_crypt` | Depth 0.25 | Size 6000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.809`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #8: Needle `fact_quantum_crypt` | Depth 0.25 | Size 10000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8082`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #9: Needle `fact_quantum_crypt` | Depth 0.5 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8378`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #10: Needle `fact_quantum_crypt` | Depth 0.5 | Size 3000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.809`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #11: Needle `fact_quantum_crypt` | Depth 0.5 | Size 6000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8005`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #12: Needle `fact_quantum_crypt` | Depth 0.5 | Size 10000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8614`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #13: Needle `fact_quantum_crypt` | Depth 0.75 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.7887`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #14: Needle `fact_quantum_crypt` | Depth 0.75 | Size 3000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8845`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #15: Needle `fact_quantum_crypt` | Depth 0.75 | Size 6000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `10`, Sim: `0.7725`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #16: Needle `fact_quantum_crypt` | Depth 0.75 | Size 10000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8115`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #17: Needle `fact_quantum_crypt` | Depth 1.0 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.853`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #18: Needle `fact_quantum_crypt` | Depth 1.0 | Size 3000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8071`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #19: Needle `fact_quantum_crypt` | Depth 1.0 | Size 6000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8387`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #20: Needle `fact_quantum_crypt` | Depth 1.0 | Size 10000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8687`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #21: Needle `quant_photonic_grant` | Depth 0.0 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8802`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #22: Needle `quant_photonic_grant` | Depth 0.0 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8802`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #23: Needle `quant_photonic_grant` | Depth 0.5 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8266`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #24: Needle `quant_photonic_grant` | Depth 0.5 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8063`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #25: Needle `quant_photonic_grant` | Depth 1.0 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8216`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #26: Needle `quant_photonic_grant` | Depth 1.0 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8492`)
- **Query**: "What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?"
- **Expected Answer**: `₹42.75 Crore`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #27: Needle `graph_multihop_carbon` | Depth 0.0 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.822`)
- **Query**: "What was the particulate reduction efficiency achieved by the initiative led by Dr. Alistair Vance?"
- **Expected Answer**: `38.4 percent`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #28: Needle `graph_multihop_carbon` | Depth 0.0 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.822`)
- **Query**: "What was the particulate reduction efficiency achieved by the initiative led by Dr. Alistair Vance?"
- **Expected Answer**: `38.4 percent`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #29: Needle `graph_multihop_carbon` | Depth 0.5 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.7819`)
- **Query**: "What was the particulate reduction efficiency achieved by the initiative led by Dr. Alistair Vance?"
- **Expected Answer**: `38.4 percent`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #30: Needle `graph_multihop_carbon` | Depth 0.5 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.7628`)
- **Query**: "What was the particulate reduction efficiency achieved by the initiative led by Dr. Alistair Vance?"
- **Expected Answer**: `38.4 percent`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #31: Needle `graph_multihop_carbon` | Depth 1.0 | Size 1000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.7936`)
- **Query**: "What was the particulate reduction efficiency achieved by the initiative led by Dr. Alistair Vance?"
- **Expected Answer**: `38.4 percent`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #32: Needle `graph_multihop_carbon` | Depth 1.0 | Size 5000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8294`)
- **Query**: "What was the particulate reduction efficiency achieved by the initiative led by Dr. Alistair Vance?"
- **Expected Answer**: `38.4 percent`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #33: Needle `fact_quantum_crypt` | Depth 0.5 | Size 4000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.893`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #34: Needle `fact_quantum_crypt` | Depth 0.5 | Size 4000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.7944`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #35: Needle `fact_quantum_crypt` | Depth 0.5 | Size 4000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.7974`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #36: Needle `fact_quantum_crypt` | Depth 0.5 | Size 4000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `2`, Sim: `0.7844`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #37: Needle `fact_quantum_crypt` | Depth 0.5 | Size 4000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8152`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #38: Needle `fact_quantum_crypt` | Depth 0.5 | Size 4000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8202`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #39: Needle `fact_quantum_crypt` | Depth 0.5 | Size 4000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8457`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

### Test #40: Needle `fact_quantum_crypt` | Depth 0.5 | Size 4000w
- **Status**: `SUCCESS`
- **Top-K Recall**: `True` (Gold Rank: `1`, Sim: `0.8202`)
- **Query**: "What is the access authorization code for the Project Chimera quantum computing cluster?"
- **Expected Answer**: `DELTA-9842-OMEGA`
- **Root Cause**: None. Needle successfully retrieved, preserved in context, and synthesized.

