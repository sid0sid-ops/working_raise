# RAISE RAG Inspiration Vault & Reference Architecture

## 1. Purpose of the `inspiration/` Folder
The `inspiration/` directory is our **authoritative reference laboratory and gold-standard knowledge repository**. It houses curated open-source repositories, 2026 AI research signals, architectural briefs, and reference implementations that guide the development of the **RAISE University Agentic GraphRAG** engine.

---

## 2. Curated Reference Codebases & Documents

| Repository / Asset | Origin / Path | Key Focus & Architectural Role |
| :--- | :--- | :--- |
| **`UNIVERSITY_REPORT_AGENTIC_GRAPHRAG_INSPIRATION_MASTER.md`** | Architectural Brief | Authoritative master specification for multi-university comparative GraphRAG, 7-tier provenance, and anti-hallucination verification. |
| **`graphrag-the-definitive-guide-code/`** | [O'Reilly Companion Code](https://github.com/graphrag/graphrag-the-definitive-guide-code) | Official code companion for *GraphRAG: The Definitive Guide*, demonstrating Neo4j Cypher property graphs, multi-tool agents (`ch08`), memory (`ch09`), entity resolution, and incremental community detection (`ch10`). |
| **`microsoft_graphrag/repo`** | [Microsoft Research](https://github.com/microsoft/graphrag) | Core GraphRAG library implementing hierarchical community detection (Leiden) and Global Search map-reduce summarization. |
| **`graphrag.github.io/`** | [GraphRAG Standards](https://github.com/graphrag/graphrag.github.io) | Official community documentation, benchmark specifications, and standardized entity/claim data schemas. |
| **`graphrag-langgraph-neo4j/`** | [FlorentB974/graphrag](https://github.com/FlorentB974/graphrag) | Native implementation of GraphRAG using LangGraph cyclic state workflows and Neo4j Cypher graph generation. |
| **`agentic-med-diag/`** | [avnlp/agentic-med-diag](https://github.com/avnlp/agentic-med-diag) | SOTA Agentic GraphRAG combining LangGraph multi-hop reasoning, parallel graph/vector/community retrieval, and an agentic plan-research-verify loop. |
| **`Knowledge-Graph-Based-Hybrid-RAG/`** | [safishamsi/KG-Hybrid-RAG](https://github.com/safishamsi/Knowledge-Graph-Based-Hybrid-RAG-System) | Hybrid Retrieval (Neo4j Graph Traversal + SBERT + BM25) orchestrated with LangGraph for academic/research publication graphs. |
| **`semantic-rag-neo4j/`** | [VimalDwarampudi/semantic-rag](https://github.com/VimalDwarampudi/semantic-rag) | Semantic RAG with Formal Ontologies + Neo4j + LangGraph workflows. |
| **`citegraph-copilot/`** | [sergiyclas/citegraph-copilot](https://github.com/sergiyclas/citegraph-copilot) | Academic citation GraphRAG assistant using LangGraph orchestration, MCP tools, and Neo4j. |
| **`rag at scale.odg`** | Architecture Diagram | Decoupled multi-document ingestion and scalable indexing architecture. |

---

## 3. 2026 Research Signals Incorporated into RAISE

1. **IBM Research Docling (`docling-project/docling`)**:
   * SOTA document understanding framework. Excels at layout analysis, reading-order reconstruction, and complex table structure recognition (via `TableFormer`).
   * Bridged into RAISE via the **Canonical Document Model (CDM)** (`ingestion_adapter.py`).

2. **Google Agentic RAG (June 2026)**:
   * Multi-source, multi-hop iterative retrieval loop with an explicit **Evidence Sufficiency Check** (`sufficient: bool`, `missing: []`) before answer generation.

3. **Google ReasoningBank (April 2026)**:
   * Lightweight reasoning trajectory store (`reasoning_memory.py`) capturing verified query patterns, entity disambiguation mappings, and failure recoveries.

4. **Anthropic Contextual Retrieval**:
   * Prepending deterministic document hierarchy context prefixes (`University | Year | Section | Page`) to chunks before vector embedding to prevent context loss.

5. **TabFM & First-Class Tables (Google Research 2026)**:
   * Isolates financial and statistical tables into 2D matrix grids (`table_engine.py`) rather than flattening them into plain prose.

---

## 4. Feature Adoption & Implementation Mapping

| Feature from Inspiration | Source Reference | RAISE Implementation in `RAG/src/` |
| :--- | :--- | :--- |
| **1. Canonical Document Model** | Docling / Master Spec | `ingestion_adapter.py`: Emits JSON, 5-Star HTML5, and Bounding Boxes simultaneously. |
| **2. Table Matrix Engine** | TabFM / Master Spec | `table_engine.py`: Preserves 2D cell grids, headers, and numeric scales. |
| **3. Deterministic Fact Model** | Master Spec | `fact_engine.py`: Normalizes currencies (INR/USD, Lakhs, Crores) and temporal periods (FY vs AY). |
| **4. Contextual Embeddings** | Anthropic Contextual Retrieval | `structure_chunker.py`: Prepends document/section metadata before ChromaDB indexing. |
| **5. Neo4j Property Graphs** | O'Reilly GraphRAG Guide | `neo4j_engine.py`: Parameterized Cypher sync and live terminal queries. |
| **6. Iterative Agentic Loop** | Google Agentic RAG 2026 | `agent_router.py`: Autonomous tool selection with Evidence Sufficiency verification. |
| **7. Reasoning Trajectory Memory** | Google ReasoningBank 2026 | `reasoning_memory.py`: Captures verified multi-hop query strategies. |
| **8. Anti-Hallucination Verifier** | Master Spec | `claim_verifier.py`: Emits validated `AnswerContract` JSON with multi-tier source authority. |
