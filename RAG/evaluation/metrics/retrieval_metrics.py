"""
Retrieval & Ranking Metrics (Recall@K, nDCG@10, MRR@10, MAP, Reranker Diagnostics)
"""

from __future__ import annotations
import math
from typing import List, Dict, Any, Set, Tuple


def _normalize_id(val: Any) -> str:
    return str(val).strip().lower()


def is_chunk_relevant(chunk: Dict[str, Any], gold_evidence: List[str]) -> bool:
    """Checks if a retrieved chunk matches any gold evidence identifier or text snippet."""
    if not gold_evidence:
        return False
    
    c_text = (chunk.get("text") or chunk.get("plain_text") or "").lower()
    c_id = _normalize_id(chunk.get("chunk_id") or chunk.get("id") or "")
    c_meta = chunk.get("metadata") or {}
    c_page = str(c_meta.get("primary_page") or c_meta.get("page") or "")
    c_pdf = str(c_meta.get("pdf_filename") or "").lower()

    for gold in gold_evidence:
        g_clean = gold.lower().strip()
        # Direct chunk id match
        if _normalize_id(gold) == c_id:
            return True
        # Citation match (e.g. "Page 155")
        if "page" in g_clean and c_page and f"page {c_page}" in g_clean:
            if not c_pdf or any(part in g_clean for part in c_pdf.split(".")[0].split("-")):
                return True
        # Text substring match
        if len(g_clean) > 8 and g_clean in c_text:
            return True
        # Exact keyword match
        if len(g_clean) > 4 and g_clean in c_text:
            return True

    return False


def calculate_recall_at_k(candidates: List[Dict[str, Any]], gold_evidence: List[str], k_values: List[int] = None) -> Dict[str, float]:
    """Calculates Recall@K for each K in k_values."""
    if k_values is None:
        k_values = [1, 4, 8, 10, 20]
    
    if not gold_evidence:
        return {f"recall@{k}": 1.0 for k in k_values}

    results = {}
    for k in k_values:
        top_k = candidates[:k]
        hit = any(is_chunk_relevant(c, gold_evidence) for c in top_k)
        results[f"recall@{k}"] = 1.0 if hit else 0.0

    return results


def calculate_mrr(candidates: List[Dict[str, Any]], gold_evidence: List[str], max_k: int = 10) -> float:
    """Mean Reciprocal Rank of first relevant passage up to max_k."""
    if not gold_evidence:
        return 1.0

    for rank, c in enumerate(candidates[:max_k], start=1):
        if is_chunk_relevant(c, gold_evidence):
            return 1.0 / rank
    return 0.0


def calculate_ndcg_at_k(candidates: List[Dict[str, Any]], gold_evidence: List[str], k: int = 10) -> float:
    """Normalized Discounted Cumulative Gain at K."""
    if not gold_evidence:
        return 1.0

    dcg = 0.0
    for rank, c in enumerate(candidates[:k], start=1):
        rel = 1.0 if is_chunk_relevant(c, gold_evidence) else 0.0
        if rel > 0:
            dcg += (2.0 ** rel - 1.0) / math.log2(rank + 1)

    # Ideal DCG with 1 relevant item at rank 1
    idcg = (2.0 ** 1.0 - 1.0) / math.log2(2.0)
    return dcg / idcg if idcg > 0 else 0.0


def calculate_reranker_diagnostics(
    pre_rerank_candidates: List[Dict[str, Any]],
    post_rerank_candidates: List[Dict[str, Any]],
    gold_evidence: List[str],
    cutoff: int = 4
) -> Dict[str, Any]:
    """
    Evaluates false promotion and false suppression rates across reranker stage.
    """
    if not gold_evidence:
        return {"false_promotion": False, "false_suppression": False, "pre_rank": -1, "post_rank": -1}

    # Find rank of first gold candidate pre and post
    pre_rank = -1
    for r, c in enumerate(pre_rerank_candidates, start=1):
        if is_chunk_relevant(c, gold_evidence):
            pre_rank = r
            break

    post_rank = -1
    for r, c in enumerate(post_rerank_candidates, start=1):
        if is_chunk_relevant(c, gold_evidence):
            post_rank = r
            break

    # False suppression: Gold was in top cutoff pre-rerank, but dropped below cutoff post-rerank
    false_suppression = (pre_rank != -1 and pre_rank <= cutoff and (post_rank == -1 or post_rank > cutoff))

    # False promotion: Top item post-rerank is irrelevant while a relevant item existed in pre-rerank
    false_promotion = (
        len(post_rerank_candidates) > 0 and 
        not is_chunk_relevant(post_rerank_candidates[0], gold_evidence) and 
        pre_rank != -1
    )

    return {
        "false_promotion": false_promotion,
        "false_suppression": false_suppression,
        "rank_pre_rerank": pre_rank,
        "rank_post_rerank": post_rank,
    }
