"""
ChromaDB Document Vector Lifecycle & Deletion Mixin
===================================================
Manages document vector purging, collection reset, and lifecycle cleanup across ChromaDB.

Architectural Role & Guarantees:
--------------------------------
1. Granular Document Deletion (`delete_document`):
   - Multi-phase document vector removal:
     * Phase 1: Matches and deletes by `pdf_filename` metadata.
     * Phase 2: Matches and deletes by `doc_id` metadata.
     * Phase 3: Matches and deletes by chunk ID prefix.
   - Prevents stale or phantom vector chunks from lingering after document deletion.

2. Collection Reset (`reset_collection`):
   - Deletes and re-creates the collection with cosine similarity space (`metadata={"hnsw:space": "cosine"}`).

3. Interface Compliance (`purge_document_vectors`):
   - Directly satisfies the `IVectorStore` interface required by ingestion and lifecycle orchestrators.

How to Update or Tune:
----------------------
- To configure alternative distance spaces (e.g. l2, ip), modify the HNSW space in `reset_collection()`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


class VectorLifecycleMixin:
    """Provides document vector deletion, purge, and collection reset operations for ChromaDB."""

    def delete_document(self, pdf_filename: str, doc_id: Optional[str] = None) -> int:
        """
        Deletes all chunks and embeddings associated with a document from ChromaDB.
        Returns the count of purged vector items.
        """
        if getattr(self, "collection", None) is None:
            return 0
        deleted_count = 0
        target_doc_id = doc_id or re.sub(r"[^a-zA-Z0-9]", "_", Path(pdf_filename).stem)[:40]
        try:
            # 1. Check by pdf_filename metadata
            try:
                res1 = self.collection.get(where={"pdf_filename": pdf_filename})
                if res1 and res1.get("ids"):
                    self.collection.delete(ids=res1["ids"])
                    deleted_count += len(res1["ids"])
            except Exception:
                pass

            # 2. Check by doc_id metadata
            try:
                res2 = self.collection.get(where={"doc_id": target_doc_id})
                if res2 and res2.get("ids"):
                    self.collection.delete(ids=res2["ids"])
                    deleted_count += len(res2["ids"])
            except Exception:
                pass

            # 3. Check by chunk ID prefix
            try:
                all_res = self.collection.get()
                matching_ids = [cid for cid in all_res.get("ids", []) if cid.startswith(target_doc_id)]
                if matching_ids:
                    self.collection.delete(ids=matching_ids)
                    deleted_count += len(matching_ids)
            except Exception:
                pass

        except Exception as e:
            print(f"Error deleting document from ChromaDB: {e}")
        return deleted_count

    def reset_collection(self):
        """Clears and re-creates active ChromaDB collection with cosine HNSW space."""
        if getattr(self, "collection", None) is not None and getattr(self, "client", None) is not None:
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.create_collection(
                    self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                pass

    def purge_document_vectors(self, doc_id: str) -> int:
        """Satisfies IVectorStore interface by purging all vector representations for doc_id."""
        return self.delete_document(pdf_filename=doc_id, doc_id=doc_id)
