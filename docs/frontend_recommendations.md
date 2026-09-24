# RAISE Frontend Integration & Architectural Recommendations

**Author**: RAISE Backend Engineering Team  
**Date**: September 2026  
**Audience**: Frontend Integration Engineers & UI Architects  
**Branch Policy**: Strict Branch Isolation (Backend engineers work exclusively on `siddharth-semantification` / `backend`; Frontend engineers work exclusively on `frontend`).

---

## 1. Executive Summary

In response to the requirements outlined in [`docs/backend_improvement.md`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/docs/backend_improvement.md), the backend team has completed all requested features, performance optimizations, and contract standardizations.

This document details:
1. **Contract specifications** for updated and newly implemented backend endpoints.
2. **Key architectural discoveries** and specific recommendations for the frontend team to achieve optimal performance and UX.
3. **One minor bug in `ChatService.ts`** that prevents streaming follow-up questions from populating in the UI.

---

## 2. Key Actionable Recommendations for Frontend Developers

### 🔴 Recommendation 1: Map `follow_up_inquiries` in `ChatService.ts` Streaming Handler
- **Location**: [`frontend/src/services/ChatService.ts`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/frontend/src/services/ChatService.ts) (lines ~197–225 in `querySubgraph`)
- **Issue**: 
  When `/api/chat` completes streaming, the backend emits `meta.follow_up_inquiries` in the terminal SSE payload. 
  In [`RaisePage.tsx`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/frontend/src/features/raise/RaisePage.tsx#L635), the UI relies on:
  ```typescript
  backendFollowUps: resp?.follow_up_inquiries || resp?.suggestions
  ```
  However, in `ChatService.ts`, `synthesizedResp` does not forward `meta.follow_up_inquiries`. Consequently, `resp.follow_up_inquiries` is `undefined`, and dynamic follow-up chips are not shown.
- **Frontend Fix**:
  Add `follow_up_inquiries` to `synthesizedResp` in `frontend/src/services/ChatService.ts`:
  ```typescript
  const synthesizedResp: SubgraphQueryResponse = {
    query: req.query,
    grounded_answer: streamRes.text,
    latency_sec: durationSec,
    execution_time: durationSec,
    traceability_score: typeof meta.traceability_score === 'number' ? meta.traceability_score : 0.95,
    subgraph,
    citations,
    verified_claims: (Array.isArray(meta.verified_claims) ? meta.verified_claims : []) as any[],
    quality_gate_decision: meta.quality_gate_decision || 'accept',
    selected_tools: (Array.isArray(meta.selected_tools) ? meta.selected_tools : []) as string[],
    cypher_repair_count: meta.cypher_repair_count ?? 0,
    path_critic_expanded: meta.path_critic_expanded ?? false,
    top_chunks: (Array.isArray(meta.top_chunks) ? meta.top_chunks : []) as any[],
    retry_count: meta.retry_count ?? 0,
    decomposed_queries: (Array.isArray(meta.decomposed_queries) ? meta.decomposed_queries : []) as string[],
    // 👇 ADD THIS LINE TO ACTIVATE FOLLOW-UP CHIPS:
    follow_up_inquiries: Array.isArray(meta.follow_up_inquiries) ? meta.follow_up_inquiries : (meta.suggestions || []),
    persisted: meta.persisted,
    saved: meta.saved,
    persistence_status: meta.persistence_status,
    persistence_error: meta.persistence_error,
  };
  ```

---

### 🟡 Recommendation 2: Handling HTTP 503 in Session History Fetch
- **Location**: [`frontend/src/features/raise/RaisePage.tsx`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/frontend/src/features/raise/RaisePage.tsx#L301-L370)
- **Backend Change**:
  The backend endpoints `GET /api/chat/sessions` and `GET /api/chat/history` now return **HTTP 503** (Service Unavailable) instead of returning an empty array `[]` when the PostgreSQL connection pool is temporarily reconnecting or cycling.
- **Frontend Benefit & Recommendation**:
  Ensure the frontend's API client inspects status 503 and treats it as a transient cache-preservation state:
  - Do **not** overwrite local storage or clear sidebar sessions on 503.
  - Display a subtle non-blocking banner: *"Connecting to storage..."* while keeping the active UI and local session tabs interactive.

---

### 🟢 Recommendation 3: PDF Streaming & Deep-Linking (`#page=N`)
- **Location**: [`frontend/src/components/citations/CitationBadge.tsx`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/frontend/src/components/citations/CitationBadge.tsx) and [`InlinePdfViewer.tsx`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/frontend/src/components/citations/InlinePdfViewer.tsx)
- **Backend Status**:
  `GET /api/pdf/{filename}` now returns:
  - `Content-Disposition: inline; filename="{filename}"` (renders directly in-browser, preventing unwanted forced downloads).
  - `Accept-Ranges: bytes` (supports standard HTTP `206 Partial Content` chunk streaming).
  - `Cache-Control: public, max-age=86400` (browser caches large PDFs locally).
- **Recommendation**:
  The frontend can link directly to:
  ```text
  /api/pdf/{pdf_filename}#page={primary_page}
  ```
  All backend chunk indices now guarantee 1-indexed physical PDF page numbering (`primary_page >= 1`).

---

### 🟢 Recommendation 4: User Satisfaction Feedback Analytics Dashboard
- **Location**: [`frontend/src/services/ChatService.ts`](file:///c:/Users/Siddharth%20Tripathi/Documents/raise/frontend/src/services/ChatService.ts#L727)
- **Backend Addition**:
  The backend now exposes `GET /api/feedback/stats` in addition to `POST /api/feedback`.
- **Response**:
  ```json
  {
    "thumbs_up": 12,
    "thumbs_down": 2,
    "satisfaction_ratio": 0.857,
    "total_feedback": 14
  }
  ```
- **Recommendation**:
  The frontend settings or operator dashboard can consume this endpoint to display a live satisfaction gauge/widget for the system operator.

---

## 3. Endpoints & API Contract Reference

### 1. Dynamic Suggestions: `GET /api/suggestions`
- **Query Parameters**:
  - `active_docs` (optional, string): Comma-separated list of filenames in the current drawer (e.g. `BRIC-Annual-Report-2025.pdf`).
  - `session_id` (optional, string): Current session identifier.
  - `limit` (optional, integer, default: 4, min: 1, max: 8).
- **Behavior**:
  - If `active_docs` is omitted, empty, or whitespace: Returns `[]` immediately (no global cross-document entity bleed).
  - If `active_docs` contains filenames: Scopes Neo4j subgraphs and chunk indices strictly to chunks belonging to those filenames, generating contextual queries.
- **Response Schema (`200 OK`)**:
  ```json
  [
    {
      "query": "What collaborative research initiatives are driven by the centre?",
      "category": "Relational Synthesis",
      "complexity": "intermediate"
    }
  ]
  ```

---

### 2. Chat Query & Streaming: `POST /api/chat`
- **Request Body**:
  ```json
  {
    "message": "Summarize the major accomplishments in 2024-25",
    "query": "Summarize the major accomplishments in 2024-25",
    "mode": "fast",
    "stream": true,
    "session_id": "session-uuid-123",
    "active_docs": ["BRIC-Annual-Report-2025.pdf"],
    "top_k": 4
  }
  ```
- **SSE Stream Contract (`stream: true`)**:
  - Token chunks:
    ```text
    data: {"text": "In "}
    data: {"text": "2024-25, "}
    ```
  - Terminal completion chunk:
    ```text
    data: {
      "status": "completed",
      "grounded_answer": "In 2024-25, the Council achieved significant milestones [1].",
      "citations": [
        {
          "citation_index": 1,
          "chunk_id": "BRIC_Annual_Report_2025_p012_c03",
          "document_id": "BRIC_Annual_Report_2025",
          "pdf_filename": "BRIC-Annual-Report-2025.pdf",
          "primary_page": 12,
          "heading": "1.0 Executive Summary",
          "plain_text": "During the fiscal year 2024-25, major biotechnology research initiatives...",
          "university": "Biotechnology Research and Innovation Council",
          "similarity": 0.94
        }
      ],
      "follow_up_inquiries": [
        "What were the primary budgetary allocations for biotechnology clusters?",
        "Which new research institutes were onboarded in this fiscal cycle?",
        "What translational medical technologies were licensed?"
      ],
      "decomposed_queries": [
        "Major accomplishments 2024-25"
      ],
      "subgraph": { "nodes": [], "edges": [] },
      "quality_gate_decision": "accept"
    }
    ```

---

### 3. Feedback Submission: `POST /api/feedback`
- **Request Body**:
  ```json
  {
    "session_id": "session-uuid-123",
    "rating": "thumbs_up",
    "query": "Summarize the major accomplishments in 2024-25",
    "message_id": "turn-1",
    "reason": "Accurate page citations and concise summary"
  }
  ```
- **Response Schema (`200 OK`)**:
  ```json
  {
    "status": "recorded",
    "session_id": "session-uuid-123",
    "rating": "thumbs_up",
    "message": "Feedback recorded successfully"
  }
  ```

---

### 4. Feedback Telemetry Stats: `GET /api/feedback/stats`
- **Response Schema (`200 OK`)**:
  ```json
  {
    "thumbs_up": 6,
    "thumbs_down": 1,
    "satisfaction_ratio": 0.857,
    "total_feedback": 7
  }
  ```

---

### 5. Chat History & Persistence:
- **`GET /api/chat/sessions`**: Authoritative session list from PostgreSQL. Returns `503` if DB unavailable.
- **`GET /api/chat/history?session_id={id}`** (or `?thread_id={id}`): High-speed Redis cache-aside read with PostgreSQL fallback.
- **`POST /api/chat/history`**: Synchronizes session metadata and messages idempotently using SHA-256 message hashing (`uq_session_message_turn` constraint), preventing duplicate messages.
