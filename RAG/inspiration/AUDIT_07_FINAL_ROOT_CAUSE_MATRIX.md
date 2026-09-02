# 📊 AUDIT 07: FINAL ROOT CAUSE MATRIX & PRIORITIZED ACTION PLAN

## Executive Summary
This document consolidates all forensic findings into a single Root Cause Matrix with exact file paths, severities, and prioritized resolution steps.

---

## 1. Master Root Cause Matrix

| Problem | Root Cause | Impacted File(s) | Severity | Permanent Technical Fix |
| :--- | :--- | :--- | :--- | :--- |
| **1. PDF Upload Fails (Nothing Happens)** | `shutil` missing import in `app.py` line 172 causes HTTP 500 when saving uploaded file. | `RAG/app.py` | **CRITICAL** | Add `import shutil` and defensive try/catch around upload stream. |
| **2. Annual Report Vault Fails** | `POST /api/upload-academic-pdfs` expects files; passing empty FormData returns HTTP 422. | `RAG/app.py`, `RAG/static/app.js` | **CRITICAL** | Create dedicated `POST /api/vault/load-defaults` endpoint to ingest existing `Download/` PDFs. |
| **3. Multi-PDF Selection Surprise** | `<input type="file" multiple>` allows multi-select without per-file progress UI. | `RAG/templates/index.html` | **HIGH** | Default to single PDF picker; add dedicated batch card if multi-upload is desired. |
| **4. Duplicate Evidence with "Page 1"** | Citation metadata fallback defaults to `1` when `primary_page` is missing; frontend doesn't deduplicate by `chunk_id`. | `RAG/src/agent_router.py`, `RAG/static/app.js` | **HIGH** | Pass real `primary_page` from ChromaDB metadata; deduplicate citations by `document_id + page + chunk_id`. |
| **5. "3 PDFs but 4 Sources"** | Code reported `top_k=4` retrieved chunk count as "sources count". | `RAG/src/rag_pipeline.py`, `RAG/static/app.js` | **HIGH** | Calculate `unique_sources = new Set(citations.map(c => c.pdf_filename)).size`. |
| **6. Global vs Per-PDF Knowledge Graph** | Neo4j queries lacked `document_id` scoping, mixing entities across all uploaded PDFs. | `RAG/src/neo4j_engine.py` | **HIGH** | Scope Cypher queries with `WHERE start.document_id = $doc_id`. |
| **7. "Create New" Notebook State** | Global document manifest rendered across all notebook views without session isolation. | `RAG/static/app.js` | **HIGH** | Maintain distinct document collections per notebook in client state. |
| **8. Dead "Tune Settings" Button** | No event listener or drawer attached to settings button. | `RAG/templates/index.html` | **MEDIUM** | Implement clean Settings drawer for theme, sound, auto-scroll, and scope. |
| **9. Unwanted Buttons in Header** | Command Palette (`terminal`) and Open Neo4j (`hub`) buttons cluttering the UI. | `RAG/templates/index.html` | **LOW** | Remove Command Palette and Open Neo4j buttons cleanly. |
| **10. Color Harmony** | High-saturation purple and stark contrasts. | `RAG/static/style.css` | **MEDIUM** | Apply restrained academic dark palette (`#0e1117`, `#151921`, `#3b82f6`). |

---

## 2. Prioritized Implementation Order

1. **Step 1: Repair Core Backend Ingestion (`RAG/app.py`)**:
   * Add `import shutil`.
   * Create `POST /api/vault/load-defaults` for instant vault loading.
   * Return real-time ingestion progress and document metadata.
2. **Step 2: Fix Provenance, Page Numbers & Deduplication (`agent_router.py`, `vector_engine.py`)**:
   * Ensure `primary_page` and `document_id` are strictly attached to every chunk and citation.
   * Deduplicate evidence cards in Grounded Evidence drawer.
   * Differentiate `Documents Loaded` (3) vs `Sources Cited` (2) vs `Evidence Chunks` (4).
3. **Step 3: Document-Scoped Neo4j Subgraphs (`neo4j_engine.py`)**:
   * Add `doc_id` filtering to Neo4j graph traversal to prevent entity mixing across unrelated PDFs.
4. **Step 4: Clean Up UI Controls (`index.html`, `style.css`, `app.js`)**:
   * Remove Command Palette and Open Neo4j buttons.
   * Fix Single PDF upload picker and real-time processing indicator.
   * Connect Settings drawer.
   * Apply calm academic dark theme.