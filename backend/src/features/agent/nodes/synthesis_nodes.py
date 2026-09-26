"""
Response Synthesis, Quality Gate & Citation Validation Nodes
=============================================================
Orchestrates claim synthesis, Runtime Faithfulness Quality Gate evaluations,
anti-hallucination refusals, and citation provenance verification.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from ..state import GraphRAGState
from src.features.evaluation.engine import RuntimeFaithfulnessQualityGate, CitationValidator


class SynthesisNodesMixin:
    """Provides Fusion & Response Synthesis, Runtime Quality Gate, and Citation Validation Nodes."""

    # =========================================================================
    # NODE 9: Fusion & Response Synthesis Node
    # =========================================================================
    def _fusion_and_response_synthesis_node(self, state: GraphRAGState) -> Dict[str, Any]:
        telemetry = state.get("telemetry")
        if telemetry:
            telemetry.start_stage("SYNTHESIS")

        query = state.get("query", "")
        active_docs = state.get("active_docs")
        doc_filter = state.get("document_filter")
        subgraph = state.get("subgraph", {})

        plan = self.rag_engine.agent_router.analyze_query(query, active_docs=active_docs, doc_filter=doc_filter)
        if doc_filter:
            plan.retrieved_evidence["target_doc_filter"] = doc_filter
        plan.retrieved_evidence["subgraph"] = subgraph
        plan.retrieved_evidence["chunks"] = state.get("relevant_chunks", [])
        executed_plan = self.rag_engine.agent_router.execute_plan(plan, active_docs=active_docs)

        plan_chunks = executed_plan.retrieved_evidence.get("chunks", [])

        if telemetry:
            telemetry.complete_stage("SYNTHESIS", f"Generated answer ({len(executed_plan.grounded_answer)} chars)")

        math_facts = []
        for clm in executed_plan.verified_claims:
            c_text = str(clm.get("claim", "")) if isinstance(clm, dict) else str(clm)
            if "Mathematically Verified" in c_text:
                math_facts.append(c_text)

        return {
            "grounded_answer": executed_plan.grounded_answer,
            "traceability_score": executed_plan.traceability_score,
            "verified_claims": executed_plan.verified_claims,
            "citations": executed_plan.citations,
            "follow_up_inquiries": getattr(executed_plan, "follow_up_inquiries", []),
            "relevant_chunks": plan_chunks or state.get("relevant_chunks", []),
            "top_chunks": plan_chunks or state.get("relevant_chunks", []),
            "math_facts": math_facts,
            "answer_contract": executed_plan.answer_contract,
            "synthesis_metadata": getattr(executed_plan, "synthesis_metadata", None),
        }

    # =========================================================================
    # NODE 10: Runtime Faithfulness Quality Gate Node
    # =========================================================================
    def _runtime_faithfulness_gate_node(self, state: GraphRAGState) -> Dict[str, Any]:
        telemetry = state.get("telemetry")
        if telemetry:
            telemetry.start_stage("QUALITY_GATE")

        query = state.get("query", "")
        answer = state.get("grounded_answer", "")
        chunks = state.get("relevant_chunks", []) or state.get("citations", [])
        subgraph = state.get("subgraph", {})
        citations = state.get("citations", [])
        active_docs = state.get("active_docs")
        math_facts = state.get("math_facts", [])
        retry_count = state.get("retry_count", 0)
        mode = state.get("mode", "fast")
        max_retries = 0 if mode == "fast" else 2

        gate_res = self.quality_gate.evaluate_runtime_state(
            query=query,
            answer=answer,
            retrieved_chunks=chunks,
            graph_evidence=subgraph,
            citations_list=citations,
            active_docs=active_docs,
            math_facts=math_facts,
            retry_count=retry_count,
            max_retries=max_retries,
        )

        if telemetry:
            telemetry.complete_stage("QUALITY_GATE", f"Decision: {gate_res['decision']}")

        return {
            "quality_gate_decision": gate_res["decision"],
            "quality_gate_report": gate_res.get("report", {}),
            "retry_count": gate_res.get("retry_count", retry_count),
        }

    def _evaluate_gate_decision(self, state: GraphRAGState) -> str:
        decision = state.get("quality_gate_decision", "accept")
        if decision == "accept":
            return "accept"
        elif decision == "retry":
            return "retry"
        return "unable_to_verify"

    # =========================================================================
    # NODE 13: Citation Validation Node
    # =========================================================================
    def _citation_validation_node(self, state: GraphRAGState) -> Dict[str, Any]:
        telemetry = state.get("telemetry")
        if telemetry:
            telemetry.complete_stage("COMPLETED", "Pipeline workflow completed successfully")

        answer = state.get("grounded_answer", "")
        citations = state.get("citations", [])
        active_docs = state.get("active_docs")

        clean_answer = answer
        negative_cit_pat = re.compile(
            r"(\b(?:do(?:es)?\s+not\s+(?:contain|mention|state|provide|include|win|have|specify|give|detail|list|report)|"
            r"did\s+not\s+(?:win|receive|award|mention|contain)|"
            r"no\s+(?:mention|information|data|details|record|reference|evidence|indication|nobel|prizes?)|"
            r"not\s+(?:found|mentioned|provided|available|present|contained|won|specified|detailed))\b[^.\n]*?)\s*\[\d+\]",
            re.IGNORECASE
        )
        if negative_cit_pat.search(clean_answer):
            clean_answer = negative_cit_pat.sub(r"\1", clean_answer)

        clean_answer = re.sub(
            r'(?:(?:Excerpts?|Passages?|Sources?|References?)\s*(?:\[\d+\][,\s&and–-]*)+[^.\n]*(?:omitted|excluded|not\s+(?:used|relevant)|do\s+not\s+pertain|pertain\s+to|refer\s+to|irrelevant)[^.\n]*[.\n]?)',
            '',
            clean_answer,
            flags=re.IGNORECASE,
        ).strip()

        _, issues, _ = CitationValidator.validate_citations(clean_answer, citations, active_docs)
        cited_indices = set(int(n) for m in re.findall(r"\[([0-9\s,\-–]+)\]", clean_answer) for n in re.findall(r"\d+", m))
        if cited_indices:
            filtered_citations = [c for c in citations if isinstance(c, dict) and c.get("citation_index") in cited_indices]
        else:
            filtered_citations = list(citations) if citations else []
        return {
            "grounded_answer": clean_answer,
            "citations": filtered_citations,
        }

    # =========================================================================
    # NODE 14: Unverified Responder Node (Controlled Refusal on Failure)
    # =========================================================================
    def _unverified_responder_node(self, state: GraphRAGState) -> Dict[str, Any]:
        telemetry = state.get("telemetry")
        if telemetry:
            telemetry.complete_stage("COMPLETED", "Refusal response delivered due to unverified claims")

        return {
            "grounded_answer": RuntimeFaithfulnessQualityGate.UNVERIFIED_REFUSAL_MESSAGE,
            "traceability_score": 0.0,
            "citations": [],
            "verified_claims": [],
        }
