"""
RAISE Academic GraphRAG — LangGraph StateGraph Workflow Orchestrator
Implements cyclical, self-reflective GraphRAG execution graph with:
  1. Query Intent Classification & Planning Node
  2. Dense Vector Retrieval Node (ChromaDB)
  3. Multi-Hop Knowledge Graph Traversal Node (Neo4j / NetworkX)
  4. Anti-Hallucination Claim Corroboration & Synthesis Node
  5. Conditional Evaluator & Corrective Retrieval Expansion Cycle
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END


class GraphRAGState(TypedDict, total=False):
    """LangGraph State Container for GraphRAG Query Lifecycle."""
    query: str
    hops: int
    top_k: int
    document_filter: Optional[str]
    active_docs: Optional[List[str]]

    # Pipeline Artifacts
    query_intent: str
    selected_tools: List[str]
    relevant_chunks: List[Dict[str, Any]]
    seed_node_ids: List[str]
    subgraph: Dict[str, Any]
    verified_claims: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    traceability_score: float
    grounded_answer: str
    answer_contract: Dict[str, Any]
    
    # Cyclical Adaptive Control
    retry_count: int
    needs_expansion: bool
    execution_time: float


class AcademicGraphRAGWorkflow:
    """
    StateGraph wrapper orchestrating the complete offline GraphRAG engine.
    """

    def __init__(self, rag_engine: Any):
        self.rag_engine = rag_engine
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(GraphRAGState)

        # 1. Define Nodes
        workflow.add_node("intent_analyzer", self._intent_analyzer_node)
        workflow.add_node("vector_retriever", self._vector_retriever_node)
        workflow.add_node("graph_traverser", self._graph_traverser_node)
        workflow.add_node("synthesizer_verifier", self._synthesizer_verifier_node)
        workflow.add_node("corrective_expander", self._corrective_expander_node)

        # 2. Define Linear Edges
        workflow.add_edge(START, "intent_analyzer")
        workflow.add_edge("intent_analyzer", "vector_retriever")
        workflow.add_edge("vector_retriever", "graph_traverser")
        workflow.add_edge("graph_traverser", "synthesizer_verifier")

        # 3. Define Conditional Branching (Self-Reflective Corrective Cycle)
        workflow.add_conditional_edges(
            "synthesizer_verifier",
            self._evaluate_grounding_condition,
            {
                "expand": "corrective_expander",
                "finalize": END
            }
        )

        # Loop back from expander to vector retrieval
        workflow.add_edge("corrective_expander", "vector_retriever")

        return workflow.compile()

    # =========================================================================
    # NODE 1: Intent Analysis
    # =========================================================================
    def _intent_analyzer_node(self, state: GraphRAGState) -> Dict[str, Any]:
        query = state.get("query", "")
        active_docs = state.get("active_docs")
        plan = self.rag_engine.agent_router.analyze_query(query, active_docs=active_docs)
        
        return {
            "query_intent": plan.query_type,
            "selected_tools": plan.selected_tools,
            "retry_count": state.get("retry_count", 0),
        }

    # =========================================================================
    # NODE 2: Dense Vector Retrieval (ChromaDB)
    # =========================================================================
    def _vector_retriever_node(self, state: GraphRAGState) -> Dict[str, Any]:
        query = state.get("query", "")
        top_k = state.get("top_k", 4)
        doc_filter = state.get("document_filter")
        active_docs = state.get("active_docs")

        # Search dense vectors scoped strictly to active workspace documents
        relevant = self.rag_engine.vector_engine.search(
            query=query,
            top_k=top_k,
            doc_filter=doc_filter,
            active_docs=active_docs
        )

        # Extract Seed Node IDs for graph traversal
        seed_node_ids: List[str] = []
        for chk in relevant:
            cid = chk.get("id") or chk.get("chunk_id")
            if cid:
                seed_node_ids.append(cid)
            u = chk.get("metadata", {}).get("university")
            if u:
                u_id = f"uni_{re.sub(r'[^a-zA-Z0-9]', '_', u.lower())[:30]}"
                seed_node_ids.append(u_id)

        return {
            "relevant_chunks": relevant,
            "seed_node_ids": seed_node_ids,
        }

    # =========================================================================
    # NODE 3: Knowledge Graph Multi-Hop Traversal (Neo4j Industry Standard)
    # =========================================================================
    def _graph_traverser_node(self, state: GraphRAGState) -> Dict[str, Any]:
        query = state.get("query", "")
        seed_node_ids = state.get("seed_node_ids", [])
        hops = state.get("hops", 2)
        doc_filter = state.get("document_filter")
        doc_id = re.sub(r"[^a-zA-Z0-9]", "_", doc_filter.replace(".pdf", ""))[:40] if (doc_filter and doc_filter != "ALL") else None

        # Extract keywords from query for Neo4j fuzzy entity matching
        kws = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", query) if w.lower() not in {"what", "the", "and", "for", "with", "how", "are", "tell", "show"}]

        subgraph = None
        # 1. Primary: Query Live Neo4j Graph Database via Cypher
        if self.rag_engine.neo4j_db.connected:
            subgraph = self.rag_engine.neo4j_db.query_multihop_subgraph(
                seed_ids=seed_node_ids,
                keywords=kws,
                hops=hops,
                doc_id=doc_id,
                limit=35
            )

        # 2. Secondary / In-Memory Fallback
        if not subgraph or not subgraph.get("nodes"):
            subgraph = self.rag_engine.graph_engine.extract_subgraph(
                seed_node_ids=seed_node_ids,
                hops=hops,
                max_nodes=35,
            )

        return {
            "subgraph": subgraph,
        }

    # =========================================================================
    # NODE 4: Answer Synthesis & Anti-Hallucination Verification
    # =========================================================================
    def _synthesizer_verifier_node(self, state: GraphRAGState) -> Dict[str, Any]:
        query = state.get("query", "")
        subgraph = state.get("subgraph", {})
        doc_filter = state.get("document_filter")
        active_docs = state.get("active_docs")

        plan = self.rag_engine.agent_router.analyze_query(query, active_docs=active_docs)
        plan.retrieved_evidence["subgraph"] = subgraph
        executed_plan = self.rag_engine.agent_router.execute_plan(plan, active_docs=active_docs)

        citations = executed_plan.citations or []
        if doc_filter and doc_filter != "ALL":
            citations = [c for c in citations if c.get("pdf_filename") == doc_filter] or citations

        score = executed_plan.traceability_score
        retry_count = state.get("retry_count", 0)

        # Check if score is low and we haven't retried yet
        needs_expansion = (score < 0.45 and retry_count == 0 and len(state.get("relevant_chunks", [])) < 8)

        return {
            "grounded_answer": executed_plan.grounded_answer,
            "traceability_score": score,
            "verified_claims": executed_plan.verified_claims,
            "citations": citations,
            "answer_contract": executed_plan.answer_contract,
            "needs_expansion": needs_expansion,
        }

    # =========================================================================
    # NODE 5: Corrective Retrieval Expander (Cyclical Edge)
    # =========================================================================
    def _corrective_expander_node(self, state: GraphRAGState) -> Dict[str, Any]:
        """Expands retrieval parameters to recover deeper ground-truth evidence."""
        curr_hops = state.get("hops", 2)
        curr_top_k = state.get("top_k", 4)
        curr_retries = state.get("retry_count", 0)

        return {
            "hops": curr_hops + 1,
            "top_k": curr_top_k + 3,
            "retry_count": curr_retries + 1,
            "needs_expansion": False,
        }

    # =========================================================================
    # CONDITIONAL EDGE: Quality Gate
    # =========================================================================
    def _evaluate_grounding_condition(self, state: GraphRAGState) -> str:
        if state.get("needs_expansion", False):
            return "expand"
        return "finalize"

    # =========================================================================
    # PUBLIC RUNNER INTERFACE
    # =========================================================================
    def run(
        self,
        query: str,
        hops: int = 2,
        top_k: int = 4,
        document_filter: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute the LangGraph state machine synchronously."""
        initial_state: GraphRAGState = {
            "query": query,
            "hops": hops,
            "top_k": top_k,
            "document_filter": document_filter,
            "active_docs": active_docs,
            "retry_count": 0,
            "needs_expansion": False,
        }

        t0 = time.time()
        final_state = self.app.invoke(initial_state)
        final_state["execution_time"] = round(time.time() - t0, 3)

        return {
            "query": final_state.get("query"),
            "query_type": final_state.get("query_intent"),
            "selected_tools": final_state.get("selected_tools"),
            "grounded_answer": final_state.get("grounded_answer"),
            "traceability_score": final_state.get("traceability_score"),
            "verified_claims": final_state.get("verified_claims"),
            "citations": final_state.get("citations"),
            "answer_contract": final_state.get("answer_contract"),
            "subgraph": final_state.get("subgraph"),
            "top_chunks": final_state.get("relevant_chunks"),
            "retry_count": final_state.get("retry_count", 0),
            "execution_time": final_state.get("execution_time"),
        }
