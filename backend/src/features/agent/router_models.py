"""
Agent Execution Plan & Sufficiency Models
=========================================
Data classes representing decomposed query analysis, tool execution schedules,
and multi-hop evidence sufficiency audits.

Architectural Role:
-------------------
1. `EvidenceSufficiencyReport`:
   - Tracks whether retrieved multi-substrate evidence is sufficient to answer the prompt.
   - Identifies missing elements (e.g., missing financial table, missing comparison year).

2. `AgentExecutionPlan`:
   - Represents the complete execution plan for an agent query:
     * query_type ("SIMPLE_FACT", "COMPARATIVE_ANALYSIS", "RELATIONSHIP_QUERY", "SEMANTIC_EXPLORATION")
     * target_metrics, target_years, extracted_universities/institutions
     * selected_tools ("fact_lookup", "vector_search", "graph_traversal", "table_lookup")
     * retrieved evidence, verified claims, citations, and grounded answer contracts.

How to Extend or Update:
------------------------
- To add new tool options, document them in `selected_tools`.
- To attach additional synthesis metadata for frontend traces, update `to_dict()`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceSufficiencyReport:
    """Audit report assessing whether retrieved evidence is sufficient to ground the answer."""
    sufficient: bool
    missing_elements: List[str]
    iteration_count: int = 1
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to standard Python dictionary."""
        return asdict(self)


@dataclass
class AgentExecutionPlan:
    """Structured plan and evidence container for agent query execution."""
    query: str
    query_type: str  # "SIMPLE_FACT", "COMPARATIVE_ANALYSIS", "RELATIONSHIP_QUERY", "SEMANTIC_EXPLORATION"
    extracted_universities: List[str] = field(default_factory=list)
    target_metrics: List[str] = field(default_factory=list)
    target_years: List[int] = field(default_factory=list)
    selected_tools: List[str] = field(default_factory=list)
    retrieved_evidence: Dict[str, Any] = field(default_factory=dict)
    sufficiency_report: Optional[EvidenceSufficiencyReport] = None
    grounded_answer: Optional[str] = None
    traceability_score: float = 0.0
    verified_claims: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    follow_up_inquiries: List[str] = field(default_factory=list)
    answer_contract: Optional[Dict[str, Any]] = None
    synthesis_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes execution plan and evidence trace for telemetry and UI display."""
        return {
            "query": self.query,
            "query_type": self.query_type,
            "extracted_universities": self.extracted_universities,
            "target_metrics": self.target_metrics,
            "target_years": self.target_years,
            "selected_tools": self.selected_tools,
            "sufficiency_report": self.sufficiency_report.to_dict() if self.sufficiency_report else None,
            "grounded_answer": self.grounded_answer,
            "traceability_score": self.traceability_score,
            "verified_claims": self.verified_claims,
            "citations": self.citations,
            "follow_up_inquiries": self.follow_up_inquiries,
            "answer_contract": self.answer_contract,
        }
