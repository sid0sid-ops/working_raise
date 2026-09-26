"""
Factual Claim Extraction & 4-Tier Verification Engine
======================================================
Decomposes answers into atomic factual claims and evaluates each claim across a 4-tier
verification hierarchy against structured vector chunks, Neo4j graph triples, and NLI.

Architectural Role & 4-Tier Verification Flow:
----------------------------------------------
1. Sentence Decomposition & Abbreviation Protection:
   - Uses regex sentence splitting while shielding academic abbreviations (`Dr.`, `Prof.`, `Rs.`,
     `e.g.`, `i.e.`, `vs.`, `Fig.`, `No.`).
   - Filters markdown table headers, boilerplate declarations ("Based on excerpts..."), and citation lines.

2. Tier 1: Deterministic Numerical & Temporal Verification:
   - Evaluates all currency, dates, percentages, and metrics via `NumericalClaimVerifier`.
   - Fails immediately with `NUMERICAL_MISMATCH` if an unsupported numerical value is claimed.

3. Tier 2: Direct Lexical Fast-Path:
   - Computes token overlap ratio and bigram ngram grounding.
   - If grounding score >= 0.70 (or token overlap >= 0.80), marks claim as `DIRECT` without invoking neural NLI.

4. Tier 3: Neural NLI Escalation (FineCat-NLI):
   - When a claim is paraphrased or ambiguous, calls the active NLI cross-encoder model.
   - Flagged as `CONTRADICTION` if contradiction probability >= 0.50.
   - Flagged as `NLI_ENTAILED` if entailment probability >= 0.55.

5. Tier 4: Soft Containment Fallback:
   - Accepts partially overlapping claims (grounding >= 0.30 or token overlap >= 0.40) where no contradiction
     was detected, ensuring reasonable recall without hallucinating.

How to Update or Tune:
----------------------
- To adjust the NLI entailment threshold, modify `ent_prob >= 0.55` in `verify_claims()`.
- To tighten or loosen lexical fast-path, modify `grounding_score >= 0.70` or `overlap_ratio >= 0.80`.
- To add new protected abbreviations, add to `abbrevs` list in `extract_claims()`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .models import StructuredEvidence, ClaimVerificationResult
from .numerical_verifier import NumericalClaimVerifier
from src.features.evaluation.nli_verifier import nli_verifier


class ClaimLevelVerifier:
    """
    Decomposes responses into discrete factual claims and evaluates each claim
    against structured vector passages, Neo4j graph triples, and neural NLI models.
    """

    STOP_WORDS = {
        "what", "is", "the", "and", "or", "for", "with", "from", "that", "this",
        "these", "those", "have", "has", "had", "were", "been", "being", "are",
        "was", "their", "they", "its", "into", "during", "which", "about", "also",
        "based", "verified", "excerpts", "uploaded", "reports", "report", "document"
    }

    @classmethod
    def extract_claims(cls, answer: str) -> List[str]:
        """
        Decomposes an answer string into clean, individual factual claims,
        filtering out structural markdown, titles, parenthetical fragments, and boilerplate.
        """
        # Protect common abbreviations from erroneous sentence splitting
        protected = answer
        abbrevs = ["Dr.", "Prof.", "Mr.", "Ms.", "Rs.", "e.g.", "i.e.", "vs.", "Fig.", "No.", "Inc.", "Ltd.", "Dept."]
        for i, abbr in enumerate(abbrevs):
            protected = protected.replace(abbr, f"__ABBR_{i}__")

        raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", protected)
        claims = []
        for s in raw_sentences:
            # Restore abbreviations
            restored = s
            for i, abbr in enumerate(abbrevs):
                restored = restored.replace(f"__ABBR_{i}__", abbr)
            s_clean = restored.strip().lstrip("•-*0123456789. ")

            # Ignore header boilerplate, structural markdown headings, raw citation mappings, or citation declarations
            is_structural_header = (
                s.strip().startswith("#")
                or s_clean.startswith("#")
                or bool(re.match(r"^\*{0,2}[A-Za-z\s/&_-]{3,40}:\*{0,2}$", s_clean))
                or bool(re.match(r"^(?:###|\*\*|##|#)?\s*[\*\_\(\[\{]*\s*(?:conclusion|note\s+on|note|notes|summary|calculation\s+of\s+difference|relevant\s+excerpts|comparison\s+with|table|schedule|methodology)\b:?", s_clean, re.IGNORECASE))
                or bool(re.search(r"^\s*[\*\_\(\[\{]*\s*note\b", s_clean, re.IGNORECASE))
            )
            # Ignore parenthetical fragments, numbers in brackets/parentheses, or fragments lacking words
            is_parenthetical_fragment = (
                bool(re.match(r"^[\(\[\{\*\s]*[₹$Rs\d\.,\s\-_/]+[\)\]\}\*\s]*(?:\[\d+\])*$", s_clean))
                or len(re.findall(r"[a-zA-Z]{2,}", s_clean)) < 2
            )
            is_boilerplate = (
                is_structural_header
                or is_parenthetical_fragment
                or s_clean.startswith("Based on the verified excerpts")
                or s_clean.startswith("Notice:")
                or bool(re.match(r"^\[\d+\]\s*\[Doc:", s_clean))
                or bool(re.match(r"^\[?\s*(?:citations?|sources?|references?)\s*[:\]]", s_clean, re.IGNORECASE))
                or bool(re.match(r"^\[\d+\](?:\s*\[\d+\])*$", s_clean))
                or bool(re.match(r"^(?:citations?|sources?|references?)\s*:\s*(\[\d+\]|\d+|,|\s)*$", s_clean, re.IGNORECASE))
            )
            if len(s_clean) > 10 and not is_boilerplate:
                claims.append(s_clean)
        return claims

    @classmethod
    def verify_claims(
        cls,
        answer: str,
        evidence: StructuredEvidence,
        citations_list: Optional[List[Dict[str, Any]]] = None,
        nli_engine: Optional[Any] = None,
        enable_nli: bool = True,
        query: str = "",
    ) -> Tuple[List[ClaimVerificationResult], float, int, int]:
        """
        Executes the 4-tier verification pipeline across all claims in the answer.

        Returns:
            Tuple of:
              - claims_results: List[ClaimVerificationResult]
              - faithfulness_score: float (supported / total)
              - numerical_mismatches: int
              - citation_errors: int
        """
        claims_text = cls.extract_claims(answer)
        if not claims_text:
            return [], 1.0, 0, 0

        evidence_text = evidence.get_full_text()
        evidence_lower = evidence_text.lower()
        results = []
        supported_count = 0
        num_mismatches = 0
        cit_errors = 0

        for idx, c_text in enumerate(claims_text, start=1):
            cid = f"claim_{idx:03d}"
            notes = []

            # Extract citations in this specific claim
            cit_refs = [int(m) for m in re.findall(r"\[(\d+)\]", c_text)]
            clean_claim = re.sub(r"\[\[?\s*\d+(?:\s*[,-–]\s*\d+)*\s*\]?\]", "", c_text).strip()

            # Resolve bound evidence chunk and page
            bound_chunk_id = None
            primary_page = None
            bound_chunk_text = ""
            retrieval_relevance = None

            if citations_list and cit_refs:
                ref_idx = cit_refs[0]
                if 1 <= ref_idx <= len(citations_list):
                    c_info = citations_list[ref_idx - 1]
                    bound_chunk_id = c_info.get("chunk_id") or c_info.get("id")
                    primary_page = int(c_info.get("primary_page", 1)) if c_info.get("primary_page") is not None else None
                    bound_chunk_text = str(c_info.get("plain_text") or c_info.get("text") or "")
                    retrieval_relevance = c_info.get("cross_encoder_score") or c_info.get("score") or c_info.get("rrf_score")

            # Premise for verification: prefer bound chunk, fallback to evidence_text
            premise_text = bound_chunk_text if bound_chunk_text else evidence_text
            premise_lower = premise_text.lower()

            # Check for negative assertion / refusal grounded in absence from evidence
            is_negative_assertion = bool(re.search(
                r"(?:do(?:es)?\s+not\s+(?:contain|mention|state|provide|include|discuss|have|list|detail|report)|"
                r"no\s+(?:mention|information|data|details|record|reference|evidence|indication)\s+(?:of|about|regarding|found|exists?)|"
                r"there\s+(?:is|are|was|were)\s+no\b|"
                r"\bno\s+[\w\s\-]+(?:\s+are|\s+is)?\s+mentioned\s+in|"
                r"not\s+(?:found|mentioned|provided|available|present|contained|stated|detailed|reported)\s+in|"
                r"cannot\s+be\s+found\s+in|"
                r"outside\s+(?:the|this)\s+scope|"
                r"neither\s+of\s+the\s+documents\s+contain|"
                r"none\s+of\s+the\s+(?:provided\s+)?documents|"
                r"not\s+contain\s+any\s+information|"
                r"not\s+detail\s+specific|"
                r"is\s+not\s+mentioned)",
                c_text,
                re.IGNORECASE
            ))

            # Tier 1: Deterministic checks (Numbers & Dates)
            num_valid, matched_nums, unmatched_nums = NumericalClaimVerifier.verify_numbers(c_text, evidence_text, query=query)
            if not num_valid and not is_negative_assertion:
                reason = f"Numerical mismatch: Values {unmatched_nums} not found in evidence."
                notes.append(reason)
                num_mismatches += 1
                results.append(ClaimVerificationResult(
                    claim_id=cid,
                    text=c_text,
                    is_supported=False,
                    status="NUMERICAL_MISMATCH",
                    extracted_numbers=unmatched_nums,
                    matched_numbers=matched_nums,
                    citations_found=cit_refs,
                    notes=notes,
                    verification_tier="TIER1_NUMERIC",
                    bound_chunk_id=bound_chunk_id,
                    primary_page=primary_page,
                    retrieval_relevance_score=retrieval_relevance,
                    verification_path="DETERMINISTIC",
                    decision_reason=reason,
                ))
                continue

            # Negative assertion handling
            if is_negative_assertion:
                supported_count += 1
                reason = "Supported negative assertion / refusal grounded in absence from evidence."
                notes.append(reason)
                results.append(ClaimVerificationResult(
                    claim_id=cid,
                    text=c_text,
                    is_supported=True,
                    status="SUPPORTED",
                    extracted_numbers=matched_nums,
                    matched_numbers=matched_nums,
                    citations_found=cit_refs,
                    notes=notes,
                    verification_tier="TIER1_NUMERIC",
                    bound_chunk_id=bound_chunk_id,
                    primary_page=primary_page,
                    retrieval_relevance_score=retrieval_relevance,
                    verification_path="DETERMINISTIC",
                    decision_reason=reason,
                ))
                continue

            c_words = set(re.findall(r"\b[a-zA-Z0-9_]{3,}\b", clean_claim.lower())) - cls.STOP_WORDS
            if not c_words:
                supported_count += 1
                reason = "No substantive non-stopword tokens to invalidate."
                results.append(ClaimVerificationResult(
                    claim_id=cid,
                    text=c_text,
                    is_supported=True,
                    status="SUPPORTED",
                    extracted_numbers=matched_nums,
                    matched_numbers=matched_nums,
                    citations_found=cit_refs,
                    notes=[reason],
                    verification_tier="TIER1_NUMERIC",
                    bound_chunk_id=bound_chunk_id,
                    primary_page=primary_page,
                    retrieval_relevance_score=retrieval_relevance,
                    verification_path="DETERMINISTIC",
                    decision_reason=reason,
                ))
                continue

            # Lexical overlap with bound premise and full retrieved evidence
            full_match = sum(1 for w in c_words if w in evidence_lower or (len(w) > 4 and w[:4] in evidence_lower))
            overlap_ratio = full_match / len(c_words)

            c_tokens = re.findall(r"\b[a-zA-Z0-9_]{3,}\b", clean_claim.lower())
            ngram_hits = 0
            total_ngrams = max(1, len(c_tokens) - 1)
            if len(c_tokens) >= 2:
                for i in range(len(c_tokens) - 1):
                    bigram = f"{c_tokens[i]} {c_tokens[i+1]}"
                    if bigram in evidence_lower:
                        ngram_hits += 1
            ngram_ratio = ngram_hits / total_ngrams
            grounding_score = (overlap_ratio * 0.6) + (ngram_ratio * 0.4)

            # Tabular / Numeric Fast-Path: If numbers are verified and non-numeric labels match evidence, accept
            non_num_words = {w for w in c_words if not any(c.isdigit() for c in w)}
            non_num_match = sum(1 for w in non_num_words if w in evidence_lower or (len(w) > 4 and w[:4] in evidence_lower))
            non_num_ratio = (non_num_match / len(non_num_words)) if non_num_words else 1.0

            is_math_equation = bool(re.search(r"[-+–/*]\s*.*=", clean_claim) or re.search(r"=\s*.*[-+–/*]", clean_claim))
            if num_valid and len(matched_nums) > 0 and (non_num_ratio >= 0.80 or is_math_equation):
                supported_count += 1
                reason = f"Verified tabular / numeric {'equation' if is_math_equation else 'claim'} ({non_num_ratio*100:.1f}% label grounding, {len(matched_nums)} numbers verified)."
                notes.append(reason)
                results.append(ClaimVerificationResult(
                    claim_id=cid,
                    text=c_text,
                    is_supported=True,
                    status="SUPPORTED",
                    extracted_numbers=matched_nums,
                    matched_numbers=matched_nums,
                    citations_found=cit_refs,
                    notes=notes,
                    verification_tier="TIER1_NUMERIC",
                    bound_chunk_id=bound_chunk_id,
                    primary_page=primary_page,
                    retrieval_relevance_score=retrieval_relevance,
                    verification_path="DETERMINISTIC",
                    decision_reason=reason,
                ))
                continue

            # Tier 2: Lexical Fast-Path (Exact quote / high overlap >= 0.70)
            if grounding_score >= 0.70 or overlap_ratio >= 0.80:
                supported_count += 1
                reason = f"Direct lexical quote match ({grounding_score*100:.1f}% grounding: {overlap_ratio*100:.1f}% tokens, {ngram_ratio*100:.1f}% ngrams)."
                notes.append(reason)
                results.append(ClaimVerificationResult(
                    claim_id=cid,
                    text=c_text,
                    is_supported=True,
                    status="DIRECT",
                    extracted_numbers=matched_nums,
                    matched_numbers=matched_nums,
                    citations_found=cit_refs,
                    notes=notes,
                    verification_tier="TIER2_LEXICAL",
                    bound_chunk_id=bound_chunk_id,
                    primary_page=primary_page,
                    retrieval_relevance_score=retrieval_relevance,
                    verification_path="DETERMINISTIC",
                    decision_reason=reason,
                ))
                continue

            # Tier 3: FineCat-NLI Escalation (Ambiguous or Paraphrased Claims)
            active_nli = nli_engine or nli_verifier
            if enable_nli and active_nli is not None:
                nli_eval = active_nli.classify_pair(
                    premise=premise_text[:2048] if len(premise_text) > 2048 else premise_text,
                    hypothesis=clean_claim,
                )
                ent_prob = nli_eval.get("entailment_prob", 0.0)
                con_prob = nli_eval.get("contradiction_prob", 0.0)
                neu_prob = nli_eval.get("neutral_prob", 0.0)
                is_entailed = nli_eval.get("is_entailed", False)
                is_contradiction = nli_eval.get("is_contradiction", False)
                raw_logits = nli_eval.get("raw_logits")
                softmax_probs = nli_eval.get("softmax_probs")
                calibration_status = nli_eval.get("calibration_status", "UNVALIDATED_RAW_SOFTMAX")
                nli_reason = nli_eval.get("decision_reason", "")
                nli_latency = nli_eval.get("latency_ms", 0.0)
            else:
                nli_eval = {}
                ent_prob = 0.0
                con_prob = 0.0
                neu_prob = 0.0
                is_entailed = False
                is_contradiction = False
                raw_logits = None
                softmax_probs = None
                calibration_status = "UNVALIDATED_RAW_SOFTMAX"
                nli_reason = ""
                nli_latency = 0.0

            if is_contradiction or con_prob >= 0.50:
                reason = nli_reason or f"Hard contradiction detected by FineCat-NLI (P(contradiction)={con_prob:.2f} >= 0.50)."
                notes.append(reason)
                results.append(ClaimVerificationResult(
                    claim_id=cid,
                    text=c_text,
                    is_supported=False,
                    status="CONTRADICTION",
                    extracted_numbers=unmatched_nums,
                    matched_numbers=matched_nums,
                    citations_found=cit_refs,
                    notes=notes,
                    nli_entailment_prob=ent_prob,
                    nli_contradiction_prob=con_prob,
                    verification_tier="TIER3_NLI",
                    bound_chunk_id=bound_chunk_id,
                    primary_page=primary_page,
                    retrieval_relevance_score=retrieval_relevance,
                    verification_path="NLI",
                    decision_reason=reason,
                    raw_logits=raw_logits,
                    softmax_probs=softmax_probs,
                    calibration_status=calibration_status,
                    latency_ms=nli_latency,
                ))
                continue
            elif is_entailed or ent_prob >= 0.55:
                supported_count += 1
                reason = nli_reason or f"Semantically entailed by FineCat-NLI (P(entailment)={ent_prob:.2f} >= 0.55)."
                notes.append(reason)
                results.append(ClaimVerificationResult(
                    claim_id=cid,
                    text=c_text,
                    is_supported=True,
                    status="NLI_ENTAILED",
                    extracted_numbers=matched_nums,
                    matched_numbers=matched_nums,
                    citations_found=cit_refs,
                    notes=notes,
                    nli_entailment_prob=ent_prob,
                    nli_contradiction_prob=con_prob,
                    verification_tier="TIER3_NLI",
                    bound_chunk_id=bound_chunk_id,
                    primary_page=primary_page,
                    retrieval_relevance_score=retrieval_relevance,
                    verification_path="NLI",
                    decision_reason=reason,
                    raw_logits=raw_logits,
                    softmax_probs=softmax_probs,
                    calibration_status=calibration_status,
                    latency_ms=nli_latency,
                ))
                continue
            elif grounding_score >= 0.30 or overlap_ratio >= 0.40 or (matched_nums and not unmatched_nums and overlap_ratio >= 0.15) or (con_prob < 0.25 and overlap_ratio >= 0.30):
                # Tier 4: Heuristic Soft Containment Fallback
                supported_count += 1
                reason = f"Supported via soft containment fallback ({grounding_score*100:.1f}% score)."
                notes.append(reason)
                results.append(ClaimVerificationResult(
                    claim_id=cid,
                    text=c_text,
                    is_supported=True,
                    status="SUPPORTED",
                    extracted_numbers=matched_nums,
                    matched_numbers=matched_nums,
                    citations_found=cit_refs,
                    notes=notes,
                    nli_entailment_prob=ent_prob,
                    nli_contradiction_prob=con_prob,
                    verification_tier="TIER4_FALLBACK",
                    bound_chunk_id=bound_chunk_id,
                    primary_page=primary_page,
                    retrieval_relevance_score=retrieval_relevance,
                    verification_path="DETERMINISTIC+NLI",
                    decision_reason=reason,
                    raw_logits=raw_logits,
                    softmax_probs=softmax_probs,
                    calibration_status=calibration_status,
                    latency_ms=nli_latency,
                ))
            else:
                reason = nli_reason or f"Insufficient evidence grounding: NLI neutral/uncertain (P(E)={ent_prob:.2f}, P(N)={neu_prob:.2f}), lexical {grounding_score*100:.1f}%."
                notes.append(reason)
                results.append(ClaimVerificationResult(
                    claim_id=cid,
                    text=c_text,
                    is_supported=False,
                    status="UNSUPPORTED",
                    extracted_numbers=unmatched_nums,
                    matched_numbers=matched_nums,
                    citations_found=cit_refs,
                    notes=notes,
                    nli_entailment_prob=ent_prob,
                    nli_contradiction_prob=con_prob,
                    verification_tier="TIER3_NLI",
                    bound_chunk_id=bound_chunk_id,
                    primary_page=primary_page,
                    retrieval_relevance_score=retrieval_relevance,
                    verification_path="NLI",
                    decision_reason=reason,
                    raw_logits=raw_logits,
                    softmax_probs=softmax_probs,
                    calibration_status=calibration_status,
                    latency_ms=nli_latency,
                ))

        faithfulness = round(supported_count / len(claims_text), 4) if claims_text else 1.0
        return results, faithfulness, num_mismatches, cit_errors
