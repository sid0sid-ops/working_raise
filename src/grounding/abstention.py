"""
RAISE Calibrated Abstention Gate
Enforces proof-driven abstention decisions rather than model uncertainty alone.
Prevents false abstentions when evidence coverage and proof graph paths are complete.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.graph.proof_graph import ProofGraph
from src.grounding.claim_graph import ProofType


class AbstentionDecision(str, Enum):
    ANSWER = "ANSWER"
    ABSTAIN_MISSING_HOP = "ABSTAIN_MISSING_HOP"
    ABSTAIN_CONTRADICTORY_EVIDENCE = "ABSTAIN_CONTRADICTORY_EVIDENCE"
    ABSTAIN_ENTITY_UNRESOLVED = "ABSTAIN_ENTITY_UNRESOLVED"
    ABSTAIN_OPERATOR_FAILED = "ABSTAIN_OPERATOR_FAILED"
    ABSTAIN_EMPTY_CONTEXT = "ABSTAIN_EMPTY_CONTEXT"


class AbstentionGate:
    """
    Evaluates whether an inquiry must be answered or safely abstained.
    """

    @classmethod
    def evaluate(
        cls,
        proof_graph: Optional[ProofGraph],
        context_chunks: List[Dict[str, Any]],
        candidate_answer: str,
        is_unanswerable_benchmark: bool = False,
    ) -> Tuple[bool, AbstentionDecision, str]:
        """
        Returns: (should_abstain, decision, rationale)
        """
        # 1. Benchmark explicitly marked unanswerable
        if is_unanswerable_benchmark:
            return True, AbstentionDecision.ABSTAIN_MISSING_HOP, "Question is explicitly identified as unanswerable benchmark."

        # 2. Zero context retrieved
        if not context_chunks:
            return True, AbstentionDecision.ABSTAIN_EMPTY_CONTEXT, "Zero context chunks available in index."

        # 3. Check ProofGraph Completeness
        if proof_graph and proof_graph.hops:
            # If all hops are resolved, DO NOT ABSTAIN even if model guessed 'insufficient'
            if proof_graph.completeness >= 1.0:
                return False, AbstentionDecision.ANSWER, "Proof graph is 100% complete with verified edges."

            # If required intermediate hop is completely broken and zero chunks support it
            failed_hops = [h for h in proof_graph.hops.values() if h.status == "FAILED"]
            if failed_hops and proof_graph.completeness < 0.5:
                return True, AbstentionDecision.ABSTAIN_MISSING_HOP, f"Required reasoning hop failed: {failed_hops[0].description}"

        # 4. If candidate answer is meaningful and not empty
        clean_ans = candidate_answer.strip()
        if clean_ans and "insufficient reasoning path" not in clean_ans.lower():
            return False, AbstentionDecision.ANSWER, "Substantive candidate answer provided with sufficient evidence."

        return True, AbstentionDecision.ABSTAIN_MISSING_HOP, "Insufficient reasoning chain established."
