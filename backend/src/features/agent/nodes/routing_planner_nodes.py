"""
Routing & Iterative Multi-Hop Reasoning Planner Nodes
======================================================
Orchestrates query classification, strategy routing, iterative multi-hop reasoning loops,
and atomic sub-query retrieval across multi-document repositories.
"""

from __future__ import annotations

import re
from typing import Any, Dict
from ..state import GraphRAGState
from src.retrieval.fusion import hydrate_macro_chunks


class RoutingPlannerNodesMixin:
    """Provides Classification, Routing, and Iterative Multi-Hop Reasoning Nodes."""

    # =========================================================================
    # NODE 2: Classification & Routing Node
    # =========================================================================
    def _classification_and_routing_node(self, state: GraphRAGState) -> Dict[str, Any]:
        query = state.get("query", "")
        active_docs = state.get("active_docs")
        plan = self.rag_engine.agent_router.analyze_query(query, active_docs=active_docs)
        
        q_lower = query.lower()
        if any(w in q_lower for w in ["overview", "summary", "ecosystem", "all domains", "thematic", "broad", "architecture"]):
            strategy = "GLOBAL_COMMUNITY"
        elif any(w in q_lower for w in ["who", "leads", "grant", "patent", "partner", "invested", "startup", "supervises", "collaborated"]):
            strategy = "LOCAL_GRAPH_CYPHER"
        else:
            strategy = "HYBRID_VECTOR"

        telemetry = state.get("telemetry")
        if telemetry:
            telemetry.start_stage("ROUTING")
            telemetry.complete_stage("ROUTING", f"Routed to {strategy} for query: '{query[:60]}'")

        return {
            "routing_strategy": strategy,
            "query_intent": plan.query_type,
            "selected_tools": plan.selected_tools,
            "cypher_repair_count": 0,
            "path_critic_expanded": False,
        }

    def _route_query_strategy(self, state: GraphRAGState) -> str:
        strategy = state.get("routing_strategy", "HYBRID_VECTOR")
        hops = state.get("hops", 1)
        intent = str(state.get("query_intent", "")).upper()
        # Activate cyclical multi-hop reasoning when hops > 1 or intent indicates multi-hop / comparative
        if hops > 1 or intent in ("MULTI_HOP", "COMPARATIVE", "BRIDGE", "MULTI_HOP_REASONING"):
            return "multi_hop_iterative"
        if strategy == "GLOBAL_COMMUNITY":
            return "global_community"
        elif strategy == "LOCAL_GRAPH_CYPHER":
            return "local_cypher"
        return "hybrid_vector"

    # =========================================================================
    # MULTI-HOP CYCLE: Iterative Planner & Sub-Query Retriever Nodes
    # =========================================================================
    def _iterative_planner_node(self, state: GraphRAGState) -> Dict[str, Any]:
        """
        Iterative Multi-Hop Query Planner.
        Evaluates current accumulated knowledge against the original query.
        Decides whether sufficient evidence is gathered (RESOLVED) or generates
        the next atomic sub-query to resolve missing entities across documents.
        """
        telemetry = state.get("telemetry")
        if telemetry:
            telemetry.start_stage("QUERY_PLANNING")

        original_query = state.get("original_query") or state.get("query", "")
        accumulated_context = list(state.get("accumulated_context") or [])
        current_hops = state.get("hop_count", 0)
        max_hops = state.get("max_hops") or state.get("hops") or 3

        # If we reached maximum hops, mark resolved to synthesize with available evidence
        if current_hops >= max_hops:
            if telemetry:
                telemetry.complete_stage("QUERY_PLANNING", f"Reached max hops ({max_hops}); proceeding to synthesis")
            return {
                "is_fully_resolved": True,
                "hop_count": current_hops,
            }

        # Format observations gathered so far
        if not accumulated_context:
            context_summary = "None yet. This is the initial reasoning hop."
        else:
            context_summary = "\n".join(f"- {c}" for c in accumulated_context[-6:])

        # Fast path for Hop 0:
        if current_hops == 0:
            next_query = original_query
            decomposed = state.get("decomposed_queries") or []
            if decomposed and len(decomposed) > 0 and decomposed[0].strip():
                next_query = decomposed[0].strip()

            if telemetry:
                telemetry.complete_stage("QUERY_PLANNING", f"Hop 1 planned sub-query: '{next_query[:60]}...'")
            return {
                "current_sub_query": next_query,
                "hop_count": 1,
                "is_fully_resolved": False,
                "accumulated_context": accumulated_context,
            }

        # For Hop >= 1: Prompt LLM via provider router to evaluate state
        from src.infrastructure.providers.router import get_provider_router, InferenceTask
        router = get_provider_router()
        prompt = (
            f"You are an iterative multi-hop reasoning query planner.\n"
            f"Original Question: {original_query}\n\n"
            f"Facts and observations accumulated so far across documents:\n{context_summary}\n\n"
            f"Task: Evaluate if the accumulated evidence is sufficient to conclusively and factually answer the Original Question.\n"
            f"- If SUFFICIENT: Output exactly 'STATUS: RESOLVED'\n"
            f"- If INSUFFICIENT: Output 'STATUS: SEARCH' followed by 'NEXT_QUERY: <exact atomic search question to find the missing bridge/entity>'\n\n"
            f"Output Format:\n"
            f"STATUS: [RESOLVED or SEARCH]\n"
            f"NEXT_QUERY: [Specific next search query]"
        )

        try:
            resp = router.generate(
                prompt=prompt,
                task=InferenceTask.REASONING,
                temperature=0.0,
                max_tokens=150,
            )
            raw_text = resp.content.strip() if hasattr(resp, "content") else str(resp).strip()
            if "STATUS: RESOLVED" in raw_text.upper() or "STATUS:RESOLVED" in raw_text.upper():
                if telemetry:
                    telemetry.complete_stage("QUERY_PLANNING", f"Resolved at hop {current_hops}")
                return {
                    "is_fully_resolved": True,
                    "hop_count": current_hops,
                }

            match = re.search(r"NEXT_QUERY:\s*(.+)", raw_text, re.IGNORECASE)
            next_q = match.group(1).strip() if match else original_query
            if not next_q or len(next_q) < 5:
                next_q = original_query

            if telemetry:
                telemetry.complete_stage("QUERY_PLANNING", f"Hop {current_hops+1} planned: '{next_q[:60]}...'")

            return {
                "current_sub_query": next_q,
                "hop_count": current_hops + 1,
                "is_fully_resolved": False,
                "accumulated_context": accumulated_context,
            }
        except Exception as exc:
            if telemetry:
                telemetry.complete_stage("QUERY_PLANNING", f"Planner fallback: {exc}")
            return {
                "is_fully_resolved": True,
                "hop_count": current_hops,
            }

    def _sub_query_retriever_node(self, state: GraphRAGState) -> Dict[str, Any]:
        """
        Sub-Query Retrieval Executor.
        Executes hybrid vector + lexical search strictly for the active sub-query,
        hydrates macro-chunks, and appends observations to accumulated_context.
        """
        telemetry = state.get("telemetry")
        if telemetry:
            telemetry.start_stage("HYBRID_RETRIEVAL")

        sub_query = state.get("current_sub_query") or state.get("query", "")
        top_k = state.get("top_k", 4)
        doc_filter = state.get("document_filter")
        active_docs = state.get("active_docs")

        dense_chunks = self.rag_engine.vector_engine.search(
            query=sub_query,
            top_k=top_k,
            doc_filter=doc_filter,
            active_docs=active_docs,
        )

        reranked = dense_chunks
        if hasattr(self.rag_engine, "agent_router") and hasattr(self.rag_engine.agent_router, "reranker"):
            reranked = self.rag_engine.agent_router.reranker.rerank(
                query=sub_query,
                candidates=dense_chunks,
                text_key="text",
                top_n=top_k,
            )

        hydrated = hydrate_macro_chunks(reranked)

        obs_snippets = []
        for c in hydrated[:2]:
            txt = (c.get("plain_text") or c.get("text") or "").strip()
            if txt:
                obs_snippets.append(txt[:300])

        new_obs = f"Observation for '{sub_query}': " + " | ".join(obs_snippets)
        accumulated = list(state.get("accumulated_context") or [])
        accumulated.append(new_obs)

        existing_chunks = list(state.get("relevant_chunks") or [])
        seen_ids = {c.get("chunk_id") or c.get("id") for c in existing_chunks}
        for c in hydrated:
            cid = c.get("chunk_id") or c.get("id")
            if cid not in seen_ids:
                seen_ids.add(cid)
                existing_chunks.append(c)

        if telemetry:
            telemetry.complete_stage("HYBRID_RETRIEVAL", f"Retrieved {len(hydrated)} chunks for sub-query: '{sub_query[:40]}'")

        return {
            "accumulated_context": accumulated,
            "relevant_chunks": existing_chunks,
            "top_chunks": existing_chunks,
        }

    def _route_multi_hop(self, state: GraphRAGState) -> str:
        """Controls cyclical loop between iterative planner and sub-query retrieval."""
        if state.get("is_fully_resolved", False):
            return "fusion_and_response_synthesis"
        max_hops = state.get("max_hops") or state.get("hops") or 3
        if state.get("hop_count", 0) >= max_hops:
            return "fusion_and_response_synthesis"
        chunks = state.get("relevant_chunks") or []
        if state.get("hop_count", 0) > 1 and not chunks:
            return "unverified_responder"
        return "sub_query_retriever"
