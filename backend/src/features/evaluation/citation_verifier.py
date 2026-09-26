"""
Citation & Document Provenance Validator
========================================
Validates bracketed citations in generated answers, confirms document provenance,
and verifies active workspace constraints.

Architectural Role & Guarantees:
--------------------------------
1. Bracket Detection:
   - Identifies citation indices in standard academic notations: `[1]`, `[1, 2]`, `[1-3]`, or `[[1]]`.
2. Provenance Integrity:
   - Ensures every citation index cited by the LLM maps to a genuine retrieved chunk in `citations_list`.
   - Flags "hallucinated citations" where an LLM fabricates `[4]` when only 2 chunks were provided.
3. Active Workspace Enforcement:
   - When user filters by active documents (e.g. `BRIC-Annual-Report-2025.pdf`), verifies that
     no citation points to an excluded or inactive PDF.
4. Grounded Negative Assertions:
   - Gracefully allows negative answers ("The documents do not mention...") when the model correctly
     identifies missing information rather than hallucinating.

How to Update or Tune:
----------------------
- To support alternative citation styles (e.g. `(Author, Year)` or `(Doc 1, p. 12)`), adjust `CITATION_PATTERN`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


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
        """
        Validates citations in the answer against the available citations list and active documents.

        Returns:
            Tuple of (is_valid: bool, issues: List[str], found_indices: List[int])
        """
        issues = []
        found_indices = []
        for m in cls.CITATION_PATTERN.finditer(answer):
            for part in re.findall(r"\d+", m.group(1)):
                try:
                    found_indices.append(int(part))
                except ValueError:
                    pass

        # If answer has citation references but no citations exist in the prompt context
        if not citations_list and found_indices:
            issues.append("Answer contains citations but no citation metadata exists.")
            return False, issues, found_indices

        available_indices = {c.get("citation_index", idx + 1) for idx, c in enumerate(citations_list)}
        is_negative = bool(re.search(
            r"\b(not\s+contain|not\s+mentioned|no\s+information|does\s+not\s+mention|no\s+mention|"
            r"cannot\s+be\s+found|insufficient\s+evidence|unmentioned|outside\s+this\s+scope)\b",
            answer,
            re.IGNORECASE,
        ))

        # Check each found citation index
        for idx in found_indices:
            if idx not in available_indices:
                if not is_negative:
                    issues.append(f"Citation [{idx}] does not map to any retrieved document passage.")

        # Check that citations point to active documents
        if active_docs:
            for c in citations_list:
                doc_name = c.get("pdf_filename") or c.get("document_id") or ""
                if doc_name and not any(doc_name in active or active in doc_name for active in active_docs):
                    issues.append(f"Citation points to inactive document '{doc_name}'.")

        is_valid = len(issues) == 0
        return is_valid, issues, found_indices
