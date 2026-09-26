"""
Query Intake & Fast Response Nodes
==================================
Handles coreference resolution, intent classification, empty workspace bypass,
and zero-DB general conversation responses.
"""

from __future__ import annotations

from typing import Any, Dict
from ..state import GraphRAGState


class IntakeNodesMixin:
    """Provides Query Intake, General Chat Responder, and Empty Workspace nodes."""

    # =========================================================================
    # NODE 0: Query Intake & Reformulation Node
    # =========================================================================
    def _query_intake_node(self, state: GraphRAGState) -> Dict[str, Any]:
        raw_query = state.get("query", "")
        thread_id = state.get("thread_id")
        chat_history = state.get("chat_history")

        # Dynamically link session_manager if available on rag_engine
        if getattr(self.rag_engine, "session_manager", None) and not self.intake_engine.coref.session_manager:
            self.intake_engine.coref.session_manager = self.rag_engine.session_manager
            self.intake_engine.session_manager = self.rag_engine.session_manager

        intake_res = self.intake_engine.process(
            query=raw_query,
            thread_id=thread_id,
            chat_history=chat_history,
        )

        active_docs = state.get("active_docs")
        is_empty = (active_docs is not None and len(active_docs) == 0)

        return {
            "original_query": intake_res.original_query,
            "standalone_query": intake_res.standalone_query,
            "decomposed_queries": intake_res.decomposed_queries,
            "bypass_retrieval": intake_res.intent_route.bypass_retrieval,
            "direct_response": intake_res.intent_route.direct_response,
            "resolved_entity": intake_res.resolved_entity,
            "telemetry": intake_res.telemetry,
            "query": intake_res.standalone_query,
            "query_intent": intake_res.intent_route.intent,
            "quality_gate_decision": "empty_workspace" if (is_empty and not intake_res.intent_route.bypass_retrieval) else "active",
        }

    def _evaluate_intake_route(self, state: GraphRAGState) -> str:
        if state.get("bypass_retrieval"):
            return "bypass"
        if state.get("quality_gate_decision") == "empty_workspace":
            return "empty_workspace"
        active_docs = state.get("active_docs")
        if active_docs is not None and len(active_docs) == 0:
            return "empty_workspace"
        return "proceed"

    def _general_chat_responder_node(self, state: GraphRAGState) -> Dict[str, Any]:
        telemetry = state.get("telemetry")
        if telemetry:
            telemetry.complete_stage("COMPLETED", "General chat response delivered (Zero-DB bypass)")
        return {
            "grounded_answer": state.get("direct_response") or "Hello! I am your RAISE Academic GraphRAG Assistant. How can I assist your research today?",
            "traceability_score": 1.0,
            "citations": [],
            "verified_claims": [],
            "quality_gate_decision": "accept",
            "pipeline_stages": telemetry.to_list() if telemetry else [],
        }

    # =========================================================================
    # NODE 1: Empty Workspace Responder
    # =========================================================================
    def _empty_workspace_responder_node(self, state: GraphRAGState) -> Dict[str, Any]:
        telemetry = state.get("telemetry")
        if telemetry:
            telemetry.skip_stage("VECTOR_RETRIEVAL", "Empty workspace")
            telemetry.skip_stage("BM25_RETRIEVAL", "Empty workspace")
            telemetry.skip_stage("GRAPH_RETRIEVAL", "Empty workspace")
            telemetry.skip_stage("FUSION", "Empty workspace")
            telemetry.skip_stage("RERANKING", "Empty workspace")
            telemetry.start_stage("SYNTHESIS")
            telemetry.complete_stage("SYNTHESIS", "Empty workspace advisory issued")
            telemetry.complete_stage("COMPLETED", "Empty workspace flow completed")
        return {
            "grounded_answer": "Please upload an academic PDF to begin your research.",
            "traceability_score": 1.0,
            "citations": [],
            "verified_claims": [],
            "quality_gate_decision": "empty_workspace",
            "pipeline_stages": telemetry.to_list() if telemetry else [],
        }
