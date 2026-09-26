"""
Runtime Faithfulness Quality Gate & Self-Correction Controller
==============================================================
Operates as the production quality checkpoint in the LangGraph StateGraph workflow.
Monitors generated answer faithfulness, manages retry self-correction loops,
and safely triggers unverified refusals when grounding fails.

Architectural Guarantees & Lifecycle:
-------------------------------------
1. Empty Workspace Bypass:
   - If `active_docs` is empty (`[]`), immediately terminates with `empty_workspace` status
     and instructs the user to upload an academic PDF, executing zero unnecessary LLM calls.

2. Quality Gate Evaluation:
   - Evaluates generated responses using `LocalHeuristicEvaluator` (faithfulness >= threshold,
     0 citation errors, 0 ungrounded numeric metrics).
   - Verifies against `RigorousQualityGate` for completeness and institutional boundary containment.

3. Controlled Self-Correction Retry Loop:
   - If response fails quality evaluation AND `retry_count < max_retries` (default: 2):
     * Formulates an expanded/clarified query targeting specific verified metrics.
     * Transitions StateGraph into the query reformulation and secondary retrieval branch.
     * Increments `retry_count`.

4. Safe Unverified Refusal:
   - If quality fails AND retry attempts are exhausted (`retry_count >= max_retries`):
     * Emits `UNVERIFIED_REFUSAL_MESSAGE` instead of leaking a hallucinated or partially verified answer.
     * Prevents misleading citations and numerical fabrications.

How to Update or Tune:
----------------------
- To modify default acceptance threshold: adjust `threshold: float = 0.80` in `__init__()`.
- To modify maximum retry cap: adjust `max_retries: int = 2` in `__init__()`.
- To modify refusal phrasing: edit `UNVERIFIED_REFUSAL_MESSAGE`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .heuristic_evaluator import LocalHeuristicEvaluator


class RuntimeFaithfulnessQualityGate:
    """
    Runtime Quality Gate node executed in LangGraph StateGraph.
    Monitors generation faithfulness, validates citations, and enforces strict retry limits.
    """

    UNVERIFIED_REFUSAL_MESSAGE = (
        "I could not verify this answer against the uploaded academic sources. "
        "Please upload additional relevant material or refine the question."
    )

    EMPTY_WORKSPACE_MESSAGE = "Please upload an academic PDF to begin your research."

    def __init__(self, threshold: float = 0.80, max_retries: int = 2):
        self.threshold = threshold
        self.max_retries = max_retries

    def evaluate_runtime_state(
        self,
        query: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        graph_evidence: Optional[Dict[str, Any]] = None,
        citations_list: Optional[List[Dict[str, Any]]] = None,
        active_docs: Optional[List[str]] = None,
        math_facts: Optional[List[str]] = None,
        retry_count: int = 0,
        max_retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates the runtime state of a generated answer in the LangGraph workflow.

        Returns a decision dictionary:
          - decision: "accept" | "retry" | "unable_to_verify" | "empty_workspace"
          - answer: final response text
          - report: detailed evaluation report dictionary
          - is_acceptable: bool
          - retry_count: updated integer
          - reformulated_query: optional query string for retry branch
        """
        # 1. Handle Empty Workspace
        if active_docs is not None and len(active_docs) == 0:
            return {
                "decision": "empty_workspace",
                "answer": self.EMPTY_WORKSPACE_MESSAGE,
                "is_acceptable": True,
                "retry_count": retry_count,
            }

        # Convert graph evidence to structured facts
        graph_facts = []
        if graph_evidence:
            for trip in graph_evidence.get("structured_triples", []):
                graph_facts.append({"fact": trip})
            for node in graph_evidence.get("nodes", []):
                graph_facts.append({"fact": f"Node: {node.get('label')} ({node.get('type')})"})

        report = LocalHeuristicEvaluator.evaluate(
            query=query,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            graph_facts=graph_facts,
            citations_list=citations_list,
            active_docs=active_docs,
            math_facts=math_facts,
            threshold=self.threshold,
        )

        # Run RigorousQualityGate (from blueprint) for strict completeness and boundary verification
        from src.features.evaluation.quality_gate import RigorousQualityGate
        rigorous_validator = RigorousQualityGate(faithfulness_threshold=self.threshold)
        contexts = [str(c.get("plain_text") or c.get("text") or "") for c in retrieved_chunks]
        rigorous_check = rigorous_validator.verify_completeness_and_grounding(
            query=query,
            response=answer,
            retrieved_contexts=contexts,
        )

        if report.is_acceptable and rigorous_check["decision"] == "ACCEPT":
            return {
                "decision": "accept",
                "answer": answer,
                "report": report.to_dict(),
                "is_acceptable": True,
                "retry_count": retry_count,
            }

        rejection_reason = report.rejection_reason or rigorous_check.get("reason")

        # If rejected, evaluate retry limits
        effective_max = max_retries if max_retries is not None else self.max_retries
        if retry_count < effective_max:
            clean_q = re.sub(r"[^a-zA-Z0-9\s]", "", query).strip()
            reformulated_query = f"{clean_q} specific verified facts metrics"
            return {
                "decision": "retry",
                "report": report.to_dict(),
                "is_acceptable": False,
                "retry_count": retry_count + 1,
                "reformulated_query": reformulated_query,
                "rejection_reason": rejection_reason,
            }
        else:
            # Controlled refusal after exhausting retries
            return {
                "decision": "unable_to_verify",
                "answer": self.UNVERIFIED_REFUSAL_MESSAGE,
                "report": report.to_dict(),
                "is_acceptable": False,
                "retry_count": retry_count,
                "rejection_reason": report.rejection_reason,
            }
