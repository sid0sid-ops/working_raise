# RAISE Data Flow Specification

**Version**: 2.5.0  
**Status**: CANONICAL & AUTHORITATIVE  
**Verification Date**: 2026-09-14  

---

## 1. End-to-End Data Lifecycle

Data in RAISE traverses six distinct phases from raw academic document ingestion to real-time client consumption:

```mermaid
flowchart TD
    subgraph PHASE1 ["Phase 1: PDF Ingestion & Document Parsing"]
        PDF["Raw Academic PDF"] --> ParserRouter{"Parser Router<br/>(document_parser.py)"}
        ParserRouter -->|Complex / Tables| Docling["Docling Deep Vision<br/>(TableFormer + Layout OCR)"]
        ParserRouter -->|Fast Native Stream| PyMuPDF["PyMuPDF Fast Stream<br/>(Native Text & Coordinates)"]
        Docling --> RawAST["Structured Document AST<br/>(Markdown / Tables / Figures)"]
        PyMuPDF --> RawAST
    end

    subgraph PHASE2 ["Phase 2: Graph-Guided Adaptive Chunking (GGAHC)"]
        RawAST --> StructuralSeg["1. Structural Segmentation"]
        StructuralSeg --> SemanticBound["2. Semantic Boundary Detection"]
        SemanticBound --> EntityClustering["3. Academic Entity & Community Graph"]
        EntityClustering --> Optimization["4. Multi-Signal Boundary Optimization"]
        Optimization --> Assembly["5. Hierarchical Assembly<br/>(Parent: 450-1400w / Child: 100-400w)"]
        Assembly --> Contextualizer["6. Contextualization & Path Breadcrumbs"]
    end

    subgraph PHASE3 ["Phase 3: Multi-Substrate Persistence & Indexing"]
        Contextualizer --> Embedder["BAAI/bge-large-en-v1.5 (1024-dim)"] --> ChromaDB[("ChromaDB Vector Store<br/>(HNSW Cosine Index)")]
        Contextualizer --> BM25Builder["Inverted Index Builder"] --> BM25Store[("In-Memory BM25 Lexical Index")]
        Contextualizer --> TripleExtractor["Academic Triple Extractor"] --> Neo4jStore[("Neo4j 5.26 Property Graph")]
        Contextualizer --> TableExtractor["Table Coordinate Matrix"] --> TableStore[("Structured Table Matrix Index")]
        Contextualizer --> MetaExtractor["Document Metadata"] --> PostgresStore[("PostgreSQL 16 documents Table")]
    end

    subgraph PHASE4 ["Phase 4: Query Intake, Retrieval & Reciprocal Rank Fusion"]
        UserQuery["User Research Query"] --> SecurityShield["ASGI Shield & Token Bucket Rate Limiter"]
        SecurityShield --> RedisCacheCheck{"Redis Cache Hit?"}
        RedisCacheCheck -->|Yes| InstantReturn["Instant Return Cached Response"]
        RedisCacheCheck -->|No| IntakeEngine["Query Intake Engine<br/>(Deictic Coreference & Decomposition)"]
        
        IntakeEngine --> ParallelDispatch["Parallel Retriever Dispatch"]
        ParallelDispatch --> ChromaDB
        ParallelDispatch --> BM25Store
        ParallelDispatch --> Neo4jStore
        ParallelDispatch --> TableStore
        
        ChromaDB --> RRF["Reciprocal Rank Fusion (k=60)<br/>+ Dynamic Table Weight Boosting"]
        BM25Store --> RRF
        Neo4jStore --> RRF
        TableStore --> RRF
        
        RRF --> Reranker["Cross-Encoder BGE-Reranker-Large<br/>(Thread-Safe GPU Singleton Cache)"]
    end

    subgraph PHASE5 ["Phase 5: Synthesis, Grounding & Verification"]
        Reranker --> TopContext["Top-k Scored Chunks + Subgraph Context"]
        TopContext --> LLM["vLLM Qwen 2.5 14B Engine (Port 8002)"]
        LLM --> GenResponse["Draft Answer + Chain-of-Thought"]
        
        GenResponse --> ClaimExtractor["Atomic Claim Proposition Extractor"]
        ClaimExtractor --> GroundingEngine["4-Tier Escalation Grounding Engine"]
        
        GroundingEngine -->|Tier 1| DeterministicMath["Exact Numbers / IEEE-754 Tolerance (0.05)"]
        GroundingEngine -->|Tier 2| LexicalFastPath["High Overlap Fast-Path (<=1ms)"]
        GroundingEngine -->|Tier 3| FineCatNLI["FineCat-NLI ModernBERT (8k context)"]
        GroundingEngine -->|Tier 4| SoftContainment["Context Expansion & Multi-Chunk Fallback"]
        
        DeterministicMath --> QualityGate["Quality Gate Evaluator (>= 80% Faithfulness)"]
        LexicalFastPath --> QualityGate
        FineCatNLI --> QualityGate
        SoftContainment --> QualityGate
    end

    subgraph PHASE6 ["Phase 6: Persistence & Client Stream Delivery"]
        QualityGate -->|PASS| FinalizeSuccess["Bind Citations [N] with #page=N Deep-Links"]
        QualityGate -->|FAIL / Abstain| FinalizeAbstain["Sanitize to INSUFFICIENT REASONING PATH"]
        
        FinalizeSuccess --> SessionStorage["Update PostgreSQL 16 & Redis 7 (Dual-Key Schema)"]
        FinalizeAbstain --> SessionStorage
        SessionStorage --> SSEStream["FastAPI Server-Sent Events (SSE) Stream / JSON API"]
        SSEStream --> ClientApp["Frontend Research Console / Mac Client"]
    end
```

---

## 2. Ingestion & Indexing Data Contracts

### A. GGAHC Chunk Schema (`RAG/src/chunking/models.py`)

Every document chunk emitted by the 8-stage pipeline conforms to `ProcessedChunk`:

```python
class ProcessedChunk:
    chunk_id: str                   # e.g., "doc_123_p14_c02"
    document_id: str                # UUID or filename of source PDF
    text: str                       # Contextualized text content
    plain_text: str                 # Uncontextualized raw excerpt
    chunk_type: str                 # "prose" | "table" | "figure" | "code"
    token_count: int                # Token length (tiktoken / transformers)
    parent_chunk_id: Optional[str]  # Parent macro-chunk ID (450-1400 tokens)
    page_number: int                # Physical PDF page number (1-based)
    printed_page_number: Optional[int] # Printed report page number
    section_path: List[str]         # e.g., ["Chapter 3", "Financial Statement", "Revenue"]
    entities: List[str]             # Extracted entity strings
    table_matrix: Optional[Dict]    # Row/column structured data if chunk_type == "table"
    hash: str                       # SHA-256 fingerprint for deduplication
```

---

## 3. Query & Retrieval Telemetry Data Contracts

### A. ClaimVerificationRecord (`RAG/src/features/evaluation/engine.py`)

Every evaluated claim is audited using `ClaimVerificationRecord`:

```python
class ClaimVerificationRecord:
    claim_text: str                 # The atomic claim proposition
    status: str                     # "SUPPORTED" | "CONTRADICTION" | "UNSUPPORTED"
    grounding_score: float          # Combined overlap score [0.0, 1.0]
    verification_path: str          # DETERMINISTIC | NLI | DETERMINISTIC+NLI | EVIDENCE_EXPANSION+NLI | CONTROLLED_ABSTENTION
    decision_reason: str            # Detailed human-readable causal rationale
    raw_logits: Optional[Dict[str, float]] # {"contradiction": l_c, "neutral": l_u, "entailment": l_e}
    softmax_probs: Optional[Dict[str, float]] # Softmax probabilities summing to 1.0
    calibration_status: str         # "UNVALIDATED_RAW_SOFTMAX"
```
