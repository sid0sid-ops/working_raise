"""
RAISE NIAH Benchmark — Needle Catalog
Defines structured test needles for scientific retrieval evaluation:
  1. Single-Fact Needle (Exact unique factual assertion)
  2. Quantitative / Financial Metric Needle (Audited numerical data)
  3. Multi-Hop Relational Graph Needle (Linked across entities for Neo4j traversal)
  4. Adversarial Distractor Needle (Tests disambiguation against false cues)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NeedleType(str, Enum):
    SINGLE_FACT = "SINGLE_FACT"
    QUANTITATIVE = "QUANTITATIVE"
    MULTI_HOP_GRAPH = "MULTI_HOP_GRAPH"
    ADVERSARIAL_DISTRACTOR = "ADVERSARIAL_DISTRACTOR"


@dataclass
class NeedleCase:
    needle_id: str
    needle_type: NeedleType
    needle_text: str
    query: str
    expected_answer: str
    validation_keywords: List[str]
    regex_pattern: Optional[str] = None
    description: str = ""
    graph_entities: List[Dict[str, Any]] = field(default_factory=list)
    graph_relations: List[Dict[str, Any]] = field(default_factory=list)
    distractor_texts: List[str] = field(default_factory=list)

    def is_answer_in_text(self, text: str) -> bool:
        """Verify if generated or retrieved text contains the expected needle answer."""
        if not text:
            return False
        clean_text = text.lower()
        # Check all required validation keywords
        all_kw_present = all(kw.lower() in clean_text for kw in self.validation_keywords)
        if all_kw_present:
            return True
        # Check regex if defined
        if self.regex_pattern:
            import re
            return bool(re.search(self.regex_pattern, text, re.IGNORECASE))
        return False


# Curated Standard Needles for Academic GraphRAG Benchmark
STANDARD_NEEDLES: Dict[str, NeedleCase] = {
    "fact_quantum_crypt": NeedleCase(
        needle_id="fact_quantum_crypt",
        needle_type=NeedleType.SINGLE_FACT,
        needle_text="The confidential access authorization code for the Project Chimera quantum computing cluster is DELTA-9842-OMEGA.",
        query="What is the access authorization code for the Project Chimera quantum computing cluster?",
        expected_answer="DELTA-9842-OMEGA",
        validation_keywords=["DELTA-9842-OMEGA"],
        regex_pattern=r"DELTA[-\s]?9842[-\s]?OMEGA",
        description="Tests isolated retrieval of an arbitrary high-entropy alphanumeric secret.",
    ),
    "quant_photonic_grant": NeedleCase(
        needle_id="quant_photonic_grant",
        needle_type=NeedleType.QUANTITATIVE,
        needle_text="In the audited FY 2024-25 fiscal report, the Advanced Photonic Computing Initiative was granted an allocation of ₹42.75 Crore from the National Science Foundation.",
        query="What was the exact grant amount allocated to the Advanced Photonic Computing Initiative in FY 2024-25?",
        expected_answer="₹42.75 Crore",
        validation_keywords=["42.75", "crore"],
        regex_pattern=r"(?:₹|rs\.?|inr)?\s*42\.75\s*crore",
        description="Tests precise numerical financial extraction and unit preservation.",
    ),
    "graph_multihop_carbon": NeedleCase(
        needle_id="graph_multihop_carbon",
        needle_type=NeedleType.MULTI_HOP_GRAPH,
        needle_text=(
            "Dr. Alistair Vance was formally appointed principal director of the Stratospheric Aerosol Capture Initiative. "
            "Under his oversight, the Stratospheric Aerosol Capture Initiative successfully completed the Leh high-altitude trial, "
            "demonstrating an audited particulate reduction efficiency of 38.4 percent."
        ),
        query="What was the particulate reduction efficiency achieved by the initiative led by Dr. Alistair Vance?",
        expected_answer="38.4 percent",
        validation_keywords=["38.4", "percent"],
        regex_pattern=r"38\.4\s*(?:%|percent)",
        description="Tests 2-hop entity-relation traversal: Dr. Alistair Vance -> LEADS -> Initiative -> HAS_METRIC -> 38.4%.",
        graph_entities=[
            {"id": "person_alistair_vance", "name": "Dr. Alistair Vance", "label": "Faculty_Person"},
            {"id": "init_stratospheric_capture", "name": "Stratospheric Aerosol Capture Initiative", "label": "Initiative"},
            {"id": "metric_reduction_efficiency", "name": "38.4 percent particulate reduction", "label": "MetricFact"},
        ],
        graph_relations=[
            {"source": "person_alistair_vance", "target": "init_stratospheric_capture", "relation": "LEADS_OR_GOVERNS"},
            {"source": "init_stratospheric_capture", "target": "metric_reduction_efficiency", "relation": "REPORTED_METRIC"},
        ],
    ),
    "adversarial_founder_award": NeedleCase(
        needle_id="adversarial_founder_award",
        needle_type=NeedleType.ADVERSARIAL_DISTRACTOR,
        needle_text="The 2024 Distinguished Bioengineering Pioneer Award was conferred exclusively upon Dr. Evelyn Thorne for her work on synthetic chloroplast organelles.",
        query="Who was awarded the 2024 Distinguished Bioengineering Pioneer Award?",
        expected_answer="Dr. Evelyn Thorne",
        validation_keywords=["Evelyn Thorne"],
        regex_pattern=r"Evelyn\s+Thorne",
        description="Tests high-precision entity resolution against closely worded distractor candidates.",
        distractor_texts=[
            "The 2024 Distinguished Bioengineering Pioneer Award nominated Dr. Robert Hayes for cellular genomics.",
            "The 2023 Distinguished Bioengineering Pioneer Award was won by Dr. Marcus Vance for enzymatic catalysts.",
            "Dr. Evelyn Thorne chaired the selection panel for the 2024 National Biochemistry Fellowship.",
        ],
    ),
    "institutional_audit_schedule": NeedleCase(
        needle_id="institutional_audit_schedule",
        needle_type=NeedleType.QUANTITATIVE,
        needle_text="Under Schedule 12 of the statutory audit report, the penalty collected from defaulting electrical infrastructure contractors was exactly ₹14,53,306.",
        query="What was the penalty collected from contractors under Schedule 12 of the statutory audit report?",
        expected_answer="₹14,53,306",
        validation_keywords=["14,53,306", "penalty"],
        regex_pattern=r"(?:₹|rs\.?)?\s*14,53,306",
        description="Tests extraction of specific institutional financial penalty from statutory annual reports.",
    ),
}


def get_needle(needle_id: str = "fact_quantum_crypt") -> NeedleCase:
    """Retrieve a standard needle test case by ID."""
    if needle_id in STANDARD_NEEDLES:
        return STANDARD_NEEDLES[needle_id]
    raise KeyError(f"Needle '{needle_id}' not found in standard catalog. Available: {list(STANDARD_NEEDLES.keys())}")


def list_available_needles() -> List[str]:
    """List all registered needle test identifiers."""
    return list(STANDARD_NEEDLES.keys())
