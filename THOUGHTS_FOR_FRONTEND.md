# RAISE Frontend Developer Collaboration & Standards Audit

**Branch**: `conv`  
**Remote Repository**: [https://github.com/sid0sid-ops/working_raise.git](https://github.com/sid0sid-ops/working_raise.git)  
**Author**: Backend & AI Systems Lead  
**Audience**: Frontend Lead & React Development Team  
**Last Updated**: September 24, 2026  
**Status**: Active Collaboration & Standards Audit Log  

---

## 1. Welcome & Collaboration Protocol on Branch `conv`

Welcome to branch `conv`! This branch serves as our shared **coordination and communication hub** between the backend systems team and the frontend engineering team.

### How We Collaborate Here:
1. **Periodic Code Audits**: As the frontend team pushes updates to `working/frontend`, the backend team pulls the branch, audits changes against backend contracts and production standards, and logs concrete feedback here.
2. **Contract Truth**: Any changes to API schemas, Server-Sent Events (SSE) streaming formats, GraphRAG metadata, or database persistence formats are documented here first so frontend code never has to guess.
3. **Bi-Directional Notes**: The frontend team can commit responses, questions, or UI requirements directly into this document or as new entries in the `conv/` directory.

### Current Backend Status & Milestone:
The RAISE backend has completed its formal **16-point evaluation battery** across retrieval, GraphRAG, answer accuracy, and conversational memory:
- **Retrieval Mode A (Vector + Hybrid BM25)**: Recall@10 reached **62.50%** with nDCG@10 of **1.2446**.
- **Reasoning Mode B (Multi-hop GraphRAG + Claim Verification)**: Passed evaluation cases jumped from 0/16 to **56.25%**, with **0.0% unsupported/hallucinated answers** on verified claims.
- **Conversational Memory**: PostgreSQL 16 + Redis 7 state persistence verified at **100% recall** with zero cross-session leakage.

The retrieval and verification core is solid. Now we need the frontend user experience and contract handling to match this standard of excellence.

---

## 2. In-Depth Audit of `working/frontend`

We conducted a forensic code review of `remotes/working/frontend` (Commit `615190a`). Here is our honest appraisal of what is working well, followed by the areas that are **below production standards** and must be resolved.

### What is Built Well:
- **Clean Modern Stack**: React 19, TypeScript, Tailwind CSS, and Lucide icons provide a responsive foundation.
- **`InlinePdfViewer` (`src/components/citations/InlinePdfViewer.tsx`)**: The `#page=N` fragment navigation, active page badge, and "Return to Cited Page" button provide an intuitive document verification experience.
- **Session Drawer Architecture**: Clear separation of session-specific documents (`session_drawer`) from the global document library (`/api/documents`).
- **SSE Stream Reader (`src/api/client.ts`)**: Line-buffered reading with support for both `data: {"token": "..."}` and completion metadata.

---

### Critical Issues & Below-Standard Patterns:

### 🔴 ISSUE 1: Hardcoded University Attribution (`'IIT Madras'`)
* **Location**: [`src/utils/citationParser.ts`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/src/utils/citationParser.ts#L34) (Lines 34 & 96)
* **Code in `working/frontend`**:
  ```typescript
  return {
    ...
    university: raw.university || raw.metadata?.university || 'IIT Madras',
    ...
  };
  ```
* **Why this is below standard**:
  RAISE is an institutional research platform indexing documents from multiple universities, national laboratories, and funding agencies (e.g., **National Institute of Plant Genome Research (NIPGR)**, **Biotechnology Research and Innovation Council (BRIC)**, **ICAR**, **DBT**, and arbitrary user-uploaded PDFs).
  Hardcoding `'IIT Madras'` as a fallback causes research papers authored by NIPGR or other institutes to be falsely attributed to IIT Madras in citation badges, tooltips, and export summaries.
* **Required Fix**:
  Preserve `raw.university || raw.metadata?.university || raw.institution || ''`. If no university is present, set it to an empty string `''` or omit it. The UI should only render the institution tag when one is actually present in the backend metadata.

---

### 🔴 ISSUE 2: Compound Citation Parsing Flaw (`[1, 2, 3]`)
* **Location**: [`src/utils/citationParser.ts`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/src/utils/citationParser.ts#L173-L200) (`parseCitations`)
* **Code in `working/frontend`**:
  ```typescript
  // Regex to match [1], [2], etc.
  const citationRegex = /\[(\d+)\]/g;
  ```
* **Why this is below standard**:
  While `cleanRagResponseText` strips compound brackets like `[1, 2]` during copy-to-clipboard, `parseCitations` **only matches single digits in brackets** (`/\[(\d+)\]/g`).
  When the backend synthesizes multi-hop answers, claims often cite multiple sources: e.g., `"The project achieved 40% yield increase [1, 3]."`.
  Because `parseCitations` only searches for single numbers, `[1, 3]` is skipped by the regex and treated as raw text. The user cannot click either citation, and the interactive badge does not appear.
* **Required Fix**:
  Update `citationRegex` to `/\[(\d+(?:\s*,\s*\d+)*)\]/g`. Split the captured group by `,`, trim whitespace, and generate either:
  - Separate individual `CitationToken` items for each index, OR
  - A compound `CitationToken` with `indices: number[]` so `CitationBadge` can render `[1, 3]` as an interactive multi-citation dropdown.

---

### 🔴 ISSUE 3: Endpoint Drift & Obsolete Fallback Routes
* **Location**: [`src/api/endpoints.ts`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/src/api/endpoints.ts) and [`src/services/ChatService.ts`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/src/services/ChatService.ts#L130-L160)
* **Code in `working/frontend`**:
  ```typescript
  SUBGRAPH_QUERY: '/api/graphrag/subgraph-query',
  ```
  `ChatService.ts` contains fallback logic where it tries `/api/graphrag/subgraph-query` if `/api/chat` fails.
* **Why this is below standard**:
  `/api/graphrag/subgraph-query` was an early prototype endpoint that is deprecated. The production FastAPI router exclusively serves:
  - `POST /api/chat`: Unified chat and GraphRAG retrieval (supports both `fast` and `expert` modes).
  - `POST /api/agent/query`: Agentic multi-step planning and tool orchestration.
  Falling back to `/api/graphrag/subgraph-query` produces red `404 Not Found` errors in the browser console when requests fail, obfuscating the real network error.
* **Required Fix**:
  Remove the fallback to `/api/graphrag/subgraph-query`. All chat requests must go directly to `POST /api/chat`.

---

### 🟡 ISSUE 4: Deprecated Request Payload Properties
* **Location**: [`src/services/ChatService.ts`](file:///c:/Users/Siddharth%20Triharth/Documents/raise/src/services/ChatService.ts#L137-L151)
* **Code in `working/frontend`**:
  ```typescript
  body: JSON.stringify({
    message: req.query,
    query: req.query,
    mode: effectiveMode,
    stream: true,
    chat_history: req.chat_history,
    session_id: req.thread_id,
    thread_id: req.thread_id,
    active_docs: req.active_docs || [],
    format: 'raw',
    document_filter: req.document_filter,
    hops: req.hops ?? (effectiveMode === 'expert' ? 3 : 1),
    top_k: req.top_k ?? (effectiveMode === 'expert' ? 8 : 4),
    parser: 'docling',               // <-- DEPRECATED
    full_potential: effectiveMode === 'expert', // <-- DEPRECATED
  })
  ```
* **Why this is below standard**:
  `parser: 'docling'` and `full_potential: boolean` are legacy experimental flags from earlier notebook scripts. The production ingestion pipeline parses documents on upload and persists them into ChromaDB and Neo4j. Ingestion format is not selected during runtime chat.
* **Required Fix**:
  Clean up the request payload to send only the active production parameters:
  ```typescript
  {
    message: req.query,
    mode: effectiveMode, // 'fast' | 'expert'
    session_id: req.thread_id,
    active_docs: req.active_docs || [],
    hops: effectiveMode === 'expert' ? 3 : 1,
    top_k: effectiveMode === 'expert' ? 8 : 4,
    stream: true
  }
  ```

---

### 🟡 ISSUE 5: Page Number Key Discrepancies
* **Location**: [`src/types/index.ts`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/src/types/index.ts) and [`src/utils/citationParser.ts`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/src/utils/citationParser.ts#L38-L58)
* **Current Situation**:
  The frontend normalizer currently checks 10 different aliases:
  `raw.primary_page`, `raw.page`, `raw.page_number`, `raw.page_no`, `raw.physical_page`, `raw.metadata?.primary_page`, etc.
* **Backend Standard**:
  The backend has strictly standardized on two distinct fields:
  1. `primary_page`: **Integer (1-indexed)**. This is the physical PDF sheet number (e.g. `23`), used for `#page=23` browser deep-linking.
  2. `printed_page`: **String** (e.g. `"xvii"` or `"15"`). This is the page number printed in the document header/footer.
* **Required Fix**:
  Update frontend TypeScript `Citation` interface to declare `primary_page: number` and `printed_page?: string`. Keep fallback inspection for defensive handling, but ensure the UI displays `primary_page` for document jump links.

---

### 🟡 ISSUE 6: Markdown Stream Boundary Sanitation
* **Location**: [`src/api/client.ts`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/src/api/client.ts#L330-L380)
* **Observation**:
  When streaming tokens in real time, if an SSE chunk splits a markdown delimiter (e.g. chunk 1 ends in `*` and chunk 2 begins with `*bold**`), or splits a LaTeX KaTeX block (`$$` or `\(`), the markdown parser (`AnswerMarkdown.tsx`) can temporarily render broken raw tags or throw re-render layout shifts.
* **Recommendation**:
  Ensure `AnswerMarkdown.tsx` uses standard memoization and graceful KaTeX parsing error boundaries (`throwOnError: false`) so partial formulas during streaming do not crash or flicker.

---

## 3. Production Backend Contract Specifications

To prevent any further drift between frontend and backend, here are the exact contracts:

### A. Primary Chat Endpoint: `POST /api/chat`

#### Request Payload:
```json
{
  "message": "What are the primary findings in the NIPGR 2024 report?",
  "session_id": "sess-20260924-001",
  "mode": "expert",
  "active_docs": ["NIPGR_Annual_Report_2023_24.pdf"],
  "hops": 3,
  "top_k": 8,
  "stream": true
}
```

#### Server-Sent Events (SSE) Wire Format:
When `stream: true`, the backend returns `Content-Type: text/event-stream`:
```text
data: {"token": "The "}

data: {"token": "primary "}

data: {"token": "findings "}

data: {"token": "demonstrate [1]."}

data: {"status": "completed", "citations": [{"citation_index": 1, "document_id": "NIPGR_Report", "pdf_filename": "NIPGR_Annual_Report_2023_24.pdf", "primary_page": 14, "printed_page": "8", "heading": "Executive Summary", "plain_text": "Field trials demonstrated 28% yield enhancement.", "university": "National Institute of Plant Genome Research", "similarity": 0.94}], "subgraph": {"nodes": [{"id": "n1", "label": "NIPGR", "type": "Institution"}], "edges": []}}

data: [DONE]
```

### B. Session Drawer Management APIs:
- **`GET /api/chat/sessions/{session_id}/drawer`**: Returns `{ "session_id": "...", "active_docs": ["doc1.pdf", "doc2.pdf"] }`.
- **`POST /api/chat/sessions/{session_id}/drawer/attach`**: Body: `{"filename": "doc.pdf"}`. Idempotently attaches document to session drawer.
- **`POST /api/chat/sessions/{session_id}/drawer/remove`**: Body: `{"filename": "doc.pdf"}`. Detaches document from session drawer without deleting from vault.

### C. PDF Document Streaming:
- **`GET /api/pdf/{filename}`**: Streams raw binary PDF file with `Content-Type: application/pdf`.
- **Deep-linking Anchor**: When opening a cited page in an iframe or new browser tab, append `#page={primary_page}` (e.g. `/api/pdf/Report.pdf#page=14`).

---

## 4. Actionable Next Steps for Frontend Team

Please review and execute the following fixes on `working/frontend`:

- [ ] **Fix 1: Remove hardcoded `'IIT Madras'` in `src/utils/citationParser.ts`**: Replace with `raw.university || raw.metadata?.university || ''`.
- [ ] **Fix 2: Add compound citation regex in `parseCitations`**: Support `[1, 2, 3]` and render distinct interactive badges.
- [ ] **Fix 3: Remove `/api/graphrag/subgraph-query` endpoint drift in `endpoints.ts` and `ChatService.ts`**: Target `POST /api/chat` exclusively.
- [ ] **Fix 4: Remove deprecated `parser: 'docling'` and `full_potential` from `ChatService.ts`**: Clean up request payload.
- [ ] **Fix 5: Verify PDF viewer deep-linking with multi-institute PDFs**: Test jump navigation against NIPGR, BRIC, and DBT documents.

---

## 5. Ongoing Review & Audit Log

| Date | Commit Audited | Status | Summary of Feedback / Findings |
| :--- | :--- | :--- | :--- |
| **2026-09-24** | `615190a` | **Audited** | UI architecture is strong; identified 6 contract divergences (hardcoded IIT Madras, compound citations, endpoint fallback drift, deprecated payload flags). Action items logged above. |

*Feel free to commit your questions, updates, and responses directly to this branch `conv`! We will pull the latest frontend commits, test end-to-end integration, and keep this document up to date.*
