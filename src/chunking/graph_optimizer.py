"""
Temporary Knowledge Graph Construction & Boundary Optimizer (Stage 6, Stage 11, Stage 12, Stage 13).
Constructs a temporary NetworkX graph of candidate units and entities.
Calculates graph features:
  - Entity continuity / overlap
  - Relationship continuity / shared events
  - Relation density
  - Graph connectivity / min-cut resistance
  - Community membership (Louvain / connected components)
  - Cross-section dependencies
Computes the Graph-Guided Boundary Score with configurable weights and produces
an explainable BoundaryExplanation ('MERGE' | 'SPLIT' | 'PRESERVE').
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

from .config import ChunkingConfig
from .models import (
    BoundaryDecision,
    BoundaryExplanation,
    CandidateUnit,
    HardConstraintResult,
    SignalResult,
)


class TemporaryGraphBuilder:
    """
    Constructs an intermediate NetworkX bipartite / projection graph of Candidate Units and Entities.
    Used exclusively for boundary optimization and community detection before chunk finalization.
    """

    def __init__(self):
        pass

    def build_graph(self, candidates: List[CandidateUnit]) -> Any:
        if not HAS_NETWORKX:
            return None

        G = nx.Graph()

        for cand in candidates:
            cid = cand.candidate_id
            G.add_node(cid, node_type="candidate", heading=cand.heading, page=cand.page_start)

            for ent in cand.entities:
                eid = ent["id"]
                G.add_node(eid, node_type="entity", label=ent.get("label", "Entity"), name=ent.get("name", eid))
                G.add_edge(cid, eid, relation="MENTIONS")

            for rel in cand.relationships:
                sid = rel["source_id"]
                tid = rel["target_id"]
                rtype = rel.get("relation_type", "RELATED_TO")
                if sid != cid and tid != cid:
                    # Entity-to-entity edge
                    G.add_node(sid, node_type="entity")
                    G.add_node(tid, node_type="entity")
                    G.add_edge(sid, tid, relation=rtype)

        return G

    def detect_communities(self, G: Any) -> Dict[str, str]:
        """
        Detects communities across the temporary graph using Louvain or connected components.
        Returns a mapping from node_id -> community_id.
        """
        if not HAS_NETWORKX or G is None or len(G.nodes) == 0:
            return {}

        try:
            from networkx.algorithms.community import louvain_communities
            communities = louvain_communities(G, seed=42)
            node_to_comm: Dict[str, str] = {}
            for c_idx, comm in enumerate(communities, start=1):
                c_label = f"comm_{c_idx:02d}"
                for node in comm:
                    node_to_comm[str(node)] = c_label
            return node_to_comm
        except Exception:
            # Fallback to connected components
            node_to_comm = {}
            for c_idx, comp in enumerate(nx.connected_components(G), start=1):
                c_label = f"comp_{c_idx:02d}"
                for node in comp:
                    node_to_comm[str(node)] = c_label
            return node_to_comm


class HardConstraintEngine:
    """
    Evaluates immutable layout and structural constraints that strictly precede
    soft graph signal evaluation.
    Enforces deterministic boundaries for:
      - Tables (first-class isolated units)
      - Figures (first-class isolated units)
      - Cross-page continuation headers (must merge)
      - Max parent token limits (must split)
    """

    @staticmethod
    def evaluate(
        unit_a: CandidateUnit,
        unit_b: CandidateUnit,
        max_parent_tokens: int,
        enable_cross_page_continuity: bool = True,
    ) -> HardConstraintResult:
        # 1. Table boundaries
        if unit_a.is_table or unit_b.is_table:
            return HardConstraintResult(
                triggered=True,
                constraint_type="TABLE_BOUNDARY",
                forced_action=BoundaryDecision.PRESERVE,
                reason_code="HARD_TABLE_BOUNDARY",
                evidence={
                    "unit_a_id": unit_a.candidate_id,
                    "unit_b_id": unit_b.candidate_id,
                    "unit_a_is_table": unit_a.is_table,
                    "unit_b_is_table": unit_b.is_table,
                },
            )

        # 2. Figure boundaries
        if unit_a.is_figure or unit_b.is_figure:
            return HardConstraintResult(
                triggered=True,
                constraint_type="FIGURE_BOUNDARY",
                forced_action=BoundaryDecision.PRESERVE,
                reason_code="HARD_FIGURE_BOUNDARY",
                evidence={
                    "unit_a_id": unit_a.candidate_id,
                    "unit_b_id": unit_b.candidate_id,
                    "unit_a_is_figure": unit_a.is_figure,
                    "unit_b_is_figure": unit_b.is_figure,
                },
            )

        # 3. Cross-page continuation
        if enable_cross_page_continuity:
            if unit_b.is_continued or (unit_b.continuation_of_id and unit_b.continuation_of_id == unit_a.candidate_id):
                return HardConstraintResult(
                    triggered=True,
                    constraint_type="CONTINUATION_HEADER",
                    forced_action=BoundaryDecision.MERGE,
                    reason_code="HARD_CROSS_PAGE_CONTINUATION",
                    evidence={
                        "unit_a_id": unit_a.candidate_id,
                        "unit_b_id": unit_b.candidate_id,
                        "continuation_of_id": unit_b.continuation_of_id,
                        "page_a": unit_a.page_start,
                        "page_b": unit_b.page_start,
                    },
                )

        # 4. Token limit guardrail
        combined_tokens = unit_a.token_estimate + unit_b.token_estimate
        if combined_tokens > max_parent_tokens:
            return HardConstraintResult(
                triggered=True,
                constraint_type="MAX_TOKENS_EXCEEDED",
                forced_action=BoundaryDecision.SPLIT,
                reason_code="HARD_MAX_PARENT_TOKENS_EXCEEDED",
                evidence={
                    "combined_tokens": combined_tokens,
                    "max_parent_tokens": max_parent_tokens,
                    "tokens_a": unit_a.token_estimate,
                    "tokens_b": unit_b.token_estimate,
                },
            )

        return HardConstraintResult(triggered=False)


class SignalAvailabilityComputer:
    """
    Computes deterministic, reproducible signals between adjacent CandidateUnits.
    Strictly forbids fabricated defaults: if evidence is insufficient, marks
    available=False and provides explicit missing_reason.
    """

    @staticmethod
    def compute_all(
        unit_a: CandidateUnit,
        unit_b: CandidateUnit,
        config: ChunkingConfig,
        graph: Optional[Any] = None,
        node_to_community: Optional[Dict[str, str]] = None,
    ) -> Dict[str, SignalResult]:
        signals: Dict[str, SignalResult] = {}

        # 1. Structural Boundary Strength
        # Based on heading equality and page transition
        if unit_a.heading != unit_b.heading:
            signals["structural_boundary"] = SignalResult(
                name="structural_boundary",
                value=0.85,
                available=True,
                method="heading_hierarchy_comparison",
                evidence_count=1,
                quality=1.0,
            )
        elif unit_a.page_end != unit_b.page_start:
            signals["structural_boundary"] = SignalResult(
                name="structural_boundary",
                value=0.35,
                available=True,
                method="page_transition",
                evidence_count=1,
                quality=1.0,
            )
        else:
            signals["structural_boundary"] = SignalResult(
                name="structural_boundary",
                value=0.0,
                available=True,
                method="contiguous_same_section",
                evidence_count=1,
                quality=1.0,
            )

        # 2. Semantic Discontinuity
        words_a = set(re.findall(r"\b[a-zA-Z]{3,}\b", unit_a.plain_text.lower()))
        words_b = set(re.findall(r"\b[a-zA-Z]{3,}\b", unit_b.plain_text.lower()))
        stop_words = {"the", "and", "for", "with", "this", "that", "from", "are", "were", "been", "have", "has", "our", "their"}
        words_a -= stop_words
        words_b -= stop_words

        if len(words_a) < config.min_content_words_for_semantic or len(words_b) < config.min_content_words_for_semantic:
            signals["semantic_discontinuity"] = SignalResult(
                name="semantic_discontinuity",
                value=None,
                available=False,
                method="token_jaccard_content_words",
                evidence_count=0,
                quality=0.0,
                missing_reason=f"insufficient_content_words (A={len(words_a)}, B={len(words_b)})",
            )
        else:
            intersection = words_a & words_b
            union = words_a | words_b
            jaccard = len(intersection) / len(union) if union else 0.0
            sem_discontinuity = max(0.0, 1.0 - (jaccard * 3.0))
            signals["semantic_discontinuity"] = SignalResult(
                name="semantic_discontinuity",
                value=sem_discontinuity,
                available=True,
                method="token_jaccard_content_words",
                evidence_count=len(intersection),
                quality=min(1.0, len(union) / 20.0),
            )

        # 3. Topic Transition
        if unit_a.heading != unit_b.heading:
            signals["topic_transition"] = SignalResult(
                name="topic_transition",
                value=0.70,
                available=True,
                method="heading_topic_shift",
                evidence_count=1,
                quality=1.0,
            )
        elif signals["semantic_discontinuity"].available and signals["semantic_discontinuity"].value is not None:
            if signals["semantic_discontinuity"].value > 0.75:
                signals["topic_transition"] = SignalResult(
                    name="topic_transition",
                    value=0.60,
                    available=True,
                    method="lexical_divergence_topic_shift",
                    evidence_count=signals["semantic_discontinuity"].evidence_count,
                    quality=signals["semantic_discontinuity"].quality,
                )
            else:
                signals["topic_transition"] = SignalResult(
                    name="topic_transition",
                    value=0.0,
                    available=True,
                    method="same_heading_low_divergence",
                    evidence_count=signals["semantic_discontinuity"].evidence_count,
                    quality=1.0,
                )
        else:
            signals["topic_transition"] = SignalResult(
                name="topic_transition",
                value=None,
                available=False,
                method="topic_shift",
                evidence_count=0,
                quality=0.0,
                missing_reason="insufficient_lexical_evidence",
            )

        # 4. Entity Continuity
        if config.ablation_disable_entity_continuity:
            signals["entity_continuity"] = SignalResult(
                name="entity_continuity",
                value=0.0,
                available=False,
                method="ablation_disabled",
                missing_reason="ablation_flag_active",
            )
        else:
            ent_ids_a = {e["id"] for e in unit_a.entities if "id" in e}
            ent_ids_b = {e["id"] for e in unit_b.entities if "id" in e}
            names_a = {e.get("name", "").lower() for e in unit_a.entities if len(e.get("name", "")) > 3}
            names_b = {e.get("name", "").lower() for e in unit_b.entities if len(e.get("name", "")) > 3}
            shared_ents = ent_ids_a & ent_ids_b
            all_ents = ent_ids_a | ent_ids_b
            shared_names = names_a & names_b

            if not all_ents and not names_a and not names_b:
                signals["entity_continuity"] = SignalResult(
                    name="entity_continuity",
                    value=None,
                    available=False,
                    method="graph_entity_overlap",
                    evidence_count=0,
                    quality=0.0,
                    missing_reason="no_entities_extracted_in_adjacent_units",
                )
            else:
                base_ratio = len(shared_ents) / len(all_ents) if all_ents else 0.0
                if shared_names and base_ratio < 0.75:
                    ent_val = max(base_ratio, 0.75)
                else:
                    ent_val = base_ratio
                signals["entity_continuity"] = SignalResult(
                    name="entity_continuity",
                    value=ent_val,
                    available=True,
                    method="graph_entity_overlap",
                    evidence_count=len(shared_ents) + len(shared_names),
                    quality=min(1.0, len(all_ents) / 5.0) if all_ents else 0.5,
                )

        # 5. Relationship Continuity
        if config.ablation_disable_relationship_continuity:
            signals["relationship_continuity"] = SignalResult(
                name="relationship_continuity",
                value=0.0,
                available=False,
                method="ablation_disabled",
                missing_reason="ablation_flag_active",
            )
        else:
            rel_targets_a = {r.get("target_id") or r.get("target") for r in unit_a.relationships if (r.get("target_id") or r.get("target"))}
            rel_targets_b = {r.get("target_id") or r.get("target") for r in unit_b.relationships if (r.get("target_id") or r.get("target"))}
            ent_ids_a = {e["id"] for e in unit_a.entities if "id" in e}
            ent_ids_b = {e["id"] for e in unit_b.entities if "id" in e}
            shared_rel_targets = rel_targets_a & rel_targets_b
            cross_rel = (ent_ids_a & rel_targets_b) | (ent_ids_b & rel_targets_a)

            if not rel_targets_a and not rel_targets_b and not cross_rel:
                shared_ents = ent_ids_a & ent_ids_b
                if shared_ents:
                    signals["relationship_continuity"] = SignalResult(
                        name="relationship_continuity",
                        value=0.50,
                        available=True,
                        method="shared_entity_relational_implication",
                        evidence_count=len(shared_ents),
                        quality=0.5,
                    )
                else:
                    signals["relationship_continuity"] = SignalResult(
                        name="relationship_continuity",
                        value=None,
                        available=False,
                        method="graph_relationship_overlap",
                        evidence_count=0,
                        quality=0.0,
                        missing_reason="no_relationships_extracted_in_adjacent_units",
                    )
            else:
                if shared_rel_targets or cross_rel:
                    rel_val = 0.85
                    ev_count = len(shared_rel_targets) + len(cross_rel)
                else:
                    rel_val = 0.0
                    ev_count = 0
                signals["relationship_continuity"] = SignalResult(
                    name="relationship_continuity",
                    value=rel_val,
                    available=True,
                    method="graph_relationship_overlap",
                    evidence_count=ev_count,
                    quality=min(1.0, (len(rel_targets_a | rel_targets_b)) / 4.0),
                )

        # 6. Graph Connectivity & Shortest Path in Temporary Graph
        if not HAS_NETWORKX or graph is None or len(graph.nodes) == 0:
            ent_ids_a = {e["id"] for e in unit_a.entities if "id" in e}
            ent_ids_b = {e["id"] for e in unit_b.entities if "id" in e}
            shared_ents = ent_ids_a & ent_ids_b
            if shared_ents:
                signals["graph_connectivity"] = SignalResult(
                    name="graph_connectivity",
                    value=0.75,
                    available=True,
                    method="shared_entity_bipartite_fallback",
                    evidence_count=len(shared_ents),
                    quality=0.75,
                )
            else:
                signals["graph_connectivity"] = SignalResult(
                    name="graph_connectivity",
                    value=None,
                    available=False,
                    method="networkx_shortest_path",
                    evidence_count=0,
                    quality=0.0,
                    missing_reason="graph_not_constructed",
                )
        elif graph.has_node(unit_a.candidate_id) and graph.has_node(unit_b.candidate_id):
            try:
                if nx.has_path(graph, unit_a.candidate_id, unit_b.candidate_id):
                    dist = nx.shortest_path_length(graph, unit_a.candidate_id, unit_b.candidate_id)
                    if dist == 2:
                        conn_val = 1.0
                    elif dist <= 4:
                        conn_val = 0.6
                    else:
                        conn_val = 0.2
                    signals["graph_connectivity"] = SignalResult(
                        name="graph_connectivity",
                        value=conn_val,
                        available=True,
                        method="networkx_shortest_path",
                        evidence_count=1,
                        quality=1.0,
                    )
                else:
                    signals["graph_connectivity"] = SignalResult(
                        name="graph_connectivity",
                        value=0.0,
                        available=True,
                        method="networkx_shortest_path",
                        evidence_count=0,
                        quality=1.0,
                    )
            except Exception as e:
                signals["graph_connectivity"] = SignalResult(
                    name="graph_connectivity",
                    value=None,
                    available=False,
                    method="networkx_shortest_path",
                    evidence_count=0,
                    quality=0.0,
                    missing_reason=f"graph_traversal_error: {str(e)}",
                )
        else:
            ent_ids_a = {e["id"] for e in unit_a.entities if "id" in e}
            ent_ids_b = {e["id"] for e in unit_b.entities if "id" in e}
            shared_ents = ent_ids_a & ent_ids_b
            if shared_ents:
                signals["graph_connectivity"] = SignalResult(
                    name="graph_connectivity",
                    value=0.75,
                    available=True,
                    method="shared_entity_bipartite_fallback",
                    evidence_count=len(shared_ents),
                    quality=0.75,
                )
            else:
                signals["graph_connectivity"] = SignalResult(
                    name="graph_connectivity",
                    value=None,
                    available=False,
                    method="networkx_shortest_path",
                    evidence_count=0,
                    quality=0.0,
                    missing_reason="candidate_nodes_missing_from_graph",
                )

        # 7. Community Continuity
        if config.ablation_disable_community_continuity:
            signals["community_continuity"] = SignalResult(
                name="community_continuity",
                value=0.0,
                available=False,
                method="ablation_disabled",
                missing_reason="ablation_flag_active",
            )
        elif not node_to_community:
            signals["community_continuity"] = SignalResult(
                name="community_continuity",
                value=None,
                available=False,
                method="louvain_community_membership",
                evidence_count=0,
                quality=0.0,
                missing_reason="community_detection_unavailable_or_empty",
            )
        else:
            comm_a = node_to_community.get(unit_a.candidate_id)
            comm_b = node_to_community.get(unit_b.candidate_id)
            if comm_a and comm_b:
                signals["community_continuity"] = SignalResult(
                    name="community_continuity",
                    value=1.0 if comm_a == comm_b else 0.0,
                    available=True,
                    method="louvain_community_membership",
                    evidence_count=1,
                    quality=1.0,
                )
            else:
                signals["community_continuity"] = SignalResult(
                    name="community_continuity",
                    value=None,
                    available=False,
                    method="louvain_community_membership",
                    evidence_count=0,
                    quality=0.0,
                    missing_reason="candidate_unit_not_in_community_map",
                )

        # 8. Cross-Section Dependency
        ent_ids_a = {e["id"] for e in unit_a.entities if "id" in e}
        ent_ids_b = {e["id"] for e in unit_b.entities if "id" in e}
        rel_targets_a = {r.get("target_id") or r.get("target") for r in unit_a.relationships if (r.get("target_id") or r.get("target"))}
        rel_targets_b = {r.get("target_id") or r.get("target") for r in unit_b.relationships if (r.get("target_id") or r.get("target"))}
        shared_ents = ent_ids_a & ent_ids_b
        cross_rel = (ent_ids_a & rel_targets_b) | (ent_ids_b & rel_targets_a)

        if unit_a.section_id != unit_b.section_id:
            if shared_ents or cross_rel:
                signals["cross_section"] = SignalResult(
                    name="cross_section",
                    value=0.9,
                    available=True,
                    method="cross_section_entity_bridge",
                    evidence_count=len(shared_ents) + len(cross_rel),
                    quality=1.0,
                )
            else:
                signals["cross_section"] = SignalResult(
                    name="cross_section",
                    value=0.0,
                    available=True,
                    method="cross_section_no_bridge",
                    evidence_count=0,
                    quality=1.0,
                )
        else:
            signals["cross_section"] = SignalResult(
                name="cross_section",
                value=0.0,
                available=True,
                method="same_section_no_cross_dependency",
                evidence_count=0,
                quality=1.0,
            )

        return signals


class GraphGuidedBoundaryOptimizer:
    """
    Evaluates pairs of adjacent candidate information units (A, B) using multi-signal graph analysis
    and dynamic weight renormalization:
      BoundaryScore(A, B) =
          w_sem * SemanticDiscontinuity
        + w_struct * StructuralBoundaryStrength
        + w_topic * TopicTransition
        - w_ent * EntityContinuity
        - w_rel * RelationshipContinuity
        - w_conn * GraphConnectivity
        - w_comm * CommunityContinuity
        - w_cross * CrossSectionDependency

    HIGH BoundaryScore -> SPLIT
    LOW BoundaryScore  -> MERGE
    """

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self.graph_builder = TemporaryGraphBuilder()
        self.hard_constraint_engine = HardConstraintEngine()
        self.signal_computer = SignalAvailabilityComputer()

    def evaluate_boundary(
        self,
        unit_a: CandidateUnit,
        unit_b: CandidateUnit,
        graph: Optional[Any] = None,
        node_to_community: Optional[Dict[str, str]] = None,
    ) -> BoundaryExplanation:
        """
        Calculates boundary score, determines decision (MERGE, SPLIT, PRESERVE),
        and provides an explainable reason trace and deterministic audit ledger.
        """
        boundary_id = f"bnd_{unit_a.candidate_id}_{unit_b.candidate_id}"

        # 1. Evaluate Hard Constraints First
        hard_result = self.hard_constraint_engine.evaluate(
            unit_a=unit_a,
            unit_b=unit_b,
            max_parent_tokens=self.config.max_parent_tokens,
            enable_cross_page_continuity=self.config.enable_cross_page_continuity,
        )

        if hard_result.triggered:
            action = hard_result.forced_action or BoundaryDecision.PRESERVE
            if action == BoundaryDecision.PRESERVE:
                score = 0.85 if unit_a.is_table or unit_b.is_table else 0.80
                reasons = [
                    f"+ preserved {hard_result.constraint_type.lower().replace('_', ' ')} as first-class information unit"
                ]
            elif action == BoundaryDecision.SPLIT:
                score = 1.0
                reasons = [f"+ hard constraint split: {hard_result.reason_code}"]
            else:  # MERGE
                score = -1.0
                reasons = [f"- hard constraint merge: {hard_result.reason_code}"]

            return BoundaryExplanation(
                boundary_id=boundary_id,
                unit_a_id=unit_a.candidate_id,
                unit_b_id=unit_b.candidate_id,
                page_a=unit_a.page_start,
                page_b=unit_b.page_start,
                decision=action,
                boundary_score=score,
                confidence=1.0,
                reasons=reasons,
                reason_codes=[hard_result.reason_code or "HARD_CONSTRAINT"],
                signals={"structural_boundary": 1.0 if action == BoundaryDecision.PRESERVE else 0.0},
                hard_constraint=hard_result,
                is_strict_mode=self.config.strict_mode,
            )

        # 2. Compute Measurable Signals (No fabricated values)
        signal_results = self.signal_computer.compute_all(
            unit_a=unit_a,
            unit_b=unit_b,
            config=self.config,
            graph=graph,
            node_to_community=node_to_community,
        )

        # 3. Dynamic Weight Renormalization
        configured_weights = {
            "semantic_discontinuity": self.config.weight_semantic_discontinuity,
            "structural_boundary": self.config.weight_structural_boundary,
            "topic_transition": self.config.weight_topic_transition,
            "entity_continuity": self.config.weight_entity_continuity,
            "relationship_continuity": self.config.weight_relationship_continuity,
            "graph_connectivity": self.config.weight_graph_connectivity,
            "community_continuity": self.config.weight_community_continuity,
            "cross_section": self.config.weight_cross_section,
        }

        signal_signs = {
            "semantic_discontinuity": 1.0,
            "structural_boundary": 1.0,
            "topic_transition": 1.0,
            "entity_continuity": -1.0,
            "relationship_continuity": -1.0,
            "graph_connectivity": -1.0,
            "community_continuity": -1.0,
            "cross_section": -1.0,
        }

        # Filter active signals
        active_signals = {
            k: res for k, res in signal_results.items()
            if res.available and res.value is not None
        }

        total_configured_weight = sum(configured_weights.values())
        active_configured_weight = sum(configured_weights[k] for k in active_signals)

        normalized_weights: Dict[str, float] = {}
        if active_configured_weight > 0.0:
            scale_factor = total_configured_weight / active_configured_weight
            for k in active_signals:
                normalized_weights[k] = configured_weights[k] * scale_factor

            score = sum(
                normalized_weights[k] * signal_signs[k] * active_signals[k].value
                for k in active_signals
            )
            available_weight_ratio = active_configured_weight / total_configured_weight
        else:
            score = 0.0
            available_weight_ratio = 0.0

        # Determine Decision and Margin
        reasons: List[str] = []
        reason_codes: List[str] = []

        if score >= self.config.split_threshold:
            decision = BoundaryDecision.SPLIT
            margin = abs(score - self.config.split_threshold)
        elif score <= self.config.merge_threshold:
            # Over-merging prevention check:
            # 1. Reject if different headings (unless cross-page continuation)
            # 2. Reject if combined child token budget exceeds max_child_tokens
            # 3. Require either entity cohesion or semantic cohesion
            combined_child_tokens = unit_a.token_estimate + unit_b.token_estimate
            sd_res = signal_results.get("semantic_discontinuity")
            ec_res = signal_results.get("entity_continuity")

            sem_sim = (1.0 - sd_res.value) if (sd_res and sd_res.available and sd_res.value is not None) else 0.0
            ent_cont = ec_res.value if (ec_res and ec_res.available and ec_res.value is not None) else 0.0

            is_jaccard = (sd_res and sd_res.method == "token_jaccard_content_words")
            effective_sem_thresh = (self.config.merge_semantic_similarity_threshold * 0.20) if is_jaccard else self.config.merge_semantic_similarity_threshold

            has_entity_cohesion = ent_cont >= self.config.merge_min_entity_cooccurrence or (legacy_signals.get("relationship_continuity", 0.0) > 0.4)
            has_semantic_cohesion = sem_sim >= effective_sem_thresh

            if unit_a.heading != unit_b.heading and not (unit_b.is_continued or unit_b.continuation_of_id == unit_a.candidate_id):
                decision = BoundaryDecision.SPLIT
                margin = abs(score - self.config.split_threshold)
                reasons.append(f"+ distinct section headings '{unit_a.heading}' != '{unit_b.heading}'")
                reason_codes.append("STRUCTURAL_HEADING_SHIFT")
            elif combined_child_tokens > self.config.max_child_tokens:
                decision = BoundaryDecision.PRESERVE
                margin = 0.0
                reasons.append(f"= over-merge prevented: combined tokens {combined_child_tokens} > max child {self.config.max_child_tokens}")
                reason_codes.append("REJECTED_MERGE_MAX_CHILD_EXCEEDED")
            elif not has_entity_cohesion and not has_semantic_cohesion:
                decision = BoundaryDecision.PRESERVE
                margin = 0.0
                reasons.append(f"= over-merge prevented: insufficient entity cohesion ({ent_cont:.2f}) and semantic similarity ({sem_sim:.2f})")
                reason_codes.append("REJECTED_MERGE_LOW_COHESION")
            else:
                decision = BoundaryDecision.MERGE
                margin = abs(self.config.merge_threshold - score)
        else:
            decision = BoundaryDecision.PRESERVE
            margin = 0.0

        agreement = min(1.0, 0.5 + 0.5 * margin)
        confidence = max(0.20, min(0.99, available_weight_ratio * agreement))

        # Build Explainable Reason Trace & Machine-Readable Reason Codes

        legacy_signals = {
            k: (res.value if res.value is not None else 0.0)
            for k, res in signal_results.items()
        }
        if "structural_boundary" in legacy_signals:
            legacy_signals["structural_strength"] = legacy_signals["structural_boundary"]

        sb_val = legacy_signals.get("structural_boundary", 0.0)
        tt_val = legacy_signals.get("topic_transition", 0.0)
        ec_val = legacy_signals.get("entity_continuity", 0.0)
        rc_val = legacy_signals.get("relationship_continuity", 0.0)
        gc_val = legacy_signals.get("graph_connectivity", 0.0)
        cc_val = legacy_signals.get("community_continuity", 0.0)
        sd_val = legacy_signals.get("semantic_discontinuity", 0.0)

        if decision == BoundaryDecision.SPLIT:
            if sb_val > 0.5:
                reasons.append("+ strong structural boundary")
                reason_codes.append("STRUCTURAL_HEADING_SHIFT")
            if tt_val > 0.5:
                reasons.append("+ strong topic transition")
                reason_codes.append("TOPIC_TRANSITION")
            if "entity_continuity" in active_signals and ec_val < 0.2:
                reasons.append("+ low entity overlap")
                reason_codes.append("LOW_ENTITY_OVERLAP")
            if "relationship_continuity" in active_signals and rc_val < 0.2:
                reasons.append("+ low relationship continuity")
                reason_codes.append("LOW_RELATIONSHIP_CONTINUITY")
            if "community_continuity" in active_signals and cc_val == 0.0:
                reasons.append("+ different graph communities")
                reason_codes.append("DIFFERENT_COMMUNITIES")
            if not reason_codes:
                reasons.append("+ split boundary threshold met")
                reason_codes.append("SPLIT_THRESHOLD_EXCEEDED")
        elif decision == BoundaryDecision.MERGE:
            if ec_val > 0.4:
                reasons.append("- high entity continuity")
                reason_codes.append("ENTITY_COHESION")
            if rc_val > 0.4:
                reasons.append("- shared relationship / event")
                reason_codes.append("RELATIONSHIP_COHESION")
            if gc_val > 0.5:
                reasons.append("- strong graph connectivity")
                reason_codes.append("GRAPH_TOPOLOGY_COHESION")
            if cc_val > 0.5:
                reasons.append("- same graph community")
                reason_codes.append("COMMUNITY_MEMBERSHIP_COHESION")
            if "semantic_discontinuity" in active_signals and sd_val < 0.35:
                reasons.append("- strong semantic similarity")
                reason_codes.append("SEMANTIC_COHESION")
            if not reason_codes:
                reasons.append("- merge boundary threshold met")
                reason_codes.append("MERGE_THRESHOLD_MET")
        else:
            if not reason_codes:
                reasons.append("= balanced signals; preserve candidate unit boundary")
                reason_codes.append("BALANCED_SIGNALS_PRESERVE")

        return BoundaryExplanation(
            boundary_id=boundary_id,
            unit_a_id=unit_a.candidate_id,
            unit_b_id=unit_b.candidate_id,
            page_a=unit_a.page_start,
            page_b=unit_b.page_start,
            decision=decision,
            boundary_score=score,
            confidence=confidence,
            reasons=reasons,
            signals=legacy_signals,
            signal_results=signal_results,
            configured_weights=configured_weights,
            normalized_weights=normalized_weights,
            reason_codes=reason_codes,
            is_strict_mode=self.config.strict_mode,
        )
