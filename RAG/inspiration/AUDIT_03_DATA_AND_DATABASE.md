# 🗄️ AUDIT 03: DATABASE PROVENANCE, CHROMADB, NEO4J & PERSISTENCE

## Executive Summary
This document audits the storage substrates, ChromaDB vector collections, Neo4j property graphs, and artifact paths across the RAISE architecture.

---

## 1. Storage of Truth Reference Table

| Data Layer | Actual Filesystem / DB Path | Persistent? | Source of Truth Description |
| :--- | :--- | :--- | :--- |
| **Original PDFs** | `c:\Users\Siddharth Tripathi\Documents\raise\Download\` | Yes | Physical PDF files (7 reports: IIT Madras, Dhanbad, BRIC, NIPGR, IITMRP, etc.) |
| **Extracted Chunks (JSON)** | `RAG/data/processed/chunks/` | Yes | Structure-aware JSON chunks with `chunk_id`, `document_id`, `primary_page`, `enriched_text` |
| **Graph Triples (JSON)** | `RAG/data/processed/graph_triples/` | Yes | Extracted entity & relationship JSONs (`entities`, `relations`) |
| **ChromaDB Vector Store** | `RAG/.runtime/.chromadb/` | Yes | SQLite + HNSW index storing 114 384-dimensional dense vectors |
| **Neo4j Property Graph** | `bolt://localhost:7687` (Docker/WSL2) | Yes | Property graph database with 383 nodes and 1,000+ relationships |
| **Ingestion Manifest** | `RAG/data/processed/ingested_manifest.json` | Yes | Metadata index of ready documents, page counts, and chunk sizes |
| **Local Model Cache** | `~/.cache/huggingface/hub/` | Yes | Offline cached weights for `all-MiniLM-L6-v2` and `Qwen2.5-1.5B-Instruct` |

---

## 2. Neo4j Knowledge Graph Model: Per-PDF vs Combined Graph

### ⚠️ Critical Architecture Finding:
* Currently, all extracted triples from all PDFs are written into a single global Neo4j default database (`neo4j`).
* Although nodes store `source_document: "Annual Report 2024-25.pdf"` in their `properties` / `provenance` dictionary, queries matching common entities (such as `Department of Science and Technology` or `Research Grant`) traverse across documents indiscriminately.
* **Required Conceptual Model**:
  ```text
  PDF A (IIT Madras)  --> Document-Scoped Subgraph (doc_id = 'iit_madras_2025')
  PDF B (BRIC Report) --> Document-Scoped Subgraph (doc_id = 'bric_annual_2025')
  PDF C (NIPGR)       --> Document-Scoped Subgraph (doc_id = 'nipgr_2025')
  ```
* **Cypher Query Fix**:
  Update `Neo4jDatabase.extract_subgraph()` to accept a `document_id` filter:
  ```cypher
  MATCH (start:AcademicEntity {document_id: $doc_id})
  MATCH path = (start)-[r:ACADEMIC_RELATION*1..2]-(target:AcademicEntity {document_id: $doc_id})
  RETURN nodes(path) AS path_nodes, relationships(path) AS path_rels
  ```

---

## 3. ChromaDB Collection Health

* **Collection Name**: `academic_reports_cosine`
* **Embedding Dimension**: `384`
* **Metric**: Cosine Distance
* **Total Chunks Stored**: `114`
* **Metadata Schema**:
  - `chunk_id`: String (e.g. `Annual_Report_2024_25_p014`)
  - `doc_id`: String
  - `pdf_filename`: String
  - `primary_page`: Integer (Actual page number, e.g. 14)
  - `university`: String
  - `heading`: String