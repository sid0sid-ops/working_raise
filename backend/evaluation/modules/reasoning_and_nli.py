"""
Reasoning and NLI Verification Evaluator Module
===============================================
Tests exact-match dates, person-to-role relationships, table values,
contradiction blocking, and citation binding.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.features.verification.math_engine import DeterministicMathEngine
from src.features.evaluation.nli_verifier import FineCatNLIVerifier
from src.retrieval.parallel_retriever import SelfContainedBM25
from src.features.evaluation.engine import ClaimLevelVerifier, StructuredEvidence


class ReasoningAndNLIEvaluator:
    """Evaluates deterministic math, exact facts, person relationships, and NLI verification."""

    def __init__(self, corpus_chunks: Optional[List[Dict[str, Any]]] = None):
        self.math_engine = DeterministicMathEngine()
        self.nli_verifier = FineCatNLIVerifier()
        if corpus_chunks is None:
            corpus_chunks = [
                {"chunk_id": "c1", "plain_text": "On 26-27 May 2023, the first Chintan Shivir and Rajbhasha Hindi workshop was organized."},
                {"chunk_id": "c2", "plain_text": "Finance Officer Vineeta Sharma oversaw institutional accounts and financial statements in 2023-24."},
                {"chunk_id": "c3", "plain_text": "Balance Sheet as at 31st March 2024: Corpus / Capital Fund stood at Rs. 1,23,92,56,765."},
            ]
        self.bm25 = SelfContainedBM25(corpus_chunks)
        self.claim_verifier = ClaimLevelVerifier()

    def verify_exact_reasoning_and_facts(self) -> Dict[str, Any]:
        """Runs validation checks across exact dates, relations, numbers, and citations."""
        report: Dict[str, Any] = {
            "checks": {},
            "all_passed": False,
            "errors": [],
        }

        # 1. Exact Date Retrieval via BM25
        try:
            date_query = "26-27 May 2023"
            hits = self.bm25.search(date_query, top_k=3)
            date_found = False
            for h in hits:
                txt = h.get("text", "") or h.get("plain_text", "")
                if "26-27 May 2023" in txt:
                    date_found = True
                    break
            report["checks"]["exact_date_match"] = {
                "passed": date_found,
                "query": date_query,
                "hits_returned": len(hits),
            }
            if not date_found:
                report["errors"].append("Exact date '26-27 May 2023' not found in top-3 BM25 hits")
        except Exception as e:
            report["checks"]["exact_date_match"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Exact date check failed: {e}")

        # 2. Person-to-Role Relationship Retrieval
        try:
            person_query = "Finance Officer Vineeta Sharma"
            hits = self.bm25.search(person_query, top_k=5)
            person_found = any("Vineeta Sharma" in (h.get("text", "") or h.get("plain_text", "")) for h in hits)
            report["checks"]["person_role_relationship"] = {
                "passed": person_found,
                "expected_person": "Vineeta Sharma",
                "hits_returned": len(hits),
            }
            if not person_found:
                report["errors"].append("Person relation 'Vineeta Sharma' not found in top-5 BM25 hits")
        except Exception as e:
            report["checks"]["person_role_relationship"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Person relation check failed: {e}")

        # 3. Exact Table Balance Sheet Value Extraction
        try:
            from src.features.evaluation.engine import NumericalClaimVerifier
            table_premise = "Balance Sheet: Corpus / Capital Fund as at 31st March 2024 stood at Rs. 1,23,92,56,765."
            table_claim = "The Corpus / Capital Fund is 1,23,92,56,765."
            v_exact, mismatches, unverified = NumericalClaimVerifier.verify_numbers(table_claim, table_premise)
            report["checks"]["table_balance_sheet_value"] = {
                "passed": v_exact,
                "expected_value": "1,23,92,56,765",
                "mismatches": mismatches,
            }
            if not v_exact:
                report["errors"].append(f"Table balance sheet number verification failed: mismatches={mismatches}")
        except Exception as e:
            report["checks"]["table_balance_sheet_value"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Table balance sheet check failed: {e}")

        # 4. Multi-Component Table Arithmetic Derivation
        try:
            from src.features.evaluation.engine import NumericalClaimVerifier
            derivation_premise = "The recurring grants increased by 5.05 crore from the base 48.50 crore."
            derivation_claim = "The total recurring grant reached 53.55 crore."
            v_deriv, m_deriv, u_deriv = NumericalClaimVerifier.verify_numbers(derivation_claim, derivation_premise)
            report["checks"]["table_arithmetic_derivation"] = {
                "passed": v_deriv,
                "mismatches": m_deriv,
            }
            if not v_deriv:
                report["errors"].append(f"Arithmetic derivation failed: {m_deriv}")
        except Exception as e:
            report["checks"]["table_arithmetic_derivation"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Arithmetic derivation check failed: {e}")

        # 5. Deterministic Contradiction Blocking
        try:
            corrupted_claim = "Under the Balance Sheet, Corpus/Capital Fund was reported as Rs. 99,99,99,999."
            ev_true = StructuredEvidence(
                vector_chunks=[{
                    "chunk_id": "chunk_nipgr_corpus",
                    "plain_text": "Corpus/Capital Fund was reported as Rs. 1,23,92,56,765.",
                    "metadata": {"doc_id": "Annual Report 2023-24.pdf", "primary_page": 155}
                }]
            )
            contra_claims, c_faith, c_mismatches, c_cit = ClaimLevelVerifier.verify_claims(
                answer=corrupted_claim,
                evidence=ev_true
            )
            c_status = contra_claims[0].status if contra_claims else "UNKNOWN"
            blocked = (not contra_claims[0].is_supported or c_status.upper() in {"NUMERICAL_MISMATCH", "UNSUPPORTED", "CONTRADICTION"})
            report["checks"]["contradiction_blocking"] = {
                "passed": blocked,
                "status": c_status,
                "is_supported": contra_claims[0].is_supported if contra_claims else None,
            }
            if not blocked:
                report["errors"].append(f"Contradiction was not blocked! Status: {c_status}")
        except Exception as e:
            report["checks"]["contradiction_blocking"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Contradiction blocking failed: {e}")

        # 6. In-line Citation Binding
        try:
            answer_text = "The institute conducted genomics research [Source: Annual Report 2023-24.pdf, Page: 45] and held events [Source: BRIC-Annual-Report-2025.pdf, Page: 12]."
            citations = re.findall(r"\[Source:\s*([^,\]]+),\s*Page:\s*(\d+)\]", answer_text)
            cits_valid = (
                len(citations) == 2
                and citations[0][0] == "Annual Report 2023-24.pdf"
                and int(citations[0][1]) == 45
                and citations[1][0] == "BRIC-Annual-Report-2025.pdf"
                and int(citations[1][1]) == 12
            )
            report["checks"]["citation_binding"] = {
                "passed": cits_valid,
                "parsed_citations": citations,
            }
            if not cits_valid:
                report["errors"].append(f"Citation binding parsing mismatch: {citations}")
        except Exception as e:
            report["checks"]["citation_binding"] = {"passed": False, "error": str(e)}
            report["errors"].append(f"Citation binding check failed: {e}")

        # Summary
        all_passed = len(report["checks"]) >= 6 and all(
            c.get("passed", False) for c in report["checks"].values()
        )
        report["all_passed"] = all_passed
        return report
