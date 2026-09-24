"""
Data Models and Type Definitions for Graph-Guided Adaptive Hierarchical Chunking (GGAHC).
Defines representations for structural units, candidate semantic units, boundary decisions,
hierarchical information units (Document, Section, Parent, Child, Proposition, Table, Figure),
and comprehensive diagnostics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ChunkLevel(str, Enum):
    DOCUMENT = "document"
    SECTION = "section"
    PARENT = "parent"
    CHILD = "child"
    PROPOSITION = "proposition"
    TABLE = "table"
    FIGURE = "figure"


class BoundaryDecision(str, Enum):
    MERGE = "MERGE"
    SPLIT = "SPLIT"
    PRESERVE = "PRESERVE"


@dataclass
class SignalResult:
    """
    Measurable calculation record for an individual chunking boundary signal.
    Ensures zero fabricated scores by requiring method and availability tracking.
    """
    name: str
    value: Optional[float]
    available: bool
    method: str  # e.g., "token_jaccard_content_words", "graph_bfs_shortest_path", "exact_overlap"
    evidence_count: int = 0  # Count of intersecting tokens, entities, relations, etc.
    quality: float = 1.0  # [0.0, 1.0] representing data density/confidence
    missing_reason: Optional[str] = None  # Reason why signal is unavailable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": round(self.value, 4) if self.value is not None else None,
            "available": self.available,
            "method": self.method,
            "evidence_count": self.evidence_count,
            "quality": round(self.quality, 4),
            "missing_reason": self.missing_reason,
        }


@dataclass
class HardConstraintResult:
    """
    Represents an immutable structural or layout constraint that gates boundary decisions
    prior to soft signal evaluation.
    """
    triggered: bool
    constraint_type: Optional[str] = None  # TABLE_BOUNDARY, FIGURE_BOUNDARY, MAX_TOKENS_EXCEEDED, MAJOR_HEADING_CHANGE, CONTINUATION_HEADER
    forced_action: Optional[BoundaryDecision] = None
    reason_code: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered": self.triggered,
            "constraint_type": self.constraint_type,
            "forced_action": self.forced_action.value if self.forced_action else None,
            "reason_code": self.reason_code,
            "evidence": dict(self.evidence),
        }


@dataclass
class BoundaryExplanation:
    """
    Deterministic Boundary Decision Record & Audit Ledger Entry.
    Maintains 100% backward compatibility with legacy consumers while providing
    complete mathematical auditability and zero fabricated metrics.
    """
    decision: BoundaryDecision
    boundary_score: float
    confidence: float
    reasons: List[str] = field(default_factory=list)
    signals: Dict[str, float] = field(default_factory=dict)
    boundary_id: str = ""
    unit_a_id: str = ""
    unit_b_id: str = ""
    page_a: int = 1
    page_b: int = 1
    hard_constraint: Optional[HardConstraintResult] = None
    signal_results: Dict[str, SignalResult] = field(default_factory=dict)
    configured_weights: Dict[str, float] = field(default_factory=dict)
    normalized_weights: Dict[str, float] = field(default_factory=dict)
    reason_codes: List[str] = field(default_factory=list)
    is_strict_mode: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "unit_a_id": self.unit_a_id,
            "unit_b_id": self.unit_b_id,
            "page_a": self.page_a,
            "page_b": self.page_b,
            "decision": self.decision.value,
            "boundary_score": round(self.boundary_score, 4),
            "confidence": round(self.confidence, 4),
            "reasons": list(self.reasons),
            "reason_codes": list(self.reason_codes),
            "signals": {k: round(v, 4) for k, v in self.signals.items()},
            "signal_results": {k: v.to_dict() for k, v in self.signal_results.items()},
            "hard_constraint": self.hard_constraint.to_dict() if self.hard_constraint else None,
            "configured_weights": {k: round(v, 4) for k, v in self.configured_weights.items()},
            "normalized_weights": {k: round(v, 4) for k, v in self.normalized_weights.items()},
            "is_strict_mode": self.is_strict_mode,
        }


@dataclass
class Proposition:
    proposition_id: str
    text: str
    parent_chunk_id: str
    document_id: str
    section_id: str
    page_number: int
    entities: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StructuralUnit:
    unit_id: str
    unit_type: str  # "title", "heading", "paragraph", "list", "table", "figure"
    content: str
    heading: str
    heading_level: int
    page_number: int
    doc_page_number: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    table_metadata: Optional[Dict[str, Any]] = None
    figure_metadata: Optional[Dict[str, Any]] = None
    source_block_id: Optional[str] = None
    is_continued: bool = False
    continuation_of_id: Optional[str] = None
    is_list: bool = False
    list_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateUnit:
    candidate_id: str
    document_id: str
    section_id: str
    heading: str
    page_start: int
    page_end: int
    plain_text: str
    heading_level: int = 3
    structural_unit_ids: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    community_id: Optional[str] = None
    is_table: bool = False
    is_figure: bool = False
    is_continued: bool = False
    continuation_of_id: Optional[str] = None
    is_list: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def token_estimate(self) -> int:
        return max(1, len(self.plain_text.split()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceBundle:
    """
    Minimum Complete Evidence Unit for retrieval.
    Combines primary text, heading hierarchy, tables, captions, footnotes,
    and provenance to prevent fragmented answers.
    """
    bundle_id: str
    primary_chunk_id: str
    document_id: str
    heading_hierarchy: List[str] = field(default_factory=list)
    text_content: str = ""
    table_content: Optional[str] = None
    table_headers: List[str] = field(default_factory=list)
    caption: Optional[str] = None
    footnotes: List[str] = field(default_factory=list)
    referenced_entity_ids: List[str] = field(default_factory=list)
    source_page: int = 1
    is_complete: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdaptiveChunk:
    """
    Standard Adaptive Chunk Model.
    Maintains 100% backward compatibility with existing RAG chunk consumers while
    providing rich multi-resolution, hierarchical, and graph metadata.
    """
    chunk_id: str
    document_id: str
    parent_chunk_id: Optional[str] = None
    section_id: str = "sec_0"
    chunk_level: str = "child"  # ChunkLevel value
    plain_text: str = ""
    contextualized_content: str = ""
    summary: Optional[str] = None
    heading: str = "Section"
    heading_level: int = 3
    primary_page: int = 1
    printed_page: Optional[str] = None
    source_pages: List[int] = field(default_factory=lambda: [1])
    propositions: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    community_ids: List[str] = field(default_factory=list)
    source_block_ids: List[str] = field(default_factory=list)
    previous_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
    token_estimate: int = 0
    boundary_score_before: float = 0.0
    boundary_score_after: float = 0.0
    boundary_reasons: List[str] = field(default_factory=list)
    chunking_strategy: str = "gga_hybrid"
    embedding_model: Optional[str] = None
    embedding_id: Optional[str] = None
    is_table: bool = False
    is_figure: bool = False
    tables_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Legacy compatibility property
    @property
    def text(self) -> str:
        return self.plain_text

    @property
    def enriched_text(self) -> str:
        return self.contextualized_content or self.plain_text

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes to dictionary ensuring all legacy and modern keys are present.
        """
        d = asdict(self)
        # Ensure backward-compatible keys expected by vector_engine and agent_router
        d["text"] = self.plain_text
        d["enriched_text"] = self.contextualized_content or self.plain_text
        d["chunk_type"] = "table" if self.is_table else ("figure" if self.is_figure else "prose")
        d["recommended_task"] = self.metadata.get("recommended_task", "academic_research")
        d["university"] = self.metadata.get("university") or self.metadata.get("institution", "Institution")
        d["pdf_filename"] = self.metadata.get("pdf_filename", f"{self.document_id}.pdf")
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AdaptiveChunk:
        data_copy = dict(data)
        # Map legacy keys if needed
        plain_text = data_copy.pop("plain_text", None) or data_copy.pop("text", "")
        contextualized_content = data_copy.pop("contextualized_content", None) or data_copy.pop("enriched_text", plain_text)
        
        # Filter valid fields
        valid_keys = set(cls.__annotations__.keys())
        filtered = {k: v for k, v in data_copy.items() if k in valid_keys}
        filtered["plain_text"] = plain_text
        filtered["contextualized_content"] = contextualized_content
        return cls(**filtered)


@dataclass
class ChunkingDiagnosticReport:
    document_id: str
    filename: str
    strategy: str
    pages: int = 0
    structural_units_count: int = 0
    candidate_semantic_units_count: int = 0
    final_parent_chunks_count: int = 0
    final_child_chunks_count: int = 0
    propositions_count: int = 0
    entities_count: int = 0
    relationships_count: int = 0
    communities_count: int = 0
    average_child_tokens: float = 0.0
    average_parent_tokens: float = 0.0
    merge_operations: int = 0
    split_operations: int = 0
    preserve_operations: int = 0
    average_boundary_confidence: float = 0.0
    tables_count: int = 0
    figures_count: int = 0
    signal_availability_rates: Dict[str, float] = field(default_factory=dict)
    hard_constraints_triggered: Dict[str, int] = field(default_factory=dict)
    decision_ledger: List[Dict[str, Any]] = field(default_factory=list)
    evidence_bundles_count: int = 0
    boundary_traces: List[Dict[str, Any]] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
