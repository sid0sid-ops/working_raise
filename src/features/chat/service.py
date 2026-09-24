"""
Chat & Conversational Reasoning Service.
Encapsulates dual-tier conversational memory (Redis + PostgreSQL),
vLLM generation, token bucket rate limiting, Redis query caching,
cancellation checks, and Server-Sent Events (SSE) streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
import httpx
from fastapi import Request

from src.api.context import (
    _parse_drawer_active_docs,
    get_authentic_client_ip,
    get_ready_documents_list,
    is_aborted,
    is_conversational_or_memory_query,
    record_abort,
    record_query_metric,
)
from src.api.schemas import ChatMessageRequest

logger = logging.getLogger("raise.services.chat")


class ChatService:
    def __init__(
        self,
        rag_engine: Any = None,
        postgres_manager: Any = None,
        redis_cache: Any = None,
        session_memory_manager: Any = None,
    ):
        self.rag_engine = rag_engine
        self.postgres_manager = postgres_manager
        self.redis_cache = redis_cache
        self.session_memory_manager = session_memory_manager

    def check_rate_limit(self, request: Request, request_id: str) -> Tuple[bool, Dict[str, str]]:
        """Token Bucket rate limiting via Redis."""
        client_ip = get_authentic_client_ip(request)
        is_allowed = True
        remaining_tokens = 100
        if self.redis_cache:
            is_allowed, remaining_tokens = self.redis_cache.check_rate_limit(client_ip)
        headers = {
            "X-RateLimit-Remaining": str(remaining_tokens),
            "X-Request-ID": request_id,
        }
        return is_allowed, headers

    async def handle_conversational_turn(
        self,
        req: ChatMessageRequest,
        request: Request,
        message: str,
        session_id: str,
        mode: str,
    ) -> Dict[str, Any]:
        """Resolves conversational turn, persona variables, and historical turns."""
        t_start = time.perf_counter()

        # 1. User Persona & Entity Memory Extraction
        extracted_name = self.session_memory_manager.extract_and_set_user_persona(session_id, message) if self.session_memory_manager else None
        if extracted_name and self.redis_cache:
            self.redis_cache.set_session_memory(session_id, "user_name", extracted_name)

        existing_vars = self.redis_cache.get_session_memory(session_id) if self.redis_cache else {}
        known_name = existing_vars.get("user_name") or (self.session_memory_manager.get_user_persona(session_id).get("user_name") if self.session_memory_manager else None)

        # 2. Sliding Window Context Retrieval
        recent_turns = (self.redis_cache.get_session_messages(session_id, limit=10) if self.redis_cache else []) or []
        if not recent_turns and self.postgres_manager:
            recent_turns = self.postgres_manager.get_messages(session_id, limit=10)
            if self.redis_cache:
                for t in recent_turns:
                    self.redis_cache.save_session_message(
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
            f"{name_ctx}"
            "Respond helpfully, politely, and concisely to greetings, personal questions, or conversation. "
            "Never invent research facts, and acknowledge user identity gracefully."
        )

        vllm_messages = [{"role": "system", "content": system_prompt}]
        for turn in recent_turns[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                vllm_messages.append({"role": role, "content": content})
        vllm_messages.append({"role": "user", "content": message})

        model_name = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4")
        vllm_candidates = [
            os.getenv("VLLM_URL", "http://127.0.0.1:8002/v1"),
            "http://127.0.0.1:8002/v1",
            "http://localhost:8002/v1",
        ]

        def get_fallback_reply():
            if known_name:
                return f"Hello {known_name}! I am RAISE, your research intelligence assistant. How can I help you today?"
            return "Hello! I am RAISE, your research intelligence assistant. How can I help you today?"

        return {
            "vllm_candidates": vllm_candidates,
            "vllm_messages": vllm_messages,
            "model_name": model_name,
            "get_fallback_reply": get_fallback_reply,
            "t_start": t_start,
        }

    def save_chat_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        mode: str = "fast",
        active_docs: Optional[List[str]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Decoupled Dual-Write Persistence to PostgreSQL and Redis."""
        if not session_id:
            return
        if self.postgres_manager:
            self.postgres_manager.save_message(session_id, "user", user_message, mode=mode, active_docs=active_docs)
            self.postgres_manager.save_message(session_id, "assistant", assistant_reply, mode=mode, sources=sources or [])
        if self.redis_cache:
            self.redis_cache.save_session_message(session_id, "user", user_message, mode=mode)
            self.redis_cache.save_session_message(session_id, "assistant", assistant_reply, mode=mode)

    def execute_rag_query(
        self,
        message: str,
        mode: str,
        session_id: str,
        active_docs: Optional[List[str]] = None,
        document_filter: Optional[List[str]] = None,
        hops: Optional[int] = None,
        top_k: Optional[int] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Dict[str, Any], float]:
        """Executes RAG subgraph query and records telemetry metrics."""
        t_start = time.perf_counter()
        effective_hops = hops or (1 if mode == "fast" else 2)
        effective_top_k = top_k or (4 if mode == "fast" else 8)

        result = self.rag_engine.query_subgraph_graphrag(
            query=message,
            hops=effective_hops,
            top_k=effective_top_k,
            document_filter=document_filter,
            active_docs=active_docs,
            mode=mode,
            thread_id=session_id,
            chat_history=chat_history,
        )
        elapsed = round(time.perf_counter() - t_start, 3)
        record_query_metric(elapsed, success=True)
        return result, elapsed


