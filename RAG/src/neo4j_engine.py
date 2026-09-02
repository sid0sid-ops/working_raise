"""
RAISE Neo4j Database Engine
Direct integration with Neo4j Graph Database (Local Neo4j Desktop / Community / Neo4j AuraDB Cloud).
Handles graph sync, Cypher queries, and graph traversal.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import neo4j
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

try:
    from .config import settings
except Exception:
    settings = None


class Neo4jDatabase:
    """
    Manages connections and transactions with Neo4j Graph Database.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        if settings:
            self.uri = uri or settings.neo4j.uri
            self.user = user or settings.neo4j.user
            self.password = password or settings.neo4j.password
            self.database = database or settings.neo4j.database
        else:
            self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
            self.user = user or os.getenv("NEO4J_USER", "neo4j")
            self.password = password or os.getenv("NEO4J_PASSWORD", "password123")
            self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        self._driver = None

    def get_driver(self):
        if not HAS_NEO4J:
            return None
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    connection_timeout=3.0,
                )
            except Exception:
                self._driver = None
        return self._driver

    def check_connection(self) -> Dict[str, Any]:
        """
        Verify live connection to Neo4j database.
        """
        if not HAS_NEO4J:
            return {"connected": False, "error": "neo4j python package not installed"}
        try:
            driver = self.get_driver()
            if not driver:
                return {"connected": False, "error": "Could not initialize Neo4j driver"}
            with driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS ping")
                record = result.single()
                if record and record["ping"] == 1:
                    # Count total nodes for health check
                    count_res = session.run("MATCH (n) RETURN count(n) AS total_nodes")
                    count_rec = count_res.single()
                    total = count_rec["total_nodes"] if count_rec else 0
                    return {
                        "connected": True,
                        "uri": self.uri,
                        "user": self.user,
                        "database": self.database,
                        "total_nodes": total,
                    }
                return {"connected": False, "error": "Ping failed"}
        except Exception as e:
            return {
                "connected": False,
                "uri": self.uri,
                "error": str(e),
                "hint": "Ensure Neo4j is running locally (bolt://localhost:7687) or provide Neo4j AuraDB credentials.",
            }

    @property
    def connected(self) -> bool:
        """Convenient boolean check for live Neo4j database connectivity."""
        return bool(self.check_connection().get("connected", False))

    def run_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute arbitrary Cypher query and return list of records as dictionaries.
        """
        driver = self.get_driver()
        if not driver:
            return []
        parameters = parameters or {}
        records = []
        try:
            with driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                for record in result:
                    records.append(record.data())
        except Exception as e:
            records.append({"error": str(e)})
        return records

    def sync_graph_data(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest D3/NetworkX graph nodes and edges into Neo4j using idempotent Cypher MERGE statements.
        """
        conn = self.check_connection()
        if not conn.get("connected"):
            return {
                "synced": False,
                "reason": "Neo4j server not reachable",
                "detail": conn.get("error"),
                "cypher_available": True,
            }

        driver = self.get_driver()
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        synced_nodes = 0
        synced_edges = 0

        try:
            with driver.session(database=self.database) as session:
                # 1. Create Nodes
                for n in nodes:
                    node_id = str(n.get("id"))
                    raw_type = str(n.get("type", "Entity"))
                    node_type = re.sub(r'[^a-zA-Z0-9_]', '_', raw_type) or "Entity"
                    label = str(n.get("label", node_id))
                    page = int(n.get("page", 1))
                    doc_id = str(n.get("document_id") or n.get("properties", {}).get("document_id") or "global_doc")

                    cypher = f"""
                    MERGE (n:{node_type} {{id: $id}})
                    ON CREATE SET n.label = $label, n.page = $page, n.document_id = $doc_id, n.created_at = timestamp()
                    ON MATCH SET n.label = $label, n.page = $page, n.document_id = $doc_id, n.updated_at = timestamp()
                    """
                    session.run(cypher, id=node_id, label=label, page=page, doc_id=doc_id)
                    synced_nodes += 1

                # 2. Create Directed Edges
                for e in edges:
                    src_id = str(e.get("source"))
                    tgt_id = str(e.get("target"))
                    raw_rel = str(e.get("relation") or e.get("type") or "RELATED_TO")
                    relation = re.sub(r'[^a-zA-Z0-9_]', '_', raw_rel.upper()) or "RELATED_TO"

                    cypher = f"""
                    MATCH (a {{id: $src_id}})
                    MATCH (b {{id: $tgt_id}})
                    MERGE (a)-[r:{relation}]->(b)
                    """
                    session.run(cypher, src_id=src_id, tgt_id=tgt_id)
                    synced_edges += 1

            return {
                "synced": True,
                "nodes_written": synced_nodes,
                "edges_written": synced_edges,
                "uri": self.uri,
            }
        except Exception as e:
            return {"synced": False, "error": str(e)}

    def extract_document_subgraph(self, doc_id: str, max_nodes: int = 50) -> Dict[str, Any]:
        """Query subgraphs scoped strictly to a specific document_id."""
        query = """
        MATCH (n {document_id: $doc_id})-[r]-(m {document_id: $doc_id})
        RETURN n, r, m LIMIT $limit
        """
        records = self.run_cypher(query, {"doc_id": doc_id, "limit": max_nodes})
        return {"records": records, "document_id": doc_id}

    def query_multihop_subgraph(
        self,
        seed_ids: List[str],
        keywords: Optional[List[str]] = None,
        hops: int = 2,
        doc_id: Optional[str] = None,
        limit: int = 40,
    ) -> Dict[str, Any]:
        """
        Industry-standard multi-hop Cypher traversal in Neo4j:
        1. Identifies seed nodes by ID or entity keyword matching.
        2. Expands 1-to-N hops along directed relationships.
        3. Returns structured nodes and edges for subgraph context and visual rendering.
        """
        if not self.check_connection().get("connected"):
            return {"nodes": [], "edges": []}

        clean_kws = [k.lower() for k in (keywords or []) if len(k) >= 3][:5]
        
        cypher = """
        MATCH (seed)
        WHERE (seed.id IN $seed_ids)
           OR (size($clean_kws) > 0 AND any(k IN $clean_kws WHERE toLower(coalesce(seed.label, seed.name, seed.id, '')) CONTAINS k))
           OR (size($clean_kws) > 0 AND any(lbl IN labels(seed) WHERE any(k IN $clean_kws WHERE toLower(lbl) CONTAINS k)))
        WITH seed LIMIT 10
        MATCH path = (seed)-[r*1..2]-(m)
        WHERE $doc_id IS NULL OR (seed.document_id = $doc_id AND m.document_id = $doc_id)
        UNWIND nodes(path) AS n
        UNWIND relationships(path) AS rel
        WITH DISTINCT n, rel
        RETURN 
            coalesce(n.id, elementId(n)) AS id,
            labels(n)[0] AS type,
            coalesce(n.label, n.name, n.id) AS label,
            coalesce(n.page, 1) AS page,
            coalesce(n.document_id, 'global') AS document_id,
            coalesce(startNode(rel).id, elementId(startNode(rel))) AS source,
            coalesce(endNode(rel).id, elementId(endNode(rel))) AS target,
            type(rel) AS relation
        LIMIT $limit
        """

        try:
            records = self.run_cypher(
                cypher,
                {
                    "seed_ids": seed_ids,
                    "clean_kws": clean_kws,
                    "doc_id": doc_id,
                    "limit": limit
                }
            )

            nodes_dict = {}
            edges_list = []
            seen_edges = set()

            for rec in records:
                nid = str(rec.get("id"))
                if nid and nid not in nodes_dict:
                    nodes_dict[nid] = {
                        "id": nid,
                        "label": str(rec.get("label", nid)),
                        "type": str(rec.get("type", "Entity")),
                        "page": int(rec.get("page", 1)),
                        "document_id": str(rec.get("document_id", "")),
                    }
                
                src = str(rec.get("source"))
                tgt = str(rec.get("target"))
                rel_type = str(rec.get("relation", "RELATED_TO"))
                edge_key = (src, tgt, rel_type)
                if src and tgt and edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges_list.append({
                        "source": src,
                        "target": tgt,
                        "type": rel_type,
                    })

            return {
                "nodes": list(nodes_dict.values()),
                "edges": edges_list,
                "engine": "Neo4j Cypher Live",
            }
        except Exception as e:
            return {"nodes": [], "edges": [], "error": str(e)}

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
