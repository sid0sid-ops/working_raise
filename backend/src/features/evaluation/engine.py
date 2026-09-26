"""
RAISE System Evaluation, Optimization, and Operational Governance Engine.
Provides:
  1. Structured Evidence Container (Vector Chunks + Neo4j Graph Facts + Provenance)
  2. Numerical Claim Verifier (Detects numeric / currency / percentage hallucinations)
  3. Citation Validator (Verifies bracketed [1] citations, document presence, page provenance)
  4. Claim-Level Verifier (Supported Claims / Total Claims)
  5. Local Heuristic Evaluator (Local RAGAS-aligned development metrics)
  6. Runtime Faithfulness Quality Gate (<0.80 rejection, 2-retry cap, controlled unverified refusal)
"""

from __future__ import annotations

import re
import math
from enum import Enum
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.features.evaluation.nli_verifier import nli_verifier


class VerificationPath(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"                     # Tier 1 Math / Numeric / Exact Date match
    NLI = "NLI"                                         # Direct Tier 3 Neural FineCat-NLI verification
    DETERMINISTIC_PLUS_NLI = "DETERMINISTIC+NLI"        # Lexical/heuristic match confirmed via NLI
    EVIDENCE_EXPANSION_PLUS_NLI = "EVIDENCE_EXPANSION+NLI" # Required multi-hop graph/chunk expansion before NLI
    CONTROLLED_ABSTENTION = "CONTROLLED_ABSTENTION"     # Safe abstention when evidence chain is incomplete


@dataclass
class StructuredEvidence:
    """Consolidated evidence container incorporating vector passages and graph facts."""
    vector_chunks: List[Dict[str, Any]] = field(default_factory=list)
    graph_facts: List[Dict[str, Any]] = field(default_factory=list)
    source_documents: List[str] = field(default_factory=list)
    active_docs: List[str] = field(default_factory=list)
    math_facts: List[str] = field(default_factory=list)

    def get_full_text(self) -> str:
        texts = []
        for c in self.vector_chunks:
            texts.append(str(c.get("plain_text") or c.get("text") or ""))
        for g in self.graph_facts:
            texts.append(str(g.get("fact") or g.get("raw_value") or str(g)))
        for m in self.math_facts:
            texts.append(str(m))
        for d in self.active_docs:
            texts.append(str(d))
        for s in self.source_documents:
            texts.append(str(s))
        return "\n".join(texts)


@dataclass
class ClaimVerificationResult:
    claim_id: str
    text: str
    is_supported: bool
    status: str  # "SUPPORTED", "DIRECT", "NLI_ENTAILED", "CONTRADICTION", "NUMERICAL_MISMATCH", "UNSUPPORTED", "CITATION_INVALID"
    extracted_numbers: List[str]
    matched_numbers: List[str]
    citations_found: List[int]
    notes: List[str] = field(default_factory=list)
    nli_entailment_prob: Optional[float] = None
    nli_contradiction_prob: Optional[float] = None
    retrieval_relevance_score: Optional[float] = None
    verification_tier: str = "TIER2_LEXICAL"  # "TIER1_NUMERIC", "TIER2_LEXICAL", "TIER3_NLI", "TIER4_FALLBACK"
    bound_chunk_id: Optional[str] = None
    primary_page: Optional[int] = None
    verification_path: str = "DETERMINISTIC"
    decision_reason: str = ""
    raw_logits: Optional[Dict[str, float]] = None
    softmax_probs: Optional[Dict[str, float]] = None
    calibration_status: str = "UNVALIDATED_RAW_SOFTMAX"
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Canonical alias ensuring single source of truth across claim audit, quality gate, and telemetry
ClaimVerificationRecord = ClaimVerificationResult


@dataclass
class EvaluationReport:
    evaluator_type: str  # "LocalHeuristicEvaluator" / "RuntimeQualityGate"
    faithfulness: float
    answer_relevance: float
    context_precision: float
    context_recall: float
    overall_score: float
    supported_claims_count: int
    total_claims_count: int
    numerical_mismatches: int
    citation_errors: int
    is_acceptable: bool
    rejection_reason: Optional[str] = None
    claims: List[ClaimVerificationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        num_claims_with_numbers = 0
        num_claims_verified = 0
        for c in self.claims:
            if c.extracted_numbers or c.matched_numbers:
                num_claims_with_numbers += 1
                if c.is_supported and c.status != "NUMERICAL_MISMATCH":
                    num_claims_verified += 1

        unsupported_count = max(0, self.total_claims_count - self.supported_claims_count)
        evidence_overlap = round(self.context_precision * 100.0, 1)
        factual_overlap = round((self.supported_claims_count / max(self.total_claims_count, 1)) * 100.0, 1)

        return {
            "evaluator_type": self.evaluator_type,
            "faithfulness": self.faithfulness,
            "faithfulness_score": self.faithfulness,
            "answer_relevance": self.answer_relevance,
            "context_precision": self.context_precision,
            "context_recall": self.context_recall,
            "overall_score": self.overall_score,
            "supported_claims_count": self.supported_claims_count,
            "total_claims_count": self.total_claims_count,
            "unsupported_claims_count": unsupported_count,
            "numerical_mismatches": self.numerical_mismatches,
            "numerical_claims_total": num_claims_with_numbers,
            "numerical_claims_verified": num_claims_verified,
            "evidence_overlap_pct": evidence_overlap,
            "factual_overlap_pct": factual_overlap,
            "citation_errors": self.citation_errors,
            "is_acceptable": self.is_acceptable,
            "rejection_reason": self.rejection_reason,
            "claims": [c.to_dict() for c in self.claims],
        }


class NumericalClaimVerifier:
    """
    Extracts and strictly verifies numeric metrics, currency values, percentages,
    and year dates against ground-truth evidence.
    """

    NUMBER_PATTERN = re.compile(r"(?:₹|Rs\.?|INR|\$)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(?:crore|crores|lakh|lakhs|million|billion|%|percent)?", re.IGNORECASE)

    @classmethod
    def extract_numbers(cls, text: str) -> List[str]:
        # Strip bracketed citation numbers (e.g. [1], [2, 3], [1-3], [[1]]) so citations are not treated as numerical metrics
        cleaned_text = re.sub(r"\[\[?\s*\d+(?:\s*[,-–]\s*\d+)*\s*\]?\]", "", text)
        # Strip filenames (e.g. Quantum_Research_Institute_2026.pdf, ARE-2016-17.pdf)
        cleaned_text = re.sub(r"\b[\w\-\.]+\.(?:pdf|docx?|txt|csv|json|md)\b", "", cleaned_text, flags=re.IGNORECASE)
        # Strip identifiers with numbers like p010, c01, ARE_2016_17
        cleaned_text = re.sub(r"\b[a-zA-Z]+[_\-][a-zA-Z0-9_\-]+\b", "", cleaned_text)
        nums = []
        for m in cls.NUMBER_PATTERN.finditer(cleaned_text):
            raw = m.group(1).replace(",", "")
            if raw:
                nums.append(raw)
        # In tabular / OCR contexts, digits may be grouped with mixed commas, dots, and OCR artifacts
        # Process line-by-line to avoid fusing distinct rows across newlines
        for line in cleaned_text.splitlines():
            for m in re.finditer(r"\b\d+(?:[,\. \t]*\d+)+\b", line):
                unified = re.sub(r"[,\. \t]", "", m.group(0))
                if unified and len(unified) >= 2 and unified not in nums:
                    nums.append(unified)
            # Normalized OCR tokens (accounting for typical OCR letter-digit substitutions in scanned financial tables: S/s->5, O/o/U/u->0, I/l/|->1, C/c/J/j/L/()->0)
            for m in re.finditer(r"\b[0-9SOUulI][0-9SOUulICcJjL\(\),\. \t\-_/]+[0-9SOUulICcJjL\(\)]\b", line):
                t = m.group(0)
                t_norm = (t.replace('S', '5').replace('s', '5')
                           .replace('O', '0').replace('o', '0')
                           .replace('U', '0').replace('u', '0')
                           .replace('I', '1').replace('l', '1').replace('|', '1')
                           .replace('C', '0').replace('c', '0')
                           .replace('J', '0').replace('j', '0')
                           .replace('L', '0')
                           .replace(')', '0').replace('(', '0'))
                t_digits = re.sub(r"[^0-9]", "", t_norm)
                if len(t_digits) >= 3 and t_digits not in nums:
                    nums.append(t_digits)
        return nums

    @classmethod
    def verify_numbers(cls, claim_text: str, evidence_text: str, query: str = "") -> Tuple[bool, List[str], List[str]]:
        claim_nums = cls.extract_numbers(claim_text)
        if not claim_nums:
            return True, [], []

        evidence_nums = set(cls.extract_numbers(evidence_text))
        # Numbers explicitly stated in the user query (e.g. years 2021-22, page 131) are context premises, not ungrounded metrics
        query_nums = set(cls.extract_numbers(query)) if query else set()
        for qn in list(query_nums):
            if len(qn) == 4 and qn.startswith("20"):
                query_nums.add(qn[2:])
        evidence_nums.update(query_nums)

        clean_evidence_digits = {re.sub(r"[,\.\s]", "", e) for e in evidence_nums}
        matched = []
        unmatched = []

        for num in claim_nums:
            clean_num = num.replace(",", "").replace(".", "").strip()
            if (num in evidence_nums
                or clean_num in clean_evidence_digits
                or any(clean_num == e or (len(clean_num) > 4 and clean_num in e) for e in clean_evidence_digits)
                or any(len(e) >= 6 and clean_num.startswith(e) and len(clean_num) <= len(e) + 2 for e in clean_evidence_digits)
                or any(len(e) >= 3 and clean_num.startswith(e) and re.fullmatch(r"0*", clean_num[len(e):]) for e in clean_evidence_digits)
                or any(len(clean_num) >= 3 and e.startswith(clean_num) and re.fullmatch(r"0*", e[len(clean_num):]) for e in clean_evidence_digits)
                or any(abs(float(num) - float(e)) < 0.01 for e in evidence_nums if _is_float(e) and _is_float(num))):
                matched.append(num)
            else:
                unmatched.append(num)

        # Mathematical derivation check: support pairwise aggregation (sums/differences)
        # e.g., LLM computes INR 1,224.4 crore from 317.99 + 906.41 or 181441812 - 159067160 = 22374652
        if unmatched:
            float_evidence = [float(e) for e in evidence_nums if _is_float(e)]
            expanded_evidence = set(float_evidence)
            for fe in float_evidence:
                if 1 <= fe <= 10000:
                    expanded_evidence.add(fe * 100000)
                    expanded_evidence.add(fe * 10000000)
            float_ev_list = list(expanded_evidence)
            still_unmatched = []
            for num in unmatched:
                if _is_float(num):
                    val = float(num)
                    found_derivation = False
                    n_ev = len(float_ev_list)
                    for i in range(n_ev):
                        for j in range(i + 1, n_ev):
                            if abs(val - (float_ev_list[i] + float_ev_list[j])) < 0.05:
                                found_derivation = True
                                break
                            if abs(val - abs(float_ev_list[i] - float_ev_list[j])) < 0.05:
                                found_derivation = True
                                break
                        if found_derivation:
                            break
                    if found_derivation:
                        matched.append(num)
                    else:
                        still_unmatched.append(num)
                else:
                    still_unmatched.append(num)
            unmatched = still_unmatched

        # If an unmatched number is just the digit-only representation of an already matched number (e.g. '22374' from '223.74'), mark as matched
        if unmatched:
            matched_digits = {m.replace(",", "").replace(".", "").strip() for m in matched}
            unmatched_final = []
            for num in unmatched:
                c_num = num.replace(",", "").replace(".", "").strip()
                if c_num in matched_digits:
                    matched.append(num)
                else:
                    unmatched_final.append(num)
            unmatched = unmatched_final

        # If any number in the claim is completely absent from the evidence, fail numerical check
        is_valid = len(unmatched) == 0
        return is_valid, matched, unmatched


def _is_float(val: str) -> bool:
    try:
        float(val)
        return True
    except ValueError:
        return False


class CitationValidator:
    """
    Validates page-level and document-level citations in generated answers.
    """

    CITATION_PATTERN = re.compile(r"\[\[?([0-9\s,\-–]+)\]?\]")

    @classmethod
    def validate_citations(
        cls,
        answer: str,
        citations_list: List[Dict[str, Any]],
        active_docs: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str], List[int]]:
        issues = []
        found_indices = []
        for m in cls.CITATION_PATTERN.finditer(answer):
            for part in re.findall(r"\d+", m.group(1)):
                try:
                    found_indices.append(int(part))
                except ValueError:
                    pass

        if not citations_list and found_indices:
            issues.append("Answer contains citations but no citation metadata exists.")
            return False, issues, found_indices

        available_indices = {c.get("citation_index", idx + 1) for idx, c in enumerate(citations_list)}
        is_negative = bool(re.search(r"\b(not\s+contain|not\s+mentioned|no\s+information|does\s+not\s+mention|no\s+mention|cannot\s+be\s+found|insufficient\s+evidence|unmentioned|outside\s+this\s+scope)\b", answer, re.IGNORECASE))

        for idx in found_indices:
            if idx not in available_indices:
                if not is_negative:
                    issues.append(f"Citation [{idx}] does not map to any retrieved document passage.")

        if active_docs:
            for c in citations_list:
                doc_name = c.get("pdf_filename") or c.get("document_id") or ""
                if doc_name and not any(doc_name in active or active in doc_name for active in active_docs):
                    issues.append(f"Citation points to inactive document '{doc_name}'.")

        is_valid = len(issues) == 0
        return is_valid, issues, found_indices


class ClaimLevelVerifier:
    """
    Decomposes responses into discrete factual claims and evaluates each claim
    against structured vector passages and Neo4j graph triples.
    """

    STOP_WORDS = {
        "what", "is", "the", "and", "or", "for", "with", "from", "that", "this",
        "these", "those", "have", "has", "had", "were", "been", "being", "are",
        "was", "their", "they", "its", "into", "during", "which", "about", "also",
        "based", "verified", "excerpts", "uploaded", "reports", "report", "document"
    }

    @classmethod
    def extract_claims(cls, answer: str) -> List[str]:
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


class LocalHeuristicEvaluator:
    """
    Local heuristic benchmarking evaluator clearly distinguished from cloud RAGAS.
    Calculates offline RAGAS-aligned proxy metrics for development testing.
    """

    @classmethod
    def evaluate(
        cls,
        query: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        graph_facts: Optional[List[Dict[str, Any]]] = None,
        ground_truth_facts: Optional[List[str]] = None,
        citations_list: Optional[List[Dict[str, Any]]] = None,
        active_docs: Optional[List[str]] = None,
        math_facts: Optional[List[str]] = None,
        threshold: float = 0.80,
    ) -> EvaluationReport:
        evidence = StructuredEvidence(
            vector_chunks=retrieved_chunks,
            graph_facts=graph_facts or [],
            active_docs=active_docs or [],
            math_facts=math_facts or [],
        )

        claims_res, f_score, num_mismatches, _ = ClaimLevelVerifier.verify_claims(
            answer=answer,
            evidence=evidence,
            citations_list=citations_list,
            query=query,
        )

        # Validate Citations
        cit_valid, cit_issues, _ = CitationValidator.validate_citations(
            answer=answer,
            citations_list=citations_list or [],
            active_docs=active_docs,
        )
        cit_errors = len(cit_issues)

        # Answer Relevance
        q_words = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", query.lower()))
        q_words = {w for w in q_words if w not in {"what", "who", "where", "how", "many", "tell", "show", "give"}}
        a_lower = answer.lower()
        rel_overlap = sum(1 for w in q_words if w in a_lower) if q_words else 1
        rel_score = round(min(1.0, (rel_overlap / max(len(q_words), 1)) + 0.30), 4)

        # Context Precision
        contexts = [str(c.get("plain_text") or c.get("text") or "") for c in retrieved_chunks]
        relevant_positions = []
        for idx, ctx in enumerate(contexts, start=1):
            ctx_lower = ctx.lower()
            if q_words and any(w in ctx_lower for w in q_words):
                relevant_positions.append(idx)
        prec_score = round(sum(i / rank for i, rank in enumerate(relevant_positions, 1)) / max(len(relevant_positions), 1), 4) if relevant_positions else 0.50

        # Context Recall
        joined_evidence = evidence.get_full_text().lower()
        recalled = 0
        if ground_truth_facts:
            for fact in ground_truth_facts:
                f_words = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", fact.lower()))
                if f_words and sum(1 for w in f_words if w in joined_evidence) / len(f_words) >= 0.5:
                    recalled += 1
            rec_score = round(recalled / len(ground_truth_facts), 4)
        else:
            rec_score = 1.0

        # 4. Startup / Entity Completeness Guardrail
        # If user asks for "startups" (plural) or "deep-tech startups", require named startup profiles
        q_lower = query.lower()
        is_startup_query = any(k in q_lower for k in ["startups", "ventures", "spin-offs", "deep-tech startups", "companies incubated"])
        completeness_failed = False
        completeness_msg = ""
        if is_startup_query:
            # Look for specific named venture patterns (e.g. capitalized entities or explicit names)
            named_ventures = re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\b", answer)
            # Filter common words
            stop_entities = {"IITM", "IIT", "Madras", "Research", "Park", "Incubation", "Cell", "IITMIC", "Based", "Section", "References", "Doc", "Page"}
            ventures_found = {v for v in named_ventures if v not in stop_entities and len(v) > 3}
            # Also check if answer explicitly confessed to having zero startup details or excuses
            has_confession_or_excuse = any(w in answer.lower() for w in ["does not provide specific details on the names", "no specific startup", "does not name"])
            if has_confession_or_excuse or len(ventures_found) < 2:
                completeness_failed = True
                completeness_msg = "Recall/Completeness check failed: Query requested deep-tech startups but answer contained fewer than 2 specific named startup profiles."

        # 5. Anti-Fabrication Boundary Guardrail
        # Check if model fabricated fictional document sections or boundaries (e.g. "Section 14 and Section 21 records")
        fabricated_boundary_match = re.search(r"\b(section\s+\d+\s+(?:and|&)\s+section\s+\d+\s+records?|document\s+boundaries?)\b", answer, re.IGNORECASE)
        fabricated_boundary_found = False
        if fabricated_boundary_match:
            # Check if this phrase is actually in the evidence text
            phrase = fabricated_boundary_match.group(0).lower()
            if phrase not in joined_evidence:
                fabricated_boundary_found = True

        overall = round((f_score * 0.4) + (rel_score * 0.3) + (prec_score * 0.15) + (rec_score * 0.15), 4)
        max_allowed_num_mismatches = 1 if len(claims_res) >= 10 else 0
        is_acceptable = f_score >= threshold and num_mismatches <= max_allowed_num_mismatches and cit_valid and not completeness_failed and not fabricated_boundary_found

        reason = None
        if not is_acceptable:
            reasons = []
            if f_score < threshold:
                reasons.append(f"Faithfulness {f_score:.2f} < {threshold:.2f}")
            if num_mismatches > max_allowed_num_mismatches:
                reasons.append(f"{num_mismatches} numerical mismatch(es)")
            if not cit_valid:
                reasons.append(f"Citation validation errors: {', '.join(cit_issues)}")
            if completeness_failed:
                reasons.append(completeness_msg)
            if fabricated_boundary_found:
                reasons.append("Anti-fabrication violation: Model fabricated non-existent document/section boundaries.")
            reason = "; ".join(reasons)

        return EvaluationReport(
            evaluator_type="LocalHeuristicEvaluator",
            faithfulness=f_score,
            answer_relevance=rel_score,
            context_precision=prec_score,
            context_recall=rec_score,
            overall_score=overall,
            supported_claims_count=sum(1 for c in claims_res if c.is_supported),
            total_claims_count=len(claims_res),
            numerical_mismatches=num_mismatches,
            citation_errors=cit_errors,
            is_acceptable=is_acceptable,
            rejection_reason=reason,
            claims=claims_res,
        )


class RuntimeFaithfulnessQualityGate:
    """
    Runtime Quality Gate node executed in LangGraph StateGraph.
    Monitors generation faithfulness, validates citations, and enforces strict 2-retry limits.
    """

    UNVERIFIED_REFUSAL_MESSAGE = (
        "I could not verify this answer against the uploaded academic sources. "
        "Please upload additional relevant material or refine the question."
    )

    EMPTY_WORKSPACE_MESSAGE = "Please upload an academic PDF to begin your research."

    def __init__(self, threshold: float = 0.80, max_retries: int = 2):
        self.threshold = threshold
        self.max_retries = max_retries

    def evaluate_runtime_state(
        self,
        query: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        graph_evidence: Optional[Dict[str, Any]] = None,
        citations_list: Optional[List[Dict[str, Any]]] = None,
        active_docs: Optional[List[str]] = None,
        math_facts: Optional[List[str]] = None,
        retry_count: int = 0,
        max_retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        # 1. Handle Empty Workspace
        if active_docs is not None and len(active_docs) == 0:
            return {
                "decision": "empty_workspace",
                "answer": self.EMPTY_WORKSPACE_MESSAGE,
                "is_acceptable": True,
                "retry_count": retry_count,
            }

        # Convert graph evidence to structured facts
        graph_facts = []
        if graph_evidence:
            for trip in graph_evidence.get("structured_triples", []):
                graph_facts.append({"fact": trip})
            for node in graph_evidence.get("nodes", []):
                graph_facts.append({"fact": f"Node: {node.get('label')} ({node.get('type')})"})

        report = LocalHeuristicEvaluator.evaluate(
            query=query,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            graph_facts=graph_facts,
            citations_list=citations_list,
            active_docs=active_docs,
            math_facts=math_facts,
            threshold=self.threshold,
        )

        # Run RigorousQualityGate (from blueprint) for strict completeness and boundary verification
        from src.features.evaluation.quality_gate import RigorousQualityGate
        rigorous_validator = RigorousQualityGate(faithfulness_threshold=self.threshold)
        contexts = [str(c.get("plain_text") or c.get("text") or "") for c in retrieved_chunks]
        rigorous_check = rigorous_validator.verify_completeness_and_grounding(
            query=query,
            response=answer,
            retrieved_contexts=contexts,
        )

        if report.is_acceptable and rigorous_check["decision"] == "ACCEPT":
            return {
                "decision": "accept",
                "answer": answer,
                "report": report.to_dict(),
                "is_acceptable": True,
                "retry_count": retry_count,
            }

        rejection_reason = report.rejection_reason or rigorous_check.get("reason")

        # If rejected, evaluate retry limits
        effective_max = max_retries if max_retries is not None else self.max_retries
        if retry_count < effective_max:
            clean_q = re.sub(r"[^a-zA-Z0-9\s]", "", query).strip()
            reformulated_query = f"{clean_q} specific verified facts metrics"
            return {
                "decision": "retry",
                "report": report.to_dict(),
                "is_acceptable": False,
                "retry_count": retry_count + 1,
                "reformulated_query": reformulated_query,
                "rejection_reason": rejection_reason,
            }
        else:
            # Controlled refusal after exhausting retries
            return {
                "decision": "unable_to_verify",
                "answer": self.UNVERIFIED_REFUSAL_MESSAGE,
                "report": report.to_dict(),
                "is_acceptable": False,
                "retry_count": retry_count,
                "rejection_reason": report.rejection_reason,
            }
