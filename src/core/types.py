"""
RAISE Core Domain Contracts & Types
Defines canonical data contracts shared across features without business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class QueryMode(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    EXPERT = "expert"
    RESEARCH = "research"


@dataclass
class Citation:
    document_id: str
    filename: str
    page_number: int
    printed_page: Optional[int] = None
    chunk_id: Optional[str] = None
    section_heading: str = ""
    excerpt: str = ""
    relevance_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "page_number": self.page_number,
            "printed_page": self.printed_page,
            "chunk_id": self.chunk_id,
            "section_heading": self.section_heading,
            "excerpt": self.excerpt,
            "relevance_score": round(self.relevance_score, 4),
        }


@dataclass
class AnswerContract:
    answer: str
    citations: List[Citation] = field(default_factory=list)
    subgraph: Dict[str, Any] = field(default_factory=lambda: {"nodes": [], "edges": []})
    confidence_score: float = 1.0
    verified: bool = True
    grounding_score: float = 1.0
    mode: str = "fast"
    reasoning_trajectory: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": [c.to_dict() if hasattr(c, "to_dict") else c for c in self.citations],
            "subgraph": self.subgraph,
            "confidence_score": round(self.confidence_score, 3),
            "verified": self.verified,
            "grounding_score": round(self.grounding_score, 3),
            "mode": self.mode,
            "reasoning_trajectory": self.reasoning_trajectory,
        }
