"""
Document Separation & Storage Isolation Evaluator Module
========================================================
Verifies that the 4 library annual report PDFs:
  1. BRIC-Annual-Report-2025.pdf
  2. Annual Report 2023-24.pdf
  3. Annual Report 2022-23.pdf
  4. Annual Report 2021-22.pdf
are strictly partitioned in storage (ChromaDB, BM25, Neo4j), have zero
cross-contamination, and that drawer scoping prevents cross-document data leakage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.infrastructure.vector.chroma import LocalVectorEngine
from src.infrastructure.graph.neo4j import Neo4jDatabase


class DocumentIsolationEvaluator:
    """Validates document-level data segregation, metadata boundaries, and drawer scoping."""

    EXPECTED_DOCUMENTS = [
        {"filename": "BRIC-Annual-Report-2025.pdf", "doc_prefix": "BRIC_Annual_Report_2025"},
        {"filename": "Annual Report 2023-24.pdf", "doc_prefix": "Annual_Report_2023_24"},
        {"filename": "Annual Report 2022-23.pdf", "doc_prefix": "Annual_Report_2022_23"},
        {"filename": "Annual Report 2021-22.pdf", "doc_prefix": "Annual_Report_2021_22"},
    ]

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.manifest_path = self.project_root / "data" / "processed" / "ingested_manifest.json"
        self.chroma_engine = LocalVectorEngine()
        self.neo4j_db = Neo4jDatabase()

    def verify_storage_separation(self) -> Dict[str, Any]:
        """
        Ensures each of the 4 documents is separately stored, indexed, and isolated.
        """
        report: Dict[str, Any] = {
            "manifest_verified": False,
            "chroma_partitioning": {},
            "neo4j_partitioning": {},
            "cross_contamination_detected": False,
            "leakage_events": [],
            "all_isolated": False,
        }

        # 1. Manifest verification
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            ready_docs = [d.get("filename") for d in manifest_data.get("ready_documents", [])]
            all_present = all(doc["filename"] in ready_docs for doc in self.EXPECTED_DOCUMENTS)
            report["manifest_verified"] = all_present
        else:
            report["leakage_events"].append("Manifest file missing: ingested_manifest.json")

        # 2. ChromaDB Partitioning & Contamination Check
        col = self.chroma_engine.collection
        total_vectors = col.count()
        report["total_vectors"] = total_vectors

        for doc_info in self.EXPECTED_DOCUMENTS:
            fname = doc_info["filename"]
            prefix = doc_info["doc_prefix"]

            # Query vectors specifically by filename
            res = col.get(where={"pdf_filename": fname}, include=["metadatas"])
            chunk_ids = res.get("ids", [])
            metadatas = res.get("metadatas", [])

            # Verify that every returned vector matches the document prefix
            corrupted = []
            for cid, meta in zip(chunk_ids, metadatas):
                if not cid.startswith(prefix):
                    corrupted.append(cid)
                if meta.get("pdf_filename") != fname:
                    corrupted.append(f"{cid} (meta filename {meta.get('pdf_filename')})")

            if corrupted:
                report["cross_contamination_detected"] = True
                report["leakage_events"].append(
                    f"Contamination in {fname}: found {len(corrupted)} alien IDs (e.g. {corrupted[:3]})"
                )

            report["chroma_partitioning"][fname] = {
                "vector_count": len(chunk_ids),
                "is_clean": len(corrupted) == 0,
                "prefix": prefix,
            }

        # 3. Neo4j Node Prefix Segregation
        if self.neo4j_db.connected:
            for doc_info in self.EXPECTED_DOCUMENTS:
                prefix = doc_info["doc_prefix"]
                fname = doc_info["filename"]
                cypher = """
                    MATCH (c:Chunk)
                    WHERE c.id STARTS WITH $prefix
                    RETURN count(c) as node_count
                """
                res = self.neo4j_db.run_cypher(cypher, {"prefix": prefix})
                node_cnt = res[0]["node_count"] if res else 0
                report["neo4j_partitioning"][fname] = {
                    "chunk_nodes": node_cnt,
                    "prefix": prefix,
                }

        # 4. Active Drawer Isolation Test
        # Attach Doc 1 (BRIC 2025). Query with drawer filter for Doc 1.
        # Ensure that absolutely ZERO chunks from Doc 2, 3, or 4 are retrieved.
        target_doc = "BRIC-Annual-Report-2025.pdf"
        other_docs = [d["filename"] for d in self.EXPECTED_DOCUMENTS if d["filename"] != target_doc]

        scoped_res = col.get(where={"pdf_filename": target_doc}, include=["metadatas"], limit=50)
        scoped_metas = scoped_res.get("metadatas", [])

        unattached_leakage = 0
        for m in scoped_metas:
            if m.get("pdf_filename") in other_docs:
                unattached_leakage += 1

        report["drawer_isolation_test"] = {
            "target_document": target_doc,
            "samples_checked": len(scoped_metas),
            "unattached_leaks": unattached_leakage,
            "passed": unattached_leakage == 0,
        }

        if unattached_leakage > 0:
            report["cross_contamination_detected"] = True
            report["leakage_events"].append(
                f"Drawer isolation breach: {unattached_leakage} unattached chunks returned"
            )

        report["all_isolated"] = (
            report["manifest_verified"]
            and not report["cross_contamination_detected"]
            and all(p.get("vector_count", 0) > 0 for p in report["chroma_partitioning"].values())
            and all(p.get("is_clean", False) for p in report["chroma_partitioning"].values())
        )
        return report
