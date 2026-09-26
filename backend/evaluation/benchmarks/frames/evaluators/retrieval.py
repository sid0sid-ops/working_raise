"""
FRAMES Benchmark Retrieval Evaluator
Evaluates retrieval accuracy against authoritative Wikipedia ground-truth source links.
Computes:
  - Hit Rate (Did at least one required source get retrieved?)
  - Evidence Coverage (Ratio of required ground-truth sources present in retrieved context)
  - Context Precision & Recall
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from ..data.schema import FramesQuestion


class RetrievalResult(BaseModel):
    """Structured retrieval evaluation metrics for a single benchmark query."""
    question_id: str
    hit_rate: float = Field(..., ge=0.0, le=1.0, description="1.0 if >=1 required source retrieved else 0.0")
    evidence_coverage: float = Field(..., ge=0.0, le=1.0, description="Ratio of ground-truth sources covered")
    total_required_sources: int
    retrieved_sources_count: int
    covered_sources: List[str] = Field(default_factory=list)
    missing_sources: List[str] = Field(default_factory=list)
    context_precision: float = Field(..., ge=0.0, le=1.0)
    source_recall: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of required sources retrieved")
    retrieved_required_source_count: int = Field(default=0, description="Count of required sources retrieved")
    hop_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="Coverage ratio across multi-hop sources")
    path_completeness: float = Field(default=0.0, ge=0.0, le=1.0, description="1.0 if all required links covered, else proportional")
    citation_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of required sources cited")
    details: Dict[str, Any] = Field(default_factory=dict)


class RetrievalEvaluator:
    """
    Measures how effectively the retrieval layer located the authoritative evidence
    mandated by the FRAMES benchmark.
    """

    def _normalize_link(self, link: str) -> str:
        """Extracts canonical Wikipedia article slug."""
        if not link:
            return ""
        # Extract last path segment
        slug = link.split("/")[-1].replace("_", " ").lower()
        # Strip anchor if any
        slug = slug.split("#")[0].strip()
        return slug

    def evaluate(
        self,
        question: FramesQuestion,
        retrieved_chunks: List[Dict[str, Any]],
        generated_answer: str = "",
    ) -> RetrievalResult:
        """
        Calculates source coverage, hit rate, hop coverage, and path completeness
        based on retrieved chunks vs required wiki links.
        """
        qid = question.question_id
        required_links = question.wiki_links
        total_req = len(required_links)

        if total_req == 0:
            # Benchmark question did not specify Wikipedia links
            return RetrievalResult(
                question_id=qid,
                hit_rate=1.0 if retrieved_chunks else 0.0,
                evidence_coverage=1.0 if retrieved_chunks else 0.0,
                total_required_sources=0,
                retrieved_sources_count=len(retrieved_chunks),
                covered_sources=[],
                missing_sources=[],
                context_precision=1.0 if retrieved_chunks else 0.0,
                source_recall=1.0 if retrieved_chunks else 0.0,
                retrieved_required_source_count=0,
                hop_coverage=1.0 if retrieved_chunks else 0.0,
                path_completeness=1.0 if retrieved_chunks else 0.0,
                citation_coverage=1.0,
                details={"note": "No ground-truth source links specified in benchmark row."}
            )

        # Extract all source URLs and titles from retrieved chunks
        retrieved_sources: Set[str] = set()
        for chk in retrieved_chunks:
            src = chk.get("source") or chk.get("metadata", {}).get("source_url", "")
            title = chk.get("title") or chk.get("metadata", {}).get("title", "")
            if src:
                retrieved_sources.add(self._normalize_link(src))
            if title:
                retrieved_sources.add(title.lower().strip())

        covered: List[str] = []
        missing: List[str] = []

        for req_link in required_links:
            slug = self._normalize_link(req_link)
            # Check if slug or main tokens of slug appear in retrieved sources or chunk texts
            is_found = False
            if slug in retrieved_sources:
                is_found = True
            else:
                # Check if significant title words match
                slug_words = [w for w in slug.split() if len(w) > 3]
                if slug_words:
                    for chk in retrieved_chunks:
                        txt = (chk.get("text") or chk.get("plain_text") or "").lower()
                        if all(w in txt for w in slug_words):
                            is_found = True
                            break

            if is_found:
                covered.append(req_link)
            else:
                missing.append(req_link)

        coverage = round(len(covered) / total_req, 4) if total_req > 0 else 0.0
        hit_rate = 1.0 if len(covered) > 0 else 0.0
        source_recall = coverage
        retrieved_req_count = len(covered)
        hop_cov = coverage
        path_comp = 1.0 if len(missing) == 0 else round(len(covered) / total_req, 4)

        # Citation coverage: check if covered links/slugs appear in generated answer
        citation_cov = 0.0
        if generated_answer and total_req > 0:
            ans_lower = generated_answer.lower()
            cited_count = 0
            for req_link in required_links:
                slug = self._normalize_link(req_link)
                slug_words = [w for w in slug.split() if len(w) > 3]
                if slug in ans_lower or (slug_words and all(w in ans_lower for w in slug_words)):
                    cited_count += 1
            citation_cov = round(cited_count / total_req, 4)
        elif len(missing) == 0:
            citation_cov = 1.0

        # Context precision: ratio of retrieved chunks that were actually relevant
        if retrieved_chunks:
            relevant_chunks_count = 0
            for chk in retrieved_chunks:
                chk_txt = (chk.get("text") or "").lower()
                if any(self._normalize_link(req) in chk_txt for req in required_links):
                    relevant_chunks_count += 1
            precision = round(relevant_chunks_count / len(retrieved_chunks), 4)
        else:
            precision = 0.0

        return RetrievalResult(
            question_id=qid,
            hit_rate=hit_rate,
            evidence_coverage=coverage,
            total_required_sources=total_req,
            retrieved_sources_count=len(retrieved_chunks),
            covered_sources=covered,
            missing_sources=missing,
            context_precision=precision,
            source_recall=source_recall,
            retrieved_required_source_count=retrieved_req_count,
            hop_coverage=hop_cov,
            path_completeness=path_comp,
            citation_coverage=citation_cov,
            details={
                "required_count": total_req,
                "covered_count": len(covered),
                "missing_count": len(missing),
                "source_recall": source_recall,
                "path_completeness": path_comp,
            }
        )
