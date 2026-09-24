# RAISE Module Registry & Code Architecture

**Version**: 2.5.0  
**Status**: CANONICAL & AUTHORITATIVE  
**Verification Date**: 2026-09-14  

---

## 1. Overview

This registry exhaustively maps every directory, module, class, and public function in `RAG/src/` to its operational responsibility, data contract, failure mode, and test suite.

---

## 2. Directory & Module Specifications

### A. `RAG/src/api/` (Application Programming Interface Layer)

- **`context.py`**:
  - *Purpose*: Implements `RequestContext` for unified per-request telemetry, request ID tracing, tenant headers, and client profiling.
  - *Public Symbols*: `RequestContext`, `get_request_context()`.
  - *Dependencies*: `uuid`, `fastapi.Request`.
  - *Tests*: `tests/api/test_routes.py`.

- **`dependencies.py`**:
  - *Purpose*: FastAPI dependency injection providers for database connection pools, Redis clients, Neo4j drivers, ChromaDB collections, and vLLM clients.
  - *Public Symbols*: `get_db()`, `get_redis()`, `get_neo4j()`, `get_chroma()`, `get_llm()`.
  - *Failure Modes*: Raises HTTP 503 if primary storage services are unreachable and offline fallback is disabled.
  - *Tests*: `tests/api/test_routes.py`.

- **`schemas.py`**:
  - *Purpose*: Pydantic v2 data models for request and response validation, configured with `model_config = ConfigDict(...)`.
  - *Public Symbols*: `ChatRequest`, `ChatResponse`, `ChatHistorySyncRequest`, `QueryRequest`, `QueryResponse`, `DocumentManifestItem`.
  - *Tests*: `tests/api/test_routes.py`.

- **`routers/`**:
  - `chat.py`: Main conversational endpoint supporting SSE streaming (`stream=True`) and non-streaming responses. Emits token events, citations, and subgraph payloads.
  - `query.py`: Direct GraphRAG query execution endpoint with full telemetry envelope.
  - `documents.py`: Document upload, ingestion tracking, manifest inspection, and deletion.
  - `graph.py`: Knowledge graph inspection, subgraph extraction, and Cypher script export.
  - `health.py`: Health diagnostics (`/api/health`, `/health`, `/api/dev/checkup`).
  - `sessions.py`: Session history management, drawer document binding (`GET /api/chat/sessions/{id}/drawer`).
  - `agent.py`: Agentic query execution path with dynamic tool-calling.

---

### B. `RAG/src/chunking/` (GGAHC 8-Stage Pipeline)

- **`pipeline.py`**:
  - *Purpose*: Orchestrates the 8-stage Graph-Guided Adaptive Hierarchical Chunking (GGAHC) pipeline.
  - *Public Symbols*: `AdaptiveChunkingPipeline`, `chunk_document()`.
  - *Responsibilities*: Ingests raw document markdown, dispatches to structural segmentation, detects semantic boundaries, runs entity clustering, optimizes boundaries, and outputs parent/child chunk trees.
  - *Dependencies*: `structure.py`, `semantic.py`, `extractor.py`, `graph_optimizer.py`, `hierarchical.py`, `contextualizer.py`.
  - *Tests*: `tests/test_advanced_chunking.py`.

- **`structure.py`**:
  - *Purpose*: Classifies Docling items into prose, headings, code, and explicit table/figure units.
  - *Public Symbols*: `StructuralSegmenter`, `classify_item()`.

- **`semantic.py`**:
  - *Purpose*: Evaluates semantic coherence and discourse transitions across sentences using sliding cosine distance.
  - *Public Symbols*: `SemanticBoundaryDetector`.

- **`extractor.py`**:
  - *Purpose*: Extracts entities for in-memory graph clustering.
  - *Public Symbols*: `EntityExtractor`.

- **`graph_optimizer.py`**:
  - *Purpose*: Builds temporary NetworkX graph and detects community boundaries (density, cohesion, split/merge decisions).
  - *Public Symbols*: `GraphGuidedBoundaryOptimizer`.

- **`hierarchical.py`**:
  - *Purpose*: Assembles parent macro-chunks (450-1400 words) and child retrieval chunks (100-400 words) linked by `parent_chunk_id`.
  - *Public Symbols*: `HierarchicalChunkAssembler`.

- **`contextualizer.py`**:
  - *Purpose*: Prepends section hierarchy, document title, and page metadata to chunk text.
  - *Public Symbols*: `ChunkContextualizer`.

- **`rust_bridge.py`**:
  - *Purpose*: PyO3 bridge loading `raise_engine.pyd` for SIMD-accelerated BM25, SimHash, and graph analytics with pure Python fallback.
  - *Public Symbols*: `RustBridge`, `is_rust_available()`.

---

### C. `RAG/src/features/` (Core Business Capabilities)

- **`evaluation/`**:
  - `engine.py`: Core claim extraction, verification dispatch, and `ClaimVerificationRecord` population.
  - `nli_verifier.py`: `FineCatNLIVerifier` executing ModernBERT-Large (`dleemiller/finecat-nli-l`) on `cuda:0` with Tri-State routing ($P(C) \ge 0.50$, $P(E) \ge 0.60 \land P(C) < 0.20$, else NEUTRAL).
  - `quality_gate.py`: Evaluates answer faithfulness against retrieved evidence ($\ge 0.80$ threshold). Rejects answers with unsupported assertions.
  - `question_generator.py`: Generates verification probes for testing.

- **`verification/`**:
  - `claim_verifier.py`: Binds numerical in-line citations `[N]` to verified physical document pages.
  - `math_engine.py`: `DeterministicMathEngine` computing verified IEEE-754 arithmetic over table coordinates.
  - `table_engine.py`: Searches and extracts tabular coordinate matrices.
  - `fact_engine.py`: Fact extraction and entity relationship linking.

- **`agent/`**:
  - `workflow.py`: 16-node LangGraph cyclical agent state machine.
  - `router.py`: Classifies user queries into appropriate execution paths.
  - `tools.py`: Tool definitions for vector search, Cypher execution, and math calculation.

- **`query/`**:
  - `intake.py`: `QueryIntakeEngine` executing deictic coreference resolution, out-of-scope firewall, and subquery decomposition.
  - `service.py`: Service coordinator for GraphRAG query execution.

- **`chat/` & `sessions/`**:
  - `service.py`: Conversational session persistence with dual-key schema (`text` and `content`).

- **`ingestion/`**:
  - `pipeline.py`: Master ingestion pipeline linking PDF parsers, GGAHC, ChromaDB, and Neo4j.
  - `academic_extractor.py`: 13+ academic entity extractors (Institutions, Startups, Grants, Patents).
  - `batch_ingest.py`: Idempotent batch folder ingestion worker.

---

### D. `RAG/src/infrastructure/` (Persistence & Drivers)

- **`database/postgres.py`**:
  - `PostgresManager`: Threaded connection pool managing tables (`documents`, `chat_sessions`, `chat_messages`, `audit_logs`).
- **`cache/redis.py`**:
  - `RedisManager`: Redis 7 client managing query result caching (`rag:query:*`) and sliding-window conversational memory.
- **`graph/neo4j.py` & `graph/schema.py`**:
  - `Neo4jManager`: Bolt driver connection pool executing Cypher queries with AST injection protection.
- **`vector/chroma.py`**:
  - `ChromaDBManager`: In-process / client ChromaDB wrapper managing 1024-dim dense embeddings via `BAAI/bge-large-en-v1.5`.
- **`providers/llm.py`**:
  - `vLLMClient`: HTTP client connecting to local vLLM server on port 8002 serving `Qwen2.5-14B-Instruct-GPTQ-Int4`.
- **`storage/r2.py`**:
  - `R2StorageManager`: Cloudflare R2 S3-compatible client with automatic software circuit breaker preventing billable operations.

---

### E. `RAG/src/retrieval/` (Search & Fusion)

- **`fusion.py`**:
  - `reciprocal_rank_fusion()`: Multi-substrate rank fusion ($k=60$) with dynamic tabular boosting.
  - `CrossEncoderModelSingleton`: Thread-safe GPU memory singleton caching `BAAI/bge-reranker-large`, eliminating 11.46s reload overhead.
- **`parallel_retriever.py`**:
  - `ParallelRetriever`: Async scatter-gather engine querying ChromaDB, BM25, and Neo4j concurrently.
- **`pipeline.py`**:
  - `SelfContainedBM25`: In-memory Okapi BM25 index over active document chunks.

---

### F. `RAG/src/security/` (Shield & Defenses)

- **`asgi_shield.py`**:
  - `ASGISecurityShield`: Middleware enforcing 4KB payload limits, IP firewall, and CORS headers.
- **`outbox_manager.py`**:
  - `TransactionalOutboxManager`: Reliable message publishing ensuring database writes and event streaming are atomic.
- **`ip_resolver.py`**:
  - Resolves client IP across Cloudflare `CF-Connecting-IP` and reverse proxy headers.
