"""
Official HotpotQA Evaluation Utility (hotpot_evaluate_v1.py)
Source: https://github.com/hotpotqa/hotpot/blob/master/hotpot_evaluate_v1.py
Calculates official Answer EM, Answer F1, Supporting Fact Precision/Recall/F1, and Joint EM/F1.
"""

from __future__ import annotations

import sys
import re
import string
from collections import Counter
from typing import Dict, Any, List, Tuple


def normalize_answer(s: str) -> str:
    def remove_articles(text):
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def f1_score(prediction: str, ground_truth: str) -> Tuple[float, float, float]:
    normalized_prediction = normalize_answer(prediction)
    normalized_ground_truth = normalize_answer(ground_truth)

    ZERO_METRIC = (0.0, 0.0, 0.0)

    if normalized_prediction in ["yes", "no", "noanswer"] and normalized_prediction != normalized_ground_truth:
        return ZERO_METRIC
    if normalized_ground_truth in ["yes", "no", "noanswer"] and normalized_prediction != normalized_ground_truth:
        return ZERO_METRIC

    prediction_tokens = normalized_prediction.split()
    ground_truth_tokens = normalized_ground_truth.split()
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return ZERO_METRIC
    precision = 1.0 * num_same / len(prediction_tokens)
    recall = 1.0 * num_same / len(ground_truth_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return precision, recall, f1


def exact_match_score(prediction: str, ground_truth: str) -> bool:
    return normalize_answer(prediction) == normalize_answer(ground_truth)


def update_sp(prediction: List[Tuple[str, int]], gold: List[Tuple[str, int]]) -> Tuple[float, float, float]:
    """Computes precision, recall, and F1 over supporting fact sentence pairs (title, sent_id)."""
    cur_sp_pred = set(map(tuple, prediction))
    gold_sp_set = set(map(tuple, gold))

    tp = len(cur_sp_pred & gold_sp_set)
    fp = len(cur_sp_pred - gold_sp_set)
    fn = len(gold_sp_set - cur_sp_pred)

    prec = 1.0 * tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = 1.0 * tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * recall / (prec + recall) if (prec + recall) > 0 else 0.0
    return prec, recall, f1


def evaluate_hotpot(prediction_file_or_data: Dict[str, Any], gold_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    prediction_file_or_data format:
    {
      "answer": {qid: answer_string, ...},
      "sp": {qid: [[title, sent_id], ...], ...}
    }
    """
    answers = prediction_file_or_data.get("answer", {})
    sp_preds = prediction_file_or_data.get("sp", {})

    total = len(gold_data)
    if total == 0:
        return {}

    em, f1, prec, recall = 0.0, 0.0, 0.0, 0.0
    sp_em, sp_f1, sp_prec, sp_recall = 0.0, 0.0, 0.0, 0.0
    joint_em, joint_f1 = 0.0, 0.0

    for item in gold_data:
        qid = item["_id"]
        gold_ans = item["answer"]
        gold_sp = item.get("supporting_facts", [])

        # Answer metrics
        pred_ans = answers.get(qid, "")
        cur_em = exact_match_score(pred_ans, gold_ans)
        cur_prec, cur_recall, cur_f1 = f1_score(pred_ans, gold_ans)
        em += float(cur_em)
        f1 += cur_f1
        prec += cur_prec
        recall += cur_recall

        # Supporting facts metrics
        cur_sp = sp_preds.get(qid, [])
        cur_sp_prec, cur_sp_rec, cur_sp_f1 = update_sp(cur_sp, gold_sp)
        cur_sp_em = float(cur_sp_rec == 1.0 and cur_sp_prec == 1.0)
        sp_em += cur_sp_em
        sp_f1 += cur_sp_f1
        sp_prec += cur_sp_prec
        sp_recall += cur_sp_rec

        # Joint metrics
        joint_em += float(cur_em and cur_sp_em)
        joint_f1 += cur_f1 * cur_sp_f1

    return {
        "answer_em": round(100.0 * em / total, 2),
        "answer_f1": round(100.0 * f1 / total, 2),
        "answer_prec": round(100.0 * prec / total, 2),
        "answer_recall": round(100.0 * recall / total, 2),
        "sp_em": round(100.0 * sp_em / total, 2),
        "sp_f1": round(100.0 * sp_f1 / total, 2),
        "sp_prec": round(100.0 * sp_prec / total, 2),
        "sp_recall": round(100.0 * sp_recall / total, 2),
        "joint_em": round(100.0 * joint_em / total, 2),
        "joint_f1": round(100.0 * joint_f1 / total, 2),
        "total_evaluated": total,
    }
