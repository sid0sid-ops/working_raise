"""
Search Router
Dense vector search across indexed document chunks.
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from src.api.context import get_ready_documents_list
from src.api.dependencies import get_rag_engine

logger = logging.getLogger("raise.router.search")
router = APIRouter(tags=["Search"])


@router.post("/api/search")
async def semantic_search(request: Request, rag_engine: Any = Depends(get_rag_engine)):
    """Perform dense vector search across indexed chunks."""
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        top_k = int(body.get("top_k", 5))
        if not query or not get_ready_documents_list():
            return {
                "results": [],
                "query": query,
                "total_matches": 0,
                "message": "Please upload an academic PDF to begin your research."
            }
        results = rag_engine.search_vectors(query=query, top_k=top_k)
        return {"results": results, "query": query, "total_matches": len(results)}
    except Exception as e:
        return {"results": [], "error": str(e)}
