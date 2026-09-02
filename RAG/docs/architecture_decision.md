# Architecture Decision Record (ADR): University Annual Report Agentic GraphRAG

## Status: ACCEPTED

---

## 1. Context & Problem Statement
We are building a production-grade **Agentic GraphRAG system** for comparative analysis of university annual reports, institutional audits, and financial statements. 
The system must:
1. Handle highly irregular PDFs (multi-column text, multi-year financial tables, nested headings, footnotes, university-specific dialects).
2. Guarantee 100% provenance and zero human-interpretation bias (never fabricate or hallucinate numeric metrics).
3. Run 100% locally and free on existing hardware: **NVIDIA RTX 3090 (24 GB VRAM) + 64 GB RAM**.
4. Support multi-PDF comparative reasoning across institutions and years.

---

## 2. Evaluation of Candidate Frameworks

### A. Ingestion & Document Understanding: PyMuPDF vs Docling
* **Docling (`docling-project/docling`)**:
  * **Strengths**: IBM Research's SOTA open-source document converter. Excels at complex table structure recognition (spanning cells, multi-level headers) and reading order reconstruction via TableFormer/LayoutLM models.
  * **Compatibility**: Produces `DoclingDocument` and clean semantic HTML/Markdown.
  * **Decision**: **Integrate Docling as an Advanced Ingestion Adapter (`DoclingParserAdapter`)** inside the ingestion layer. When documents have highly warped tables or scanned elements, Docling provides superior matrix preservation; PyMuPDF remains the fast native baseline.

### B. Graph & Vector Storage: Architecture Options A through E
* **Architecture A: Neo4j + Custom Hybrid Retriever + Local LLM (SELECTED)**:
  * **Rationale**: Neo4j serves as both the primary property graph database (Cypher queries, multi-hop relationship traversal) and supports native vector indexes. Eliminates redundant database infrastructure while providing direct integration with O'Reilly GraphRAG patterns.
* **Architecture B: Neo4j + LightRAG**:
  * **Rationale**: LightRAG has fast dual-level retrieval, but its agentic reasoning loop and table provenance are less customizable than our deterministic fact model.
* **Architecture C: Neo4j + LlamaIndex `PropertyGraphIndex`**:
  * **Rationale**: Useful property graph abstraction, but heavy abstraction overhead and higher latency for specialized multi-metric university comparisons.
* **Architecture D: Neo4j + Haystack**:
  * **Rationale**: Strong agent pipelines, but requires extra glue code for custom Cypher entity validation.
* **Architecture E: Microsoft GraphRAG custom pipeline**:
  * **Rationale**: Leiden community detection is excellent for high-level summaries, but poor for pinpoint numeric metric lookups.

---

## 3. The Definitive Selected Architecture: **Modular Agentic GraphRAG**

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION & SEMANTIC INTERMEDIATE REPRESENTATION                                         │
│ • Existing PyMuPDF Parser + Docling Adapter (Difficult Layouts & Tables)                    │
│ • Canonical 5-Star Semantic HTML5 (<article>, <section>, <table data-page="87">, <data>)    │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. DUAL-STORE GROUNDED INDEXING                                                             │
│ • Structured Fact Store: Deterministic numeric records (metric, value, unit, currency, year)│
│ • Property Knowledge Graph: Neo4j (Institutes, Faculty, Grants, Patents, Initiatives)       │
│ • Vector Store: ChromaDB / Neo4j Vector (BAAI/bge-m3 / sentence-transformers)               │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. AGENTIC RETRIEVAL & REASONING LOOP                                                       │
│ • Query Analyzer & Plan Builder (Identifies universities, metrics, temporal ranges)         │
│ • Multi-Tool Parallel Retrieval (StructuredFactTool, CypherTool, VectorTool, LexicalTool)   │
│ • Conflict Resolution & Source Authority Ranking                                            │
│ • Anti-Hallucination Claim Verification Layer (Every claim checked against source bbox/page)│
│ • Grounded Answer Generator with Full Provenance Breadcrumbs                                │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Hardware Optimization & Model Selection
* **Hardware**: NVIDIA GeForce RTX 3090 (24 GB VRAM) + 64 GB System RAM.
* **Embedding Model**: `BAAI/bge-m3` (1024-d, dense + sparse multi-vector, multilingual, 8192 context length, runs under 4 GB VRAM on CUDA).
* **Local Inference LLM**: `Qwen2.5-32B-Instruct-GGUF` (Q4_K_M / Q5_K_M ~19 GB VRAM via `llama.cpp` / vLLM) or `Qwen2.5-14B-Instruct` (~9 GB VRAM, ultra-fast latency).
* **Local Backend API**: OpenAI-compatible local server (`http://127.0.0.1:8000/v1` or `http://localhost:11434/v1` via Ollama / llama-server).
