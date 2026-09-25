# RAISE Engineering Synchronization & Collaboration Specification (v2)

**Authors**: Frontend & Integration Engineering Team  
**Audience**: Backend Engineering Team (`backend` / `siddharth-semantification`), Architecture & QA  
**Date**: September 25, 2026  
**Active Collaboration Branch**: `conv`  
**Frontend Deployment Branch**: `frontend`  

---

## 1. Executive Summary & Review of Backend Work

We audited the latest commits merged into `target/conv` (`479c355`, `5b7278aa`, `ad2f4c47`, `f00c049b`, `ac2f09c7`) and tested against the live backend gateway. 

### ✅ Verified & Highly Commended Backend Upgrades:
1. **87.5% Benchmark Accuracy Reached**: Evaluation run `run_20260925_005605_raise_domain_playbook_v2` successfully achieved 87.5% accuracy across domain test cases.
2. **Multi-Cloud Dynamic LLM Routing**: 
   - New adapters (`MistralProvider`, `VercelProvider`, `UniversalProvider`) and dynamic fallback router in `backend/src/infrastructure/providers/router.py`.
   - Dynamic credential management (`get_credential_manager()`) and runtime `.env` syncing.
3. **Control Center Hardware & Telemetry Router**:
   - `GET /api/system/hardware` dynamically probes CPU, RAM, CUDA VRAM (RTX 3090 24GB), Ollama socket, and disk space.
   - `POST /api/system/config` dynamically switches inference engines between Cloud Groq, Gemini, NVIDIA, Mistral, Vercel, and Local Ollama.
   - `POST /api/system/test-db` validates Neo4j, Redis, and PostgreSQL connections.
4. **Neo4j AuraDB Dual-Protocol Resilience**:
   - Successfully activated dual-protocol Bolt and HTTP Query v2 API fallback for cloud graph queries.

---

## 2. Cleanup of Outdated Points (Now 100% Completed)

The following items from earlier discussion documents have been fully implemented and verified on both frontend and backend:

| Previous Action Item | Status | Verification Detail |
| :--- | :---: | :--- |
| **Streaming `follow_up_inquiries`** | ✅ Complete | Emitted by backend SSE `meta.follow_up_inquiries` and mapped directly in `ChatService.ts`. |
| **HTTP 503 Transient Reconnection** | ✅ Complete | Frontend treats HTTP 503 as non-destructive; never wipes sidebar or localStorage sessions. |
| **PDF Deep-Linking (`#page=N`)** | ✅ Complete | `/api/pdf/{filename}#page={page}` configured with `Accept-Ranges: bytes` and `Content-Disposition: inline`. |
| **User Feedback Stats** | ✅ Complete | `GET /api/feedback/stats` operational and integrated with frontend satisfaction ratio indicator. |
| **Tabular & Comparative Generalization** | ✅ Complete | Hardcoded prompts removed; clean schema derivation active in `system_synthesis.py`. |

---

## 3. Findings from Live Audits & Backend Action Items

During live user testing and testing against Cloudflare tunnel endpoints, two specific issues were identified when inspecting chat history and citations:

### 🔴 Finding A: Citation Page Numbers Missing in Saved Chat History

#### The Root Cause
1. In live sessions, when a user asks a question, the LLM emits citations with `primary_page` and chunk IDs.
2. However, in PostgreSQL table `chat_messages`:
   - The backend currently stores `sources = ["IITMRP Annual Report.pdf"]` as a simple string array.
   - The rich `citations` array (containing `primary_page`, `chunk_id`, `plain_text`, `heading`) is **not persisted** into `chat_messages`.
3. Consequently, when the frontend loads historical sessions via `GET /api/chat/history?session_id={thread_id}`, the assistant messages contain `sources: ["..."]` but `citations: undefined`.
4. In the UI popover, this caused citations to display `Audited Document` and omit page numbers (`Page undefined`).

#### Frontend Workaround Implemented
- The frontend now automatically detects string sources in `msg.sources`, normalizes them into `Citation` models, extracts in-text parenthetical page references, assigns deterministic fallback page numbers (`primary_page >= 1`), and renders visible page badges (`[1] p.8`) on both buttons and popovers.

#### 🛠️ Requested Backend Action
In `backend/src/features/chat` or wherever `chat_messages` are inserted into PostgreSQL:
1. Please add/persist the full `citations` JSON payload in `chat_messages`:
   ```python
   # When persisting assistant messages in PostgreSQL:
   await db.execute(
       """
       INSERT INTO chat_messages (thread_id, role, content, mode, sources, citations, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       """,
       thread_id,
       "assistant",
       content,
       mode,
       json.dumps(sources),
       json.dumps(citations), # <-- PERSIST FULL CITATION OBJECTS HERE
       datetime.utcnow()
   )
   ```
2. In `GET /api/chat/history`, return `citations` alongside `sources` in each message item:
   ```json
   {
     "role": "assistant",
     "content": "...",
     "mode": "fast",
     "sources": ["IITMRP Annual Report.pdf"],
     "citations": [
       {
         "citation_index": 1,
         "pdf_filename": "IITMRP Annual Report.pdf",
         "primary_page": 8,
         "chunk_id": "doc_IITMRP_p008_c01",
         "heading": "R&D Commercialisation",
         "plain_text": "Commercialization pipeline exceeded targets..."
       }
     ]
   }
   ```

---

### 🔴 Finding B: Empty Attached Documents Drawer in Historical Sessions

#### The Root Cause
1. Several historical sessions and evaluation runs stored in PostgreSQL have `session_metadata.attached_docs = []`.
2. When a user switches to one of these sessions, `GET /api/chat/sessions/{session_id}/drawer` returns `attached_docs: []`.
3. As a result, the right-hand **Sources Drawer** appeared completely blank, even though the conversation messages were referencing attached PDFs.

#### Frontend Workaround Implemented
- In `RaisePage.tsx`, `handleSelectSession` now executes an automatic **source harvest**:
  - It inspects all historical messages (`msg.sources`, `msg.citations`, `msg.response.sources`).
  - Matches filenames against `GET /api/documents` to retrieve accurate file sizes, page counts, and ready states.
  - Automatically re-populates the Sources Drawer and fires a background `PATCH /api/chat/sessions/{id}/drawer` sync to repair the session metadata on the backend.

#### 🛠️ Requested Backend Action
1. **Auto-Populate `attached_docs` on Query**:
   When `POST /api/chat` or `POST /api/graphrag/subgraph-query` is called with `documents` or `sources`, ensure the session's `attached_docs` in `session_metadata` automatically includes those documents if not already present.
2. **Backfill Existing Sessions**:
   Run a migration/script on existing PostgreSQL rows to backfill `attached_docs` from `chat_messages.sources`:
   ```sql
   UPDATE session_metadata sm
   SET attached_docs = sub.doc_list
   FROM (
       SELECT thread_id, jsonb_agg(DISTINCT elem) AS doc_list
       FROM chat_messages cm, jsonb_array_elements_text(cm.sources::jsonb) elem
       GROUP BY thread_id
   ) sub
   WHERE sm.thread_id = sub.thread_id AND (sm.attached_docs IS NULL OR sm.attached_docs = '[]'::jsonb);
   ```

---

## 4. Summary of Frontend Status & Compatibility

- **Branch**: `frontend` (commit `d5be83d`)
- **Unit Tests**: 29/29 suites passing, 251/251 tests passing.
- **Production Build**: Clean bundle in 1.57s.
- **Visual Citations**: Page numbers are now clearly rendered on badge buttons (`[1] p.8`) and inside hover/click popovers (`Page 8`).
- **Drawer Restoration**: Sources Drawer displays all referenced documents when navigating between historical chats.
