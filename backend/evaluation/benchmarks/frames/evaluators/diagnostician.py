"""
FRAMES Benchmark Failure Diagnostician
Implements the 13-category failure taxonomy specified in Section 9 of the benchmark specification:
  1. RETRIEVAL_FAILURE
  2. GRAPH_RETRIEVAL_FAILURE
  3. RERANKING_FAILURE
  4. CONTEXT_ASSEMBLY_FAILURE
  5. MULTIHOP_REASONING_FAILURE
  6. NUMERICAL_REASONING_FAILURE
  7. TEMPORAL_REASONING_FAILURE
  8. TABULAR_REASONING_FAILURE
  9. CONSTRAINT_FAILURE
  10. GENERATION_FAILURE
  11. HALLUCINATION
  12. INSUFFICIENT_INFORMATION
  13. UNKNOWN_FAILURE
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .factuality import FactualityResult
from .reasoning import ReasoningResult
from .retrieval import RetrievalResult
from ..data.schema import FramesQuestion


class FailureDiagnosis(BaseModel):
    """Structured failure diagnosis and root-cause attribution."""
    question_id: str
    is_failure: bool
    primary_failure: Optional[str] = None
    secondary_failures: List[str] = Field(default_factory=list)
    retrieval_evidence_found: bool = False
    graph_evidence_found: bool = False
    reasoning_failure: bool = False
    probable_cause: str = ""


class FailureDiagnostician:
    """
    Performs forensic diagnostic analysis across retrieval logs, reasoning scores,
    and factuality metrics to attribute failure root causes.
    """

    TAXONOMY = [
        "RETRIEVAL_FAILURE",
        "GRAPH_RETRIEVAL_FAILURE",
        "GRAPH_ENTITY_RESOLUTION_FAILURE",
        "GRAPH_PATH_FAILURE",
        "MULTIHOP_INTEGRATION_FAILURE",
        "REASONING_FAILURE",
        "NUMERICAL_REASONING_FAILURE",
        "TEMPORAL_REASONING_FAILURE",
        "TABULAR_REASONING_FAILURE",
        "CONSTRAINT_FAILURE",
        "GENERATION_FAILURE",
        "FALLBACK_FAILURE",
        "UNSUPPORTED_CLAIM",
        "HALLUCINATION",
        "INSUFFICIENT_INFORMATION",
        "VECTOR_CONFIG_MISMATCH",
        "VECTOR_COLLECTION_MISMATCH",
        "TABLE_EXTRACTION_FAILURE",
        "MATH_ENGINE_FAILURE",
        "PROMPT_CONTRACT_FAILURE",
        "LLM_PARSE_FAILURE",
        "LLM_TIMEOUT",
        "UNGROUNDED_CLAIM_BLOCKED",
        "UNKNOWN_FAILURE",
    ]

    def diagnose(
        self,
        question: FramesQuestion,
        factuality: FactualityResult,
        reasoning: ReasoningResult,
        retrieval: RetrievalResult,
        pipeline_trace: Dict[str, Any],
    ) -> FailureDiagnosis:
        """
        Diagnoses whether a run succeeded, or identifies primary and secondary failure modes.
        Enforces granular taxonomy and strictly prevents misclassifying high-coverage queries as GRAPH_RETRIEVAL_FAILURE.
        """
        qid = question.question_id
        is_success = factuality.answer_status == "correct" and factuality.factuality_score >= 0.80

        graph_trace = pipeline_trace.get("retrieval_trace", {}).get("graph_data")
        if not graph_trace or not isinstance(graph_trace, dict):
            graph_trace = pipeline_trace.get("retrieval_trace", {}).get("hybrid_details", {}).get("graph_data", {})
        graph_nodes = graph_trace.get("subgraph_nodes", []) if isinstance(graph_trace, dict) else []
        graph_edges = graph_trace.get("subgraph_edges", []) if isinstance(graph_trace, dict) else []
        graph_evidence_found = bool(graph_nodes)

        if is_success:
            return FailureDiagnosis(
                question_id=qid,
                is_failure=False,
                primary_failure=None,
                secondary_failures=[],
                retrieval_evidence_found=retrieval.hit_rate > 0.0,
                graph_evidence_found=graph_evidence_found,
                reasoning_failure=False,
                probable_cause="Pipeline executed and reasoned over retrieved evidence successfully."
            )

        primary: Optional[str] = None
        secondaries: List[str] = []
        probable_cause = ""

        evidence_found = retrieval.hit_rate > 0.0 or retrieval.evidence_coverage >= 0.40
        reasoning_fail = reasoning.overall_reasoning_score < 0.60
        gen_mode = pipeline_trace.get("generation_mode", "")
        audit = pipeline_trace.get("audit", {})
        exact_trigger = str(audit.get("exact_fallback_trigger") or audit.get("fallback_reason") or "").lower()

        # 1. Configuration & Storage Mismatch
        if "chroma" in exact_trigger or "vector_store" in exact_trigger:
            primary = "VECTOR_CONFIG_MISMATCH"
            secondaries.append("FALLBACK_FAILURE")
            probable_cause = f"Vector database storage or configuration contract mismatch detected: {exact_trigger}"

        # 2. Fallback / Controlled Abstention Failure (Typed Triggers)
        elif gen_mode in ["controlled_abstention", "deterministic_fallback"] or factuality.answer_status == "abstained":
            if "ungrounded_claim_blocked" in exact_trigger or "unsupported_claim_blocked" in exact_trigger:
                primary = "UNGROUNDED_CLAIM_BLOCKED"
                secondaries.append("FALLBACK_FAILURE")
                probable_cause = f"Factuality verifier detected and blocked ungrounded claim ({audit.get('fallback_reason')}); safe controlled abstention emitted."
            elif "missing_intermediate_hop" in exact_trigger:
                primary = "MULTIHOP_INTEGRATION_FAILURE"
                secondaries.append("FALLBACK_FAILURE")
                probable_cause = f"Multi-hop bridge broke: intermediate dependency documents missing."
            elif "zero_chunks_retrieved" in exact_trigger:
                primary = "RETRIEVAL_FAILURE"
                secondaries.append("FALLBACK_FAILURE")
                probable_cause = "Zero candidate chunks retrieved from index."
            elif "numerical_input_unverified" in exact_trigger:
                primary = "NUMERICAL_REASONING_FAILURE"
                secondaries.append("FALLBACK_FAILURE")
                probable_cause = "Numerical arithmetic variables could not be grounded in retrieved context."
            elif "table_cell_not_found" in exact_trigger:
                primary = "TABULAR_REASONING_FAILURE"
                secondaries.append("FALLBACK_FAILURE")
                probable_cause = "Target table cell coordinate or schema lookup failed."
            elif "timeout" in exact_trigger or audit.get("llm_timeout"):
                primary = "LLM_TIMEOUT"
                secondaries.append("FALLBACK_FAILURE")
                probable_cause = f"LLM generation exceeded operational deadline ({exact_trigger})."
            elif retrieval.total_required_sources > 0 and retrieval.evidence_coverage < 0.40:
                primary = "RETRIEVAL_FAILURE"
                secondaries.append("FALLBACK_FAILURE")
                probable_cause = f"Retrieval failed to cover required sources ({len(retrieval.missing_sources)} missing); safe abstention triggered."
            elif "insufficient" in exact_trigger:
                primary = "MULTIHOP_INTEGRATION_FAILURE" if question.is_multihop else "REASONING_FAILURE"
                secondaries.append("FALLBACK_FAILURE")
                probable_cause = "Model determined retrieved context was insufficient to establish full reasoning chain."
            else:
                primary = "FALLBACK_FAILURE"
                trigger = audit.get("exact_fallback_trigger") or audit.get("fallback_reason") or "Inference failure"
                probable_cause = f"Reasoning path was interrupted or LLM synthesis failed ({trigger}); controlled abstention emitted."
                if question.is_multihop:
                    secondaries.append("MULTIHOP_INTEGRATION_FAILURE")

        # 3. LLM Execution Faults
        elif "timeout" in exact_trigger or audit.get("llm_timeout"):
            primary = "LLM_TIMEOUT"
            secondaries.append("FALLBACK_FAILURE")
            probable_cause = f"LLM generation exceeded operational deadline ({exact_trigger})."
        elif "parse" in exact_trigger or "json" in exact_trigger:
            if question.is_multihop:
                primary = "MULTIHOP_INTEGRATION_FAILURE"
            elif question.is_tabular:
                primary = "TABULAR_REASONING_FAILURE"
            elif question.is_numerical:
                primary = "NUMERICAL_REASONING_FAILURE"
            else:
                primary = "REASONING_FAILURE"
            secondaries.append("FALLBACK_FAILURE")
            probable_cause = "Model reasoning failed to synthesize a well-grounded answer adhering to reference facts."

        # 4. Insufficient Information / Zero Retrieval
        elif factuality.answer_status == "unanswerable" or pipeline_trace.get("retrieved_chunks_count", 0) == 0:
            primary = "INSUFFICIENT_INFORMATION"
            if retrieval.total_required_sources > 0 and retrieval.hit_rate == 0.0:
                secondaries.append("RETRIEVAL_FAILURE")
            probable_cause = "No relevant source passages were available or retrieved for this inquiry."

        # 5. Unsupported Claims / Hallucination
        elif factuality.answer_status == "unsupported" or factuality.grounding_score < 0.35:
            primary = "UNSUPPORTED_CLAIM"
            secondaries.append("HALLUCINATION")
            if not evidence_found:
                secondaries.append("RETRIEVAL_FAILURE")
            probable_cause = "Generated answer asserted claims or facts not corroborated by retrieved context."

        # 6. Retrieval Failure (Missing required sources)
        elif retrieval.total_required_sources > 0 and retrieval.evidence_coverage < 0.40:
            primary = "RETRIEVAL_FAILURE"
            if question.is_multihop:
                secondaries.append("MULTIHOP_INTEGRATION_FAILURE")
            probable_cause = f"Retrieval failed to cover required Wikipedia sources ({len(retrieval.missing_sources)} missing)."

        # 7. High-Coverage or Evidence Found Path: NEVER classify as GRAPH_RETRIEVAL_FAILURE or RETRIEVAL_FAILURE
        elif evidence_found:
            # Check Graph Sub-failures as secondaries
            if pipeline_trace.get("mode") in ["graph", "hybrid"] and question.is_multihop:
                if not graph_nodes:
                    secondaries.append("GRAPH_ENTITY_RESOLUTION_FAILURE")
                elif not graph_edges:
                    secondaries.append("GRAPH_PATH_FAILURE")

            # Specialized Reasoning Failures
            if question.is_numerical and reasoning.numerical_score is not None and reasoning.numerical_score < 0.60:
                if "math_engine" in exact_trigger or "division by zero" in exact_trigger:
                    primary = "MATH_ENGINE_FAILURE"
                    secondaries.append("NUMERICAL_REASONING_FAILURE")
                    probable_cause = "Symbolic math evaluation engine failed or raised an arithmetic exception."
                else:
                    primary = "NUMERICAL_REASONING_FAILURE"
                    probable_cause = "Numerical calculations or quantitative derivations diverged from reference."
            elif question.is_temporal and reasoning.temporal_score is not None and reasoning.temporal_score < 0.60:
                primary = "TEMPORAL_REASONING_FAILURE"
                probable_cause = "Temporal sequencing or date constraint was violated in synthesized answer."
            elif question.is_tabular and reasoning.tabular_score is not None and reasoning.tabular_score < 0.60:
                if "table" in exact_trigger or "cell" in exact_trigger:
                    primary = "TABLE_EXTRACTION_FAILURE"
                    secondaries.append("TABULAR_REASONING_FAILURE")
                    probable_cause = "Table header schema or cell coordinate extraction failed."
                else:
                    primary = "TABULAR_REASONING_FAILURE"
                    probable_cause = "Structured tabular data lookup failed to map row/column coordinates correctly."
            elif question.is_constraint and reasoning.constraint_score is not None and reasoning.constraint_score < 0.60:
                primary = "CONSTRAINT_FAILURE"
                probable_cause = "Generated answer failed to satisfy one or more compound qualifying conditions."
            elif question.is_multihop and reasoning.multihop_score is not None and reasoning.multihop_score < 0.60:
                primary = "MULTIHOP_INTEGRATION_FAILURE"
                probable_cause = "Evidence passages were retrieved, but synthesis failed to integrate multi-hop entity relations."
            elif factuality.reference_correctness_score < 0.50:
                primary = "GENERATION_FAILURE"
                probable_cause = "Context contained relevant evidence, but final generation missed the specific reference entity/fact."
            else:
                primary = "REASONING_FAILURE"
                probable_cause = "Logical reasoning over retrieved facts deviated from the reference chain."

        # 8. Fallback
        if not primary:
            primary = "UNKNOWN_FAILURE"
            probable_cause = "Discrepancy observed between generated response and benchmark reference."

        # Deduplicate secondaries
        secondaries = [s for s in secondaries if s != primary]

        return FailureDiagnosis(
            question_id=qid,
            is_failure=True,
            primary_failure=primary,
            secondary_failures=secondaries,
            retrieval_evidence_found=evidence_found,
            graph_evidence_found=graph_evidence_found,
            reasoning_failure=reasoning_fail,
            probable_cause=probable_cause,
        )
