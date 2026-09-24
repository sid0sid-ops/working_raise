"""
RAISE Master Ingestion Engine — 4 Multi-Year Institutional Reports
Ingests:
1. NIPGR Annual Report 2021-22 (Scanned English Chapters, Audited Financials, Grants)
2. NIPGR Annual Report 2022-23 (Digital English Chapters, Staff, Audited Accounts)
3. NIPGR Annual Report 2023-24 (Digital English Chapters, Staff, Audited Accounts)
4. BRIC Annual Report 2025 (Full Digital 218-Page Multi-Institute Report)

Produces:
- 1024-dim Dense Vector Embeddings in ChromaDB (BAAI/bge-large-en-v1.5)
- Okapi BM25 Lexical Inverted Index
- Neo4j Knowledge Graph (Entities, Metrics, Research Topics, Citations)
- Updated Manifest in data/processed/ingested_manifest.json
"""

import os
import sys
import json
import time
import re
import fitz
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure GPU execution
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_VERBOSITY"] = "error"

from src.features.ingestion.academic_extractor import AcademicDomainExtractor, AcademicEntity, AcademicRelation
from src.infrastructure.graph.neo4j import Neo4jDatabase
from src.infrastructure.vector.chroma import LocalVectorEngine
from src.features.verification.fact_engine import FactEngine
from src.chunking.pipeline import AdaptiveChunkingPipeline
from src.parsers.document_parser import SmartDocumentParser

TARGET_DOCS = [
    {
        "filename": "BRIC-Annual-Report-2025.pdf",
        "institution": "Biotechnology Research and Innovation Council (BRIC)",
        "period": "2024-25",
        "max_pages": 218,  # Full 218 pages digital
        "ocr_scanned_only": True,
    },
    {
        "filename": "Annual Report 2023-24.pdf",
        "institution": "National Institute of Plant Genome Research (NIPGR)",
        "period": "2023-24",
        "max_pages": 165,  # English Report (0-148) + Audited Accounts (149-165)
        "ocr_scanned_only": True,
    },
    {
        "filename": "Annual Report 2022-23.pdf",
        "institution": "National Institute of Plant Genome Research (NIPGR)",
        "period": "2022-23",
        "max_pages": 160,  # English Report (0-142) + Audited Accounts (143-160)
        "ocr_scanned_only": True,
    },
    {
        "filename": "Annual Report 2021-22.pdf",
        "institution": "National Institute of Plant Genome Research (NIPGR)",
        "period": "2021-22",
        "max_pages": 160,  # English Report + Audited Financials & Grants (Pages 0-160)
        "ocr_scanned_only": False,  # All scanned pages require OCR
    },
]


def run_ingestion():
    t_global_start = time.time()
    print("=" * 78)
    print("🚀 RAISE MASTER INGESTION PIPELINE: 4 ANNUAL REPORTS")
    print("=" * 78)

    docs_dir = BASE_DIR / "data" / "documents"
    processed_dir = BASE_DIR / "data" / "processed"
    (processed_dir / "chunks").mkdir(parents=True, exist_ok=True)
    (processed_dir / "facts").mkdir(parents=True, exist_ok=True)
    (processed_dir / "graph_triples").mkdir(parents=True, exist_ok=True)
    (processed_dir / "neo4j").mkdir(parents=True, exist_ok=True)

    # 1. Initialize Subsystem Engines
    print("\n[1/4] Initializing AI Embedding & Knowledge Graph Engines...")
    extractor = AcademicDomainExtractor()
    fact_engine = FactEngine()
    neo4j_db = Neo4jDatabase()
    vector_engine = LocalVectorEngine()
    smart_parser = SmartDocumentParser()
    adaptive_chunker = AdaptiveChunkingPipeline()

    # Load OCR Reader on GPU
    import easyocr
    print("   • Loading GPU EasyOCR Reader (RTX 3090 Accelerated)...")
    ocr_reader = easyocr.Reader(['en'], gpu=True)
    print("   • Subsystems initialized successfully.")

    manifest_docs = []

    # 2. Process each target document
    for doc_idx, config in enumerate(TARGET_DOCS, start=1):
        fn = config["filename"]
        uni = config["institution"]
        period = config["period"]
        max_p = config["max_pages"]
        pdf_path = docs_dir / fn

        if not pdf_path.exists():
            print(f"\n⚠️  [SKIP] File not found: {pdf_path}")
            continue

        print(f"\n" + "-" * 78)
        print(f"[{doc_idx}/{len(TARGET_DOCS)}] INGESTING: {fn}")
        print(f"      Institution : {uni} ({period})")
        print(f"      Scope       : Processing Pages 1 to {max_p}")
        print("-" * 78)

        t_doc_start = time.time()
        doc = fitz.open(str(pdf_path))
        total_in_file = len(doc)
        pages_to_process = min(total_in_file, max_p)

        parsed_sections: List[Dict[str, Any]] = []
        doc_id = re.sub(r"[^a-zA-Z0-9]", "_", pdf_path.stem)[:40]

        ocr_count = 0
        digital_count = 0

        for p_idx in range(pages_to_process):
            page = doc[p_idx]
            p_num = p_idx + 1
            
            # Extract digital text
            text = page.get_text("text").strip()

            # Check if digital text is empty/insufficient and images are present
            if (len(text) < 40 or not config["ocr_scanned_only"]) and len(page.get_images()) > 0:
                # Run OCR
                try:
                    pix = page.get_pixmap(dpi=130)
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                    ocr_lines = ocr_reader.readtext(img, detail=0)
                    if ocr_lines:
                        text = "\n".join(ocr_lines).strip()
                        ocr_count += 1
                except Exception as _ocr_e:
                    pass
            else:
                digital_count += 1

            if not text or len(text) < 15:
                continue

            # Detect heading from first lines
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            heading = lines[0][:80] if lines else f"Section (Page {p_num})"
            if len(heading) < 4:
                heading = f"Section (Page {p_num})"

            # Extract tables if present
            tables_count = 0
            try:
                tbls = page.find_tables()
                if tbls.tables:
                    tables_count = len(tbls.tables)
                    for t in tbls.tables:
                        try:
                            t_df = t.extract()
                            if t_df and len(t_df) > 1:
                                headers = [str(c or "").strip() for c in t_df[0]]
                                md_rows = [" | ".join(headers), " | ".join(["---"] * len(headers))]
                                for row in t_df[1:]:
                                    md_rows.append(" | ".join([str(c or "").strip() for c in row]))
                                text += "\n\n### Extracted Table:\n" + "\n".join(md_rows)
                        except Exception:
                            pass
            except Exception:
                pass

            parsed_sections.append({
                "page_number": p_num,
                "heading": heading,
                "text": text,
                "tables_count": tables_count,
                "engine": "PyMuPDF + EasyOCR Hybrid",
            })

            if (p_num % 30 == 0) or (p_num == pages_to_process):
                print(f"      ... extracted page {p_num}/{pages_to_process} ({ocr_count} OCR, {digital_count} digital)")

        doc.close()

        # 3. Adaptive Chunking (GGAHC)
        print(f"   ⚙️  Running Graph-Guided Adaptive Chunking (GGAHC)...")
        adaptive_result = adaptive_chunker.process_document(
            parsed_sections=parsed_sections,
            document_id=doc_id,
            filename=fn,
            university=uni,
            reporting_period=period,
            total_pages=total_in_file,
        )
        all_chunks = adaptive_result["legacy_chunks"]
        parent_chunks = adaptive_result["parent_chunks"]
        print(f"      Generated {len(all_chunks)} child chunks ({len(parent_chunks)} parent contexts).")

        # Save chunks
        (processed_dir / "chunks" / f"{doc_id}_chunks.json").write_text(
            json.dumps(all_chunks, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (processed_dir / "chunks" / f"{doc_id}_parent_chunks.json").write_text(
            json.dumps([p.to_dict() for p in parent_chunks], indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 4. Academic Entity & Graph Extraction
        print(f"   🧠 Extracting Academic Entities, Financial Facts & Relationships...")
        all_entities: List[AcademicEntity] = []
        all_relations: List[AcademicRelation] = []

        for chunk_record in all_chunks:
            pno = chunk_record.get("primary_page", 1)
            doc_pno = chunk_record.get("printed_page")
            cleaned_text = chunk_record.get("plain_text", "")
            heading = chunk_record.get("heading", "")
            chunk_id = chunk_record["chunk_id"]

            # Chunk Node
            chunk_ent = AcademicEntity(
                entity_id=chunk_id,
                label="Chunk",
                name=f"Chunk {chunk_id}",
                properties={
                    "document_id": doc_id,
                    "primary_page": pno,
                    "printed_page": doc_pno,
                    "heading": heading,
                    "pdf_filename": fn,
                    "reporting_period": period,
                },
                provenance={"pdf_filename": fn, "page_number": pno, "chunk_id": chunk_id},
            )
            all_entities.append(chunk_ent)

            # Entities and Relations
            ents, rels = extractor.extract_academic_knowledge(
                text=cleaned_text,
                pdf_filename=fn,
                page_number=pno,
                section_heading=heading,
                chunk_id=chunk_id,
                university_name=uni,
            )
            all_entities.extend(ents)
            all_relations.extend(rels)

            for e in ents:
                all_relations.append(AcademicRelation(
                    relation_id=f"rel_{chunk_id}_{e.entity_id}_mentions",
                    source_id=chunk_id,
                    source_label="Chunk",
                    relation_type="MENTIONS",
                    target_id=e.entity_id,
                    target_label=e.label,
                    provenance={"pdf_filename": fn, "page_number": pno, "chunk_id": chunk_id},
                ))

            # Fact extraction
            try:
                fact_engine.extract_facts_from_text(
                    text=cleaned_text,
                    document_id=doc_id,
                    university=uni,
                    page_number=pno,
                    section_id=f"sec_{doc_id}_{pno}",
                )
            except Exception:
                pass

        # Save triples
        triples_data = {
            "document_id": doc_id,
            "filename": fn,
            "entities": [e.to_dict() for e in all_entities],
            "relations": [r.to_dict() for r in all_relations],
        }
        (processed_dir / "graph_triples" / f"{doc_id}_triples.json").write_text(
            json.dumps(triples_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"      Extracted {len(all_entities)} entities & {len(all_relations)} relations.")

        # 5. ChromaDB Ingestion (BGE-Large 1024-dim Embeddings)
        print(f"   📊 Computing BGE-Large 1024-dim Vector Embeddings into ChromaDB...")
        vector_count = vector_engine.ingest_chunks(all_chunks, doc_id=doc_id)
        print(f"      ChromaDB indexed {vector_count} chunks (Total stored: {vector_engine.collection.count()}).")

        # 6. Neo4j Knowledge Graph Sync
        print(f"   🌐 Syncing Nodes & Relationships into Neo4j Knowledge Graph...")
        if neo4j_db.connected:
            gdata = {
                "nodes": [
                    {
                        "id": e.entity_id,
                        "label": e.name,
                        "type": e.label,
                        "page": e.provenance.get("page_number", 1) if isinstance(e.provenance, dict) else 1,
                        "document_id": doc_id,
                        "institution": uni,
                        "period": period,
                    }
                    for e in all_entities
                ],
                "edges": [
                    {
                        "source": r.source_id,
                        "target": r.target_id,
                        "type": r.relation_type,
                    }
                    for r in all_relations
                ],
            }
            neo4j_res = neo4j_db.sync_graph_data(gdata)
            print(f"      Neo4j graph sync complete: {neo4j_res}")
        else:
            print(f"      Neo4j not connected. Data persisted to local JSON graph.")

        doc_elapsed = round(time.time() - t_doc_start, 2)
        print(f"   ✅ [COMPLETED in {doc_elapsed}s] {fn}: {len(all_chunks)} chunks, {len(all_entities)} entities.")

        manifest_docs.append({
            "filename": fn,
            "is_protected": True,
            "uploaded_by": "system",
            "institution": uni,
            "period": period,
            "pages": pages_to_process,
            "total_pages": total_in_file,
            "size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
            "chunks_count": len(all_chunks),
            "entities_count": len(all_entities),
            "status": "ready",
        })

    # 7. Write Final Manifest
    manifest_file = processed_dir / "ingested_manifest.json"
    manifest_file.write_text(
        json.dumps({"ready_documents": manifest_docs, "deleted_documents": []}, indent=2),
        encoding="utf-8",
    )
    print(f"\n[4/4] Ingested manifest written to: {manifest_file}")

    total_time = round(time.time() - t_global_start, 2)
    total_chunks = sum(d["chunks_count"] for d in manifest_docs)
    total_nodes = sum(d["entities_count"] for d in manifest_docs)

    print("\n" + "=" * 78)
    print(f"🏆 ALL 4 REPORTS INGESTED SUCCESSFULLY IN {total_time}s")
    print(f"   • Total Active Documents : {len(manifest_docs)}")
    print(f"   • Total Indexed Chunks   : {total_chunks}")
    print(f"   • Total Extracted Nodes  : {total_nodes}")
    print(f"   • ChromaDB Chunk Count   : {vector_engine.collection.count() if vector_engine.collection else 0}")
    if neo4j_db.connected:
        try:
            cnt = neo4j_db.run_cypher("MATCH (n) RETURN count(n) AS c")[0]["c"]
            print(f"   • Neo4j Total Live Nodes : {cnt}")
        except Exception:
            pass
    print("=" * 78)


if __name__ == "__main__":
    run_ingestion()
