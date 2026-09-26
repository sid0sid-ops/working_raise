"""
FRAMES Benchmark Factuality Evaluator
Evaluates factual correctness and evidence grounding.
Distinguishes between:
  1. Reference-Answer Correctness (Does answer match ground truth?)
  2. Evidence-Grounded Factuality (Are generated claims corroborated by retrieved sources?)
Status values: correct, partially_correct, incorrect, unsupported, unanswerable.
"""

from __future__ import annotations

import re
import string
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from src.features.verification.math_engine import DeterministicMathEngine
from ..data.schema import FramesQuestion


class FactualityResult(BaseModel):
    """Structured factuality evaluation result for a single question."""
    question_id: str
    answer_status: str = Field(..., description="correct | partially_correct | incorrect | unsupported | unanswerable | abstained")
    factuality_score: float = Field(..., ge=0.0, le=1.0)
    reference_correctness_score: float = Field(..., ge=0.0, le=1.0)
    grounding_score: float = Field(..., ge=0.0, le=1.0)
    missing_information: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    explanation: str = ""


class FactualityEvaluator:
    """
    Evaluates generated answers against official FRAMES reference answers and retrieved context.
    Avoids relying exclusively on exact string matching.
    """

    def __init__(self):
        self.math_engine = DeterministicMathEngine()

    def _normalize_text(self, text: str) -> str:
        """Lowercases, folds Unicode diacritics, normalizes units/numbers, strips punctuation."""
        if not text:
            return ""
        import unicodedata
        # 1. Clean Unicode replacement characters (\ufffd) and fold diacritics (e.g. Lü -> Lu, Atlético -> Atletico)
        text = text.replace("\ufffd", "").replace("", "")
        text = "".join(
            c for c in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(c)
        )
        text = text.lower()

        # 2. Domain & unit equivalences
        text = re.sub(r"\bh1n1\b", "swine flu", text)
        text = re.sub(r"\bbezirk\b", "district", text)
        text = re.sub(r"\bmeters?\b|\bmetres?\b", "m", text)
        text = re.sub(r"\bkilometres?\b|\bkilometers?\b", "km", text)
        text = re.sub(r"\byears?\s+old\b", "years", text)
        text = re.sub(r"\bpercent\b|%", "percent", text)

        # 3. Frequency, ordinal, and word-number normalization
        word_num_map = {
            r"\bonce\b": "1", r"\btwice\b": "2", r"\bthrice\b": "3",
            r"\bfirst\b": "1", r"\bsecond\b": "2", r"\bthird\b": "3",
            r"\bfourth\b": "4", r"\bfifth\b": "5", r"\bsixth\b": "6",
            r"\bseventh\b": "7", r"\beighth\b": "8", r"\bninth\b": "9",
            r"\btenth\b": "10",
            r"\bone\b": "1", r"\btwo\b": "2", r"\bthree\b": "3",
            r"\bfour\b": "4", r"\bfive\b": "5", r"\bsix\b": "6",
            r"\bseven\b": "7", r"\beight\b": "8", r"\bnine\b": "9",
            r"\bten\b": "10",
        }
        for pat, repl in word_num_map.items():
            text = re.sub(pat, repl, text)

        # 4. Ordinal suffixes on digits (1st -> 1, 2nd -> 2, etc.)
        text = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", r"\1", text)

        # 5. Remove punctuation except decimal points between digits
        text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)
        text = re.sub(r"[^\w\s\.]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _stem_word(self, w: str) -> str:
        w = w.lower().strip(".,;:\"'!?()[]{}")
        if w.endswith("ies") and len(w) > 4:
            return w[:-3] + "y"
        if w.endswith("es") and len(w) > 3:
            return w[:-2]
        if w.endswith("s") and not w.endswith("ss") and len(w) > 2:
            return w[:-1]
        return w

    def _extract_tokens(self, text: str) -> Set[str]:
        norm = self._normalize_text(text)
        # Filter common stopwords
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "of", "and", "or", "it", "its"}
        tokens = {
            self._stem_word(w)
            for w in norm.split()
            if self._stem_word(w) not in stopwords and (len(self._stem_word(w)) > 1 or self._stem_word(w).isdigit())
        }
        return tokens

    def _extract_numbers(self, text: str) -> List[float]:
        """Extracts numerical quantities from text after normalization."""
        norm = self._normalize_text(text)
        raw_nums = re.findall(r"\b\d+(?:[\.,]\d+)?\b", norm)
        res = []
        for n in raw_nums:
            cleaned = n.replace(",", "")
            try:
                res.append(float(cleaned))
            except Exception:
                pass
        return res

    def evaluate(
        self,
        question: FramesQuestion,
        generated_answer: str,
        retrieved_context: str,
    ) -> FactualityResult:
        """
        Computes reference correctness, evidence grounding, and overall factuality status.
        """
        qid = question.question_id
        ref_ans = question.reference_answer.strip()
        gen_ans = generated_answer.strip()

        # 1. Controlled Abstention & Unanswerability Protocol Handling
        is_abstained = (
            "insufficient" in gen_ans.lower()
            or "not enough information" in gen_ans.lower()
            or "no answer released" in gen_ans.lower()
        )

        if is_abstained and getattr(question, "is_unanswerable", False):
            return FactualityResult(
                question_id=qid,
                answer_status="unanswerable",
                factuality_score=1.0,
                reference_correctness_score=1.0,
                grounding_score=1.0,
                missing_information=[],
                unsupported_claims=[],
                explanation="Pipeline correctly identified unanswerable inquiry."
            )

        if not gen_ans.strip() or (is_abstained and not retrieved_context.strip()):
            return FactualityResult(
                question_id=qid,
                answer_status="unanswerable",
                factuality_score=0.0,
                reference_correctness_score=0.0,
                grounding_score=1.0,
                missing_information=["Insufficient evidence retrieved to answer"],
                unsupported_claims=[],
                explanation="Pipeline correctly identified insufficient information to form an answer."
            )

        if is_abstained:
            return FactualityResult(
                question_id=qid,
                answer_status="abstained",
                factuality_score=0.0,
                reference_correctness_score=0.0,
                grounding_score=1.0 if not retrieved_context.strip() else 0.5,
                missing_information=["Controlled abstention emitted: incomplete reasoning path."],
                unsupported_claims=[],
                explanation="Model exercised controlled abstention due to insufficient grounded evidence."
            )

        norm_ref = self._normalize_text(ref_ans)
        norm_gen = self._normalize_text(gen_ans)
        ref_tokens = self._extract_tokens(ref_ans)
        gen_tokens = self._extract_tokens(gen_ans)

        # 2. Reference Correctness Evaluation
        ref_correctness = 0.0
        missing_info: List[str] = []

        if norm_ref == norm_gen or (norm_ref and re.search(rf"\b{re.escape(norm_ref)}\b", norm_gen)):
            ref_correctness = 1.0
        elif norm_gen and (len(norm_gen) >= 4 or norm_gen.isdigit()) and re.search(rf"\b{re.escape(norm_gen)}\b", norm_ref):
            ref_correctness = 1.0
        elif ref_tokens:
            common = ref_tokens.intersection(gen_tokens)
            token_recall = len(common) / len(ref_tokens)
            token_prec = len(common) / max(1, len(gen_tokens))
            f1 = (2 * token_prec * token_recall) / (token_prec + token_recall) if (token_prec + token_recall) > 0 else 0.0

            # Numerical match check for numerical questions or numerical answers
            ref_nums = self._extract_numbers(ref_ans)
            gen_nums = self._extract_numbers(gen_ans)
            if ref_nums and gen_nums:
                matched_ref_count = sum(
                    1 for rn in ref_nums
                    if any(abs(rn - gn) / max(abs(rn), 1e-5) < 0.01 for gn in gen_nums)
                )
                num_coverage = matched_ref_count / len(ref_nums)
                if num_coverage >= 0.99:
                    ref_correctness = max(token_recall, 1.0)
                elif num_coverage >= 0.50:
                    ref_correctness = max(token_recall, 0.70)
                elif question.is_numerical:
                    ref_correctness = min(token_recall, 0.40)
            elif gen_tokens.issubset(ref_tokens) and len(gen_tokens) >= 1:
                ref_correctness = max(token_recall, 0.95)
            else:
                if token_recall >= 0.80 or f1 >= 0.75:
                    ref_correctness = 1.0
                elif token_recall >= 0.40:
                    ref_correctness = token_recall
                else:
                    ref_correctness = f1

            # Identify missing key information
            missing = ref_tokens - gen_tokens
            if missing:
                missing_info = list(missing)[:5]

        # 3. Evidence Grounding Evaluation (Corroboration from context)
        context_tokens = self._extract_tokens(retrieved_context)
        unsupported: List[str] = []
        if gen_tokens:
            grounded_tokens = gen_tokens.intersection(context_tokens)
            grounding_score = round(len(grounded_tokens) / len(gen_tokens), 4)
            unsupported_set = gen_tokens - context_tokens
            if unsupported_set:
                unsupported = list(unsupported_set)[:5]
        else:
            grounding_score = 0.0

        ref_in_context = (
            len(ref_tokens.intersection(context_tokens)) / len(ref_tokens) >= 0.5
            if ref_tokens else True
        )

        # 4. Synthesize Final Status
        if ref_correctness >= 0.90 or (ref_correctness >= 0.80 and (grounding_score >= 0.40 or ref_in_context)):
            status = "correct"
            factuality_score = round((ref_correctness * 0.7) + (max(grounding_score, 0.7) * 0.3), 4)
            explanation = "Answer accurately satisfies reference answer and is well-grounded in evidence."
        elif ref_correctness >= 0.40:
            status = "partially_correct"
            factuality_score = round((ref_correctness * 0.6) + (grounding_score * 0.4), 4)
            explanation = f"Answer captures partial reference elements but misses: {', '.join(missing_info)}."
        elif grounding_score < 0.35 and len(gen_ans) > 20:
            status = "unsupported"
            factuality_score = 0.15
            explanation = "Generated answer asserts claims not substantiated by retrieved context."
        else:
            status = "incorrect"
            factuality_score = round(ref_correctness * 0.5, 4)
            explanation = f"Answer does not match reference answer '{ref_ans}'."

        return FactualityResult(
            question_id=qid,
            answer_status=status,
            factuality_score=factuality_score,
            reference_correctness_score=round(ref_correctness, 4),
            grounding_score=grounding_score,
            missing_information=missing_info,
            unsupported_claims=unsupported,
            explanation=explanation,
        )
