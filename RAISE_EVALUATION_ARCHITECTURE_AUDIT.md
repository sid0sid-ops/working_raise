# RAISE Architecture & Runtime Consistency Forensic Audit

**Document Status**: CANONICAL & AUDITED  
**Audit Date**: 2026-09-24T06:21:00+05:30  
**Target Repository**: `semanticClimate/RAISE`  
**Execution Environment**: Windows 11 / Python 3.13.13 / Miniconda3 / Native Rust (PyO3)  
**Evaluator Principle**: First Principle: Zero Pipeline Code Modification Before Baseline Establishment

---

## 1. Executive Summary

This forensic audit rigorously inspects the canonical architecture documentation of RAISE against its live codebase, Docker container stack, database instances, and actual execution paths. 

The canonical documentation claims a **16-node LangGraph StateGraph**, end-to-end multi-substrate retrieval (BGE-Large ChromaDB, Okapi BM25, Neo4j Knowledge Graph, Reciprocal Rank Fusion, Cross-Encoder Reranking), verified claim-level NLI grounding, and session memory across PostgreSQL 16 and Redis 7.

This audit establishes:
1. **The exact truth of the LangGraph node count discrepancy**: The codebase registers **18 nodes**, of which **16 are reachable** and **2 are dead/unreachable**.
2. **The exact state of live database backends**: PostgreSQL 16.15 (healthy, 6 public tables), Redis 7.4.11 (healthy, 0 active keys), Neo4j 5.26 (healthy, 2,580 nodes, 6,376 relationships), and ChromaDB (healthy, 9,776 chunks in `iitmrp_docling_bge_large`).
3. **The active runtime inference configuration**: `.env` specifies `LLM_BACKEND=groq` with `llama-3.3-70b-versatile`, while local vLLM container (`raise-vllm-prod`) is currently in an unhealthy container state.
4. **Rust acceleration status**: Verified active and running via native PyO3 binding (`raise_engine`).
5. **Retrieval and fusion discrepancy**: In `workflow.py`, Reciprocal Rank Fusion fuses Dense and BM25 candidates, while Neo4j graph nodes are passed directly as graph evidence to the synthesis prompt rather than participating as equal chunk candidates in `reciprocal_rank_fusion()`.
6. **Immutable Runtime Component Manifest**: Documenting every single active component for auditable benchmarking.

---

## 2. LangGraph Node Count & State Machine Forensic Audit

### 2.1 The Architectural Inconsistency

Canonical documentation across multiple documents states:
- `docs/ARCHITECTURE.md` (lines 13, 27): *"asynchronous 16-node LangGraph execution state machine"*
- `docs/CHUNKING_RETRIEVAL_DATA_ARCHITECTURE.md` (lines 541, 821, 970): *"The query lifecycle is orchestrated by a 16-node cyclical StateGraph in src/features/agent/workflow.py"*
- `docs/MODULE_REGISTRY.md` (line 101): *"workflow.py: 16-node LangGraph cyclical agent state machine."*
- `docs/EXECUTION_FLOW.md` (line 13, 88): *"LangGraph 16-Node Cyclical Agent Execution"*

However, the Markdown table in `docs/CHUNKING_RETRIEVAL_DATA_ARCHITECTURE.md` (lines 584–606) explicitly enumerates rows numbered **1 through 18**.

### 2.2 Source-Level Code Audit (`backend/src/features/agent/workflow.py`)

In `AcademicGraphRAGWorkflow._build_graph()` (lines 126–228), `workflow.add_node(...)` is invoked exactly **18 times**:

| # | Registered Node Name | Implementation Handler | Edge Ingress (Incoming) | Edge Egress (Outgoing) | Reachability Status | Notes / Behavioral Classification |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `query_intake` | `_query_intake_node` | `START` | Conditional: `bypass`, `empty_workspace`, `proceed` | **REACHABLE** | Initial entrypoint; coreference resolution, session binding |
| 2 | `general_chat_responder` | `_general_chat_responder_node` | `query_intake` (bypass) | `END` | **REACHABLE** | Direct conversational response, bypasses retrieval |
| 3 | `empty_workspace_check` | `_empty_workspace_check_node` | **NONE** (0 incoming edges) | **NONE** (0 outgoing edges) | **DEAD / UNREACHABLE** | **Dead code**. Intake router directly targets `empty_workspace_responder` |
| 4 | `empty_workspace_responder` | `_empty_workspace_responder_node` | `query_intake` (empty_workspace) | `END` | **REACHABLE** | Refusal when active document set is 0 |
| 5 | `classification_and_routing` | `_classification_and_routing_node` | `query_intake` (proceed) | Conditional: `global_community`, `local_cypher`, `hybrid_vector` | **REACHABLE** | Intent classification and routing |
| 6 | `community_summary_retriever`| `_community_summary_retriever_node` | `classification_and_routing` | `fusion_and_response_synthesis` | **REACHABLE** | Global macro-level summaries |
| 7 | `text_to_cypher_generator` | `_text_to_cypher_generator_node` | `classification_and_routing` | `cypher_executor_and_validator` | **REACHABLE** | Text-to-Cypher generation via LLM |
| 8 | `cypher_executor_and_validator`| `_cypher_executor_and_validator_node` | `text_to_cypher_generator`, `cypher_repair` | Conditional: `success`, `repair`, `fallback` | **REACHABLE** | Cypher syntax check & Neo4j execution |
| 9 | `cypher_repair` | `_cypher_repair_node` | `cypher_executor_and_validator` (repair) | Conditional: `retry`, `fallback` | **REACHABLE (Fallback-only)** | Self-correction loop (max 2 retries) |
| 10 | `relational_path_critic` | `_relational_path_critic_node` | `cypher_executor_and_validator` (success) | `hybrid_retriever` | **REACHABLE** | Multi-hop graph expansion & entity linking |
| 11 | `hybrid_retriever` | `_hybrid_retriever_node` | `classification_and_routing`, `relational_path_critic`, `cypher_executor_and_validator` (fallback), `cypher_repair` (fallback) | `fusion_and_response_synthesis` | **REACHABLE** | Core parallel dense vector + BM25 + Neo4j subgraph + RRF |
| 12 | `dense_vector_fallback` | `_hybrid_retriever_node` | **NONE** (0 incoming edges) | `fusion_and_response_synthesis` | **DEAD / UNREACHABLE** | **Dead duplicate**. Exact duplicate handler of `hybrid_retriever`; no node routes to it |
| 13 | `fusion_and_response_synthesis`| `_fusion_and_response_synthesis_node` | `community_summary_retriever`, `hybrid_retriever`, `dense_vector_fallback`, `secondary_retrieval` | `runtime_faithfulness_gate` | **REACHABLE** | LLM grounded synthesis over retrieved evidence |
| 14 | `runtime_faithfulness_gate` | `_runtime_faithfulness_gate_node` | `fusion_and_response_synthesis` | Conditional: `accept`, `retry`, `unable_to_verify` | **REACHABLE** | Quality gate evaluating claims, tables, citations |
| 15 | `query_reformulation` | `_query_reformulation_node` | `runtime_faithfulness_gate` (retry) | `secondary_retrieval` | **REACHABLE (Fallback-only)** | Rewrites query if faithfulness < 0.80 |
| 16 | `secondary_retrieval` | `_secondary_retrieval_node` | `query_reformulation` | `fusion_and_response_synthesis` | **REACHABLE (Fallback-only)** | Iterative retrieval loop over reformulated query |
| 17 | `citation_validation` | `_citation_validation_node` | `runtime_faithfulness_gate` (accept) | `END` | **REACHABLE** | Verifies physical page citations |
| 18 | `unverified_responder` | `_unverified_responder_node` | `runtime_faithfulness_gate` (unable_to_verify) | `END` | **REACHABLE (Fallback-only)** | Safe refusal for ungrounded queries |

### 2.3 Summary of Graph Topology Audit

- **Documented Node Count**: 16
- **Registry Table Rows**: 18
- **Code Registered Nodes**: 18
- **Reachable Nodes**: Exactly **16**
- **Dead / Unreachable Nodes**: Exactly **2**
  1. `empty_workspace_check` (Node #3): Bypassed completely because `_query_intake_node` inspects `active_docs` and `_evaluate_intake_route` branches directly to `empty_workspace_responder`.
  2. `dense_vector_fallback` (Node #12): Registered with outgoing edge to synthesis, but every fallback condition in `_evaluate_cypher_execution` and `_evaluate_repair_iteration` explicitly targets `hybrid_retriever`.
- **Duplicate Nodes**: `dense_vector_fallback` is an exact alias/duplicate pointing to `self._hybrid_retriever_node` (line 140, 710).
- **Fallback-Only Nodes**: 4 nodes (`cypher_repair`, `query_reformulation`, `secondary_retrieval`, `unverified_responder`).
- **Production Path Actually Exercised**:
  - **Standard Academic QA Route** (7 nodes):
    `START` $\to$ `query_intake` $\to$ `classification_and_routing` $\to$ `hybrid_retriever` $\to$ `fusion_and_response_synthesis` $\to$ `runtime_faithfulness_gate` $\to$ `citation_validation` $\to$ `END`.
  - **Complex Relational Cypher Route** (9 nodes):
    `START` $\to$ `query_intake` $\to$ `classification_and_routing` $\to$ `text_to_cypher_generator` $\to$ `cypher_executor_and_validator` $\to$ `relational_path_critic` $\to$ `hybrid_retriever` $\to$ `fusion_and_response_synthesis` $\to$ `runtime_faithfulness_gate` $\to$ `citation_validation` $\to$ `END`.
  - **Direct Conversational Route** (2 nodes):
    `START` $\to$ `query_intake` $\to$ `general_chat_responder` $\to$ `END`.
  - **Empty Workspace Refusal Route** (2 nodes):
    `START` $\to$ `query_intake` $\to$ `empty_workspace_responder` $\to$ `END`.

**Conclusion on Node Discrepancy**: The original design intended 18 nodes, but during implementation, `empty_workspace_check` was subsumed into the intake router and `dense_vector_fallback` was consolidated into `hybrid_retriever`. The remaining reachable graph has **16 active nodes**, which matches the high-level architecture documents.

---

## 3. Production vs Benchmark Pipeline Audit

A rigorous check of existing benchmark and evaluation scripts (`backend/evaluation/`) was conducted to verify whether previous benchmarking used real production components or shortcuts.

### 3.1 Audited Findings

1. **Storage Substrates**:
   - **ChromaDB**: Live persistent store at `backend/.chromadb_bge_large`, collection `iitmrp_docling_bge_large` containing **9,776 chunks** generated from institutional annual reports. Real embeddings are `BAAI/bge-large-en-v1.5` (1024-dim, cosine).
   - **Neo4j**: Live property graph at `bolt://localhost:7687`, verified with **2,580 nodes** and **6,376 relationships** across 38 labels (Startup, Person, CoE, Grant, Patent, Table, etc.).
   - **BM25**: In-memory `SelfContainedBM25` built over the active corpus chunks.
2. **Prior Benchmark Divergences Found**:
   - In `backend/evaluation/benchmark_retrieval_ablation.py`: Synthetic retrieval queries were executed directly against vector and BM25 objects without traversing the LangGraph state machine.
   - In `backend/evaluation/verify_readiness_gate.py`: Mocked test cases were injected to verify quality gate thresholds without live LLM inference.
   - In `backend/evaluation/benchmark_finecat_vs_baseline.py`: FineCat ModernBERT NLI was evaluated in isolation on static premise/hypothesis pairs.
3. **Retrieval Fusion Finding in `workflow.py`**:
   - In `workflow.py` lines 661–666, `reciprocal_rank_fusion` is called with:
     ```python
     fused_candidates = reciprocal_rank_fusion(
         ranked_lists=[dense_chunks, bm25_chunks],
         k=60,
         weights=[1.0, 1.15] if any(c.isdigit() for c in q_text) else [1.0, 1.0],
         table_boost=has_table_intent,
     )
     ```
   - Neo4j subgraph nodes retrieved from lines 603–643 are populated into `state["subgraph"]` and passed directly to `plan.retrieved_evidence["subgraph"]`. They are **NOT** represented as candidate ranked lists inside `reciprocal_rank_fusion`.
   - This means **Mode A retrieval evaluation** of RRF currently measures Dense + BM25 fusion, while Graph evidence operates at the prompt synthesis stage.
4. **Rust Bridge Reality vs Registry**:
   - `MODULE_REGISTRY.md` states: `RustBridge`, `is_rust_available()`.
   - Actual code in `src/chunking/rust_bridge.py`: `is_rust_engine_available()`, `get_rust_backend_type()`.
   - Live execution test: `is_rust_engine_available() == True`, `get_rust_backend_type() == 'pyo3'`. Native Rust acceleration is fully operational.
5. **PostgreSQL 16 & Redis 7 Status**:
   - PostgreSQL 16.15: 6 tables active (`document_metadata`, `chat_messages`, `session_metadata`, `message_history`, `documents`, `chat_feedback`).
   - Redis 7.4.11: Port 6379 active. Cache and session methods (`get_completion`, `save_session_message`, `set_session_memory`) are implemented in `src/infrastructure/cache/redis.py`.

---

## 4. Actual Runtime Component Manifest

```json
{
  "manifest_version": "1.0.0",
  "audit_timestamp": "2026-09-24T06:21:00+05:30",
  "system": {
    "os": "Windows 11 (10.0.26100)",
    "python_version": "3.13.13",
    "python_executable": "C:\\Users\\Siddharth Tripathi\\Miniconda3\\python.exe",
    "rust_acceleration": {
      "available": true,
      "backend_type": "pyo3",
      "binary": "raise_engine.pyd / raise_engine.dll"
    }
  },
  "databases": {
    "postgresql": {
      "version": "PostgreSQL 16.15 on x86_64-pc-linux-musl (Alpine 15.2.0)",
      "host": "localhost",
      "port": 5432,
      "database": "raise_db",
      "status": "CONNECTED",
      "tables": ["document_metadata", "chat_messages", "session_metadata", "message_history", "documents", "chat_feedback"]
    },
    "redis": {
      "version": "7.4.11",
      "host": "localhost",
      "port": 6379,
      "status": "CONNECTED",
      "active_keys": 0
    },
    "neo4j": {
      "version": "5.26-community",
      "uri": "bolt://localhost:7687",
      "status": "CONNECTED",
      "node_count": 2580,
      "relationship_count": 6376,
      "labels_count": 38,
      "relationship_types_count": 15
    },
    "chromadb": {
      "persist_directory": "./.chromadb_bge_large",
      "collection_name": "iitmrp_docling_bge_large",
      "status": "CONNECTED",
      "chunk_count": 9776,
      "embedding_model": "BAAI/bge-large-en-v1.5",
      "embedding_dimension": 1024,
      "distance_metric": "cosine"
    }
  },
  "retrieval_and_reranking": {
    "dense_retriever": "ChromaDB + BAAI/bge-large-en-v1.5 (CUDA)",
    "sparse_retriever": "SelfContainedBM25 (Okapi BM25)",
    "graph_retriever": "Neo4j Cypher / Subgraph Traversal",
    "fusion": "Reciprocal Rank Fusion (k=60, table boost)",
    "reranker": "BAAI/bge-reranker-large (CrossEncoderModelSingleton, CUDA)"
  },
  "agent_orchestration": {
    "framework": "LangGraph StateGraph",
    "orchestrator_class": "AcademicGraphRAGWorkflow",
    "registered_nodes": 18,
    "reachable_nodes": 16,
    "dead_nodes": ["empty_workspace_check", "dense_vector_fallback"]
  },
  "verification_and_grounding": {
    "quality_gate": "RuntimeFaithfulnessQualityGate",
    "nli_model": "FineCat-NLI / ModernBERT-Large (dleemiller/finecat-nli-l)",
    "math_engine": "DeterministicMathEngine (IEEE-754 table coordinate cross-check)",
    "citation_validator": "CitationValidator",
    "faithfulness_threshold": 0.80,
    "max_retries": 1
  },
  "llm_inference": {
    "backend": "groq",
    "model_name": "llama-3.3-70b-versatile",
    "temperature": 0.1,
    "max_tokens": 2048,
    "vllm_local_fallback": "http://localhost:8002/v1 (container status: unhealthy)"
  },
  "active_corpus": {
    "manifest_file": "backend/data/processed/ingested_manifest.json",
    "ready_documents": [
      {
        "filename": "BRIC-Annual-Report-2025.pdf",
        "institution": "Biotechnology Research and Innovation Council (BRIC)",
        "period": "2024-25",
        "pages": 218,
        "chunks": 218,
        "entities": 1397
      },
      {
        "filename": "Annual Report 2023-24.pdf",
        "institution": "National Institute of Plant Genome Research (NIPGR)",
        "period": "2023-24",
        "pages": 165,
        "chunks": 145,
        "entities": 1488
      },
      {
        "filename": "Annual Report 2022-23.pdf",
        "institution": "National Institute of Plant Genome Research (NIPGR)",
        "period": "2022-23",
        "pages": 160,
        "chunks": 141,
        "entities": 1428
      },
      {
        "filename": "Annual Report 2021-22.pdf",
        "institution": "National Institute of Plant Genome Research (NIPGR)",
        "period": "2021-22",
        "pages": 160,
        "chunks": 45,
        "entities": 288
      }
    ]
  }
}
```

---

## 5. Audit Conclusions & Immediate Mandate

1. **No Code Modification Prior to Baseline**: The existing pipeline must remain untouched until the baseline benchmark is fully executed and persisted.
2. **Evaluation Framework Isolation**: The new evaluation framework must reside in `RAG/evaluation/` (with a symlink/import bridge to `backend/`), calling the production pipeline via `from src.retrieval.pipeline import StandaloneRAGPipeline` and `AcademicGraphRAGWorkflow`.
3. **No Mocking**: Every evaluation must execute against the live ChromaDB, live Neo4j, live BM25, and live LangGraph.
4. **Authoritative Persistence**: All evaluation runs, cases, retrieval traces, failure diagnostics, and memory tests must be written to PostgreSQL 16 under dedicated evaluation tables linked to `session_metadata`.
