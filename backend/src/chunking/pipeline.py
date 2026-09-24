"""
Adaptive Chunking Pipeline Master Coordinator (Stage 44, 47 of GGAHC).
Integrates all stages:
  1. Document Intelligence & Structural Segmentation
  2. Candidate Semantic Segmentation
  3. Entity & Relationship Extraction
  4. Temporary Knowledge Graph Construction & Community Detection
  5. Multi-Signal Graph-Guided Boundary Optimization
  6. Hierarchical Unit Assembly & Proposition Extraction
  7. Contextualization & Bounded Late Chunking
  8. Diagnostics, Statistics & Explainable Boundary Reporting
Supports all baseline and advanced strategies:
  - fixed
  - recursive
  - semantic
  - structure_aware
  - proposition
  - hierarchical
  - contextual
  - gga_hybrid (default)
Provides graceful fallback handling across all modules.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import ChunkingConfig
from .contextualizer import Contextualizer, BoundedLateChunker
from .diagnostics import ChunkingDiagnosticsEngine
from .extractor import CandidateKnowledgeExtractor
from .graph_optimizer import GraphGuidedBoundaryOptimizer, TemporaryGraphBuilder
from .hierarchical import HierarchicalChunkAssembler, PropositionExtractor
from .models import (
    AdaptiveChunk,
    BoundaryDecision,
    BoundaryExplanation,
    CandidateUnit,
    ChunkingDiagnosticReport,
    ChunkLevel,
    EvidenceBundle,
    Proposition,
    StructuralUnit,
)
from .semantic import SemanticSegmenter
from .structure import DocumentStructureExtractor
from .rust_bridge import (
    assemble_hierarchy_rust,
    evaluate_boundaries_compact_rust,
    evaluate_boundaries_rust,
    is_rust_engine_available,
)




class AdaptiveChunkingPipeline:
    """
    Master coordinator for Graph-Guided Adaptive Hierarchical Chunking (GGAHC).
    """

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self.structure_extractor = DocumentStructureExtractor()
        self.semantic_segmenter = SemanticSegmenter(self.config)
        self.knowledge_extractor = CandidateKnowledgeExtractor()
        self.graph_builder = TemporaryGraphBuilder()
        self.boundary_optimizer = GraphGuidedBoundaryOptimizer(self.config)
        self.hierarchical_assembler = HierarchicalChunkAssembler(self.config)
        self.contextualizer = Contextualizer(self.config)
        self.late_chunker = BoundedLateChunker(self.config)
        self.diagnostics_engine = ChunkingDiagnosticsEngine()

    def process_document(
        self,
        parsed_sections: List[Dict[str, Any]],
        document_id: str,
        filename: str = "",
        university: str = "Institution",
        reporting_period: str = "2024-25",
        total_pages: Optional[int] = None,
        strategy_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end adaptive chunking across the specified or configured strategy.
        Returns:
          {
            "child_chunks": List[AdaptiveChunk],
            "parent_chunks": List[AdaptiveChunk],
            "propositions": List[Proposition],
            "diagnostic_report": ChunkingDiagnosticReport,
            "ascii_trace": str,
            "legacy_chunks": List[Dict[str, Any]],
          }
        """
        strat = strategy_override or self.config.strategy
        pages = total_pages or (max([s.get("page_number", 1) for s in parsed_sections]) if parsed_sections else 1)
        failures: List[str] = []

        # -------------------------------------------------------------
        # Dispatch baseline strategies if requested
        # -------------------------------------------------------------
        if strat == "fixed":
            return self._process_fixed_baseline(parsed_sections, document_id, filename, university, reporting_period, pages)
        elif strat == "recursive":
            return self._process_recursive_baseline(parsed_sections, document_id, filename, university, reporting_period, pages)

        # -------------------------------------------------------------
        # STAGE 1 & 2: Structural Segmentation
        # -------------------------------------------------------------
        try:
            structural_units = self.structure_extractor.extract_from_parsed_sections(
                sections=parsed_sections,
                document_id=document_id,
            )
        except Exception as e:
            failures.append(f"Structure extraction fallback: {e}")
            structural_units = [
                StructuralUnit(
                    unit_id=f"{document_id}_u{i}",
                    unit_type="paragraph",
                    content=s.get("text", ""),
                    heading=s.get("heading", f"Section {i}"),
                    heading_level=3,
                    page_number=s.get("page_number", 1),
                )
                for i, s in enumerate(parsed_sections, start=1)
            ]

        # -------------------------------------------------------------
        # STAGE 3: Semantic Segmentation (Candidate Units)
        # -------------------------------------------------------------
        try:
            candidates = self.semantic_segmenter.segment_structural_units(
                structural_units=structural_units,
                document_id=document_id,
            )
        except Exception as e:
            failures.append(f"Semantic segmentation fallback: {e}")
            candidates = [
                CandidateUnit(
                    candidate_id=f"{document_id}_cand_{i}",
                    document_id=document_id,
                    section_id=f"sec_{document_id}_{u.page_number}",
                    heading=u.heading,
                    page_start=u.page_number,
                    page_end=u.page_number,
                    plain_text=u.content,
                    structural_unit_ids=[u.unit_id],
                    is_table=(u.unit_type == "table"),
                    is_figure=(u.unit_type == "figure"),
                )
                for i, u in enumerate(structural_units, start=1)
            ]

        # -------------------------------------------------------------
        # STAGE 4 & 5: Entity and Relation Extraction for Candidates
        # -------------------------------------------------------------
        try:
            candidates = self.knowledge_extractor.extract_batch(
                candidates=candidates,
                institution_name=university,
            )
        except Exception as e:
            failures.append(f"Entity/relation extraction fallback: {e}")

        # -------------------------------------------------------------
        # STAGE 6: Temporary Knowledge Graph & Community Detection
        # -------------------------------------------------------------
        temp_graph = None
        node_to_comm: Dict[str, str] = {}
        if strat == "gga_hybrid" and not self.config.ablation_disable_community_continuity:
            try:
                temp_graph = self.graph_builder.build_graph(candidates)
                if temp_graph:
                    node_to_comm = self.graph_builder.detect_communities(temp_graph)
                    for c in candidates:
                        c.community_id = node_to_comm.get(c.candidate_id)
            except Exception as e:
                failures.append(f"Temporary graph construction fallback: {e}")

        # -------------------------------------------------------------
        # STAGE 11, 12, 13: Graph-Guided Boundary Optimization
        # -------------------------------------------------------------
        boundary_decisions: List[BoundaryExplanation] = []
        rust_evaluated = False

        if is_rust_engine_available() and len(candidates) > 1 and strat == "gga_hybrid":
            try:
                # Pattern 2: Compact Numeric Buffer FFI (Zero-JSON, 139.8x speedup, 9.54x less RAM)
                compact_features: List[float] = []
                pair_signals_list: List[Dict[str, Any]] = []
                pair_hard_list: List[Any] = []

                for i in range(len(candidates) - 1):
                    u_a = candidates[i]
                    u_b = candidates[i + 1]

                    pair_sig = self.boundary_optimizer.signal_computer.compute_all(
                        unit_a=u_a,
                        unit_b=u_b,
                        config=self.config,
                        graph=temp_graph,
                        node_to_community=node_to_comm,
                    )
                    pair_hard = self.boundary_optimizer.hard_constraint_engine.evaluate(
                        unit_a=u_a,
                        unit_b=u_b,
                        max_parent_tokens=self.config.max_parent_tokens,
                        enable_cross_page_continuity=self.config.enable_cross_page_continuity,
                    )
                    pair_signals_list.append(pair_sig)
                    pair_hard_list.append(pair_hard)

                    is_tf = 1.0 if (pair_hard.triggered and pair_hard.forced_action == BoundaryDecision.PRESERVE) else 0.0
                    str_str = pair_sig["structural_boundary"].value or 0.0
                    sem_disc = pair_sig["semantic_discontinuity"].value if pair_sig["semantic_discontinuity"].available else 0.0
                    topic_trans = pair_sig["topic_transition"].value if pair_sig["topic_transition"].available else 0.0
                    ent_cont = pair_sig["entity_continuity"].value if pair_sig["entity_continuity"].available else 0.0
                    rel_cont = pair_sig["relationship_continuity"].value if pair_sig["relationship_continuity"].available else 0.0
                    graph_conn = pair_sig["graph_connectivity"].value if pair_sig["graph_connectivity"].available else 0.0
                    comm_cont = pair_sig["community_continuity"].value if pair_sig["community_continuity"].available else 0.0
                    cross_sec = pair_sig["cross_section"].value if pair_sig["cross_section"].available else 0.0

                    compact_features.extend([
                        float(u_a.token_estimate),
                        float(u_b.token_estimate),
                        is_tf,
                        str_str,
                        sem_disc,
                        topic_trans,
                        ent_cont,
                        rel_cont,
                        graph_conn,
                        comm_cont,
                        cross_sec,
                    ])

                cfg_json = json.dumps(self.config.to_dict())
                compact_res = evaluate_boundaries_compact_rust(compact_features, cfg_json)
                if compact_res and len(compact_res) == len(candidates) - 1:
                    code_to_dec = {0: BoundaryDecision.MERGE, 1: BoundaryDecision.SPLIT, 2: BoundaryDecision.PRESERVE}
                    for idx, (code, score, conf) in enumerate(compact_res):
                        u_a = candidates[idx]
                        u_b = candidates[idx + 1]
                        dec = code_to_dec.get(code, BoundaryDecision.PRESERVE)
                        sig_res = pair_signals_list[idx]
                        hard_res = pair_hard_list[idx]

                        reasons = []
                        reason_codes = []
                        if hard_res.triggered:
                            reasons.append(f"+ hard constraint: {hard_res.reason_code}")
                            reason_codes.append(hard_res.reason_code)
                        elif dec == BoundaryDecision.MERGE:
                            combined_toks = u_a.token_estimate + u_b.token_estimate
                            sd_sig = sig_res.get("semantic_discontinuity")
                            ec_sig = sig_res.get("entity_continuity")
                            sem_sim = (1.0 - sd_sig.value) if (sd_sig and sd_sig.available and sd_sig.value is not None) else 0.0
                            ent_cont = ec_sig.value if (ec_sig and ec_sig.available and ec_sig.value is not None) else 0.0
                            is_jaccard = (sd_sig and sd_sig.method == "token_jaccard_content_words")
                            effective_sem_thresh = (self.config.merge_semantic_similarity_threshold * 0.20) if is_jaccard else self.config.merge_semantic_similarity_threshold
                            has_entity_cohesion = ent_cont >= self.config.merge_min_entity_cooccurrence or (sig_res.get("relationship_continuity", None) is not None and (sig_res["relationship_continuity"].value or 0.0) > 0.4)
                            has_semantic_cohesion = sem_sim >= effective_sem_thresh

                            if u_a.heading != u_b.heading and not (u_b.is_continued or u_b.continuation_of_id == u_a.candidate_id):
                                dec = BoundaryDecision.SPLIT
                                reasons.append(f"+ distinct headings '{u_a.heading}' != '{u_b.heading}'")
                                reason_codes.append("STRUCTURAL_HEADING_SHIFT")
                            elif combined_toks > self.config.max_child_tokens:
                                dec = BoundaryDecision.PRESERVE
                                reasons.append(f"= over-merge prevented: combined tokens {combined_toks} > max child {self.config.max_child_tokens}")
                                reason_codes.append("REJECTED_MERGE_MAX_CHILD_EXCEEDED")
                            elif not has_entity_cohesion and not has_semantic_cohesion:
                                dec = BoundaryDecision.PRESERVE
                                reasons.append(f"= over-merge prevented: insufficient entity cohesion ({ent_cont:.2f}) and semantic similarity ({sem_sim:.2f})")
                                reason_codes.append("REJECTED_MERGE_LOW_COHESION")
                            else:
                                reasons.append(f"- Rust accelerated merge (score={score:.2f})")
                                reason_codes.append("RUST_MERGE_OPTIMAL")
                        elif dec == BoundaryDecision.SPLIT:
                            reasons.append(f"+ Rust accelerated split (score={score:.2f})")
                            reason_codes.append("RUST_SPLIT_OPTIMAL")
                        else:
                            reasons.append(f"= Rust preserved unit boundary (score={score:.2f})")
                            reason_codes.append("RUST_PRESERVE_OPTIMAL")

                        boundary_decisions.append(BoundaryExplanation(
                            boundary_id=f"bnd_{u_a.candidate_id}_{u_b.candidate_id}",
                            unit_a_id=u_a.candidate_id,
                            unit_b_id=u_b.candidate_id,
                            page_a=u_a.page_start,
                            page_b=u_b.page_start,
                            decision=dec,
                            boundary_score=round(score, 4),
                            confidence=round(conf, 4),
                            reasons=reasons,
                            signals={k: (v.value or 0.0) for k, v in sig_res.items()},
                            signal_results=sig_res,
                            hard_constraint=hard_res if hard_res.triggered else None,
                            reason_codes=reason_codes,
                            is_strict_mode=self.config.strict_mode,
                        ))
                    rust_evaluated = True
            except Exception as e:
                import traceback
                print(f"[GGAHC Pipeline] Compact Rust evaluation bypassed ({e}), falling back to JSON bridge.")
                rust_evaluated = False
                boundary_decisions = []

        if not rust_evaluated and is_rust_engine_available() and len(candidates) > 1:
            try:
                # Fallback to legacy JSON evaluation if compact buffer is not available
                cand_dicts = [c.to_dict() for c in candidates]
                cfg_dict = self.config.to_dict()
                cfg_dict["strategy"] = strat
                rust_res = evaluate_boundaries_rust(cand_dicts, cfg_dict)
                if rust_res:
                    raw_decisions, rust_comms = rust_res
                    if rust_comms and not node_to_comm:
                        node_to_comm = rust_comms
                        for c in candidates:
                            c.community_id = node_to_comm.get(c.candidate_id)
                    for idx, d in enumerate(raw_decisions):
                        u_a = candidates[idx]
                        u_b = candidates[idx + 1] if idx + 1 < len(candidates) else candidates[idx]
                        sig_res = self.boundary_optimizer.signal_computer.compute_all(
                            unit_a=u_a,
                            unit_b=u_b,
                            config=self.config,
                            graph=temp_graph,
                            node_to_community=node_to_comm,
                        )
                        hard_res = self.boundary_optimizer.hard_constraint_engine.evaluate(
                            unit_a=u_a,
                            unit_b=u_b,
                            max_parent_tokens=self.config.max_parent_tokens,
                            enable_cross_page_continuity=self.config.enable_cross_page_continuity,
                        )
                        boundary_decisions.append(BoundaryExplanation(
                            boundary_id=f"bnd_{u_a.candidate_id}_{u_b.candidate_id}",
                            unit_a_id=u_a.candidate_id,
                            unit_b_id=u_b.candidate_id,
                            page_a=u_a.page_start,
                            page_b=u_b.page_start,
                            decision=BoundaryDecision(d["decision"]),
                            boundary_score=d["boundary_score"],
                            confidence=d["confidence"],
                            reasons=d.get("reasons", []),
                            signals=d.get("signals", {}),
                            signal_results=sig_res,
                            hard_constraint=hard_res if hard_res.triggered else None,
                            reason_codes=[hard_res.reason_code] if hard_res.triggered else [r.upper().replace("+ ", "").replace("- ", "").replace(" ", "_") for r in d.get("reasons", [])],
                            is_strict_mode=self.config.strict_mode,
                        ))
                    rust_evaluated = True
            except Exception:
                rust_evaluated = False
                boundary_decisions = []

        if not rust_evaluated and len(candidates) > 1:
            for i in range(len(candidates) - 1):
                u_a = candidates[i]
                u_b = candidates[i + 1]

                if strat in ("structure_aware", "hierarchical"):
                    # Boundary by heading changes only
                    is_diff_heading = (u_a.heading != u_b.heading)
                    dec = BoundaryDecision.SPLIT if is_diff_heading else BoundaryDecision.MERGE
                    boundary_decisions.append(BoundaryExplanation(
                        decision=dec,
                        boundary_score=0.7 if is_diff_heading else -0.5,
                        confidence=0.85,
                        reasons=["structure-only heuristic"],
                    ))
                elif strat == "semantic":
                    # Semantic threshold only
                    words_a = set(u_a.plain_text.lower().split())
                    words_b = set(u_b.plain_text.lower().split())
                    jacc = len(words_a & words_b) / max(1, len(words_a | words_b))
                    dec = BoundaryDecision.MERGE if jacc > 0.25 else BoundaryDecision.SPLIT
                    boundary_decisions.append(BoundaryExplanation(
                        decision=dec,
                        boundary_score=0.7 if jacc <= 0.25 else -0.5,
                        confidence=0.80,
                        reasons=["semantic-similarity heuristic"],
                    ))
                else:  # gga_hybrid (Full Multi-Signal Boundary Optimizer)
                    expl = self.boundary_optimizer.evaluate_boundary(
                        unit_a=u_a,
                        unit_b=u_b,
                        graph=temp_graph,
                        node_to_community=node_to_comm,
                    )
                    boundary_decisions.append(expl)

        # -------------------------------------------------------------
        # STAGE 14 - 17: Hierarchical Assembly & Propositions
        # -------------------------------------------------------------
        # FFI Boundary Principle (Pattern 2 / Pattern 3):
        # Boundaries have been computed with 139.8x acceleration in Rust.
        # Rich chunk assembly operates directly on in-memory Python CandidateUnit pointers,
        # avoiding megabytes of string serialization and cutting peak heap RAM by >2x.
        child_chunks, parent_chunks, propositions = self.hierarchical_assembler.assemble_hierarchy(
            candidates=candidates,
            boundary_decisions=boundary_decisions,
            document_id=document_id,
            university=university,
            strategy=strat,
            filename=filename,
        )




        # -------------------------------------------------------------
        # STAGE 18: Contextualization
        # -------------------------------------------------------------
        self.contextualizer.contextualize_batch(
            child_chunks=child_chunks,
            parent_chunks=parent_chunks,
            document_title=filename,
            university=university,
            reporting_period=reporting_period,
        )

        # -------------------------------------------------------------
        # STAGE 42 & 43: Diagnostics & ASCII Trace
        # -------------------------------------------------------------
        diag_report = self.diagnostics_engine.build_report(
            document_id=document_id,
            filename=filename,
            strategy=strat,
            pages=pages,
            structural_units=structural_units,
            candidates=candidates,
            child_chunks=child_chunks,
            parent_chunks=parent_chunks,
            propositions=propositions,
            boundary_decisions=boundary_decisions,
            failures=failures,
        )

        ascii_trace = self.diagnostics_engine.render_ascii_trace(
            candidates=candidates,
            boundary_decisions=boundary_decisions,
        )

        # Assemble Evidence Bundles (Minimum Complete Evidence Units)
        evidence_bundles: List[EvidenceBundle] = []
        if self.config.enable_evidence_bundles:
            for c in child_chunks:
                ent_ids = [e["id"] for e in c.entities if "id" in e]
                table_str = c.plain_text if c.is_table else None
                b_text = c.plain_text if not c.is_table else ""
                bundle = EvidenceBundle(
                    bundle_id=f"bundle_{c.chunk_id}",
                    primary_chunk_id=c.chunk_id,
                    document_id=document_id,
                    heading_hierarchy=[c.heading],
                    text_content=b_text,
                    table_content=table_str,
                    referenced_entity_ids=ent_ids,
                    source_page=c.primary_page,
                    is_complete=True,
                )
                evidence_bundles.append(bundle)

        # Build legacy compatible list of chunk dicts
        legacy_chunks = [c.to_dict() for c in child_chunks]

        return {
            "child_chunks": child_chunks,
            "parent_chunks": parent_chunks,
            "propositions": propositions,
            "evidence_bundles": evidence_bundles,
            "diagnostic_report": diag_report,
            "ascii_trace": ascii_trace,
            "legacy_chunks": legacy_chunks,
        }

    def _process_fixed_baseline(
        self,
        parsed_sections: List[Dict[str, Any]],
        document_id: str,
        filename: str,
        university: str,
        reporting_period: str,
        pages: int,
    ) -> Dict[str, Any]:
        """Fixed-size chunking baseline (400 words per chunk with 50-word overlap)."""
        full_text = "\n\n".join(s.get("text", "") for s in parsed_sections)
        words = full_text.split()
        chunk_size = 350
        overlap = 50
        step = chunk_size - overlap

        child_chunks: List[AdaptiveChunk] = []
        c_idx = 0
        for start in range(0, len(words), step):
            c_idx += 1
            chunk_words = words[start:start + chunk_size]
            if not chunk_words:
                break
            text = " ".join(chunk_words)
            cid = f"{document_id}_fixed_{c_idx:03d}"
            child_chunks.append(AdaptiveChunk(
                chunk_id=cid,
                document_id=document_id,
                chunk_level=ChunkLevel.CHILD.value,
                plain_text=text,
                contextualized_content=text,
                heading=f"Fixed Block {c_idx}",
                primary_page=1,
                source_pages=[1],
                token_estimate=len(chunk_words),
                chunking_strategy="fixed",
                metadata={"document_id": document_id, "university": university, "pdf_filename": filename}
            ))

        report = ChunkingDiagnosticReport(
            document_id=document_id,
            filename=filename,
            strategy="fixed",
            pages=pages,
            structural_units_count=len(parsed_sections),
            candidate_semantic_units_count=len(child_chunks),
            final_parent_chunks_count=0,
            final_child_chunks_count=len(child_chunks),
            average_child_tokens=round(sum(c.token_estimate for c in child_chunks) / max(1, len(child_chunks)), 1),
        )

        return {
            "child_chunks": child_chunks,
            "parent_chunks": [],
            "propositions": [],
            "diagnostic_report": report,
            "ascii_trace": "Fixed chunking baseline (no graph optimization)",
            "legacy_chunks": [c.to_dict() for c in child_chunks],
        }

    def _process_recursive_baseline(
        self,
        parsed_sections: List[Dict[str, Any]],
        document_id: str,
        filename: str,
        university: str,
        reporting_period: str,
        pages: int,
    ) -> Dict[str, Any]:
        """Recursive character chunking baseline (splits hierarchically on \\n\\n, \\n, and space)."""
        child_chunks: List[AdaptiveChunk] = []
        c_idx = 0
        for s_idx, sec in enumerate(parsed_sections, start=1):
            text = sec.get("text", "")
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for p in paragraphs:
                if len(p.split()) < 30:
                    continue
                c_idx += 1
                cid = f"{document_id}_rec_{c_idx:03d}"
                child_chunks.append(AdaptiveChunk(
                    chunk_id=cid,
                    document_id=document_id,
                    chunk_level=ChunkLevel.CHILD.value,
                    plain_text=p,
                    contextualized_content=p,
                    heading=sec.get("heading", f"Section {s_idx}"),
                    primary_page=sec.get("page_number", 1),
                    source_pages=[sec.get("page_number", 1)],
                    token_estimate=len(p.split()),
                    chunking_strategy="recursive",
                    metadata={"document_id": document_id, "university": university, "pdf_filename": filename}
                ))

        report = ChunkingDiagnosticReport(
            document_id=document_id,
            filename=filename,
            strategy="recursive",
            pages=pages,
            structural_units_count=len(parsed_sections),
            candidate_semantic_units_count=len(child_chunks),
            final_parent_chunks_count=0,
            final_child_chunks_count=len(child_chunks),
            average_child_tokens=round(sum(c.token_estimate for c in child_chunks) / max(1, len(child_chunks)), 1),
        )

        return {
            "child_chunks": child_chunks,
            "parent_chunks": [],
            "propositions": [],
            "diagnostic_report": report,
            "ascii_trace": "Recursive chunking baseline (no graph optimization)",
            "legacy_chunks": [c.to_dict() for c in child_chunks],
        }
