"""
RAISE Unified Operator Engine
Coordinates deterministic mathematical, temporal, tabular, and logical operators.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.reasoning.numerical import NumericalExecutor, DeterministicExecutionResult
from src.reasoning.temporal import TemporalEngine, EventInterval
from src.reasoning.tables import TableReasoningEngine, ParsedTable


class UnifiedOperatorEngine:
    """
    Central router and dispatcher for deterministic operations.
    """

    @classmethod
    def execute(
        cls,
        operator_name: str,
        operands: List[Any],
        proof_chunk_ids: Optional[List[str]] = None,
    ) -> DeterministicExecutionResult:
        op = operator_name.upper().strip()

        # 1. Temporal Operators
        if op == "ELAPSED_FULL_YEARS" and len(operands) >= 2:
            d1 = TemporalEngine.parse_flexible_date(str(operands[0]))
            d2 = TemporalEngine.parse_flexible_date(str(operands[1]))
            if d1 and d2:
                years = TemporalEngine.elapsed_full_years(d1, d2)
                return DeterministicExecutionResult(
                    operator="ELAPSED_FULL_YEARS",
                    inputs=operands,
                    result=years,
                    proof_chunk_ids=proof_chunk_ids or [],
                    explanation=f"Elapsed full years between {d1} and {d2} is {years}",
                )

        elif op in ("AGE_AT_EVENT", "AGE_ON") and len(operands) >= 2:
            birth_d = TemporalEngine.parse_flexible_date(str(operands[0]))
            event_d = TemporalEngine.parse_flexible_date(str(operands[1]))
            if birth_d and event_d:
                age = TemporalEngine.age_on_date(birth_d, event_d)
                return DeterministicExecutionResult(
                    operator="AGE_AT_EVENT",
                    inputs=operands,
                    result=age,
                    proof_chunk_ids=proof_chunk_ids or [],
                    explanation=f"Age at event on {event_d} for birthdate {birth_d} is {age}",
                )

        # 2. Numerical Operators
        return NumericalExecutor.execute(operator_name, operands, proof_chunk_ids)
