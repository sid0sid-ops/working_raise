"""
Graph Router
Endpoints for Neo4j Property Graph and NetworkX knowledge graph operations:
canvas visualization, subgraph neighborhood extraction, entity search, Cypher download, and synchronization.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import FileResponse, JSONResponse

from src.api.context import get_ready_documents_list
from src.api.dependencies import get_rag_engine

logger = logging.getLogger("raise.router.graph")
router = APIRouter(tags=["Knowledge Graph & Neo4j"])

BASE_DIR = Path(__file__).resolve().parent.parent


@router.get("/api/graph")
async def get_graph_data(rag_engine: Any = Depends(get_rag_engine)):
    """Retrieve full node-link knowledge graph for canvas rendering."""
    if not get_ready_documents_list():
        return {
            "nodes": [],
            "edges": [],
            "total_nodes": 0,
            "total_edges": 0,
            "message": "No knowledge graph yet. Upload an academic PDF to build the graph."
        }
    return rag_engine.get_graph_data()


@router.get("/api/subgraph/{node_id}")
async def get_node_subgraph(node_id: str, hops: int = 2, rag_engine: Any = Depends(get_rag_engine)):
    """Get multi-hop neighborhood subgraph for specific node."""
    return rag_engine.graph_engine.extract_subgraph([node_id], hops=hops)


@router.get("/api/graph/search")
async def search_graph_entities(
    q: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    limit: int = 25,
    rag_engine: Any = Depends(get_rag_engine),
):
    """
    Tier 2 High Value: Entity search across Neo4j Property Graph and local GraphRAG engine.
    Supports both ?q= and ?query= parameters from various frontend components.
    """
    target_q = (q or query or "").strip()
    if not target_q:
        return {"query": "", "nodes": [], "count": 0}

    matched_nodes = []
    seen = set()

    # 1. Neo4j Cypher search
    if rag_engine and rag_engine.neo4j_db and rag_engine.neo4j_db.connected:
        try:
            cypher = """
            MATCH (n)
            WHERE toLower(n.name) CONTAINS toLower($q) OR toLower(n.label) CONTAINS toLower($q)
            RETURN n.id AS id, n.name AS name, n.label AS label, labels(n)[0] AS type, n.page AS page, n.document_id AS document_id
            LIMIT $limit
            """
            rows = rag_engine.neo4j_db.run_cypher(cypher, {"q": target_q, "limit": limit})
            for r in rows:
                nid = str(r.get("id"))
                if nid not in seen:
                    seen.add(nid)
                    matched_nodes.append({
                        "id": nid,
                        "name": r.get("name") or nid,
                        "label": r.get("label") or r.get("name") or nid,
                        "type": r.get("type", "Entity"),
                        "page": r.get("page", 1),
                        "document_id": r.get("document_id", ""),
                    })
        except Exception:
            pass

    # 2. NetworkX fallback
    if len(matched_nodes) < limit and rag_engine and hasattr(rag_engine, "graph_engine"):
        g = rag_engine.graph_engine.graph
        for nid, data in g.nodes(data=True):
            if str(nid) in seen:
                continue
            name = str(data.get("name") or data.get("label") or nid)
            if target_q.lower() in name.lower():
                seen.add(str(nid))
                matched_nodes.append({
                    "id": str(nid),
                    "name": name,
                    "label": str(data.get("label", name)),
                    "type": str(data.get("type", "Entity")),
                    "color": data.get("color", "#64748b"),
                    "page": data.get("page", 1),
                })
            if len(matched_nodes) >= limit:
                break

    return {"query": target_q, "nodes": matched_nodes, "count": len(matched_nodes)}


@router.get("/api/cypher")
async def get_cypher_script(rag_engine: Any = Depends(get_rag_engine)):
    """Download Neo4j Cypher ingestion script."""
    cypher_text = rag_engine.get_cypher_script()
    cypher_file = BASE_DIR / "data" / "processed" / "neo4j" / "academic_graph.cypher"
    cypher_file.parent.mkdir(parents=True, exist_ok=True)
    cypher_file.write_text(cypher_text, encoding="utf-8")
    return FileResponse(str(cypher_file), filename="academic_graph.cypher", media_type="text/plain")


@router.get("/api/neo4j/status")
async def neo4j_status(rag_engine: Any = Depends(get_rag_engine)):
    """Check live connection to Neo4j database."""
    return rag_engine.check_neo4j()


@router.post("/api/neo4j/sync")
async def neo4j_sync(rag_engine: Any = Depends(get_rag_engine)):
    """Sync all knowledge graph triples into Neo4j."""
    return rag_engine.sync_to_neo4j()


@router.post("/api/neo4j/query")
async def neo4j_run_query(request: Request, rag_engine: Any = Depends(get_rag_engine)):
    """Execute raw Cypher query against live Neo4j."""
    try:
        body = await request.json()
        cypher_query = body.get("query", "").strip()
        if not cypher_query:
            return {"records": [], "error": "Query cannot be empty"}
        records = rag_engine.execute_cypher(cypher_query)
        return {"records": records, "query": cypher_query}
    except Exception as e:
        return {"records": [], "error": str(e)}
