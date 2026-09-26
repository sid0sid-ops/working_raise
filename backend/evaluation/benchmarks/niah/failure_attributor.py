"""
RAISE NIAH Benchmark — Scientific Failure Attribution Engine
Classifies benchmark query failures into discrete architectural stages:
  1. EMBEDDING_REPRESENTATION_FAILURE
  2. RETRIEVAL_FAILURE (ChromaDB / Vector Search)
  3. RERANKING_FAILURE (Cross-Encoder demoted needle)
  4. GRAPH_TRAVERSAL_FAILURE (Neo4j / Knowledge Graph Disconnection)
  5. CONTEXT_ASSEMBLY_FAILURE (Truncation / Context Budget Overflow)
  6. GENERATION_FAILURE (LLM In-Context Extraction / Hallucination / Refusal)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from .component_probes import (
    ChromaDBProbeResult,
    EmbeddingProbeResult,
    GraphTraversalProbeResult,
    LLMGenerationProbeResult,
    RerankerProbeResult,
)


class FailureStage(str, Enum):
    SUCCESS = "SUCCESS"
    ADVERSARIAL_RANKING_DEMOTION = "ADVERSARIAL_RANKING_DEMOTION"
    EMBEDDING_REPRESENTATION_FAILURE = "EMBEDDING_REPRESENTATION_FAILURE"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    RERANKING_FAILURE = "RERANKING_FAILURE"
    GRAPH_TRAVERSAL_FAILURE = "GRAPH_TRAVERSAL_FAILURE"
    CONTEXT_ASSEMBLY_FAILURE = "CONTEXT_ASSEMBLY_FAILURE"
    GENERATION_FAILURE = "GENERATION_FAILURE"


@dataclass
class FailureAttribution:
    stage: FailureStage
    root_cause: str
    recommended_fix: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "root_cause": self.root_cause,
            "recommended_fix": self.recommended_fix,
            "details": self.details,
        }


class FailureAttributor:
    """
    Diagnostic decision tree that pinpoints the exact failure point in the GraphRAG pipeline.
    Enforces strict Top-1 precision on adversarial distractor benchmarks.
    """

    @staticmethod
    def diagnose(
        embedding_res: Optional[EmbeddingProbeResult] = None,
        retrieval_res: Optional[ChromaDBProbeResult] = None,
        reranker_res: Optional[RerankerProbeResult] = None,
        graph_res: Optional[GraphTraversalProbeResult] = None,
        generation_res: Optional[LLMGenerationProbeResult] = None,
        needle_case: Optional[Any] = None,
    ) -> FailureAttribution:
        """
        Executes a diagnostic decision tree over probe results.
        """
        # 1. Check Graph Traversal for multi-hop graph needles
        if graph_res and not graph_res.traversal_success:
            return FailureAttribution(
                stage=FailureStage.GRAPH_TRAVERSAL_FAILURE,
                root_cause=f"Graph traversal failed: Seed entity '{graph_res.seed_id}' was {'' if graph_res.seed_found else 'NOT '}found, but target was NOT reachable within max hops.",
                recommended_fix="Increase Cypher traversal hops (e.g., from 2 to 3), improve entity extraction, or verify relationship links.",
                details=graph_res.to_dict(),
            )

        # 2. Check ChromaDB / Vector Retrieval (Top-K Recall)
        if retrieval_res and not retrieval_res.top_k_recall:
            if embedding_res and not embedding_res.representation_success and embedding_res.similarity_margin < 0:
                return FailureAttribution(
                    stage=FailureStage.EMBEDDING_REPRESENTATION_FAILURE,
                    root_cause=f"Embedding collision: Distractor paragraph scored higher ({embedding_res.max_distractor_sim:.4f}) than the needle ({embedding_res.query_needle_sim:.4f}), causing retrieval miss.",
                    recommended_fix="Utilize asymmetric task prefixes, switch to a domain-fine-tuned embedding model (e.g. BGE-M3 or Qwen3-Embedding), or adjust chunking.",
                    details=embedding_res.to_dict(),
                )
            return FailureAttribution(
                stage=FailureStage.RETRIEVAL_FAILURE,
                root_cause=f"ChromaDB failed to retrieve the needle chunk within top-{retrieval_res.top_k} (rank: {retrieval_res.gold_rank or 'Not in results'}).",
                recommended_fix=f"Increase retrieval top_k, increase candidate fetch size (n_fetch), add BM25 sparse hybrid fusion, or optimize chunk overlap.",
                details=retrieval_res.to_dict(),
            )
        elif not retrieval_res and embedding_res and not embedding_res.representation_success and embedding_res.similarity_margin < 0:
            return FailureAttribution(
                stage=FailureStage.EMBEDDING_REPRESENTATION_FAILURE,
                root_cause=f"Embedding collision: Distractor paragraph scored higher ({embedding_res.max_distractor_sim:.4f}) than the needle ({embedding_res.query_needle_sim:.4f}).",
                recommended_fix="Utilize asymmetric task prefixes, switch to a domain-fine-tuned embedding model (e.g. BGE-M3 or Qwen3-Embedding), or adjust chunking.",
                details=embedding_res.to_dict(),
            )

        # 3. Check for Adversarial Distractor Ranking Demotion (Top-1 Precision)
        if needle_case and getattr(needle_case, "needle_type", None) and str(needle_case.needle_type).upper().endswith("ADVERSARIAL_DISTRACTOR"):
            final_rank = None
            if reranker_res and reranker_res.post_rerank_rank:
                final_rank = reranker_res.post_rerank_rank
            elif retrieval_res and retrieval_res.gold_rank:
                final_rank = retrieval_res.gold_rank

            if final_rank and final_rank > 1:
                return FailureAttribution(
                    stage=FailureStage.ADVERSARIAL_RANKING_DEMOTION,
                    root_cause=f"Adversarial distractor prioritized ahead of gold evidence: Gold needle ranked #{final_rank} (Top-1 precision failure; distractor took rank #1).",
                    recommended_fix="Calibrate Cross-Encoder reranker score margin, apply BM25 exact entity boosting, or implement negative distractor filtering.",
                    details={"gold_rank": final_rank, "needle_id": getattr(needle_case, "needle_id", "unknown")},
                )

        # 4. Check Reranker
        if reranker_res and not reranker_res.reranker_retained:
            return FailureAttribution(
                stage=FailureStage.RERANKING_FAILURE,
                root_cause=f"Cross-encoder demoted needle from pre-rank {reranker_res.pre_rerank_rank} to post-rank {reranker_res.post_rerank_rank} (dropped outside top-{reranker_res.top_n}).",
                recommended_fix="Adjust CrossEncoder score calibration, add keyword lexical overlap boost, or expand reranker candidate retention window (top_n).",
                details=reranker_res.to_dict(),
            )

        # 5. Check Context Assembly
        if generation_res and not generation_res.gold_in_context:
            return FailureAttribution(
                stage=FailureStage.CONTEXT_ASSEMBLY_FAILURE,
                root_cause="Needle was retrieved by search but dropped or truncated before assembling the final LLM prompt context.",
                recommended_fix="Increase max_context_chunks or max prompt token budget in synthesis node.",
                details=generation_res.to_dict(),
            )

        # 6. Check Final Generation
        if generation_res and not generation_res.generation_success:
            cause = "Refusal triggered (ungrounded refusal)" if generation_res.refusal_detected else "LLM failed to extract exact needle answer despite presence in context"
            return FailureAttribution(
                stage=FailureStage.GENERATION_FAILURE,
                root_cause=f"Generation error: {cause}. Output: '{generation_res.generated_answer[:150]}...'",
                recommended_fix="Refine synthesis system prompt to prioritize direct factual extraction and cite exact figures.",
                details=generation_res.to_dict(),
            )

        return FailureAttribution(
            stage=FailureStage.SUCCESS,
            root_cause="None. Needle successfully retrieved, preserved in context, and synthesized.",
            recommended_fix="None required. Benchmark test passed all stages.",
            details={"status": "PASSED"},
        )
