"""
Configuration Dataclasses and Defaults for Graph-Guided Adaptive Hierarchical Chunking (GGAHC).
Supports flexible parameter tuning, strategy selection, ablation switches, and hardware-conscious constraints.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChunkingConfig:
    # Strategy mode: 'fixed' | 'recursive' | 'semantic' | 'structure_aware' | 'hierarchical' | 'proposition' | 'contextual' | 'gga_hybrid'
    strategy: str = "gga_hybrid"

    # Token constraints for child chunks
    min_child_tokens: int = 150
    target_child_tokens: int = 250
    max_child_tokens: int = 350

    # Token constraints for parent chunks
    min_parent_tokens: int = 450
    target_parent_tokens: int = 800
    max_parent_tokens: int = 1400

    # Semantic segmentation thresholds
    semantic_similarity_threshold: float = 0.65
    sentence_similarity_window: int = 3

    # Graph-Guided Boundary Score Weights:
    # BoundaryScore(A, B) =
    #   w_semantic * SemanticDiscontinuity
    # + w_structural * StructuralBoundaryStrength
    # + w_topic * TopicTransition
    # - w_entity * EntityContinuity
    # - w_relation * RelationshipContinuity
    # - w_graph_conn * GraphConnectivity
    # - w_community * CommunityContinuity
    # - w_cross_sec * CrossSectionDependency
    weight_semantic_discontinuity: float = 1.0
    weight_structural_boundary: float = 1.2
    weight_topic_transition: float = 1.0
    weight_entity_continuity: float = 1.4
    weight_relationship_continuity: float = 1.5
    weight_graph_connectivity: float = 1.2
    weight_community_continuity: float = 1.1
    weight_cross_section: float = 0.8

    # Decision thresholds
    split_threshold: float = 0.60   # Score above this -> SPLIT
    merge_threshold: float = -0.20  # Score below this -> MERGE
    merge_semantic_similarity_threshold: float = 0.82  # Required semantic similarity to permit merge
    merge_min_entity_cooccurrence: float = 0.35        # Required entity overlap to permit merge

    # Feature toggles
    enable_propositions: bool = True
    enable_contextualization: bool = True
    enable_late_chunking: bool = False  # Bounded token pooling if supported
    enable_parent_child: bool = True
    enable_tables: bool = True
    enable_figures: bool = True
    enable_community_detection: bool = True

    # Hardware & batch limits (adjust based on available GPU VRAM or CPU)
    batch_size: int = 32
    max_late_chunk_tokens: int = 4096
    device: str = "cuda"

    # Strict Mode & Anti-Gimmick Controls
    strict_mode: bool = field(default_factory=lambda: os.getenv("GGAHC_STRICT_MODE", "true").lower() in ("1", "true", "yes"))
    enable_cross_page_continuity: bool = True
    enable_list_cohesion: bool = True
    enable_evidence_bundles: bool = True

    # Signal Validity & Minimum Evidence Thresholds
    min_content_words_for_semantic: int = 3
    min_entities_for_continuity: int = 1
    min_relations_for_continuity: int = 1
    min_graph_nodes_for_connectivity: int = 1

    # Ablation Flags (for research benchmarks)
    ablation_disable_entity_continuity: bool = False
    ablation_disable_relationship_continuity: bool = False
    ablation_disable_community_continuity: bool = False
    ablation_disable_propositions: bool = False
    ablation_disable_contextualization: bool = False
    ablation_disable_hierarchical: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChunkingConfig:
        valid_keys = set(cls.__annotations__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
