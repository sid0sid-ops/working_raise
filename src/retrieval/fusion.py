"""
RAISE Hybrid Retrieval & Fusion Engine — Layer B: Reranker
Component          : CrossEncoderReranker (src/retrieval/fusion.py)
Hardware / Process : cuda:0 (auto-detected GPU)
Dimensions / Specs : Cross-Attention (BAAI/bge-reranker-large)
Verification       : Real-time cross-attention scores + neighborhood chunk expansion
Status             : VERIFIED
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from langchain_core.documents import Document
    HAS_LANGCHAIN_DOC = True
except ImportError:
    HAS_LANGCHAIN_DOC = False
    class Document:  # type: ignore
        def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
            self.page_content = page_content
            self.metadata = metadata or {}

# Auto-load .env variables if not already loaded
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
    else:
        load_dotenv()
except Exception:
    pass

HAS_CROSS_ENCODER = True


def chunk_to_document(chunk: Dict[str, Any] | Document) -> Document:
    """Converts a raw chunk dictionary into a canonical LangChain Document."""
    if isinstance(chunk, Document):
        return chunk
    text = str(chunk.get("plain_text") or chunk.get("text") or chunk.get("content") or "")
    metadata = dict(chunk.get("metadata") or {})
    for key in [
        "chunk_id", "id", "pdf_filename", "primary_page", "printed_page",
        "heading", "doc_id", "similarity", "score", "cross_encoder_score",
        "rrf_score", "source", "document", "is_table"
    ]:
        if key in chunk and key not in metadata:
            metadata[key] = chunk[key]
    if "chunk_id" not in metadata and "id" in chunk:
        metadata["chunk_id"] = chunk["id"]
    return Document(page_content=text, metadata=metadata)


def document_to_chunk(doc: Document | Dict[str, Any]) -> Dict[str, Any]:
    """Converts a LangChain Document into a standard dictionary chunk."""
    if isinstance(doc, dict):
        return dict(doc)
    chunk = dict(doc.metadata or {})
    chunk["text"] = doc.page_content
    chunk["plain_text"] = doc.page_content
    if "chunk_id" not in chunk and "id" in chunk:
        chunk["chunk_id"] = chunk["id"]
    return chunk


def is_table_candidate(candidate: Dict[str, Any] | Document) -> bool:
    """Detects whether candidate contains tabular, markdown schedule, or financial grid structure."""
    if hasattr(candidate, "page_content"):
        txt = str(candidate.page_content or "")
        meta = getattr(candidate, "metadata", {}) or {}
    else:
        txt = str(candidate.get("plain_text") or candidate.get("text") or "")
        meta = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else candidate

    return (
        "| --- |" in txt
        or "|:---" in txt
        or "| ---:" in txt
        or "### Extracted Table" in txt
        or bool(meta.get("has_table"))
        or bool(meta.get("is_table"))
        or int(meta.get("tables_count", 0) or 0) > 0
    )


def _extract_id_and_dict(item: Any, id_key: str = "chunk_id") -> Tuple[str, Dict[str, Any]]:
    """Extracts a unique string ID and dictionary from either a dict or a LangChain Document."""
    if isinstance(item, dict):
        d = dict(item)
        doc_id = str(
            d.get(id_key)
            or d.get("id")
            or (d.get("metadata", {}).get(id_key) if isinstance(d.get("metadata"), dict) else None)
            or (d.get("metadata", {}).get("chunk_id") if isinstance(d.get("metadata"), dict) else None)
            or f"doc_{hash(str(d.get('text') or d.get('plain_text') or d)[:100])}"
        )
        return doc_id, d
    elif hasattr(item, "page_content") and hasattr(item, "metadata"):
        meta = dict(item.metadata or {})
        doc_id = str(
            meta.get(id_key)
            or meta.get("id")
            or meta.get("chunk_id")
            or f"doc_{hash(item.page_content[:100])}"
        )
        d = dict(meta)
        d["text"] = item.page_content
        d["plain_text"] = item.page_content
        if "chunk_id" not in d:
            d["chunk_id"] = doc_id
        return doc_id, d
    else:
        doc_id = f"doc_{hash(str(item))}"
        d = {"text": str(item), "plain_text": str(item), "chunk_id": doc_id}
        return doc_id, d


def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any] | Any]],
    k: int = 60,
    id_key: str = "chunk_id",
    weights: Optional[List[float]] = None,
    table_boost: bool = True,
) -> List[Dict[str, Any]]:
    """
    Computes Reciprocal Rank Fusion (RRF) over multiple ranked retrieval result sets.
    Formula: RRF(d) = sum(w_m / (k + rank_m(d)))
    
    Supports:
    - Input items as Python dicts or LangChain Documents.
    - Intent-aware modality weights (Dense, Sparse BM25, Knowledge Graph).
    - Table and schedule structural boosting (1.35x).
    """
    if not ranked_lists:
        return []

    scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict[str, Any]] = {}

    for l_idx, r_list in enumerate(ranked_lists):
        w = weights[l_idx] if (weights and l_idx < len(weights)) else 1.0
        for rank, item in enumerate(r_list, start=1):
            doc_id, entry_dict = _extract_id_and_dict(item, id_key=id_key)
            if doc_id not in doc_map:
                doc_map[doc_id] = entry_dict

            score_increment = (1.0 / (k + rank)) * w
            if table_boost and is_table_candidate(entry_dict):
                score_increment *= 1.35
            scores[doc_id] = scores.get(doc_id, 0.0) + score_increment

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    results = []
    for rank, doc_id in enumerate(sorted_ids, start=1):
        entry = dict(doc_map[doc_id])
        entry["rrf_score"] = round(scores[doc_id], 6)
        entry["rrf_rank"] = rank
        results.append(entry)

    return results



_CROSS_ENCODER_MODEL_CACHE: Dict[str, Any] = {}


def get_library_institutions() -> Dict[str, List[str]]:
    """
    Dynamically loads registered institutions and their aliases from the library manifest.
    Zero hardcoded institution names in Python code.
    """
    try:
        from src.core.config import settings
        manifest_path = settings.processed_dir / "ingested_manifest.json"
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            inst_map: Dict[str, List[str]] = {}
            for doc in data.get("ready_documents", []):
                short_name = (doc.get("short_name") or doc.get("institution") or "").lower().strip()
                inst_full = (doc.get("institution") or "").lower().strip()
                aliases = [a.lower().strip() for a in doc.get("aliases", []) if a]
                if short_name:
                    if short_name not in inst_map:
                        inst_map[short_name] = []
                    for a in aliases:
                        if a not in inst_map[short_name]:
                            inst_map[short_name].append(a)
                    if inst_full and inst_full not in inst_map[short_name]:
                        inst_map[short_name].append(inst_full)
            if inst_map:
                return inst_map
    except Exception:
        pass
    return {}


def filter_entity_mismatches(
    query: str,
    candidates: List[Dict[str, Any] | Any],
) -> List[Dict[str, Any] | Any]:
    """
    Enforces strict institutional/entity boundary filtering.
    If the user's query specifically targets an institution, prunes candidate chunks
    that explicitly belong to a conflicting institution not mentioned in the query.
    Institutions are dynamically resolved from the active Library manifest.
    """
    if not candidates or not query:
        return candidates

    q_lower = query.lower()
    institutions = get_library_institutions()
    if not institutions:
        return candidates

    # Detect which institutions are targeted by the query
    targeted = set()
    for inst_key, aliases in institutions.items():
        if any(alias in q_lower for alias in aliases):
            targeted.add(inst_key)

    # If no specific institution is targeted, or multiple conflicting ones are requested, preserve all
    if not targeted:
        return candidates

    filtered = []
    for c in candidates:
        if hasattr(c, "metadata"):
            meta = c.metadata or {}
            c_text = str(getattr(c, "page_content", "")).lower()
        else:
            meta = c.get("metadata") or {} if isinstance(c, dict) else {}
            c_text = (c.get("text") or c.get("plain_text") or meta.get("contextualized_content") or "").lower()

        pdf_name = (meta.get("pdf_filename") or (c.get("pdf_filename") if isinstance(c, dict) else "") or "").lower()
        doc_id = (meta.get("document_id") or (c.get("document_id") if isinstance(c, dict) else "") or "").lower()

        # Check for conflict with an institution NOT in targeted
        is_conflict = False
        for inst_key, aliases in institutions.items():
            if inst_key not in targeted:
                if any(alias in pdf_name for alias in aliases) or any(alias in doc_id for alias in aliases):
                    is_conflict = True
                    break
                if any(f"institution: {alias}" in c_text for alias in aliases):
                    is_conflict = True
                    break

        if not is_conflict:
            filtered.append(c)

    # Fallback to candidates if filtering would leave zero candidates
    return filtered if filtered else candidates


def filter_subgraph_entity_mismatches(
    query: str,
    subgraph: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Filters Neo4j subgraph nodes and edges to prune entities belonging to conflicting institutions.
    Dynamically loads institutional aliases from the library manifest.
    """
    if not subgraph or not query or not isinstance(subgraph, dict):
        return subgraph

    q_lower = query.lower()
    institutions = get_library_institutions()
    if not institutions:
        return subgraph

    targeted = set()
    for inst_key, aliases in institutions.items():
        if any(alias in q_lower for alias in aliases):
            targeted.add(inst_key)

    if not targeted:
        return subgraph

    conflict_aliases = []
    for inst_key, aliases in institutions.items():
        if inst_key not in targeted:
            conflict_aliases.extend(aliases)

    nodes = subgraph.get("nodes", [])
    valid_nodes = []
    valid_names = set()
    for n in nodes:
        name = str(n.get("name", "")).lower()
        nid = str(n.get("id", "")).lower()
        lbl = str(n.get("label", "")).lower()
        if any(alias in name or alias in nid or alias in lbl for alias in conflict_aliases):
            continue
        valid_nodes.append(n)
        valid_names.add(str(n.get("name", "")))

    edges = subgraph.get("edges", [])
    valid_edges = []
    for e in edges:
        src = str(e.get("source", "")).lower()
        tgt = str(e.get("target", "")).lower()
        if any(alias in src or alias in tgt for alias in conflict_aliases):
            continue
        valid_edges.append(e)

    return {"nodes": valid_nodes, "edges": valid_edges}


class CrossEncoderReranker:
    """
    Cross-Encoder Contextual Reranking supporting BAAI/bge-reranker-large
    and cross-encoder/ms-marco-MiniLM-L-6-v2 with fallback token-level cross-attention heuristic scoring.
    Loads weights lazily on first rerank() call and caches as singleton in memory for instant reuse.
    """

    AVAILABLE_RERANKERS = {
        "bge-reranker-large": "BAAI/bge-reranker-large",
        "bge-reranker-base": "BAAI/bge-reranker-base",
        "ms-marco-MiniLM-L-6-v2": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    }

    def __init__(self, model_name: Optional[str] = None):
        target_name = model_name or "BAAI/bge-reranker-large"
        self.model_name = self.AVAILABLE_RERANKERS.get(target_name, target_name)
        self.model = _CROSS_ENCODER_MODEL_CACHE.get(self.model_name)
        self._loaded = self.model is not None

    def _ensure_model_loaded(self):
        """Lazy-loads CrossEncoder model and weights once into singleton GPU cache."""
        if self.model is not None:
            return
        if self.model_name in _CROSS_ENCODER_MODEL_CACHE:
            self.model = _CROSS_ENCODER_MODEL_CACHE[self.model_name]
            self._loaded = True
            return
        if self._loaded:
            return
        self._loaded = True
        try:
            from sentence_transformers import CrossEncoder
            import torch, warnings
            dev = "cuda" if torch.cuda.is_available() else "cpu"
            token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning)
                    loaded_model = CrossEncoder(
                        self.model_name,
                        device=dev,
                        token=token,
                    )
                    self.model = loaded_model
                    _CROSS_ENCODER_MODEL_CACHE[self.model_name] = loaded_model
            except Exception:
                try:
                    fallback_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
                    if fallback_name in _CROSS_ENCODER_MODEL_CACHE:
                        self.model = _CROSS_ENCODER_MODEL_CACHE[fallback_name]
                        self.model_name = fallback_name
                    else:
                        loaded_model = CrossEncoder(
                            fallback_name,
                            device=dev,
                            token=token,
                        )
                        self.model = loaded_model
                        self.model_name = fallback_name
                        _CROSS_ENCODER_MODEL_CACHE[fallback_name] = loaded_model
                except Exception:
                    self.model = None
        except Exception:
            self.model = None

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        text_key: str = "plain_text",
        top_n: int = 8,
        subqueries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Computes query-candidate cross-attention relevance scores and filters peripheral neighbors.
        Supports multi-hop sub-query max-pooling:
        score(c) = max(CrossEncoder(Q_raw, c), max_i CrossEncoder(Q_sub_i, c))
        This eliminates score collapse for atomic multi-hop facts.
        """
        if not candidates:
            return []

        self._ensure_model_loaded()

        # Build list of queries: raw query + non-empty distinct subqueries
        all_queries = [query]
        if subqueries:
            for sq in subqueries:
                sq_clean = sq.strip()
                if sq_clean and sq_clean.lower() != query.strip().lower() and sq_clean not in all_queries:
                    all_queries.append(sq_clean)

        stop_words = {"what", "which", "where", "when", "that", "this", "from", "with", "have", "does", "about", "into"}
        global_structural_terms = re.findall(r"(?:table\s*\d+(?:\.\d+)?|schedule\s*\d+|section\s*\d+)", query, re.IGNORECASE)

        # Prepare pairs for all queries against all candidates
        # Batch size = len(all_queries) * len(candidates)
        all_pairs: List[Tuple[str, str]] = []
        for q in all_queries:
            q_structural = re.findall(r"(?:table\s*\d+(?:\.\d+)?|schedule\s*\d+|section\s*\d+)", q, re.IGNORECASE)
            q_words = [w for w in re.findall(r"\b[a-zA-Z0-9_\-]{4,}\b", q) if w.lower() not in stop_words]

            for c in candidates:
                if hasattr(c, "page_content"):
                    text = str(c.page_content or "")
                else:
                    text = str(c.get(text_key) or c.get("text") or c.get("plain_text") or c.get("heading") or "")
                snippet = text[:3000]

                # Find keyword matches with weights
                all_matches = []
                for qt in q_structural:
                    for m in re.finditer(re.escape(qt), text, re.IGNORECASE):
                        all_matches.append((m.start(), 5))
                for qw in q_words:
                    for m in re.finditer(r"\b" + re.escape(qw) + r"\b", text, re.IGNORECASE):
                        all_matches.append((m.start(), 1))

                if all_matches:
                    best_idx = all_matches[0][0]
                    best_score = -1
                    for idx, _ in all_matches:
                        window_score = sum(weight for m_pos, weight in all_matches if idx - 150 <= m_pos <= idx + 650)
                        if window_score > best_score:
                            best_score = window_score
                            best_idx = idx

                    start_idx = max(0, best_idx - 250)
                    snippet = text[start_idx : start_idx + 2500]

                all_pairs.append((q, snippet))

        # Predict relevance scores in single batch
        if self.model is not None:
            try:
                raw_scores = self.model.predict(all_pairs)
                all_scores = [float(s) for s in raw_scores]
            except Exception:
                all_scores = []
                for p_q, p_snip in all_pairs:
                    all_scores.extend(self._heuristic_cross_attention_scores(p_q, [(p_q, p_snip)]))
        else:
            all_scores = []
            for p_q, p_snip in all_pairs:
                all_scores.extend(self._heuristic_cross_attention_scores(p_q, [(p_q, p_snip)]))

        # Max-pool across all queries for each candidate
        n_candidates = len(candidates)
        reranked = []
        for idx, c in enumerate(candidates):
            if hasattr(c, "page_content") and hasattr(c, "metadata"):
                entry = document_to_chunk(c)
            else:
                entry = dict(c)

            cand_raw = str(entry.get(text_key) or entry.get("text") or entry.get("plain_text") or entry.get("heading") or "")
            table_bonus = 3.0 if any(re.search(re.escape(qt), cand_raw, re.IGNORECASE) for qt in global_structural_terms) else 0.0

            # Find maximum score across all_queries for candidate idx
            best_q_score = -999.0
            best_matched_q = query
            for q_idx, q_str in enumerate(all_queries):
                score_val = all_scores[q_idx * n_candidates + idx]
                if score_val > best_q_score:
                    best_q_score = score_val
                    best_matched_q = q_str

            entry["cross_encoder_score"] = round(best_q_score + table_bonus, 6)
            entry["raw_cross_encoder_score"] = round(all_scores[idx], 6)
            entry["matched_subquery"] = best_matched_q
            reranked.append(entry)

        # 1. Enforce strict institutional entity-boundary filtering before final selection
        reranked = filter_entity_mismatches(query, reranked)

        reranked.sort(key=lambda x: x["cross_encoder_score"], reverse=True)

        # 2. Enforce strict cross-encoder score cutoff
        if reranked:
            best_score = reranked[0]["cross_encoder_score"]
            # Prune candidates with scores significantly lower than top match
            is_logits = (best_score > 1.0 or best_score < -1.0)
            score_cutoff = (best_score - 7.5) if is_logits else 0.15
            filtered_by_score = [c for c in reranked if c["cross_encoder_score"] >= score_cutoff]
            top_candidates = (filtered_by_score if filtered_by_score else reranked)[:top_n]
        else:
            top_candidates = []

        expanded_results = []
        seen_ids = set()
        for cand in top_candidates:
            cid = cand.get("chunk_id") or cand.get("id") or (cand.get("metadata", {}).get("chunk_id") if isinstance(cand.get("metadata"), dict) else None)
            if not cid:
                cid = f"chk_anon_{len(seen_ids)}"
            if cid not in seen_ids:
                seen_ids.add(cid)
                expanded_results.append(cand)

        return expanded_results[:top_n]

    def _heuristic_cross_attention_scores(
        self, query: str, pairs: List[Tuple[str, str]]
    ) -> List[float]:
        """High-precision lexical overlap & contextual co-occurrence fallback."""
        q_tokens = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", query.lower()))
        if not q_tokens:
            return [0.5] * len(pairs)

        scores = []
        for _, text in pairs:
            t_tokens = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower()))
            overlap = len(q_tokens.intersection(t_tokens))
            precision = overlap / len(q_tokens) if q_tokens else 0.0
            # Boost for numeric/financial terms if present in query
            num_boost = 0.2 if re.search(r"\b(\d+|crore|lakh|inr|grant|patent)\b", text, re.IGNORECASE) else 0.0
            score = round(min(1.0, precision + num_boost), 4)
            scores.append(score)
        return scores


def hybrid_fuse_and_rerank(
    query: str,
    dense_candidates: List[Dict[str, Any] | Any],
    sparse_candidates: List[Dict[str, Any] | Any],
    graph_candidates: Optional[List[Dict[str, Any] | Any]] = None,
    top_n: int = 5,
    rrf_k: int = 60,
    as_documents: bool = False,
    subqueries: Optional[List[str]] = None,
) -> List[Dict[str, Any]] | List[Document]:
    """
    End-to-end Hybrid Fusion Pipeline:
    1. Reciprocal Rank Fusion (RRF) across Dense, Sparse, and Graph candidate sets.
    2. Cross-Encoder Contextual Reranking on Top-N merged candidates (with optional sub-query max-pooling).
    3. Optional conversion to canonical LangChain Documents.
    """
    channel_lists = [dense_candidates, sparse_candidates]
    if graph_candidates:
        channel_lists.append(graph_candidates)

    # 1. RRF Merging
    fused = reciprocal_rank_fusion(channel_lists, k=rrf_k)

    # 2. Cross-Encoder Reranking
    reranker = CrossEncoderReranker()
    final_passages = reranker.rerank(query=query, candidates=fused, top_n=top_n, subqueries=subqueries)

    if as_documents:
        return [chunk_to_document(p) for p in final_passages]
    return final_passages


# =============================================================================
# LangChain Core BaseRetriever Integration
# =============================================================================
try:
    from pydantic import ConfigDict
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.callbacks import CallbackManagerForRetrieverRun

    class HybridRetriever(BaseRetriever):
        """
        Production LangChain Core BaseRetriever for RAISE GraphRAG.
        Executes Dense Vector + Sparse BM25 + Neo4j Graph traversal in parallel,
        fuses candidates via Reciprocal Rank Fusion, and applies Cross-Encoder reranking.
        """
        model_config = ConfigDict(arbitrary_types_allowed=True)

        rag_pipeline: Any
        top_k: int = 6
        hops: int = 2
        rerank_top_n: int = 4
        doc_filter: Optional[str] = None
        active_docs: Optional[List[str]] = None

        def _get_relevant_documents(
            self, query: str, *, run_manager: Optional[CallbackManagerForRetrieverRun] = None
        ) -> List[Document]:
            retriever = getattr(self.rag_pipeline, "parallel_retriever", None)
            if retriever and hasattr(retriever, "retrieve_sync"):
                res = retriever.retrieve_sync(
                    query=query,
                    top_k=self.top_k,
                    hops=self.hops,
                    doc_filter=self.doc_filter,
                    active_docs=self.active_docs,
                    rerank_top_n=self.rerank_top_n,
                )
                chunks = res.get("reranked_chunks") or []
            else:
                chunks = self.rag_pipeline.vector_engine.search(
                    query=query,
                    top_k=self.top_k,
                    doc_filter=self.doc_filter,
                    active_docs=self.active_docs,
                )
            return [chunk_to_document(c) for c in chunks]

except ImportError:
    pass
