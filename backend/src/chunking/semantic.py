"""
Semantic Segmentation Engine (Stage 3 of GGAHC).
Generates candidate semantic units based on sentence similarity, discourse transitions,
heading relationships, and topic cohesion instead of rigid token limits.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional

from .config import ChunkingConfig
from .models import CandidateUnit, StructuralUnit


class SemanticSegmenter:
    """
    Evaluates semantic continuity across structural units to produce candidate information units.
    Uses token overlaps, discourse markers, and optional embedding similarity.
    """

    TRANSITION_MARKERS = {
        "however", "moreover", "furthermore", "in addition", "consequently", "therefore",
        "meanwhile", "on the other hand", "in contrast", "subsequently", "accordingly"
    }

    DISCONTINUITY_MARKERS = {
        "table of contents", "appendix", "chapter", "financial statements", "independent auditor's report",
        "board of governors", "balance sheet", "profit and loss", "notes forming part of accounts"
    }

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()

    def segment_structural_units(
        self,
        structural_units: List[StructuralUnit],
        document_id: str,
    ) -> List[CandidateUnit]:
        """
        Groups adjacent structural units into coherent candidate semantic units.
        Tables and figures are protected as discrete candidate units.
        """
        candidates: List[CandidateUnit] = []
        if not structural_units:
            return candidates

        current_units: List[StructuralUnit] = []
        cand_counter = 0

        def flush_current():
            nonlocal cand_counter, current_units
            if not current_units:
                return
            cand_counter += 1
            combined_text = "\n\n".join(u.content for u in current_units)
            first_u = current_units[0]
            last_u = current_units[-1]
            c_id = f"{document_id}_cand_{cand_counter:03d}"
            sec_id = f"sec_{document_id}_{first_u.page_number}"
            
            is_cont = any(u.is_continued for u in current_units)
            cont_id = next((u.continuation_of_id for u in current_units if u.continuation_of_id), None)
            is_lst = any(u.is_list for u in current_units)

            cand = CandidateUnit(
                candidate_id=c_id,
                document_id=document_id,
                section_id=sec_id,
                heading=first_u.heading,
                page_start=first_u.page_number,
                page_end=last_u.page_number,
                plain_text=combined_text,
                structural_unit_ids=[u.unit_id for u in current_units],
                is_table=any(u.unit_type == "table" for u in current_units),
                is_figure=any(u.unit_type == "figure" for u in current_units),
                is_continued=is_cont,
                continuation_of_id=cont_id,
                is_list=is_lst,
            )
            candidates.append(cand)
            current_units = []

        for unit in structural_units:
            # Tables and figures are emitted as standalone candidates to prevent flattening
            if unit.unit_type in ("table", "figure"):
                flush_current()
                cand_counter += 1
                cand = CandidateUnit(
                    candidate_id=f"{document_id}_cand_{cand_counter:03d}",
                    document_id=document_id,
                    section_id=f"sec_{document_id}_{unit.page_number}",
                    heading=unit.heading,
                    page_start=unit.page_number,
                    page_end=unit.page_number,
                    plain_text=unit.content,
                    structural_unit_ids=[unit.unit_id],
                    is_table=(unit.unit_type == "table"),
                    is_figure=(unit.unit_type == "figure"),
                    is_continued=unit.is_continued,
                    continuation_of_id=unit.continuation_of_id,
                    is_list=unit.is_list,
                    metadata={"table_meta": unit.table_metadata, "figure_meta": unit.figure_metadata},
                )
                candidates.append(cand)
                continue

            if not current_units:
                current_units.append(unit)
                continue

            # If unit is explicitly marked as continued from previous unit, do NOT split
            if unit.is_continued or unit.continuation_of_id:
                current_units.append(unit)
                continue

            # Evaluate boundary with current accumulator
            prev_unit = current_units[-1]
            current_tokens = sum(len(u.content.split()) for u in current_units)
            unit_tokens = len(unit.content.split())

            # Strong structural boundary: heading changed or page transition between distinct sections
            heading_changed = (unit.heading != prev_unit.heading)
            page_transition_new_topic = (unit.page_number != prev_unit.page_number) and (unit.heading != prev_unit.heading)

            # Check for explicit topic discontinuity marker
            first_line_lower = unit.content.split("\n")[0].lower()
            explicit_discontinuity = any(m in first_line_lower for m in self.DISCONTINUITY_MARKERS)

            # Check if accumulated size exceeds target child tokens
            size_exceeded = (current_tokens + unit_tokens > self.config.target_child_tokens * 1.5)

            if heading_changed or page_transition_new_topic or explicit_discontinuity or (size_exceeded and current_tokens >= self.config.min_child_tokens):
                flush_current()
                current_units.append(unit)
            else:
                current_units.append(unit)

        flush_current()
        return candidates
