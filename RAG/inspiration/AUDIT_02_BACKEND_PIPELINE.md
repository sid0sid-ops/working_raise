# ⚙️ AUDIT 02: BACKEND PIPELINE, EXTRACTION & ROUTE INTEGRATION

## Executive Summary
This document provides a technical audit of the FastAPI routes (`RAG/app.py`), the academic ingestion pipeline (`RAG/src/pipeline_academic_ingest.py`), and the master GraphRAG engine (`RAG/src/rag_pipeline.py`).

---

## 1. Backend Route & Middleware Audit

| Endpoint | Method | Expected Input Payload | Response Structure | Status / Health | Failure Reason (if any) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | `GET` | None | `HTMLResponse` (index.html) | ✅ 200 OK | None |
| `/api/documents` | `GET` | None | `{"documents": [...]}` | ✅ 200 OK | Reads static manifest; doesn't detect raw PDFs in `Download/` |
| `/api/documents/delete` | `POST` | `{"filename": "..."}` | `{"status": "success", ...}` | ✅ 200 OK | Removes entry from manifest JSON; does not delete from ChromaDB or Neo4j |
| `/api/upload-academic-pdfs` | `POST` | `multipart/form-data` (files) | `{"status": "success", "uploaded_count": N, ...}` | ❌ **500 / 422** | 1. `shutil` missing import causes 500.<br>2. Empty file list causes 422 validation error. |
| `/api/graphrag/subgraph-query` | `POST` | `{"query": "...", "hops": 2, "top_k": 4}` | `{"grounded_answer": "...", "citations": [...], ...}` | ⚠️ **200 OK (Partial)** | Grounded answer contains hardcoded fallback templates for select queries. |
| `/api/search` | `POST` | `{"query": "...", "top_k": 5}` | `{"results": [...]}` | ✅ 200 OK | Performs cosine search on ChromaDB |
| `/api/neo4j/query` | `POST` | `{"query": "MATCH..."}` | `{"records": [...]}` | ✅ 200 OK | Queries live Neo4j database |

---

## 2. PDF Ingestion Pipeline Diagnostic

The actual processing pipeline in `AcademicPipelineIngestor.process_pdf()` executes the following steps:
1. **PyMuPDF Extraction**: Opens PDF with `fitz.open()`, extracts raw text and font sizes.
2. **Context Enrichment**: Prepends Anthropic-style contextual prefix (`Institution`, `Document`, `Period`, `Page`, `Heading`).
3. **Academic Entity Extraction**: `AcademicDomainExtractor` uses regex/heuristic patterns for Grants, Inventions, Startups, and Metrics.
4. **ChromaDB Vector Upsert**: Embeds chunks locally via `all-MiniLM-L6-v2` (`384` dimensions).
5. **Neo4j Cypher Generation**: Translates entities and relationships into property graph nodes/edges.

### 📍 Pipeline Breakpoint Identified:
* When a user uploads a new PDF through the web UI, the backend crashes at:
  ```python
  # RAG/app.py line 172
  with open(dest_path, "wb") as buffer:
      shutil.copyfileobj(upload_file.file, buffer) # NameError: name 'shutil' is not defined
  ```
* Because `shutil` is missing, execution never reaches `academic_pipeline.process_pdf()`. The file is partially created as 0 bytes, no chunks are indexed into ChromaDB, no nodes are added to Neo4j, and the manifest is not updated.

---

## 3. Grounded Answer Synthesis & Hardcoded Strings Audit

In `RAG/src/agent_router.py` (lines 213–340), queries matching specific keyword patterns (e.g., `"research budget"`, `"patents"`, `"inventions"`) bypass dynamic chunk synthesis and return hardcoded multi-institution text:
* **Query Matcher**: `if any(k in q_lower for k in ["patents", "inventions", "startups"]):`
* **Result**: Emits fixed statistics for IIT Madras (417 patents, INR 7.03 Cr, etc.) regardless of which PDF is active in the user's workspace.
* **Fix Required**: Route ALL queries through dynamic chunk context assembly, local LLM generation (`LocalLLMEngine`), and factual claim extraction.