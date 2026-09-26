"""
FRAMES Benchmark Data Schema
Defines strongly typed representations for benchmark questions, reasoning types,
and evaluation metadata.
"""

from __future__ import annotations

import re
import ast
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class ReasoningType(str, Enum):
    """Official reasoning types defined in the FRAMES benchmark."""
    MULTIPLE_CONSTRAINTS = "Multiple constraints"
    NUMERICAL_REASONING = "Numerical reasoning"
    TEMPORAL_REASONING = "Temporal reasoning"
    TABULAR_REASONING = "Tabular reasoning"
    POST_PROCESSING = "Post processing"
    MULTI_HOP = "Multi-hop"  # Inferred from multi-document requirements or multi-step links
    OTHER = "Other"


class FramesQuestion(BaseModel):
    """
    Normalized internal representation of a FRAMES benchmark example.
    Guarantees strict separation between benchmark ground-truth and retrieval engines.
    """
    question_id: str = Field(..., description="Unique question index from benchmark")
    prompt: str = Field(..., description="The multi-hop or reasoning question text")
    reference_answer: str = Field(..., description="Ground-truth reference answer (strictly quarantined)")
    reasoning_types: List[str] = Field(default_factory=list, description="Parsed official reasoning type tags")
    raw_reasoning_types: str = Field(default="", description="Original pipe-separated string from test.tsv")
    wiki_links: List[str] = Field(default_factory=list, description="List of authoritative Wikipedia source URLs")
    source_count: int = Field(default=0, description="Total unique source documents required")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional benchmark metadata")

    @classmethod
    def from_tsv_row(cls, row: Dict[str, Any]) -> FramesQuestion:
        """Parses a row from the official test.tsv file."""
        qid = str(row.get("", row.get("id", "0"))).strip()
        prompt = (row.get("Prompt") or row.get("prompt") or "").strip()
        answer = (row.get("Answer") or row.get("answer") or "").strip()
        raw_types = (row.get("reasoning_types") or "").strip()

        # Parse pipe-separated reasoning types
        if raw_types:
            r_types = [t.strip() for t in raw_types.split("|") if t.strip()]
        else:
            r_types = []

        # Parse wiki links
        links: List[str] = []
        raw_links = row.get("wiki_links", "")
        if raw_links:
            try:
                # Often formatted as string representation of a Python list
                parsed = ast.literal_eval(raw_links)
                if isinstance(parsed, list):
                    links = [str(l).strip() for l in parsed if l and str(l).strip()]
            except Exception:
                # Fallback: extract URLs via regex
                links = re.findall(r"https?://[^\s'\",]+", raw_links)

        # Also inspect individual wikipedia_link_N columns if wiki_links was empty
        if not links:
            for i in range(1, 20):
                k = f"wikipedia_link_{i}"
                if k in row and row[k] and row[k].strip():
                    links.append(row[k].strip())
                kp = f"wikipedia_link_{i}+"
                if kp in row and row[kp] and row[kp].strip():
                    links.append(row[kp].strip())

        # Deduplicate while preserving order
        seen = set()
        unique_links = []
        for l in links:
            if l not in seen:
                seen.add(l)
                unique_links.append(l)

        # Determine multi-hop attribute: if >1 wiki source is needed, it is multi-hop
        if len(unique_links) > 1 and "Multi-hop" not in r_types:
            r_types.append("Multi-hop")

        return cls(
            question_id=qid,
            prompt=prompt,
            reference_answer=answer,
            reasoning_types=r_types,
            raw_reasoning_types=raw_types,
            wiki_links=unique_links,
            source_count=len(unique_links),
            metadata={
                "link_count": len(unique_links),
                "has_answer": bool(answer),
            }
        )

    def has_reasoning_type(self, type_name: str) -> bool:
        """Checks if a reasoning category applies to this question."""
        tn_lower = type_name.lower().strip()
        return any(tn_lower in t.lower() for t in self.reasoning_types)

    @property
    def is_multihop(self) -> bool:
        return self.has_reasoning_type("multi-hop") or self.source_count > 1

    @property
    def is_numerical(self) -> bool:
        return self.has_reasoning_type("numerical")

    @property
    def is_temporal(self) -> bool:
        return self.has_reasoning_type("temporal")

    @property
    def is_tabular(self) -> bool:
        return self.has_reasoning_type("tabular")

    @property
    def is_constraint(self) -> bool:
        return self.has_reasoning_type("constraint")

    @property
    def is_post_processing(self) -> bool:
        return self.has_reasoning_type("post processing")

    @property
    def is_unanswerable(self) -> bool:
        return (
            self.has_reasoning_type("unanswerable")
            or "unanswerable" in self.reference_answer.lower()
            or "insufficient" in self.reference_answer.lower()
        )
