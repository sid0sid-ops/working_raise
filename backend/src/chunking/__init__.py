"""
Graph-Guided Adaptive Hierarchical Chunking (GGAHC) Package.
Re-exports core models, configurations, and the master AdaptiveChunkingPipeline.
"""

from __future__ import annotations

from .config import ChunkingConfig
from .diagnostics import ChunkingDiagnosticsEngine
from .models import (
    AdaptiveChunk,
    BoundaryDecision,
    BoundaryExplanation,
    CandidateUnit,
    ChunkingDiagnosticReport,
    ChunkLevel,
    Proposition,
    StructuralUnit,
)
from .table_chunker import (
    TablePreservingChunker,
    DoclingTablePreservingChunker,
    MarkdownTablePreservingChunker,
)
from .pipeline import AdaptiveChunkingPipeline
from .rust_bridge import (
    assemble_hierarchy_rust,
    bm25_search_rust,
    claim_fingerprint_rust,
    evaluate_boundaries_compact_rust,
    evaluate_boundaries_rust,
    get_rust_backend_type,
    is_rust_engine_available,
    normalize_text_rust,
    rank_candidates_rust,
    reciprocal_rank_fusion_rust,
)


__all__ = [
    "AdaptiveChunkingPipeline",
    "TablePreservingChunker",
    "DoclingTablePreservingChunker",
    "MarkdownTablePreservingChunker",
    "ChunkingConfig",
    "AdaptiveChunk",
    "CandidateUnit",
    "StructuralUnit",
    "Proposition",
    "ChunkLevel",
    "BoundaryDecision",
    "BoundaryExplanation",
    "ChunkingDiagnosticReport",
    "ChunkingDiagnosticsEngine",
    "is_rust_engine_available",
    "get_rust_backend_type",
    "evaluate_boundaries_rust",
    "assemble_hierarchy_rust",
    "reciprocal_rank_fusion_rust",
    "bm25_search_rust",
    "rank_candidates_rust",
    "normalize_text_rust",
    "claim_fingerprint_rust",
]

