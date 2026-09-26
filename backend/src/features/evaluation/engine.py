"""
RAISE System Evaluation, Optimization, and Operational Governance Engine
========================================================================
Coordinates factual claim verification, numerical consistency checks, citation validation,
offline RAGAS-aligned proxy evaluation, and runtime quality gating.

Modular Architecture Breakdown:
--------------------------------
  - models.py: Data containers (`StructuredEvidence`, `ClaimVerificationResult`, `EvaluationReport`, `VerificationPath`)
  - numerical_verifier.py: Numeric, currency, percentage, and pairwise arithmetic check (`NumericalClaimVerifier`, `_is_float`)
  - citation_verifier.py: Academic bracket citation extraction & provenance matching (`CitationValidator`)
  - claim_verifier.py: Sentence splitting, abbreviation shielding, and 4-tier verification (`ClaimLevelVerifier`)
  - heuristic_evaluator.py: RAGAS-aligned proxy metrics for local development (`LocalHeuristicEvaluator`)
  - runtime_gate.py: LangGraph state machine runtime checkpoint & retry coordinator (`RuntimeFaithfulnessQualityGate`)

All symbols are cleanly re-exported here for 100% backward compatibility across all pipelines,
benchmark harnesses, and test suites.
"""

from __future__ import annotations

from .models import (
    VerificationPath,
    StructuredEvidence,
    ClaimVerificationResult,
    ClaimVerificationRecord,
    EvaluationReport,
)
from .numerical_verifier import (
    NumericalClaimVerifier,
    _is_float,
)
from .citation_verifier import (
    CitationValidator,
)
from .claim_verifier import (
    ClaimLevelVerifier,
)
from .heuristic_evaluator import (
    LocalHeuristicEvaluator,
)
from .runtime_gate import (
    RuntimeFaithfulnessQualityGate,
)

__all__ = [
    "VerificationPath",
    "StructuredEvidence",
    "ClaimVerificationResult",
    "ClaimVerificationRecord",
    "EvaluationReport",
    "NumericalClaimVerifier",
    "_is_float",
    "CitationValidator",
    "ClaimLevelVerifier",
    "LocalHeuristicEvaluator",
    "RuntimeFaithfulnessQualityGate",
]
