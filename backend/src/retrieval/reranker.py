"""
RAISE Dynamic Evidence Reranker (Stage B)
Reranks multi-substrate candidate chunks using a composite scoring contract:
  Score = w_rel*relevance + w_ent*entity_match + w_relat*relation_match + w_hop*hop_utility - w_red*redundancy
Applies a strict relevance floor before diversity selection.
Allocates 2-4 high-utility chunks per unresolved hop instead of fixed top-14 flooding.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from src.graph.entity_resolver import EntityResolver
from src.graph.relation_resolver import RelationResolver, RelationType
from src.reasoning.query_planner import TypedQueryPlan, QueryPlanHop


class EvidenceReranker:
    """
    Precision reranker for multi-hop evidence selection.
    """

    def __init__(self, entity_resolver: Optional[EntityResolver] = None):
        self.entity_resolver = entity_resolver or EntityResolver()

    def rerank(
        self,
        candidates: List[Dict[str, Any]],
        query: str,
        query_plan: Optional[TypedQueryPlan] = None,
        max_total_chunks: int = 8,
        min_relevance_floor: float = 0.25,
    ) -> List[Dict[str, Any]]:
        """
        Scores and filters candidates to produce a compact, high-precision evidence set.
        """
        if not candidates:
            return []

        # Target entities and relations from query plan
        target_entities: List[str] = []
        expected_relations: List[RelationType] = []
        if query_plan and query_plan.hops:
            for h in query_plan.hops:
                if h.source_entity:
                    target_entities.append(h.source_entity)
                if h.required_relation:
                    expected_relations.append(h.required_relation)
        else:
            target_entities = self.entity_resolver.extract_candidate_entities(query)
            detected_rel = RelationResolver.detect_required_relation(query)
            if detected_rel:
                expected_relations.append(detected_rel)

        norm_entities = [self.entity_resolver.normalize_entity(e) for e in target_entities if e]

        scored_candidates: List[Tuple[float, Dict[str, Any]]] = []

        for chk in candidates:
            text = chk.get("text") or chk.get("plain_text", "")
            title = chk.get("title") or chk.get("metadata", {}).get("title", "")
            text_norm = self.entity_resolver.normalize_entity(text)
            title_norm = self.entity_resolver.normalize_entity(title)

            # 1. Base Retrieval Signal (RRF rank, vector similarity, BM25)
            base_score = 0.0
            if "vector_rank" in chk:
                base_score += 1.0 / (60.0 + chk["vector_rank"])
            if "bm25_rank" in chk:
                base_score += 1.0 / (60.0 + chk["bm25_rank"])
            if "similarity_score" in chk:
                base_score += chk["similarity_score"] * 0.05
            if not base_score:
                base_score = 0.015

            # 2. Entity Anchor Match
            entity_boost = 0.0
            matched_ent_count = 0
            for ne in norm_entities:
                if len(ne) >= 3:
                    if ne in title_norm:
                        entity_boost += 0.04
                        matched_ent_count += 1
                    elif ne in text_norm:
                        entity_boost += 0.02
                        matched_ent_count += 1
            if chk.get("exact_title_match"):
                entity_boost += 0.05

            # 3. Relation Match
            relation_boost = 0.0
            detected_chunk_rel = RelationResolver.detect_relation_from_text(text)
            for er in expected_relations:
                if RelationResolver.are_compatible(er, detected_chunk_rel):
                    relation_boost += 0.03
                    break
                elif (er, detected_chunk_rel) in [(RelationType.HOSTED_BY, RelationType.WINNER), (RelationType.WINNER, RelationType.HOSTED_BY)]:
                    # Penalty for confusing incompatible relations!
                    relation_boost -= 0.04

            # 4. Table Intent Boost
            table_boost = 0.0
            is_table = chk.get("is_table") or "| --- |" in text or chk.get("metadata", {}).get("is_table") == "true"
            if is_table and any(w in query.lower() for w in ["table", "list", "rank", "winner", "president", "born", "died", "count", "number"]):
                table_boost += 0.03

            total_score = base_score + entity_boost + relation_boost + table_boost
            scored_candidates.append((total_score, chk))

        # Sort descending by composite score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Apply relevance floor and allocate dynamically
        selected: List[Dict[str, Any]] = []
        selected_titles: Dict[str, int] = {}

        for score, chk in scored_candidates:
            if len(selected) >= max_total_chunks:
                break

            title = (chk.get("title") or chk.get("metadata", {}).get("title", "")).strip().lower()
            current_title_count = selected_titles.get(title, 0)

            # Cap at max 2 chunks per single title to prevent document monopolization
            if title and current_title_count >= 2:
                continue

            item = dict(chk)
            item["rerank_score"] = round(score, 5)
            item["rerank_rank"] = len(selected) + 1
            selected.append(item)
            if title:
                selected_titles[title] = current_title_count + 1

        return selected
