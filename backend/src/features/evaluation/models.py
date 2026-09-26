"""
RAISE Evaluation Data Models & Evidence Schemas
================================================
Defines standardized data containers for factual claim verification, evidence representation,
and evaluation reporting across the RAISE GraphRAG architecture.

Architectural Role:
-------------------
1. `VerificationPath`: Enum tracking the decision route taken for each claim:
   - DETERMINISTIC: Exact numeric, date, or direct lexical matches.
   - NLI: FineCat-NLI neural entailment verification.
   - DETERMINISTIC+NLI: Hybrid verification (lexical match confirmed by NLI).
   - EVIDENCE_EXPANSION+NLI: Multi-hop graph/chunk traversal before NLI.
   - CONTROLLED_ABSTENTION: Explicit refusal when facts cannot be verified.

2. `StructuredEvidence`: Aggregates retrieved vector chunks, Neo4j graph facts,
   mathematical derivations, and active document scopes into a single verifiable context.

3. `ClaimVerificationResult` (alias: `ClaimVerificationRecord`):
   Granular audit record for a single atomic claim, including numbers verified,
   citation index mappings, NLI logits/probabilities, and verification status.

4. `EvaluationReport`:
   Consolidated scoring report returning RAGAS-aligned metrics:
   - faithfulness (supported claims / total claims)
   - answer_relevance (query-answer semantic overlap)
   - context_precision (ranking quality of retrieved evidence)
   - context_recall (coverage of ground-truth evidence)
   - overall_score (weighted synthesis of all dimensions)

How to Extend or Update:
------------------------
- To add a new verification status, append to the `status` documentation in `ClaimVerificationResult`.
- To modify serialization for frontend telemetry, update `EvaluationReport.to_dict()`.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


class VerificationPath(str, Enum):
    """
    Categorizes the verification mechanism executed for an individual factual claim.
    """
    DETERMINISTIC = "DETERMINISTIC"                     # Tier 1 Math / Numeric / Exact Date match
    NLI = "NLI"                                         # Direct Tier 3 Neural FineCat-NLI verification
    DETERMINISTIC_PLUS_NLI = "DETERMINISTIC+NLI"        # Lexical/heuristic match confirmed via NLI
    EVIDENCE_EXPANSION_PLUS_NLI = "EVIDENCE_EXPANSION+NLI" # Required multi-hop graph/chunk expansion before NLI
    CONTROLLED_ABSTENTION = "CONTROLLED_ABSTENTION"     # Safe abstention when evidence chain is incomplete


@dataclass
class StructuredEvidence:
    """
    Consolidated evidence container incorporating vector passages, Neo4j graph facts,
    mathematical derivations, and document filters into a unified verifiable substrate.
    """
    vector_chunks: List[Dict[str, Any]] = field(default_factory=list)
    graph_facts: List[Dict[str, Any]] = field(default_factory=list)
    source_documents: List[str] = field(default_factory=list)
    active_docs: List[str] = field(default_factory=list)
    math_facts: List[str] = field(default_factory=list)

    def get_full_text(self) -> str:
        """
        Concatenates all evidence sources into a single plain-text string for lexical
        and numeric cross-referencing.
        """
        texts = []
        for c in self.vector_chunks:
            texts.append(str(c.get("plain_text") or c.get("text") or ""))
        for g in self.graph_facts:
            texts.append(str(g.get("fact") or g.get("raw_value") or str(g)))
        for m in self.math_facts:
            texts.append(str(m))
        for d in self.active_docs:
            texts.append(str(d))
        for s in self.source_documents:
            texts.append(str(s))
        return "\n".join(texts)


@dataclass
class ClaimVerificationResult:
    """
    Granular verification record for an individual atomic claim extracted from the LLM answer.
    """
    claim_id: str
    text: str
    is_supported: bool
    status: str  # "SUPPORTED", "DIRECT", "NLI_ENTAILED", "CONTRADICTION", "NUMERICAL_MISMATCH", "UNSUPPORTED", "CITATION_INVALID"
    extracted_numbers: List[str]
    matched_numbers: List[str]
    citations_found: List[int]
    notes: List[str] = field(default_factory=list)
    nli_entailment_prob: Optional[float] = None
    nli_contradiction_prob: Optional[float] = None
    retrieval_relevance_score: Optional[float] = None
    verification_tier: str = "TIER2_LEXICAL"  # "TIER1_NUMERIC", "TIER2_LEXICAL", "TIER3_NLI", "TIER4_FALLBACK"
    bound_chunk_id: Optional[str] = None
    primary_page: Optional[int] = None
    verification_path: str = "DETERMINISTIC"
    decision_reason: str = ""
    raw_logits: Optional[Dict[str, float]] = None
    softmax_probs: Optional[Dict[str, float]] = None
    calibration_status: str = "UNVALIDATED_RAW_SOFTMAX"
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to standard Python dictionary."""
        return asdict(self)


# Canonical alias ensuring single source of truth across claim audit, quality gate, and telemetry
ClaimVerificationRecord = ClaimVerificationResult


@dataclass
class EvaluationReport:
    """
    Consolidated evaluation report summarizing quality metrics, claim statistics,
    and gating acceptance decisions for an answered query.
    """
    evaluator_type: str  # "LocalHeuristicEvaluator" / "RuntimeQualityGate"
    faithfulness: float
    answer_relevance: float
    context_precision: float
    context_recall: float
    overall_score: float
    supported_claims_count: int
    total_claims_count: int
    numerical_mismatches: int
    citation_errors: int
    is_acceptable: bool
    rejection_reason: Optional[str] = None
    claims: List[ClaimVerificationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes evaluation report into structured format compatible with REST API telemetry,
        benchmark suites, and frontend dashboards.
        """
        num_claims_with_numbers = 0
        num_claims_verified = 0
        for c in self.claims:
            if c.extracted_numbers or c.matched_numbers:
                num_claims_with_numbers += 1
                if c.is_supported and c.status != "NUMERICAL_MISMATCH":
                    num_claims_verified += 1

        unsupported_count = max(0, self.total_claims_count - self.supported_claims_count)
        evidence_overlap = round(self.context_precision * 100.0, 1)
        factual_overlap = round((self.supported_claims_count / max(self.total_claims_count, 1)) * 100.0, 1)

        return {
            "evaluator_type": self.evaluator_type,
            "faithfulness": self.faithfulness,
            "faithfulness_score": self.faithfulness,
            "answer_relevance": self.answer_relevance,
            "context_precision": self.context_precision,
            "context_recall": self.context_recall,
            "overall_score": self.overall_score,
            "supported_claims_count": self.supported_claims_count,
            "total_claims_count": self.total_claims_count,
            "unsupported_claims_count": unsupported_count,
            "numerical_mismatches": self.numerical_mismatches,
            "numerical_claims_total": num_claims_with_numbers,
            "numerical_claims_verified": num_claims_verified,
            "evidence_overlap_pct": evidence_overlap,
            "factual_overlap_pct": factual_overlap,
            "citation_errors": self.citation_errors,
            "is_acceptable": self.is_acceptable,
            "rejection_reason": self.rejection_reason,
            "claims": [c.to_dict() for c in self.claims],
        }
