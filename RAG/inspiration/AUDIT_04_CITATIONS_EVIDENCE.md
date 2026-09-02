# 📑 AUDIT 04: CITATIONS, GROUNDED EVIDENCE & TRACEABILITY

## Executive Summary
This document audits why duplicate evidence cards appear with "Page 1", why the system claims "4 sources" when only 3 documents are loaded, and where the grounding score (e.g., 84%) originates.

---

## 1. Duplicate Grounding Evidence & "Page 1" Root Cause

### 🔍 Observed Failure:
In the Grounded Evidence drawer, clicking citation badges `[1]`, `[2]` shows the same generic card repeatedly with `Page 1` / `Page 1`.

### 📍 Technical Cause:
1. In `RAG/src/agent_router.py` (lines 192-202):
   ```python
   raw_chunks = self.vector_engine.search(query=plan.query, top_k=6)
   chunks = raw_chunks[:4]
   for c in chunks:
       citations.append(c.get("metadata", {}))
   ```
2. When the fallback hardcoded answer is returned for template queries, the response payload does not bind individual sentence citations to specific chunk IDs.
3. In `RAG/src/claim_verifier.py` line 137:
   ```python
   "page": fact_dict.get("provenance", {}).get("page_number", 1)
   ```
   If `provenance` is not fully serialized, `get("page_number", 1)` falls back to `1`.
4. In `RAG/static/app.js`, `EvidenceDrawer.loadCitations(citations)` iterates over `citations` without deduplicating by `document_id + page + chunk_id`. If the top 4 vector hits come from the same document or default page, 4 identical cards are rendered.

---

## 2. "3 Documents Loaded vs 4 Sources Reported" Bug

### 🔍 Observed Failure:
The user uploads 3 PDFs, but the answer footer or thoughts trace reports `"4 sources"`.

### 📍 Technical Cause:
1. In `RAG/src/rag_pipeline.py`, `top_k` is hardcoded to `4` (`top_k=4`).
2. Vector retrieval fetches `4` chunks. The code treats `len(chunks)` as the number of "sources":
   ```python
   # Treated chunks.length (4 chunks) as sources count (4 sources)
   ```
3. If 4 chunks were retrieved from 2 distinct PDFs, the system erroneously reported `4 sources` instead of `2 sources (4 chunks)`.

### 🛠️ Permanent Fix:
Explicitly differentiate:
* `documents_loaded`: Total PDFs in notebook (e.g. 3)
* `sources_cited`: Unique `pdf_filename` count in retrieved evidence (e.g. 2)
* `evidence_passages`: Total chunk count (e.g. 4)
* `citations_count`: Inline `[N]` references in the generated text.

---

## 3. Grounding / Traceability Score (84%) Origin

* **Origin**: Calculated in `RAG/src/claim_verifier.py` (lines 180–215):
  ```python
  vc = self.verify_claim(...)
  confidence = 0.96 if any(s.get("type") == "numeric_fact" for s in support) else 0.85
  avg_grounding = sum(vc.confidence for vc in verified_claims) / max(len(verified_claims), 1)
  ```
* When claims are verified against numeric facts in `FactEngine`, each claim receives `0.96` or `0.85`. Their average produces values like `0.84` (84%) or `0.85` (85%).
* **Status**: The calculation is deterministic and grounded in retrieved facts, but needs live dynamic binding to prevent displaying scores when evidence is insufficient.