"""
Autonomous Query Analyzer & Tool Selection Mixin
================================================
Deconstructs natural user queries into intents, target institutions, target fiscal years,
and selects the appropriate tool execution schedule.

Architectural Role & Analysis Pipeline:
---------------------------------------
1. Document Scope Discovery:
   - Identifies whether the query mentions a specific PDF in the active workspace.
   - Extracts university / institution names from active document filenames and metadata.

2. Temporal Filtering:
   - Detects target years (e.g. 2021, 2022, 2023, 2024, 2025) via regex pattern `20[12][0-9]`.

3. Query Intent Classification:
   - `COMPARATIVE_ANALYSIS`: Triggered if multiple institutions are extracted, or keywords
     like "compare", "versus", "vs" appear.
     Selected tools: `structured_fact_search`, `comparative_engine`, `vector_search`, `claim_verifier`.
   - `RELATIONSHIP_QUERY`: Triggered by organizational keywords ("who leads", "director", "collaborated with").
     Selected tools: `cypher_query`, `graph_traversal`, `vector_search`, `claim_verifier`.
   - `SIMPLE_FACT`: Triggered by financial or metric keywords ("balance sheet", "audit", "budget", "expenditure").
     Selected tools: `structured_fact_search`, `vector_search`, `claim_verifier`.
   - `SEMANTIC_EXPLORATION`: Default research query.
     Selected tools: `vector_search`, `graph_traversal`, `claim_verifier`.

4. Mathematical Operand Extractor (`_extract_math_operands`):
   - Searches markdown table rows and matching sentences for numbers to support arithmetic operations
     (e.g., computing growth rates, sums, differences).

How to Update or Tune:
----------------------
- To add a new intent category or tool, modify `analyze_query()`.
- To update keyword lists for financial or organizational queries, edit `analyze_query()`.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .router_models import AgentExecutionPlan


class QueryAnalyzerMixin:
    """Provides query intent classification, institution extraction, and operand parsing."""

    def _get_active_documents(self) -> List[str]:
        """Dynamically fetch list of confirmed active PDF filenames from manifest."""
        manifest_file = Path(__file__).parent.parent / "data" / "processed" / "ingested_manifest.json"
        if manifest_file.exists():
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                return [d["filename"] for d in data.get("ready_documents", []) if "filename" in d]
            except Exception:
                pass
        return []

    @staticmethod
    def _extract_relevant_chunk_text(text: str, query: str = "", max_chars: int = 4000) -> str:
        """Preserves chunk text up to max_chars, centering around query keyword density if longer."""
        if len(text) <= max_chars:
            return text
        if query:
            stop_words = {"what", "which", "where", "when", "that", "this", "from", "with", "have", "does", "about", "into"}
            query_words = [w for w in re.findall(r"\b[a-zA-Z0-9_\-]{4,}\b", query) if w.lower() not in stop_words]
            matches = []
            for qw in query_words:
                for m in re.finditer(r"\b" + re.escape(qw) + r"\b", text, re.IGNORECASE):
                    matches.append(m.start())
            if matches:
                best_idx = matches[0]
                best_count = -1
                for idx in matches:
                    count = sum(1 for m in matches if idx - 150 <= m <= idx + 650)
                    if count > best_count:
                        best_count = count
                        best_idx = idx
                start_idx = max(0, best_idx - 500)
                return text[start_idx : start_idx + max_chars]
        return text[:max_chars]

    def analyze_query(
        self,
        query: str,
        active_docs: Optional[List[str]] = None,
        doc_filter: Optional[str] = None,
    ) -> AgentExecutionPlan:
        """Deconstruct natural query into intent, target universities/documents, and tools."""
        q_lower = query.lower()
        active_doc_list = active_docs if active_docs is not None else self._get_active_documents()

        # 1. Dynamically identify Target Document Filter from Active Workspace or explicit argument
        target_doc = doc_filter if (doc_filter and doc_filter != "ALL") else None
        if not target_doc:
            for fname in active_doc_list:
                stem = Path(fname).stem.lower().replace("_", " ").replace("-", " ")
                if fname.lower() in q_lower or (len(stem) > 4 and stem in q_lower):
                    target_doc = fname
                    break

        # 2. Identify University Keywords or Names
        unis: List[str] = []
        for fname in active_doc_list:
            clean_name = Path(fname).stem.replace("_", " ").replace("-", " ")
            words = [w for w in clean_name.split() if len(w) > 3 and w.lower() not in {"report", "annual", "english", "final", "upload", "combined"}]
            if any(w.lower() in q_lower for w in words):
                if clean_name not in unis:
                    unis.append(clean_name)

        # 3. Identify Years
        years: List[int] = []
        for y_match in re.finditer(r"\b(20[12][0-9])\b", query):
            years.append(int(y_match.group(1)))

        # 4. Classify Query Type
        if len(unis) >= 2 or "compare" in q_lower or "versus" in q_lower or " vs " in q_lower:
            q_type = "COMPARATIVE_ANALYSIS"
            tools = ["structured_fact_search", "comparative_engine", "vector_search", "claim_verifier"]
        elif any(w in q_lower for w in ["who leads", "director", "collaborated with", "partner", "relationship", "network", "programs", "institutes", "centres", "initiatives", "faculty"]):
            q_type = "RELATIONSHIP_QUERY"
            tools = ["cypher_query", "graph_traversal", "vector_search", "claim_verifier"]
        elif any(w in q_lower for w in ["balance sheet", "audit", "cag", "financial", "expenditure", "grant", "budget", "patents", "enrollment", "funding", "money", "rupees", "inr", "crore", "lakh"]):
            q_type = "SIMPLE_FACT"
            tools = ["structured_fact_search", "vector_search", "claim_verifier"]
        else:
            q_type = "SEMANTIC_EXPLORATION"
            tools = ["vector_search", "graph_traversal", "claim_verifier"]

        plan = AgentExecutionPlan(
            query=query,
            query_type=q_type,
            extracted_universities=unis,
            selected_tools=tools,
            target_years=years,
        )
        if target_doc:
            plan.retrieved_evidence["target_doc_filter"] = target_doc
        return plan

    def _get_bm25_search(
        self,
        query: str,
        top_k: int = 12,
        doc_filter: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Performs lexical BM25 retrieval across processed chunks or ChromaDB collection."""
        if active_docs is not None and len(active_docs) == 0:
            return []
        try:
            from src.retrieval.bm25 import SelfContainedBM25
            if not hasattr(self, "_cached_bm25") or self._cached_bm25 is None:
                chunks_dir = Path(__file__).parent.parent / "data" / "processed" / "chunks"
                corpus_chunks = []
                if chunks_dir.exists():
                    for cf in chunks_dir.glob("*_chunks.json"):
                        try:
                            c_list = json.loads(cf.read_text(encoding="utf-8"))
                            if isinstance(c_list, list):
                                corpus_chunks.extend(c_list)
                        except Exception:
                            pass
                if not corpus_chunks and hasattr(self, "vector_engine") and self.vector_engine.collection:
                    try:
                        cdata = self.vector_engine.collection.get()
                        for idx, cid in enumerate(cdata.get("ids", [])):
                            corpus_chunks.append({
                                "chunk_id": cid,
                                "plain_text": cdata["documents"][idx] if idx < len(cdata["documents"]) else "",
                                "metadata": cdata["metadatas"][idx] if idx < len(cdata["metadatas"]) else {},
                            })
                    except Exception:
                        pass
                self._cached_bm25 = SelfContainedBM25(corpus_chunks) if corpus_chunks else None

            if self._cached_bm25:
                raw_hits = self._cached_bm25.search(query, top_k=top_k, active_docs=active_docs)
                res = []
                for b in raw_hits:
                    pdf_n = b.get("pdf_filename") or (b.get("metadata") or {}).get("pdf_filename", "")
                    if doc_filter and doc_filter != "ALL" and pdf_n:
                        clean_df = re.sub(r"[^a-zA-Z0-9]", "", str(doc_filter).lower())
                        clean_n = re.sub(r"[^a-zA-Z0-9]", "", str(pdf_n).lower())
                        if clean_df not in clean_n and clean_n not in clean_df:
                            continue
                    b_meta = dict(b.get("metadata") or {})
                    if "pdf_filename" not in b_meta:
                        b_meta["pdf_filename"] = b.get("pdf_filename")
                    if "primary_page" not in b_meta:
                        b_meta["primary_page"] = b.get("primary_page", 1)
                    if "heading" not in b_meta:
                        b_meta["heading"] = b.get("heading", "")
                    if "chunk_id" not in b_meta:
                        b_meta["chunk_id"] = b.get("chunk_id")
                    if "doc_id" not in b_meta:
                        b_meta["doc_id"] = b.get("document_id")
                    res.append({
                        "id": b.get("chunk_id"),
                        "chunk_id": b.get("chunk_id"),
                        "text": b.get("plain_text", ""),
                        "similarity": round(float(b.get("bm25_score", 1.0)), 4),
                        "boosted_score": round(float(b.get("bm25_score", 1.0)), 4),
                        "metadata": b_meta,
                    })
                return res
        except Exception:
            pass
        return []

    def _extract_math_operands(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        intent: str,
    ) -> Tuple[List[float], Optional[str]]:
        """
        Extract numerical operands and units from retrieved chunks and tabular rows
        matching the query's semantic keywords.
        """
        unit = None
        q_lower = query.lower()
        if "crore" in q_lower or any("crore" in (c.get("text") or "").lower() for c in chunks):
            unit = "Rs. Crore"
        elif "lakh" in q_lower or any("lakh" in (c.get("text") or "").lower() for c in chunks):
            unit = "Rs. Lakh"
        elif "%" in q_lower or "percent" in q_lower:
            unit = "%"
        elif "inr" in q_lower:
            unit = "INR"

        stop_words = {
            "what", "was", "the", "growth", "rate", "of", "in", "between", "and", "fy", "year",
            "total", "sum", "average", "to", "for", "is", "by", "how", "much", "many", "combined",
            "all", "across", "annual", "report", "show", "calculate", "find", "net", "change"
        }
        kw_tokens = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", q_lower) if w not in stop_words]

        candidates: List[float] = []

        # 1. Search markdown table rows containing matching keywords
        for c in chunks:
            text = c.get("text") or ""
            lines = text.split("\n")
            for line in lines:
                if "|" in line:
                    l_lower = line.lower()
                    if kw_tokens and any(k in l_lower for k in kw_tokens):
                        cells = [col.strip() for col in line.split("|") if col.strip()]
                        for cell in cells:
                            for m in re.finditer(r"\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\b", cell):
                                val_str = m.group(1).replace(",", "")
                                try:
                                    fval = float(val_str)
                                    if 1990 <= fval <= 2040 and "." not in val_str:
                                        continue
                                    candidates.append(fval)
                                except ValueError:
                                    continue
                        if len(candidates) >= 2:
                            return candidates, unit

        # 2. Search sentences matching keywords
        if len(candidates) < 2:
            candidates.clear()
            for c in chunks:
                text = c.get("text") or ""
                sentences = re.split(r"(?<=[.!?])\s+", text)
                for s in sentences:
                    s_lower = s.lower()
                    if kw_tokens and any(k in s_lower for k in kw_tokens):
                        for m in re.finditer(r"(?:Rs\.?|INR|\$)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\b", s):
                            val_str = m.group(1).replace(",", "")
                            try:
                                fval = float(val_str)
                                if 1990 <= fval <= 2040 and "." not in val_str:
                                    continue
                                candidates.append(fval)
                            except ValueError:
                                continue
                        if len(candidates) >= 2:
                            return candidates, unit

        return candidates, unit
