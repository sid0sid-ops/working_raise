# 🏛️ RAISE Current System Architecture

## 1. System Components

```text
                                [ User Research Query ]
                                           │
                                           ▼
                   ┌───────────────────────────────────────────────┐
                   │    LangGraph StateGraph 5-Node Workflow       │
                   └───────────────────────┬───────────────────────┘
                                           │
            ┌──────────────────────────────┴──────────────────────────────┐
            ▼                                                             ▼
 [ 1. Vector Search (ChromaDB) ]                               [ 2. Subgraph Traversal (Neo4j) ]
 • Cosine $k$-NN over Dense Vectors                             • Seed node expansion (2-hop Cypher)
 • Anthropic Context Enriched Chunks                           • Discovers multi-hop relationships
            │                                                             │
            └──────────────────────────────┬──────────────────────────────┘
                                           ▼
                            [ 3. Hybrid Context Fusion ]
                            (ChromaDB Chunk -> Neo4j Entities)
                                           │
                                           ▼
                          [ 4. Anti-Hallucination Gate ]
                        • Verifies citations [1], [2]
                        • Computes traceability score
                                           │
                                           ▼
                                [ Grounded Research Answer ]
```

---

## 2. Core Modules in `src/`

1. **`parsers/document_parser.py`**:
   - `SmartDocumentParser`: Docling native layout parser (`Layout-Heron` + `TableFormer` + `RapidOCR`) with PyMuPDF fallback.
2. **`pipeline_academic_ingest.py`**:
   - Master ingestion orchestrator. Reads `data/documents/`, builds enriched chunks, extracts academic entities/triples, and updates ChromaDB & Neo4j.
3. **`vector_engine.py`**:
   - `LocalVectorEngine`: ChromaDB persistent HNSW cosine index engine.
4. **`neo4j_engine.py` & `neo4j_schema.py`**:
   - `Neo4jDatabase`: Neo4j Bolt driver with automatic index verification and seamless in-memory NetworkX graph fallback.
5. **`langgraph_workflow.py`**:
   - `GraphRAGWorkflow`: 5-Node cyclical StateGraph (`intent_analyzer` -> `vector_retriever` -> `graph_traverser` -> `synthesizer_verifier` <-> `corrective_expander`).
6. **`agent_router.py`**:
   - Autonomous query classifier and anti-hallucination grounded synthesizer.
7. **`reasoning_memory.py`**:
   - `ReasoningMemory`: Trajectory store for verified query retrieval patterns with substantive Jaccard matching.
