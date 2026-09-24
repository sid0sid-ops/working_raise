"""
MuSiQue Evaluation Utility
Evaluates 2-hop, 3-hop, and 4-hop multi-hop reasoning and contrast unanswerability handling.
"""

from __future__ import annotations

import re
import string
from collections import Counter, defaultdict
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


def evaluate_musique(predictions: Dict[str, str], gold_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates MuSiQue predictions stratified across 2-hop, 3-hop, and 4-hop questions,
    and measures unanswerable / unsupported answer rate.
    """
    total = len(gold_data)
    if total == 0:
        return {}

    overall_em, overall_f1 = 0.0, 0.0
    hop_stats = defaultdict(lambda: {"em": 0.0, "f1": 0.0, "count": 0})
    unanswerable_total = 0
    safe_abstentions = 0
    unsupported_answers = 0

    for item in gold_data:
        qid = str(item.get("id"))
        gold_ans = item.get("answer", "")
        pred_ans = predictions.get(qid, "")
        hop_count = item.get("hop_count", 2)
        is_answerable = item.get("answerable", True)

        norm_pred = normalize_text(pred_ans)
        norm_gold = normalize_text(gold_ans)
        
        is_abstention = any(kw in pred_ans.lower() for kw in ["insufficient", "cannot answer", "unable to verify", "no evidence"])

        if not is_answerable:
            unanswerable_total += 1
            if is_abstention:
                safe_abstentions += 1
            else:
                unsupported_answers += 1
            continue

        em = 1.0 if (norm_pred == norm_gold or (norm_gold and norm_gold in norm_pred)) else 0.0
        _, _, f1 = compute_f1(pred_ans, gold_ans)

        overall_em += em
        overall_f1 += f1

        hop_stats[hop_count]["em"] += em
        hop_stats[hop_count]["f1"] += f1
        hop_stats[hop_count]["count"] += 1

    ans_count = total - unanswerable_total
    results = {
        "overall_em": round(100.0 * overall_em / max(ans_count, 1), 2),
        "overall_f1": round(100.0 * overall_f1 / max(ans_count, 1), 2),
        "safe_abstention_rate": round(100.0 * safe_abstentions / max(unanswerable_total, 1), 2) if unanswerable_total > 0 else 100.0,
        "unsupported_answer_rate": round(100.0 * unsupported_answers / max(unanswerable_total, 1), 2) if unanswerable_total > 0 else 0.0,
        "total_evaluated": total,
        "answerable_count": ans_count,
        "unanswerable_count": unanswerable_total,
    }

    # Stratified per-hop metrics
    for hop, st in sorted(hop_stats.items()):
        c = max(st["count"], 1)
        results[f"hop_{hop}_em"] = round(100.0 * st["em"] / c, 2)
        results[f"hop_{hop}_f1"] = round(100.0 * st["f1"] / c, 2)
        results[f"hop_{hop}_count"] = st["count"]

    return results
