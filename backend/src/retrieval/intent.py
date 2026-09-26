"""
Retrieval Intent Classifier & Channel Weight Allocator
======================================================
Dynamically classifies query intent into retrieval modalities (Dense, Sparse BM25, Graph)
and dynamically redistributes channel weight budgets based on candidate signal variance.
"""

from __future__ import annotations

import re
from typing import List, Tuple, Dict, Any


def classify_retrieval_intent(query: str) -> Tuple[str, List[float]]:
    """
    Dynamically classifies query intent into retrieval modalities:
    - NUMERICAL_OR_FACTUAL: High density of digits, dates, currencies, schedule/census/budget keywords.
      Weights: [Dense: 0.30, Sparse BM25: 0.50, Neo4j Graph: 0.20]
    - RELATIONAL_OR_LINEAGE: Entity hierarchies, directors, organizations, faculties, dependencies.
      Weights: [Dense: 0.25, Sparse BM25: 0.20, Neo4j Graph: 0.55]
    - THEMATIC_OR_OVERVIEW: Broad summaries, conceptual research, comparative narratives.
      Weights: [Dense: 0.55, Sparse BM25: 0.25, Neo4j Graph: 0.20]
    """
    q_lower = query.lower()

    # 1. Numerical & Quantitative indicators
    has_numbers = bool(re.search(r"\b\d+(?:\.\d+)?%?\b", query))
    has_financial = any(k in q_lower for k in [
        "expenditure", "revenue", "budget", "cost", "crore", "lakh", "million", "billion",
        "schedule", "fee", "penalty", "population", "census", "growth", "metric", "count",
        "how many", "total", "percentage", "amount", "rupees", "inr", "$", "₹", "€"
    ])
    if has_financial or (has_numbers and ("how" in q_lower or "what" in q_lower or "which" in q_lower)):
        return "NUMERICAL_OR_FACTUAL", [0.30, 0.50, 0.20]

    # 2. Relational & Multi-hop Lineage indicators
    has_relational = any(k in q_lower for k in [
        "director", "dean", "faculty", "professor", "head", "department", "centre",
        "alumnus", "alumni", "founder", "incubated", "startup", "partner", "collaborat",
        "subsidiary", "who is", "who was", "affiliated", "connected", "lineage", "parent of",
        "born in", "founded by", "led by", "awarded to"
    ])
    if has_relational:
        return "RELATIONAL_OR_LINEAGE", [0.25, 0.20, 0.55]

    # 3. Default Thematic / Conceptual
    return "THEMATIC_OR_OVERVIEW", [0.55, 0.25, 0.20]


def redistribute_channel_weights(
    raw_intent_weights: List[float],
    dense_res: List[Dict[str, Any]],
    sparse_res: List[Dict[str, Any]],
    graph_res: List[Dict[str, Any]],
) -> List[float]:
    """
    Variance-based signal calibration:
    If BM25 or Graph have zero discriminative signal (e.g. out-of-domain terms),
    dynamically shifts weight budget into the dense vector channel.
    """
    dense_signal = bool(dense_res and len(dense_res) > 0)
    sparse_signal = False
    if sparse_res:
        s_scores = [float(s.get("similarity") or s.get("score") or 0.0) for s in sparse_res]
        if len(s_scores) > 1 and (max(s_scores) - min(s_scores)) > 0.01:
            sparse_signal = True
        elif len(s_scores) == 1 and s_scores[0] > 0.1:
            sparse_signal = True

    graph_signal = bool(graph_res and len(graph_res) > 0)

    w_dense, w_sparse, w_graph = raw_intent_weights
    if not sparse_signal and not graph_signal:
        w_dense = 1.0
        w_sparse = 0.0
        w_graph = 0.0
    elif not sparse_signal:
        w_dense += w_sparse * 0.75
        w_graph += w_sparse * 0.25
        w_sparse = 0.0
    elif not graph_signal:
        w_dense += w_graph * 0.75
        w_sparse += w_graph * 0.25
        w_graph = 0.0

    return [w_dense, w_sparse, w_graph]
