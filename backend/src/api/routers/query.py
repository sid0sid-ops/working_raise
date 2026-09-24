"""
Query & GraphRAG Router
Endpoints for headless network query execution, Server-Sent Events (SSE) streaming,
LangGraph multi-engine subgraph reasoning, and dynamic research suggestions.
Thinned controller delegating business logic to QueryService.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.dependencies import get_query_service
from src.api.schemas import QueryRequest
from src.features.query.service import QueryService

logger = logging.getLogger("raise.router.query")
router = APIRouter(tags=["Query & GraphRAG"])


@router.post("/api/query", response_class=JSONResponse)
async def query_pipeline(
    request_data: QueryRequest,
    query_service: QueryService = Depends(get_query_service),
):
    """
    Primary Headless Network Query Endpoint for remote Mac frontend.
    Executes complete pipeline:
      Intent Router -> Coref Resolver -> Decomposer -> Multi-Query Vector & Graph Retrieval -> Reranking -> Synthesis -> Quality Gate.
    """
    query = request_data.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if len(query) > 2500:
        raise HTTPException(status_code=400, detail="Query exceeds maximum length of 2500 characters")

    thread_id = request_data.thread_id or request_data.session_id or "default"
    result = query_service.execute_query(
        query=query,
        thread_id=thread_id,
        active_docs=request_data.active_docs,
        hops=request_data.hops or 2,
        top_k=request_data.top_k or 4,
        document_filter=request_data.document_filter,
        chat_history=request_data.chat_history,
    )
    return JSONResponse(content=result)


@router.post("/api/query/stream")
async def query_pipeline_stream(
    request_data: QueryRequest,
    query_service: QueryService = Depends(get_query_service),
):
    """
    Server-Sent Events (SSE) Streaming Query Endpoint.
    Emits stage transitions (event: stage), tokens (event: token), and final verification payload (event: final).
    """
    query = request_data.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    thread_id = request_data.thread_id or request_data.session_id or "default"
    return StreamingResponse(
        query_service.stream_query_events(
            query=query,
            thread_id=thread_id,
            active_docs=request_data.active_docs,
            hops=request_data.hops or 2,
            top_k=request_data.top_k or 4,
            document_filter=request_data.document_filter,
            chat_history=request_data.chat_history,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/graphrag/subgraph-query")
async def graphrag_subgraph_query(
    request: Request,
    query_service: QueryService = Depends(get_query_service),
):
    """
    Execute LangGraph StateGraph Workflow:
      1. intent_analyzer node
      2. vector_retriever node (ChromaDB)
      3. graph_traverser node (Neo4j / NetworkX)
      4. synthesizer_verifier node (ClaimVerifier)
      5. corrective_expander conditional loop
    """
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        session_id = body.get("session_id")
        hops = int(body.get("hops", 2))
        top_k = int(body.get("top_k", 4))
        doc_filter = body.get("document_filter")

        if not query:
            return {"error": "Query cannot be empty"}
        if len(query) > 2500:
            return {"error": "Query exceeds maximum allowed length of 2500 characters"}

        return query_service.execute_subgraph_workflow(
            query=query,
            session_id=session_id,
            hops=hops,
            top_k=top_k,
            doc_filter=doc_filter,
        )
    except Exception as e:
        logger.error(f"[ERROR] LangGraph query execution failed: {e}")
        return {"error": str(e)}


@router.get("/api/suggestions")
@router.post("/api/suggestions")
async def get_query_suggestions(
    request: Request,
    limit: int = 5,
    active_docs: Optional[Union[str, List[str]]] = None,
    drawer: Optional[Union[str, List[str]]] = None,
    session_id: Optional[str] = None,
    query_service: QueryService = Depends(get_query_service),
):
    """
    Return dynamic, complex graph-grounded research questions based on documents present in the active drawer.
    Supports:
      1. Repeated query params: ?active_docs=doc1.pdf&active_docs=doc2.pdf
      2. Comma-separated query strings: ?active_docs=doc1.pdf,doc2.pdf
      3. URL-encoded spaces and special characters unquoted via urllib.parse.unquote_plus
      4. POST JSON payloads: {"active_docs": ["doc1.pdf", "doc2.pdf"]} or {"active_docs": "doc1.pdf,doc2.pdf"}
    Rule 1 (Drawer Isolation): Even if documents exist in the library, if 0 documents are in the drawer, returns [].
    Rule 2 (Complex Grounded Questions): Formulates deep multi-hop and relational synthesis questions whose exact
            underlying relationships and factual evidence are verified in our knowledge graph.
    """
    raw_candidates: List[str] = []
    has_explicit_drawer_param = False

    # 1. Gather all candidates from query params
    for param_name in ("active_docs", "drawer", "selected_docs"):
        if param_name in request.query_params:
            has_explicit_drawer_param = True
            raw_candidates.extend(request.query_params.getlist(param_name))

    # 2. Check JSON payload for POST
    if request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                limit = int(body.get("limit", limit))
                for key in ("active_docs", "drawer", "selected_docs"):
                    if key in body:
                        has_explicit_drawer_param = True
                        val = body[key]
                        if isinstance(val, (list, tuple, set)):
                            raw_candidates.extend([str(v) for v in val if v is not None])
                        elif val is not None:
                            raw_candidates.append(str(val))
        except Exception:
            pass

    # 3. Fallback to injected FastAPI params if query_params didn't catch it
    if not raw_candidates:
        if active_docs is not None:
            has_explicit_drawer_param = True
            raw_candidates.extend(active_docs if isinstance(active_docs, list) else [str(active_docs)])
        elif drawer is not None:
            has_explicit_drawer_param = True
            raw_candidates.extend(drawer if isinstance(drawer, list) else [str(drawer)])

    return query_service.get_dynamic_suggestions(
        raw_candidates=raw_candidates,
        has_explicit_drawer_param=has_explicit_drawer_param,
        limit=limit,
    )

