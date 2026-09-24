# RAISE Backend Improvement Specification & Architectural Roadmap

**Author**: Senior Systems Architect & Frontend Integration Team  
**Date**: September 2026  
**Target Architecture**: FastAPI Gateway, LangGraph 15-Node Cyclical RAG Pipeline, Neo4j Knowledge Graph, ChromaDB Vector Store, vLLM / NVIDIA RTX 3090 Inference Engine  
**Live Testing Reference**: `https://limousines-phoenix-con-interval.trycloudflare.com`

---

## 1. Executive Summary & Root Cause Analysis

During end-to-end integration and live user testing of the RAISE frontend against the local FastAPI backend (exposed via temporary Cloudflare tunnels), several architectural bottlenecks and behavioral regressions were identified. 

The most critical user-facing issues include:
1. **Cross-Document Citation Bleed in Suggestions**: Calling `GET /api/suggestions` returns queries derived from unrelated PDFs in the Neo4j graph (e.g., questions regarding *Prof. V. Kamakoti, Department of Civil Engineering, and Ph.D. degrees* from an academic annual report appear even when the user has only attached `IITMRP Annual Report.pdf`).
2. **Missing In-Text Citation Anchors**: The LLM frequently synthesizes factual responses without placing citation markers (`[1]`, `[2]`) in the text body, forcing the frontend to fall back to post-hoc heuristic placement.
3. **Physical vs. Printed Page Number Mismatches**: Citations occasionally cite printed page numbers or 0-indexed chunk offsets rather than the 1-indexed physical PDF page, breaking deep-linking to `#page=N` in native browser PDF viewers.
4. **SSE Completion Payload Inconsistencies**: In streaming mode (`stream: true`), the terminal SSE event emitted by `/api/chat` lacked unified schemas across responses, previously dropping citation arrays before client-side patches were applied.
5. **PDF Streaming & Large File Handling**: Serving institutional PDFs (e.g. `IITMRP Annual Report.pdf` at 28.8 MB) through `/api/pdf/{filename}` without strict byte-range support (`Accept-Ranges: bytes`) causes latency spikes and viewer stalls over tunnel connections.

This document details **what to append**, **what to update**, and **what to remove** in the backend repository.

---

## 2. What to APPEND (New Features & Endpoints)

### A. Document-Scoped Dynamic Query Suggestion Generation in `/api/suggestions`
- **Root Cause & Frontend Policy**:
  - The frontend has enforced a **strict zero-hardcoding policy**. All legacy static questions (e.g. *"What collaborative research initiatives and industry-aligned mandates are driven through IIT Madras Research Park??"*) and client-side institution keyword heuristics have been completely removed.
  - The frontend now relies **100% on the backend** to compute and serve dynamic suggestions.
  - If the backend returns `[]`, the frontend cleanly renders no suggestion bubbles.
- **Specification to Implement in Backend**:
  - Route: `GET /api/suggestions`
  - Parameters:
    - `active_docs`: Comma-separated list of filenames or document IDs currently attached in the user's workspace/drawer (e.g. `?active_docs=IITMRP_Annual_Report.pdf`).
    - `session_id`: Active chat session identifier.
    - `limit`: Number of suggestions to return (default: `4`, range: `1..8`).
  - Generation Logic:
    1. **If `active_docs` is empty or not provided**: Immediately return an empty list `[]`. Do NOT return unconstrained global graph entities.
    2. **Entity & Community Extraction from Neo4j / ChromaDB**:
       Query Neo4j for high-centrality entities and community summaries linked to the active documents:
       ```cypher
       MATCH (d:Document)<-[:PART_OF]-(c:Chunk)-[:MENTIONS]->(e:Entity)
       WHERE d.filename IN $active_docs OR d.id IN $active_docs
       WITH e, count(c) AS frequency
       ORDER BY frequency DESC LIMIT 10
       RETURN e.name AS entity, e.type AS type, e.description AS description
       ```
    3. **One-Shot / Few-Shot LLM Dynamic Question Synthesis**:
       Pass the top entities and chunk summary to a lightweight fast LLM call (or vLLM prompt):
       ```python
       prompt = f"""
       Based on the following active research document topics and entities:
       {entities_context}

       Generate {limit} concise, high-value exploratory questions that an investigator or analyst would ask.
       Rules:
       - Every question must be directly grounded in the provided topics.
       - Questions must be natural, diverse, and under 80 characters.
       - Return JSON only: [{{"query": "...", "category": "...", "grounding_confidence": "95%"}}]
       """
       ```
    4. **FastAPI Route Implementation**:
       ```python
       from fastapi import APIRouter, Query
       from typing import List, Optional
       from pydantic import BaseModel, Field

       class SuggestionItem(BaseModel):
           query: str = Field(..., description="The dynamic exploratory question text")
           category: Optional[str] = Field(None, description="Domain / Topic category")
           grounding_confidence: Optional[str] = Field("95%", description="Confidence score")
           complexity: Optional[str] = Field("intermediate", description="basic, intermediate, advanced")

       @router.get("/api/suggestions", response_model=List[SuggestionItem])
       async def get_document_suggestions(
           active_docs: Optional[str] = Query(None, description="Comma-separated filenames or doc IDs"),
           session_id: Optional[str] = Query(None),
           limit: int = Query(4, ge=1, le=8)
       ):
           if not active_docs or not active_docs.trim():
               return []
           doc_list = [d.strip() for d in active_docs.split(",") if d.strip()]
           if not doc_list:
               return []
           return await suggestion_engine.generate_scoped_suggestions(doc_list, limit=limit)
       ```

### B. High-Probability Contextual Follow-Up Inquiries in `/api/chat` Completion Payload
- **Problem**: Following each assistant answer, users expect 2 to 4 high-probability contextual follow-up questions (similar to ChatGPT and NotebookLM follow-up chips) directly related to *what was just answered*.
- **Specification to Implement in Backend**:
  - In the terminal SSE payload of `/api/chat` (`data: {"status": "completed", ...}`) or standard JSON response, include a `follow_up_inquiries` array (or `suggestions` array) generated dynamically during the LangGraph synthesis step.
  - In the LangGraph synthesis node, prompt the model to output 3 natural follow-ups based on the synthesized answer.
  - Payload Schema:
```json
{
  "status": "completed",
  "sources": ["IITMRP Annual Report.pdf"],
  "citations": [
    {
      "citation_index": 1,
      "document_id": "IITMRP_Annual_Report",
      "pdf_filename": "IITMRP Annual Report.pdf",
      "primary_page": 20,
      "heading": "4.0 Boot Camp",
      "plain_text": "At IIT Madras Research Park, ecosystem enablers are strategic partners..."
    }
  ],
  "follow_up_inquiries": [
    "What specific metrics define success in the Boot Camp program?",
    "How are seed funds distributed among incubation cohorts?",
    "Which industry partners collaborate with this centre?"
  ],
  "decomposed_queries": [
    "Identify ecosystem enablers at the research park",
    "Extract incubation funding statistics"
  ],
  "subgraph": { "nodes": [], "edges": [] }
}
```

### C. System Prompt Citation Enforcement in LangGraph Generation Node
- **Specification to Append**:
  - Update the LangGraph synthesis node system prompt to strictly instruct the model to append bracketed citation indices (`[1]`, `[2]`) immediately after the factual statement it supports.
  - System prompt rule addition:
    > "CRITICAL CITATION RULE: You MUST ground every factual claim, metric, or entity with an inline citation bracket referencing the source chunk index, e.g., 'The Chennai Angels has invested over INR 150 Cr [1].' Do not use bold unicode numbers (e.g. do NOT use [𝟏]). Use only standard ASCII brackets: [1], [2]."

### D. CRITICAL: Citation Metadata Standardization (Why Citations Show "Document" & Missing Page Numbers)
- **Root Cause Analysis of the "Document" & Missing Page Bug**:
  1. **Missing / Empty `citations` in SSE**: In `/api/chat` streaming mode, the completion chunk sometimes omits the `citations: [...]` array, or emits `citations: []`. When the user clicks `[1]`, the frontend has no source object and falls back to displaying `"Document"` with an `undefined` page number.
  2. **Non-Standard Field Naming**: Some backend serializers emit `filename`, `doc_name`, `page`, `page_number`, or `text` instead of standard `pdf_filename`, `primary_page`, and `plain_text`.
  3. **Unindexed / 0-Indexed Chunk Offsets**: PyMuPDF or Docling chunks frequently store `printed_page: null` while omitting `primary_page` or recording it as a 0-indexed integer (`0` instead of `1`).
  4. **Failure to Populate from `top_chunks`**: When the LangGraph synthesizer creates an answer from retrieved chunks, it must explicitly serialize those chunks into the `citations` list in the response.

- **Mandatory Pydantic Citation Schema**:
```python
from pydantic import BaseModel, Field
from typing import Optional

class CitationItem(BaseModel):
    citation_index: int = Field(..., ge=1, description="1-indexed citation ID corresponding to [1], [2]")
    chunk_id: str = Field(..., description="Unique chunk identifier, e.g. IITMRP_Annual_Report_p020_c21_01")
    document_id: str = Field(..., description="Document identifier, e.g. IITMRP_Annual_Report")
    pdf_filename: str = Field(..., description="Full filename with extension, e.g. 'IITMRP Annual Report.pdf'")
    primary_page: int = Field(..., ge=1, description="1-indexed physical PDF page number for #page=N browser deep-linking")
    heading: Optional[str] = Field("", description="Section or chapter title, e.g. '4.0 Boot Camp'")
    plain_text: str = Field(..., description="Clean excerpt of the passage supporting the claim")
    university: Optional[str] = Field("IIT Madras Research Park (IITMRP)", description="Institutional provenance")
    similarity: Optional[float] = Field(0.95, description="Cosine / RRF relevance score")
```

- **LangGraph Serializer Fix (Example Python Implementation)**:
```python
def serialize_citations(retrieved_chunks: list, active_doc_filename: str) -> list[dict]:
    citations = []
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        meta = chunk.get("metadata", {})
        
        # 1. Resolve 1-indexed physical page
        page = meta.get("primary_page") or meta.get("physical_page") or meta.get("page")
        if not page or page < 1:
            # Fallback: extract page from chunk_id string (e.g. "IITMRP_Annual_Report_p020_c21_01" -> 20)
            chunk_id = chunk.get("chunk_id", "")
            match = re.search(r"_p0*(\d+)", chunk_id)
            page = int(match.group(1)) if match else 1
            
        # 2. Resolve PDF filename
        pdf_name = meta.get("pdf_filename") or meta.get("filename") or active_doc_filename or "Document.pdf"
        
        citations.append({
            "citation_index": idx,
            "chunk_id": chunk.get("chunk_id") or chunk.get("id") or f"chunk_{idx}",
            "document_id": meta.get("doc_id") or pdf_name.replace(".pdf", ""),
            "pdf_filename": pdf_name,
            "primary_page": int(page),
            "heading": meta.get("heading") or "",
            "plain_text": chunk.get("text", "").strip(),
            "university": meta.get("university") or "IIT Madras",
            "similarity": float(chunk.get("similarity", 0.95)),
        })
    return citations
```

### E. Clean Inline Citation Bracket Formatting & Grouping
- **Current Issue**: The LLM occasionally emits verbose inlined text like `(Annual Report.pdf, Page 8) [1]:` or `(p. 1) [1]`, polluting the synthesized response body.
- **Specification for Backend Prompt**:
  - Synthesizer prompts must mandate clean ASCII brackets:
    - Single citation: `[1]`
    - Multi-citation: `[1, 2]` or `[1, 3]`
  - Instruct the model never to repeat the PDF filename, page number, or redundant labels inside the text prose itself.
  - The frontend now features an ultra-sleek, compact, dark/black tooltip (`bg-black/95`) that cleanly renders single or multiple citations responsively, with the page number displayed cleanly in the header badge (`Page N`), and an instant deep-link (`View PDF ↗`) without repetitive page clutter.

---

## 3. What to UPDATE (Bug Fixes & Enhancements)

### A. Fix Physical PDF Page Number Ingestion & Mapping
- **Current Issue**: The chunk metadata stored in ChromaDB and Neo4j frequently records `page` as an arbitrary integer, printed header number, or 0-indexed chunk offset.
- **Required Fix**:
  - When IBM Docling or PyMuPDF parses the PDF, record two distinct page fields on every chunk:
    1. `physical_page`: **1-indexed physical page number** of the PDF file (mandatory for `#page=N` browser viewer deep-linking).
    2. `printed_page`: Optional printed document page number (e.g. page Roman numerals 'iv' or '16').
  - Ensure the citation serialization always maps `primary_page = chunk.metadata["physical_page"]`.

### B. Standardize PDF Streaming Endpoint (`GET /api/pdf/{filename}`)
- **Current Issue**: When users click a citation to open the PDF in a new tab, large PDFs (25–35 MB) can buffer slowly or trigger browser download prompts instead of in-tab viewing.
- **Required Fix**:
  - Ensure `Content-Disposition: inline; filename="{filename}"` header is always set (never `attachment`).
  - Set `Content-Type: application/pdf`.
  - Implement HTTP `206 Partial Content` with `Accept-Ranges: bytes` support via FastAPI's `FileResponse` or streaming generator so the browser's native PDF reader can stream and jump to `#page=N` instantly.

```python
@router.get("/api/pdf/{filename}")
async def serve_pdf(filename: str, request: Request):
    file_path = storage_service.resolve_pdf_path(filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found.")
    
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{file_path.name}"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400"
        }
    )
```

### C. Clean Text Excerpts in Citations
- **Current Issue**: `plain_text` in citation payloads frequently contains raw parser artifacts like `[Section Context: ...]` prefixes, OCR control characters (`\x00`, `\x08`), or consecutive repeated lines.
- **Required Fix**:
  - Sanitize chunk text prior to sending: strip parser scaffolding and return only the clean, human-readable paragraph or table row.

---

## 4. What to REMOVE (Technical Debt & Unnecessary Complexity)

| Target to Remove | Location / Subsystem | Rationale |
| :--- | :--- | :--- |
| **Unscoped / Cross-Document Suggestions** | `api/routes/suggestions.py` | **CRITICAL**: The current `/api/suggestions` queries Neo4j globally across all documents, returning questions about *Prof. V. Kamakoti, Department of Civil Engineering, and Ph.D. Degrees* from other annual reports even when the user only attached `IITMRP Annual Report.pdf`. This unscoped logic must be completely removed or rewritten to enforce strict document isolation. |
| **Hardcoded `100%` & Category Metadata** | `api/routes/suggestions.py` | Hardcoded `"grounding_confidence": "100%"`, `"complexity": "Multi-hop Relational Synthesis"`, and `"category": "Governance & Institutional Strategy"` create visual clutter and should be removed from API payloads. |
| **Leaked Internal Chunk IDs & Raw Math Scores** | Citation Serializer (`api/serializers.py`) | Do not expose raw internal chunk hashes like `IITMRP_Annual_Report_p020_c21_01` or raw cosine similarities (`similarity: 0.893`) in public UI payloads. The frontend only needs `citation_index`, `pdf_filename`, `primary_page`, `heading`, and `plain_text`. |
| **Separate Broken Modal UI Payloads** | Gateway Response Handlers | Remove legacy modal metadata (`EXTRACTED HEADING`, `CHUNK ID`, `RELEVANCE NaN%`). The user experience is unified around direct in-tab PDF navigation. |
| **Hardcoded CORS / Host Assumptions** | `main.py` Middleware | Ensure Cloudflare tunnel headers (`X-Forwarded-Proto`, `cf-connecting-ip`) are respected, and dynamic origins (`*` or tunnel domains) are allowed without CORS preflight blocks. |

---

## 5. Prioritized Backend Implementation Roadmap

### Phase 1: High Priority (Immediate Impact)
1. **Scope `/api/suggestions` by Document**:
   - Filter Neo4j Cypher query by `active_docs` parameter.
   - Prevent cross-document suggestion bleed immediately.
2. **Enforce Inline Citation Markers in System Prompt**:
   - Add prompt constraints forcing standard ASCII `[1]`, `[2]` citation brackets after statements.
3. **Verify 1-Indexed `primary_page`**:
   - Guarantee `primary_page` matches the physical PDF page index.

### Phase 2: Medium Priority (Stability & Polish)
1. **Enhance `/api/pdf/{filename}`**:
   - Add `Accept-Ranges: bytes` and `Content-Disposition: inline`.
2. **Emit `follow_up_inquiries`**:
   - Return dynamic question bubbles in the completion event.
3. **Clean Citation Text Snippets**:
   - Strip internal Docling scaffolding (`[Section Context: ...]`).

### Phase 3: Long-term Architecture
1. **Cyclical LangGraph Verification**:
   - Add a verification node that checks if every generated claim has a matching chunk index.
2. **ChromaDB Multi-Tenant Session Collections**:
   - Isolate document chunk indexes per user session drawer.

---

## 6. PostgreSQL & Redis Persistence Architecture (Fixing "Empty Recent Chats" & Session Glitches)

### A. Live System Audit & Root Cause Analysis
During active system diagnostic probing of `https://limousines-phoenix-con-interval.trycloudflare.com` via `/api/dev/checkup` and `/api/dev/recent-chats`, the operational telemetry reported:
- **PostgreSQL 16.15**: Connected (latency `0.57ms`), holding `28` chat messages.
- **Redis 7.4.11**: Connected (latency `0.65ms`), holding `23` keys across `1.69MB`.

However, severe data integrity issues and loading glitches were uncovered:

#### 1. Quadruplicate Message Writes (Lack of Idempotency)
Inspecting `/api/dev/recent-chats` revealed that the exact same query turn was inserted **4 separate times** in PostgreSQL for `session_id="default"` within seconds:
```
[2026-09-21 22:48:30] "What are the ecosystem enablers and investments..."
[2026-09-21 22:48:36] "What are the ecosystem enablers and investments..."
[2026-09-21 22:49:03] "What are the ecosystem enablers and investments..."
[2026-09-21 22:49:03] "What are the ecosystem enablers and investments..."
```
**Why this happens**:
- Every retry, duplicate POST, or streaming token chunk invokes an unconstrained `INSERT INTO chat_messages` without a unique hash or turn index.
- There is no composite unique constraint (`session_id`, `turn_index`, or `message_hash`).

#### 2. Why Recent Chats Sometimes Appear Empty (The "Empty Sidebar" Glitch)
1. **Parameter Name Divergence (`session_id` vs `thread_id`)**:
   - Some backend endpoints query by `session_id`, while others expect `thread_id`. If Redis keys are indexed as `raise:session:{session_id}` but the incoming query passes `thread_id` (or vice-versa), Redis misses the key and returns an empty list `[]`.
2. **Redis Cache Expiration (TTL) without PostgreSQL Fallback**:
   - If session memory is kept in Redis with a short TTL (e.g. 1 hour or 24 hours), sessions vanish as soon as the TTL expires unless PostgreSQL is queried as the authoritative fallback.
3. **Silent Exception Drops on Database Connection Hiccups**:
   - When a connection pool drop occurs (e.g. over a temporary Cloudflare tunnel restart or Docker network reset), backend query routes wrap the database call in `try... except Exception: return []`. Returning an empty array `[]` on error tricks the client into believing no chats exist, wiping the UI list.
4. **Summary List vs Full Turn Disconnect**:
   - `GET /api/chat/sessions` returns session metadata with `message_count`, but omits `messages: [...]`. If the frontend selects a session and calls `GET /api/chat/history?session_id=...`, any delay or 500 error on that secondary call causes the chat window to render completely blank.

---

### B. PostgreSQL Relational Schema & Migration DDL

To permanently fix session vanishing and turn duplication, implement the following schema in PostgreSQL:

```sql
-- 1. Authoritative Chat Sessions Table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR(64) PRIMARY KEY,              -- Session UUID or thread_id
    username VARCHAR(128) NOT NULL DEFAULT 'Operator',
    title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
    attached_docs JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_saved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Authoritative Chat Message Turns Table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(64) NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    turn_index INT NOT NULL DEFAULT 0,
    role VARCHAR(32) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    mode VARCHAR(16) NOT NULL DEFAULT 'fast',
    sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    duration_sec DOUBLE PRECISION DEFAULT 0.0,
    message_hash VARCHAR(64) NOT NULL,        -- SHA-256(session_id + role + content)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Prevents duplicate turn inserts
    CONSTRAINT uq_session_message_turn UNIQUE (session_id, message_hash)
);

-- 3. High-Performance Indices
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated 
    ON chat_sessions (username, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created 
    ON chat_messages (session_id, created_at ASC);
```

---

### C. Redis Caching Strategy (Write-Through + Cache-Aside)

Use Redis as a high-speed cache and rate-limiter, **not** as the primary storage.

#### 1. Key Naming Standards
| Redis Key Pattern | Type | TTL | Purpose |
| :--- | :--- | :--- | :--- |
| `raise:session:{session_id}:meta` | Hash | 7 Days (Sliding) | Fast metadata lookup (`title`, `username`, `attached_docs`) |
| `raise:session:{session_id}:turns` | List (JSON strings) | 7 Days (Sliding) | Chronological message turns for quick sidebar selection |
| `raise:ratelimit:{user_or_ip}` | String / Hash | 60 Seconds | Token bucket rate limiter |
| `raise:stream:{request_id}:cancel` | String | 5 Minutes | Real-time SSE stream abort flag |

#### 2. Write-Through Flow (When a turn completes):
1. **Transaction Begin**: Write the session metadata to `chat_sessions` (`ON CONFLICT (id) DO UPDATE SET updated_at = NOW(), title = EXCLUDED.title`).
2. Insert the message turn into `chat_messages` (`ON CONFLICT (session_id, message_hash) DO NOTHING`).
3. **Commit Transaction**.
4. **Update Redis**: Push the turn into `raise:session:{session_id}:turns` and update `raise:session:{session_id}:meta`. Reset TTL to 7 days (`EXPIRE 604800`).

#### 3. Read Flow (`GET /api/chat/history?session_id=...`):
1. Check if `raise:session:{session_id}:turns` exists in Redis.
2. If cache hit: Return the turns immediately (`latency < 2ms`).
3. If cache miss: Query `chat_messages` from PostgreSQL (`WHERE session_id = :id ORDER BY created_at ASC`), populate Redis, and return.

---

### D. FastAPI Backend Route Implementations

Implement the following routes in your FastAPI gateway (`api/routes/chat_history.py`):

```python
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

router = APIRouter(prefix="/api/chat", tags=["Sessions & History"])

class MessageTurn(BaseModel):
    role: str
    content: str
    text: Optional[str] = None
    mode: Optional[str] = "fast"
    sources: Optional[List[Any]] = []
    citations: Optional[List[Any]] = []
    durationSec: Optional[float] = 0.0
    created_at: Optional[str] = None

class ChatSyncPayload(BaseModel):
    session_id: Optional[str] = None
    thread_id: Optional[str] = None
    username: Optional[str] = "Operator"
    title: Optional[str] = "New Chat"
    messages: List[MessageTurn] = []
    attached_docs: Optional[List[str]] = []
    is_saved: Optional[bool] = False

def compute_msg_hash(session_id: str, role: str, content: str) -> str:
    raw = f"{session_id}:{role}:{content.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

@router.get("/sessions")
async def list_chat_sessions(
    username: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Authoritative session list from PostgreSQL.
    CRITICAL: Never return [] on DB connection errors; raise HTTP 503 so frontend preserves cache.
    """
    try:
        query = select(ChatSessionModel).order_by(ChatSessionModel.updated_at.desc())
        if username and username != "Operator":
            query = query.where(ChatSessionModel.username == username)
        
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        return [
            {
                "id": s.id,
                "thread_id": s.id,
                "session_id": s.id,
                "title": s.title,
                "username": s.username,
                "attached_docs": s.attached_docs or [],
                "is_saved": s.is_saved,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ]
    except Exception as exc:
        logger.error(f"PostgreSQL session query failure: {exc}")
        raise HTTPException(
            status_code=503, 
            detail="Database temporarily unreachable. Preserving client cache."
        )

@router.get("/history")
async def get_chat_history(
    session_id: Optional[str] = Query(None),
    thread_id: Optional[str] = Query(None),
    redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    target_id = session_id or thread_id
    if not target_id:
        raise HTTPException(status_code=400, detail="session_id or thread_id is required")

    # 1. Try Redis Cache
    cache_key = f"raise:session:{target_id}:turns"
    cached = await redis.lrange(cache_key, 0, -1)
    if cached:
        return {
            "session_id": target_id,
            "thread_id": target_id,
            "messages": [json.loads(turn) for turn in cached],
            "cached": True
        }

    # 2. Fallback to PostgreSQL
    try:
        result = await db.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == target_id)
            .order_by(ChatMessageModel.created_at.asc())
        )
        records = result.scalars().all()
        turns = [
            {
                "role": r.role,
                "content": r.content,
                "text": r.content,
                "mode": r.mode,
                "sources": r.sources,
                "citations": r.citations,
                "durationSec": r.duration_sec,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ]

        # Populate Redis cache for future queries
        if turns:
            pipeline = redis.pipeline()
            pipeline.delete(cache_key)
            pipeline.rpush(cache_key, *[json.dumps(t) for t in turns])
            pipeline.expire(cache_key, 604800)  # 7 days
            await pipeline.execute()

        return {"session_id": target_id, "thread_id": target_id, "messages": turns, "cached": False}
    except Exception as exc:
        logger.error(f"PostgreSQL history fetch failure for {target_id}: {exc}")
        raise HTTPException(status_code=503, detail="Database history retrieval failed")

@router.post("/history")
async def sync_chat_history(
    payload: ChatSyncPayload,
    redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    target_id = payload.session_id or payload.thread_id
    if not target_id:
        raise HTTPException(status_code=400, detail="session_id or thread_id is required")

    try:
        # 1. Upsert session metadata
        session_stmt = (
            insert(ChatSessionModel)
            .values(
                id=target_id,
                username=payload.username or "Operator",
                title=payload.title or "New Chat",
                attached_docs=payload.attached_docs or [],
                is_saved=bool(payload.is_saved),
                updated_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=[ChatSessionModel.id],
                set_={
                    "title": payload.title or ChatSessionModel.title,
                    "attached_docs": payload.attached_docs or ChatSessionModel.attached_docs,
                    "is_saved": payload.is_saved if payload.is_saved is not None else ChatSessionModel.is_saved,
                    "updated_at": datetime.utcnow(),
                }
            )
        )
        await db.execute(session_stmt)

        # 2. Insert message turns idempotently
        synced_count = 0
        for idx, msg in enumerate(payload.messages):
            content = msg.content or msg.text or ""
            if not content:
                continue
            m_hash = compute_msg_hash(target_id, msg.role, content)
            
            msg_stmt = (
                insert(ChatMessageModel)
                .values(
                    session_id=target_id,
                    turn_index=idx,
                    role=msg.role,
                    content=content,
                    mode=msg.mode or "fast",
                    sources=msg.sources or [],
                    citations=msg.citations or [],
                    duration_sec=msg.durationSec or 0.0,
                    message_hash=m_hash,
                )
                .on_conflict_do_nothing(
                    constraint="uq_session_message_turn"
                )
            )
            res = await db.execute(msg_stmt)
            if res.rowcount > 0:
                synced_count += 1

        await db.commit()

        # 3. Refresh Redis Cache
        cache_key = f"raise:session:{target_id}:turns"
        await redis.delete(cache_key)
        
        return {
            "status": "synchronized",
            "id": target_id,
            "session_id": target_id,
            "thread_id": target_id,
            "synced_count": synced_count,
            "total_messages": len(payload.messages)
        }
    except Exception as exc:
        await db.rollback()
        logger.error(f"Failed to sync session {target_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
```

---

### E. Verification Checklist for Backend Engineer
- [ ] Run the migration DDL in PostgreSQL (`psql -d raise_db -f schema.sql`).
- [ ] Ensure `uq_session_message_turn` unique constraint is active to prevent quadruplicate message turns.
- [ ] Verify `GET /api/chat/history` accepts both `?session_id=` and `?thread_id=` query parameters.
- [ ] Verify `POST /api/chat` persists the turn to PostgreSQL inside the same transaction that updates Redis cache.
- [ ] Ensure database connectivity errors return **HTTP 503** rather than an empty list `[]` so that the frontend's local cache remains intact.

---

## 7. User Satisfaction Feedback Architecture (`POST /api/feedback` Thumbs Up / Thumbs Down)

### A. Overview & Functional Specification
The RAISE user interface provides inline satisfaction controls on every synthesized assistant response:
- **Thumbs Up** (`thumbs_up`): Indicates accurate, well-grounded retrieval, valid citation anchors, and helpful synthesis.
- **Thumbs Down** (`thumbs_down`): Indicates hallucinations, citation page mismatch, incomplete reasoning, or poor formatting.

Users can toggle their rating on and off. When submitted, the client fires `POST /api/feedback` to register the feedback into PostgreSQL.

### B. Client Request Payload Contract
- **Endpoint**: `POST /api/feedback`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "session_id": "72fd9bc2-dd1f-472c-94e2-2ec89eecf4dc",
  "rating": "thumbs_up",
  "query": "What are the ecosystem enablers and investments by The Chennai Angels?",
  "message_id": "msg-1",
  "reason": "Clear citations and accurate financial data"
}
```

- **Response Contract (HTTP 200 OK)**:
```json
{
  "status": "recorded",
  "session_id": "72fd9bc2-dd1f-472c-94e2-2ec89eecf4dc",
  "rating": "thumbs_up",
  "message": "Feedback recorded successfully"
}
```

### C. PostgreSQL Database Schema & Migration DDL
To store and index feedback with foreign key integrity to the chat session:

```sql
-- 1. Dedicated Feedback Audit Table
CREATE TABLE IF NOT EXISTS chat_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(64) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    message_id VARCHAR(64),
    query TEXT,
    rating VARCHAR(16) NOT NULL CHECK (rating IN ('thumbs_up', 'thumbs_down', 'positive', 'negative')),
    reason TEXT,
    client_ip VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Indices for High-Speed Aggregation
CREATE INDEX IF NOT EXISTS idx_chat_feedback_session_id 
    ON chat_feedback (session_id);

CREATE INDEX IF NOT EXISTS idx_chat_feedback_rating_created 
    ON chat_feedback (rating, created_at DESC);

-- 3. Optional denormalized feedback indicator on chat_messages table
ALTER TABLE chat_messages 
    ADD COLUMN IF NOT EXISTS feedback_rating VARCHAR(16);
```

### D. Backend Enhancements & Improvements Needed
1. **Correlate with Message Turns in PostgreSQL**:
   - In `api/routes/feedback.py`, after inserting into `chat_feedback`, update the corresponding message turn in `chat_messages` if `message_id` or `turn_index` is provided:
   ```python
   await db.execute(
       update(ChatMessageModel)
       .where(ChatMessageModel.session_id == payload.session_id)
       .values(feedback_rating=payload.rating)
   )
   ```
2. **Aggregated Analytics Endpoint (`GET /api/feedback/stats`)**:
   - Provide an operational telemetry endpoint for the operator dashboard:
   ```python
   @router.get("/api/feedback/stats")
   async def get_feedback_stats(db: AsyncSession = Depends(get_db)):
       """Returns overall thumbs_up vs thumbs_down counts, satisfaction ratio, and recent feedback."""
       result = await db.execute(
           select(
               ChatFeedbackModel.rating,
               func.count(ChatFeedbackModel.id)
           ).group_by(ChatFeedbackModel.rating)
       )
       counts = dict(result.all())
       total = sum(counts.values()) or 1
       return {
           "thumbs_up": counts.get("thumbs_up", 0),
           "thumbs_down": counts.get("thumbs_down", 0),
           "satisfaction_ratio": round(counts.get("thumbs_up", 0) / total, 3),
           "total_feedback": total
       }
   ```
3. **Automated GraphRAG Retrieval Quality Flagging**:
   - When a turn receives `thumbs_down`, flag the retrieved chunks in ChromaDB / Neo4j for re-ranking review or query rewrite training.
4. **Token Bucket Rate Limiting**:
   - Guard `POST /api/feedback` using Redis key `raise:ratelimit:feedback:{client_ip}` (limit 30 submissions per minute per IP) to prevent denial-of-service or database poisoning.


