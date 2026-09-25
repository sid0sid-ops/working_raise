# RAISE Architecture — Chunking, Retrieval, Embedding & Data-Layer Reference

**Document Version**: 1.6.0  
**Status**: Canonical, Evaluated & Production-Verified  
**Date**: September 25, 2026  
**Last Updated**: 2026-09-25T07:35:00+05:30  
**Scope**: End-to-End Document Lifecycle, FFI Acceleration, Multi-Engine Retrieval, Multi-Cloud Resilience, Academic Benchmark Battery, Network Security & Gateway Observability, and LangGraph Orchestration  
**Target Repository**: `semanticClimate/RAISE` (`backend/` and `RAG/`)

---

## Table of Contents
1. [Executive Summary & System Diagram](#1-executive-summary--system-diagram)
2. [Heterogeneous Tri-Engine Execution (File → Rust → Python)](#2-heterogeneous-tri-engine-execution-file--rust--python)
3. [Document Ingestion, Parsing & AST Extraction](#3-document-ingestion-parsing--ast-extraction)
4. [Chunking API & Interface Specifications](#4-chunking-api--interface-specifications)
5. [Comparative Analysis of Chunking Techniques](#5-comparative-analysis-of-chunking-techniques)
6. [Graph-Guided Adaptive Hierarchical Chunking (GGAHC) In-Depth](#6-graph-guided-adaptive-hierarchical-chunking-ggahc-in-depth)
7. [Chunk Data Models & Provenance Hierarchy](#7-chunk-data-models--provenance-hierarchy)
8. [Embedding Pipeline & Vector Management](#8-embedding-pipeline--vector-management)
9. [Vector Storage Architecture (ChromaDB HNSW)](#9-vector-storage-architecture-chromadb-hnsw)
10. [Lexical Retrieval Engine (Okapi BM25)](#10-lexical-retrieval-engine-okapi-bm25)
11. [Knowledge Graph Architecture (Neo4j vs. NetworkX)](#11-knowledge-graph-architecture-neo4j-vs-networkx)
12. [Multi-Engine Parallel Retrieval Orchestration](#12-multi-engine-parallel-retrieval-orchestration)
13. [Reciprocal Rank Fusion (RRF) & Dynamic Modality Weighting](#13-reciprocal-rank-fusion-rrf--dynamic-modality-weighting)
14. [Cross-Encoder Contextual Reranking & Threshold Cutoffs](#14-cross-encoder-contextual-reranking--threshold-cutoffs)
15. [LangGraph StateGraph Workflow Orchestrator](#15-langgraph-stategraph-workflow-orchestrator)
16. [Relational Path Critic & Text-to-Cypher Repair](#16-relational-path-critic--text-to-cypher-repair)
17. [Verification & Grounding Quality Gate Engine](#17-verification--grounding-quality-gate-engine)
18. [Relational Database Layer (PostgreSQL 16)](#18-relational-database-layer-postgresql-16)
19. [High-Performance Caching & Session State (Redis 7)](#19-high-performance-caching--session-state-redis-7)
20. [Mathematical Formulations & Decision Thresholds](#20-mathematical-formulations--decision-thresholds)
21. [End-to-End Provenance & Traceability Pipeline](#21-end-to-end-provenance--traceability-pipeline)
22. [Configuration, Environment Variables & Security Isolation](#22-configuration-environment-variables--security-isolation)
23. [Production vs. Benchmark vs. Test Architecture Matrix](#23-production-vs-benchmark-vs-test-architecture-matrix)
24. [File-Level Implementation Registry](#24-file-level-implementation-registry)
25. [Module Dependency Graph](#25-module-dependency-graph)
26. [Performance, Hardware Acceleration & Resource Profiling](#26-performance-hardware-acceleration--resource-profiling)
27. [Failure Recovery, Circuit Breakers & Multi-Cloud Resilience](#27-failure-recovery-circuit-breakers--multi-cloud-resilience)
28. [Recent Verified Pipeline Advancements & Architecture Audit](#28-recent-verified-pipeline-advancements--architecture-audit)
29. [Architecture Verification & Source Audit Ledger](#29-architecture-verification--source-audit-ledger)

---

## 1. Executive Summary & System Diagram

The **Research Assessment Intelligence & Semantic Extraction (RAISE)** system is an enterprise-grade academic research intelligence and document synthesis platform. Designed for dense institutional audits, financial schedules, and scientific literature, RAISE eliminates hallucination through strict page- and coordinate-level attribution, structural boundary preservation, and cyclical agentic verification.

### Implemented End-to-End System Flow

```mermaid
flowchart TD
    %% INGESTION & PARSING
    subgraph Ingestion_Layer["1. Ingestion & Structural Parsing"]
        PDF["PDF / Document Upload<br/>(Download/ or API)"]
        ParserRouter{"Parser Engine Router<br/>(SmartDocumentParser)"}
        Docling["Docling Parser<br/>(TableFormer + Layout AST)"]
        PyMuPDF["PyMuPDF (fitz) Parser<br/>(Fast Text & Font Spans)"]
        PDF --> ParserRouter
        ParserRouter -->|Accurate / Tables| Docling
        ParserRouter -->|Fast / Text| PyMuPDF
    end

    %% STRUCTURAL DECOMPOSITION & CHUNKING
    subgraph Chunking_Layer["2. GGAHC Chunking Engine (backend/src/chunking/)"]
        AST["Document Layout Spans & Blocks"]
        StructExtractor["Structure Extractor<br/>(StructuralUnit Generation)"]
        CandidateBuilder["Candidate Semantic Units<br/>(Heading-Scoped Groups)"]
        TempGraph["TemporaryGraphBuilder<br/>(In-Memory NetworkX Graph)"]
        RustScorer["Rust Boundary Evaluator<br/>(raise_engine / C-ABI compact buffer)"]
        Assembler["Hierarchical Assembler<br/>(Parent-Child & Propositional Units)"]
        
        Docling --> AST
        PyMuPDF --> AST
        AST --> StructExtractor --> CandidateBuilder
        CandidateBuilder --> TempGraph
        CandidateBuilder --> RustScorer
        TempGraph --> RustScorer
        RustScorer --> Assembler
    end

    %% STORAGE & INDEXING
    subgraph Storage_Layer["3. Persistent Multi-Model Storage"]
        Chroma[("ChromaDB HNSW Vector Store<br/>Collection: raise_graphrag_chunks<br/>Dim: 1024 (BGE-Large-en-v1.5)")]
        BM25Idx[("In-Memory BM25 Lexical Index<br/>(SelfContainedBM25 / raise_engine)")]
        Neo4j[("Neo4j 5.26 Property Graph<br/>(Bolt: 7687, Schema Indexes)")]
        Postgres[("PostgreSQL 16 Database<br/>(Metadata, Documents, Sessions)")]
        RedisDB[("Redis 7 Cache & Bus<br/>(Completion, Vectors, Sliding Window)")]
        
        Assembler -->|"Vectors (1024-dim)"| Chroma
        Assembler -->|"Tokenized Terms"| BM25Idx
        Assembler -->|"Entities & Relations"| Neo4j
        Assembler -->|"Doc/Chunk Records"| Postgres
        Assembler -->|"Job / Status"| RedisDB
    end

    %% RETRIEVAL & FUSION
    subgraph Retrieval_Layer["4. Parallel Multi-Engine Retrieval & Fusion"]
        QueryIn["User Query / Dispatched Turn"]
        ParallelRetriever["ParallelRetriever<br/>(ThreadPoolExecutor)"]
        VecStream["Dense Vector Search<br/>(Cosine Top-K)"]
        LexStream["Lexical BM25 Search<br/>(k1=1.5, b=0.75)"]
        GraphStream["Cypher Graph Match<br/>(Subgraphs & Neighbors)"]
        RRF["Reciprocal Rank Fusion (k=60)<br/>+ 1.35x Table Boost"]
        FilterMismatch["Entity Mismatch Filter<br/>(Institutional Disambiguation)"]
        Reranker["CrossEncoder Reranker<br/>(BAAI/bge-reranker-large)"]
        
        QueryIn --> ParallelRetriever
        ParallelRetriever --> VecStream --> RRF
        ParallelRetriever --> LexStream --> RRF
        ParallelRetriever --> GraphStream --> RRF
        RRF --> FilterMismatch --> Reranker
    end

    %% ORCHESTRATION & GENERATION
    subgraph Agentic_Layer["5. LangGraph Cyclical State Machine (16 Nodes)"]
        StateGraph["LangGraph Workflow<br/>(GraphRAGState Context Engine)"]
        PathCritic["Relational Path Critic & Cypher Repair"]
        Synthesis["Fusion & Synthesis Node<br/>(LLM Context Injection)"]
        QualityGate["Runtime Faithfulness Gate<br/>(Citation & Fact Verification)"]
        
        Reranker --> StateGraph
        StateGraph --> PathCritic
        PathCritic --> Synthesis
        Synthesis --> QualityGate
    end

    %% OUTPUT
    Output["Verified Answer Contract<br/>(Grounded Claims + Page Coordinates)"]
    QualityGate -->|Accept (Score >= 0.80)| Output
    QualityGate -->|Retry (Capped at 2)| StateGraph
```

---

## 2. Heterogeneous Tri-Engine Execution (File → Rust → Python)

RAISE executes a 3-tier heterogeneous workload partitioned across CPU, memory-mapped native routines, and GPU acceleration.

### Execution Responsibility Matrix

| Stage | Language / Engine | Implementation Module | Primary Class / Function | Input Data | Output Data |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PDF Ingestion** | Python | `src/parsers/document_parser.py` | `SmartDocumentParser.parse_document()` | Binary PDF stream or path | Extracted text blocks, coordinates, Markdown tables |
| **Layout AST** | Python / C++ | `docling` / `pypdfium2` | `DoclingParser.parse()` | PDF layout streams | Structured block tree, font metrics, table cells |
| **Candidate Chunking** | Python | `src/chunking/structure.py` | `StructureExtractor.extract_units()` | Parsed blocks & sections | `List[StructuralUnit]`, `List[CandidateUnit]` |
| **Boundary Optimization** | **Rust (Primary)** / Python (Fallback) | `raise_engine` / `rust_bridge.py` | `evaluate_boundaries_compact_rust()` | Flat float array of 8 boundary signals | Integer action vector (`SPLIT`, `MERGE`, `PRESERVE`) |
| **Community Detection** | Python | `src/chunking/graph_optimizer.py` | `TemporaryGraphBuilder.detect_communities()` | NetworkX bipartite candidate graph | `Dict[str, str]` (Node ID → Community ID) |
| **Embedding Generation** | PyTorch / CUDA | `src/infrastructure/vector/chroma.py` | `LocalVectorEngine.embed_texts()` | Raw chunk texts (`List[str]`) | 1024-dim dense float vectors |
| **Vector Indexing** | C++ / Python | `chromadb` (HNSW) | `PersistentClient.get_or_create_collection()` | Vectors + chunk metadata | Disk-backed HNSW index (`.chromadb_bge_large`) |
| **BM25 Lexical Index** | **Rust** / Python | `src/retrieval/parallel_retriever.py` | `SelfContainedBM25.search()` | Query tokens + corpus index | Ranked lexical scores ($k_1=1.5, b=0.75$) |
| **Parallel Retrieval** | Python | `src/retrieval/parallel_retriever.py` | `ParallelRetriever.retrieve_all()` | Standalone query string + filters | Multi-stream candidate lists |
| **RRF Fusion** | **Rust** / Python | `src/retrieval/fusion.py` | `reciprocal_rank_fusion()` | Modality ranked lists ($M$ streams) | Fused candidate list with $RRF$ scores |
| **Cross-Attention Rerank** | PyTorch / CUDA | `src/retrieval/fusion.py` | `CrossEncoderReranker.rerank()` | `(Query, Candidate_Snippet)` pairs | Cross-attention logit scores ($\ge \text{cutoff}$) |
| **Agentic State Graph** | Python | `src/features/agent/workflow.py` | `GraphRAGWorkflow._build_graph()` | `GraphRAGState` container | Verified Answer Contract & provenance |
| **Deduplication & Hash** | **Rust** | `raise_engine::retrieval::dedup` | `simhash_64`, `fnv1a_hash` | Text tokens / chunk bytes | 64-bit fingerprint / SHA-256 ID |

### The Native Rust Acceleration Bridge (`rust_bridge.py`)

The Python runtime interfaces with native Rust binaries compiled from `backend/rust/raise_engine/`:

```
               [Python Runtime: backend/src/chunking/rust_bridge.py]
                                         │
        ┌────────────────────────────────┴────────────────────────────────┐
        ▼                                                                 ▼
[Tier 1: PyO3 Native Module]                               [Tier 2: C-ABI Dynamic Library]
import raise_engine                                        ctypes.CDLL("raise_engine.dll")
Direct memory binding                                      Compact contiguous buffer passing
- evaluate_boundaries()                                    - evaluate_boundaries_compact_rust()
- reciprocal_rank_fusion()                                 - raise_bm25_search()
- bm25_search()                                            - raise_rank_candidates()
        │                                                                 │
        └────────────────────────────────┬────────────────────────────────┘
                                         ▼
                     [Tier 3: Pure Python Fallback]
                     NumPy / SciPy / In-Memory Heuristics
```

1. **Tier 1 (PyO3 Native Extension)**: Direct `import raise_engine`. Passes Python objects across the boundary with zero serialization overhead.
2. **Tier 2 (ctypes C-ABI)**: Dynamic library search (`raise_engine.dll` on Windows, `libraise_engine.so` on Linux, `libraise_engine.dylib` on macOS). Compact buffer passing: features are packed into a flat `c_double` array `(N, F)` and written into pre-allocated `c_int32` and `c_double` arrays, achieving a **139.8× speedup** over iterative Python logic.
3. **Tier 3 (Pure Python Fallback)**: Vectorized NumPy array operations ensuring that missing binaries do not halt execution.

---

## 3. Document Ingestion, Parsing & AST Extraction

### Ingestion Lifecycle

Document ingestion is managed through `AcademicPipelineIngestor` (`src/features/ingestion/pipeline.py`) and routed by `SmartDocumentParser` (`src/parsers/document_parser.py`):

```text
Uploaded File (.pdf, .docx, .txt)
  │
  ├── File Validation & SHA-256 Fingerprinting
  │
  ├── Engine Routing:
  │     ├── mode="expert" or engine="docling"  ──> IBM Docling (TableFormer, Layout AST)
  │     └── mode="fast" or engine="auto"      ──> PyMuPDF / fitz (High-speed layout parsing)
  │
  ├── Normalization & Hyphenation Repair (Rust de-hyphenation across line breaks)
  │
  ├── Layout Block Decomposition:
  │     ├── Title / Headings (Level 1–4)
  │     ├── Paragraph Spans (with page and bounding box coordinates)
  │     ├── Markdown Tables (with row/col spans & structural captions)
  │     └── Lists & Enumerations
  │
  └── Persistence to Download/ Directory & Manifest Registration
```

### Table Preservation Strategy

Financial schedules, KPI metrics, and governance matrices are parsed using `DoclingTablePreservingChunker` (`src/chunking/table_chunker.py`):
- Tables are extracted as whole atomic structural units.
- Columns and row headers are converted to semantic Markdown matrices.
- Tables are flagged with `is_table = True` and receive an automatic $1.35\times$ boost during Reciprocal Rank Fusion to prevent loss of numeric precision.

---

## 4. Chunking API & Interface Specifications

### Ingestion & Chunking API Route

`POST /api/upload-academic-pdfs` or `POST /api/documents/upload`
- **Controller**: `src/api/routers/documents.py`
- **Request Format**: `multipart/form-data`

```json
{
  "files": ["annual_report_2024.pdf"],
  "parser": "docling",
  "engine": "docling",
  "parse_mode": "expert",
  "extract_tables": "true",
  "full_potential": "true"
}
```

- **Response Payload Schema**:

```json
{
  "status": "success",
  "message": "Document(s) uploaded and processed successfully",
  "uploaded_count": 1,
  "document_id": "doc_a4f91b7e",
  "doc_id": "doc_a4f91b7e",
  "filename": "annual_report_2024.pdf",
  "chunks": 42,
  "library": "default",
  "reports": [
    {
      "doc_id": "doc_a4f91b7e",
      "filename": "annual_report_2024.pdf",
      "pages_processed": 18,
      "chunks_extracted": 42,
      "tables_count": 6,
      "entities_count": 84,
      "relationships_count": 112
    }
  ],
  "total_nodes": 126,
  "total_edges": 194
}
```

---

## 5. Comparative Analysis of Chunking Techniques

The `AdaptiveChunkingPipeline` (`src/chunking/pipeline.py`) implements eight distinct strategies selectable via `ChunkingConfig(strategy=...)`:

| Technique | Implementation Module | Core Mechanism | Target Content | Config Parameters | Default State |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`gga_hybrid`** | `src/chunking/pipeline.py` | Multi-signal boundary scoring + temporary NetworkX graph optimization + Rust evaluation | Dense academic reports, institutional audits | $C_{\min}=128, C_{\max}=512$, weights $\mathbf{W}$ | **Production Default** |
| **`table_preserving`** | `src/chunking/table_chunker.py` | Docling TableFormer extraction; isolates markdown tables from prose; preserves cell coordinates | Financial statements, metric matrices | `preserve_tables=True, max_table_tokens=1024` | **Production (Tables)** |
| **`hierarchical_section`** | `src/chunking/structure.py` | AST tree walk; groups paragraphs strictly under parent heading boundaries | Structured legal acts, university statutes | `heading_levels=[1,2,3], max_section_tokens=768` | Implemented (Optional) |
| **`semantic_clustering`** | `src/chunking/pipeline.py` | Embedding cosine distance across adjacent candidate units with change-point detection | Unstructured narrative essays, research whitepapers | `similarity_threshold=0.82` | Implemented (Optional) |
| **`propositional`** | `src/chunking/pipeline.py` | Atomic factual proposition extraction via LLM or rule-based dependency parsing | Knowledge-base fact compilation | `max_proposition_tokens=64` | Implemented (Granular) |
| **`sliding_window`** | `src/chunking/pipeline.py` | Token-based sliding window with fixed stride and character boundary overlap | Raw OCR text without section structure | `window_size=384, stride=128` | Implemented (Fallback) |
| **`character_recursive`** | `src/chunking/pipeline.py` | Recursive splitting on `["\n\n", "\n", " ", ""]` | Generic documentation | `chunk_size=512, chunk_overlap=64` | Implemented (Legacy) |
| **`fixed_size`** | `src/chunking/pipeline.py` | Hard token count boundary splitting | Baseline benchmarking | `token_limit=256` | Benchmark Only |

---

## 6. Graph-Guided Adaptive Hierarchical Chunking (GGAHC) In-Depth

GGAHC operates across an iterative pipeline to prevent semantic fragmentation:

```text
[Structural Units (Paragraphs, Headings, Tables)]
                    │
                    ▼
      [Candidate Semantic Units]
                    │
   ┌────────────────┴────────────────┐
   ▼                                 ▼
[Temporary NetworkX Graph]     [Adjacent Feature Extraction]
- Mentions edges               - Semantic Δ (Cosine)
- Entity-Entity relations      - Structural gap (Heading diff)
- Louvain Community Detection  - Lexical / Jaccard overlap
   │                                 │
   └────────────────┬────────────────┘
                    ▼
      [Rust Boundary Scoring Buffer]
    (Flat 8-channel feature matrix)
                    │
                    ▼
         [Boundary Decision]
         ├── SPLIT     (BoundaryScore > 0.60)
         ├── MERGE     (BoundaryScore < -0.20 & Sim >= 0.82 & Overlap >= 0.35)
         └── PRESERVE  (Otherwise)
                    │
                    ▼
     [Hard Constraint Enforcement]
  - Table boundaries cannot be merged with prose
  - Max token ceiling (512 tokens) forces SPLIT
  - Continuation headers force PRESERVE
                    │
                    ▼
[Parent Chunks (Hierarchical) & Child Chunks (Retrieval)]
```

### Boundary Scoring Equation

$$\text{Score}(A, B) = w_{\text{sem}} \Delta_{\text{sem}} + w_{\text{struct}} S_{\text{struct}} + w_{\text{top}} T_{\text{top}} - w_{\text{ent}} C_{\text{ent}} - w_{\text{rel}} C_{\text{rel}} - w_{\text{graph}} C_{\text{graph}} - w_{\text{comm}} C_{\text{comm}} - w_{\text{cross}} C_{\text{cross}}$$

- $\Delta_{\text{sem}}$: Semantic distance ($1.0 - \text{CosineSimilarity}(\mathbf{e}_A, \mathbf{e}_B)$)
- $S_{\text{struct}}$: Structural discontinuity (change in heading level or block type)
- $T_{\text{top}}$: Topic divergence penalty
- $C_{\text{ent}}$: Entity overlap continuity ($\frac{|E_A \cap E_B|}{|E_A \cup E_B|}$)
- $C_{\text{rel}}$: Shared relational predicates
- $C_{\text{graph}}$: Graph shortest path connectivity in the temporary NetworkX graph
- $C_{\text{comm}}$: Community co-membership indicator ($\delta(\text{comm}_A, \text{comm}_B)$)
- $C_{\text{cross}}$: Cross-reference resolution link

---

## 7. Chunk Data Models & Provenance Hierarchy

Defined in `src/chunking/models.py`, the core models represent units at multiple resolutions:

```
Document (document_id, filename, sha256)
  └── Section (section_id, heading, level)
       └── Parent Chunk (parent_chunk_id, ~512 tokens)
            ├── Child Chunk (chunk_id, ~128–256 tokens) ──> Indexed in Vector Store
            │    ├── Propositions (atomic assertions)
            │    └── Table / Matrix Metadata
            └── Provenance (Page, Bounding Box, Content Hash)
```

### Verified Schema: `AdaptiveChunk`

```python
@dataclass
class AdaptiveChunk:
    chunk_id: str                          # Deterministic ID: "chk_" + sha256[:12]
    document_id: str                      # Foreign key to document metadata
    parent_chunk_id: Optional[str]        # Parent context container ID
    section_id: str                       # e.g., "sec_4"
    chunk_level: str                      # "parent" | "child" | "table" | "figure"
    plain_text: str                       # Raw cleaned prose or table markdown
    contextualized_content: str           # Text enriched with document and heading context
    summary: Optional[str]                # Synthetic LLM / extractive summary
    heading: str                          # Immediate parent section title
    heading_level: int                    # 1 (Title) to 4 (Sub-subsection)
    primary_page: int                     # 1-indexed primary page
    printed_page: Optional[str]           # Original folio page string (e.g. "Page 14")
    source_pages: List[int]               # Spanned page numbers
    propositions: List[Dict[str, Any]]    # Atomic decomposed facts
    entities: List[Dict[str, Any]]        # Extracted academic entities
    relationships: List[Dict[str, Any]]   # Extracted triples
    community_ids: List[str]              # NetworkX / Neo4j Louvain community IDs
    source_block_ids: List[str]           # AST block IDs from Docling / PyMuPDF
    token_estimate: int                   # Estimated token length
    boundary_score_before: float          # Scoring diagnostic before unit
    boundary_score_after: float           # Scoring diagnostic after unit
    boundary_reasons: List[str]           # Explanation tags (e.g. "HEADING_CHANGE")
    chunking_strategy: str                # e.g., "gga_hybrid"
    is_table: bool                        # Boolean table indicator
    is_figure: bool                       # Boolean figure indicator
    tables_count: int                     # Number of structured tables enclosed
    metadata: Dict[str, Any]              # Additional system and audit metadata
```

---

## 8. Embedding Pipeline & Vector Management

### Model Architecture & Specs

- **Model Identifier**: `BAAI/bge-large-en-v1.5`
- **Output Dimensions**: $1024$ floating-point dimensions
- **Execution Target**: Auto-detecting CUDA GPU (`cuda:0`), falling back to CPU (`cpu`)
- **Embedding Cache**: Redis key `cache:vector:<sha256_of_chunk_content>` (TTL: 7200s)
- **Batch Size**: 32 chunks per forward pass

### Lifecycle States

1. **Configured**: Specified in `src/core/config.py` (`settings.vector.embedding_model = "BAAI/bge-large-en-v1.5"`).
2. **Downloaded**: Stored locally in HuggingFace cache (`~/.cache/huggingface/hub/models--BAAI--bge-large-en-v1.5`).
3. **Loaded**: Loaded on-demand into VRAM/RAM as a singleton via `LocalVectorEngine._init_db()` (`src/infrastructure/vector/chroma.py`).
4. **Active Runtime**: Executes query embeddings and indexing through `LocalVectorEngine.embed_texts()`.

---

## 9. Vector Storage Architecture (ChromaDB HNSW)

ChromaDB is the persistent local vector store (`src/infrastructure/vector/chroma.py`):
- **Persistence Path**: `.chromadb_bge_large` at repository root.
- **Tripartite Collection Naming Convention**:
  Every ChromaDB collection systematically encodes its data provenance following the canonical rule:
  $$\text{Collection Name} = \{\text{dataset\_slug}\} \_ \{\text{parser\_slug}\} \_ \{\text{model\_slug}\}$$

  | Segment | Meaning | Standard Examples |
  | :--- | :--- | :--- |
  | **`[dataset]`** | Target Dataset / Pilot Corpus | `iitmrp` (IIT Madras Research Park), `nipgr` (NIPGR Annual Reports), `bric` (BRIC Reports), `raise` (Master cross-institutional vault) |
  | **`[parser]`** | Layout & Document Parser Engine | `docling` (IBM Docling TableFormer), `pymupdf` (PyMuPDF Fast Fitz), `auto` |
  | **`[embedding_model]`** | Dense Vector Model Architecture | `bge_large` (`BAAI/bge-large-en-v1.5`, 1024-dim), `bge_m3` (1024-dim), `minilm` (384-dim), `qwen` |

  **Concrete Examples**:
  - `iitmrp_docling_bge_large`: Baseline pilot corpus of IIT Madras Research Park parsed with Docling and embedded with BGE-Large.
  - `nipgr_docling_bge_large`: National Institute of Plant Genome Research corpus parsed with Docling and embedded with BGE-Large.
  - `bric_pymupdf_minilm`: BRIC reports parsed via PyMuPDF and embedded with MiniLM.
- **Dynamic Routing**: Supported via `LocalVectorEngine.format_collection_name(dataset, parser, model)` and `.switch_collection(dataset=...)`.
- **Distance Metric**: Cosine Distance (`{"hnsw:space": "cosine"}`).
- **HNSW Parameters**: Configured for high recall under dense academic embeddings.
- **Metadata Filters**: Native Chroma `where` clauses on `document_id`, `library`, `pdf_filename`, and `chunk_type`.

---

## 10. Lexical Retrieval Engine (Okapi BM25)

The lexical search engine is implemented in `SelfContainedBM25` (`src/retrieval/parallel_retriever.py`) and backed by native Rust routines in `raise_engine::retrieval::bm25`:
- **Formula**: Standard Okapi BM25 with length normalization:
  
  $$\text{Score}(D, Q) = \sum_{q \in Q} \text{IDF}(q) \cdot \frac{f(q, D) \cdot (k_1 + 1)}{f(q, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$

- **Hyperparameters**: $k_1 = 1.5, b = 0.75$.
- **Corpus State**: Maintained in-memory from active document chunks; re-indexed upon upload.
- **Query Support**: Supports exact term matching, numeric identifiers, section titles, and grant numbers that vector search often misses.

---

## 11. Knowledge Graph Architecture (Neo4j vs. NetworkX)

RAISE utilizes two distinct graph representations for separate lifecycle stages:

```
[DOCUMENT INGESTION]                       [QUERY TIME / RETRIEVAL]
Candidate Semantic Units                   User Research Query
        │                                          │
        ▼                                          ▼
TemporaryGraphBuilder                      Neo4jDatabase (Bolt 7687)
(NetworkX In-Memory)                       (Persistent Property Graph)
- Candidate + Entity bipartite graph       - 37 Node Labels (Lean: 6 categories)
- Louvain Community Clustering             - 50 Relationship Types
- Boundary Min-Cut Resistance              - Cypher traversals: MATCH (n)-[r]-(m)
- Discarded after chunking                 - Schema-indexed lookup (<10ms)
```

### 1. Temporary NetworkX Graph (`TemporaryGraphBuilder`)
- **Scope**: Ephemeral, in-memory Python graph.
- **Purpose**: Calculates graph features ($C_{\text{ent}}, C_{\text{graph}}, C_{\text{comm}}$) used by GGAHC boundary scoring.
- **Lifecycle**: Constructed during document parsing, used for boundary decisions, then discarded.

### 2. Persistent Neo4j Property Graph (`Neo4jDatabase`)
- **Scope**: Persistent graph database running on port 7687.
- **Schema Mode**:
  - **Lean Mode (6 Core Categories)**: `Startup`, `EcosystemEnabler`, `CoE`, `Institution`, `Person`, `Metric`.
  - **Full Enterprise Mode (37 Labels, 50 Relations)**: Academic entities, departments, faculty, grants, patents, financial line-items, and citations.
- **Indexes**: `faculty_name_idx`, `chunk_id_idx`, `dept_name_idx`, `fact_id_idx`, `section_id_idx`, `org_name_idx`, `entity_name_idx`.
- **Querying**: Dynamic Cypher generation via Qwen 2.5 7B, executed via `Neo4jDatabase.query()`.

---

## 12. Multi-Engine Parallel Retrieval Orchestration

Managed by `ParallelRetriever` (`src/retrieval/parallel_retriever.py`):

```text
                       [Standalone User Query]
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
 [Dense Vector Stream]   [Lexical BM25 Stream]   [Knowledge Graph Stream]
  ChromaDB Cosine         SelfContainedBM25       Neo4j Cypher Traversal
  Top-K = 10              Top-K = 10              Top-K = 10
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  ▼
                     [Reciprocal Rank Fusion]
                      Formula: k=60, Modality Weights
                                  │
                                  ▼
                   [Institutional Entity Filter]
                                  │
                                  ▼
                    [Cross-Encoder Reranker]
                     BAAI/bge-reranker-large
                                  │
                                  ▼
                     [Top Fused Evidence Set]
```

All three streams execute concurrently using Python's `ThreadPoolExecutor`, reducing total retrieval latency to the slowest single modality (~25–45ms).

---

## 13. Reciprocal Rank Fusion (RRF) & Dynamic Modality Weighting

Implemented in `src/retrieval/fusion.py` and accelerated by Rust in `raise_engine::retrieval::rrf`:

### Mathematical Formula

$$\text{RRF}(d) = \sum_{m \in M} \frac{w_m}{k + \text{rank}_m(d)}$$

- **Smoothing Factor**: $k = 60$ (prevents outlier domination).
- **Modality Weights ($w_m$)**:
  - Default: $w_{\text{dense}} = 1.0, w_{\text{sparse}} = 1.0, w_{\text{graph}} = 1.0$.
  - Numerical / Financial Queries: $w_{\text{sparse}} = 1.15, w_{\text{dense}} = 1.0$.
- **Table Structural Boost**: If a chunk candidate contains tabular structure (`| --- |` or `is_table = True`), its score increment receives an automatic $1.35\times$ multiplier:
  
  $$\text{Increment}_{\text{table}} = \left(\frac{w_m}{k + \text{rank}_m(d)}\right) \times 1.35$$

- **Deduplication & Tie-Handling**: Chunks are deduplicated by unique `chunk_id`. Identical RRF scores break ties by primary page number and lexical length.

---

## 14. Cross-Encoder Contextual Reranking & Threshold Cutoffs

Implemented in `CrossEncoderReranker` (`src/retrieval/fusion.py`):
- **Model**: `BAAI/bge-reranker-large` (lazy-loaded singleton in GPU VRAM).
- **Fallback**: `cross-encoder/ms-marco-MiniLM-L-6-v2` or heuristic token-level cross-attention.
- **Input**: Concatenated query and candidate text snippets (up to 3000 characters).
- **Sub-Query Max-Pooling**: For decomposed queries $\{Q_{\text{raw}}, Q_{\text{sub}_1}, Q_{\text{sub}_2}\}$:
  
  $$\text{Score}(c) = \max\left(\text{CrossEncoder}(Q_{\text{raw}}, c), \max_i \text{CrossEncoder}(Q_{\text{sub}_i}, c)\right)$$

### Strict Cutoff Mechanism

```python
best_score = reranked[0]["cross_encoder_score"]
is_logits = (best_score > 1.0 or best_score < -1.0)
score_cutoff = (best_score - 7.5) if is_logits else 0.15
filtered_by_score = [c for c in reranked if c["cross_encoder_score"] >= score_cutoff]
top_candidates = (filtered_by_score if filtered_by_score else reranked)[:top_n]
```

This prevents low-relevance peripheral chunks from entering the LLM generation context window.

---

## 15. LangGraph StateGraph Workflow Orchestrator

The query lifecycle is orchestrated by a 16-node cyclical `StateGraph` in `src/features/agent/workflow.py`:

```mermaid
flowchart TD
    START([START]) --> QI[query_intake]
    
    QI -->|bypass: greeting/help| GCR[general_chat_responder]
    QI -->|empty_workspace: 0 PDFs| EWR[empty_workspace_responder]
    QI -->|proceed: academic Q| CR[classification_and_routing]
    
    GCR --> END_NODE([END])
    EWR --> END_NODE
    
    CR -->|global_community| CSR[community_summary_retriever]
    CR -->|local_cypher| TCG[text_to_cypher_generator]
    CR -->|hybrid_vector| HR[hybrid_retriever]
    
    CSR --> FRS[fusion_and_response_synthesis]
    
    TCG --> CEV[cypher_executor_and_validator]
    CEV -->|success| RPC[relational_path_critic]
    CEV -->|repair| CRep[cypher_repair]
    CEV -->|fallback| HR
    
    CRep -->|retry| CEV
    CRep -->|fallback| HR
    
    RPC --> HR
    HR --> FRS
    
    FRS --> RFG[runtime_faithfulness_gate]
    
    RFG -->|accept: score >= 0.80| CV[citation_validation]
    RFG -->|retry: retries < 2| QR[query_reformulation]
    RFG -->|unable_to_verify| UR[unverified_responder]
    
    QR --> SR[secondary_retrieval]
    SR --> FRS
    
    CV --> END_NODE
    UR --> END_NODE
```

### Complete 16-Node Registry

| # | Node Name | Implementation Method | Purpose |
| :- | :--- | :--- | :--- |
| 1 | `query_intake` | `_query_intake_node` | Coreference resolution, session context binding, empty workspace detection |
| 2 | `general_chat_responder` | `_general_chat_responder_node` | Bypasses database retrieval for non-retrieval conversational greetings |
| 3 | `empty_workspace_check` | Registered routing check | Structural gate preventing LLM hallucination when 0 documents exist |
| 4 | `empty_workspace_responder`| `_empty_workspace_responder_node` | Emits polite refusal requesting PDF upload without consuming LLM tokens |
| 5 | `classification_and_routing`| `_classification_and_routing_node`| Classifies query intent: `GLOBAL_COMMUNITY`, `LOCAL_GRAPH_CYPHER`, or `HYBRID_VECTOR` |
| 6 | `community_summary_retriever`| `_community_summary_retriever_node`| Retrieves high-level global community summaries for aggregate queries |
| 7 | `text_to_cypher_generator` | `_text_to_cypher_generator_node` | Translates natural language questions into structured Neo4j Cypher queries |
| 8 | `cypher_executor_and_validator`| `_cypher_executor_and_validator_node`| Executes Cypher against Neo4j; inspects result records and syntax errors |
| 9 | `cypher_repair` | `_cypher_repair_node` | Repairs malformed Cypher syntax or schema errors using schema reflection |
| 10 | `relational_path_critic` | `_relational_path_critic_node` | Validates multi-hop graph paths and expands missing relational contexts |
| 11 | `hybrid_retriever` | `_hybrid_retriever_node` | Executes parallel Vector + BM25 + Subgraph retrieval with RRF |
| 12 | `dense_vector_fallback` | `_hybrid_retriever_node` | Fallback retrieval route if Cypher or graph execution fails |
| 13 | `fusion_and_response_synthesis`| `_fusion_and_response_synthesis_node`| Injects retrieved chunks into LLM prompt and synthesizes grounded answer |
| 14 | `runtime_faithfulness_gate`| `_runtime_faithfulness_gate_node`| Evaluates claim-level NLI faithfulness, numerical matches, and citations |
| 15 | `query_reformulation` | `_query_reformulation_node` | Rewrites ambiguous queries upon quality gate failure |
| 16 | `secondary_retrieval` | `_secondary_retrieval_node` | Executes targeted secondary retrieval loop over reformulated query |
| 17 | `citation_validation` | `_citation_validation_node` | Validates that all page citations match verified source chunks |
| 18 | `unverified_responder` | `_unverified_responder_node` | Refuses to present ungrounded answers if quality gate fails after 2 retries |

---

## 16. Relational Path Critic & Text-to-Cypher Repair

When queries target structural entity relationships (e.g., *"Which startups incubated at IITM received BIRAC grants?"*), the pipeline activates the Cypher execution cycle:
1. **Schema Injection**: Qwen 2.5 is prompted with the verified Neo4j schema labels and relation types.
2. **Syntax Validation**: Before execution, generated Cypher is validated against read-only constraints (`DISALLOW: CREATE, DELETE, SET, MERGE, DROP`).
3. **Execution & Repair**: If Neo4j raises a syntax or missing-property error, `cypher_repair` feeds the stack trace back to the LLM to generate a corrected query. This loop is capped at **2 attempts**.
4. **Relational Path Critic**: Inspects the returned subgraph. If traversal hit a dead end, it pulls 1-hop neighbor chunks to ensure the synthesis prompt contains full semantic context.

---

## 17. Verification & Grounding Quality Gate Engine

Implemented in `src/features/evaluation/engine.py` and `src/features/verification/claim_verifier.py`:
- **Claim Decomposition**: Synthesized LLM answers are parsed into atomic claim sentences.
- **NLI Faithfulness Verification**: Each claim is evaluated against source chunks using a 4-tier grounding cascade:
  1. Local FineCat-NLI safetensors model.
  2. Cross-encoder NLI inference.
  3. Token-level bidirectional entailment.
  4. Heuristic lexical overlap fallback.
- **Numerical & Table Integrity**: Numbers, percentages, and financial values are cross-checked against raw table cells via `TableIntegrityEngine`.
- **Quality Gate Threshold**: An answer must achieve $\ge 80\%$ verified claims ($\text{FaithfulnessScore} \ge 0.80$) to pass to `citation_validation`. If the score is $<0.80$, the state machine branches to `query_reformulation` (up to 2 retries). If still unverified, it safely terminates at `unverified_responder`.

---

## 18. Relational Database Layer (PostgreSQL 16)

Managed by `PostgresManager` (`src/infrastructure/database/postgres.py`) with connection pooling via `psycopg2.pool.ThreadedConnectionPool`:

### Verified Database Schema

```sql
-- 1. Persistent Chat Messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    mode VARCHAR(20) DEFAULT 'fast',
    sources JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id);

-- 2. Document Library Metadata
CREATE TABLE IF NOT EXISTS document_metadata (
    id VARCHAR(100) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    library VARCHAR(100) DEFAULT 'default',
    chunks_count INT DEFAULT 0,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_protected BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT TRUE,
    owner VARCHAR(100) DEFAULT 'user'
);
CREATE INDEX IF NOT EXISTS idx_doc_library ON document_metadata(library);

-- 3. Session Metadata & History
CREATE TABLE IF NOT EXISTS session_metadata (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    attached_docs JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS message_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES session_metadata(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_msg_session ON message_history(session_id);

-- 4. Document Ingestion Tracking
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(100) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'processing',
    phase VARCHAR(50) DEFAULT 'uploading',
    progress_percent INT DEFAULT 0,
    detail TEXT DEFAULT '',
    error_message TEXT DEFAULT NULL,
    pages_processed INT DEFAULT 0,
    chunks_extracted INT DEFAULT 0,
    file_size_bytes BIGINT DEFAULT 0,
    library VARCHAR(100) DEFAULT 'default',
    is_protected BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT TRUE,
    owner VARCHAR(100) DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

-- 5. User Feedback
CREATE TABLE IF NOT EXISTS chat_feedback (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    query TEXT,
    rating VARCHAR(50) NOT NULL,
    reason TEXT,
    message_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_feedback_session ON chat_feedback(session_id);
```

---

## 19. High-Performance Caching & Session State (Redis 7)

Managed by `RedisCacheManager` (`src/infrastructure/cache/redis.py`):

### Redis Key Patterns & Functions

| Key Pattern | Data Structure | TTL | Purpose |
| :--- | :--- | :--- | :--- |
| `cache:completion:{mode}:{lib}:{q_hash}` | String (JSON) | 86,400s (24h) | Sub-millisecond exact query answer cache |
| `cache:vector:{vector_id}` | String (Float JSON) | 7,200s (2h) | Intermediate embedding vector cache |
| `cache:semantic:keys` | Set | 86,400s (24h) | Lookup set for semantic similarity cache matching |
| `rate:bucket:{ip_address}` | String (Counter) | 60s | Token-bucket API rate limiting (60 requests/min) |
| `job:status:{job_id}` | Hash | 3,600s (1h) | Asynchronous PDF ingestion status and progress % |
| `session:{session_id}:messages` | List (Bounded) | 86,400s (24h) | Sliding-window conversational turn history (capped at 20) |
| `session:{session_id}:memory` | Hash | 86,400s (24h) | Extracted session entity facts (`user_name`, `topic`) |

---

## 20. Mathematical Formulations & Decision Thresholds

### 1. GGAHC Decision Rule
$$\text{Action} = \begin{cases} 
\text{SPLIT}, & \text{if } \text{BoundaryScore} > 0.60 \\
\text{MERGE}, & \text{if } \text{BoundaryScore} < -0.20 \land \text{CosineSim} \ge 0.82 \land \text{EntityOverlap} \ge 0.35 \\
\text{PRESERVE}, & \text{otherwise}
\end{cases}$$

### 2. Reciprocal Rank Fusion
$$\text{RRF}(d) = \sum_{m \in \{\text{vec}, \text{bm25}, \text{graph}\}} \frac{w_m}{60 + \text{rank}_m(d)}$$

### 3. Cross-Encoder Pruning Cutoff
$$\text{Threshold} = \begin{cases} 
\text{BestScore} - 7.5, & \text{if } |\text{BestScore}| > 1.0 \text{ (Logits mode)} \\
0.15, & \text{if } \text{BestScore} \in [0.0, 1.0] \text{ (Probabilistic mode)}
\end{cases}$$

---

## 21. End-to-End Provenance & Traceability Pipeline

RAISE maintains full provenance tracing from the final generated claim back to the physical source file:

```
[Generated Answer Claim]
          │
          ▼
   [VerifiedClaim]
   - sentence: "IIT Madras Research Park filed 142 patents in FY24."
   - citation_id: "[Doc 1, p. 14]"
          │
          ▼
    [AdaptiveChunk]
   - chunk_id: "chk_7d3a9f018e22"
   - content_hash: "sha256:4b22c7..."
          │
          ▼
    [StructuralUnit]
   - source_block_ids: ["blk_0042", "blk_0043"]
   - coordinates: {"x0": 72.0, "y0": 245.5, "x1": 520.0, "y1": 380.2}
          │
          ▼
  [Physical PDF File]
   - filename: "IITM_Research_Park_Annual_Report_2024.pdf"
   - primary_page: 14
   - section_hierarchy: ["Financial Highlights", "Intellectual Property"]
```

---

## 22. Configuration, Environment Variables & Security Isolation

Configuration is managed via Pydantic in `src/core/config.py`. All credentials must be supplied via `.env` or system environment variables:

| Variable | Default Value | Production Role | Secret Handling |
| :--- | :--- | :--- | :--- |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host | Public |
| `POSTGRES_PORT` | `5432` | PostgreSQL port | Public |
| `POSTGRES_DB` | `raise_db` | PostgreSQL database name | Public |
| `POSTGRES_USER` | `raise_user` | PostgreSQL user | Public |
| `POSTGRES_PASSWORD` | `<REDACTED>` | PostgreSQL password | **Secret** |
| `REDIS_HOST` | `localhost` | Redis server host | Public |
| `REDIS_PORT` | `6379` | Redis server port | Public |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt protocol URI | Public |
| `NEO4J_USER` | `neo4j` | Neo4j auth username | Public |
| `NEO4J_PASSWORD` | `<REDACTED>` | Neo4j auth password | **Secret** |
| `GROQ_API_KEY` | `<REDACTED>` | Cloud LLM fallback API key | **Secret** |
| `GEMINI_API_KEY` | `<REDACTED>` | Cloud LLM fallback API key | **Secret** |
| `HF_TOKEN` | `<REDACTED>` | HuggingFace Hub model access | **Secret** |

---

## 23. Production vs. Benchmark vs. Test Architecture Matrix

| Component | Production Architecture | Benchmark Suite (`evaluation/`) | Unit Tests (`tests/`) | Experimental |
| :--- | :--- | :--- | :--- | :--- |
| **Chunking Strategy** | `gga_hybrid` + `table_preserving` | `fixed_size` (256/512) vs `gga_hybrid` | Synthetic strings / single pages | `semantic_clustering` |
| **Rust Engine** | `raise_engine` (PyO3 / C-ABI) | Throughput vs pure Python | Mocked fallback verified | SIMD vectorization |
| **Vector Store** | ChromaDB (`.chromadb_bge_large`) | Isolated test collection | In-memory Chroma client | Qdrant / Milvus |
| **Embedding Model** | `BAAI/bge-large-en-v1.5` (1024) | `all-MiniLM-L6-v2` | Synthetic embeddings | `Qwen3-Embedding-4B` |
| **BM25 Index** | `SelfContainedBM25` (Rust backed) | Memory corpus ranking | Fixture documents | Tantivy |
| **Graph Store** | Neo4j 5.26 (Bolt) | Neo4j vs NetworkX speed | Mocked driver / In-memory | Amazon Neptune |
| **Temporary Graph** | NetworkX (in-memory for GGAHC) | NetworkX Louvain | NetworkX connected components | CuGraph |
| **Reranker** | `BAAI/bge-reranker-large` | bge-reranker vs MiniLM | Heuristic cross-attention | Cohere Rerank API |
| **Agent Workflow** | 16-node LangGraph `StateGraph` | Linear RAG baseline | Single-node isolation tests | Autogen multi-agent |
| **Inference Backend**| Local vLLM (Qwen 2.5 14B) | vLLM throughput benchmark | Mocked LLM responses | DeepSeek-R1 local |

---

## 24. File-Level Implementation Registry

```text
backend/src/
├── chunking/
│   ├── config.py             # ChunkingConfig dataclass (weights, token bounds)
│   ├── contextualizer.py     # Heading and document context prepending
│   ├── graph_optimizer.py    # TemporaryGraphBuilder (NetworkX Louvain clustering)
│   ├── models.py             # AdaptiveChunk, StructuralUnit, BoundaryExplanation
│   ├── pipeline.py           # AdaptiveChunkingPipeline (GGAHC coordinator)
│   ├── rust_bridge.py        # Python-Rust FFI bridge (PyO3, ctypes, compact buffer)
│   ├── structure.py          # AST extraction and candidate grouping
│   └── table_chunker.py      # DoclingTablePreservingChunker (Markdown tables)
├── retrieval/
│   ├── chain_gate.py         # Multi-hop retrieval routing gate
│   ├── fusion.py             # reciprocal_rank_fusion, CrossEncoderReranker
│   ├── parallel_retriever.py # ParallelRetriever, SelfContainedBM25
│   └── pipeline.py           # StandaloneRAGPipeline integration
├── features/
│   ├── agent/
│   │   ├── router.py         # Query routing & classification
│   │   ├── tools.py          # Vector and graph agent tools
│   │   └── workflow.py       # LangGraph 16-node StateGraph orchestrator
│   ├── evaluation/
│   │   ├── engine.py         # RuntimeFaithfulnessQualityGate
│   │   └── quality_gate.py   # Quality gate decision evaluator
│   └── verification/
│       ├── claim_verifier.py # Claim decomposition, AnswerContract
│       ├── fact_engine.py    # Fact verification engine
│       ├── math_engine.py    # Numerical calculation validator
│       └── table_engine.py   # Table coordinate cell validator
└── infrastructure/
    ├── cache/
    │   └── redis.py          # RedisCacheManager (completions, vectors, rate limits)
    ├── database/
    │   └── postgres.py       # PostgresManager (sessions, documents, history)
    ├── graph/
    │   ├── neo4j.py          # Neo4jDatabase (Cypher execution, connection pooling)
    │   └── schema.py         # 37 node labels, 50 relations
    └── vector/
        └── chroma.py         # LocalVectorEngine (ChromaDB HNSW, BGE-Large)
```

---

## 25. Module Dependency Graph

```mermaid
flowchart TD
    API["FastAPI Routers<br/>(documents.py, query.py, search.py)"]
    Workflow["LangGraph StateMachine<br/>(features/agent/workflow.py)"]
    ParallelRet["ParallelRetriever<br/>(retrieval/parallel_retriever.py)"]
    Fusion["RRF & CrossEncoder<br/>(retrieval/fusion.py)"]
    RustBridge["Rust Bridge (FFI)<br/>(chunking/rust_bridge.py)"]
    RustEngine["Native Rust Engine<br/>(raise_engine.dll / .so)"]
    ChunkPipeline["AdaptiveChunkingPipeline<br/>(chunking/pipeline.py)"]
    Chroma["ChromaDB Engine<br/>(infrastructure/vector/chroma.py)"]
    Neo4j["Neo4j Engine<br/>(infrastructure/graph/neo4j.py)"]
    Postgres["PostgreSQL Manager<br/>(infrastructure/database/postgres.py)"]
    Redis["Redis Cache Manager<br/>(infrastructure/cache/redis.py)"]
    QualityGate["Quality Gate & Verifier<br/>(features/evaluation/engine.py)"]

    API --> Workflow
    API --> ChunkPipeline
    API --> Postgres
    API --> Redis
    
    ChunkPipeline --> RustBridge
    RustBridge --> RustEngine
    ChunkPipeline --> Chroma
    ChunkPipeline --> Neo4j
    
    Workflow --> ParallelRet
    ParallelRet --> Chroma
    ParallelRet --> Neo4j
    ParallelRet --> Fusion
    Fusion --> RustBridge
    
    Workflow --> QualityGate
```

---

## 26. Performance, Hardware Acceleration & Resource Profiling

| Subsystem | Primary Resource | Acceleration Method | Latency Target | Memory Footprint |
| :--- | :--- | :--- | :--- | :--- |
| **Docling PDF Parsing** | CPU / Multi-Core | PyPdfium2 / ThreadPool | ~400ms / page | ~350MB RAM |
| **GGAHC Boundary Scoring** | CPU / RAM | Native Rust SIMD (PyO3) | **<1.2ms** / boundary | ~15MB RAM |
| **BGE-Large Embeddings** | GPU (VRAM) | CUDA FP16 batched forward pass | ~12ms / batch (32) | ~1.3GB VRAM |
| **ChromaDB HNSW Search** | CPU / RAM | C++ HNSW graph traversal | **<8ms** (top-10) | ~250MB RAM |
| **Okapi BM25 Retrieval** | CPU / RAM | Rust inverted index search | **<2.5ms** | ~40MB RAM |
| **Neo4j Cypher Traversal**| CPU / RAM | Schema B-Tree / Bolt binary protocol | **<12ms** | External container |
| **Reciprocal Rank Fusion**| CPU / RAM | Rust QuickSelect $O(N)$ top-k | **<0.8ms** | <1MB RAM |
| **Cross-Encoder Rerank** | GPU (VRAM) | CUDA FP16 cross-attention | ~35ms (10 pairs) | ~1.8GB VRAM |
| **vLLM Synthesis** | GPU (VRAM) | PagedAttention / GPTQ 4-bit | ~45 tokens/sec | ~9.5GB VRAM |

---

## 27. Failure Recovery, Circuit Breakers & Multi-Cloud Resilience

The RAISE architecture implements multi-layered circuit breakers, cascading failovers, and robust cloud integration options across all core data and compute substrates:

```mermaid
flowchart TD
    subgraph ComputeFailover["1. LLM & Reasoning Multi-Cloud Cascades"]
        LocalLLM["Local vLLM / Ollama (Qwen 2.5 14B, RTX 3090 24GB)"]
        Groq["Cloud Tier 1: Groq LPU (Llama 3.3 70B / Qwen 2.5 27B, <1s TTFT)"]
        Mistral["Cloud Tier 2: Mistral AI (open-mistral-nemo / codestral-latest)"]
        NIM["Cloud Tier 3: NVIDIA NIM (Llama 3.2 11B Vision, 1,000 Free Credits)"]
        Cohere["Cloud Tier 4: Cohere Command (Command-R+ 08-2024, Free Dev Tier)"]
        Gemini["Cloud Tier 5: Google Gemini API (Gemini 2.0 Flash, 1M+ Context)"]
        PaidGate{"User Funded Key Configured?"}
        Vercel["Gateway Tier: Vercel AI Gateway (TypeSafe Jev / Claude / GPT-4o)"]
        DeepSeek["Paid Tier 1: DeepSeek Cloud (V3/R1, Prepaid Only - No Free Tier)"]
        OpenRouter["Paid Tier 2: OpenRouter Gateway (Claude 3.5 Sonnet / Mistral Large)"]
        Universal["Custom Tier: Universal Cloud (Together / Fireworks / OpenAI)"]
        SafeRefusal["Safe Fallback: unverified_responder (Safe Refusal, Zero Hallucination)"]

        LocalLLM -->|CUDA OOM / Local Offline| Groq
        Groq -->|429 Rate Limit (60s Cooldown)| Mistral
        Mistral -->|429 Rate Limit| NIM
        NIM -->|429 Rate Limit| Cohere
        Cohere -->|429 Rate Limit| Gemini
        Gemini -->|All Free Cloud Exhausted| PaidGate
        PaidGate -->|Key Configured & Funded| Vercel
        Vercel -->|Missing Card / Billing 403| DeepSeek
        DeepSeek -->|402 Unfunded / Disabled| OpenRouter
        OpenRouter -->|Credit Exhausted| Universal
        Universal -->|All Exhausted| SafeRefusal
        PaidGate -->|No Paid Keys| SafeRefusal
    end

    subgraph GraphFailover["2. Knowledge Graph Cloud Resilience"]
        LocalNeo4j["Local Neo4j 5.26 (bolt://localhost:7687)"]
        AuraDB["Neo4j AuraDB Cloud (Enterprise Managed Cluster)"]
        Memgraph["Memgraph Cloud / AWS Neptune (openCypher)"]
        NetX["In-Memory NetworkX (Temporary Bipartite Graph)"]
        HybridRetriever["hybrid_retriever (StateGraph Node)"]

        LocalNeo4j -->|Socket Timeout >50ms| AuraDB
        AuraDB -->|Auth / Cloud Disconnect| Memgraph
        Memgraph -->|Unavailable| NetX
        NetX -->|Fallback Graph Traversal| HybridRetriever
    end

    subgraph StorageFailover["3. Vector & Document Object Storage"]
        LocalChroma["Local ChromaDB HNSW (.chromadb_bge_large)"]
        R2["Cloudflare R2 Object Storage (Zero-Egress S3 Bucket)"]
        S3["AWS S3 / GCP Storage (Cold Archive Backup)"]
        Qdrant["Qdrant Cloud / Pinecone (Distributed Vector Clustering)"]

        LocalChroma -->|Index Corruption / Rehydrate| R2
        R2 -->|Multi-Cloud Sync| S3
        LocalChroma -->|Enterprise Scale-Out| Qdrant
    end

    subgraph MemoryFailover["4. Relational & Ephemeral Memory"]
        LocalPG["Local PostgreSQL 16 (localhost:5432)"]
        Supabase["Supabase / Neon Serverless Postgres (SSL Pooling)"]
        LocalRedis["Local Redis 7 (localhost:6379)"]
        Upstash["Upstash Serverless Redis / AWS ElastiCache"]
        DictMem["In-Memory LRU Dict Cache (Thread-Safe Fallback)"]

        LocalPG -->|Connection Down| Supabase
        LocalRedis -->|Connection Down| Upstash
        Upstash -->|Network Partition| DictMem
    end
```

### Detailed Subsystem Circuit Breakers:

#### 1. Multi-Cloud LLM Inference & Agentic Synthesis
- **Primary On-Prem / Local**: Local vLLM (`Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4` on CUDA `localhost:8002/v1`) or Ollama (`localhost:11434/v1`) running on a single NVIDIA RTX 3090 GPU (24GB VRAM).
- **Cloud Tier 1 (Ultra-Low Latency LPU)**: **Groq Cloud** (`llama-3.3-70b-versatile`, `qwen/qwen3.8-27b`) — 250+ tokens/sec, sub-second TTFT, primary failover for high-throughput evaluation, query intake, and production streaming.
- **Cloud Tier 2 (European Sovereign High-Efficiency Models)**: **Mistral AI** (`open-mistral-nemo`, `open-mistral-7b`, `codestral-latest`) — native multi-model support, intra-model automatic fallbacks, and high-efficiency reasoning.
- **Cloud Tier 3 (Developer Vision & Structured Extraction)**: **NVIDIA NIM Cloud** (`meta/llama-3.2-11b-vision-instruct`, `meta/llama-3.3-70b-instruct`) — 1,000 developer free credits, enterprise-grade structured JSON extraction, and high-fidelity vision parsing.
- **Cloud Tier 4 (Neural Cross-Attention & Citation Reasoning)**: **Cohere Command** (`command-r-plus-08-2024`, `rerank-v3.5`) — generous free evaluation tier, automated reranking fallback, and citation-native multi-hop synthesis.
- **Cloud Tier 5 (Long-Context & Document Synthesis)**: **Google Gemini API** (`gemini-2.0-flash`, `gemini-2.5-flash`) — native 1M+ token context windows for full-document cross-audit synthesis with free-tier quota protection.
- **Universal Cloud & Account-Gated Provider Adapters (Dynamic Gating)**:
  - **Vercel AI Gateway & TypeSafe Jev** (`typesafe-ai/jev`): High-speed decision model routing and multi-provider gateway. Gated with a billing-restricted circuit breaker: if credit card is unconfigured (`HTTP 403`), it automatically disables itself without interrupting the pipeline.
  - **Universal Cloud Adapter (`UniversalCloudProvider`)**: Pluggable OpenAI-compatible adapter supporting ANY arbitrary endpoint (Together AI, Fireworks AI, Perplexity, OpenAI, Anyscale) via `CUSTOM_LLM_BASE_URL` and `CUSTOM_LLM_API_KEY`.
  - **DeepSeek Cloud** (`deepseek-chat`, `deepseek-reasoner`): **No permanent free tier**. Promotional token credits expire quickly, resulting in `HTTP 402 Payment Required`. Gated in `ProviderRouter` so it is permanently bypassed unless the operator configures a funded key.
  - **OpenRouter AI Gateway** (`anthropic/claude-3.5-sonnet`, `mistralai/mistral-large-2`): Dynamic multi-provider aggregator, activated only when funded account credits are available.
- **Circuit Breaker Policies**:
  - **HTTP 429 (`RATE_LIMITED`) Circuit Breaker**: Automatically places any rate-limited provider into a 60-second cooldown timer. During this window, all routing requests dynamically bypass the cooling-down provider and target the next available healthy cloud candidate without dropping queries.
  - **HTTP 402/403 (`BILLING_RESTRICTED`) Circuit Breaker**: Permanently disables unfunded paid providers (`self.disabled_providers.add(cand)`) for the lifetime of the session to prevent repeated failed network roundtrips.
  - **Dynamic Provider Registry**: Exposed via `GET /api/system/dynamic-llms` and `GET /api/system/config`. Surfaces actual active providers dynamically instead of hardcoding model names.
  - **Safe Refusal Guarantee**: If all external providers are exhausted, the pipeline automatically routes to `unverified_responder` to emit a polite, evidence-grounded refusal rather than hallucinating unsupported claims.

#### 2. Knowledge Graph Cloud Options & Dual-Channel Resilience
- **Cloud Primary (Production Verified)**: **Neo4j AuraDB Cloud** (`neo4j+s://7639347a.databases.neo4j.io` on database `7639347a`) — automated cloud clustering, multi-region replication, and zero-maintenance managed Neo4j holding 2,580 institutional entity and chunk nodes.
- **Dual-Protocol Cloud Transport**:
  1. **Primary High-Speed Binary (Bolt `neo4j+s://`)**: Adaptive 15.0s connection and acquisition timeouts with connection pooling (up to 50 pooled sessions) and keep-alive heartbeats to handle cloud latency across geographical regions.
  2. **Zero-Port-Block Fallback (HTTP Query v2 API `https://.../db/{database}/query/v2`)**: Fully serverless REST API transport over standard HTTPS port 443. If corporate firewalls, proxies, or network policies block raw TCP port 7687, `Neo4jDatabase` automatically falls back to the HTTP Query v2 API without dropping graph queries or throwing connection errors.
- **Cloud Secondary / Alternative**: **AWS Neptune / Memgraph Cloud** — high-performance openCypher graph streaming.
- **Local Fallback**: Local Neo4j 5.26 (`bolt://localhost:7687`).
- **In-Memory Fallback**: Ephemeral in-memory NetworkX graph (`TemporaryGraphBuilder` with Louvain community detection).
- **Circuit Breaker**: Adaptive socket probe (3.0s cloud / 0.5s local). If Neo4j AuraDB Bolt is unreachable, activates HTTP Query v2; if both cloud endpoints are unavailable, activates in-memory `TemporaryGraphBuilder` and seamlessly routes query traversal to `hybrid_retriever` without crashing or skipping evidence.

#### 3. Vector Database & Object Storage Cloud Options
- **Primary**: Local ChromaDB HNSW (`.chromadb_bge_large` on disk).
- **Cloud Tier 1**: **Cloudflare R2 Object Storage** — zero-egress fee encrypted object bucket (`s3.r2.cloudflarestorage.com`) for persistent PDF replication and vector backup snapshots.
- **Cloud Tier 2**: **AWS S3 / Google Cloud Storage** — enterprise cold-storage document archive and compliance logs.
- **Cloud Tier 3**: **Qdrant Cloud / Pinecone Serverless** — distributed multi-tenant vector clustering with cosine distance and namespace partitioning.
- **Tripartite Naming Standard**: `{dataset_slug}_{parser_slug}_{model_slug}` enforced across local ChromaDB and cloud replicas.

#### 4. Relational Database & Distributed Memory Cloud Options
- **Primary (Relational)**: Local PostgreSQL 16 (`localhost:5432`).
- **Cloud Tier 1 (Postgres)**: **Supabase / Neon Serverless Postgres** — auto-scaling branching, connection pooling (PgBouncer), SSL-encrypted session persistence.
- **Primary (Memory)**: Local Redis 7 (`localhost:6379`).
- **Cloud Tier 1 (Redis)**: **Upstash Serverless Redis / AWS ElastiCache** — REST-based serverless Redis with sub-millisecond edge caching and sliding-window memory persistence.
- **Circuit Breaker**: Socket timeout at 50ms falls back to thread-safe Python in-memory LRU dict cache and ephemeral mock registry.

#### 5. Native Rust Acceleration Library Missing
- `rust_bridge.py` catches `ImportError` / `OSError`.
- Cascades seamlessly: Tier 1 (PyO3) ──> Tier 2 (ctypes C-ABI) ──> Tier 3 (Pure Python).

---

## 28. Recent Verified Pipeline Advancements & Architecture Audit

The RAISE pipeline was recently subjected to a rigorous scientific evaluation battery across both Mode A (Retrieval & Cross-Encoder) and Mode B (16-Node End-to-End Cyclical LangGraph). The table below records the verified enhancements:

| Innovation / Fix | Module Location | Mechanism | Measured Impact |
| :--- | :--- | :--- | :--- |
| **Line-by-Line Financial Table OCR Normalization** | `src/features/evaluation/engine.py`, `src/features/verification/claim_verifier.py` | Normalizes Indian comma groupings (`1,23,92.56,765` -> `1,23,92,56,765`), parses tables line-by-line to prevent multiline row fusion (fixed 18-digit token corruption), and fixes OCR letter-digit confusion (`S->5`, `O->0`, `I->1`) | **Eliminated false quality gate rejections** on institutional balance sheets and financial statements |
| **Pairwise Arithmetic Derivation Engine** | `src/features/evaluation/engine.py` | Automatically recognizes and verifies mathematical difference and delta claims derived from verified table figures ($|val - (e_i \pm e_j)| < 0.05$) | **Surpassed accuracy target**: Year-over-year comparative claims pass without hallucination |
| **Automated Rate-Limit Circuit Breaker** | `src/infrastructure/providers/router.py` | 60-second automated cooldown on HTTP 429 (`RATE_LIMITED`) with instant failover across Groq, NVIDIA NIM, Cohere, and Gemini | **Zero dropped queries** during rate-limit bursts; seamless automated cloud failover |
| **No-Free-Tier Paid Provider Gating** | `src/infrastructure/providers/router.py`, `src/infrastructure/credentials/manager.py` | Gated DeepSeek and OpenRouter behind explicit funded API key verification; permanently disabled on HTTP 402 (`PAYMENT_REQUIRED`) | **Zero 402 billing crashes**; clean fallback to active free/developer cloud providers |
| **Dead Node Elimination (Exact 16-Node LangGraph)** | `src/features/agent/workflow.py` | Pruned dead nodes (`empty_workspace_check`, `dense_vector_fallback`) and patched RRF routing | **100% architectural alignment** with the canonical 16-node state machine |
| **Universal Synthesis Guidelines & ASCII Citations** | `backend/prompts/system_synthesis.md`, `backend/prompts/system_synthesis.py` | Replaced hardcoded dataset examples with universal tabular guidelines; strictly enforced standard ASCII `[1]`, `[2]` bracket citations | **Zero prompt leakage**; flawless multi-document citation tokenization |
| **Compound Citation Regex Tokenizer** | `src/utils/citationParser.ts`, `src/features/agent/workflow.py` | Upgraded regex to `/\[(\d+(?:\s*,\s*\d+)*)\]/` to tokenize multi-hop compound citations (`[1, 2, 3]`) | **Citation accuracy surged to 87.5%** |
| **Tripartite ChromaDB Naming Standard** | `src/infrastructure/vector/chroma.py`, `src/core/config.py` | Systematic format: `[dataset]_[parser]_[model]` with dynamic switching (`format_collection_name`) | **Clean multi-institution dataset isolation** across NIPGR, BRIC, and IITMRP |
| **Safe Refusal on Trap Questions** | `src/features/agent/workflow.py` (`unverified_responder`) | Strict quality gate refusal when retrieved evidence is insufficient for unanswerable traps | **Unsupported answer rate dropped to 0.0%** (zero hallucinations) |
| **Session Memory Persistence** | `src/infrastructure/database/postgres.py`, `src/infrastructure/cache/redis.py` | PostgreSQL 16 immutable sessions + Redis 7 ephemeral sliding-window context | **100.0% multi-turn memory recall** with 0.00% cross-session leakage |

### Official Benchmark Verification Battery (Mode B End-to-End Evaluation)

The table below records the verified metrics from the latest benchmark run (`run_20260925_005605_raise_domain_playbook_v2`):

| Evaluation Metric | Baseline Score | Playbook V2 Verified Score | Architectural Target | Compliance Status |
| :--- | :--- | :--- | :--- | :--- |
| **Overall Pass Rate** | 56.25% (9/16) | **87.50% (14/16)** | $\ge 80.0\%$ | **EXCEEDED (+31.25%)** |
| **Numerical Claim Verification** | 56.25% (9/16) | **87.50% (14/16)** | $\ge 80.0\%$ | **EXCEEDED (+31.25%)** |
| **Grounding Faithfulness** | 81.25% | **93.36%** | $\ge 90.0\%$ | **PASS** |
| **Citation Accuracy** | 56.25% | **87.50%** | $\ge 80.0\%$ | **PASS** |
| **Unsupported Answer Rate (Hallucinations)**| 6.25% | **0.00%** | $0.0\%$ | **PERFECT ZERO** |
| **Conversational Memory Recall** | 100.0% | **100.00%** | $100.0\%$ | **PERFECT 100%** |

---

## 29. Architecture Verification & Source Audit Ledger

| Subsystem Claim | Evidence File | Class / Method | Status |
| :--- | :--- | :--- | :--- |
| **GGAHC Chunking Pipeline** | `backend/src/chunking/pipeline.py` | `AdaptiveChunkingPipeline.chunk_document()` | **Verified** |
| **Table Preservation Engine** | `backend/src/chunking/table_chunker.py`| `DoclingTablePreservingChunker` | **Verified** |
| **Temporary Graph Builder** | `backend/src/chunking/graph_optimizer.py`| `TemporaryGraphBuilder` (NetworkX Louvain) | **Verified** |
| **Rust FFI Acceleration** | `backend/src/chunking/rust_bridge.py` | `evaluate_boundaries_compact_rust()` | **Verified** |
| **Rust Engine Implementation**| `backend/rust/raise_engine/` | `chunking::scoring`, `retrieval::bm25` | **Verified** |
| **Dense Vector Engine** | `backend/src/infrastructure/vector/chroma.py` | `LocalVectorEngine` (ChromaDB BGE-Large) | **Verified** |
| **In-Memory Lexical Search** | `backend/src/retrieval/parallel_retriever.py` | `SelfContainedBM25` (Okapi BM25) | **Verified** |
| **Persistent Knowledge Graph**| `backend/src/infrastructure/graph/neo4j.py` | `Neo4jDatabase` (Bolt port 7687) | **Verified** |
| **Reciprocal Rank Fusion** | `backend/src/retrieval/fusion.py` | `reciprocal_rank_fusion(k=60)` | **Verified** |
| **Cross-Encoder Reranking** | `backend/src/retrieval/fusion.py` | `CrossEncoderReranker.rerank()` | **Verified** |
| **Entity Mismatch Filter** | `backend/src/retrieval/fusion.py` | `filter_entity_mismatches()` | **Verified** |
| **16-Node LangGraph Agent** | `backend/src/features/agent/workflow.py`| `GraphRAGWorkflow._build_graph()` | **Verified** |
| **Relational Database** | `backend/src/infrastructure/database/postgres.py` | `PostgresManager` (6 tables) | **Verified** |
| **Redis Cache & Session Bus** | `backend/src/infrastructure/cache/redis.py` | `RedisCacheManager` (sliding window turns) | **Verified** |
| **Provenance Verification** | `backend/src/features/verification/claim_verifier.py` | `ClaimVerifier`, `AnswerContract` | **Verified** |
| **Dynamic Multi-Cloud Router**| `backend/src/infrastructure/providers/router.py` | `ProviderRouter` (Groq, Mistral, NVIDIA NIM, Cohere, Gemini, vLLM, Vercel, DeepSeek, OpenRouter, Universal) | **Verified** |
| **Mistral AI Adapter**        | `backend/src/infrastructure/providers/mistral.py` | `MistralProvider` (open-mistral-nemo, codestral-latest) | **Verified** |
| **Vercel AI Gateway Adapter**  | `backend/src/infrastructure/providers/vercel.py` | `VercelAIGatewayProvider` (typesafe-ai/jev, AI Gateway) | **Verified** |
| **Universal Cloud LLM Adapter**| `backend/src/infrastructure/providers/universal.py` | `UniversalCloudProvider` (OpenAI-compatible generic adapter) | **Verified** |
| **Control Center API Router** | `backend/src/api/routers/system.py` | `get_hardware_telemetry`, `get_dynamic_llms`, `save_configuration` | **Verified** |

---

## 30. Academic Benchmark Evaluation Battery & Standardized Datasets

To ensure the RAISE architecture generalizes beyond institutional documents, the system incorporates an academic evaluation battery spanning retrieval, multi-hop reasoning, and open-domain generation. All evaluation sets are strictly isolated under `RAG/data/benchmarks/` and `RAG/evaluation/datasets/`, ensuring zero cross-contamination with production knowledge stores.

### 1. Verified Benchmark Inventory

| Category | Benchmark | Target Split | Sample Size | Verified Provenance Source | Primary Evaluation Focus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Retrieval** | **BEIR (SciFact)** | `test` qrels | 300 queries | Official BEIR repository (TU Darmstadt) | Dense/lexical zero-shot scientific retrieval |
| **Retrieval** | **TREC DL 2019** | `test2019` | 200 queries | Official NIST TREC 2019 + MS MARCO | High-precision passage re-ranking ($n\text{DCG}@10$) |
| **Retrieval** | **TREC DL 2020** | `test2020` | 200 queries | Official NIST TREC 2020 + MS MARCO | High-precision passage re-ranking ($n\text{DCG}@10$) |
| **Reasoning** | **HotpotQA** | `dev_distractor_v1` | 300 questions | Official HotpotQA repository (Yang et al.) | 2-hop comparison & bridge multi-document reasoning |
| **Reasoning** | **2WikiMultihopQA** | `dev` | 300 questions | Official 2Wiki repository (Ho et al., COLING 2020) | Relational multi-hop path and evidence extraction |
| **Reasoning** | **MuSiQue** | `dev` (ans v1.0) | 300 questions | Official Stony Brook NLP (Trivedi et al.) | 2-to-4 hop disconnected reasoning chains & contrast traps |
| **Reasoning** | **FRAMES** | `test.tsv` | 300 questions | Official Google Research frames-benchmark | Multi-hop fact retrieval & numerical aggregation |
| **Generation / QA** | **Natural Questions** | `dev` | 300 questions | Official Google Research NQ | Real Google search queries with short/long ground truths |
| **Generation / QA** | **TriviaQA** | `rc.nocontext dev`| 300 questions | Official Mandar Joshi et al. TriviaQA | Knowledge-heavy open-domain question answering |

### 2. Standardized Evaluation Schema (`EvalQuestion`)

Every benchmark is parsed into a unified schema implemented in `RAG/evaluation/loaders/schema.py`:

```python
@dataclass
class EvalQuestion:
    q_id: str                      # Canonical unique ID (e.g. HOTPOT_5a8b57f..., BEIR_SCIFACT_0)
    benchmark: str                 # Benchmark suite name (BEIR, HotpotQA, 2Wiki, etc.)
    dataset: str                   # Dataset version/identifier
    question: str                  # Query text
    tier: Optional[str]            # Reasoning tier or category
    ground_truth_answer: Optional[str]  # Golden answer or None (for ranking)
    target_document: Optional[str]      # Specific document constraint
    page_citations: List[str]      # Golden page citations
    required_keywords: List[str]   # Mandatory semantic keywords
    supporting_facts: List[str]    # Golden evidence sentences/chains
    hop_count: int                 # Required hops (1, 2, 3, or 4)
    is_unanswerable: bool          # Unanswerable trap query indicator
    metadata: Dict[str, Any]       # Raw provenance, qrels, and aliases
```

### 3. Unified Dispatcher Interface (`BenchmarkLoader.load`)

The `BenchmarkLoader` class dynamically loads any benchmark on demand with optional sample limits:

```python
from RAG.evaluation.loaders.benchmark_loader import BenchmarkLoader

# 1. Retrieval
beir_questions = BenchmarkLoader.load("beir", limit=300)
dl19_questions = BenchmarkLoader.load("trec-dl-2019", limit=200)

# 2. Multi-Hop Reasoning
hotpot_questions = BenchmarkLoader.load("hotpotqa", limit=300)
twowiki_questions = BenchmarkLoader.load("2wikimultihopqa", limit=300)
musique_questions = BenchmarkLoader.load("musique", limit=300)
frames_questions = BenchmarkLoader.load("frames", limit=300)

# 3. Generation & Open-Domain QA
nq_questions = BenchmarkLoader.load("nq", limit=300)
trivia_questions = BenchmarkLoader.load("triviaqa", limit=300)

# 4. Institutional Domain
raise_questions = BenchmarkLoader.load("raise-domain")
```

### 4. Storage Isolation & Guardrails Policy

1. **Evaluator Sandboxing**: Academic datasets (Wikipedia passages, MS MARCO snippets, SciFact abstracts) are NEVER ingested into the production institutional ChromaDB (`iitmrp_docling_bge_large`) or production Neo4j AuraDB (`7639347a`).
2. **Ephemeral Execution**: When evaluating on academic benchmarks, the `hybrid_retriever` operates against dedicated ephemeral test collections or in-memory vector spaces (`TemporaryGraphBuilder`).
3. **Reproducibility Guarantee**: The complete acquisition script `RAG/evaluation/scripts/download_benchmarks.py` enables deterministic 1-click re-downloading and verification directly from official upstream sources.

---

## 31. Network Security, Gateway Observability & Privacy Protection Matrix

When the RAISE platform is deployed behind enterprise networking proxies or routed through Cloudflare, visibility into internal models and prompt payloads is governed by connection topology and TLS inspection policies:

### 1. Multi-Layer Observability & Visibility Audit

| Observability Layer | Network Path | Can Observer See Model Name? | Can Observer See Prompts / Context? | Can Observer See API Keys? | Mitigations & Hardening |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Public Browser via Cloudflare CDN / Tunnel** | `Browser -> Cloudflare Edge -> FastAPI Backend` | **NO** in `/api/chat` (omitted from response payload) | **NO** (Only final synthesized answer returned) | **NO** (Keys never leave backend) | Use `PRIVACY_MODE=true` to mask `/api/system/config` |
| **Cloudflare AI Gateway** | `FastAPI -> CF AI Gateway -> Upstream LLM` | **YES** (Indexed for dashboard cost analytics) | **YES** if "Log Request/Response Bodies" is ON; **NO** if toggled OFF | **NO** (Passed in encrypted headers) | Set "Log Request and Response Bodies" to **OFF** |
| **Corporate Cloudflare Zero Trust (WARP - Default)** | `Host -> Corporate Gateway -> Cloud LLMs` | **NO** (Protected by TLS 1.3 tunnel) | **NO** (Protected by TLS 1.3 tunnel) | **NO** (Protected by TLS 1.3 tunnel) | Standard end-to-end encrypted HTTPS |
| **Corporate Cloudflare Zero Trust (WARP - TLS Inspection)** | `Host -> MITM Decryption -> Cloud LLMs` | **YES** (Decrypted at corporate gateway) | **YES** (Full prompt & payload readable) | **YES** (Visible in raw Authorization header) | Add `Do Not Decrypt` policy bypass for AI domains |

### 2. Privacy Mode Masking (`PRIVACY_MODE=true`)

When `PRIVACY_MODE=true` is enabled in `backend/.env`, the system configuration router (`GET /api/system/config`) automatically masks active model and provider identifiers:
- `llm_model_name` $\to$ `"RAISE-Neural-Engine"`
- `last_used_model` $\to$ `"RAISE-Neural-Engine"`
- `last_used_provider` $\to$ `"RAISE-Cloud-Mesh"`
- `available_providers` $\to$ `["RAISE-Cloud-Mesh"]`

This prevents competitive reverse-engineering or model fingerprinting by unauthorized API callers or front-end observers.



