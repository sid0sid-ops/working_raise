"""
RAISE Advanced GraphRAG Engine
Extracts Organizations, Leaders, Patents, Initiatives, Funding, Programs, Departments, and Regulations.
Builds typed multi-hop property graphs with Cypher generation for Neo4j.
Supports Multi-Hop Subgraph Traversal and Graph-Context Assembly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

try:
    import neo4j
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False


class GraphRAGEngine:
    """
    State-of-the-Art Property Graph & Entity Extraction Engine.
    Converts semantic document sections into structured knowledge graphs.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.doc_id = "default"
        self.node_provenance: Dict[str, Dict[str, Any]] = {}

    def build_from_academic_triples(
        self,
        triples_data: List[Dict[str, Any]],
        doc_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Populate NetworkX graph from extracted academic entity and relation triples.
        """
        for item in triples_data:
            for ent in item.get("entities", []):
                nid = ent["entity_id"]
                label = ent.get("name", nid)
                ntype = ent.get("label", "Entity")
                props = ent.get("properties", {})
                prov = ent.get("provenance", {})
                
                # Color mapping by entity type
                color_map = {
                    "University": "#2563eb",
                    "Department": "#0284c7",
                    "Centre": "#0d9488",
                    "Program": "#7c3aed",
                    "Subject": "#9333ea",
                    "Practical_Lab": "#c026d3",
                    "AcademicRegulation": "#ea580c",
                    "EligibilityRequirement": "#d97706",
                    "Faculty_Person": "#16a34a",
                    "AdministrativeRole": "#059669",
                    "ResearchProject": "#4f46e5",
                    "Publication_Patent": "#e11d48",
                    "MetricFact": "#ca8a04",
                }
                
                self.graph.add_node(
                    nid,
                    id=nid,
                    label=label,
                    type=ntype,
                    properties=props,
                    provenance=prov,
                    color=color_map.get(ntype, "#64748b"),
                    size=24 if ntype in ["University", "Department", "Centre"] else 16,
                    page=prov.get("page_number", 1),
                )
                self.node_provenance[nid] = prov

            for rel in item.get("relations", []):
                src = rel["source_id"]
                tgt = rel["target_id"]
                rtype = rel.get("relation_type", "RELATED_TO")
                props = rel.get("properties", {})
                prov = rel.get("provenance", {})

                if self.graph.has_node(src) and self.graph.has_node(tgt):
                    self.graph.add_edge(
                        src,
                        tgt,
                        relation=rtype,
                        type=rtype,
                        properties=props,
                        provenance=prov,
                    )

        return self.get_graph_data()

    def build_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        taxonomy_report: Optional[Dict[str, Any]] = None,
        doc_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Perform deep multi-entity extraction and construct directed relationship graph.
        """
        self.doc_id = doc_id

        # 1. Root Document Node
        self.graph.add_node(
            doc_id,
            type="Document",
            label=f"Document: {doc_id}",
            color="#2563eb",
            size=28,
            page=1,
        )

        known_orgs: Dict[str, str] = {}
        known_persons: Dict[str, str] = {}
        known_patents: Dict[str, str] = {}
        known_inits: Dict[str, str] = {}
        known_grants: Dict[str, str] = {}

        for idx, chunk in enumerate(chunks):
            cid = str(chunk.get("chunk_id") or f"{doc_id}_chunk_{idx}")
            heading = str(chunk.get("heading") or f"Section {idx+1}")
            page = int(chunk.get("source_pages", [1])[0] if chunk.get("source_pages") else 1)
            task = str(chunk.get("recommended_task") or "general")
            text = str(chunk.get("plain_text") or "")
            if not text.strip():
                continue

            # Add Section Node
            self.graph.add_node(
                cid,
                type="Section",
                label=heading[:38] + ("..." if len(heading) > 38 else ""),
                heading=heading,
                page=page,
                task=task,
                color="#0ea5e9",
                size=18,
            )
            self.graph.add_edge(doc_id, cid, relation="CONTAINS_SECTION")

            # Entity Extraction (dynamic institutional discovery + standard national bodies)
            current_section_orgs = []
            standard_orgs = [
                "BRIC", "CDFD", "NIPGR", "DBT", "AstraBio Innovations Council", "Indian Institute of Technology Madras",
                "IIT Madras Research Park", "Panjab University", "Delhi University", "JNU", "CSIR", "ICMR", "DST", "AIIMS"
            ]
            discovered_orgs = set(standard_orgs)
            found_insts = re.findall(r"\b([A-Z][A-Za-z\s&]{3,40}(?:Institute|Council|University|Foundation|Centre|Center|Laboratory|Board))\b", text)
            for inst in found_insts:
                clean_inst = inst.strip()
                if 4 < len(clean_inst) < 45 and not clean_inst.startswith("The "):
                    discovered_orgs.add(clean_inst)

            for org_name in discovered_orgs:
                if org_name.lower() in text.lower():
                    org_id = f"org_{slugify(org_name)}"
                    if org_id not in known_orgs:
                        known_orgs[org_id] = org_name
                        self.graph.add_node(
                            org_id,
                            type="Organization",
                            label=org_name,
                            color="#10b981",
                            size=24,
                            page=page,
                        )
                    self.graph.add_edge(cid, org_id, relation="MENTIONS_ORGANIZATION")
                    current_section_orgs.append(org_id)

            # Leaders/Persons
            person_matches = re.finditer(r"(?:Dr\.|Prof\.|Mr\.|Ms\.|Director|Dean)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", text)
            for pm in person_matches:
                p_name = pm.group(0).strip()
                p_id = f"person_{slugify(p_name)}"
                if p_id not in known_persons:
                    known_persons[p_id] = p_name
                    self.graph.add_node(
                        p_id,
                        type="Person",
                        label=p_name,
                        color="#f59e0b",
                        size=18,
                        page=page,
                    )
                self.graph.add_edge(cid, p_id, relation="MENTIONS_LEADERSHIP")
                for o_id in current_section_orgs:
                    self.graph.add_edge(p_id, o_id, relation="LEADS_OR_GOVERNS")

            # Funding Grants
            grant_matches = re.finditer(r"(?:₹|Rs\.?|INR|\$)\s*([0-9]+(?:\.[0-9]+)?\s*(?:Crore|Crores|Lakh|Lakhs|Million|Billion))", text, re.IGNORECASE)
            for gm in grant_matches:
                g_val = gm.group(0).strip()
                g_id = f"grant_{slugify(g_val)}"
                if g_id not in known_grants:
                    known_grants[g_id] = g_val
                    self.graph.add_node(
                        g_id,
                        type="FundingAllocation",
                        label=f"Metric: {g_val}",
                        color="#ca8a04",
                        size=18,
                        page=page,
                    )
                self.graph.add_edge(cid, g_id, relation="REPORTS_FINANCIALS")

        return self.get_graph_data()

    def extract_subgraph(
        self,
        seed_node_ids: List[str],
        hops: int = 2,
        max_nodes: int = 40,
    ) -> Dict[str, Any]:
        """
        Traverse neighbourhood of seed nodes up to 'hops' relationship steps.
        Returns sub-graph and structured text summary.
        """
        subgraph_nodes: Set[str] = set()
        
        # Collect valid seed nodes
        valid_seeds = [nid for nid in seed_node_ids if self.graph.has_node(nid)]
        
        if not valid_seeds:
            # Fallback to top degree nodes if seeds not found
            valid_seeds = sorted(self.graph.nodes(), key=lambda n: self.graph.degree(n), reverse=True)[:5]

        # Multi-Hop Neighborhood Expansion (BFS)
        frontier = set(valid_seeds)
        subgraph_nodes.update(frontier)

        for _ in range(hops):
            next_frontier = set()
            for current_node in frontier:
                # Successors (outgoing)
                for succ in self.graph.successors(current_node):
                    if succ not in subgraph_nodes:
                        next_frontier.add(succ)
                # Predecessors (incoming)
                for pred in self.graph.predecessors(current_node):
                    if pred not in subgraph_nodes:
                        next_frontier.add(pred)
            subgraph_nodes.update(next_frontier)
            frontier = next_frontier
            if len(subgraph_nodes) >= max_nodes:
                break

        # Extract induced subgraph
        sub_g = self.graph.subgraph(list(subgraph_nodes)[:max_nodes])

        nodes = []
        for n, d in sub_g.nodes(data=True):
            nodes.append({
                "id": n,
                "label": d.get("label", n),
                "type": d.get("type", "Node"),
                "color": d.get("color", "#64748b"),
                "size": d.get("size", 16),
                "page": d.get("page", 1),
                "properties": d.get("properties", {}),
                "provenance": d.get("provenance", {}),
            })

        edges = []
        structured_triples = []
        for u, v, d in sub_g.edges(data=True):
            rel = d.get("relation") or d.get("type") or "RELATED_TO"
            edges.append({
                "source": u,
                "target": v,
                "relation": rel,
            })
            u_lbl = sub_g.nodes[u].get("label", u)
            v_lbl = sub_g.nodes[v].get("label", v)
            structured_triples.append(f"({u_lbl}) -[:{rel}]-> ({v_lbl})")

        # Assemble structured context text
        assembled_context_lines = [
            "### Knowledge Graph Subgraph Context",
            f"**Total Traversed Nodes**: {len(nodes)} | **Directed Relations**: {len(edges)}",
            "",
            "**Key Graph Entities & Facts**:",
        ]
        for n in nodes[:15]:
            n_type = n["type"]
            n_lbl = n["label"]
            prov = n.get("provenance", {})
            doc = prov.get("pdf_filename", "Report")
            pg = prov.get("page_number", n.get("page", 1))
            assembled_context_lines.append(f"- **{n_lbl}** ({n_type}) — [Doc: {doc}, Page {pg}]")

        assembled_context_lines.append("\n**Directed Entity Relationships**:")
        for trip in structured_triples[:20]:
            assembled_context_lines.append(f"- {trip}")

        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
            "structured_triples": structured_triples,
            "assembled_text_context": "\n".join(assembled_context_lines),
        }

    def get_graph_data(self) -> Dict[str, Any]:
        """
        Export complete graph in D3.js force-directed graph node-link format.
        """
        nodes = []
        for n, d in self.graph.nodes(data=True):
            nodes.append({
                "id": n,
                "label": d.get("label", n),
                "type": d.get("type", "Node"),
                "color": d.get("color", "#64748b"),
                "size": d.get("size", 14),
                "page": d.get("page", 1),
                "properties": d.get("properties", {}),
                "provenance": d.get("provenance", {}),
            })

        edges = []
        for u, v, d in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "relation": d.get("relation") or d.get("type") or "RELATED_TO",
            })

        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def detect_communities(self, algorithm: str = "louvain") -> List[Dict[str, Any]]:
        """
        Dual-Tier Analytical Processing: Offload community detection from Neo4j to NetworkX.
        Supports Louvain modularity optimization and greedy modularity communities.
        """
        if self.graph.number_of_nodes() == 0:
            return []

        # Convert to undirected graph for community detection
        undirected_g = self.graph.to_undirected()

        communities_list = []
        try:
            if algorithm == "louvain" and hasattr(nx.community, "louvain_communities"):
                raw_communities = nx.community.louvain_communities(undirected_g, seed=42)
            else:
                raw_communities = list(nx.community.greedy_modularity_communities(undirected_g))
        except Exception:
            # Fallback to connected components
            raw_communities = list(nx.connected_components(undirected_g))

        # Compute PageRank scores for hub ranking
        try:
            pagerank_scores = nx.pagerank(self.graph, max_iter=100, alpha=0.85)
        except Exception:
            pagerank_scores = {n: float(self.graph.degree(n)) for n in self.graph.nodes()}

        for cid, comm in enumerate(raw_communities):
            members = list(comm)
            # Sort members by centrality / PageRank
            sorted_members = sorted(members, key=lambda n: pagerank_scores.get(n, 0.0), reverse=True)
            
            member_details = []
            entity_types = {}
            for m in sorted_members:
                node_data = self.graph.nodes[m]
                ntype = node_data.get("type", "Entity")
                entity_types[ntype] = entity_types.get(ntype, 0) + 1
                member_details.append({
                    "id": m,
                    "label": node_data.get("label", m),
                    "type": ntype,
                    "pagerank": round(float(pagerank_scores.get(m, 0.0)), 4),
                    "page": node_data.get("page", 1),
                })

            top_hubs = [m["label"] for m in member_details[:3]]
            primary_domain = max(entity_types.items(), key=lambda x: x[1])[0] if entity_types else "General"

            communities_list.append({
                "community_id": cid + 1,
                "size": len(members),
                "primary_domain": primary_domain,
                "top_hubs": top_hubs,
                "members": member_details,
            })

        return communities_list

    def compute_centrality_metrics(self, exclude_super_hubs: bool = True) -> Dict[str, Dict[str, float]]:
        """
        Compute node centrality metrics (PageRank, Degree, Betweenness) via NetworkX.
        When exclude_super_hubs=True, prunes high-degree institutional super-hubs (e.g. IIT Madras, IITMIC)
        to prevent them from starving peripheral leaf entities (e.g., individual deep-tech startups, patents).
        """
        if self.graph.number_of_nodes() == 0:
            return {}

        calc_graph = self.graph
        if exclude_super_hubs and self.graph.number_of_nodes() > 5:
            # Copy graph and remove top 10% highest-degree nodes or nodes tagged as generic institutions
            calc_graph = self.graph.copy()
            degree_dict = dict(calc_graph.degree())
            sorted_degrees = sorted(degree_dict.values(), reverse=True)
            high_degree_threshold = sorted_degrees[max(0, len(sorted_degrees) // 10)] if sorted_degrees else 20
            
            hubs_to_prune = [
                n for n, d in degree_dict.items()
                if (d >= high_degree_threshold and d >= 5) or
                calc_graph.nodes[n].get("type") in ["Institution", "University", "EcosystemEnabler", "Incubator"]
            ]
            # Ensure we don't prune everything
            if len(hubs_to_prune) < calc_graph.number_of_nodes():
                calc_graph.remove_nodes_from(hubs_to_prune)

        try:
            pr = nx.pagerank(calc_graph, max_iter=100, alpha=0.85)
        except Exception:
            pr = {}

        try:
            deg = nx.degree_centrality(calc_graph)
        except Exception:
            deg = {}

        try:
            bet = nx.betweenness_centrality(calc_graph, k=min(50, len(calc_graph)))
        except Exception:
            bet = {}

        metrics = {}
        for n in self.graph.nodes():
            metrics[n] = {
                "pagerank": round(float(pr.get(n, 0.0)), 4),
                "degree_centrality": round(float(deg.get(n, 0.0)), 4),
                "betweenness_centrality": round(float(bet.get(n, 0.0)), 4),
            }
        return metrics

    def generate_hierarchical_summaries(self, max_communities: int = 5) -> List[Dict[str, Any]]:
        """
        Hierarchical Community Summarization for global GraphRAG queries.
        """
        communities = self.detect_communities()
        summaries = []

        for comm in communities[:max_communities]:
            cid = comm["community_id"]
            hubs = ", ".join(comm["top_hubs"])
            domain = comm["primary_domain"]
            size = comm["size"]
            
            summary_text = (
                f"Community #{cid} ({domain} Cluster, {size} entities): "
                f"Anchored around key hubs [{hubs}]. Contains dense relational interactions "
                f"spanning institutional governance, research funding, and academic operations."
            )
            summaries.append({
                "community_id": cid,
                "domain": domain,
                "size": size,
                "top_hubs": comm["top_hubs"],
                "summary": summary_text,
            })

        return summaries

    def generate_cypher_script(self) -> str:
        """
        Generate complete idempotent Cypher script for Neo4j.
        """
        lines = [
            "// ========================================================",
            "// RAISE GraphRAG - Neo4j Knowledge Graph Ingestion Script",
            f"// Nodes: {self.graph.number_of_nodes()} | Edges: {self.graph.number_of_edges()}",
            "// ========================================================\n",
        ]

        for n, d in self.graph.nodes(data=True):
            ntype = d.get("type", "Entity").replace(" ", "_")
            lbl = d.get("label", n).replace('"', '\\"')
            lines.append(f'MERGE (n_{slugify(n)}:{ntype} {{id: "{n}"}}) ON CREATE SET n_{slugify(n)}.label = "{lbl}"')

        lines.append("")
        for u, v, d in self.graph.edges(data=True):
            rel = (d.get("relation") or d.get("type") or "RELATED_TO").upper().replace(" ", "_")
            lines.append(f'MERGE (n_{slugify(u)})-[:{rel}]->(n_{slugify(v)})')

        return "\n".join(lines)

    def remove_document_nodes(self, doc_id: str, entity_ids: Optional[List[str]] = None) -> int:
        """Removes all nodes associated with a document from the NetworkX graph."""
        to_remove = set()
        if entity_ids:
            to_remove.update(entity_ids)
        for n, d in list(self.graph.nodes(data=True)):
            if d.get("document_id") == doc_id or str(n).startswith(f"{doc_id}_"):
                to_remove.add(n)
        
        valid_remove = [n for n in to_remove if self.graph.has_node(n)]
        self.graph.remove_nodes_from(valid_remove)
        for n in valid_remove:
            self.node_provenance.pop(n, None)
        return len(valid_remove)

    def clear(self):
        """Clears all nodes and edges from the graph."""
        self.graph.clear()
        self.node_provenance.clear()


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", str(text).strip())

