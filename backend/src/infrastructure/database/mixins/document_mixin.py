"""
Postgres Document Store Mixin
=============================
Handles document metadata, library categorization, ingestion status tracking,
and document lifecycle operations in PostgreSQL.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("raise.infrastructure.database.postgres.documents")


class DocumentStoreMixin:
    """Provides methods for managing document metadata and pipeline status tracking."""

    def save_document(
        self,
        doc_id: str,
        filename: str,
        chunks_count: int,
        library: str = "default",
        is_protected: bool = False,
        can_delete: bool = True,
        owner: str = "user"
    ) -> bool:
        if not self.is_connected:
            self._memory_docs[doc_id] = {
                "id": doc_id,
                "filename": filename,
                "chunks": chunks_count,
                "library": library,
                "is_protected": is_protected,
                "can_delete": can_delete,
                "owner": owner,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
            return True

        conn = self._get_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO document_metadata (id, filename, chunks_count, library, is_protected, can_delete, owner)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE 
                SET filename = EXCLUDED.filename,
                    chunks_count = EXCLUDED.chunks_count,
                    library = EXCLUDED.library,
                    is_protected = EXCLUDED.is_protected,
                    can_delete = EXCLUDED.can_delete,
                    owner = EXCLUDED.owner
            """, (doc_id, filename, chunks_count, library, is_protected, can_delete, owner))
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save document metadata in PostgreSQL: {e}")
            return False
        finally:
            self._release_connection(conn)

    def save_document_metadata(
        self,
        doc_id: str,
        filename: str,
        chunks_count: int,
        library: str = "default",
        is_protected: bool = False,
        can_delete: bool = True,
        owner: str = "user"
    ) -> bool:
        """Alias for save_document matching document ingestion specification."""
        return self.save_document(
            doc_id=doc_id,
            filename=filename,
            chunks_count=chunks_count,
            library=library,
            is_protected=is_protected,
            can_delete=can_delete,
            owner=owner
        )

    def list_documents(self, library: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_connected:
            docs = list(self._memory_docs.values())
            if library:
                docs = [d for d in docs if d.get("library") == library]
            return docs

        conn = self._get_connection()
        if not conn:
            return list(self._memory_docs.values())
        try:
            cur = conn.cursor()
            if library:
                cur.execute("""
                    SELECT id, filename, uploaded_at, chunks_count, library, is_protected, can_delete, owner
                    FROM document_metadata
                    WHERE library = %s
                    ORDER BY uploaded_at DESC
                """, (library,))
            else:
                cur.execute("""
                    SELECT id, filename, uploaded_at, chunks_count, library, is_protected, can_delete, owner
                    FROM document_metadata
                    ORDER BY uploaded_at DESC
                """)
            rows = cur.fetchall()
            cur.close()
            return [
                {
                    "id": r[0],
                    "filename": r[1],
                    "uploaded_at": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2]),
                    "chunks": r[3],
                    "library": r[4],
                    "is_protected": bool(r[5]) if len(r) > 5 and r[5] is not None else False,
                    "can_delete": bool(r[6]) if len(r) > 6 and r[6] is not None else True,
                    "owner": r[7] if len(r) > 7 and r[7] else "user",
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list documents from PostgreSQL: {e}")
            return []
        finally:
            self._release_connection(conn)

    def delete_document(self, doc_id: str) -> bool:
        self._memory_docs.pop(doc_id, None)
        self._memory_doc_status.pop(doc_id, None)
        for k in list(self._memory_docs.keys()):
            if self._memory_docs[k].get("filename") == doc_id or self._memory_docs[k].get("id") == doc_id:
                self._memory_docs.pop(k, None)
        for k in list(self._memory_doc_status.keys()):
            if self._memory_doc_status[k].get("filename") == doc_id or self._memory_doc_status[k].get("id") == doc_id:
                self._memory_doc_status.pop(k, None)

        if not self.is_connected:
            return True

        conn = self._get_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM document_metadata WHERE id = %s OR filename = %s", (doc_id, doc_id))
            cur.execute("DELETE FROM documents WHERE id = %s OR filename = %s", (doc_id, doc_id))
            conn.commit()
            cur.close()
            return True

        except Exception as e:
            logger.error(f"Failed to delete document from PostgreSQL: {e}")
            return False
        finally:
            self._release_connection(conn)

    def upsert_document_status(
        self,
        doc_id: str,
        filename: str,
        phase: str = "uploading",
        percent: int = 0,
        status: str = "processing",
        detail: str = "",
        error_message: Optional[str] = None,
        pages_processed: int = 0,
        chunks_extracted: int = 0,
        file_size_bytes: int = 0,
        library: str = "default",
        is_protected: bool = False,
        can_delete: bool = True,
        owner: str = "user",
    ) -> bool:
        """
        Record and update document ingestion pipeline status in PostgreSQL documents table
        and in-memory registry.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        status_record = {
            "id": doc_id,
            "doc_id": doc_id,
            "filename": filename,
            "phase": phase,
            "percent": percent,
            "progress_percent": percent,
            "status": status,
            "detail": detail,
            "message": detail or f"{phase.capitalize()} in progress ({percent}%)",
            "error_message": error_message,
            "pages_processed": pages_processed,
            "chunks_extracted": chunks_extracted,
            "file_size_bytes": file_size_bytes,
            "library": library,
            "is_protected": is_protected,
            "can_delete": can_delete,
            "owner": owner,
            "updated_at": now_iso,
        }
        self._memory_doc_status[doc_id] = status_record
        self._memory_doc_status[filename] = status_record

        if not self.is_connected:
            return True

        conn = self._get_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO documents (
                    id, filename, phase, progress_percent, status, detail, error_message, 
                    pages_processed, chunks_extracted, file_size_bytes, library,
                    is_protected, can_delete, owner, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    phase = EXCLUDED.phase,
                    progress_percent = EXCLUDED.progress_percent,
                    status = EXCLUDED.status,
                    detail = EXCLUDED.detail,
                    error_message = EXCLUDED.error_message,
                    pages_processed = EXCLUDED.pages_processed,
                    chunks_extracted = EXCLUDED.chunks_extracted,
                    file_size_bytes = EXCLUDED.file_size_bytes,
                    library = EXCLUDED.library,
                    is_protected = EXCLUDED.is_protected,
                    can_delete = EXCLUDED.can_delete,
                    owner = EXCLUDED.owner,
                    updated_at = CURRENT_TIMESTAMP
            """, (doc_id, filename, phase, percent, status, detail, error_message, pages_processed, chunks_extracted, file_size_bytes, library, is_protected, can_delete, owner))
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Failed to upsert document status in PostgreSQL: {e}")
            return False
        finally:
            self._release_connection(conn)

    def get_document_status(self, doc_id_or_filename: str) -> Optional[Dict[str, Any]]:
        """
        Query real ingestion progress state for a given document.
        """
        rec = self._memory_doc_status.get(doc_id_or_filename)

        if not self.is_connected:
            return rec

        conn = self._get_connection()
        if not conn:
            return rec
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, filename, phase, progress_percent, status, detail, error_message, 
                       pages_processed, chunks_extracted, file_size_bytes, library, updated_at,
                       is_protected, can_delete, owner
                FROM documents
                WHERE id = %s OR filename = %s
                ORDER BY updated_at DESC
                LIMIT 1
            """, (doc_id_or_filename, doc_id_or_filename))
            row = cur.fetchone()
            cur.close()
            if row:
                phase = row[2]
                percent = int(row[3])
                status = row[4]
                detail = row[5] or ""
                return {
                    "id": row[0],
                    "doc_id": row[0],
                    "filename": row[1],
                    "phase": phase,
                    "percent": percent,
                    "progress_percent": percent,
                    "status": status,
                    "detail": detail,
                    "message": detail or f"{phase.capitalize()} in progress ({percent}%)",
                    "error_message": row[6],
                    "pages_processed": int(row[7]),
                    "chunks_extracted": int(row[8]),
                    "file_size_bytes": int(row[9]),
                    "library": row[10],
                    "updated_at": row[11].isoformat() if hasattr(row[11], "isoformat") else str(row[11]),
                    "is_protected": bool(row[12]) if len(row) > 12 and row[12] is not None else False,
                    "can_delete": bool(row[13]) if len(row) > 13 and row[13] is not None else True,
                    "owner": row[14] if len(row) > 14 and row[14] else "user",
                }
            return rec
        except Exception as e:
            logger.error(f"Failed to fetch document status from PostgreSQL: {e}")
            return rec
        finally:
            self._release_connection(conn)
