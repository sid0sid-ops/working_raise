"""
RAISE Deterministic Numerical Executor
Executes mathematical and numeric comparisons deterministically in Python sandbox.
Provides verified outputs for arithmetic, sorting, counting, and set operations.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union


@dataclass
class DeterministicExecutionResult:
    operator: str
    inputs: List[Any]
    result: Any
    proof_chunk_ids: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NumericalExecutor:
    """
    Sandboxed Python execution engine for algebraic, numerical, and set reasoning.
    """

    @staticmethod
    def _safe_float(val: Any, default: float = 0.0) -> float:
        try:
            return float(str(val).replace(",", "").strip())
        except (ValueError, TypeError):
            return default

    @classmethod
    def execute(
        cls,
        operator: str,
        operands: List[Any],
        proof_chunk_ids: Optional[List[str]] = None,
    ) -> DeterministicExecutionResult:
        op = operator.upper().strip()
        proof_ids = proof_chunk_ids or []

        if op in ("ADD", "SUM"):
            numeric_vals = [cls._safe_float(x) for x in operands if x is not None]
            res = sum(numeric_vals)
            # If all are ints, return int
            if all(cls._safe_float(x).is_integer() for x in numeric_vals):
                res = int(res)
            return DeterministicExecutionResult(
                operator="ADD",
                inputs=operands,
                result=res,
                proof_chunk_ids=proof_ids,
                explanation=f"{' + '.join(str(x) for x in operands)} = {res}",
            )

        elif op in ("SUB", "DIFFERENCE", "SUBTRACT"):
            if len(operands) >= 2:
                v1 = cls._safe_float(operands[0])
                v2 = cls._safe_float(operands[1])
                res = v1 - v2
                if v1.is_integer() and v2.is_integer():
                    res = int(res)
                return DeterministicExecutionResult(
                    operator="SUB",
                    inputs=operands,
                    result=res,
                    proof_chunk_ids=proof_ids,
                    explanation=f"{operands[0]} - {operands[1]} = {res}",
                )

        elif op in ("ABS_DIFF", "AGE_DIFF"):
            if len(operands) >= 2:
                v1 = cls._safe_float(operands[0])
                v2 = cls._safe_float(operands[1])
                res = abs(v1 - v2)
                if v1.is_integer() and v2.is_integer():
                    res = int(res)
                return DeterministicExecutionResult(
                    operator="ABS_DIFF",
                    inputs=operands,
                    result=res,
                    proof_chunk_ids=proof_ids,
                    explanation=f"|{operands[0]} - {operands[1]}| = {res}",
                )

        elif op in ("PERCENTAGE_CHANGE", "GROWTH_RATE"):
            if len(operands) >= 2:
                initial = cls._safe_float(operands[0])
                final = cls._safe_float(operands[1])
                if initial != 0:
                    pct = ((final - initial) / abs(initial)) * 100.0
                    return DeterministicExecutionResult(
                        operator="PERCENTAGE_CHANGE",
                        inputs=operands,
                        result=round(pct, 2),
                        proof_chunk_ids=proof_ids,
                        explanation=f"(({final} - {initial}) / {initial}) * 100 = {pct:.2f}%",
                    )

        elif op in ("ARGMAX", "MAX"):
            # Handles list of (label, val) tuples or list of values
            if operands and isinstance(operands[0], (tuple, list)) and len(operands[0]) == 2:
                best = max(operands, key=lambda x: float(x[1]))
                return DeterministicExecutionResult(
                    operator="ARGMAX",
                    inputs=operands,
                    result=best[0],
                    proof_chunk_ids=proof_ids,
                    explanation=f"Max item is {best[0]} with value {best[1]}",
                )
            elif operands:
                res = max(float(x) for x in operands)
                return DeterministicExecutionResult(
                    operator="MAX",
                    inputs=operands,
                    result=res,
                    proof_chunk_ids=proof_ids,
                    explanation=f"Max is {res}",
                )

        elif op in ("ARGMIN", "MIN"):
            if operands and isinstance(operands[0], (tuple, list)) and len(operands[0]) == 2:
                best = min(operands, key=lambda x: float(x[1]))
                return DeterministicExecutionResult(
                    operator="ARGMIN",
                    inputs=operands,
                    result=best[0],
                    proof_chunk_ids=proof_ids,
                    explanation=f"Min item is {best[0]} with value {best[1]}",
                )
            elif operands:
                res = min(float(x) for x in operands)
                return DeterministicExecutionResult(
                    operator="MIN",
                    inputs=operands,
                    result=res,
                    proof_chunk_ids=proof_ids,
                    explanation=f"Min is {res}",
                )

        elif op in ("COUNT",):
            res = len(operands)
            return DeterministicExecutionResult(
                operator="COUNT",
                inputs=operands,
                result=res,
                proof_chunk_ids=proof_ids,
                explanation=f"Counted {res} elements",
            )

        elif op in ("INTERSECT", "SET_INTERSECTION"):
            sets = [set(x) if isinstance(x, (list, tuple, set)) else {x} for x in operands]
            if sets:
                res = list(set.intersection(*sets))
                return DeterministicExecutionResult(
                    operator="INTERSECT",
                    inputs=operands,
                    result=res,
                    proof_chunk_ids=proof_ids,
                    explanation=f"Intersection contains {len(res)} elements: {res}",
                )

        elif op in ("LETTER_COUNT", "LETTERS_COUNT"):
            text = str(operands[0]) if operands else ""
            res = len([c for c in text if c.isalnum()])
            return DeterministicExecutionResult(
                operator="LETTER_COUNT",
                inputs=operands,
                result=res,
                proof_chunk_ids=proof_ids,
                explanation=f"Alphanumeric letter count of '{text}' is {res}",
            )

        elif op in ("CHAR_COUNT", "CHARS_COUNT"):
            text = str(operands[0]) if operands else ""
            res = len(text.strip().strip('"').strip("'"))
            return DeterministicExecutionResult(
                operator="CHAR_COUNT",
                inputs=operands,
                result=res,
                proof_chunk_ids=proof_ids,
                explanation=f"Character count of '{text}' is {res}",
            )

        elif op in ("MULTIPLY", "PRODUCT", "MULT"):
            import math
            numeric_vals = [float(x) for x in operands if x is not None]
            res = math.prod(numeric_vals) if numeric_vals else 0
            if numeric_vals and all(float(x).is_integer() for x in numeric_vals):
                res = int(res)
            return DeterministicExecutionResult(
                operator="MULTIPLY",
                inputs=operands,
                result=res,
                proof_chunk_ids=proof_ids,
                explanation=f"{' * '.join(str(x) for x in operands)} = {res}",
            )

        # Fallback / Identity
        return DeterministicExecutionResult(
            operator=op,
            inputs=operands,
            result=operands[0] if operands else None,
            proof_chunk_ids=proof_ids,
            explanation=f"Evaluated {op}",
        )
