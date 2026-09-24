"""
RAISE Verification Feature Service
Integrates claim verification, numeric fact validation, deterministic table arithmetic, and anti-hallucination checks.
"""
from .claim_verifier import ClaimVerifier, VerifiedClaim, AnswerContract
from .fact_engine import FactEngine, NumericFact, TemporalPeriod
from .table_engine import TableEngine, TableMatrixRecord, CellCoordinate
from .math_engine import DeterministicMathEngine, MathComputationResult

class VerificationService:
    """Unified facade for all verification, arithmetic, and validation operations."""

    def __init__(self, llm_client=None):
        self.claim_verifier = ClaimVerifier(llm_client=llm_client)
        self.fact_engine = FactEngine()
        self.table_engine = TableEngine()
        self.math_engine = DeterministicMathEngine()

    def verify_answer(self, claim_text: str, context_text: str) -> VerifiedClaim:
        return self.claim_verifier.verify(claim_text, context_text)

__all__ = [
    "VerificationService",
    "ClaimVerifier",
    "VerifiedClaim",
    "AnswerContract",
    "FactEngine",
    "NumericFact",
    "TemporalPeriod",
    "TableEngine",
    "TableMatrixRecord",
    "CellCoordinate",
    "DeterministicMathEngine",
    "MathComputationResult",
]
