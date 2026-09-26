"""
RAISE NIAH Benchmark — Haystack Generator
Generates realistic academic, institutional, and scientific distractor text
to create customizable haystacks of controllable token/word volume.
"""

from __future__ import annotations

import random
from typing import List, Optional


# Curated academic domain distractor corpus segments
ACADEMIC_DISTRACTOR_PARAGRAPHS = [
    (
        "The University Academic Senate convened for its annual curriculum harmonization session. "
        "The committee reviewed proposals from the Faculty of Electrical Engineering regarding undergraduate laboratory credits. "
        "Revisions to the credit distribution framework were approved, requiring four additional hours in embedded systems design. "
        "Departmental liaisons agreed that the practical syllabus should mirror industrial microelectronic fabrication requirements."
    ),
    (
        "The Technology Transfer Office announced the licensing of nine provisional patent portfolios in advanced dielectric materials. "
        "Commercial partners from the heavy equipment sector have committed non-dilutive co-development capital. "
        "The university incubator will retain equity warrants according to the standard intellectual property governance policy. "
        "Periodic royalty distributions are slated to commence following the third operational manufacturing audit."
    ),
    (
        "In accordance with institutional financial oversight guidelines, the internal audit committee completed its review of expenditure statements. "
        "Recurring operational disbursements across all seven zonal campuses matched authorized budgetary projections within a 1.2% variance. "
        "Capital allocations for cryogenic spectroscopy suites were scheduled across three fiscal milestone disbursements. "
        "Depreciation schedules for high-performance compute clusters were adjusted to a four-year linear amortization timeline."
    ),
    (
        "The Centre for Advanced Materials Science inaugurated its secondary cleanroom facility for chemical vapor deposition experiments. "
        "The specialized cleanroom provides ISO Class 5 ambient conditions for transition-metal dichalcogenide crystallization. "
        "Interdisciplinary research scholars from chemistry, physics, and bio-nanotechnology will share instrument access schedules. "
        "Maintenance contracts for turbomolecular vacuum stations were extended under a multi-institutional consortium agreement."
    ),
    (
        "The Joint Research Advisory Board published its bi-annual evaluation of inter-departmental doctoral scholarships. "
        "A total of forty-two candidate dossiers were examined across biochemical engineering, photonics, and distributed computing. "
        "Standardized peer-review metrics confirmed an average publication index of 3.4 peer-reviewed manuscripts per candidate before thesis submission. "
        "Travel stipends for international symposium participation were augmented to facilitate bilateral exchange collaborations."
    ),
    (
        "The Institutional Biosafety Board ratified standard operating procedures for recombinant DNA containment in Level 3 suites. "
        "Autoclave calibration logs and negative-pressure sensor registries must be submitted electronically on the first Monday of each calendar month. "
        "Faculty investigators must maintain continuous chain-of-custody documentation for vector transport across affiliated regional hospital wings."
    ),
    (
        "Infrastructure development initiatives for the southern campus perimeter advanced with the commissioning of a 1.5 megawatt solar array. "
        "The grid-synchronous inverter architecture enables bidirectional power routing, reducing campus reliance on municipal utility grids during peak diurnal hours. "
        "Telemetry logs are logged into the central environmental management portal for real-time monitoring of carbon displacement indices."
    ),
    (
        "The Department of Computer Science and Engineering introduced an advanced seminar series on formal verification of distributed ledger protocols. "
        "Graduate students explored state space reduction techniques in bounded model checking, focusing on asynchronous Byzantine fault tolerance algorithms. "
        "Open-source artifact evaluation benchmarks were released on the departmental repository under an permissive academic license."
    ),
    (
        "The University Library Consortium completed digitizing four centuries of regional historical cartography manuscripts. "
        "High-resolution multispectral image scans were ingested into the open-access institutional repository alongside Dublin Core metadata records. "
        "Optical character recognition validation runs revealed a 98.7% character fidelity rate for seventeenth-century bilingual administrative registers."
    ),
    (
        "The Directorate of Alumni Relations and Philanthropic Giving registered end-of-year endowment contributions totaling fourteen major benefactions. "
        "Endowment yields will perpetually subsidize competitive need-based undergraduate tuition waivers across STEM and humanities faculties. "
        "The Board of Trustees reaffirmed its policy requiring endowment principal investments to observe socially responsible sustainability principles."
    ),
]


class HaystackGenerator:
    """
    Generates deterministic academic distractor text for NIAH benchmark haystacks.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def reset_seed(self, seed: Optional[int] = None):
        if seed is not None:
            self.seed = seed
        self.rng = random.Random(self.seed)

    def generate_haystack(self, target_words: int) -> List[str]:
        """
        Generates an ordered list of distractor paragraphs reaching or slightly exceeding target_words.
        """
        paragraphs: List[str] = []
        current_words = 0
        pool_size = len(ACADEMIC_DISTRACTOR_PARAGRAPHS)
        idx = 0

        while current_words < target_words:
            # Pick paragraph deterministically with subtle variations
            base_p = ACADEMIC_DISTRACTOR_PARAGRAPHS[idx % pool_size]
            cycle = (idx // pool_size) + 1

            # Vary the paragraph slightly per cycle so text is not 100% identical duplicates
            if cycle > 1:
                para = f"[Report Section {idx+1}] {base_p} (Addendum {cycle}: Verified under standard compliance protocol {1000 + idx})."
            else:
                para = f"[Report Section {idx+1}] {base_p}"

            p_words = len(para.split())
            paragraphs.append(para)
            current_words += p_words
            idx += 1

        return paragraphs

    def generate_full_text(self, target_words: int) -> str:
        """Returns generated haystack as a single multi-paragraph string."""
        paragraphs = self.generate_haystack(target_words=target_words)
        return "\n\n".join(paragraphs)
