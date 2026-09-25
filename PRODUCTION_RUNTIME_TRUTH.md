# RAISE — PRODUCTION RUNTIME TRUTH AUDIT

**Date Verified**: 2026-09-26  
**Auditor**: Antigravity Automated Verification Agent  
**Repository**: `C:\Users\Siddharth Tripathi\Documents\raise`  
**Git Branch**: `conv`  
**Target Environment**: Windows 11 + NVIDIA RTX 3090 (24GB VRAM) + Local Neo4j + Local Redis  

---

## 1. Executive Summary & Root Path Verification

- **Production Code Path**: The actual production code is located at **`C:\Users\Siddharth Tripathi\Documents\raise\backend\src`**.
- **`RAG\src` Status**: **DOES NOT EXIST**. Any documentation claiming production code lives in `RAG\src` is obsolete. The `RAG\` directory contains only `data\`, `docs\`, `evaluation\`, and `.cache\`.
- **Imports Runtime Mapping**: At runtime, `backend\app.py` and `backend\server.py` insert `backend` into `sys.path[0]`, resolving all `from src.*` imports to `backend\src\*`.

---

## 2. Component Runtime Truth Matrix

| Component | Claimed Path | Actual Imported Path | Actual Class / Function | Live? | Live Configuration / Weights |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **API Entry Point** | `backend/server.py` | `backend/app.py` | `app: FastAPI` | **YES** | FastAPI Modular Monolith with 10 routers |
| **Master Orchestrator** | `backend/src/retrieval/pipeline.py` | `backend/src/retrieval/pipeline.py` | `StandaloneRAGPipeline` | **YES** | Auto-inits vector, graph, tabular, and LangGraph |
| **Workflow Module** | `backend/src/features/agent/workflow.py` | `backend/src/features/agent/workflow.py` | `AcademicGraphRAGWorkflow` | **YES** | LangGraph StateGraph (16 nodes, cyclical retry loop) |
| **Dense Vector Retriever**| `backend/src/infrastructure/vector/chroma.py` | `backend/src/infrastructure/vector/chroma.py` | `LocalVectorEngine` | **YES** | ChromaDB collection `iitmrp_docling_bge_large` (9,776 chunks) |
| **Sparse Lexical Retriever**| `backend/src/retrieval/parallel_retriever.py` | `backend/src/retrieval/parallel_retriever.py` | `SelfContainedBM25` | **YES** | In-memory rank-bm25 index synchronized with chunk text |
| **Knowledge Graph Backend**| `backend/src/infrastructure/graph/neo4j.py` | `backend/src/infrastructure/graph/neo4j.py` | `Neo4jDatabase` | **YES** | `bolt://localhost:7687` (2,580 nodes, APOC enabled) |
| **In-Memory Graph Engine** | `backend/src/features/graph/engine.py` | `backend/src/features/graph/engine.py` | `GraphRAGEngine` | **YES** | NetworkX property graph representation |
| **Embedding Model** | `BAAI/bge-large-en-v1.5` | `backend/src/infrastructure/vector/chroma.py` | `SentenceTransformer` | **YES** | `BAAI/bge-large-en-v1.5` (1024-dim, cosine distance) |
| **Reranker** | `BAAI/bge-reranker-large` | `backend/src/retrieval/fusion.py` | `CrossEncoderReranker` | **YES** | `CrossEncoder("BAAI/bge-reranker-large")` on CUDA (batch 64) |
| **Reciprocal Rank Fusion**| `backend/src/retrieval/fusion.py` | `backend/src/retrieval/fusion.py` | `reciprocal_rank_fusion` | **YES** | Channels: Dense, BM25, and Neo4j graph triples (k=60) |
| **LLM Provider Router** | `backend/src/infrastructure/providers/router.py`| `backend/src/infrastructure/providers/router.py`| `ProviderRouter` | **YES** | Primary: Groq (`qwen/qwen3.8-27b`), Fallback: Mistral |
| **Quality Gate Verification**| `backend/src/features/evaluation/engine.py` | `backend/src/features/evaluation/engine.py` | `RuntimeFaithfulnessQualityGate` | **YES** | `NumericalClaimVerifier` + `FineCat-ModernBERT-NLI` |
| **Citation Validator** | `backend/src/features/evaluation/engine.py` | `backend/src/features/evaluation/engine.py` | `CitationValidator` | **YES** | Strict bracket `[page]` and document title boundary check |
| **Relational Memory / DB**| `backend/src/infrastructure/database/postgres.py`| `backend/src/infrastructure/database/postgres.py`| `PostgresManager` | **YES** | PostgreSQL 16 at `localhost:5432` (`raise_db`) |
| **Cache & Limiting Layer**| `backend/src/infrastructure/cache/redis.py` | `backend/src/infrastructure/cache/redis.py` | `RedisCacheManager` | **YES** | Redis 7 at `redis://localhost:6379/0` (0.33 ms latency) |

---

## 3. Audit Findings Verification

### A. LangGraph Node Count Discrepancy
- **Claimed in previous documentation**: 7 or 9 nodes.
- **Actual Live Implementation**: **16 nodes** registered in `AcademicGraphRAGWorkflow._build_graph()`:
  1. `query_intake`
  2. `general_chat_responder`
  3. `empty_workspace_responder`
  4. `classification_and_routing`
  5. `community_summary_retriever`
  6. `text_to_cypher_generator`
  7. `cypher_executor_and_validator`
  8. `cypher_repair`
  9. `relational_path_critic`
  10. `hybrid_retriever`
  11. `fusion_and_response_synthesis`
  12. `runtime_faithfulness_gate`
  13. `query_reformulation`
  14. `secondary_retrieval`
  15. `citation_validation`
  16. `unverified_responder`

### B. Neo4j Graph Evidence in RRF Discrepancy
- **Previous Audit Finding**: Graph evidence was queried but discarded or handled outside the candidate list for RRF.
- **Current Live Truth**: In [`backend/src/features/agent/workflow.py`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/backend/src/features/agent/workflow.py#L640-L680), Neo4j subgraph edges are formatted into synthetic chunks (`graph_chunks` with `Institutional Knowledge Graph Fact: {src} --[{rel}]--> {tgt}.`) and explicitly appended as a 3rd channel into `reciprocal_rank_fusion` with a dedicated channel weight of `1.05`.

---

## 4. Operational Prerequisites for Multi-Benchmark Testing
- Any execution testing the production GraphRAG path must connect to real Neo4j (`bolt://localhost:7687`), real ChromaDB (`.chromadb_bge_large` or isolated evaluation collections), and real CrossEncoder GPU reranking.
- Mode A tests must execute retrieval only (Dense + BM25 + Neo4j Graph + RRF + CrossEncoder) with zero generation calls.
- Mode B tests must execute through `StandaloneRAGPipeline` / `AcademicGraphRAGWorkflow`.
