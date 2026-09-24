"""
RAISE Dynamic Multi-Substrate Candidate Generation (Stage A)
Gathers candidate evidence across dense vector, BM25, exact entity, phrase, year, and graph anchor indices.
Produces an expanded, multi-signal candidate pool for downstream precision reranking.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from src.graph.entity_resolver import EntityResolver


class CandidateGenerator:
    """
    Multi-substrate candidate generator for Stage A retrieval.
    """

    def __init__(self, entity_resolver: Optional[EntityResolver] = None):
        self.entity_resolver = entity_resolver or EntityResolver()

    def generate_candidates(
        self,
        query: str,
        vector_search_fn: Any,
        bm25_search_fn: Optional[Any] = None,
        raw_chunks: Optional[List[Dict[str, Any]]] = None,
        top_k_per_substrate: int = 12,
    ) -> List[Dict[str, Any]]:
        """
        Gathers raw candidates from all available substrates.
        """
        candidate_map: Dict[str, Dict[str, Any]] = {}

        # 1. Dense Vector Search
        try:
            vec_hits = vector_search_fn(query, top_k=top_k_per_substrate)
            for rank, hit in enumerate(vec_hits):
                cid = hit.get("chunk_id")
                if cid:
                    item = dict(hit)
                    item["vector_rank"] = rank + 1
                    candidate_map[cid] = item
        except Exception:
            pass

        # 2. Extract Decomposed Sub-Query Entities, Phrases, and Years
        entities = self.entity_resolver.extract_candidate_entities(query)

        # 3. BM25 Sparse Lexical Search
        if bm25_search_fn:
            try:
                bm25_hits = bm25_search_fn(query, top_k=top_k_per_substrate)
                for rank, hit in enumerate(bm25_hits):
                    cid = hit.get("chunk_id")
                    if cid:
                        if cid in candidate_map:
                            candidate_map[cid]["bm25_rank"] = rank + 1
                        else:
                            item = dict(hit)
                            item["bm25_rank"] = rank + 1
                            candidate_map[cid] = item

                # Entity-targeted BM25 sub-queries
                for ent in entities[:4]:
                    sub_hits = bm25_search_fn(ent, top_k=4)
                    for sh in sub_hits:
                        scid = sh.get("chunk_id")
                        if scid and scid not in candidate_map:
                            item = dict(sh)
                            item["targeted_entity_hit"] = ent
                            candidate_map[scid] = item
            except Exception:
                pass

        # 4. Exact Title and Year Anchor Lookup across raw chunks
        if raw_chunks and entities:
            norm_entities = {self.entity_resolver.normalize_entity(e): e for e in entities}
            for chk in raw_chunks:
                cid = chk.get("chunk_id")
                if not cid or cid in candidate_map:
                    continue

                title = chk.get("title") or chk.get("metadata", {}).get("title", "")
                title_norm = self.entity_resolver.normalize_entity(title)

                # Check if chunk title exactly matches or contains an extracted entity
                if title_norm in norm_entities:
                    item = dict(chk)
                    item["exact_title_match"] = norm_entities[title_norm]
                    candidate_map[cid] = item
                elif any(ne in title_norm for ne in norm_entities if len(ne) >= 4):
                    item = dict(chk)
                    item["partial_title_match"] = True
                    candidate_map[cid] = item

        return list(candidate_map.values())
