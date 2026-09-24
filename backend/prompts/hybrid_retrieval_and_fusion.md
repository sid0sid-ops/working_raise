# Hybrid Retrieval and Fusion: Reciprocal Rank Fusion & Cross-Encoder Reranking

## 1. Reciprocal Rank Fusion (RRF) Formulation
To reconcile disparate score distributions across heterogeneous retrieval channels (Dense Vector Search, BM25/Sparse Keyword Search, and Graph Subgraph Extractions), RAISE applies **Reciprocal Rank Fusion (RRF)**.

RRF scores candidate documents based on their ordinal rank across retrieval systems rather than uncalibrated raw similarity metrics:

$$\text{RRF Score}(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$

Where:
- $M$: The set of retrieval systems (Dense Vector, Sparse Lexical, Graph Subgraph).
- $r_m(d)$: The 1-based ordinal rank of document/chunk $d$ in retrieval system $m$.
- $k$: Constant smoothing parameter (calibrated to $k = 60$) to prevent top-ranked outliers from dominating the fused scoring distribution.

---

## 2. Cross-Encoder Contextual Reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
While RRF effectively merges ranked candidate lists, it relies on rank positions and does not assess direct cross-attention semantic relevance between candidate texts and the user query.

1. **Candidate Pool Selection**: The top $N$ candidates (e.g., $N = 15\text{--}20$) identified by RRF are passed to a cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
2. **Cross-Attention Pass**: The model computes full token-to-token cross-attention between the query and each candidate chunk:
   $$\text{Score}(q, d) = \text{CrossEncoder}([\text{CLS}] \circ q \circ [\text{SEP}] \circ d \circ [\text{SEP}])$$
3. **Peripheral Filtering**: Cross-attention filters out peripheral graph nodes, tangential lexical matches, and irrelevant semantic neighbors.
4. **Final Context Injection**: Only the top $K$ ($K = 3\text{--}5$) highly relevant, verified passages are injected into the final synthesis context window of **Qwen 2.5 7B**.
