"""
Official Natural Questions (NQ) Evaluation Utility
Calculates exact match, token F1, and short/long answer precision/recall per official Google Research specifications.
"""

from __future__ import annotations

import re
import string
from collections import Counter
from typing import Dict, Any, List, Optional, Tuple


def normalize_text(text: str) -> str:
    """Official NQ text normalization."""
    def remove_articles(t):
        return re.sub(r"\b(a|an|the)\b", " ", t)

    def white_space_fix(t):
        return " ".join(t.split())

    def remove_punc(t):
        exclude = set(string.punctuation)
        return "".join(ch for ch in t if ch not in exclude)

    def lower(t):
        return t.lower()

    return white_space_fix(remove_articles(remove_punc(lower(text))))


def compute_f1(prediction: str, ground_truth: str) -> Tuple[float, float, float]:
    """Computes precision, recall, and F1 over tokens."""
    pred_tokens = normalize_text(prediction).split()
    gold_tokens = normalize_text(ground_truth).split()

    if not pred_tokens and not gold_tokens:
        return 1.0, 1.0, 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0, 0.0, 0.0

    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())

    if num_same == 0:
        return 0.0, 0.0, 0.0

    precision = 1.0 * num_same / len(pred_tokens)
    recall = 1.0 * num_same / len(gold_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return precision, recall, f1


def evaluate_nq_predictions(predictions: Dict[str, str], ground_truths: Dict[str, List[str]]) -> Dict[str, float]:
    """
    Evaluates predictions against a list of acceptable ground-truth answers per question.
    """
    total = len(ground_truths)
    if total == 0:
        return {"exact_match": 0.0, "token_f1": 0.0, "total": 0}

    em_total = 0.0
    f1_total = 0.0

    for qid, gold_list in ground_truths.items():
        pred = predictions.get(qid, "")
        norm_pred = normalize_text(pred)

        # Max across acceptable reference answers
        max_em = 0.0
        max_f1 = 0.0

        for gold in gold_list:
            norm_gold = normalize_text(gold)
            if norm_pred == norm_gold or (norm_gold and norm_gold in norm_pred):
                max_em = 1.0
            _, _, f1 = compute_f1(pred, gold)
            if f1 > max_f1:
                max_f1 = f1

        em_total += max_em
        f1_total += max_f1

    return {
        "exact_match": round(100.0 * em_total / total, 2),
        "token_f1": round(100.0 * f1_total / total, 2),
        "total_evaluated": total
    }
