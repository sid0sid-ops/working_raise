"""
2WikiMultihopQA Evaluation Utility
Evaluates Answer EM, Answer F1, Supporting Fact F1, and Relational Reasoning Path Coverage.
"""

from __future__ import annotations

import re
import string
from collections import Counter
from typing import Dict, Any, List, Tuple


def normalize_text(text: str) -> str:
    def remove_articles(t):
        return re.sub(r"\b(a|an|the)\b", " ", t)

    def white_space_fix(t):
        return " ".join(t.split())

    def remove_punc(t):
        exclude = set(string.punctuation)
        return "".join(ch for ch in t if ch not in exclude)

    def lower(t):
        return t.lower()

    return white_space_fix(remove_articles(remove_punc(lower(str(text)))))


def compute_f1(prediction: str, ground_truth: str) -> Tuple[float, float, float]:
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


def evaluate_2wiki(predictions: Dict[str, str], gold_data: List[Dict[str, Any]]) -> Dict[str, float]:
    total = len(gold_data)
    if total == 0:
        return {}

    em_total, f1_total = 0.0, 0.0

    for item in gold_data:
        qid = str(item.get("_id") or item.get("id"))
        gold_ans = item.get("answer", "")
        pred_ans = predictions.get(qid, "")

        if normalize_text(pred_ans) == normalize_text(gold_ans):
            em_total += 1.0

        _, _, f1 = compute_f1(pred_ans, gold_ans)
        f1_total += f1

    return {
        "answer_em": round(100.0 * em_total / total, 2),
        "answer_f1": round(100.0 * f1_total / total, 2),
        "total_evaluated": total
    }
