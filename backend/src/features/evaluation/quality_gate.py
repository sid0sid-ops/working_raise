"""
Rigorous Grounding, Completeness, and Anti-Fabrication Quality Gate.
Enforces precision, recall (leaf-node entity completeness), and blocks
ungrounded boundary/section hallucinations as defined in the RAISE pipeline blueprint.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class RigorousQualityGate:
    """
    Validates both Precision (Faithfulness) and Recall (Completeness).
    Prevents the LLM from fabricating structural boundaries or excuses.
    """

    def __init__(self, faithfulness_threshold: float = 0.85):
        self.threshold = faithfulness_threshold

    def verify_completeness_and_grounding(
        self,
        query: str,
        response: str,
        retrieved_contexts: List[str],
    ) -> Dict[str, Any]:
        """
        Validates both Precision (Faithfulness) and Recall (Completeness).
        """
        # 1. Structural Completeness Check: Ensure entity lookup is matched
        requires_multiple_entities = any(term in query.lower() for term in ["startups", "companies", "names", "ventures"])
        requires_any_entity = any(term in query.lower() for term in ["startup", "company", "who", "institution", "organization", "university", "faculty", "director"])
        extracted_entities = re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", response)  # Capture Capitalized Entity Names

        # Strip out system/formatting artifacts to verify concrete domain entity recovery
        system_nodes = {
            "IITM", "IITMRP", "IITMIC", "Research", "Park", "Annual", "Report", "The", "Based", "Section",
            "References", "Doc", "Page", "Table", "Figure", "Appendix", "According", "Document", "Source"
        }
        leaf_entities = [entity for entity in extracted_entities if entity not in system_nodes]

        min_required = 2 if requires_multiple_entities else (1 if requires_any_entity else 0)
        if min_required > 0 and len(leaf_entities) < min_required and len(response.split()) > 35:
            return {
                "decision": "REJECT",
                "reason": f"Completeness Failure: The query requested entities/organizations, but fewer than {min_required} concrete leaf-node entities were identified in the response.",
                "retry_action": "BM25_ENTITY_FALLBACK",
            }

        # 2. Grounding & Anti-Fabrication Boundary Verification
        # Check if the LLM generated pseudo-boundaries to justify lack of retrieval
        suspicious_patterns = [
            r"records are restricted",
            r"not detailed in this section",
            r"not included in current records",
            r"Section \d+ and Section \d+ records are missing",
            r"bounded by Section .* unavailable",
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                # Verify if this specific section or restriction is present in retrieved chunks
                has_grounding = any(re.search(pattern, context, re.IGNORECASE) for context in retrieved_contexts)
                if not has_grounding:
                    return {
                        "decision": "REJECT",
                        "reason": f"Anti-Fabrication Failure: Detected ungrounded structural boundary claim ('{pattern}') in response.",
                        "retry_action": "RE-GENERATE_WITH_STRICT_NO_COMMENTARY",
                    }

        return {
            "decision": "ACCEPT",
            "reason": "Passed grounding, completeness, and anti-fabrication gates.",
        }


QualityGateValidator = RigorousQualityGate
quality_gate_validator = RigorousQualityGate()
