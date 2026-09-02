# 📐 RAISE Master Ingestion Pipeline Specification

## 1. Overview & Core Objective
The RAISE Ingestion Pipeline converts raw academic university PDF reports into an auditable, grounded, multi-substrate knowledge base (ChromaDB + Neo4j).

```
   Uploaded PDF (`data/documents/`)
              ↓
  Docling Document Parsing (`docling`)
              ↓
   Layout & Table Markdown Structure
              ↓
 Context-Enriched Semantic Chunks (`data/processed/chunks/`)
              ↓
 ┌────────────┴─────────────────────────┐
 ▼                                      ▼
Dense Cosine Embeddings          Domain Entity & Relation Extraction
 (ChromaDB Vector Store)             (`AcademicDomainExtractor`)
                                        ↓
                                  Neo4j Property Graph
                                (`data/processed/graph_triples/`)
```

---

## 2. Ingestion Stages

### Stage 1: Document Acquisition & Content Hashing
- Source location: `data/documents/`
- Every document is assigned a deterministic `document_id` using its clean stem.
- Raw PDFs are kept strictly read-only to preserve citation page provenance.

### Stage 2: Docling Layout & Table Extraction
- Primary Parser: `Docling` (`v2.124.0`)
- Extracts reading order, Markdown tables (`TableFormer`), headers, and scanned OCR (`RapidOCR`).
- Fallback: PyMuPDF (`fitz`) only if Docling encounters corrupt or unsupported binary files.

### Stage 3: Semantic Chunking & Anthropic Context Enrichment
- Each section chunk is prepended with explicit contextual provenance metadata:
  ```text
  Institution: <University Name>
  Document: <Filename.pdf>
  Period: <Academic Year>
  Page: <Page Number>
  Heading: <Section Title>
  ```
- Stored as deterministic JSON artifacts in `data/processed/chunks/<document_id>_chunks.json`.

### Stage 4: Dense Vector Indexing (ChromaDB)
- Collection: `raise_academic_documents`
- Persisted location: `.runtime/.chromadb/`
- Dense cosine similarity vectors with complete chunk metadata.

### Stage 5: Academic Knowledge Graph Extraction (Neo4j)
- Extracts entities (`University`, `Department`, `Faculty`, `Grant`, `Patent`, `Startup`, `Facility`, `MoU`).
- Extracts typed relationships (`FUNDS`, `FILED_PATENT`, `INCUBATED`, `HAS_DEPARTMENT`, `COLLABORATED_WITH`).
- Offline JSON artifacts stored in `data/processed/graph_triples/<document_id>_triples.json`.
- Synced to Neo4j via Cypher `MERGE` statements.
