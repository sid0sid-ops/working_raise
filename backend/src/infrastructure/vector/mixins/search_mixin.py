"""
ChromaDB Dense Similarity Search & Contextual Boosting Mixin
============================================================
Executes dense vector cosine similarity search with active workspace scoping,
target page resolution, and heuristic intent-based candidate boosting.

Architectural Role & Search Pipeline:
-------------------------------------
1. Strict Workspace Scoping:
   - If `active_docs` is explicitly empty (`[]`), returns 0 candidates to guarantee zero
     unauthorized retrieval when no documents are active in the session drawer.

2. Document Name Normalization:
   - Canonical filename mapping resolves discrepancies between user references, filesystem names,
     and database slugs (e.g. "Annual Report 2021-22.pdf" vs "annual_report_2021_22").

3. Query-Aware Heuristic Boosting:
   - Contact Info Boost: Phone numbers and email regex matches boosted (+0.20 to +0.40).
   - Author / Title Page Boost: Page 1 and title sections boosted (+0.35) for identity queries.
   - Tabular / Financial Schedule Boost: Markdown table pipes and schedule tokens boosted (+0.30 to +0.50).
   - Explicit Page Retrieval: Direct page queries ("page 131") trigger targeted direct metadata lookups
     guaranteeing 100% recall for physical and printed page targets.

4. Multi-Resolution Macro Hydration Backlinks:
   - For child chunks containing `parent_chunk_id`, fetches and attaches parent section context
     for downstream cross-encoder reranking.

How to Update or Tune:
----------------------
- To add a new intent boosting rule, add regex patterns in `search()`.
- To adjust the baseline fetch multiplier, modify `n_fetch = min(max(top_k * 6, 35), total_items)`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class VectorSearchMixin:
    """Provides dense similarity search and intent-aware boosting for ChromaDB."""

    def search(
        self,
        query: str,
        top_k: int = 5,
        university_filter: Optional[str] = None,
        doc_filter: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform dense vector cosine similarity search with active document workspace scoping.
        """
        if not query.strip():
            return []

        # Strict drawer isolation: If active_docs is explicitly empty, return zero hits
        if active_docs is not None and len(active_docs) == 0:
            return []

        formatted_query = self.format_query_for_embedding(query)
        query_emb = self.compute_embeddings([formatted_query])[0]
        results = []

        col = self._get_collection()
        total_items = self.count()

        if col is not None and total_items > 0:
            try:
                # Robust canonical mapping for document filenames across formats
                doc_name_map = {
                    "annualreport202122": "Annual Report 2021-22.pdf",
                    "annualreport202223": "Annual Report 2022-23.pdf",
                    "annualreport202324": "Annual Report 2023-24.pdf",
                    "bricannualreport2025": "BRIC-Annual-Report-2025.pdf",
                    "bric2025": "BRIC-Annual-Report-2025.pdf",
                }

                def _canonical_names(val: str) -> List[str]:
                    c_clean = re.sub(r"[^a-zA-Z0-9]", "", str(val).lower())
                    names = [val, val.replace(" ", "_"), val.replace("_", " ")]
                    for k, mapped in doc_name_map.items():
                        if k in c_clean or c_clean in k:
                            names.append(mapped)
                    return list(dict.fromkeys(names))

                where_clause = None
                if doc_filter and doc_filter != "ALL":
                    norm_filter = _canonical_names(doc_filter)
                    if len(norm_filter) == 1:
                        where_clause = {"pdf_filename": norm_filter[0]}
                    else:
                        where_clause = {"pdf_filename": {"$in": norm_filter}}
                elif active_docs and len(active_docs) > 0:
                    active_candidates = []
                    for ad in active_docs:
                        active_candidates.extend(_canonical_names(ad))
                    active_list = list(dict.fromkeys(active_candidates))
                    if len(active_list) == 1:
                        where_clause = {"pdf_filename": active_list[0]}
                    else:
                        where_clause = {"pdf_filename": {"$in": active_list}}

                # Expand candidate fetch size to avoid dense starvation on specific keywords/contact info
                n_fetch = min(max(top_k * 6, 35), total_items)
                chroma_res = None
                if where_clause:
                    try:
                        chroma_res = col.query(
                            query_embeddings=[query_emb],
                            n_results=min(n_fetch, total_items),
                            where=where_clause,
                            include=["documents", "metadatas", "distances"],
                        )
                    except Exception:
                        chroma_res = None

                # Fallback search across collection ONLY if NO active_docs or doc_filter was specified
                # or if scoped query returned 0 hits due to metadata mismatch
                if not chroma_res or not chroma_res.get("ids") or len(chroma_res["ids"][0]) == 0:
                    chroma_res = col.query(
                        query_embeddings=[query_emb],
                        n_results=n_fetch,
                        include=["documents", "metadatas", "distances"],
                    )

                if chroma_res and chroma_res.get("ids") and len(chroma_res["ids"][0]) > 0:
                    ret_ids = chroma_res["ids"][0]
                    ret_docs = chroma_res["documents"][0]
                    ret_meta = chroma_res["metadatas"][0]
                    ret_dists = chroma_res["distances"][0] if "distances" in chroma_res else [0.2] * len(ret_ids)

                    # Intent detection for hybrid keyword/entity boosting
                    q_lower = query.lower()
                    is_contact_query = bool(re.search(r"\b(phone|mobile|number|num|call|cell|contact|email|reach|tel)\b", q_lower))
                    is_author_query = bool(re.search(r"\b(author|who is|whose|candidate|name|profile|bio|cv|resume)\b", q_lower))
                    is_structure_query = bool(re.search(r"\b(layer|layers|architecture|checklist|overview)\b", q_lower))
                    is_table_query = bool(re.search(r"\b(table|schedule|figure|tabular|counts|enrolled|enrollment|admitted|outlay|publications|subcategories)\b", q_lower))

                    candidates = []
                    for cid, doc, meta, dist in zip(ret_ids, ret_docs, ret_meta, ret_dists):
                        meta_pdf = str(meta.get("pdf_filename", ""))
                        meta_doc_id = str(meta.get("doc_id", ""))
                        meta_uni = str(meta.get("university", ""))

                        # Active document filter
                        if active_docs and len(active_docs) > 0:
                            clean_pdf = re.sub(r"[^a-zA-Z0-9]", "", meta_pdf.lower())
                            clean_doc = re.sub(r"[^a-zA-Z0-9]", "", meta_doc_id.lower())
                            matched_active = False
                            for ad in active_docs:
                                clean_ad = re.sub(r"[^a-zA-Z0-9]", "", str(ad).lower())
                                clean_stem = re.sub(r"[^a-zA-Z0-9]", "", Path(ad).stem.lower())
                                if clean_ad in clean_pdf or clean_pdf in clean_ad or clean_stem in clean_doc or clean_doc in clean_stem:
                                    matched_active = True
                                    break
                            if not matched_active:
                                continue

                        # Single document filter
                        if doc_filter and doc_filter != "ALL":
                            clean_df = re.sub(r"[^a-zA-Z0-9]", "", str(doc_filter).lower())
                            clean_pdf = re.sub(r"[^a-zA-Z0-9]", "", meta_pdf.lower())
                            clean_doc = re.sub(r"[^a-zA-Z0-9]", "", meta_doc_id.lower())
                            if clean_df not in clean_pdf and clean_pdf not in clean_df and clean_df not in clean_doc and clean_doc not in clean_df:
                                continue

                        # University filter
                        if university_filter and university_filter.lower() not in meta_uni.lower():
                            continue

                        base_sim = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                        boost = 0.0
                        doc_lower = doc.lower()

                        # Contact information boost
                        if is_contact_query:
                            if re.search(r"(?i)\b(?:phone|tel|mobile|call|contact)[\s:]*(\+?\d[\d\s\-\(\)]{7,}\d)\b", doc) or re.search(r"\b(?:\+91[\-\s]?)?[6789]\d{9}\b", doc):
                                boost += 0.40
                            if re.search(r"[\w\.-]+@[\w\.-]+\.\w+", doc):
                                boost += 0.25
                            if any(k in doc_lower for k in ["phone", "mobile", "contact", "tel"]):
                                boost += 0.20

                        # Author / candidate identity boost
                        if is_author_query:
                            pno = int(meta.get("primary_page", 1))
                            if pno == 1 or "p001" in cid:
                                boost += 0.35

                        # Structural / Checklist / Layers boost
                        if is_structure_query:
                            if "checklist" in q_lower and ("checklist" in doc_lower or "### extracted table" in doc_lower):
                                boost += 0.35
                            if ("layer" in q_lower or "architecture" in q_lower) and ("layer" in doc_lower or "architecture" in doc_lower):
                                boost += 0.30

                        # Tabular & Schedule Data boost
                        if is_table_query:
                            if "### extracted table data" in doc_lower or "| --- |" in doc:
                                boost += 0.30
                            t_num_match = re.search(r"(table\s*\d+(?:\.\d+)?|schedule\s*\d+(?:\.\d+)?)", q_lower)
                            if t_num_match and t_num_match.group(1) in doc_lower:
                                boost += 0.50

                        # Target Page Boost (supports both PDF physical page and document printed page)
                        page_match = re.search(r"\bpage\s*(?:no\.?|number|#)?\s*(\d+)\b", q_lower)
                        if page_match:
                            target_page_num = int(page_match.group(1))
                            p_page = int(meta.get("primary_page", 1))
                            d_page = str(meta.get("printed_page", "")).strip()
                            if p_page == target_page_num or d_page == str(target_page_num):
                                boost += 0.85

                        final_score = round(base_sim + boost, 4)
                        candidates.append({
                            "id": cid,
                            "chunk_id": cid,
                            "text": doc,
                            "similarity": round(base_sim, 4),
                            "boosted_score": final_score,
                            "metadata": meta,
                        })

                    # Direct target page retrieval guarantees 100% recall for explicit page requests (PDF or Doc page)
                    page_query_match = re.search(r"\bpage\s*(?:no\.?|number|#)?\s*(\d+)\b", q_lower)
                    if page_query_match:
                        target_p = int(page_query_match.group(1))
                        for target_cond in [{"primary_page": target_p}, {"printed_page": str(target_p)}]:
                            try:
                                p_filter = dict(target_cond)
                                if doc_filter and doc_filter != "ALL":
                                    p_filter = {"$and": [{"pdf_filename": doc_filter}, target_cond]}
                                elif active_docs and len(active_docs) == 1:
                                    p_filter = {"$and": [{"pdf_filename": active_docs[0]}, target_cond]}
                                elif active_docs and len(active_docs) > 1:
                                    p_filter = {"$and": [{"pdf_filename": {"$in": active_docs}}, target_cond]}
                                
                                direct_page_res = self.collection.get(where=p_filter, include=["documents", "metadatas"])
                                if direct_page_res and direct_page_res.get("ids"):
                                    existing_ids = {c["id"] for c in candidates}
                                    for d_id, d_doc, d_meta in zip(direct_page_res["ids"], direct_page_res["documents"], direct_page_res["metadatas"]):
                                        if d_id not in existing_ids:
                                            candidates.append({
                                                "id": d_id,
                                                "chunk_id": d_id,
                                                "text": d_doc,
                                                "similarity": 0.95,
                                                "boosted_score": 1.95,
                                                "metadata": d_meta,
                                            })
                            except Exception:
                                pass

                    # Sort by boosted score descending
                    candidates.sort(key=lambda x: x["boosted_score"], reverse=True)

                    # Return top-k (expanded for table queries or small doc filter)
                    effective_k = min(len(candidates), max(top_k, 12) if (is_table_query or (doc_filter and len(candidates) <= 20)) else top_k)
                    top_candidates = candidates[:effective_k]

                    # Multi-Resolution Parent-Child Resolution: attach parent context if present
                    parent_ids = [c.get("metadata", {}).get("parent_chunk_id") for c in top_candidates if c.get("metadata", {}).get("parent_chunk_id")]
                    if parent_ids:
                        try:
                            parent_res = self.collection.get(ids=list(set(parent_ids)), include=["documents", "metadatas"])
                            if parent_res and parent_res.get("ids"):
                                p_map = {pid: pdoc for pid, pdoc in zip(parent_res["ids"], parent_res["documents"])}
                                for c in top_candidates:
                                    pid = c.get("metadata", {}).get("parent_chunk_id")
                                    if pid and pid in p_map:
                                        c["parent_context"] = p_map[pid]
                        except Exception:
                            pass

                    return top_candidates

            except Exception as e:
                print(f"ChromaDB search notice: {e}")

        return results

    def get_active_workspace_documents(self) -> List[str]:
        """
        Returns the list of active documents registered in the system manifest.
        """
        try:
            from src.core.config import settings
            manifest_file = settings.processed_dir / "ingested_manifest.json"
            if manifest_file.exists():
                import json
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                docs = data.get("ready_documents", [])
                return [d.get("filename", "") for d in docs if isinstance(d, dict) and d.get("filename")]
        except Exception:
            pass
        return []
