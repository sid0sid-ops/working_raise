"""
RAISE Deterministic Mathematical Pre-computation Engine.
Executes deterministic Python arithmetic calculations (Sum, Average, Growth Rate,
Percentage Share, Ratios, YoY Differences) on extracted numeric arrays before LLM synthesis.
Bypasses LLM arithmetic hallucinations and provides mathematically verified fact envelopes.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MathComputationResult:
    operation: str  # "SUM", "AVERAGE", "GROWTH_RATE", "DIFFERENCE", "RATIO", "PERCENTAGE_SHARE"
    input_values: List[float]
    calculated_value: float
    formatted_result: str
    formula_expression: str
    units: Optional[str] = None
    is_verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DeterministicMathEngine:
    """
    Local sandbox execution engine for deterministic mathematical pre-computations.
    """

    MATH_INTENT_PATTERNS = {
        "GROWTH_RATE": r"\b(growth rate|percentage increase|percentage change|grew by|increased by|yoy growth|cagr)\b",
        "SUM": r"\b(calculate\s+(?:the\s+)?(?:total|sum)|compute\s+(?:the\s+)?(?:total|sum)|sum\s+of\b|total\s+(?:combined|sum|revenue|amount|expenditure)|combined\s+(?:sum|total|revenue)|total\b|sum\b|add\s+(?:up|together))\b",
        "AVERAGE": r"\b(calculate\s+(?:the\s+)?average|compute\s+(?:the\s+)?average|average\s+per\s+faculty|mean\s+per\s+department)\b",
        "DIFFERENCE": r"\b(calculate\s+(?:the\s+)?difference|compute\s+(?:the\s+)?difference|net\s+change\s+between|delta\s+between)\b",
        "RATIO": r"\b(calculate\s+(?:the\s+)?ratio|compute\s+(?:the\s+)?ratio|student\s+faculty\s+ratio)\b",
    }

    @classmethod
    def detect_math_intent(cls, query: str) -> Optional[str]:
        q_lower = query.lower()
        for intent, pattern in cls.MATH_INTENT_PATTERNS.items():
            if re.search(pattern, q_lower):
                return intent
        return None

    @classmethod
    def compute(
        cls,
        operation: str,
        values: List[float],
        units: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Optional[MathComputationResult]:
        if not values:
            return None

        clean_vals = [float(v) for v in values if v is not None]
        if not clean_vals:
            return None

        op = operation.upper()

        if op == "SUM":
            res = sum(clean_vals)
            formula = " + ".join([f"{v:g}" for v in clean_vals]) + f" = {res:g}"
            formatted = f"{res:g}"
            return MathComputationResult(
                operation="SUM",
                input_values=clean_vals,
                calculated_value=round(res, 4),
                formatted_result=formatted,
                formula_expression=formula,
                units=units,
            )

        elif op == "AVERAGE":
            res = sum(clean_vals) / len(clean_vals)
            formula = f"({ ' + '.join([f'{v:g}' for v in clean_vals]) }) / {len(clean_vals)} = {res:.2f}"
            formatted = f"{res:.2f}"
            return MathComputationResult(
                operation="AVERAGE",
                input_values=clean_vals,
                calculated_value=round(res, 4),
                formatted_result=formatted,
                formula_expression=formula,
                units=units,
            )

        elif op == "GROWTH_RATE" and len(clean_vals) >= 2:
            initial = clean_vals[0]
            final = clean_vals[-1]
            if initial != 0:
                growth_pct = ((final - initial) / abs(initial)) * 100
                formula = f"(({final:g} - {initial:g}) / {initial:g}) * 100 = {growth_pct:+.2f}%"
                formatted = f"{growth_pct:+.2f}%"
                return MathComputationResult(
                    operation="GROWTH_RATE",
                    input_values=[initial, final],
                    calculated_value=round(growth_pct, 4),
                    formatted_result=formatted,
                    formula_expression=formula,
                    units="percentage",
                )

        elif op == "DIFFERENCE" and len(clean_vals) >= 2:
            diff = clean_vals[-1] - clean_vals[0]
            formula = f"{clean_vals[-1]:g} - {clean_vals[0]:g} = {diff:g}"
            formatted = f"{diff:g}"
            return MathComputationResult(
                operation="DIFFERENCE",
                input_values=[clean_vals[0], clean_vals[-1]],
                calculated_value=round(diff, 4),
                formatted_result=formatted,
                formula_expression=formula,
                units=units,
            )

        elif op == "RATIO" and len(clean_vals) >= 2:
            denom = clean_vals[1]
            if denom != 0:
                ratio = clean_vals[0] / denom
                formula = f"{clean_vals[0]:g} / {clean_vals[1]:g} = {ratio:.2f}:1"
                formatted = f"{ratio:.2f}:1"
                return MathComputationResult(
                    operation="RATIO",
                    input_values=[clean_vals[0], clean_vals[1]],
                    calculated_value=round(ratio, 4),
                    formatted_result=formatted,
                    formula_expression=formula,
                    units="ratio",
                )

        return None

    @classmethod
    def generate_precomputed_context(
        cls,
        query: str,
        extracted_numbers: List[float],
        units: Optional[str] = None,
    ) -> Optional[str]:
        intent = cls.detect_math_intent(query)
        if not intent:
            return None

        result = cls.compute(intent, extracted_numbers, units=units)
        if not result:
            return None

        return (
            f"\n[DETERMINISTIC MATHEMATICAL PRE-COMPUTATION — AUDITED FACT]\n"
            f"• Operation: {result.operation}\n"
            f"• Verified Calculation: {result.formula_expression}\n"
            f"• Deterministic Result: {result.formatted_result} {result.units or ''}\n"
            f"[INSTRUCTION FOR QWEN 2.5 7B: Cite the exact calculated value above. Do NOT perform independent mental arithmetic.]\n"
        )
