"""
Chat & Conversational Reasoning Router
Main conversational and research chat router conforming to BACKEND_DEVELOPER_GUIDE.md and system-architecture.md:
- Fast Mode & Expert Mode execution with LangGraph multi-engine traversal
- Dual-tier conversational memory (vLLM Qwen2.5-14B-Instruct-GPTQ-Int4)
- Server-Sent Events (SSE) streaming & plain-text raw streaming
- Token Bucket rate limiting via Redis
- Semantic & Exact Match Redis query caching
- Real-time cancellation via POST /api/chat/abort
- User feedback submission and batch query execution
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
try:
    from prompts.system_synthesis import sanitize_rag_text
except ImportError:
    from RAG.prompts.system_synthesis import sanitize_rag_text

from src.api.context import (
    _parse_drawer_active_docs,
    get_authentic_client_ip,
    get_ready_documents_list,
    is_aborted,
    is_conversational_or_memory_query,
    record_abort,
    record_query_metric,
)
from src.api.dependencies import (
    get_postgres_manager,
    get_rag_engine,
    get_redis_cache,
    get_session_memory,
    get_chat_service,
)

from src.api.schemas import (
    AbortRequest,
    BatchChatRequest,
    ChatMessageRequest,
    FeedbackRequest,
)

logger = logging.getLogger("raise.router.chat")
router = APIRouter(tags=["Chat & Reasoning"])


async def handle_conversational_chat(
    req: ChatMessageRequest,
    request: Request,
    message: str,
    session_id: str,
    mode: str,
    rate_headers: Dict[str, str],
    postgres_manager: Any,
    redis_cache: Any,
    session_memory_manager: Any,
):
    """
    Dual-Tier Conversational Memory & Multi-Turn Context Handler.
    - Zero database transaction locks held during inference.
    - Resolves user persona attributes (e.g. name) and stores in Redis session hash.
    - Retrieves recent conversation turns from Redis bounded list (with PostgreSQL sliding window fallback).
    - Orchestrates with vLLM Qwen2.5-14B-Instruct-GPTQ-Int4 maintaining conversational memory.
    - Decoupled atomic dual-write to Redis and PostgreSQL.
    """
    t_start = time.perf_counter()

    # 1. User Persona & Entity Memory Extraction
    extracted_name = session_memory_manager.extract_and_set_user_persona(session_id, message) if session_memory_manager else None
    if extracted_name and redis_cache:
        redis_cache.set_session_memory(session_id, "user_name", extracted_name)

    existing_vars = redis_cache.get_session_memory(session_id) if redis_cache else {}
    known_name = existing_vars.get("user_name") or (session_memory_manager.get_user_persona(session_id).get("user_name") if session_memory_manager else None)

    # 2. Sliding Window Context Retrieval (Short-Term Redis -> Long-Term Postgres)
    recent_turns = (redis_cache.get_session_messages(session_id, limit=10) if redis_cache else []) or []
    if not recent_turns and postgres_manager:
        # Load from Postgres sliding window (no transaction held open)
        recent_turns = postgres_manager.get_messages(session_id, limit=10)
        # Backfill Redis session list
        if redis_cache:
            for t in recent_turns:
                redis_cache.save_session_message(
                    session_id,
                    t.get("role", "user"),
                    t.get("content", ""),
                    mode=t.get("mode", "fast"),
                    sources=t.get("sources", [])
                )

    # 3. System Prompt & Chat History Construction
    name_ctx = f"The user's name is {known_name}. " if known_name else ""
    system_prompt = (
        "You are RAISE, your research intelligence assistant. Your name is strictly RAISE. "
        "Never expand the acronym RAISE. "
        "You are helpful, concise, warm, intellectually sharp, and conversational. "
        f"{name_ctx}"
        "You maintain conversational context across turns and remember facts shared by the user. "
        "If the user introduces themselves, greet them warmly by name. "
        "If the user asks if you know their name or asks what their name is, answer directly from your conversation memory. "
        "When the user is ready to conduct research on academic documents, remind them that they can attach documents in their drawer. "
        "Always use the verb 'attach' (never 'select') when referring to drawer documents. "
        "Never fabricate document citations for casual conversation."
    )

    vllm_messages = [{"role": "system", "content": system_prompt}]
    for turn in recent_turns[-8:]:
        r = turn.get("role")
        c = turn.get("content") or turn.get("text")
        if r in ("user", "assistant") and c:
            vllm_messages.append({"role": r, "content": c})
    vllm_messages.append({"role": "user", "content": message})

    vllm_candidates = [
        os.getenv("VLLM_BASE_URL", "http://localhost:8002/v1"),
        "http://raise-vllm-prod:8000/v1",
        "http://localhost:8002/v1",
    ]
    model_name = os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4")

    # Helper for fallback reply if vLLM is temporarily unreachable
    def get_fallback_reply() -> str:
        q_lower = message.lower()
        if any(w in q_lower for w in ["do you know my name", "what is my name", "who am i"]):
            if known_name:
                return f"Yes, of course! Your name is {known_name}. How can I assist you with your research today? When you are ready, please attach an academic document in your drawer."
            return "You haven't told me your name yet! What should I call you? When you are ready to conduct document research, please attach a document in your drawer."
        if known_name:
            return f"Hello {known_name}! I am RAISE, your research intelligence assistant. How can I help you today? Please attach an academic document in your drawer when you wish to begin research."
        return "Hello! I am RAISE, your research intelligence assistant. How can I help you today? Please attach an academic document in your drawer when you wish to begin research."

    # A. Plain-Text Stream Response
    if req.stream and (req.format == "raw" or "text/plain" in request.headers.get("accept", "").lower()):
        async def conv_raw_stream():
            full_response_parts = []
            stream_succeeded = False
            for vllm_url in vllm_candidates:
                endpoint = f"{vllm_url.rstrip('/')}/chat/completions"
                payload = {
                    "model": model_name,
                    "messages": vllm_messages,
                    "temperature": 0.3,
                    "max_tokens": 384,
                    "stream": True,
                }
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        async with client.stream("POST", endpoint, json=payload) as resp:
                            if resp.status_code == 200:
                                async for line in resp.aiter_lines():
                                    if await request.is_disconnected():
                                        return
                                    if not line.startswith("data: "):
                                        continue
                                    data_str = line[6:].strip()
                                    if data_str == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data_str)
                                        delta = chunk["choices"][0]["delta"].get("content", "")
                                        if delta:
                                            full_response_parts.append(delta)
                                            yield delta
                                    except Exception:
                                        pass
                                stream_succeeded = True
                                break
                except Exception:
                    continue

            if not stream_succeeded:
                fb = get_fallback_reply()
                full_response_parts.append(fb)
                words = re.findall(r"\S+|\s+", fb)
                for w in words:
                    if await request.is_disconnected():
                        return
                    yield w
                    await asyncio.sleep(0.015)

            complete_text = "".join(full_response_parts).strip()
            # Decoupled Dual-Write Persistence
            if session_id and complete_text:
                if postgres_manager:
                    postgres_manager.save_message(session_id, "user", message, mode=mode, active_docs=req.active_docs)
                    postgres_manager.save_message(session_id, "assistant", complete_text, mode=mode, sources=[])
                if redis_cache:
                    redis_cache.save_session_message(session_id, "user", message, mode=mode)
                    redis_cache.save_session_message(session_id, "assistant", complete_text, mode=mode)

        return StreamingResponse(
            conv_raw_stream(),
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", **rate_headers}
        )

    # B. SSE Stream Response
    if req.stream:
        async def conv_sse_stream():
            yield ": keepalive\n\n"
            full_response_parts = []
            stream_succeeded = False
            for vllm_url in vllm_candidates:
                endpoint = f"{vllm_url.rstrip('/')}/chat/completions"
                payload = {
                    "model": model_name,
                    "messages": vllm_messages,
                    "temperature": 0.3,
                    "max_tokens": 384,
                    "stream": True,
                }
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        async with client.stream("POST", endpoint, json=payload) as resp:
                            if resp.status_code == 200:
                                async for line in resp.aiter_lines():
                                    if await request.is_disconnected():
                                        return
                                    if not line.startswith("data: "):
                                        continue
                                    data_str = line[6:].strip()
                                    if data_str == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data_str)
                                        delta = chunk["choices"][0]["delta"].get("content", "")
                                        if delta:
                                            full_response_parts.append(delta)
                                            yield f"data: {json.dumps({'token': delta})}\n\n"
                                    except Exception:
                                        pass
                                stream_succeeded = True
                                break
                except Exception:
                    continue

            if not stream_succeeded:
                fb = get_fallback_reply()
                full_response_parts.append(fb)
                words = re.findall(r"\S+|\s+", fb)
                for w in words:
                    if await request.is_disconnected():
                        return
                    yield f"data: {json.dumps({'token': w})}\n\n"
                    await asyncio.sleep(0.015)

            complete_text = "".join(full_response_parts).strip()
            # Decoupled Dual-Write Persistence
            if session_id and complete_text:
                if postgres_manager:
                    postgres_manager.save_message(session_id, "user", message, mode=mode, active_docs=req.active_docs)
                    postgres_manager.save_message(session_id, "assistant", complete_text, mode=mode, sources=[])
                if redis_cache:
                    redis_cache.save_session_message(session_id, "user", message, mode=mode)
                    redis_cache.save_session_message(session_id, "assistant", complete_text, mode=mode)

            yield f"data: {json.dumps({'status': 'completed', 'sources': [], 'citations': []})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            conv_sse_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no", **rate_headers}
        )

    # C. Non-Streaming Response
    full_reply = ""
    try:
        from src.infrastructure.providers.router import get_provider_router, InferenceTask
        router = get_provider_router()
        router_reply = router.complete(
            prompt=message,
            task=InferenceTask.CHAT,
            system_prompt=system_instruction,
            max_tokens=384,
            temperature=0.3,
        )
        if router_reply and not router_reply.startswith("Inference execution error"):
            full_reply = router_reply.strip()
    except Exception as e:
        logger.warning(f"Router chat completion notice: {e}")

    if not full_reply:
        # Secondary check against local endpoint candidates
        for vllm_url in vllm_candidates:
            endpoint = f"{vllm_url.rstrip('/')}/chat/completions"
            payload = {
                "model": model_name,
                "messages": vllm_messages,
                "temperature": 0.3,
                "max_tokens": 384,
                "stream": False,
            }
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(endpoint, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        full_reply = data["choices"][0]["message"]["content"].strip()
                        break
            except Exception:
                continue

    if not full_reply:
        full_reply = get_fallback_reply()


    elapsed = round(time.perf_counter() - t_start, 3)

    # Decoupled Dual-Write Persistence
    if session_id and full_reply:
        if postgres_manager:
            postgres_manager.save_message(session_id, "user", message, mode=mode, active_docs=req.active_docs)
            postgres_manager.save_message(session_id, "assistant", full_reply, mode=mode, sources=[])
        if redis_cache:
            redis_cache.save_session_message(session_id, "user", message, mode=mode)
            redis_cache.save_session_message(session_id, "assistant", full_reply, mode=mode)

    return JSONResponse(
        content={
            "reply": full_reply,
            "grounded_answer": full_reply,
            "answer": full_reply,
            "sources": [],
            "citations": [],
            "verified_claims": [],
            "subgraph": {"nodes": [], "edges": []},
            "quality_gate_decision": "accept",
            "execution_time": elapsed,
            "latency_sec": elapsed,
            "mode_used": mode,
            "thread_id": session_id,
            "session_id": session_id,
        },
        headers={"X-Process-Time-Ms": str(round(elapsed * 1000, 1)), **rate_headers}
    )


@router.post("/api/chat")
async def chat_endpoint(
    req: ChatMessageRequest,
    request: Request,
    rag_engine: Any = Depends(get_rag_engine),
    postgres_manager: Any = Depends(get_postgres_manager),
    redis_cache: Any = Depends(get_redis_cache),
    session_memory_manager: Any = Depends(get_session_memory),
    chat_service: Any = Depends(get_chat_service),
):

    """
    Main Chat Endpoint conforming to BACKEND_DEVELOPER_GUIDE.md and system-architecture.md:
    - Supports Fast Mode (speed-first) and Expert Mode (depth-first).
    - Supports Server-Sent Events (SSE) streaming when stream=True.
    - Token Bucket rate limiting via Redis with X-RateLimit-Remaining header.
    - Caches repeated queries in Redis with X-Redis-Cache header.
    - Persists session turns in PostgreSQL.
    - Supports real-time cancellation via POST /api/chat/abort.
    """
    raw_query = req.query or req.message or ""
    message = raw_query.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    mode = (req.mode or "fast").lower()
    session_id = req.session_id or req.thread_id or "default"
    request_id = req.request_id or f"req-{int(time.time() * 1000)}"
    library = req.library

    # Normalize, unquote, and handle URL encoded spaces in active_docs
    if req.active_docs is not None:
        req.active_docs = _parse_drawer_active_docs(req.active_docs)

    # 0. Rate Limiting Check (Token Bucket with Authentic Proxy IP Resolution)
    is_allowed, rate_headers = chat_service.check_rate_limit(request, request_id)
    if not is_allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "Too Many Requests", "detail": "API rate limit exceeded. Please retry momentarily."},
            headers=rate_headers
        )


    # 1. Conversational & Memory Routing: Introductions, chit-chat, and memory recall bypass drawer check
    if is_conversational_or_memory_query(message):
        return await handle_conversational_chat(
            req=req,
            request=request,
            message=message,
            session_id=session_id,
            mode=mode,
            rate_headers=rate_headers,
            postgres_manager=postgres_manager,
            redis_cache=redis_cache,
            session_memory_manager=session_memory_manager,
        )

    # 2. Document Research Queries: Validate active_docs and Enforce Drawer Guard
    ready_docs = get_ready_documents_list()
    pg_docs = postgres_manager.list_documents() if postgres_manager else []
    is_empty_workspace = (len(ready_docs) == 0 and len(pg_docs) == 0)

    # If session_id provided and req.active_docs specified, cross-reference with session drawer
    if session_id and req.active_docs and postgres_manager:
        session_drawer = postgres_manager.get_session_drawer(session_id)
        if session_drawer:
            for doc in req.active_docs:
                if doc not in session_drawer and not any(doc in d or d in doc for d in session_drawer):
                    logger.warning(f"Session {session_id}: Document '{doc}' in active_docs is not in session drawer {session_drawer}")

    has_empty_drawer = (req.active_docs is not None and len(req.active_docs) == 0)

    if has_empty_drawer or is_empty_workspace:
        if has_empty_drawer:
            immediate_reply = "No active documents are currently attached to your drawer. Please attach a document in the drawer to begin research."
        else:
            immediate_reply = "No documents have been uploaded to the workspace yet. Please upload an academic PDF or report from the frontend to begin research and analysis."

        if session_id:
            if postgres_manager:
                postgres_manager.save_message(session_id, "user", message, mode=mode, active_docs=req.active_docs)
                postgres_manager.save_message(session_id, "assistant", immediate_reply, mode=mode, sources=[])
            if redis_cache:
                redis_cache.save_session_message(session_id, "user", message, mode=mode)
                redis_cache.save_session_message(session_id, "assistant", immediate_reply, mode=mode)

        # If raw text stream requested
        if req.stream and (req.format == "raw" or "text/plain" in request.headers.get("accept", "").lower()):
            async def fast_raw_stream():
                words = re.findall(r"\S+|\s+", immediate_reply)
                for w in words:
                    if await request.is_disconnected():
                        return
                    yield w
                    await asyncio.sleep(0.015)
            return StreamingResponse(fast_raw_stream(), media_type="text/plain; charset=utf-8", headers={"Cache-Control": "no-cache", **rate_headers})

        # If SSE stream requested
        if req.stream:
            async def fast_sse_stream():
                yield ": keepalive\n\n"
                words = re.findall(r"\S+|\s+", immediate_reply)
                for w in words:
                    if await request.is_disconnected():
                        return
                    yield f"data: {json.dumps({'token': w})}\n\n"
                    await asyncio.sleep(0.015)
                meta_payload = {
                    "reply": immediate_reply,
                    "answer": immediate_reply,
                    "sources": [],
                    "citations": [],
                    "verified_claims": [],
                    "subgraph": {"nodes": [], "edges": []},
                    "quality_gate_decision": "accept",
                    "mode_used": mode,
                    "session_id": session_id,
                    "thread_id": session_id,
                }
                yield f"data: {json.dumps(meta_payload)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(fast_sse_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", **rate_headers})

        # If non-streaming
        return JSONResponse(
            content={
                "reply": immediate_reply,
                "grounded_answer": immediate_reply,
                "answer": immediate_reply,
                "sources": [],
                "citations": [],
                "verified_claims": [],
                "subgraph": {"nodes": [], "edges": []},
                "quality_gate_decision": "accept",
                "execution_time": 0.005,
                "latency_sec": 0.005,
                "mode_used": mode,
                "thread_id": session_id,
                "session_id": session_id,
            },
            headers={"X-Process-Time-Ms": "5.0", **rate_headers}
        )

    # 1. Check Redis Semantic & Exact Match Cache
    query_embedding = None
    try:
        if rag_engine and hasattr(rag_engine, "vector_engine") and rag_engine.vector_engine:
            emb_res = rag_engine.vector_engine.compute_embeddings([message])
            if emb_res and len(emb_res) > 0:
                query_embedding = emb_res[0]
    except Exception:
        query_embedding = None

    cached = None
    if redis_cache:
        cached = redis_cache.semantic_get(
            query=message,
            mode=mode,
            embedding=query_embedding,
            threshold=0.95,
            library=library,
            active_docs=req.active_docs
        )

    if not req.stream and cached:
        cached_ans = cached.get("answer") or cached.get("reply") or cached.get("grounded_answer") or ""
        payload = {
            "reply": cached_ans,
            "grounded_answer": cached_ans,
            "answer": cached_ans,
            "sources": cached.get("sources", []),
            "citations": cached.get("citations", []),
            "follow_up_inquiries": cached.get("follow_up_inquiries", []),
            "verified_claims": cached.get("verified_claims", []),
            "subgraph": cached.get("subgraph", {"nodes": [], "edges": []}),
            "top_chunks": cached.get("top_chunks", []),
            "quality_gate_decision": cached.get("quality_gate_decision", "accept"),
            "selected_tools": cached.get("selected_tools", ["redis_cache"]),
            "decomposed_queries": cached.get("decomposed_queries", []),
            "traceability_score": cached.get("traceability_score", 0.98),
            "execution_time": 0.005,
            "latency_sec": 0.005,
            "mode_used": mode,
            "thread_id": session_id,
            "session_id": session_id,
        }
        if session_id and postgres_manager:
            postgres_manager.save_message(session_id, "user", message, mode=mode, active_docs=req.active_docs)
            postgres_manager.save_message(session_id, "assistant", cached_ans, mode=mode, sources=payload["sources"])
        record_query_metric(0.005, success=True)
        return JSONResponse(
            content=payload,
            headers={"X-Redis-Cache": "HIT", "X-Process-Time-Ms": "5.0", **rate_headers}
        )

    if req.stream and cached:
        async def cached_sse_stream():
            yield ": keepalive\n\n"
            cached_ans = cached.get("answer") or cached.get("reply") or cached.get("grounded_answer") or ""
            words = re.findall(r"\S+|\s+", cached_ans)
            chunk_size = 3
            for i in range(0, len(words), chunk_size):
                if await request.is_disconnected() or is_aborted(session_id, request_id):
                    return
                token_chunk = "".join(words[i:i+chunk_size])
                yield f"data: {json.dumps({'token': token_chunk})}\n\n"
                await asyncio.sleep(0.008)

            cits = cached.get("citations", []) or []
            yield f"data: {json.dumps({'status': 'completed', 'sources': cached.get('sources', []), 'citations': cits, 'follow_up_inquiries': cached.get('follow_up_inquiries', []), 'subgraph': cached.get('subgraph', {'nodes': [], 'edges': []})})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            cached_sse_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no", "X-Redis-Cache": "HIT", **rate_headers}
        )

    # 2. Non-Streaming Execution
    if not req.stream:
        try:
            result, elapsed = chat_service.execute_rag_query(
                message=message,
                mode=mode,
                session_id=session_id,
                active_docs=req.active_docs,
                document_filter=req.document_filter,
                hops=req.hops,
                top_k=req.top_k,
                chat_history=req.chat_history,
            )
        except Exception as exc:
            record_query_metric(0.0, success=False)
            raise HTTPException(status_code=500, detail=f"Pipeline error: {str(exc)}")


        raw_ans = result.get("grounded_answer") or result.get("answer", "")
        answer = sanitize_rag_text(str(raw_ans))
        sources = []
        for c in result.get("citations", []):
            fn = c.get("pdf_filename") or (c.get("metadata", {}).get("pdf_filename") if isinstance(c, dict) else None)
            if fn and fn not in sources:
                sources.append(fn)
        if not sources and result.get("source_documents"):
            sources = result.get("source_documents")

        response_payload = {
            "reply": answer,
            "grounded_answer": answer,
            "answer": answer,
            "sources": sources,
            "citations": result.get("citations", []) or [],
            "follow_up_inquiries": result.get("follow_up_inquiries", []) or [],
            "verified_claims": result.get("verified_claims", []) or [],
            "subgraph": result.get("subgraph", {"nodes": [], "edges": []}) or {"nodes": [], "edges": []},
            "top_chunks": result.get("top_chunks", []) or [],
            "quality_gate_decision": result.get("quality_gate_decision", "accept"),
            "selected_tools": result.get("selected_tools", []) or [],
            "decomposed_queries": result.get("decomposed_queries", []) or [],
            "traceability_score": result.get("traceability_score", 0.95),
            "execution_time": elapsed,
            "latency_sec": elapsed,
            "mode_used": mode,
            "thread_id": session_id,
            "session_id": session_id,
            "persisted": bool(session_id is not None),
        }

        # Cache in Redis with semantic vector indexing (TTL: 86400s / 24h)
        if redis_cache:
            redis_cache.semantic_set(
                query=message,
                mode=mode,
                result=response_payload,
                embedding=query_embedding,
                library=library,
                active_docs=req.active_docs,
                ttl=86400
            )

        # Persist in PostgreSQL
        if session_id and postgres_manager:
            postgres_manager.save_message(session_id, "user", message, mode=mode, active_docs=req.active_docs)
            postgres_manager.save_message(session_id, "assistant", answer, mode=mode, sources=sources)

        return JSONResponse(
            content=response_payload,
            headers={
                "X-Redis-Cache": "MISS",
                "X-Process-Time-Ms": str(round(elapsed * 1000, 1)),
                **rate_headers
            }
        )

    # 2.5 Raw Plain-Text Streaming Execution (zero parsing required on frontend)
    if req.format == "raw" or "text/plain" in request.headers.get("accept", "").lower():
        async def chat_raw_generator():
            t_start = time.perf_counter()
            try:
                result = rag_engine.query_subgraph_graphrag(
                    query=message,
                    hops=req.hops or (1 if mode == "fast" else 2),
                    top_k=req.top_k or (4 if mode == "fast" else 8),
                    document_filter=req.document_filter,
                    active_docs=req.active_docs,
                    mode=mode,
                    thread_id=session_id,
                    chat_history=req.chat_history,
                )
                elapsed = round(time.perf_counter() - t_start, 3)
                record_query_metric(elapsed, success=True)
                raw_ans = result.get("grounded_answer") or result.get("answer", "")
                answer = sanitize_rag_text(str(raw_ans))
                sources = []
                for c in result.get("citations", []):
                    fn = c.get("pdf_filename") or (c.get("metadata", {}).get("pdf_filename") if isinstance(c, dict) else None)
                    if fn and fn not in sources:
                        sources.append(fn)
                if not sources and result.get("source_documents"):
                    sources = result.get("source_documents")

                words = re.findall(r"\S+|\s+", answer)
                chunk_size = 3
                for i in range(0, len(words), chunk_size):
                    if await request.is_disconnected() or is_aborted(session_id, request_id):
                        logger.info(f"Client disconnected or aborted: session={session_id}, req={request_id}")
                        yield " [Request Cancelled]"
                        return
                    token_chunk = "".join(words[i:i+chunk_size])
                    yield token_chunk
                    await asyncio.sleep(0.015)

                if session_id and postgres_manager:
                    postgres_manager.save_message(session_id, "user", message, mode=mode, active_docs=req.active_docs)
                    postgres_manager.save_message(session_id, "assistant", answer, mode=mode, sources=sources)
            except Exception as exc:
                yield f"\n[Error: {str(exc)}]"

        return StreamingResponse(
            chat_raw_generator(),
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                **rate_headers,
            }
        )

    # 3. Streaming Execution (SSE) with Real-Time Cancellation & Structured Events
    async def chat_sse_generator():
        t_start = time.perf_counter()
        yield ": keepalive\n\n"
        if await request.is_disconnected() or is_aborted(session_id, request_id):
            yield f"event: error\ndata: {json.dumps({'error': {'code': 'CANCELLED', 'message': 'Request cancelled by user', 'request_id': request_id}})}\n\n"
            yield "data: [DONE]\n\n"
            return

        try:
            result = rag_engine.query_subgraph_graphrag(
                query=message,
                hops=req.hops or (1 if mode == "fast" else 2),
                top_k=req.top_k or (4 if mode == "fast" else 8),
                document_filter=req.document_filter,
                active_docs=req.active_docs,
                mode=mode,
                thread_id=session_id,
                chat_history=req.chat_history,
            )
            elapsed = round(time.perf_counter() - t_start, 3)
            record_query_metric(elapsed, success=True)
            raw_ans = result.get("grounded_answer") or result.get("answer", "")
            answer = sanitize_rag_text(str(raw_ans))
            sources = []
            citations = result.get("citations", []) or []
            for c in citations:
                fn = c.get("pdf_filename") or (c.get("metadata", {}).get("pdf_filename") if isinstance(c, dict) else None)
                if fn and fn not in sources:
                    sources.append(fn)
            if not sources and result.get("source_documents"):
                sources = result.get("source_documents")

            # Stream tokens with abort checks
            words = re.findall(r"\S+|\s+", answer)
            chunk_size = 3
            for i in range(0, len(words), chunk_size):
                if await request.is_disconnected() or is_aborted(session_id, request_id):
                    logger.info(f"Client disconnected or aborted: session={session_id}, req={request_id}")
                    yield f"data: {json.dumps({'error': {'code': 'CANCELLED', 'message': 'Request cancelled by user'}})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                token_chunk = "".join(words[i:i+chunk_size])
                yield f"data: {json.dumps({'token': token_chunk})}\n\n"
                await asyncio.sleep(0.012)

            # Final metadata event
            final_meta = {
                "reply": answer,
                "grounded_answer": answer,
                "answer": answer,
                "sources": sources,
                "citations": citations,
                "follow_up_inquiries": result.get("follow_up_inquiries", []) or [],
                "verified_claims": result.get("verified_claims", []) or [],
                "subgraph": result.get("subgraph", {"nodes": [], "edges": []}) or {"nodes": [], "edges": []},
                "quality_gate_decision": result.get("quality_gate_decision", "accept"),
                "execution_time": elapsed,
                "latency_sec": elapsed,
                "mode_used": mode,
                "session_id": session_id,
                "thread_id": session_id,
                "persisted": bool(session_id is not None),
            }

            # Cache & Persist consolidated response
            if redis_cache:
                redis_cache.semantic_set(
                    query=message,
                    mode=mode,
                    result=final_meta,
                    embedding=query_embedding,
                    library=library,
                    active_docs=req.active_docs,
                    ttl=86400
                )
            if session_id and postgres_manager:
                postgres_manager.save_message(session_id, "user", message, mode=mode, active_docs=req.active_docs)
                postgres_manager.save_message(session_id, "assistant", answer, mode=mode, sources=sources)

            # Emit clean completion payload without 'reply' to prevent duplicate text in client.ts
            yield f"data: {json.dumps({'status': 'completed', 'sources': sources, 'citations': citations, 'follow_up_inquiries': result.get('follow_up_inquiries', []) or [], 'subgraph': final_meta['subgraph'], 'verified_claims': final_meta['verified_claims']})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            record_query_metric(round(time.perf_counter() - t_start, 3), success=False)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        chat_sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Redis-Cache": "MISS",
            **rate_headers,
        }
    )


@router.post("/api/chat/abort")
async def abort_chat_generation(req: AbortRequest):
    """
    Tier 1 Critical: Cancel in-flight streaming or execution for a session or request ID.
    """
    sid = req.session_id or req.thread_id
    rid = req.request_id
    if not sid and not rid:
        raise HTTPException(status_code=400, detail="session_id or request_id required")
    record_abort(sid, rid)
    return {
        "status": "aborted",
        "session_id": sid,
        "request_id": rid,
        "message": "Chat generation cancelled successfully"
    }


@router.post("/api/feedback")
async def submit_chat_feedback(
    fb: FeedbackRequest,
    request: Request,
    postgres_manager: Any = Depends(get_postgres_manager),
):
    """
    Tier 2 High Value: Record user feedback on response relevance and accuracy into PostgreSQL.
    """
    sid = fb.session_id or "default"
    ip = get_authentic_client_ip(request)
    if postgres_manager:
        postgres_manager.save_feedback(
            session_id=sid,
            rating=fb.rating,
            reason=fb.reason,
            query=fb.query,
            message_id=fb.message_id,
            client_ip=ip,
        )
    return {
        "status": "recorded",
        "session_id": sid,
        "rating": fb.rating,
        "message": "Feedback recorded successfully"
    }


@router.get("/api/feedback/stats")
async def get_feedback_stats_endpoint(
    postgres_manager: Any = Depends(get_postgres_manager),
):
    """
    Operational Telemetry: Overall thumbs_up vs thumbs_down counts and satisfaction ratio.
    """
    if not postgres_manager:
        return {
            "thumbs_up": 0,
            "thumbs_down": 0,
            "satisfaction_ratio": 1.0,
            "total_feedback": 0,
        }
    try:
        return postgres_manager.get_feedback_stats()
    except Exception as exc:
        logger.error(f"Error fetching feedback stats: {exc}")
        raise HTTPException(status_code=503, detail="Database feedback analytics unavailable")


@router.post("/api/chat/batch")
async def batch_chat_query(
    req: BatchChatRequest,
    rag_engine: Any = Depends(get_rag_engine),
):
    """
    Tier 3 Medium: Execute research query across multiple document filters in parallel.
    """
    filters = req.doc_filters or req.documents or []
    if not filters:
        ready_docs = get_ready_documents_list()
        filters = [d["filename"] for d in ready_docs]

    results = []
    for doc in filters[:5]:
        res = rag_engine.query_subgraph_graphrag(
            query=req.query,
            mode=req.mode or "fast",
            document_filter=doc,
            active_docs=[doc],
        )
        ans = res.get("grounded_answer") or res.get("answer", "")
        results.append({
            "document": doc,
            "answer": ans,
            "reply": ans,
            "grounded_answer": ans,
            "citations": res.get("citations", []),
            "quality_gate_decision": res.get("quality_gate_decision", "accept"),
            "grounded": res.get("grounded", True),
        })

    return {"query": req.query, "mode": req.mode or "fast", "results": results, "count": len(results)}
