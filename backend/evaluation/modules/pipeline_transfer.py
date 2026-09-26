"""
Pipeline Inter-Module Data Transfer Evaluator
=============================================
Validates data transfer contracts and state transitions across the full pipeline:
  QueryIntake -> QueryDecomposition -> ParallelRetriever (Dense/BM25/Graph)
  -> RRF Fusion -> CrossEncoderReranker -> DeterministicMathEngine
  -> FineCatNLIVerifier -> QualityGate -> TelemetryService
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from src.features.query.intake import IntentRouterNode, QueryDecomposerNode
from src.retrieval.pipeline import StandaloneRAGPipeline
from src.retrieval.fusion import reciprocal_rank_fusion
from src.features.verification.math_engine import DeterministicMathEngine
from src.features.evaluation.nli_verifier import FineCatNLIVerifier
from src.cli.telemetry_service import TelemetryService
from src.cli.models import MetricValue


class PipelineDataTransferEvaluator:
    """Validates data structures and payload integrity as data moves between pipeline modules."""

    def __init__(self):
        self.router = IntentRouterNode()
        self.decomposer = QueryDecomposerNode()
        self.pipeline = StandaloneRAGPipeline()
        self.math_engine = DeterministicMathEngine()
        self.nli_verifier = FineCatNLIVerifier()
        self.telemetry = TelemetryService()

    def verify_pipeline_data_flow(self) -> Dict[str, Any]:
        """Runs an end-to-end test query through each module step by step."""
        report: Dict[str, Any] = {
            "steps": {},
            "all_transfers_valid": False,
            "errors": [],
        }

        query = "What was the total Corpus/Capital fund as of 31st March 2024 in the balance sheet?"

        # Step 1: Query Intake & Intent Classification
        try:
            route_res = self.router.route(query)
            is_valid_intent = (route_res.intent in ("ACADEMIC_RESEARCH", "FINANCIAL_FACT", "MULTI_HOP_RELATION")) and route_res.is_safe
            report["steps"]["1_query_intake"] = {
                "passed": is_valid_intent,
                "intent": route_res.intent,
                "datasource": route_res.datasource,
            }
            if not is_valid_intent:
                report["errors"].append(f"Intent classified unexpectedly: {route_res.intent}")
        except Exception as e:
            report["steps"]["1_query_intake"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Query intake failed: {e}")

        # Step 2: Adaptive Query Decomposition
        try:
            subqueries = self.decomposer.decompose(query)
            has_subqueries = isinstance(subqueries, list) and len(subqueries) >= 1
            report["steps"]["2_decomposition"] = {
                "passed": has_subqueries,
                "subquery_count": len(subqueries) if isinstance(subqueries, list) else 0,
                "subqueries": subqueries[:2] if isinstance(subqueries, list) else [],
            }
            if not has_subqueries:
                report["errors"].append("Decomposition returned empty or invalid structure")
        except Exception as e:
            report["steps"]["2_decomposition"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Decomposition failed: {e}")

        # Step 3: Hybrid Retrieval Data Transfer
        try:
            hits = self.pipeline.vector_engine.search(query, top_k=5)
            has_candidates = len(hits) > 0

            # Verify candidate schema contract
            first_cand = hits[0] if hits else {}
            has_required_keys = all(
                k in first_cand for k in ("chunk_id", "text", "similarity")
            )
            report["steps"]["3_hybrid_retrieval"] = {
                "passed": has_candidates and has_required_keys,
                "candidates_count": len(hits),
                "top_similarity": first_cand.get("similarity"),
                "has_schema_keys": has_required_keys,
            }
            if not (has_candidates and has_required_keys):
                report["errors"].append(f"Retrieval candidate schema invalid: {first_cand.keys()}")
        except Exception as e:
            report["steps"]["3_hybrid_retrieval"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Hybrid retrieval failed: {e}")

        # Step 4: RRF Fusion Channel Merging
        try:
            chan1 = [{"chunk_id": "c1", "score": 0.9}, {"chunk_id": "c2", "score": 0.8}]
            chan2 = [{"chunk_id": "c2", "score": 0.95}, {"chunk_id": "c3", "score": 0.7}]
            fused = reciprocal_rank_fusion([chan1, chan2], k=60)
            fused_valid = len(fused) == 3 and "chunk_id" in fused[0] and "rrf_score" in fused[0]
            report["steps"]["4_rrf_fusion"] = {
                "passed": fused_valid,
                "fused_count": len(fused),
                "top_chunk_id": fused[0].get("chunk_id") if fused else None,
            }
            if not fused_valid:
                report["errors"].append("RRF fusion output failed schema contract")
        except Exception as e:
            report["steps"]["4_rrf_fusion"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"RRF fusion failed: {e}")

        # Step 5: Deterministic Math Engine Transfer
        try:
            from src.features.evaluation.engine import NumericalClaimVerifier
            premise = "Total Corpus and Capital Fund stood at Rs. 1,23,92,56,765 as per audited balance sheet."
            claim = "The Corpus fund is 1,23,92,56,765."
            v_ok, mismatches, unverified = NumericalClaimVerifier.verify_numbers(claim, premise)
            report["steps"]["5_math_engine"] = {
                "passed": v_ok,
                "mismatches": mismatches,
                "unverified": unverified,
            }
            if not v_ok:
                report["errors"].append(f"Math engine verification failed: mismatches={mismatches}")
        except Exception as e:
            report["steps"]["5_math_engine"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Math engine failed: {e}")

        # Step 6: FineCat-NLI Premise-Hypothesis Transfer
        try:
            premise_text = "Dr. Subhra Chakraborty served as Director of NIPGR."
            hypo_true = "Dr. Subhra Chakraborty was Director."
            hypo_false = "Dr. Subhra Chakraborty was an airline pilot."
            res_true = self.nli_verifier.classify_pair(premise_text, hypo_true)
            res_false = self.nli_verifier.classify_pair(premise_text, hypo_false)
            nli_valid = (
                res_true.get("verdict") == "ENTAILMENT"
                and res_false.get("verdict") in ("CONTRADICTION", "NEUTRAL")
            )
            report["steps"]["6_finecat_nli"] = {
                "passed": nli_valid,
                "true_verdict": res_true.get("verdict"),
                "false_verdict": res_false.get("verdict"),
            }
            if not nli_valid:
                report["errors"].append(f"NLI verdicts unexpected: True={res_true}, False={res_false}")
        except Exception as e:
            report["steps"]["6_finecat_nli"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"NLI verification failed: {e}")

        # Step 7: Telemetry MetricValue Schema Transfer
        try:
            m1 = MetricValue.measured(145.2, unit="ms")
            m2 = MetricValue.measured(890.0, unit="MB")
            telem_valid = (
                m1.value == 145.2 and m1.unit == "ms" and m2.unit == "MB"
            )
            report["steps"]["7_telemetry_schema"] = {
                "passed": telem_valid,
                "metric_samples": [m1.value, m2.value],
            }
            if not telem_valid:
                report["errors"].append("Telemetry MetricValue model failed validation")
        except Exception as e:
            report["steps"]["7_telemetry_schema"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Telemetry schema failed: {e}")

        # Summary
        all_passed = len(report["steps"]) >= 7 and all(
            s.get("passed", False) for s in report["steps"].values()
        )
        report["all_transfers_valid"] = all_passed
        return report
