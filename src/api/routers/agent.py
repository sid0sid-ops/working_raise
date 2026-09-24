"""
Agent Router
Autonomous agentic multi-tool reasoning with session memory.
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Request, Depends

from src.api.context import get_ready_documents_list
from src.api.dependencies import get_rag_engine, get_session_memory

logger = logging.getLogger("raise.router.agent")
router = APIRouter(tags=["Agentic Reasoning"])


@router.post("/api/agent/query")
async def agent_query(
    request: Request,
    rag_engine: Any = Depends(get_rag_engine),
    session_memory_manager: Any = Depends(get_session_memory),
):
    """Execute autonomous agentic multi-tool reasoning with session memory."""
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        session_id = body.get("session_id")
        if not query:
            return {"error": "Query cannot be empty"}
        if len(query) > 2500:
            return {"error": "Query exceeds maximum allowed length of 2500 characters"}

        resolved_query = query
        resolved_entity = None
        if session_id and session_memory_manager:
            resolved_query, resolved_entity = session_memory_manager.resolve_coreference(query, session_id)

        ready_docs = get_ready_documents_list()
        if not ready_docs:
            resp = {
                "response": "Please upload an academic PDF to begin your research.",
                "tool_calls": [],
                "citations": []
            }
            if session_id:
                resp["session_id"] = session_id
                resp["resolved_query"] = resolved_query
            return resp

        active_filenames = [d["filename"] for d in ready_docs if "filename" in d]
        agent_result = rag_engine.ask_agent(resolved_query, active_docs=active_filenames)
        if session_id and session_memory_manager:
            session_memory_manager.record_turn(
                thread_id=session_id,
                user_query=query,
                resolved_query=resolved_query,
                active_entities=[resolved_entity] if resolved_entity else [],
                citations=agent_result.get("citations", []),
                assistant_answer=agent_result.get("response", ""),
            )
            agent_result["session_id"] = session_id
            agent_result["resolved_query"] = resolved_query
        return agent_result
    except Exception as e:
        return {"error": str(e)}
