"""
RAISE Multi-PDF Batch Ingestion Engine
Auto-discovers and ingests all real university annual reports from the Download/ directory.
Populates Neo4j Knowledge Graph, Structured Fact Store, and ChromaDB Vector Index incrementally.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag_pipeline import StandaloneRAGPipeline
from src.fact_engine import FactEngine
from src.table_engine import TableEngine


class BatchReportIngestor:
    """
    Manages multi-document discovery, parsing, fact extraction, and Neo4j graph population.
    """

    def __init__(self, download_dir: Optional[Path | str] = None):
        self.download_dir = Path(download_dir or Path(__file__).parent.parent / "data" / "documents").resolve()
        self.pipeline = StandaloneRAGPipeline()

    def discover_pdfs(self) -> List[Path]:
        """Find all PDF files in the Download directory."""
        if not self.download_dir.exists():
            return []
        return sorted(list(self.download_dir.glob("*.pdf")))

    def infer_university_and_year(self, pdf_path: Path) -> Tuple[str, str]:
        """Heuristically infer institution name and reporting year from filename."""
        fname = pdf_path.stem

        # Year detection (e.g. 2024-25, 2025, 2024)
        year_m = re.search(r"(20[12][0-9](?:[-–][0-9]{2,4})?)", fname)
        year = year_m.group(1) if year_m else "2024-25"

        # University / Institution detection
        name_lower = fname.lower()
        if "bric" in name_lower:
            uni = "Biotechnology Research and Innovation Council (BRIC)"
        elif "nipgr" in name_lower:
            uni = "National Institute of Plant Genome Research (NIPGR)"
        elif "astrabio" in name_lower or "taxonomy" in name_lower:
            uni = "AstraBio Innovations Council"
        elif "pu" in name_lower or "panjab" in name_lower:
            uni = "Panjab University"
        elif "du" in name_lower or "delhi" in name_lower:
            uni = "Delhi University"
        elif "annual report" in name_lower:
            uni = "National Biotechnology Innovation Council"
        else:
            uni = fname.replace("_", " ").replace("-", " ").title()

        return uni, year

    def ingest_all(self, max_pages_per_doc: int = 15) -> Dict[str, Any]:
        """
        Process all PDFs in the Download directory.
        """
        pdfs = self.discover_pdfs()
        print(f"\n[DISCOVERY] Found {len(pdfs)} PDF reports in {self.download_dir}")

        total_facts = 0
        total_vectors = 0
        total_nodes = 0
        total_edges = 0
        ingested_docs = []

        for pdf in pdfs:
            uni, year = self.infer_university_and_year(pdf)
            doc_id = pdf.stem.replace(" ", "_").replace("-", "_")
            print(f"\n-> Ingesting: {pdf.name}")
            print(f"   Institution: {uni} | Period: {year} | Size: {round(pdf.stat().st_size / (1024*1024), 2)} MB")

            t0 = time.time()

            # Extract raw text spans using fitz (PyMuPDF)
            try:
                import fitz
                doc = fitz.open(str(pdf))
                page_count = min(len(doc), max_pages_per_doc)
                chunks = []

                for pno in range(page_count):
                    page = doc[pno]
                    text = page.get_text("text").strip()
                    if not text:
                        continue

                    # Split text into logical section blocks
                    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
                    for pidx, para in enumerate(paragraphs):
                        # Detect heading
                        first_line = para.split("\n")[0][:60]
                        cid = f"{doc_id}_p{pno+1}_blk{pidx+1}"
                        chunks.append({
                            "chunk_id": cid,
                            "section_id": f"sec_p{pno+1}_{pidx+1}",
                            "heading": first_line,
                            "heading_level": 2 if pidx == 0 else 3,
                            "source_pages": [pno + 1],
                            "plain_text": para,
                            "recommended_task": "general_research",
                            "token_estimate": len(para.split()),
                        })

                doc.close()

                # Ingest through master RAG pipeline
                # 1. Facts
                doc_facts = 0
                for c in chunks:
                    efacts = self.pipeline.fact_engine.extract_facts_from_text(
                        text=c["plain_text"],
                        document_id=doc_id,
                        university=uni,
                        page_number=c["source_pages"][0],
                        section_id=c["section_id"],
                    )
                    doc_facts += len(efacts)

                # 2. Vectors
                doc_vectors = self.pipeline.vector_engine.ingest_chunks(chunks, doc_id=doc_id)

                # 3. Knowledge Graph & Neo4j
                gdata = self.pipeline.graph_engine.build_from_chunks(chunks, doc_id=doc_id)
                neo4j_res = self.pipeline.neo4j_db.sync_graph_data(gdata)

                elapsed = round(time.time() - t0, 3)
                print(f"   [OK] Ingested in {elapsed}s: {doc_facts} facts, {doc_vectors} chunks, {gdata.get('node_count', 0)} graph nodes (Neo4j: {neo4j_res.get('synced', False)})")

                total_facts += doc_facts
                total_vectors += doc_vectors
                total_nodes += gdata.get("node_count", 0)
                total_edges += gdata.get("edge_count", 0)
                ingested_docs.append({
                    "file": pdf.name,
                    "institution": uni,
                    "period": year,
                    "facts": doc_facts,
                    "vectors": doc_vectors,
                    "nodes": gdata.get("node_count", 0),
                    "neo4j_synced": neo4j_res.get("synced", False),
                })

            except Exception as e:
                print(f"   [ERROR] Failed to ingest {pdf.name}: {e}")

        print("\n" + "=" * 70)
        print(f" [BATCH INGESTION COMPLETE] {len(ingested_docs)} Reports Processed")
        print(f" Total Facts Extracted: {total_facts}")
        print(f" Total Vectors Indexed in ChromaDB: {total_vectors}")
        print(f" Total Nodes & Edges in Neo4j: {total_nodes} nodes, {total_edges} edges")
        print("=" * 70 + "\n")

        return {
            "status": "success",
            "download_dir": str(self.download_dir),
            "documents_count": len(ingested_docs),
            "documents": ingested_docs,
            "total_facts": total_facts,
            "total_vectors": total_vectors,
            "total_nodes": total_nodes,
        }


if __name__ == "__main__":
    ingestor = BatchReportIngestor()
    ingestor.ingest_all()
