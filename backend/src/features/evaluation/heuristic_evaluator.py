"""
Local Heuristic Evaluator & Development Metric Engine
======================================================
Calculates offline RAGAS-aligned proxy metrics for development testing, regression detection,
and runtime quality enforcement without external API dependencies.

Architectural Role & Metric Formulas:
--------------------------------------
1. Faithfulness (f_score):
   - Fraction of atomic claims extracted from the answer that are strictly supported by evidence
     (Tier 1 math, Tier 2 lexical, Tier 3 NLI, or Tier 4 soft containment).
   - f_score = supported_claims / total_claims

2. Answer Relevance (rel_score):
   - Overlap ratio between non-stopword tokens in the user query and the generated answer,
     boosted by base coverage: min(1.0, (token_overlap / query_tokens) + 0.30).

3. Context Precision (prec_score):
   - Evaluates whether the most relevant evidence chunks were ranked near the top.
   - Mean reciprocal rank / precision at rank k across retrieved contexts.

4. Context Recall (rec_score):
   - If ground-truth facts are supplied, measures what fraction were successfully retrieved
     into the joined evidence context.

5. Domain Guardrails:
   - Startup / Venture Completeness Guardrail: If user explicitly queries deep-tech startups
     or ventures, requires at least 2 distinct named entities or flags incomplete recall.
   - Anti-Fabrication Boundary Guardrail: Detects and rejects fabricated section headings
     or non-existent document partitions (e.g., "Section 14 and Section 21 records").

6. Overall Composite Score:
   - overall = (f_score * 0.40) + (rel_score * 0.30) + (prec_score * 0.15) + (rec_score * 0.15)

How to Update or Tune:
----------------------
- To change dimension weights, adjust coefficients in line 103 `overall = ...`.
- To tune the startup entity threshold, adjust `len(ventures_found) < 2`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .models import StructuredEvidence, EvaluationReport
from .claim_verifier import ClaimLevelVerifier
from .citation_verifier import CitationValidator


class LocalHeuristicEvaluator:
    """
    Local heuristic benchmarking evaluator clearly distinguished from cloud RAGAS.
    Calculates offline RAGAS-aligned proxy metrics for development testing.
    """

    @classmethod
    def evaluate(
        cls,
        query: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        graph_facts: Optional[List[Dict[str, Any]]] = None,
        ground_truth_facts: Optional[List[str]] = None,
        citations_list: Optional[List[Dict[str, Any]]] = None,
        active_docs: Optional[List[str]] = None,
        math_facts: Optional[List[str]] = None,
        threshold: float = 0.80,
    ) -> EvaluationReport:
        """
        Calculates multidimensional evaluation metrics across faithfulness, relevance,
        precision, recall, and domain completeness guardrails.
        """
        evidence = StructuredEvidence(
            vector_chunks=retrieved_chunks,
            graph_facts=graph_facts or [],
            active_docs=active_docs or [],
            math_facts=math_facts or [],
        )

        claims_res, f_score, num_mismatches, _ = ClaimLevelVerifier.verify_claims(
            answer=answer,
            evidence=evidence,
            citations_list=citations_list,
            query=query,
        )

        # Validate Citations
        cit_valid, cit_issues, _ = CitationValidator.validate_citations(
            answer=answer,
            citations_list=citations_list or [],
            active_docs=active_docs,
        )
        cit_errors = len(cit_issues)

        # Answer Relevance
        q_words = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", query.lower()))
        q_words = {w for w in q_words if w not in {"what", "who", "where", "how", "many", "tell", "show", "give"}}
        a_lower = answer.lower()
        rel_overlap = sum(1 for w in q_words if w in a_lower) if q_words else 1
        rel_score = round(min(1.0, (rel_overlap / max(len(q_words), 1)) + 0.30), 4)

        # Context Precision
        contexts = [str(c.get("plain_text") or c.get("text") or "") for c in retrieved_chunks]
        relevant_positions = []
        for idx, ctx in enumerate(contexts, start=1):
            ctx_lower = ctx.lower()
            if q_words and any(w in ctx_lower for w in q_words):
                relevant_positions.append(idx)
        prec_score = round(sum(i / rank for i, rank in enumerate(relevant_positions, 1)) / max(len(relevant_positions), 1), 4) if relevant_positions else 0.50

        # Context Recall
        joined_evidence = evidence.get_full_text().lower()
        recalled = 0
        if ground_truth_facts:
            for fact in ground_truth_facts:
                f_words = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", fact.lower()))
                if f_words and sum(1 for w in f_words if w in joined_evidence) / len(f_words) >= 0.5:
                    recalled += 1
            rec_score = round(recalled / len(ground_truth_facts), 4)
        else:
            rec_score = 1.0

        # Startup / Entity Completeness Guardrail
        # If user asks for "startups" (plural) or "deep-tech startups", require named startup profiles
        q_lower = query.lower()
        is_startup_query = any(k in q_lower for k in ["startups", "ventures", "spin-offs", "deep-tech startups", "companies incubated"])
        completeness_failed = False
        completeness_msg = ""
        if is_startup_query:
            named_ventures = re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\b", answer)
            stop_entities = {"IITM", "IIT", "Madras", "Research", "Park", "Incubation", "Cell", "IITMIC", "Based", "Section", "References", "Doc", "Page"}
            ventures_found = {v for v in named_ventures if v not in stop_entities and len(v) > 3}
            has_confession_or_excuse = any(w in answer.lower() for w in ["does not provide specific details on the names", "no specific startup", "does not name"])
            if has_confession_or_excuse or len(ventures_found) < 2:
                completeness_failed = True
                completeness_msg = "Recall/Completeness check failed: Query requested deep-tech startups but answer contained fewer than 2 specific named startup profiles."

        # Anti-Fabrication Boundary Guardrail
        # Check if model fabricated fictional document sections or boundaries (e.g. "Section 14 and Section 21 records")
        fabricated_boundary_match = re.search(r"\b(section\s+\d+\s+(?:and|&)\s+section\s+\d+\s+records?|document\s+boundaries?)\b", answer, re.IGNORECASE)
        fabricated_boundary_found = False
        if fabricated_boundary_match:
            phrase = fabricated_boundary_match.group(0).lower()
            if phrase not in joined_evidence:
                fabricated_boundary_found = True

        overall = round((f_score * 0.4) + (rel_score * 0.3) + (prec_score * 0.15) + (rec_score * 0.15), 4)
        max_allowed_num_mismatches = 1 if len(claims_res) >= 10 else 0
        is_acceptable = (
            f_score >= threshold
            and num_mismatches <= max_allowed_num_mismatches
            and cit_valid
            and not completeness_failed
            and not fabricated_boundary_found
        )

        reason = None
        if not is_acceptable:
            reasons = []
            if f_score < threshold:
                reasons.append(f"Faithfulness {f_score:.2f} < {threshold:.2f}")
            if num_mismatches > max_allowed_num_mismatches:
                reasons.append(f"{num_mismatches} numerical mismatch(es)")
            if not cit_valid:
                reasons.append(f"Citation validation errors: {', '.join(cit_issues)}")
            if completeness_failed:
                reasons.append(completeness_msg)
            if fabricated_boundary_found:
                reasons.append("Anti-fabrication violation: Model fabricated non-existent document/section boundaries.")
            reason = "; ".join(reasons)

        return EvaluationReport(
            evaluator_type="LocalHeuristicEvaluator",
            faithfulness=f_score,
            answer_relevance=rel_score,
            context_precision=prec_score,
            context_recall=rec_score,
            overall_score=overall,
            supported_claims_count=sum(1 for c in claims_res if c.is_supported),
            total_claims_count=len(claims_res),
            numerical_mismatches=num_mismatches,
            citation_errors=cit_errors,
            is_acceptable=is_acceptable,
            rejection_reason=reason,
            claims=claims_res,
        )
