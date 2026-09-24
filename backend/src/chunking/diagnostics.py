"""
Diagnostics and Visual Decision Tracing (Stage 42, 43 of GGAHC).
Generates machine-readable diagnostic reports and human-interpretable visual ASCII traces
explaining exact boundary decisions ('Why was this boundary created?').
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    AdaptiveChunk,
    BoundaryDecision,
    BoundaryExplanation,
    CandidateUnit,
    ChunkingDiagnosticReport,
    Proposition,
    StructuralUnit,
)


class ChunkingDiagnosticsEngine:
    """
    Generates machine-readable reports and ASCII visual debug representations
    for explainability audits.
    """

    def __init__(self):
        pass

    def build_report(
        self,
        document_id: str,
        filename: str,
        strategy: str,
        pages: int,
        structural_units: List[StructuralUnit],
        candidates: List[CandidateUnit],
        child_chunks: List[AdaptiveChunk],
        parent_chunks: List[AdaptiveChunk],
        propositions: List[Proposition],
        boundary_decisions: List[BoundaryExplanation],
        failures: Optional[List[str]] = None,
    ) -> ChunkingDiagnosticReport:
        """Constructs machine-readable diagnostic metrics."""
        child_tokens = [c.token_estimate for c in child_chunks] if child_chunks else [0]
        parent_tokens = [p.token_estimate for p in parent_chunks] if parent_chunks else [0]

        merges = sum(1 for b in boundary_decisions if b.decision == BoundaryDecision.MERGE)
        splits = sum(1 for b in boundary_decisions if b.decision == BoundaryDecision.SPLIT)
        preserves = sum(1 for b in boundary_decisions if b.decision == BoundaryDecision.PRESERVE)

        avg_conf = (
            sum(b.confidence for b in boundary_decisions) / len(boundary_decisions)
            if boundary_decisions else 1.0
        )

        # Count total entities & relationships
        all_ents = set()
        all_rels = set()
        for c in child_chunks:
            for e in c.entities:
                all_ents.add(e["id"])
            for r in c.relationships:
                all_rels.add(r.get("relation_id", str(r)))

        # Count distinct communities
        comms = set()
        for c in candidates:
            if c.community_id:
                comms.add(c.community_id)

        tbls = sum(1 for c in child_chunks if c.is_table)
        figs = sum(1 for c in child_chunks if c.is_figure)

        # Compute Signal Availability Rates and Hard Constraints
        signal_counts: Dict[str, int] = {}
        signal_available_counts: Dict[str, int] = {}
        hard_constraints: Dict[str, int] = {}
        decision_ledger: List[Dict[str, Any]] = []

        for b in boundary_decisions:
            decision_ledger.append(b.to_dict())
            if b.hard_constraint and b.hard_constraint.triggered:
                ctype = b.hard_constraint.constraint_type or "OTHER_HARD_CONSTRAINT"
                hard_constraints[ctype] = hard_constraints.get(ctype, 0) + 1

            for s_name, s_res in b.signal_results.items():
                signal_counts[s_name] = signal_counts.get(s_name, 0) + 1
                if s_res.available:
                    signal_available_counts[s_name] = signal_available_counts.get(s_name, 0) + 1

        availability_rates: Dict[str, float] = {}
        for s_name, total_evaluated in signal_counts.items():
            avail = signal_available_counts.get(s_name, 0)
            availability_rates[s_name] = round(avail / max(1, total_evaluated), 3)

        traces = [b.to_dict() for b in boundary_decisions]

        return ChunkingDiagnosticReport(
            document_id=document_id,
            filename=filename,
            strategy=strategy,
            pages=pages,
            structural_units_count=len(structural_units),
            candidate_semantic_units_count=len(candidates),
            final_parent_chunks_count=len(parent_chunks),
            final_child_chunks_count=len(child_chunks),
            propositions_count=len(propositions),
            entities_count=len(all_ents),
            relationships_count=len(all_rels),
            communities_count=len(comms),
            average_child_tokens=round(sum(child_tokens) / max(1, len(child_tokens)), 1),
            average_parent_tokens=round(sum(parent_tokens) / max(1, len(parent_tokens)), 1),
            merge_operations=merges,
            split_operations=splits,
            preserve_operations=preserves,
            average_boundary_confidence=round(avg_conf, 3),
            tables_count=tbls,
            figures_count=figs,
            signal_availability_rates=availability_rates,
            hard_constraints_triggered=hard_constraints,
            decision_ledger=decision_ledger,
            evidence_bundles_count=len(child_chunks),
            boundary_traces=traces,
            failures=failures or [],
        )

    def render_ascii_trace(
        self,
        candidates: List[CandidateUnit],
        boundary_decisions: List[BoundaryExplanation],
        max_units: int = 8,
    ) -> str:
        """
        Renders human-readable ASCII decision graph for explainability inspection (Prompt Section 43).
        """
        lines = [
            "=================================================================",
            "    GRAPH-GUIDED BOUNDARY OPTIMIZATION EXPLAINABILITY TRACE      ",
            "=================================================================",
        ]

        display_count = min(len(candidates), max_units)
        for i in range(display_count):
            c = candidates[i]
            lines.append(f"\n[Unit {i+1}: {c.candidate_id}] (p.{c.page_start})")
            lines.append(f"  Heading : {c.heading[:50]}")
            ent_names = [e.get("name", e["id"]) for e in c.entities[:4]]
            lines.append(f"  Entities: {', '.join(ent_names) if ent_names else 'None'}")
            lines.append(f"  Tokens  : {c.token_estimate} words")

            if i < len(boundary_decisions) and i < display_count - 1:
                b = boundary_decisions[i]
                dec = b.decision.value
                symbol = "│\n        ▼ [MERGE: Combined into coherent parent]" if dec == "MERGE" else "│\n        ✂️ [SPLIT: Boundary finalized]"
                if dec == "PRESERVE":
                    symbol = "│\n        🔒 [PRESERVE: Discrete unit maintained]"
                
                lines.append(f"        {symbol}")
                lines.append(f"        Score: {b.boundary_score:.2f} | Confidence: {b.confidence:.2f}")
                for r in b.reasons[:3]:
                    lines.append(f"        * {r}")
                lines.append("        │")

        lines.append("\n=================================================================\n")
        return "\n".join(lines)
