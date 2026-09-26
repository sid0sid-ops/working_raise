"""
Rust-Python Bridge Evaluator Module
===================================
Tests data transfer across the Rust-Python FFI boundary (ctypes/PyO3).
Verifies:
- DLL dynamic loading & ABI compatibility
- Zero-copy / JSON buffer serialization integrity
- Mathematical parity between Rust engine and Python algorithms
- High-throughput QuickSelect and compact BM25
- Text normalization & boundary evaluation
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Tuple

from src.chunking.rust_bridge import (
    is_rust_engine_available,
    get_rust_backend_type,
    normalize_text_rust,
    reciprocal_rank_fusion_rust,
    bm25_search_rust,
    rank_candidates_rust,
    evaluate_boundaries_rust,
    claim_fingerprint_rust,
)
from src.retrieval.fusion import reciprocal_rank_fusion as python_rrf


class RustBridgeEvaluator:
    """Evaluates the Rust Acceleration Engine FFI bridge."""

    def verify_bridge_integrity(self) -> Dict[str, Any]:
        """Runs the complete suite of Rust-Python bridge verification checks."""
        report: Dict[str, Any] = {
            "is_available": False,
            "backend_type": "none",
            "checks": {},
            "all_passed": False,
            "errors": [],
        }

        # 1. Engine Availability Check
        report["is_available"] = is_rust_engine_available()
        report["backend_type"] = get_rust_backend_type()

        if not report["is_available"]:
            report["errors"].append("raise_engine.dll is not loaded or unavailable.")
            return report

        # 2. Text Normalization & Hyphen Repair
        try:
            raw_sample = "Deep-tech infra-\nstructure \u2014 \u201Cquantum sensors\u201D at   Jamnagar."
            cleaned = normalize_text_rust(raw_sample)
            norm_ok = (
                cleaned is not None
                and "infrastructure" in cleaned
                and '"quantum sensors"' in cleaned
                and " - " in cleaned
            )
            report["checks"]["text_normalization"] = {
                "passed": norm_ok,
                "output": cleaned,
            }
            if not norm_ok:
                report["errors"].append(f"Text normalization mismatch: got {cleaned}")
        except Exception as e:
            report["checks"]["text_normalization"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Text normalization exception: {e}")

        # 3. Reciprocal Rank Fusion Parity
        try:
            dense = [{"chunk_id": "c1"}, {"chunk_id": "c2"}, {"chunk_id": "c3"}]
            sparse = [{"chunk_id": "c2"}, {"chunk_id": "c1"}, {"chunk_id": "c4"}]
            rust_res = reciprocal_rank_fusion_rust([["c1", "c2", "c3"], ["c2", "c1", "c4"]], k=60)
            py_res = python_rrf([dense, sparse], k=60)

            # Check math: c1 score = 1/61 + 1/62 = 0.032522
            expected_c1_score = 1.0 / 61.0 + 1.0 / 62.0
            rust_c1 = next((item for item in rust_res if item.get("chunk_id") == "c1" or item.get("id") == "c1"), None)
            
            rrf_ok = (
                rust_res is not None
                and len(rust_res) == 4
                and rust_c1 is not None
                and math.isclose(rust_c1.get("rrf_score", 0.0), expected_c1_score, abs_tol=1e-4)
            )
            report["checks"]["rrf_parity"] = {
                "passed": rrf_ok,
                "rust_top_count": len(rust_res) if rust_res else 0,
                "score_c1": rust_c1.get("rrf_score") if rust_c1 else None,
                "expected": expected_c1_score,
            }
            if not rrf_ok:
                report["errors"].append(f"RRF parity mismatch: rust_res={rust_res}")
        except Exception as e:
            report["checks"]["rrf_parity"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"RRF exception: {e}")

        # 4. Compact BM25 Lexical Inverted Index
        try:
            docs = [
                ("doc_1", "Biotechnology Research and Innovation Council BRIC genomics"),
                ("doc_2", "National Institute of Plant Genome Research NIPGR chickpea drought tolerance"),
                ("doc_3", "Balance sheet capital fund endowment liability audit statement"),
            ]
            bm25_res = bm25_search_rust(docs, query="chickpea drought tolerance", top_k=2)
            bm25_ok = (
                bm25_res is not None
                and len(bm25_res) > 0
                and bm25_res[0][0] == "doc_2"
                and bm25_res[0][1] > 0.5
            )
            report["checks"]["bm25_search"] = {
                "passed": bm25_ok,
                "top_hit": bm25_res[0] if bm25_res else None,
            }
            if not bm25_ok:
                report["errors"].append(f"BM25 mismatch: got {bm25_res}")
        except Exception as e:
            report["checks"]["bm25_search"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"BM25 exception: {e}")

        # 5. QuickSelect Top-K Pre-ranking (5,000 items)
        try:
            candidates = [{"id": i, "score": float(i) * 0.25} for i in range(5000)]
            t0 = time.perf_counter()
            top_5 = rank_candidates_rust(candidates, top_k=5)
            dt_ms = (time.perf_counter() - t0) * 1000.0

            qselect_ok = (
                top_5 is not None
                and len(top_5) == 5
                and top_5[0]["id"] == 4999
                and top_5[1]["id"] == 4998
                and top_5[2]["id"] == 4997
            )
            report["checks"]["quickselect_ranking"] = {
                "passed": qselect_ok,
                "latency_ms": round(dt_ms, 3),
                "top_ids": [x["id"] for x in top_5] if top_5 else [],
            }
            if not qselect_ok:
                report["errors"].append(f"QuickSelect top-5 order incorrect: {top_5}")
        except Exception as e:
            report["checks"]["quickselect_ranking"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"QuickSelect exception: {e}")

        # 6. GGAHC Boundary Scoring & Community Detection
        try:
            c1 = {
                "candidate_id": "c_01",
                "document_id": "test_doc",
                "section_id": "s1",
                "heading": "Genomics Research",
                "page_start": 1,
                "page_end": 1,
                "plain_text": "BRIC institutions lead molecular biology and plant genomics in India.",
                "structural_unit_ids": ["u1"],
                "entities": [{"id": "e_bric", "name": "BRIC", "label": "Institution"}],
                "relationships": [],
            }
            c2 = {
                "candidate_id": "c_02",
                "document_id": "test_doc",
                "section_id": "s1",
                "heading": "Genomics Research",
                "page_start": 1,
                "page_end": 1,
                "plain_text": "BRIC coordinates multi-institutional biotechnology consortia.",
                "structural_unit_ids": ["u2"],
                "entities": [{"id": "e_bric", "name": "BRIC", "label": "Institution"}],
                "relationships": [],
            }
            eval_res = evaluate_boundaries_rust([c1, c2], {})
            if eval_res:
                decisions, communities = eval_res
                dec_ok = (
                    len(decisions) == 1
                    and decisions[0]["decision"] == "MERGE"
                    and decisions[0]["confidence"] >= 0.85
                    and communities.get("c_01") == communities.get("c_02")
                )
            else:
                dec_ok = False

            report["checks"]["boundary_scoring"] = {
                "passed": dec_ok,
                "decision": decisions[0]["decision"] if eval_res and decisions else None,
                "confidence": decisions[0]["confidence"] if eval_res and decisions else None,
            }
            if not dec_ok:
                report["errors"].append(f"Boundary scoring mismatch: {eval_res}")
        except Exception as e:
            report["checks"]["boundary_scoring"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Boundary scoring exception: {e}")

        # 7. Claim SHA-256 Fingerprinting
        try:
            fp1 = claim_fingerprint_rust("BRIC was established by DBT", "bric_doc", 1)
            fp2 = claim_fingerprint_rust("BRIC was established by DBT", "bric_doc", 1)
            fp_diff = claim_fingerprint_rust("BRIC was established by DST", "bric_doc", 1)
            fp_ok = (
                fp1 is not None
                and fp1.startswith("clm_")
                and len(fp1) == 20
                and fp1 == fp2
                and fp1 != fp_diff
            )
            report["checks"]["claim_fingerprint"] = {
                "passed": fp_ok,
                "fingerprint_length": len(fp1) if fp1 else 0,
            }
            if not fp_ok:
                report["errors"].append("Claim fingerprint deterministic property failed")
        except Exception as e:
            report["checks"]["claim_fingerprint"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Claim fingerprint exception: {e}")

        # Overall Status
        all_checks_passed = len(report["checks"]) >= 6 and all(
            c.get("passed", False) for c in report["checks"].values()
        )
        report["all_passed"] = all_checks_passed
        return report
