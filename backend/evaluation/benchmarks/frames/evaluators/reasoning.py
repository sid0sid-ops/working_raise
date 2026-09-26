"""
FRAMES Benchmark Reasoning Evaluator
Assesses complex cognitive reasoning across 5 major dimensions:
  1. Multi-Hop Reasoning (Multi-document bridge entity integration)
  2. Numerical Reasoning (Mathematical operations and quantity precision)
  3. Temporal Reasoning (Chronological sequencing, intervals, dates)
  4. Tabular Reasoning (Structured row/column lookup and cross-referencing)
  5. Multiple-Constraint Reasoning (Satisfiability across compound criteria)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from ..data.schema import FramesQuestion


class ReasoningResult(BaseModel):
    """Structured reasoning evaluation result across active dimensions."""
    question_id: str
    overall_reasoning_score: float = Field(..., ge=0.0, le=1.0)
    evaluated_dimensions: List[str] = Field(default_factory=list)
    multihop_score: Optional[float] = None
    numerical_score: Optional[float] = None
    temporal_score: Optional[float] = None
    tabular_score: Optional[float] = None
    constraint_score: Optional[float] = None
    passed_dimensions: List[str] = Field(default_factory=list)
    failed_dimensions: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class ReasoningEvaluator:
    """
    Evaluates pipeline reasoning ability based on the specific reasoning demands of each question.
    """

    def _extract_years(self, text: str) -> Set[str]:
        return set(re.findall(r"\b(?:18|19|20)\d{2}\b", text))

    def _extract_numbers(self, text: str) -> List[float]:
        raw = re.findall(r"\b\d+(?:[\.,]\d+)?\b", text)
        res = []
        for r in raw:
            try:
                res.append(float(r.replace(",", "")))
            except Exception:
                pass
        return res

    def evaluate(
        self,
        question: FramesQuestion,
        generated_answer: str,
        retrieved_context: str,
    ) -> ReasoningResult:
        """
        Evaluates active reasoning dimensions for the benchmark question.
        """
        qid = question.question_id
        ref_ans = question.reference_answer.strip()
        gen_ans = generated_answer.strip()

        scores: Dict[str, float] = {}
        details: Dict[str, Any] = {}
        active_dims: List[str] = []

        # 1. Multi-Hop Reasoning Evaluation
        if question.is_multihop:
            active_dims.append("Multi-hop")
            # Multi-hop succeeds if evidence from multiple distinct source titles/links is utilized
            sources_present = [link for link in question.wiki_links if any(
                part.lower() in retrieved_context.lower() 
                for part in link.split("/")[-1].replace("_", " ").split() if len(part) > 3
            )]
            hop_ratio = len(sources_present) / max(1, len(question.wiki_links))
            # Answer must also reflect final integrated state
            ref_overlap = 1.0 if ref_ans.lower() in gen_ans.lower() else (
                len(set(ref_ans.lower().split()).intersection(gen_ans.lower().split())) / max(1, len(ref_ans.split()))
            )
            multihop_score = round((hop_ratio * 0.4) + (ref_overlap * 0.6), 4)
            scores["Multi-hop"] = multihop_score
            details["multihop"] = {
                "required_sources": question.source_count,
                "sources_evidenced": len(sources_present),
                "integration_score": multihop_score
            }

        # 2. Numerical Reasoning Evaluation
        if question.is_numerical:
            active_dims.append("Numerical reasoning")
            ref_nums = self._extract_numbers(ref_ans)
            gen_nums = self._extract_numbers(gen_ans)
            if not ref_nums:
                num_score = 1.0 if ref_ans.lower() in gen_ans.lower() else 0.5
            elif gen_nums:
                # Check for exact or close numeric matches (< 1% relative error)
                matched = 0
                for rn in ref_nums:
                    if any(abs(rn - gn) / max(abs(rn), 1e-5) < 0.01 for gn in gen_nums):
                        matched += 1
                num_score = round(matched / len(ref_nums), 4)
            else:
                num_score = 0.0
            scores["Numerical reasoning"] = num_score
            details["numerical"] = {
                "reference_numbers": ref_nums,
                "generated_numbers": gen_nums,
                "exact_numerical_match": num_score >= 0.99
            }

        # 3. Temporal Reasoning Evaluation
        if question.is_temporal:
            active_dims.append("Temporal reasoning")
            ref_years = self._extract_years(ref_ans)
            gen_years = self._extract_years(gen_ans)
            if ref_years:
                temp_score = 1.0 if ref_years.issubset(gen_years) else 0.0
            else:
                # Chronological keywords check
                time_words = {"first", "last", "before", "after", "during", "since", "until", "century", "decade", "year"}
                ref_time_tokens = set(ref_ans.lower().split()).intersection(time_words)
                if ref_time_tokens:
                    temp_score = 1.0 if ref_time_tokens.intersection(gen_ans.lower().split()) else 0.2
                else:
                    temp_score = 1.0 if ref_ans.lower() in gen_ans.lower() else 0.4
            scores["Temporal reasoning"] = temp_score
            details["temporal"] = {
                "reference_years": list(ref_years),
                "generated_years": list(gen_years),
                "temporal_match": temp_score >= 0.8
            }

        # 4. Tabular Reasoning Evaluation
        if question.is_tabular:
            active_dims.append("Tabular reasoning")
            # Checks if structured values or entity-metric pairs from reference appear in answer
            tab_score = 1.0 if ref_ans.lower() in gen_ans.lower() else (
                len(set(ref_ans.lower().split()).intersection(gen_ans.lower().split())) / max(1, len(ref_ans.split()))
            )
            scores["Tabular reasoning"] = round(tab_score, 4)
            details["tabular"] = {"tabular_cell_match": tab_score >= 0.75}

        # 5. Multiple-Constraint Reasoning Evaluation
        if question.is_constraint:
            active_dims.append("Multiple constraints")
            # Check satisfaction of distinct entity/attribute criteria in question
            keywords = [w for w in re.findall(r"\b[A-Z][a-z]+\b", question.prompt) if len(w) > 3]
            if keywords:
                satisfied = sum(1 for kw in keywords if kw.lower() in gen_ans.lower() or kw.lower() in retrieved_context.lower())
                c_score = round(satisfied / len(keywords), 4)
            else:
                c_score = 1.0 if ref_ans.lower() in gen_ans.lower() else 0.5
            scores["Multiple constraints"] = c_score
            details["constraints"] = {"constraint_satisfaction_rate": c_score}

        # Default if no specialized reasoning tags matched
        if not scores:
            base_overlap = len(set(ref_ans.lower().split()).intersection(gen_ans.lower().split())) / max(1, len(ref_ans.split()))
            overall = round(base_overlap, 4)
            active_dims.append("General reasoning")
            scores["General reasoning"] = overall
        else:
            overall = round(sum(scores.values()) / len(scores), 4)

        passed = [dim for dim, s in scores.items() if s >= 0.70]
        failed = [dim for dim, s in scores.items() if s < 0.70]

        return ReasoningResult(
            question_id=qid,
            overall_reasoning_score=overall,
            evaluated_dimensions=active_dims,
            multihop_score=scores.get("Multi-hop"),
            numerical_score=scores.get("Numerical reasoning"),
            temporal_score=scores.get("Temporal reasoning"),
            tabular_score=scores.get("Tabular reasoning"),
            constraint_score=scores.get("Multiple constraints"),
            passed_dimensions=passed,
            failed_dimensions=failed,
            details=details,
        )
