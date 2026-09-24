"""
RAISE Proof-Level Telemetry Schema
Captures comprehensive forensic traces across query planning, candidate generation,
evidence reranking, relation resolution, proof graph traversal, deterministic operations,
answer derivation, and calibrated abstention gating.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProofHopTelemetry:
    hop_id: int
    query_text: str
    target_entity: str
    expected_relation: str
    candidate_count: int
    accepted_evidence_ids: List[str] = field(default_factory=list)
    rejected_evidence_ids: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    proof_status: str = "PENDING"  # "PENDING", "RESOLVED", "FAILED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProofLevelLedger:
    query_plan: Dict[str, Any] = field(default_factory=dict)
    retrieval_candidates: List[Dict[str, Any]] = field(default_factory=list)
    reranked_chunks: List[Dict[str, Any]] = field(default_factory=list)
    hop_evidence: List[ProofHopTelemetry] = field(default_factory=list)
    entity_resolutions: List[Dict[str, Any]] = field(default_factory=list)
    relation_checks: List[Dict[str, Any]] = field(default_factory=list)
    proof_graph: Dict[str, Any] = field(default_factory=dict)
    deterministic_operations: List[Dict[str, Any]] = field(default_factory=list)
    answer_derivation: Dict[str, Any] = field(default_factory=dict)
    abstention_gate: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_plan": self.query_plan,
            "retrieval_candidates_count": len(self.retrieval_candidates),
            "reranked_chunks_count": len(self.reranked_chunks),
            "hop_evidence": [h.to_dict() for h in self.hop_evidence],
            "entity_resolutions": self.entity_resolutions,
            "relation_checks": self.relation_checks,
            "proof_graph": self.proof_graph,
            "deterministic_operations": self.deterministic_operations,
            "answer_derivation": self.answer_derivation,
            "abstention_gate": self.abstention_gate,
            "timestamp": self.timestamp,
        }
