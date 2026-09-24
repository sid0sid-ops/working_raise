"""
RAISE Master Academic Ingestion Pipeline
Processes all university and academic PDFs from Download/ (READ-ONLY).
Builds structure-aware chunks, extracts academic entities/relationships, populates Neo4j and ChromaDB.
Stores structured JSON artifacts in RAG/data/processed/.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

# Auto-load .env variables if not already loaded
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
    else:
        load_dotenv()
except Exception:
    pass

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_VERBOSITY"] = "error"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from .academic_extractor import AcademicDomainExtractor, AcademicEntity, AcademicRelation
from src.infrastructure.graph.neo4j import Neo4jDatabase
from src.infrastructure.vector.chroma import LocalVectorEngine
from src.parsers.document_parser import SmartDocumentParser
from src.features.verification.fact_engine import FactEngine
from src.chunking.pipeline import AdaptiveChunkingPipeline
from src.chunking.config import ChunkingConfig
from src.infrastructure.database.postgres import PostgresManager



def should_ingest(file_path: str | Path) -> bool:
    """
    Enforces strict database isolation to prevent benchmark data contamination.
    Excludes test suites, evaluation materials, benchmark QA files, and question suites.
    """
    path_str = str(file_path).lower().replace("\\", "/")
    excluded_patterns = [
        "evaluation",
        "benchmark",
        "question_suite",
        "question suite",
        "raise-bench",
        "gemini-notebook",
        "benchmark_qa"
    ]
    return not any(pattern in path_str for pattern in excluded_patterns)


class CrossDatabaseConsistencyAuditor:
    """
    Audits cross-substrate data integrity between:
      1. Chunks created in ingestion pipeline
      2. Vectors persisted in ChromaDB
      3. Entities and relationships populated in Neo4j / NetworkX
    """
    @staticmethod
    def audit_ingestion(
        doc_id: str,
        expected_chunks: int,
        vector_count: int,
        entities_count: int,
        relations_count: int,
        neo4j_synced: bool = False,
        neo4j_nodes: int = 0
    ) -> Dict[str, Any]:
        discrepancies = []
        if vector_count < expected_chunks:
            discrepancies.append(
                f"ChromaDB vector count mismatch: stored {vector_count} vs {expected_chunks} expected chunks."
            )
        if entities_count == 0 and expected_chunks > 0:
            discrepancies.append("Zero academic entities extracted for populated document.")
        if neo4j_synced and neo4j_nodes == 0 and entities_count > 0:
            discrepancies.append(
                f"Neo4j live sync reported success but 0 nodes were verified in graph."
            )
        
        is_consistent = len(discrepancies) == 0
        return {
            "doc_id": doc_id,
            "is_consistent": is_consistent,
            "expected_chunks": expected_chunks,
            "vector_count": vector_count,
            "entities_count": entities_count,
            "relations_count": relations_count,
            "neo4j_nodes": neo4j_nodes,
            "discrepancies": discrepancies,
        }


class AcademicPipelineIngestor:
    """
    End-to-end academic report processing and Neo4j graph population.
    """

    def __init__(
        self,
        download_dir: Optional[Path | str] = None,
        processed_dir: Optional[Path | str] = None,
    ):
        base_rag_dir = Path(__file__).resolve().parents[3]
        self.download_dir = Path(download_dir or base_rag_dir / "data" / "documents").resolve()
        self.output_dir = Path(processed_dir or base_rag_dir / "data" / "processed").resolve()
        
        # Create output directories
        (self.output_dir / "chunks").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "facts").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "graph_triples").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "neo4j").mkdir(parents=True, exist_ok=True)

        self.extractor = AcademicDomainExtractor()
        self.fact_engine = FactEngine()
        self.neo4j_db = Neo4jDatabase()
        self.vector_engine = LocalVectorEngine()
        self.smart_parser = SmartDocumentParser()
        self.adaptive_chunker = AdaptiveChunkingPipeline()
        self.postgres = PostgresManager()

    def close(self):
        """Cleanly releases underlying database connections."""
        if hasattr(self, "neo4j_db") and self.neo4j_db is not None:
            try:
                self.neo4j_db.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def identify_institution(self, pdf_path: Path, first_page_text: str) -> Tuple[str, str]:
        """Determine canonical institution name and academic/reporting year."""
        combined_text = (pdf_path.name + " " + first_page_text[:1000]).lower()

        if re.search(r"\b(iit madras research park|iitmrp)\b", combined_text):
            uni = "IIT Madras Research Park (IITMRP)"
        elif re.search(r"\b(indian institute of technology madras|iit madras|iitm)\b", combined_text):
            uni = "Indian Institute of Technology Madras (IIT Madras)"
        elif re.search(r"\b(biotechnology research and innovation council|bric)\b", combined_text):
            uni = "Biotechnology Research and Innovation Council (BRIC)"
        elif re.search(r"\b(national institute of plant genome research|nipgr)\b", combined_text):
            uni = "National Institute of Plant Genome Research (NIPGR)"
        elif re.search(r"\b(astrabio innovations council|astrabio)\b", combined_text):
            uni = "AstraBio Innovations Council"
        elif re.search(r"\b(panjab university|\(pu\))\b", combined_text):
            uni = "Panjab University"
        elif re.search(r"\b(delhi university|university of delhi|\(du\))\b", combined_text):
            uni = "Delhi University"
        elif re.search(r"\b(national stock exchange|nse)\b", combined_text):
            uni = "National Stock Exchange of India (NSE)"
        else:
            uni = pdf_path.stem.replace("_", " ").replace("-", " ").title()

        # Year detection
        year_match = re.search(r"(20[12][0-9](?:[-–][0-9]{2,4})?)", combined_text)
        year = year_match.group(1) if year_match else "2024-25"

        return uni, year

    def process_pdf(
        self,
        pdf_path: Path | str,
        max_pages: Optional[int] = None,
        engine: str = "fast",
        full_potential: bool = False,
        extract_tables: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a single academic PDF into chunks, entities, and Neo4j nodes.
        - engine: 'fast' (PyMuPDF, 2-3s) | 'deep' | 'docling' (Docling TableFormer) | 'auto'
        Allows processing without arbitrary max caps when max_pages is None.
        """
        pdf_path = Path(pdf_path)
        if not should_ingest(pdf_path):
            print(f"⛔ [Isolation Guard] Skipping excluded evaluation/benchmark file: {pdf_path.name}")
            return {
                "document": pdf_path.name,
                "status": "excluded",
                "reason": "File matches excluded evaluation/benchmark patterns",
                "pages_processed": 0,
                "chunks_count": 0,
                "entities_count": 0,
                "relations_count": 0,
                "facts_count": 0,
            }

        doc_id = re.sub(r"[^a-zA-Z0-9]", "_", pdf_path.stem)[:40]
        chunk_file = self.output_dir / "chunks" / f"{doc_id}_chunks.json"
        triple_file = self.output_dir / "graph_triples" / f"{doc_id}_triples.json"

        # If PDF is 0 bytes but cached chunks exist, load from disk cache
        if pdf_path.stat().st_size == 0:
            if chunk_file.exists():
                try:
                    all_chunks = json.loads(chunk_file.read_text(encoding="utf-8"))
                    triples_data = json.loads(triple_file.read_text(encoding="utf-8")) if triple_file.exists() else {"entities": [], "relations": []}
                    
                    # Sync to ChromaDB
                    vector_count = self.vector_engine.ingest_chunks(all_chunks, doc_id=doc_id)
                    
                    # Sync to Neo4j
                    gdata = {
                        "nodes": [{"id": e["entity_id"], "label": e["name"], "type": e["label"], "page": e.get("provenance", {}).get("page_number", 1), "document_id": doc_id} for e in triples_data.get("entities", [])],
                        "edges": [{"source": r["source_id"], "target": r["target_id"], "type": r["relation_type"]} for r in triples_data.get("relations", [])],
                    }
                    self.neo4j_db.sync_graph_data(gdata)

                    return {
                        "document": pdf_path.name,
                        "institution": pdf_path.stem.replace("_", " ").title(),
                        "period": "2024-25",
                        "pages_processed": len(all_chunks),
                        "total_pages": len(all_chunks),
                        "chunks_count": len(all_chunks),
                        "entities_count": len(triples_data.get("entities", [])),
                        "relations_count": len(triples_data.get("relations", [])),
                        "neo4j_synced": True,
                    }
                except Exception as e:
                    print(f"Error loading cached chunk {doc_id}: {e}")
            return {
                "document": pdf_path.name,
                "institution": pdf_path.stem.replace("_", " ").title(),
                "period": "2024-25",
                "pages_processed": 0,
                "total_pages": 0,
                "chunks_count": 0,
                "entities_count": 0,
                "relations_count": 0,
                "neo4j_synced": False,
            }

        doc = fitz.open(str(pdf_path))
        total_doc_pages = len(doc)
        if max_pages is not None and int(max_pages) > 0:
            pages_to_process = min(total_doc_pages, int(max_pages))
            page_desc = f"first {pages_to_process} of {total_doc_pages}"
        else:
            pages_to_process = total_doc_pages
            page_desc = f"all {total_doc_pages} pages (no cap)"

        first_p_txt = doc[0].get_text("text") if total_doc_pages > 0 else ""
        institution_name, reporting_period = self.identify_institution(pdf_path, first_p_txt)

        print(f"\n======================================================================")
        print(f" [INGESTING] {pdf_path.name}")
        print(f"   Institution: {institution_name} | Period: {reporting_period}")
        print(f"   Pages: Processing {page_desc} (Engine: {engine.upper()})")
        print(f"======================================================================")

        all_chunks: List[Dict[str, Any]] = []
        all_entities: List[AcademicEntity] = []
        all_relations: List[AcademicRelation] = []

        t0 = time.time()

        parsed_sections = self.smart_parser.parse_pdf(
            pdf_path,
            max_pages=pages_to_process,
            engine=engine,
            full_potential=full_potential,
            extract_tables=extract_tables,
        )
        doc.close()

        # Run Graph-Guided Adaptive Hierarchical Chunking (GGAHC)
        adaptive_result = self.adaptive_chunker.process_document(
            parsed_sections=parsed_sections,
            document_id=doc_id,
            filename=pdf_path.name,
            university=institution_name,
            reporting_period=reporting_period,
            total_pages=total_doc_pages,
        )
        child_chunks = adaptive_result["child_chunks"]
        parent_chunks = adaptive_result["parent_chunks"]
        all_chunks = adaptive_result["legacy_chunks"]

        # Save Parent Chunks and Diagnostic Report for inspection
        (self.output_dir / "chunks" / f"{doc_id}_parent_chunks.json").write_text(
            json.dumps([p.to_dict() for p in parent_chunks], indent=2), encoding="utf-8"
        )
        (self.output_dir / "chunks" / f"{doc_id}_chunking_diagnostics.json").write_text(
            json.dumps(adaptive_result["diagnostic_report"].to_dict(), indent=2), encoding="utf-8"
        )

        for chunk_record in all_chunks:
            pno = chunk_record.get("primary_page", 1)
            doc_pno = chunk_record.get("printed_page")
            cleaned_text = chunk_record.get("plain_text", "")
            heading = chunk_record.get("heading", "")
            chunk_id = chunk_record["chunk_id"]

            # Register Chunk entity in Knowledge Graph for Dynamic Neighborhood Cypher Traversal
            chunk_ent = AcademicEntity(
                entity_id=chunk_id,
                label="Chunk",
                name=f"Chunk {chunk_id}",
                properties={
                    "document_id": doc_id,
                    "primary_page": pno,
                    "printed_page": doc_pno,
                    "heading": heading,
                    "pdf_filename": pdf_path.name,
                    "parent_chunk_id": chunk_record.get("parent_chunk_id"),
                },
                provenance={"pdf_filename": pdf_path.name, "page_number": pno, "printed_page": doc_pno, "chunk_id": chunk_id},
            )
            all_entities.append(chunk_ent)

            # Extract Academic Entities & Relations
            ents, rels = self.extractor.extract_academic_knowledge(
                text=cleaned_text,
                pdf_filename=pdf_path.name,
                page_number=pno,
                section_heading=heading,
                chunk_id=chunk_id,
                university_name=institution_name,
            )
            all_entities.extend(ents)
            all_relations.extend(rels)

            # Link Chunk to extracted Academic Entities
            for e in ents:
                all_relations.append(AcademicRelation(
                    relation_id=f"rel_{chunk_id}_{e.entity_id}_mentions",
                    source_id=chunk_id,
                    source_label="Chunk",
                    relation_type="MENTIONS",
                    target_id=e.entity_id,
                    target_label=e.label,
                    provenance={"pdf_filename": pdf_path.name, "page_number": pno, "chunk_id": chunk_id},
                ))

            # Extract Quantitative Facts via FactEngine
            try:
                num_facts = self.fact_engine.extract_facts_from_text(
                    text=cleaned_text,
                    document_id=doc_id,
                    university=institution_name,
                    page_number=pno,
                    section_id=f"sec_{doc_id}_{pno}",
                )
                uni_id = f"uni_{re.sub(r'[^a-zA-Z0-9]', '_', institution_name.lower())[:30]}"
                for nf in num_facts:
                    f_id = nf.fact_id
                    f_name = f"{nf.metric_name.replace('_', ' ').title()}: {nf.raw_value}"
                    f_ent = AcademicEntity(
                        entity_id=f_id,
                        label="MetricFact",
                        name=f_name,
                        properties=nf.to_dict(),
                        provenance={"pdf_filename": pdf_path.name, "page_number": pno, "printed_page": doc_pno, "chunk_id": chunk_id},
                    )
                    all_entities.append(f_ent)
                    all_relations.append(AcademicRelation(
                        relation_id=f"rel_{chunk_id}_{f_id}_reports",
                        source_id=chunk_id,
                        source_label="Chunk",
                        relation_type="HAS_FACT",
                        target_id=f_id,
                        target_label="MetricFact",
                        provenance={"pdf_filename": pdf_path.name, "page_number": pno, "printed_page": doc_pno, "chunk_id": chunk_id},
                    ))
                    all_relations.append(AcademicRelation(
                        relation_id=f"rel_{uni_id}_{f_id}_reported_metric",
                        source_id=uni_id,
                        source_label="University",
                        relation_type="REPORTED_METRIC",
                        target_id=f_id,
                        target_label="MetricFact",
                        provenance={"pdf_filename": pdf_path.name, "page_number": pno, "printed_page": doc_pno, "chunk_id": chunk_id},
                    ))
            except Exception:
                pass

        # Deduplicate Entities by ID
        unique_entities: Dict[str, AcademicEntity] = {}
        for e in all_entities:
            unique_entities[e.entity_id] = e

        # Deduplicate Relations by ID
        unique_relations: Dict[str, AcademicRelation] = {}
        for r in all_relations:
            unique_relations[r.relation_id] = r

        # Save Processed Artifacts to disk
        (self.output_dir / "chunks" / f"{doc_id}_chunks.json").write_text(
            json.dumps(all_chunks, indent=2), encoding="utf-8"
        )
        (self.output_dir / "graph_triples" / f"{doc_id}_triples.json").write_text(
            json.dumps({
                "entities": [e.to_dict() for e in unique_entities.values()],
                "relations": [r.to_dict() for r in unique_relations.values()],
            }, indent=2), encoding="utf-8"
        )


        # Ingest to ChromaDB Vector Store
        vector_count = self.vector_engine.ingest_chunks(all_chunks, doc_id=doc_id)

        # Ingest to Neo4j Property Knowledge Graph
        gdata = {
            "nodes": [
                {
                    "id": e.entity_id,
                    "label": e.name,
                    "type": e.label,
                    "properties": e.properties,
                    "provenance": e.provenance,
                }
                for e in unique_entities.values()
            ],
            "edges": [
                {
                    "source": r.source_id,
                    "target": r.target_id,
                    "type": r.relation_type,
                    "properties": r.properties,
                }
                for r in unique_relations.values()
            ],
            "node_count": len(unique_entities),
            "edge_count": len(unique_relations),
        }

        neo4j_res = self.neo4j_db.sync_graph_data(gdata)
        elapsed = round(time.time() - t0, 2)
        facts_count = len([e for e in unique_entities.values() if e.label == "MetricFact"])

        # Ingest to PostgreSQL
        pg_synced = False
        try:
            self.postgres.save_document(
                doc_id=doc_id,
                filename=pdf_path.name,
                chunks_count=len(all_chunks),
                library="default"
            )
            self.postgres.upsert_document_status(
                doc_id=doc_id,
                filename=pdf_path.name,
                phase="ready",
                percent=100,
                status="ready",
                detail=f"Ingested {len(all_chunks)} chunks, {len(unique_entities)} entities",
                library="default"
            )
            pg_synced = True
        except Exception as e:
            print(f"        -> PostgreSQL Sync Notice: {e}")

        print(f"   [OK] Ingested in {elapsed}s:")
        print(f"        -> {len(all_chunks)} Context Chunks (ChromaDB: {vector_count})")
        print(f"        -> {len(unique_entities)} Academic Entities")
        print(f"        -> {len(unique_relations)} Academic Relationships")
        print(f"        -> {facts_count} Verified Metric Facts")
        print(f"        -> Neo4j Live Sync: {neo4j_res.get('synced', False)} ({neo4j_res.get('nodes_written', 0)} nodes)")
        print(f"        -> PostgreSQL Sync: {pg_synced}")

        consistency_audit = CrossDatabaseConsistencyAuditor.audit_ingestion(
            doc_id=doc_id,
            expected_chunks=len(all_chunks),
            vector_count=vector_count,
            entities_count=len(unique_entities),
            relations_count=len(unique_relations),
            neo4j_synced=neo4j_res.get("synced", False),
            neo4j_nodes=neo4j_res.get("nodes_written", 0),
        )

        # Update persistent manifest
        try:
            manifest_file = self.output_dir / "ingested_manifest.json"
            manifest = {"ready_documents": [], "deleted_documents": []}
            if manifest_file.exists():
                try:
                    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                except Exception:
                    manifest = {"ready_documents": [], "deleted_documents": []}
            manifest["deleted_documents"] = [f for f in manifest.get("deleted_documents", []) if f != pdf_path.name]
            docs = manifest.get("ready_documents", [])
            size_mb = round(pdf_path.stat().st_size / (1024 * 1024), 2) if pdf_path.exists() else 0.0
            updated = False
            for d in docs:
                if d.get("filename") == pdf_path.name:
                    d["pages"] = pages_to_process
                    d["size_mb"] = size_mb
                    d["chunks_count"] = len(all_chunks)
                    d["status"] = "ready"
                    updated = True
                    break
            if not updated:
                docs.append({
                    "filename": pdf_path.name,
                    "pages": pages_to_process,
                    "size_mb": size_mb,
                    "chunks_count": len(all_chunks),
                    "status": "ready"
                })
            manifest["ready_documents"] = docs
            manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Manifest update notice: {e}")

        return {
            "document": pdf_path.name,
            "institution": institution_name,
            "period": reporting_period,
            "pages_processed": pages_to_process,
            "total_pages": total_doc_pages,
            "chunks_count": len(all_chunks),
            "entities_count": len(unique_entities),
            "relations_count": len(unique_relations),
            "facts_extracted": facts_count,
            "triples_extracted": len(unique_relations),
            "entities": [e.to_dict() for e in unique_entities.values()],
            "relationships": [r.to_dict() for r in unique_relations.values()],
            "facts": [e.to_dict() for e in unique_entities.values()],
            "triples": [r.to_dict() for r in unique_relations.values()],
            "neo4j_synced": neo4j_res.get("synced", False),
            "consistency_audit": consistency_audit,
        }

    def process_all_downloads(self, max_pages_per_doc: Optional[int] = None, engine: str = "fast") -> Dict[str, Any]:
        """
        Process every PDF report in the Download folder into the live Neo4j database.
        """
        pdfs = sorted([p for p in self.download_dir.glob("*.pdf") if should_ingest(p)])
        print(f"\n======================================================================")
        print(f" 🚀 STARTING FULL ACADEMIC GRAPHRAG INGESTION ({len(pdfs)} PDFS)")
        print(f" Source: {self.download_dir}")
        print(f" Target: Neo4j (bolt://localhost:7687) & ChromaDB")
        print(f"======================================================================")

        results = []
        tot_chunks = 0
        tot_entities = 0
        tot_relations = 0

        for pdf in pdfs:
            res = self.process_pdf(pdf, max_pages=max_pages_per_doc, engine=engine)
            results.append(res)
            tot_chunks += res["chunks_count"]
            tot_entities += res["entities_count"]
            tot_relations += res["relations_count"]

        # Global summary
        print(f"\n======================================================================")
        print(f" 📊 [ACADEMIC INGESTION COMPLETED SUCCESSFULLY]")
        print(f" Total PDF Documents Ingested: {len(results)}")
        print(f" Total Semantic Context Chunks: {tot_chunks}")
        print(f" Total Academic Entities in Neo4j: {tot_entities}")
        print(f" Total Academic Relationships in Neo4j: {tot_relations}")
        print(f" Artifacts Stored in: {self.output_dir}")
        print(f"======================================================================\n")

        return {
            "status": "success",
            "total_documents": len(results),
            "total_chunks": tot_chunks,
            "total_entities": tot_entities,
            "total_relations": tot_relations,
            "documents": results,
        }


if __name__ == "__main__":
    pipeline = AcademicPipelineIngestor()
    pipeline.process_all_downloads(max_pages_per_doc=25)
