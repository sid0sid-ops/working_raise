"""
RAISE NIAH Benchmark — Corpus Builder
Assembles benchmark documents by injecting needles at precise fractional depths
into synthetic or academic haystacks, tracking exact character and paragraph positions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .haystack_generator import HaystackGenerator
from .needle_catalog import NeedleCase, get_needle


@dataclass
class AssembledCorpus:
    corpus_id: str
    needle_case: NeedleCase
    full_text: str
    paragraphs: List[str]
    target_words: int
    actual_words: int
    depth_requested: float
    depth_actual: float
    needle_paragraph_idx: int
    needle_char_start: int
    needle_char_end: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "corpus_id": self.corpus_id,
            "needle_id": self.needle_case.needle_id,
            "target_words": self.target_words,
            "actual_words": self.actual_words,
            "depth_requested": self.depth_requested,
            "depth_actual": round(self.depth_actual, 4),
            "needle_paragraph_idx": self.needle_paragraph_idx,
            "needle_char_start": self.needle_char_start,
            "needle_char_end": self.needle_char_end,
            "metadata": self.metadata,
        }


class CorpusBuilder:
    """
    Builds NIAH evaluation documents with precise needle depth placement.
    """

    def __init__(self, generator: Optional[HaystackGenerator] = None):
        self.generator = generator or HaystackGenerator(seed=42)

    def build_corpus(
        self,
        needle: NeedleCase | str,
        target_words: int = 5000,
        depth: float = 0.50,
        corpus_id: Optional[str] = None,
    ) -> AssembledCorpus:
        """
        Builds a full text corpus inserting the needle at the specified fractional depth.
        depth: 0.0 (top/start) <= depth <= 1.0 (bottom/end).
        """
        if isinstance(needle, str):
            needle_case = get_needle(needle)
        else:
            needle_case = needle

        # Clamp depth to valid range
        clamped_depth = max(0.0, min(1.0, float(depth)))

        # Generate base haystack paragraphs
        haystack_paragraphs = self.generator.generate_haystack(target_words=target_words)
        total_p = len(haystack_paragraphs)

        # Determine insertion paragraph index
        if clamped_depth == 0.0:
            insert_idx = 0
        elif clamped_depth == 1.0:
            insert_idx = total_p
        else:
            insert_idx = int(round(clamped_depth * total_p))
            insert_idx = min(insert_idx, total_p)

        # Format needle as natural report text (no artificial disclosure tags)
        needle_paragraph = needle_case.needle_text

        # Insert needle
        assembled_paragraphs = list(haystack_paragraphs)

        # Distribute adversarial distractors evenly across the haystack if defined
        if getattr(needle_case, "distractor_texts", None):
            num_d = len(needle_case.distractor_texts)
            step = max(1, len(assembled_paragraphs) // (num_d + 1))
            for i, d_text in enumerate(needle_case.distractor_texts):
                d_idx = min((i + 1) * step, len(assembled_paragraphs))
                assembled_paragraphs.insert(d_idx, d_text)
                if d_idx <= insert_idx:
                    insert_idx += 1

        assembled_paragraphs.insert(insert_idx, needle_paragraph)

        # Compute full text and character offsets
        full_text = "\n\n".join(assembled_paragraphs)
        needle_char_start = full_text.find(needle_case.needle_text)
        needle_char_end = needle_char_start + len(needle_case.needle_text)

        # Compute actual fractional depth based on character position
        actual_depth = needle_char_start / max(1, len(full_text) - len(needle_case.needle_text))

        total_words = len(full_text.split())
        cid = corpus_id or f"corpus_{needle_case.needle_id}_d{int(clamped_depth*100):03d}_w{target_words}"

        return AssembledCorpus(
            corpus_id=cid,
            needle_case=needle_case,
            full_text=full_text,
            paragraphs=assembled_paragraphs,
            target_words=target_words,
            actual_words=total_words,
            depth_requested=clamped_depth,
            depth_actual=actual_depth,
            needle_paragraph_idx=insert_idx,
            needle_char_start=needle_char_start,
            needle_char_end=needle_char_end,
            metadata={
                "needle_id": needle_case.needle_id,
                "needle_type": needle_case.needle_type.value,
                "query": needle_case.query,
                "expected_answer": needle_case.expected_answer,
            },
        )
