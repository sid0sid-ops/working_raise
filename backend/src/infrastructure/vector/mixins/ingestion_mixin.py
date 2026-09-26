"""
ChromaDB Chunk Ingestion & Corpus Isolation Mixin
=================================================
Manages context-enriched chunk ingestion, proposition indexing, metadata attachment,
and strict database isolation between production corpora and benchmark evaluations.

Architectural Role & Guarantees:
--------------------------------
1. Database Isolation Boundary (`should_ingest`):
   - Rejects evaluation datasets, benchmark question suites, and synthetic testing files
     from being indexed into the production collection.
   - Prevents benchmark contamination and test-set leakage.

2. Production Chunk Ingestion (`ingest_chunks`):
   - Attaches complete provenance metadata: `doc_id`, `pdf_filename`, `primary_page`,
     `printed_page`, `heading`, `token_estimate`, `chunk_level`.
   - Supports proposition and atomic fact indexing with parent chunk backlinks for compact reports.

3. Benchmark Ingestion Pathway (`ingest_evaluation_chunks`):
   - Ingests external benchmark passages into dedicated isolated collections (e.g. `eval_qna_bge_large`)
     without corrupting the production academic knowledge base.

4. SQLite Batch Limiter:
   - Batches upserts in chunks of 2,000 items to respect ChromaDB's SQLite maximum parameter limit
     (`max_batch_size = 5,461`), preventing `ValueError` on large document batches.

How to Update or Tune:
----------------------
- To add a new excluded test pattern, add it to `should_ingest()`.
- To tune the upsert batch size, adjust `batch_size = 2000` in `ingest_chunks()`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


def should_ingest(file_path: str | Path) -> bool:
    """Enforces strict database isolation: ignores test suites, benchmarks, and evaluation files."""
    path_str = str(file_path).lower().replace("\\", "/")
    excluded_patterns = [
        "evaluation",
        "benchmark",
        "question_suite",
        "question suite",
        "raise-bench",
        "gemini-notebook",
        "benchmark_qa",
    ]
    return not any(pattern in path_str for pattern in excluded_patterns)


class VectorIngestionMixin:
    """Provides document chunk ingestion and benchmark isolation for ChromaDB."""

    def ingest_evaluation_chunks(
        self,
        chunks: List[Dict[str, Any]],
        collection_name: str,
        doc_id: str = "eval_corpus",
    ) -> int:
        """
        Securely ingests benchmark/evaluation passages into an isolated ChromaDB collection.
        Bypasses standard production doc_id rejection while strictly isolating from the
        production academic corpus.
        """
        if not chunks:
            return 0

        self.switch_collection(collection_name)
        col = self._get_collection()
        if col is None:
            return 0

        ids = []
        documents = []
        metadatas = []

        for idx, chunk in enumerate(chunks):
            cid = str(chunk.get("chunk_id") or f"{doc_id}_chk_{idx}")
            plain_text = chunk.get("plain_text") or chunk.get("text") or chunk.get("content") or ""
            if not plain_text.strip():
                continue

            ids.append(cid)
            documents.append(plain_text)
            meta = dict(chunk.get("metadata") or {})
            meta.update({
                "chunk_id": cid,
                "doc_id": str(chunk.get("doc_id") or doc_id),
                "pdf_filename": str(chunk.get("pdf_filename") or doc_id),
                "heading": str(chunk.get("heading") or chunk.get("title") or "Section"),
                "primary_page": int(chunk.get("primary_page") or 1),
                "token_estimate": int(chunk.get("token_estimate") or len(plain_text.split())),
            })
            metadatas.append(meta)

        if not ids:
            return 0

        # Fast path: check existing IDs
        try:
            all_existing = set()
            chk_batch = 2000
            for i in range(0, len(ids), chk_batch):
                batch_res = col.get(ids=ids[i:i+chk_batch])
                if batch_res and "ids" in batch_res:
                    all_existing.update(batch_res["ids"])
            missing_indices = [i for i, c_id in enumerate(ids) if c_id not in all_existing]
            if not missing_indices:
                return len(ids)
            ids = [ids[i] for i in missing_indices]
            documents = [documents[i] for i in missing_indices]
            metadatas = [metadatas[i] for i in missing_indices]
        except Exception:
            pass

        embeddings = self.compute_embeddings(documents)

        batch_size = 2000
        total_inserted = 0
        for i in range(0, len(ids), batch_size):
            b_ids = ids[i:i+batch_size]
            b_docs = documents[i:i+batch_size]
            b_metas = metadatas[i:i+batch_size]
            b_embs = embeddings[i:i+batch_size]
            col.upsert(
                ids=b_ids,
                documents=b_docs,
                embeddings=b_embs,
                metadatas=b_metas,
            )
            total_inserted += len(b_ids)

        return total_inserted

    def ingest_chunks(self, chunks: List[Dict[str, Any]], doc_id: str = "default") -> int:
        """
        Add context-enriched document chunks into ChromaDB collection with full provenance metadata.
        Strictly rejects evaluation / benchmark files to prevent test contamination.
        """
        if not chunks:
            return 0

        if not should_ingest(doc_id):
            print(f"⛔ [ChromaDB Isolation] Ingestion rejected for excluded evaluation doc_id: '{doc_id}'")
            return 0

        ids = []
        documents = []
        metadatas = []

        for idx, chunk in enumerate(chunks):
            pdf_fname = str(chunk.get("pdf_filename", doc_id))
            if not should_ingest(pdf_fname):
                continue
            cid = str(chunk.get("chunk_id") or f"{doc_id}_chk_{idx}")
            plain_text = chunk.get("plain_text") or chunk.get("text") or ""
            enriched_text = chunk.get("enriched_text") or plain_text
            
            if not plain_text.strip():
                continue

            ids.append(cid)
            documents.append(enriched_text)
            metadatas.append({
                "chunk_id": cid,
                "doc_id": doc_id,
                "parent_chunk_id": str(chunk.get("parent_chunk_id") or ""),
                "chunk_level": str(chunk.get("chunk_level") or "child"),
                "chunking_strategy": str(chunk.get("chunking_strategy") or "gga_hybrid"),
                "pdf_filename": str(chunk.get("pdf_filename", doc_id)),
                "university": str(chunk.get("university", "Institution")),
                "heading": str(chunk.get("heading", f"Section {idx+1}")),
                "primary_page": int(chunk.get("primary_page", chunk.get("source_pages", [1])[0] if chunk.get("source_pages") else 1)),
                "printed_page": str(chunk.get("printed_page") or ""),
                "token_estimate": int(chunk.get("token_estimate", len(plain_text.split()))),
                "recommended_task": str(chunk.get("recommended_task", "general")),
            })

            # Optional fine-grained proposition/atomic fact indexing with parent backlinks (applied for compact reports <= 400 chunks)
            props = chunk.get("propositions") or chunk.get("atomic_facts") or []
            if isinstance(props, list) and len(chunks) <= 400:
                for p_idx, p_item in enumerate(props):
                    p_str = str(p_item).strip()
                    if p_str and p_str != plain_text.strip():
                        p_id = f"{cid}_prop_{p_idx}"
                        ids.append(p_id)
                        documents.append(p_str)
                        metadatas.append({
                            "chunk_id": p_id,
                            "doc_id": doc_id,
                            "parent_chunk_id": cid,
                            "chunk_level": "proposition",
                            "chunking_strategy": str(chunk.get("chunking_strategy") or "gga_hybrid"),
                            "pdf_filename": str(chunk.get("pdf_filename", doc_id)),
                            "university": str(chunk.get("university", "Institution")),
                            "heading": str(chunk.get("heading", f"Section {idx+1}")),
                            "primary_page": int(chunk.get("primary_page", chunk.get("source_pages", [1])[0] if chunk.get("source_pages") else 1)),
                            "printed_page": str(chunk.get("printed_page") or ""),
                            "token_estimate": len(p_str.split()),
                            "recommended_task": "fact_lookup",
                        })

        if not ids:
            return 0

        # Fast path: check if chunks are already indexed in persistent ChromaDB collection
        col = self._get_collection()
        total_items = self.count()
        if col is not None and total_items > 0:
            try:
                all_existing = set()
                chk_batch = 2000
                for i in range(0, len(ids), chk_batch):
                    batch_res = col.get(ids=ids[i:i+chk_batch])
                    if batch_res and "ids" in batch_res:
                        all_existing.update(batch_res["ids"])
                missing_indices = [i for i, cid in enumerate(ids) if cid not in all_existing]
                if not missing_indices:
                    return len(ids)
                ids = [ids[i] for i in missing_indices]
                documents = [documents[i] for i in missing_indices]
                metadatas = [metadatas[i] for i in missing_indices]
            except Exception as ex:
                print(f"ChromaDB ID lookup notice: {ex}")

        embeddings = self.compute_embeddings(documents)

        if col is not None:
            try:
                batch_size = 2000
                total_inserted = 0
                for b_start in range(0, len(ids), batch_size):
                    b_end = b_start + batch_size
                    col.upsert(
                        ids=ids[b_start:b_end],
                        documents=documents[b_start:b_end],
                        embeddings=embeddings[b_start:b_end],
                        metadatas=metadatas[b_start:b_end],
                    )
                    total_inserted += len(ids[b_start:b_end])
                return total_inserted
            except Exception as e:
                print(f"ChromaDB upsert notice: {e}")

        return len(ids)
