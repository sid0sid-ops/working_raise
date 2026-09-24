"""
RAISE Telemetry Models & Data Specifications
=============================================
Provides decoupled, typed data structures for pipeline observability:
1. MetricState enum (MEASURED, DERIVED, ESTIMATED, UNAVAILABLE, NOT_APPLICABLE)
2. MetricValue container ensuring zero silent fake-number synthesis
3. TelemetryFrame container used across CLI, API, Frontend, and JSON Export
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


class MetricState(str, Enum):
    """
    Forensic classification of telemetry data provenance.
    Ensures developer consoles never silently replace missing measurements
    with realistic-looking numbers.
    """
    MEASURED = "MEASURED"          # Directly queried / recorded by database, engine, or timer
    DERIVED = "DERIVED"            # Mathematically computed from measured raw inputs
    ESTIMATED = "ESTIMATED"        # Deterministic approximation (e.g. word-split tokens)
    UNAVAILABLE = "UNAVAILABLE"    # Metric was not recorded or unsupported by the current backend
    NOT_APPLICABLE = "NOT_APPLICABLE"  # Skipped because the execution path bypassed this component
    NOT_RUN = "NOT_RUN"            # Check was scheduled/applicable but skipped/deferred
    FAILED = "FAILED"              # Metric computation or check threw an unhandled exception


@dataclass
class MetricValue(Generic[T]):
    """Container holding a metric value alongside its verifiable provenance state."""
    value: Optional[T] = None
    state: MetricState = MetricState.UNAVAILABLE
    unit: str = ""
    notes: Optional[str] = None

    def __post_init__(self):
        # Strict Invariant: non-value states must never hold a value
        if self.state in (MetricState.UNAVAILABLE, MetricState.NOT_APPLICABLE, MetricState.NOT_RUN, MetricState.FAILED):
            self.value = None
        # Strict Invariant: value states with None automatically normalize to UNAVAILABLE
        elif self.state in (MetricState.MEASURED, MetricState.DERIVED, MetricState.ESTIMATED) and self.value is None:
            self.state = MetricState.UNAVAILABLE

    @classmethod
    def measured(cls, val: T, unit: str = "", notes: Optional[str] = None) -> MetricValue[T]:
        return cls(value=val, state=MetricState.MEASURED, unit=unit, notes=notes)

    @classmethod
    def derived(cls, val: T, unit: str = "", notes: Optional[str] = None) -> MetricValue[T]:
        return cls(value=val, state=MetricState.DERIVED, unit=unit, notes=notes)

    @classmethod
    def estimated(cls, val: T, unit: str = "", notes: Optional[str] = None) -> MetricValue[T]:
        return cls(value=val, state=MetricState.ESTIMATED, unit=unit, notes=notes)

    @classmethod
    def unavailable(cls, unit: str = "", notes: Optional[str] = None) -> MetricValue[T]:
        return cls(value=None, state=MetricState.UNAVAILABLE, unit=unit, notes=notes)

    @classmethod
    def not_applicable(cls, unit: str = "", notes: Optional[str] = None) -> MetricValue[T]:
        return cls(value=None, state=MetricState.NOT_APPLICABLE, unit=unit, notes=notes)

    @classmethod
    def not_run(cls, unit: str = "", notes: Optional[str] = None) -> MetricValue[T]:
        return cls(value=None, state=MetricState.NOT_RUN, unit=unit, notes=notes)

    @classmethod
    def failed(cls, unit: str = "", notes: Optional[str] = None) -> MetricValue[T]:
        return cls(value=None, state=MetricState.FAILED, unit=unit, notes=notes)

    @property
    def is_available(self) -> bool:
        return self.state in (MetricState.MEASURED, MetricState.DERIVED, MetricState.ESTIMATED) and self.value is not None

    def display(self, format_spec: str = "") -> str:
        """Formatted string representation with provenance indicator."""
        if not self.is_available:
            return f"-- [{self.state.value}]"
        if format_spec and isinstance(self.value, (int, float)):
            val_str = f"{self.value:{format_spec}}"
        else:
            val_str = str(self.value)
        unit_str = f" {self.unit}" if self.unit else ""
        if self.state == MetricState.MEASURED:
            return f"{val_str}{unit_str}"
        return f"{val_str}{unit_str} [{self.state.value}]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "state": self.state.value,
            "unit": self.unit,
            "notes": self.notes,
        }


class FailureClassification(str, Enum):
    NONE_PASS = "NONE (PASS)"
    INTENT_ROUTING_FAILURE = "INTENT_ROUTING_FAILURE"
    QUERY_REWRITE_FAILURE = "QUERY_REWRITE_FAILURE"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    RERANKING_FAILURE = "RERANKING_FAILURE"
    CONTEXT_ASSEMBLY_FAILURE = "CONTEXT_ASSEMBLY_FAILURE"
    GENERATION_FAILURE = "GENERATION_FAILURE"
    CITATION_FAILURE = "CITATION_FAILURE"
    GRAPH_FAILURE = "GRAPH_FAILURE"
    DATA_PROVENANCE_FAILURE = "DATA_PROVENANCE_FAILURE"
    QUALITY_GATE_FAILURE = "QUALITY_GATE_FAILURE"
    ZERO_EVIDENCE_REFUSAL = "ZERO_EVIDENCE_REFUSAL"
    ERR_OCR_NOISE = "ERR_OCR_NOISE"
    ERR_RETRIEVAL_MISS = "ERR_RETRIEVAL_MISS"
    ERR_RERANK_DROPOUT = "ERR_RERANK_DROPOUT"
    ERR_LLM_HALLUCINATION = "ERR_LLM_HALLUCINATION"
    ERR_GATE_OVERBLOCK = "ERR_GATE_OVERBLOCK"
    ERR_UNANSWERABLE_CORRECT = "ERR_UNANSWERABLE_CORRECT"



@dataclass
class IntentMetrics:
    intent: MetricValue[str] = field(default_factory=MetricValue.unavailable)
    confidence: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    query_type: MetricValue[str] = field(default_factory=MetricValue.unavailable)
    complexity: MetricValue[str] = field(default_factory=MetricValue.unavailable)
    coreference_resolved: MetricValue[str] = field(default_factory=MetricValue.unavailable)
    subqueries: List[str] = field(default_factory=list)
    routing_decision: MetricValue[str] = field(default_factory=MetricValue.unavailable)
    latency_ms: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    domain: str = "ACADEMIC / INSTITUTIONAL REPORT"
    routing_explanation: str = ""
    intent_rule_fired: str = "academic_research_firewall_v2"
    competing_intents: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "confidence": self.confidence.to_dict(),
            "query_type": self.query_type.to_dict(),
            "complexity": self.complexity.to_dict(),
            "coreference_resolved": self.coreference_resolved.to_dict(),
            "subqueries": self.subqueries,
            "routing_decision": self.routing_decision.to_dict(),
            "latency_ms": self.latency_ms.to_dict(),
            "domain": self.domain,
            "routing_explanation": self.routing_explanation,
            "intent_rule_fired": self.intent_rule_fired,
            "competing_intents": self.competing_intents,
        }


@dataclass
class VectorRetrievalMetrics:
    model: str = "BAAI/bge-large-en-v1.5"
    collection: str = "raise_graphrag_chunks"
    candidates: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    top_k: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    distance_min: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    distance_max: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    latency_ms: MetricValue[float] = field(default_factory=MetricValue.unavailable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "collection": self.collection,
            "candidates": self.candidates.to_dict(),
            "top_k": self.top_k.to_dict(),
            "distance_min": self.distance_min.to_dict(),
            "distance_max": self.distance_max.to_dict(),
            "latency_ms": self.latency_ms.to_dict(),
        }


@dataclass
class BM25RetrievalMetrics:
    candidates: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    exact_matches: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    latency_ms: MetricValue[float] = field(default_factory=MetricValue.unavailable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidates": self.candidates.to_dict(),
            "exact_matches": self.exact_matches.to_dict(),
            "latency_ms": self.latency_ms.to_dict(),
        }


@dataclass
class GraphRetrievalMetrics:
    entry_entities: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    nodes_visited: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    edges_traversed: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    max_hops: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    cypher_query: MetricValue[str] = field(default_factory=MetricValue.unavailable)
    latency_ms: MetricValue[float] = field(default_factory=MetricValue.unavailable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_entities": self.entry_entities.to_dict(),
            "nodes_visited": self.nodes_visited.to_dict(),
            "edges_traversed": self.edges_traversed.to_dict(),
            "max_hops": self.max_hops.to_dict(),
            "cypher_query": self.cypher_query.to_dict(),
            "latency_ms": self.latency_ms.to_dict(),
        }


@dataclass
class RerankMetrics:
    input_candidates: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    output_evidence: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    mean_score: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    score_improvement_pct: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    latency_ms: MetricValue[float] = field(default_factory=MetricValue.unavailable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_candidates": self.input_candidates.to_dict(),
            "output_evidence": self.output_evidence.to_dict(),
            "mean_score": self.mean_score.to_dict(),
            "score_improvement_pct": self.score_improvement_pct.to_dict(),
            "latency_ms": self.latency_ms.to_dict(),
        }


@dataclass
class CandidateAuditItem:
    rank: int
    chunk_id: str
    score: float
    retriever: str  # "VECTOR", "BM25", "GRAPH", "HYBRID"
    primary_page: int
    heading: str = ""
    semantic_similarity: Optional[float] = None
    bm25_score: Optional[float] = None
    entity_overlap: Optional[float] = None
    numeric_overlap: Optional[float] = None
    graph_distance: Optional[int] = None
    contains_expected_entity: Optional[bool] = None
    reranker_dropout: bool = False
    text_snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "chunk_id": self.chunk_id,
            "score": self.score,
            "retriever": self.retriever,
            "primary_page": self.primary_page,
            "heading": self.heading,
            "semantic_similarity": self.semantic_similarity,
            "bm25_score": self.bm25_score,
            "entity_overlap": self.entity_overlap,
            "numeric_overlap": self.numeric_overlap,
            "graph_distance": self.graph_distance,
            "contains_expected_entity": self.contains_expected_entity,
            "reranker_dropout": self.reranker_dropout,
            "text_snippet": self.text_snippet,
        }



@dataclass
class RetrievalMetrics:
    vector: VectorRetrievalMetrics = field(default_factory=VectorRetrievalMetrics)
    bm25: BM25RetrievalMetrics = field(default_factory=BM25RetrievalMetrics)
    graph: GraphRetrievalMetrics = field(default_factory=GraphRetrievalMetrics)
    rerank: RerankMetrics = field(default_factory=RerankMetrics)
    total_retrieval_ms: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    retrievers_enabled: Dict[str, bool] = field(default_factory=lambda: {"Vector": True, "BM25": True, "Graph": False})
    candidates_merged: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    candidates_deduplicated: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    top_candidates_audit: List[CandidateAuditItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vector": self.vector.to_dict(),
            "bm25": self.bm25.to_dict(),
            "graph": self.graph.to_dict(),
            "rerank": self.rerank.to_dict(),
            "total_retrieval_ms": self.total_retrieval_ms.to_dict(),
            "retrievers_enabled": self.retrievers_enabled,
            "candidates_merged": self.candidates_merged.to_dict(),
            "candidates_deduplicated": self.candidates_deduplicated.to_dict(),
            "top_candidates_audit": [c.to_dict() for c in self.top_candidates_audit],
        }


@dataclass
class ContextAssemblyMetrics:
    chunks_in_context: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    unique_documents: int = 1
    unique_pages: int = 1
    context_tokens: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    max_context_tokens: int = 8192
    context_utilization_pct: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    chunks_dropped: int = 0
    context_order: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunks_in_context": self.chunks_in_context.to_dict(),
            "unique_documents": self.unique_documents,
            "unique_pages": self.unique_pages,
            "context_tokens": self.context_tokens.to_dict(),
            "max_context_tokens": self.max_context_tokens,
            "context_utilization_pct": self.context_utilization_pct.to_dict(),
            "chunks_dropped": self.chunks_dropped,
            "context_order": self.context_order,
        }


@dataclass
class PromptContextTelemetry:
    packed_chunk_ids: List[str] = field(default_factory=list)
    prompt_context_tokens: int = 0
    context_snippets: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packed_chunk_ids": self.packed_chunk_ids,
            "prompt_context_tokens": self.prompt_context_tokens,
            "context_snippets": self.context_snippets,
        }


@dataclass
class ClaimEvidenceAuditItem:

    claim_id: str
    text: str
    evidence_chunk_id: Optional[str] = None
    primary_page: Optional[int] = None
    support_status: str = "DIRECT"  # "DIRECT", "NLI_ENTAILED", "CONTRADICTION", "RELATED", "UNSUPPORTED", "NUMERICAL_MISMATCH"
    confidence: float = 1.0
    notes: str = ""
    nli_entailment_prob: Optional[float] = None
    nli_contradiction_prob: Optional[float] = None
    retrieval_relevance_score: Optional[float] = None
    verification_tier: str = "TIER2_LEXICAL"  # "TIER1_NUMERIC", "TIER2_LEXICAL", "TIER3_NLI", "TIER4_FALLBACK"
    verification_path: str = "DETERMINISTIC"
    decision_reason: str = ""
    raw_logits: Optional[Dict[str, float]] = None
    softmax_probs: Optional[Dict[str, float]] = None
    calibration_status: str = "UNVALIDATED_RAW_SOFTMAX"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "evidence_chunk_id": self.evidence_chunk_id,
            "primary_page": self.primary_page,
            "support_status": self.support_status,
            "confidence": self.confidence,
            "notes": self.notes,
            "nli_entailment_prob": self.nli_entailment_prob,
            "nli_contradiction_prob": self.nli_contradiction_prob,
            "retrieval_relevance_score": self.retrieval_relevance_score,
            "verification_tier": self.verification_tier,
            "verification_path": self.verification_path,
            "decision_reason": self.decision_reason,
            "raw_logits": self.raw_logits,
            "softmax_probs": self.softmax_probs,
            "calibration_status": self.calibration_status,
        }


@dataclass
class NumericalAuditItem:
    detected_metrics: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)  # e.g. "218 + 175 = 393 acres"
    arithmetic_status: str = "PASS"  # "PASS" | "MISMATCH" | "N/A"
    numeric_consistency: str = "PASS"
    tolerance: str = "±0.0"
    source_page: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected_metrics": self.detected_metrics,
            "relationships": self.relationships,
            "arithmetic_status": self.arithmetic_status,
            "numeric_consistency": self.numeric_consistency,
            "tolerance": self.tolerance,
            "source_page": self.source_page,
        }


@dataclass
class NumericalDiffItem:
    metric_name: str
    ground_truth_value: Optional[str] = None
    pipeline_value: Optional[str] = None
    source_page_expected: Optional[int] = None
    source_page_retrieved: Optional[int] = None
    status: str = "PASS"  # "PASS" | "MISMATCH" | "MISSING_IN_ANSWER" | "UNGROUNDED_IN_CONTEXT"
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "ground_truth_value": self.ground_truth_value,
            "pipeline_value": self.pipeline_value,
            "source_page_expected": self.source_page_expected,
            "source_page_retrieved": self.source_page_retrieved,
            "status": self.status,
            "details": self.details,
        }


@dataclass
class CitationAuditItem:

    sentence_index: int
    sentence_snippet: str
    cited_indices: List[int]
    resolved_pages: List[int]
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sentence_index": self.sentence_index,
            "sentence_snippet": self.sentence_snippet,
            "cited_indices": self.cited_indices,
            "resolved_pages": self.resolved_pages,
            "is_valid": self.is_valid,
        }
@dataclass
class SynthesisMetrics:
    provider: str = "vLLM (Local TensorRT/PagedAttention)"
    model: str = "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4"
    context_chunks: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    context_tokens: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    output_tokens: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    generation_speed_tok_s: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    time_to_first_token_ms: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    temperature: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    grounding_mode: str = "STRICT (Anti-Hallucination Enabled)"
    citation_contract: str = "NUMERIC BRACKETS ONLY [1..N]"
    latency_ms: MetricValue[float] = field(default_factory=MetricValue.unavailable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "context_chunks": self.context_chunks.to_dict(),
            "context_tokens": self.context_tokens.to_dict(),
            "output_tokens": self.output_tokens.to_dict(),
            "generation_speed_tok_s": self.generation_speed_tok_s.to_dict(),
            "time_to_first_token_ms": self.time_to_first_token_ms.to_dict(),
            "temperature": self.temperature.to_dict(),
            "grounding_mode": self.grounding_mode,
            "citation_contract": self.citation_contract,
            "latency_ms": self.latency_ms.to_dict(),
        }


@dataclass
class QualityMetrics:
    evidence_overlap_pct: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    numerical_claims_verified: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    numerical_claims_total: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    citation_binding_pct: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    source_coverage_actual: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    source_coverage_total: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    faithfulness_score: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    unsupported_claims_count: MetricValue[int] = field(default_factory=MetricValue.unavailable)
    decision: str = "accept"
    is_gate_passed: bool = True
    rejection_reason: Optional[str] = None
    latency_ms: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    claims_audit: List[ClaimEvidenceAuditItem] = field(default_factory=list)
    unsupported_claims: List[str] = field(default_factory=list)
    numerical_audit: Optional[NumericalAuditItem] = None
    citation_audit: List[CitationAuditItem] = field(default_factory=list)
    citation_precision_pct: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    citation_recall_pct: MetricValue[float] = field(default_factory=MetricValue.unavailable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_overlap_pct": self.evidence_overlap_pct.to_dict(),
            "numerical_claims_verified": self.numerical_claims_verified.to_dict(),
            "numerical_claims_total": self.numerical_claims_total.to_dict(),
            "citation_binding_pct": self.citation_binding_pct.to_dict(),
            "source_coverage_actual": self.source_coverage_actual.to_dict(),
            "source_coverage_total": self.source_coverage_total.to_dict(),
            "faithfulness_score": self.faithfulness_score.to_dict(),
            "unsupported_claims_count": self.unsupported_claims_count.to_dict(),
            "decision": self.decision,
            "is_gate_passed": self.is_gate_passed,
            "rejection_reason": self.rejection_reason,
            "latency_ms": self.latency_ms.to_dict(),
            "claims_audit": [c.to_dict() for c in self.claims_audit],
            "unsupported_claims": self.unsupported_claims,
            "numerical_audit": self.numerical_audit.to_dict() if self.numerical_audit else None,
            "citation_audit": [c.to_dict() for c in self.citation_audit],
            "citation_precision_pct": self.citation_precision_pct.to_dict(),
            "citation_recall_pct": self.citation_recall_pct.to_dict(),
        }


@dataclass
class ProvenanceItem:
    citation_index: int
    document: str
    primary_page: int
    printed_page: Optional[str] = None
    section_heading: str = ""
    chunk_id: str = ""
    evidence_score: MetricValue[float] = field(default_factory=MetricValue.unavailable)
    excerpt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citation_index": self.citation_index,
            "document": self.document,
            "primary_page": self.primary_page,
            "printed_page": self.printed_page,
            "section_heading": self.section_heading,
            "chunk_id": self.chunk_id,
            "evidence_score": self.evidence_score.to_dict(),
            "excerpt": self.excerpt,
        }


@dataclass
class ProvenanceData:
    citations: List[ProvenanceItem] = field(default_factory=list)
    unique_documents: List[str] = field(default_factory=list)
    unique_sections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citations": [c.to_dict() for c in self.citations],
            "unique_documents": self.unique_documents,
            "unique_sections": self.unique_sections,
        }


@dataclass
class PerformanceMetrics:
    routing_ms: float = 0.0
    retrieval_ms: float = 0.0
    synthesis_ms: float = 0.0
    quality_gate_ms: float = 0.0
    total_latency_ms: float = 0.0
    unattributed_latency_ms: float = 0.0
    instrumentation_coverage_pct: float = 100.0
    bottleneck_stage: str = "Synthesis"
    bottleneck_pct: float = 0.0
    stage_percentages: Dict[str, float] = field(default_factory=dict)
    breakdown_tree: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "routing_ms": self.routing_ms,
            "retrieval_ms": self.retrieval_ms,
            "synthesis_ms": self.synthesis_ms,
            "quality_gate_ms": self.quality_gate_ms,
            "total_latency_ms": self.total_latency_ms,
            "unattributed_latency_ms": self.unattributed_latency_ms,
            "instrumentation_coverage_pct": self.instrumentation_coverage_pct,
            "bottleneck_stage": self.bottleneck_stage,
            "bottleneck_pct": self.bottleneck_pct,
            "stage_percentages": self.stage_percentages,
            "breakdown_tree": self.breakdown_tree,
        }


@dataclass
class DebugSummary:
    status: str = "PASS"  # "PASS" | "WARNING" | "BLOCKED" | "FAILED"
    failure_class: FailureClassification = FailureClassification.NONE_PASS
    expected_intent: str = "RESEARCH_FACTUAL"
    actual_intent: str = "ACADEMIC_RESEARCH"
    root_cause: str = "All pipeline stages satisfied grounding and quality thresholds."
    fix_priority: str = "NONE"  # "NONE", "P0", "P1", "P2", "P3"
    reproducible: bool = True
    request_id: str = ""
    pipeline_version: str = "v3.1-Forensic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "failure_class": self.failure_class.value if hasattr(self.failure_class, "value") else str(self.failure_class),
            "expected_intent": self.expected_intent,
            "actual_intent": self.actual_intent,
            "root_cause": self.root_cause,
            "fix_priority": self.fix_priority,
            "reproducible": self.reproducible,
            "request_id": self.request_id,
            "pipeline_version": self.pipeline_version,
        }


@dataclass
class HopEvidenceItem:
    hop_id: int
    sub_goal: str = ""
    source_entity: str = ""
    relation: str = ""
    target_entity: str = ""
    supporting_chunks: List[str] = field(default_factory=list)
    graph_path: List[Dict[str, str]] = field(default_factory=list)
    temporal_constraints: List[str] = field(default_factory=list)
    confidence: float = 1.0
    status: str = "VERIFIED"  # "VERIFIED", "MISSING", "AMBIGUOUS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hop_id": self.hop_id,
            "sub_goal": self.sub_goal,
            "source_entity": self.source_entity,
            "relation": self.relation,
            "target_entity": self.target_entity,
            "supporting_chunks": self.supporting_chunks,
            "graph_path": self.graph_path,
            "temporal_constraints": self.temporal_constraints,
            "confidence": self.confidence,
            "status": self.status,
        }


@dataclass
class TelemetryFrame:
    """
    Consolidated, decoupled Telemetry Frame holding all verified observability metrics.
    Safe for consumption by CLI Renderers, FastAPI Endpoints, and JSON Exporters.
    """
    turn_id: str
    session_id: str
    timestamp: str
    query: str
    scope: str
    mode: str
    answer: str

    intent: IntentMetrics = field(default_factory=IntentMetrics)
    retrieval: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    context_assembly: ContextAssemblyMetrics = field(default_factory=ContextAssemblyMetrics)
    synthesis: SynthesisMetrics = field(default_factory=SynthesisMetrics)
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    provenance: ProvenanceData = field(default_factory=ProvenanceData)
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    debug_summary: DebugSummary = field(default_factory=DebugSummary)
    prompt_context: Optional[PromptContextTelemetry] = None
    candidate_audit: List[CandidateAuditItem] = field(default_factory=list)
    numerical_diffs: List[NumericalDiffItem] = field(default_factory=list)
    hop_evidence_chain: List[HopEvidenceItem] = field(default_factory=list)
    chain_completeness_gate: Dict[str, Any] = field(default_factory=dict)

    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "query": self.query,
            "scope": self.scope,
            "mode": self.mode,
            "answer": self.answer,
            "intent": self.intent.to_dict(),
            "retrieval": self.retrieval.to_dict(),
            "context_assembly": self.context_assembly.to_dict(),
            "synthesis": self.synthesis.to_dict(),
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "performance": self.performance.to_dict(),
            "debug_summary": self.debug_summary.to_dict(),
            "prompt_context": self.prompt_context.to_dict() if self.prompt_context else None,
            "candidate_audit": [c.to_dict() for c in self.candidate_audit],
            "numerical_diffs": [d.to_dict() for d in self.numerical_diffs],
            "hop_evidence_chain": [h.to_dict() for h in self.hop_evidence_chain],
            "chain_completeness_gate": self.chain_completeness_gate,
        }

