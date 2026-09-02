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

# Enforce 100% Pure Offline Local Execution (Zero External / Hub Requests)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.academic_extractor import AcademicDomainExtractor, AcademicEntity, AcademicRelation
from src.neo4j_engine import Neo4jDatabase
from src.vector_engine import LocalVectorEngine
from src.parsers.document_parser import SmartDocumentParser


class AcademicPipelineIngestor:
    """
    End-to-end academic report processing and Neo4j graph population.
    """

    def __init__(
        self,
        download_dir: Optional[Path | str] = None,
        processed_dir: Optional[Path | str] = None,
    ):
        self.download_dir = Path(download_dir or Path(__file__).parent.parent / "data" / "documents").resolve()
        self.output_dir = Path(processed_dir or Path(__file__).parent.parent / "data" / "processed").resolve()
        
        # Create output directories
        (self.output_dir / "chunks").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "facts").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "graph_triples").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "neo4j").mkdir(parents=True, exist_ok=True)

        self.extractor = AcademicDomainExtractor()
        self.neo4j_db = Neo4jDatabase()
        self.vector_engine = LocalVectorEngine()
        self.smart_parser = SmartDocumentParser()

    def identify_institution(self, pdf_path: Path, first_page_text: str) -> Tuple[str, str]:
        """Determine canonical institution name and academic/reporting year."""
        combined_text = (pdf_path.name + " " + first_page_text[:1000]).lower()

        if "iit madras research park" in combined_text or "iitmrp" in combined_text:
            uni = "IIT Madras Research Park (IITMRP)"
        elif "indian institute of technology madras" in combined_text or "iit madras" in combined_text:
            uni = "Indian Institute of Technology Madras (IIT Madras)"
        elif "biotechnology research and innovation council" in combined_text or "bric" in combined_text:
            uni = "Biotechnology Research and Innovation Council (BRIC)"
        elif "national institute of plant genome research" in combined_text or "nipgr" in combined_text:
            uni = "National Institute of Plant Genome Research (NIPGR)"
        elif "astrabio" in combined_text or "taxonomy" in combined_text:
            uni = "AstraBio Innovations Council"
        elif "panjab university" in combined_text or "pu" in combined_text:
            uni = "Panjab University"
        elif "delhi university" in combined_text or "du" in combined_text:
            uni = "Delhi University"
        else:
            uni = pdf_path.stem.replace("_", " ").replace("-", " ").title()

        # Year detection
        year_match = re.search(r"(20[12][0-9](?:[-–][0-9]{2,4})?)", combined_text)
        year = year_match.group(1) if year_match else "2024-25"

        return uni, year

    def process_pdf(self, pdf_path: Path, max_pages: int = 25) -> Dict[str, Any]:
        """
        Process a single academic PDF into chunks, entities, and Neo4j nodes.
        """
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
        pages_to_process = min(total_doc_pages, max_pages)

        first_p_txt = doc[0].get_text("text") if total_doc_pages > 0 else ""
        institution_name, reporting_period = self.identify_institution(pdf_path, first_p_txt)

        print(f"\n======================================================================")
        print(f" [INGESTING] {pdf_path.name}")
        print(f"   Institution: {institution_name} | Period: {reporting_period}")
        print(f"   Pages: Processing first {pages_to_process} of {total_doc_pages} pages")
        print(f"======================================================================")

        all_chunks: List[Dict[str, Any]] = []
        all_entities: List[AcademicEntity] = []
        all_relations: List[AcademicRelation] = []

        t0 = time.time()

        parsed_sections = self.smart_parser.parse_pdf(pdf_path, max_pages=pages_to_process)
        doc.close()

        for sec in parsed_sections:
            pno = sec["page_number"]
            raw_text = sec["text"]
            heading = sec["heading"]

            cleaned_text = self.extractor.clean_text(raw_text)
            chunk_id = f"{doc_id}_p{pno:03d}"

            # Contextual Prefix Enrichment
            context_prefix = (
                f"Institution: {institution_name}\n"
                f"Document: {pdf_path.name}\n"
                f"Period: {reporting_period}\n"
                f"Page: {pno}\n"
                f"Heading: {heading}"
            )
            enriched_text = f"{context_prefix}\n\nContent:\n{cleaned_text}"

            chunk_record = {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "pdf_filename": pdf_path.name,
                "university": institution_name,
                "reporting_period": reporting_period,
                "heading": heading,
                "primary_page": pno,
                "source_pages": [pno],
                "plain_text": cleaned_text,
                "enriched_text": enriched_text,
                "token_estimate": len(cleaned_text.split()),
                "recommended_task": "academic_research",
            }
            all_chunks.append(chunk_record)

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

        print(f"   [OK] Ingested in {elapsed}s:")
        print(f"        -> {len(all_chunks)} Context Chunks (ChromaDB: {vector_count})")
        print(f"        -> {len(unique_entities)} Academic Entities")
        print(f"        -> {len(unique_relations)} Academic Relationships")
        print(f"        -> Neo4j Live Sync: {neo4j_res.get('synced', False)} ({neo4j_res.get('nodes_written', 0)} nodes)")

        return {
            "document": pdf_path.name,
            "institution": institution_name,
            "period": reporting_period,
            "pages_processed": pages_to_process,
            "total_pages": total_doc_pages,
            "chunks_count": len(all_chunks),
            "entities_count": len(unique_entities),
            "relations_count": len(unique_relations),
            "neo4j_synced": neo4j_res.get("synced", False),
        }

    def process_all_downloads(self, max_pages_per_doc: int = 25) -> Dict[str, Any]:
        """
        Process every PDF report in the Download folder into the live Neo4j database.
        """
        pdfs = sorted(list(self.download_dir.glob("*.pdf")))
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
            res = self.process_pdf(pdf, max_pages=max_pages_per_doc)
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
