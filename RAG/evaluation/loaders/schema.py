"""
Canonical Data Models for Evaluation Questions & Cases
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class EvalQuestion:
    q_id: str
    benchmark: str  # RAISE-Domain, FRAMES, NQ, HotpotQA, 2Wiki, MuSiQue, BEIR, TREC-DL
    dataset: str
    question: str
    tier: Optional[str] = "Tier 1"
    ground_truth_answer: Optional[str] = None
    target_document: Optional[str] = None
    page_citations: List[str] = field(default_factory=list)
    required_keywords: List[str] = field(default_factory=list)
    supporting_facts: List[str] = field(default_factory=list)
    hop_count: int = 1
    is_unanswerable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
