"""
RAISE NIAH Benchmark — Chunking Simulator
Simulates and evaluates different chunking configurations:
  - Chunk Size (e.g. 128, 256, 450, 512, 1024 words)
  - Chunk Overlap (e.g. 0%, 10%, 20%, 30%)
Tracks gold chunk IDs and detects boundary fragmentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .corpus_builder import AssembledCorpus


@dataclass
class SimulatedChunk:
    chunk_id: str
    chunk_index: int
    text: str
    word_count: int
    char_start: int
    char_end: int
    contains_needle: bool = False
    needle_overlap_ratio: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "word_count": self.word_count,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "contains_needle": self.contains_needle,
            "needle_overlap_ratio": round(self.needle_overlap_ratio, 4),
            "metadata": self.metadata,
        }


@dataclass
class ChunkedCorpus:
    corpus_id: str
    chunk_size: int
    chunk_overlap: float
    chunks: List[SimulatedChunk]
    gold_chunk_ids: List[str]
    primary_gold_chunk_id: Optional[str]
    needle_fragmented: bool
    total_chunks: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "corpus_id": self.corpus_id,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "total_chunks": self.total_chunks,
            "gold_chunk_ids": self.gold_chunk_ids,
            "primary_gold_chunk_id": self.primary_gold_chunk_id,
            "needle_fragmented": self.needle_fragmented,
            "chunks_summary": [c.to_dict() for c in self.chunks],
        }


class ChunkingSimulator:
    """
    Parametric chunking simulator supporting arbitrary chunk size and overlap sweeps.
    """

    @staticmethod
    def chunk_corpus(
        corpus: AssembledCorpus,
        chunk_size: int = 450,
        chunk_overlap: float = 0.0,
        strategy: str = "sliding_words",
    ) -> ChunkedCorpus:
        """
        Chunks the assembled corpus according to specified parameters.
        chunk_overlap: fractional overlap (e.g. 0.10 for 10% overlap).
        """
        overlap_words = int(round(chunk_size * max(0.0, min(0.5, float(chunk_overlap)))))
        step_words = max(1, chunk_size - overlap_words)

        full_text = corpus.full_text
        words = full_text.split()
        total_words = len(words)

        chunks: List[SimulatedChunk] = []
        gold_chunk_ids: List[str] = []
        needle_char_start = corpus.needle_char_start
        needle_char_end = corpus.needle_char_end
        needle_len = max(1, needle_char_end - needle_char_start)

        start_word_idx = 0
        chunk_idx = 0

        # Word-to-character map for fast offset tracking
        # Approximate char positions from text tokens
        cur_char = 0
        word_spans = []
        for w in words:
            w_start = full_text.find(w, cur_char)
            w_end = w_start + len(w)
            word_spans.append((w_start, w_end))
            cur_char = w_end

        best_gold_ratio = 0.0
        primary_gold_id = None

        while start_word_idx < total_words:
            end_word_idx = min(start_word_idx + chunk_size, total_words)
            chunk_words = words[start_word_idx:end_word_idx]
            chunk_text = " ".join(chunk_words)

            c_start = word_spans[start_word_idx][0] if start_word_idx < len(word_spans) else 0
            c_end = word_spans[end_word_idx - 1][1] if end_word_idx - 1 < len(word_spans) else len(full_text)

            # Check overlap with needle span
            overlap_start = max(c_start, needle_char_start)
            overlap_end = min(c_end, needle_char_end)
            overlap_chars = max(0, overlap_end - overlap_start)
            overlap_ratio = overlap_chars / needle_len

            cid = f"{corpus.corpus_id}_c{chunk_idx:04d}"
            contains_needle = overlap_ratio >= 0.50 or corpus.needle_case.is_answer_in_text(chunk_text)

            chunk_obj = SimulatedChunk(
                chunk_id=cid,
                chunk_index=chunk_idx,
                text=chunk_text,
                word_count=len(chunk_words),
                char_start=c_start,
                char_end=c_end,
                contains_needle=contains_needle,
                needle_overlap_ratio=overlap_ratio,
                metadata={
                    "doc_id": corpus.corpus_id,
                    "pdf_filename": f"{corpus.corpus_id}.pdf",
                    "primary_page": (chunk_idx // 2) + 1,
                    "heading": f"Section {chunk_idx + 1}",
                    "token_estimate": len(chunk_words),
                },
            )
            chunks.append(chunk_obj)

            if contains_needle:
                gold_chunk_ids.append(cid)
                if overlap_ratio > best_gold_ratio:
                    best_gold_ratio = overlap_ratio
                    primary_gold_id = cid

            chunk_idx += 1
            start_word_idx += step_words

            # Terminate if end of document is reached
            if end_word_idx >= total_words:
                break

        # Fallback if needle was not detected due to spacing
        if not gold_chunk_ids:
            for c in chunks:
                if corpus.needle_case.expected_answer.lower() in c.text.lower():
                    c.contains_needle = True
                    gold_chunk_ids.append(c.chunk_id)
                    primary_gold_id = c.chunk_id
                    break

        needle_fragmented = len(gold_chunk_ids) > 1

        return ChunkedCorpus(
            corpus_id=corpus.corpus_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunks=chunks,
            gold_chunk_ids=gold_chunk_ids,
            primary_gold_chunk_id=primary_gold_id,
            needle_fragmented=needle_fragmented,
            total_chunks=len(chunks),
        )
