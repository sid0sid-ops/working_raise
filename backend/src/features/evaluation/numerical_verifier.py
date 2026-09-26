"""
Numerical Claim & Financial Metric Verifier
===========================================
Detects, extracts, normalizes, and strictly verifies numerical metrics, currency values,
percentages, and dates in generated responses against source evidence chunks.

Architectural Role & Verification Pipeline:
-------------------------------------------
1. `NUMBER_PATTERN`: Detects standard currency (₹, Rs, INR, $), scales (crore, lakh, million, billion),
   percentages (%), and formatted decimals/integers.
2. Citation & Artifact Sanitization:
   - Strips bracketed citations `[1]`, `[[2]]` so citation numbers are never confused with data metrics.
   - Strips PDF filenames (e.g. `Annual_Report_2022-23.pdf`) and page tokens (`p010`).
3. OCR Digit Normalization:
   - Scanned annual report tables frequently contain OCR substitution errors (e.g. 'S' for '5',
     'O'/'U' for '0', 'I'/'l'/'|' for '1'). These are normalized line-by-line.
4. User Query Context Ingestion:
   - Numbers provided directly in the user question (e.g., "In the year 2022-23...") are context
     premises rather than ungrounded claims, and are absorbed into allowable evidence.
5. Mathematical Aggregation / Derivation Checks:
   - If an LLM performs arithmetic over table figures (e.g. Total = 317.99 + 906.41 = 1224.40,
     or Net Change = 181441812 - 159067160 = 22374652), pairwise sums and differences are checked
     within a 0.05 absolute tolerance.

How to Update or Tune:
----------------------
- To add a new currency symbol or metric scale, adjust `NUMBER_PATTERN`.
- To tune arithmetic aggregation tolerance, adjust the float tolerance threshold in `verify_numbers()`.
- To add custom units (e.g. hectares, megawatts, MT), add them to `NUMBER_PATTERN`.
"""

from __future__ import annotations

import re
from typing import List, Tuple


def _is_float(val: str) -> bool:
    """Helper to safely check if a string represents a valid floating-point number."""
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False


class NumericalClaimVerifier:
    """
    Extracts and strictly verifies numeric metrics, currency values, percentages,
    and year dates against ground-truth evidence.
    """

    NUMBER_PATTERN = re.compile(
        r"(?:₹|Rs\.?|INR|\$)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(?:crore|crores|lakh|lakhs|million|billion|%|percent)?",
        re.IGNORECASE,
    )

    @classmethod
    def extract_numbers(cls, text: str) -> List[str]:
        """
        Extracts clean numeric strings from text while stripping out citation numbers,
        document filenames, and section identifiers.
        """
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

        # In tabular / OCR contexts, digits may be grouped with mixed commas, dots, and OCR artifacts.
        # Process line-by-line to avoid fusing distinct rows across newlines.
        for line in cleaned_text.splitlines():
            for m in re.finditer(r"\b\d+(?:[,\. \t]*\d+)+\b", line):
                unified = re.sub(r"[,\. \t]", "", m.group(0))
                if unified and len(unified) >= 2 and unified not in nums:
                    nums.append(unified)

            # Normalized OCR tokens (accounting for typical OCR letter-digit substitutions in scanned financial tables: S/s->5, O/o/U/u->0, I/l/|->1, C/c/J/j/L/()->0)
            for m in re.finditer(r"\b[0-9SOUulI][0-9SOUulICcJjL\(\),\. \t\-_/]+[0-9SOUulICcJjL\(\)]\b", line):
                t = m.group(0)
                t_norm = (
                    t.replace('S', '5').replace('s', '5')
                    .replace('O', '0').replace('o', '0')
                    .replace('U', '0').replace('u', '0')
                    .replace('I', '1').replace('l', '1').replace('|', '1')
                    .replace('C', '0').replace('c', '0')
                    .replace('J', '0').replace('j', '0')
                    .replace('L', '0')
                    .replace(')', '0').replace('(', '0')
                )
                t_digits = re.sub(r"[^0-9]", "", t_norm)
                if len(t_digits) >= 3 and t_digits not in nums:
                    nums.append(t_digits)

        return nums

    @classmethod
    def verify_numbers(cls, claim_text: str, evidence_text: str, query: str = "") -> Tuple[bool, List[str], List[str]]:
        """
        Cross-verifies all numbers extracted from a single claim against the evidence text.
        Returns:
            Tuple of (is_valid: bool, matched_numbers: List[str], unmatched_numbers: List[str])
        """
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
            if (
                num in evidence_nums
                or clean_num in clean_evidence_digits
                or any(clean_num == e or (len(clean_num) > 4 and clean_num in e) for e in clean_evidence_digits)
                or any(len(e) >= 6 and clean_num.startswith(e) and len(clean_num) <= len(e) + 2 for e in clean_evidence_digits)
                or any(len(e) >= 3 and clean_num.startswith(e) and re.fullmatch(r"0*", clean_num[len(e):]) for e in clean_evidence_digits)
                or any(len(clean_num) >= 3 and e.startswith(clean_num) and re.fullmatch(r"0*", e[len(clean_num):]) for e in clean_evidence_digits)
                or any(abs(float(num) - float(e)) < 0.01 for e in evidence_nums if _is_float(e) and _is_float(num))
            ):
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
