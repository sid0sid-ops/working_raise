"""
QA Accuracy, Token F1, Numeric Integrity & Abstention Classification
"""

from __future__ import annotations

import re
import string
from collections import Counter
from typing import Dict, Any, List, Optional, Tuple


def normalize_answer(s: str) -> str:
    """Lowercases, removes punctuation, articles, and extra whitespace."""
    def remove_articles(text):
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    if not s:
        return ""
    return white_space_fix(remove_articles(remove_punc(lower(str(s)))))


def compute_exact_match(prediction: str, ground_truth: str) -> bool:
    """Exact string match after normalization."""
    norm_p = normalize_answer(prediction)
    norm_g = normalize_answer(ground_truth)
    if not norm_g:
        return norm_p == ""
    return norm_p == norm_g or norm_g in norm_p


def compute_token_f1(prediction: str, ground_truth: str) -> Tuple[float, float, float]:
    """Computes (precision, recall, f1) over normalized token bags."""
    norm_p = normalize_answer(prediction)
    norm_g = normalize_answer(ground_truth)

    pred_tokens = norm_p.split()
    gold_tokens = norm_g.split()

    if not gold_tokens:
        return (1.0, 1.0, 1.0) if not pred_tokens else (0.0, 0.0, 0.0)
    if not pred_tokens:
        return 0.0, 0.0, 0.0

    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())

    if num_same == 0:
        return 0.0, 0.0, 0.0

    precision = 1.0 * num_same / len(pred_tokens)
    recall = 1.0 * num_same / len(gold_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return precision, recall, f1


def extract_numbers(text: str) -> List[str]:
    """Extracts numbers, formatted currencies, and percentages."""
    cleaned = re.sub(r"[,\s]", "", text)
    # Match numbers with optional decimals
    return re.findall(r"\b\d+(?:\.\d+)?\b", cleaned)


def compute_numeric_exact_match(prediction: str, ground_truth: str, required_keywords: List[str] = None) -> bool:
    """Checks whether key numbers and financial metrics in ground truth appear in prediction."""
    # 1. Check required keywords
    if required_keywords:
        pred_clean = prediction.lower()
        matched = sum(1 for kw in required_keywords if kw.lower() in pred_clean)
        if matched / len(required_keywords) >= 0.70:
            return True

    # 2. Extract raw numbers
    gold_nums = extract_numbers(ground_truth)
    if not gold_nums:
        return True

    pred_nums = set(extract_numbers(prediction))
    hits = sum(1 for n in gold_nums if n in pred_nums)
    return (hits / len(gold_nums)) >= 0.75


def is_abstention(text: str) -> bool:
    """Detects whether model output signifies an intentional abstention / insufficient evidence refusal."""
    refusal_keywords = [
        "insufficient_evidence",
        "insufficient evidence",
        "cannot answer",
        "unable to verify",
        "could not verify",
        "not mentioned in the provided",
        "no evidence found",
        "does not contain information",
        "do not contain information",
        "does not contain",
        "do not contain",
        "not available in the documents",
        "not available",
        "no records",
        "contains no records",
        "not registered in the active document library",
        "outside the scope",
        "no matching verified statements",
        "could not find",
        "unverified",
    ]
    t_clean = text.lower()
    return any(kw in t_clean for kw in refusal_keywords)


def classify_outcome(prediction: str, ground_truth: str, is_unanswerable: bool, em: bool, f1: float, num_match: bool = False) -> str:
    """
    Classifies the QA outcome into 5 distinct categories:
    - CORRECT_ANSWER
    - CORRECT_ABSTENTION
    - UNNECESSARY_ABSTENTION
    - UNSUPPORTED_ANSWER
    - WRONG_ANSWER
    """
    abstained = is_abstention(prediction)

    if is_unanswerable:
        if abstained:
            return "CORRECT_ABSTENTION"
        else:
            return "UNSUPPORTED_ANSWER"  # Fabricated an answer to an unanswerable question
    else:
        if abstained:
            return "UNNECESSARY_ABSTENTION"  # Refused a question that was answerable
        elif em or f1 >= 0.60 or (num_match and f1 >= 0.20):
            return "CORRECT_ANSWER"
        else:
            return "WRONG_ANSWER"
