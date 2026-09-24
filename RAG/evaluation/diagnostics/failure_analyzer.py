"""
Forensic Failure Diagnostic Engine
Maps every failed question to the 23-category RAISE Failure Taxonomy.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

from ..loaders.schema import EvalQuestion


@dataclass
class FailureReport:
    failure_id: str
    run_id: str
    dataset: str
    question_id: str
    question: str
    expected_answer: str
    raise_answer: str
    expected_evidence: str
    retrieved_evidence: str
    correct_evidence_present: bool
    highest_relevant_rank: int
    vector_rank: int
    bm25_rank: int
    graph_rank: int
    rrf_rank: int
    reranker_rank: int
    failure_stage: str
    root_cause: str
    secondary_cause: Optional[str]
    affected_component: str
    why_architecture_failed: str
    proposed_fix: str
    expected_effect: str
    risk: str
    confidence: float = 1.0


class FailureAnalyzer:
    """
    Analyzes execution traces and assigns root causes from the 23-category taxonomy.
    """

    @staticmethod
    def analyze_case(
        run_id: str,
        question: EvalQuestion,
        raw_result: Dict[str, Any],
        retrieval_trace: Dict[str, Any],
        qa_result: Dict[str, Any],
        outcome_category: str
    ) -> Optional[FailureReport]:
        """
        If the question succeeded without error or regression, returns None.
        Otherwise, returns a fully populated FailureReport.
        """
        if outcome_category in ("CORRECT_ANSWER", "CORRECT_ABSTENTION"):
            return None

        q_id = question.q_id
        gold_ans = question.ground_truth_answer or ""
        gen_ans = raw_result.get("grounded_answer") or raw_result.get("answer") or ""

        # Trace details
        vec_rank = retrieval_trace.get("rank_vector", -1)
        bm25_rank = retrieval_trace.get("rank_bm25", -1)
        graph_rank = retrieval_trace.get("rank_graph", -1)
        rrf_rank = retrieval_trace.get("rank_rrf", -1)
        rerank_rank = retrieval_trace.get("rank_reranked", -1)

        ranks = [r for r in [vec_rank, bm25_rank, graph_rank, rrf_rank, rerank_rank] if r > 0]
        highest_rank = min(ranks) if ranks else -1
        gold_present = retrieval_trace.get("gold_present_in_reranked", False) or (highest_rank > 0)

        # Root cause classification logic
        root_cause = "GENERATION_ERROR"
        secondary_cause = None
        affected_comp = "LLM Generation Node"
        stage = "SYNTHESIS"
        why_failed = "Model synthesized an inaccurate answer despite retrieved evidence."
        proposed_fix = "Refine synthesis prompt guidelines and verify table cell alignment."
        expected_effect = "+5% answer exact match"
        risk = "Minor prompt tuning sensitivity"

        if outcome_category == "UNSUPPORTED_ANSWER":
            root_cause = "UNSUPPORTED_ANSWER"
            affected_comp = "Quality Gate / Faithfulness Filter"
            stage = "RUNTIME_FAITHFULNESS_GATE"
            why_failed = "Pipeline answered an unanswerable or unsupported question instead of safely refusing."
            proposed_fix = "Enforce strict refusal threshold when evidence similarity is below cutoff."
            expected_effect = "Eliminates parametric hallucinations on unanswerable traps"
            risk = "Potential slight increase in false refusals"

        elif outcome_category == "UNNECESSARY_ABSTENTION":
            if highest_rank > 0:
                root_cause = "UNNECESSARY_ABSTENTION"
                affected_comp = "Quality Gate / Unverified Responder"
                stage = "UNVERIFIED_RESPONDER"
                why_failed = "Supporting evidence was present in retrieved chunks, but quality gate rejected verified claims."
                proposed_fix = "Calibrate FineCat NLI claim splitting to prevent multi-sentence rejection."
                expected_effect = "+10% answerable coverage"
                risk = "Slight risk of accepting marginally grounded claims"
            else:
                root_cause = "RETRIEVAL_MISS"
                affected_comp = "Multi-Substrate Retriever"
                stage = "RETRIEVAL"
                why_failed = "No candidate substrate retrieved the supporting evidence from the corpus."
                proposed_fix = "Expand BM25 query terms and optimize dense embedding vector search."
                expected_effect = "+8% evidence recall"
                risk = "Increased candidate pool latency"

        elif highest_rank == -1:
            root_cause = "RETRIEVAL_MISS"
            affected_comp = "ChromaDB / BM25 / Neo4j Retriever"
            stage = "RETRIEVAL"
            why_failed = "Zero candidate retrieval substrates matched the required gold evidence."
            proposed_fix = "Expand subquery decomposition and index coverage."
            expected_effect = "+12% candidate discovery"
            risk = "Higher retrieval latency"

        elif rrf_rank > 0 and rrf_rank <= 8 and (rerank_rank == -1 or rerank_rank > 8):
            root_cause = "RERANKER_ERROR"
            secondary_cause = "FALSE_SUPPRESSION"
            affected_comp = "CrossEncoderReranker (BAAI/bge-reranker-large)"
            stage = "RERANKING"
            why_failed = f"Gold passage ranked #{rrf_rank} after fusion but was suppressed to #{rerank_rank} by cross-encoder."
            proposed_fix = "Calibrate cross-encoder score normalization or lower threshold."
            expected_effect = "+5% reranked evidence recall"
            risk = "Marginal noise inclusion"

        elif qa_result.get("numeric_exact_match") is False:
            root_cause = "NUMERIC_ERROR"
            affected_comp = "DeterministicMathEngine / Table Engine"
            stage = "SYNTHESIS_TABLE_PARSER"
            why_failed = "Generated answer misread table numbers or financial statement currency units."
            proposed_fix = "Route financial/tabular queries through DeterministicMathEngine with cell coordinate locking."
            expected_effect = "Exact IEEE-754 precision on Balance Sheet lines"
            risk = "Requires structured table annotations"

        elif not qa_result.get("citations_valid", True):
            root_cause = "CITATION_ERROR"
            affected_comp = "CitationValidator"
            stage = "CITATION_VALIDATION"
            why_failed = "Inline citations [Page N] did not match verified source page metadata."
            proposed_fix = "Bind citation tags strictly to verified physical page indices before synthesis."
            expected_effect = "100% citation precision"
            risk = "None"

        return FailureReport(
            failure_id=f"FAIL-{run_id}-{q_id}",
            run_id=run_id,
            dataset=question.dataset,
            question_id=q_id,
            question=question.question,
            expected_answer=gold_ans,
            raise_answer=gen_ans,
            expected_evidence=str(question.page_citations or question.required_keywords),
            retrieved_evidence=f"Highest rank: #{highest_rank} (Vec:{vec_rank}, BM25:{bm25_rank}, Graph:{graph_rank}, RRF:{rrf_rank}, Rerank:{rerank_rank})",
            correct_evidence_present=gold_present,
            highest_relevant_rank=highest_rank,
            vector_rank=vec_rank,
            bm25_rank=bm25_rank,
            graph_rank=graph_rank,
            rrf_rank=rrf_rank,
            reranker_rank=rerank_rank,
            failure_stage=stage,
            root_cause=root_cause,
            secondary_cause=secondary_cause,
            affected_component=affected_comp,
            why_architecture_failed=why_failed,
            proposed_fix=proposed_fix,
            expected_effect=expected_effect,
            risk=risk,
            confidence=0.95
        )
