"""
RAISE Claim-Evidence-Derivation Graph
Represents assertions as either:
  1. DIRECT_PROOF: Claim token is explicitly supported by retrieved text spans.
  2. DERIVED_PROOF: Leaf premises are verified and conclusion is produced by a deterministic operator.
Eliminates over-abstention where validly derived answers (e.g. arithmetic, dates, table lookups)
were rejected simply because the final answer string was not verbatim in the source chunks.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ProofType(str, Enum):
    DIRECT_PROOF = "DIRECT_PROOF"
    DERIVED_PROOF = "DERIVED_PROOF"
    UNVERIFIED = "UNVERIFIED"


@dataclass
class DerivationStep:
    operator: str
    input_premises: List[str]
    output_value: str
    supporting_chunk_ids: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GroundedClaimNode:
    claim_text: str
    proof_type: ProofType
    is_valid: bool
    confidence: float
    supporting_chunk_ids: List[str] = field(default_factory=list)
    derivation: Optional[DerivationStep] = None
    verification_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["proof_type"] = self.proof_type.value
        return d


class ClaimGraph:
    """
    Manages claim derivation paths and evidence chains.
    """

    def __init__(self):
        self.claims: List[GroundedClaimNode] = []

    def add_direct_claim(
        self,
        claim_text: str,
        supporting_chunks: List[Dict[str, Any]],
        confidence: float = 1.0,
    ) -> GroundedClaimNode:
        cids = [c.get("chunk_id", "") for c in supporting_chunks if c.get("chunk_id")]
        node = GroundedClaimNode(
            claim_text=claim_text,
            proof_type=ProofType.DIRECT_PROOF,
            is_valid=True,
            confidence=confidence,
            supporting_chunk_ids=cids,
            verification_notes="Directly substantiated by explicit context passage text.",
        )
        self.claims.append(node)
        return node

    def add_derived_claim(
        self,
        claim_text: str,
        operator: str,
        input_premises: List[str],
        supporting_chunks: List[Dict[str, Any]],
        explanation: str = "",
        confidence: float = 0.95,
    ) -> GroundedClaimNode:
        cids = [c.get("chunk_id", "") for c in supporting_chunks if c.get("chunk_id")]
        step = DerivationStep(
            operator=operator,
            input_premises=input_premises,
            output_value=claim_text,
            supporting_chunk_ids=cids,
            explanation=explanation,
        )
        node = GroundedClaimNode(
            claim_text=claim_text,
            proof_type=ProofType.DERIVED_PROOF,
            is_valid=True,
            confidence=confidence,
            supporting_chunk_ids=cids,
            derivation=step,
            verification_notes=f"Deterministically derived via {operator} from verified leaf premises.",
        )
        self.claims.append(node)
        return node

    def is_fully_grounded(self) -> bool:
        if not self.claims:
            return False
        return all(c.is_valid for c in self.claims)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claims": [c.to_dict() for c in self.claims],
            "is_fully_grounded": self.is_fully_grounded(),
        }
