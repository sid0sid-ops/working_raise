"""
RAISE — Full-Document Graph-Guided Adaptive Hierarchical Chunking (GGAHC) Runner
================================================================================
Executes the complete, end-to-end GGAHC pipeline on a full PDF document:
  1. Document Intelligence & Structural Layout Extraction (Docling / SmartParser)
  2. Candidate Semantic Segmentation
  3. Candidate Entity & Relation Extraction
  4. Temporary Knowledge Graph Construction & Community Detection (LPA)
  5. Rust-Accelerated Multi-Signal Boundary Optimization (Pattern 2 Compact Buffer)
  6. Hierarchical Unit Assembly (Parent Chunks, Child Chunks, Propositions)
  7. Contextualization & Metadata Injection
  8. Full Post-Chunking Institutional Knowledge Graph Triples & Fact Extraction
  9. Comprehensive Diagnostics, Telemetry, and Quantitative Breakdown
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

# Enforce UTF-8 console output for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure RAG directory is in Python path
RAG_DIR = Path(__file__).resolve().parent.parent
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from src.parsers.document_parser import SmartDocumentParser
from src.chunking.pipeline import AdaptiveChunkingPipeline
from src.chunking.config import ChunkingConfig
from src.features.ingestion.academic_extractor import (
    AcademicDomainExtractor,
    AcademicEntity,
    AcademicRelation,
)
from src.features.verification.fact_engine import FactEngine


def run_full_pdf_ggahc(
    pdf_path: Path,
    output_dir: Optional[Path] = None,
    engine: str = "auto",
    save_artifacts: bool = True,
) -> Dict[str, Any]:
    print("=" * 80)
    print(" 🚀 ADVANCED GRAPH-GUIDED ADAPTIVE HIERARCHICAL CHUNKING (GGAHC) — FULL RUN")
    print("=" * 80)
    print(f" PDF Source File : {pdf_path.resolve()}")
    print(f" File Size       : {pdf_path.stat().st_size / (1024 * 1024):.2f} MB")
    print(f" Parse Engine    : {engine.upper()}")
    print("=" * 80)

    t_total_start = time.perf_counter()

    # 1. Document Layout & Structure Parsing
    print("\n[Phase 1/6] Executing Document Intelligence & Layout Parsing...")
    t0 = time.perf_counter()
    parser = SmartDocumentParser()
    parsed_sections = parser.parse_pdf(
        pdf_path,
        max_pages=None,  # Full PDF: no page cap
        engine=engine,
        extract_tables=True,
    )
    t_parse = time.perf_counter() - t0
    total_pages = len(parsed_sections)
    print(f"  -> Extracted {total_pages} page sections in {t_parse:.2f}s ({total_pages / max(t_parse, 0.001):.1f} pages/sec)")

    doc_id = re.sub(r"[^a-zA-Z0-9_]", "_", pdf_path.stem)
    institution_name = "IIT Madras Research Park" if "iitmrp" in pdf_path.stem.lower() else "Institution"
    reporting_period = "2024-25"

    # 2. Configure & Run Master GGAHC Pipeline
    print("\n[Phase 2/6] Initializing GGAHC Adaptive Chunking Pipeline (Rust Accelerated)...")
    config = ChunkingConfig(
        strategy="gga_hybrid",
        target_child_tokens=256,
        min_child_tokens=64,
        max_child_tokens=512,
        target_parent_tokens=1024,
        max_parent_tokens=2048,
        enable_propositions=True,
        enable_parent_child=True,
    )
    pipeline = AdaptiveChunkingPipeline(config=config)

    t1 = time.perf_counter()
    result = pipeline.process_document(
        parsed_sections=parsed_sections,
        document_id=doc_id,
        filename=pdf_path.name,
        university=institution_name,
        reporting_period=reporting_period,
        total_pages=total_pages,
    )
    t_chunking = time.perf_counter() - t1

    child_chunks = result["child_chunks"]
    parent_chunks = result["parent_chunks"]
    propositions = result["propositions"]
    diag_report = result["diagnostic_report"]
    legacy_chunks = result["legacy_chunks"]

    print(f"  -> GGAHC pipeline completed in {t_chunking:.3f}s")
    print(f"  -> Generated {len(parent_chunks)} Parent Chunks")
    print(f"  -> Generated {len(child_chunks)} Child Chunks")
    print(f"  -> Extracted {len(propositions)} Atomic Propositions")

    # 3. Analyze In-Chunking Graph & Candidate Topology
    boundaries = getattr(diag_report, "boundary_traces", []) or []
    decision_counts = Counter(b.get("decision") if isinstance(b, dict) else str(b) for b in boundaries)
    
    # Analyze tokens
    child_token_lengths = [c.token_estimate for c in child_chunks]
    parent_token_lengths = [p.token_estimate for p in parent_chunks]
    prop_token_lengths = [len(p.text.split()) for p in propositions]

    avg_child_tokens = sum(child_token_lengths) / max(len(child_token_lengths), 1)
    avg_parent_tokens = sum(parent_token_lengths) / max(len(parent_token_lengths), 1)
    avg_prop_tokens = sum(prop_token_lengths) / max(len(prop_token_lengths), 1)

    # Tables vs Text
    table_children = [c for c in child_chunks if c.is_table]
    text_children = [c for c in child_chunks if not c.is_table]

    # In-chunking candidate entities & relationships
    cand_entities_counter = Counter()
    cand_relations_counter = Counter()
    total_cand_entities = 0
    total_cand_relations = 0
    for c in child_chunks:
        for ent in c.entities:
            ename = ent.get("name") or ent.get("text", "")
            etype = ent.get("label") or ent.get("type", "Entity")
            cand_entities_counter[etype] += 1
            total_cand_entities += 1
        for rel in c.relationships:
            rtype = rel.get("type") or rel.get("relation_type", "RELATED")
            cand_relations_counter[rtype] += 1
            total_cand_relations += 1

    # 4. Extract Full Institutional Knowledge Graph Triples & Fact Alignment
    print("\n[Phase 4/6] Extracting Institutional Knowledge Graph Triples & Fact Envelopes...")
    t2 = time.perf_counter()
    academic_extractor = AcademicDomainExtractor()
    fact_engine = FactEngine()

    all_entities: List[AcademicEntity] = []
    all_relations: List[AcademicRelation] = []

    # Map Parent-Child hierarchy edges
    for child in child_chunks:
        if child.parent_chunk_id:
            all_relations.append(AcademicRelation(
                relation_id=f"rel_{child.chunk_id}_{child.parent_chunk_id}_has_parent",
                source_id=child.chunk_id,
                source_label="Chunk",
                relation_type="HAS_PARENT_CHUNK",
                target_id=child.parent_chunk_id,
                target_label="ParentChunk",
                provenance={"pdf_filename": pdf_path.name, "page_number": child.primary_page, "chunk_id": child.chunk_id},
            ))

    # Map Child-Proposition hierarchy edges
    for prop in propositions:
        all_relations.append(AcademicRelation(
            relation_id=f"rel_{prop.parent_chunk_id}_{prop.proposition_id}_has_prop",
            source_id=prop.parent_chunk_id,
            source_label="Chunk",
            relation_type="HAS_PROPOSITION",
            target_id=prop.proposition_id,
            target_label="Proposition",
            provenance={"pdf_filename": pdf_path.name, "chunk_id": prop.parent_chunk_id},
        ))

    # Register Parent Chunks as Graph Entities
    for p in parent_chunks:
        all_entities.append(AcademicEntity(
            entity_id=p.chunk_id,
            label="ParentChunk",
            name=f"ParentChunk {p.chunk_id}",
            properties={
                "document_id": doc_id,
                "token_estimate": p.token_estimate,
                "heading": p.heading,
                "page_start": p.primary_page,
                "page_end": p.source_pages[-1] if p.source_pages else p.primary_page,
                "source_pages": p.source_pages,
            },
            provenance={"pdf_filename": pdf_path.name, "page_number": p.primary_page, "chunk_id": p.chunk_id},
        ))

    # Register Child Chunks & Extract Fine-Grained Knowledge
    for chunk in child_chunks:
        chunk_ent = AcademicEntity(
            entity_id=chunk.chunk_id,
            label="Chunk",
            name=f"Chunk {chunk.chunk_id}",
            properties={
                "document_id": doc_id,
                "primary_page": chunk.primary_page,
                "heading": chunk.heading,
                "token_estimate": chunk.token_estimate,
                "parent_chunk_id": chunk.parent_chunk_id,
                "is_table": chunk.is_table,
            },
            provenance={"pdf_filename": pdf_path.name, "page_number": chunk.primary_page, "chunk_id": chunk.chunk_id},
        )
        all_entities.append(chunk_ent)

        # Domain Entity & Relationship Extraction
        ents, rels = academic_extractor.extract_academic_knowledge(
            text=chunk.plain_text,
            pdf_filename=pdf_path.name,
            page_number=chunk.primary_page,
            section_heading=chunk.heading,
            chunk_id=chunk.chunk_id,
            university_name=institution_name,
        )
        all_entities.extend(ents)
        all_relations.extend(rels)

        # MENTIONS edges
        for e in ents:
            all_relations.append(AcademicRelation(
                relation_id=f"rel_{chunk.chunk_id}_{e.entity_id}_mentions",
                source_id=chunk.chunk_id,
                source_label="Chunk",
                relation_type="MENTIONS",
                target_id=e.entity_id,
                target_label=e.label,
                provenance={"pdf_filename": pdf_path.name, "page_number": chunk.primary_page, "chunk_id": chunk.chunk_id},
            ))

        # FactEngine Extraction
        try:
            num_facts = fact_engine.extract_facts_from_text(
                text=chunk.plain_text,
                document_id=doc_id,
                university=institution_name,
                page_number=chunk.primary_page,
                section_id=f"sec_{doc_id}_{chunk.primary_page}",
            )
            uni_id = f"uni_{re.sub(r'[^a-zA-Z0-9]', '_', institution_name.lower())[:30]}"
            for nf in num_facts:
                f_id = nf.fact_id
                f_name = f"{nf.metric_name.replace('_', ' ').title()}: {nf.raw_value}"
                all_entities.append(AcademicEntity(
                    entity_id=f_id,
                    label="MetricFact",
                    name=f_name,
                    properties=nf.to_dict(),
                    provenance={"pdf_filename": pdf_path.name, "page_number": chunk.primary_page, "chunk_id": chunk.chunk_id},
                ))
                all_relations.append(AcademicRelation(
                    relation_id=f"rel_{chunk.chunk_id}_{f_id}_reports",
                    source_id=chunk.chunk_id,
                    source_label="Chunk",
                    relation_type="HAS_FACT",
                    target_id=f_id,
                    target_label="MetricFact",
                    provenance={"pdf_filename": pdf_path.name, "page_number": chunk.primary_page, "chunk_id": chunk.chunk_id},
                ))
                all_relations.append(AcademicRelation(
                    relation_id=f"rel_{uni_id}_{f_id}_reported_metric",
                    source_id=uni_id,
                    source_label="University",
                    relation_type="REPORTED_METRIC",
                    target_id=f_id,
                    target_label="MetricFact",
                    provenance={"pdf_filename": pdf_path.name, "page_number": chunk.primary_page, "chunk_id": chunk.chunk_id},
                ))
        except Exception:
            pass

    t_kg = time.perf_counter() - t2

    # Deduplicate Entities and Relations
    unique_entities: Dict[str, AcademicEntity] = {e.entity_id: e for e in all_entities}
    unique_relations: Dict[str, AcademicRelation] = {r.relation_id: r for r in all_relations}

    kg_entity_labels = Counter(e.label for e in unique_entities.values())
    kg_relation_types = Counter(r.relation_type for r in unique_relations.values())

    # 5. Persist Processed Artifacts to Disk
    if save_artifacts:
        out_dir = output_dir or (RAG_DIR / "data" / "processed")
        chunks_dir = out_dir / "chunks"
        triples_dir = out_dir / "graph_triples"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        triples_dir.mkdir(parents=True, exist_ok=True)

        print("\n[Phase 5/6] Persisting Chunks & Knowledge Graph Triples to Disk...")
        # Save child/legacy chunks
        (chunks_dir / f"{doc_id}_chunks.json").write_text(
            json.dumps(legacy_chunks, indent=2), encoding="utf-8"
        )
        # Save parent chunks
        (chunks_dir / f"{doc_id}_parent_chunks.json").write_text(
            json.dumps([p.to_dict() for p in parent_chunks], indent=2), encoding="utf-8"
        )
        # Save diagnostics
        (chunks_dir / f"{doc_id}_chunking_diagnostics.json").write_text(
            json.dumps(diag_report.to_dict(), indent=2), encoding="utf-8"
        )
        # Save propositions
        (chunks_dir / f"{doc_id}_propositions.json").write_text(
            json.dumps([p.to_dict() for p in propositions], indent=2), encoding="utf-8"
        )
        # Save evidence bundles
        evidence_bundles = result.get("evidence_bundles", [])
        (chunks_dir / f"{doc_id}_evidence_bundles.json").write_text(
            json.dumps([b.to_dict() for b in evidence_bundles], indent=2), encoding="utf-8"
        )
        # Save graph triples
        (triples_dir / f"{doc_id}_triples.json").write_text(
            json.dumps({
                "document_id": doc_id,
                "pdf_filename": pdf_path.name,
                "node_count": len(unique_entities),
                "edge_count": len(unique_relations),
                "entities": [e.to_dict() for e in unique_entities.values()],
                "relations": [r.to_dict() for r in unique_relations.values()],
            }, indent=2), encoding="utf-8"
        )
        print(f"  -> Saved chunks, parents, propositions, evidence bundles & triples to: {out_dir}")

    t_total = time.perf_counter() - t_total_start

    # 6. Quantitative Dashboard Report
    print("\n" + "=" * 80)
    print(" 📊 ADVANCED GGAHC FULL-DOCUMENT TELEMETRY & AUDIT REPORT")
    print("=" * 80)
    print(f" Document Processed               : {pdf_path.name}")
    print(f" Total Document Pages             : {total_pages}")
    print(f" Total Execution Time             : {t_total:.2f} seconds")
    print(f"   ├─ Docling / Layout Parsing    : {t_parse:.2f}s ({t_parse / t_total * 100:.1f}%)")
    print(f"   ├─ GGAHC Adaptive Chunking     : {t_chunking:.3f}s ({t_chunking / t_total * 100:.1f}%)")
    print(f"   └─ KG Triples & Fact Mapping   : {t_kg:.2f}s ({t_kg / t_total * 100:.1f}%)")
    print("-" * 80)

    print(" 🧱 HIERARCHICAL CHUNKING & EVIDENCE SUMMARY:")
    print(f"   • Total Parent Chunks Created  : {len(parent_chunks)}")
    print(f"     └─ Avg Tokens / Parent Chunk : {avg_parent_tokens:.1f} (min: {min(parent_token_lengths or [0])}, max: {max(parent_token_lengths or [0])})")
    print(f"   • Total Child Chunks Created   : {len(child_chunks)}")
    print(f"     ├─ Text Chunks               : {len(text_children)}")
    print(f"     ├─ Table Chunks (Discrete)   : {len(table_children)}")
    print(f"     └─ Avg Tokens / Child Chunk  : {avg_child_tokens:.1f} (min: {min(child_token_lengths or [0])}, max: {max(child_token_lengths or [0])})")
    print(f"   • Total Evidence Bundles       : {len(result.get('evidence_bundles', []))}")
    print(f"   • Total Atomic Propositions    : {len(propositions)}")
    print(f"     └─ Avg Words / Proposition   : {avg_prop_tokens:.1f}")
    print("-" * 80)

    print(" 🛡️ DETERMINISTIC AUDIT LEDGER & HARD CONSTRAINTS:")
    hard_triggers = getattr(diag_report, "hard_constraints_triggered", {}) or {}
    print(f"   • Hard Constraints Fired       : {sum(hard_triggers.values())}")
    for hc_name, hc_count in hard_triggers.items():
        print(f"     ├─ {hc_name:<28}: {hc_count:>4}")
    print(f"   • Total Boundaries Evaluated   : {len(boundaries)}")
    print(f"   • Merge Operations             : {getattr(diag_report, 'merge_operations', 0)}")
    print(f"   • Split Operations             : {getattr(diag_report, 'split_operations', 0)}")
    print(f"   • Preserve Operations          : {getattr(diag_report, 'preserve_operations', 0)}")
    print(f"   • Avg Boundary Confidence      : {getattr(diag_report, 'average_boundary_confidence', 0.0):.2f}")
    if decision_counts:
        for dec, count in decision_counts.most_common():
            pct = (count / max(len(boundaries), 1)) * 100
            print(f"     ├─ {dec:<24}: {count:>4} ({pct:.1f}%)")
    print("-" * 80)

    print(" 📡 SIGNAL AVAILABILITY MATRIX (Zero Fabricated Metrics):")
    avail_rates = getattr(diag_report, "signal_availability_rates", {}) or {}
    if avail_rates:
        for sig_name, rate in avail_rates.items():
            status = "ACTIVE" if rate > 0.5 else ("SPARSE" if rate > 0 else "UNAVAILABLE")
            bar = "█" * int(rate * 15) + "░" * (15 - int(rate * 15))
            print(f"   • {sig_name:<26}: [{bar}] {rate * 100:>5.1f}% ({status})")
    else:
        print("   • Hard-gated decisions; soft signal matrix was bypassed.")
    print("-" * 80)

    print(" 🕸️ IN-CHUNKING LOCAL GRAPH FEATURES:")
    print(f"   • Input Structural Units       : {getattr(diag_report, 'structural_units_count', 0)}")
    print(f"   • Semantic Candidate Units     : {getattr(diag_report, 'candidate_semantic_units_count', 0)}")
    print(f"   • Extracted Candidate Entities : {total_cand_entities}")
    print(f"   • Extracted Candidate Relations: {total_cand_relations}")
    print(f"   • LPA Communities Detected     : {getattr(diag_report, 'communities_count', 'N/A')}")
    print("-" * 80)

    print(" 🌐 FULL INSTITUTIONAL KNOWLEDGE GRAPH TRIPLE METRICS:")
    print(f"   • Total Unique Graph Entities  : {len(unique_entities)}")
    print(f"   • Total Unique Relationships   : {len(unique_relations)}")
    print("   • Entity Breakdown by Label:")
    for label, count in kg_entity_labels.most_common(12):
        print(f"     ├─ {label:<22}: {count:>5}")
    print("   • Relationship Breakdown by Type:")
    for rtype, count in kg_relation_types.most_common(12):
        print(f"     ├─ {rtype:<22}: {count:>5}")
    print("=" * 80)

    return {
        "pdf_filename": pdf_path.name,
        "total_pages": total_pages,
        "total_parent_chunks": len(parent_chunks),
        "total_child_chunks": len(child_chunks),
        "total_propositions": len(propositions),
        "total_entities": len(unique_entities),
        "total_relationships": len(unique_relations),
        "parent_token_lengths": parent_token_lengths,
        "child_token_lengths": child_token_lengths,
        "decision_counts": dict(decision_counts),
        "entity_labels": dict(kg_entity_labels),
        "relation_types": dict(kg_relation_types),
        "timing": {
            "total_seconds": round(t_total, 3),
            "parse_seconds": round(t_parse, 3),
            "chunking_seconds": round(t_chunking, 3),
            "kg_seconds": round(t_kg, 3),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run GGAHC on full PDF")
    parser.add_argument(
        "--pdf",
        type=str,
        default="RAG/tests/Test pdf/IITMRP Annual Report.pdf",
        help="Path to PDF file",
    )
    parser.add_argument(
        "--engine",
        type=str,
        default="auto",
        choices=["auto", "docling", "quick"],
        help="Document parser engine: 'auto', 'docling', or 'quick'",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not persist chunk files to disk",
    )
    args = parser.parse_args()

    pdf_file = Path(args.pdf)
    if not pdf_file.exists():
        print(f"❌ ERROR: File not found: {pdf_file}")
        sys.exit(1)

    run_full_pdf_ggahc(
        pdf_path=pdf_file,
        engine=args.engine,
        save_artifacts=not args.no_save,
    )


if __name__ == "__main__":
    main()
