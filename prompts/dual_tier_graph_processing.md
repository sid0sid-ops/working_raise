# Dual-Tier Graph Processing Architecture

## Overview: Bypassing Neo4j Community Edition GDS Limitations
In standard enterprise deployments, graph analytics (such as Louvain Community Detection, PageRank, and Betweenness Centrality) rely on the **Neo4j Graph Data Science (GDS)** plugin. However, in **Neo4j Community Edition**, the GDS library is unavailable.

To resolve this limitation without proprietary licensing, RAISE implements a **Dual-Tier Graph Processing Architecture**:
1. **Tier 1: Transactional Graph Store (Neo4j Community Edition)**
   - Manages ACID transactions, parameterized batch ingestion (`UNWIND $batch`), uniqueness constraints, and index-accelerated point lookups / shallow Cypher path traversals.
2. **Tier 2: In-Memory Analytical Processing Engine (NetworkX)**
   - Synchronizes subgraphs and global graphs into in-memory `networkx.DiGraph` / `networkx.Graph` data structures.
   - Computes Louvain Community Detection, Clauset-Newman-Moore Greedy Modularity, PageRank, and Betweenness Centrality in Python memory.
   - Generates hierarchical community clusters and domain summaries for global GraphRAG reasoning.

---

## 1. NetworkX Community Detection Workflow

### A. Graph Undirection & Modularity Optimization:
NetworkX partitions directed or undirected graphs into disjoint communities using modularity maximization:
- **Louvain Heuristic (`nx.community.louvain_communities`)**:
  Optimizes modularity in $O(N \log N)$ time, identifying dense intra-cluster clusters (e.g., related research labs, grant consortia, startup incubators).
- **Greedy Modularity (`nx.community.greedy_modularity_communities`)**:
  Hierarchical agglomeration fallback when deterministic clustering is required.

### B. Node Centrality & Hub Identification:
- **PageRank (`nx.pagerank`)**: Computes prestige scores for institutional nodes (identifying core institutes and flagship programs).
- **Degree & Betweenness Centrality**: Highlights bridge nodes (e.g., cross-departmental PIs, shared research facilities, technology transfer offices).

---

## 2. Hierarchical Summarization Pattern for GraphRAG
1. **Cluster Partitioning**: The global graph is partitioned into level-0 and level-1 communities.
2. **Community Profiling**: For each community $C_k$, extract:
   - Hub Entities (top-3 PageRank / degree nodes).
   - Thematic Section types (e.g., *Patents & Intellectual Property*, *Financial Statements & Budgets*).
   - High-weight relational bridges.
3. **Synthesis**: LLM generates a structured community summary that answers broad thematic and multi-hop queries without querying thousands of individual chunks.
