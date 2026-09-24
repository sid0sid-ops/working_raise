from __future__ import annotations
import hashlib
import os
import json
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from src.storage.interfaces import ISessionStore, ICacheStore

logger = logging.getLogger("raise.infrastructure.database.postgres")

class PostgresManager(ISessionStore):
    """
    Manages long-term chat sessions, message logs, and document metadata in PostgreSQL.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        dbname: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(port or os.getenv("POSTGRES_PORT", "5432"))
        self.dbname = dbname or os.getenv("POSTGRES_DB", "raise_db")
        self.user = user or os.getenv("POSTGRES_USER", "raise_user")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "raise_password")
        
        self.is_connected = False
        self._pool = None
        self._memory_chat: Dict[str, List[Dict[str, Any]]] = {}
        self._memory_docs: Dict[str, Dict[str, Any]] = {}
        self._memory_doc_status: Dict[str, Dict[str, Any]] = {}
        self._memory_feedback: List[Dict[str, Any]] = []
        self._memory_sessions: Dict[str, Dict[str, Any]] = {}
        
        self._connect_and_init()

    def _init_pool(self):
        try:
            from psycopg2 import pool
            if self._pool is None:
                self._pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=30,
                    host=self.host,
                    port=self.port,
                    dbname=self.dbname,
                    user=self.user,
                    password=self.password,
                    connect_timeout=2
                )
        except Exception as e:
            logger.debug(f"ThreadedConnectionPool init skipped/failed: {e}")

    def _get_connection(self):
        now = time.time()
        if not self.is_connected and (now - getattr(self, "_last_pg_probe", 0)) < 3.0:
            return None
        self._last_pg_probe = now

        probe_host = "127.0.0.1" if self.host in ("localhost", "127.0.0.1") else self.host
        try:
            import socket
            with socket.create_connection((probe_host, self.port), timeout=0.05):
                pass
        except Exception:
            self.is_connected = False
            return None

        try:
            if not self._pool:
                self._init_pool()
            if self._pool:
                conn = self._pool.getconn()
                self.is_connected = True
                return conn
            import psycopg2
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                connect_timeout=2
            )
            self.is_connected = True
            return conn
        except Exception as e:
            logger.warning(f"PostgreSQL connection attempt failed: {e}")
            self.is_connected = False
            return None

    def _release_connection(self, conn):
        if not conn:
            return
        try:
            if self._pool:
                self._pool.putconn(conn)
            else:
                conn.close()
        except Exception as e:
            logger.debug(f"Error releasing PostgreSQL connection: {e}")

    def _connect_and_init(self):
        conn = self._get_connection()
        if not conn:
            self.is_connected = False
            logger.info("PostgreSQL unreachable. Running in in-memory fallback mode.")
            return

        try:
            cur = conn.cursor()
            # 1. Chat Messages Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    mode VARCHAR(20) DEFAULT 'fast',
                    sources JSONB DEFAULT '[]'::jsonb,
                    citations JSONB DEFAULT '[]'::jsonb,
                    duration_sec DOUBLE PRECISION DEFAULT 0.0,
                    turn_index INT DEFAULT 0,
                    message_hash VARCHAR(64),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS citations JSONB DEFAULT '[]'::jsonb;
                ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS duration_sec DOUBLE PRECISION DEFAULT 0.0;
                ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS turn_index INT DEFAULT 0;
                ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS message_hash VARCHAR(64);
                CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id);
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'uq_session_message_turn'
                    ) THEN
                        ALTER TABLE chat_messages ADD CONSTRAINT uq_session_message_turn UNIQUE (session_id, message_hash);
                    END IF;
                END $$;
            """)

            # 2. Document Library Metadata Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_metadata (
                    id VARCHAR(100) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    library VARCHAR(100) DEFAULT 'default',
                    chunks_count INT DEFAULT 0,
                    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    is_protected BOOLEAN DEFAULT FALSE,
                    can_delete BOOLEAN DEFAULT TRUE,
                    owner VARCHAR(100) DEFAULT 'user'
                );
                ALTER TABLE document_metadata ADD COLUMN IF NOT EXISTS is_protected BOOLEAN DEFAULT FALSE;
                ALTER TABLE document_metadata ADD COLUMN IF NOT EXISTS can_delete BOOLEAN DEFAULT TRUE;
                ALTER TABLE document_metadata ADD COLUMN IF NOT EXISTS owner VARCHAR(100) DEFAULT 'user';
                CREATE INDEX IF NOT EXISTS idx_doc_library ON document_metadata(library);
            """)

            # 3. Session Metadata and Message History Tables (system-architecture.md compliance)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS session_metadata (
                    id VARCHAR(255) PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    attached_docs JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                ALTER TABLE session_metadata ADD COLUMN IF NOT EXISTS attached_docs JSONB DEFAULT '[]'::jsonb;
                CREATE TABLE IF NOT EXISTS message_history (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) REFERENCES session_metadata(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_msg_session ON message_history(session_id);
            """)

            # 4. Ingestion Pipeline & Document Tracking Table (Frontend Real Progress Contract)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id VARCHAR(100) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'processing',
                    phase VARCHAR(50) DEFAULT 'uploading',
                    progress_percent INT DEFAULT 0,
                    detail TEXT DEFAULT '',
                    error_message TEXT DEFAULT NULL,
                    pages_processed INT DEFAULT 0,
                    chunks_extracted INT DEFAULT 0,
                    file_size_bytes BIGINT DEFAULT 0,
                    library VARCHAR(100) DEFAULT 'default',
                    is_protected BOOLEAN DEFAULT FALSE,
                    can_delete BOOLEAN DEFAULT TRUE,
                    owner VARCHAR(100) DEFAULT 'user',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_protected BOOLEAN DEFAULT FALSE;
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS can_delete BOOLEAN DEFAULT TRUE;
                ALTER TABLE documents ADD COLUMN IF NOT EXISTS owner VARCHAR(100) DEFAULT 'user';
                CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
            """)

            # 5. User Feedback Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_feedback (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(100) NOT NULL,
                    query TEXT,
                    rating VARCHAR(50) NOT NULL,
                    reason TEXT,
                    message_id VARCHAR(100),
                    client_ip VARCHAR(45),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                ALTER TABLE chat_feedback ADD COLUMN IF NOT EXISTS client_ip VARCHAR(45);
                CREATE INDEX IF NOT EXISTS idx_feedback_session ON chat_feedback(session_id);
            """)
            conn.commit()
            cur.close()
            self._release_connection(conn)
            self.is_connected = True
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}/{self.dbname}")
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL schema: {e}")
            self.is_connected = False

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        mode: str = "fast",
        sources: Optional[List[str]] = None,
        active_docs: Optional[List[str]] = None
    ) -> bool:
        sources = sources or []
        if not self.is_connected:
            self._memory_chat.setdefault(session_id, []).append({
                "role": role,
                "content": content,
                "text": content,
                "mode": mode,
                "sources": sources,
                "citations": sources,
                "response": {"sources": sources},
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            if active_docs is not None:
                self._memory_sessions.setdefault(session_id, {})["attached_docs"] = active_docs
            return True

        conn = self._get_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            # Keep session_metadata in sync so foreign key on message_history is valid
            clean_title = (content[:60] + "...") if len(content) > 60 else content
            docs_json = json.dumps(active_docs) if active_docs is not None else None
            if role == "user":
                if docs_json is not None:
                    cur.execute("""
                        INSERT INTO session_metadata (id, title, attached_docs, created_at, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO UPDATE SET
                            title = CASE 
                                WHEN session_metadata.title = 'New Session' OR session_metadata.title LIKE 'Chat %%' 
                                THEN EXCLUDED.title 
                                ELSE session_metadata.title 
                            END,
                            attached_docs = CASE
                                WHEN EXCLUDED.attached_docs IS NOT NULL AND EXCLUDED.attached_docs != '[]'::jsonb
                                THEN EXCLUDED.attached_docs
                                ELSE session_metadata.attached_docs
                            END,
                            updated_at = CURRENT_TIMESTAMP;
                    """, (session_id, clean_title.strip(), docs_json))
                else:
                    cur.execute("""
                        INSERT INTO session_metadata (id, title, created_at, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO UPDATE SET
                            title = CASE 
                                WHEN session_metadata.title = 'New Session' OR session_metadata.title LIKE 'Chat %%' 
                                THEN EXCLUDED.title 
                                ELSE session_metadata.title 
                            END,
                            updated_at = CURRENT_TIMESTAMP;
                    """, (session_id, clean_title.strip()))
            else:
                cur.execute("""
                    INSERT INTO session_metadata (id, title, created_at, updated_at)
                    VALUES (%s, 'New Session', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET
                        updated_at = CURRENT_TIMESTAMP;
                """, (session_id,))

            # Save in chat_messages idempotently
            m_hash = hashlib.sha256(f"{session_id}:{role}:{content.strip()}".encode("utf-8")).hexdigest()
            cur.execute("""
                INSERT INTO chat_messages (session_id, role, content, mode, sources, citations, message_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, message_hash) DO NOTHING
            """, (session_id, role, content, mode, json.dumps(sources), json.dumps(sources), m_hash))

            # Keep message_history in sync for relational consistency
            try:
                cur.execute("""
                    INSERT INTO message_history (session_id, role, content, timestamp)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """, (session_id, role, content))
            except Exception:
                pass

            conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save message in PostgreSQL: {e}")
            return False
        finally:
            self._release_connection(conn)

    def update_session_drawer(self, session_id: str, attached_docs: List[str]) -> bool:
        """
        Directly update the attached drawer documents for a given session.
        """
        attached_docs = attached_docs or []
        docs_json = json.dumps(attached_docs)
        if not self.is_connected:
            self._memory_sessions.setdefault(session_id, {})["attached_docs"] = attached_docs
            return True

        conn = self._get_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO session_metadata (id, title, attached_docs, created_at, updated_at)
                VALUES (%s, 'New Session', %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    attached_docs = EXCLUDED.attached_docs,
                    updated_at = CURRENT_TIMESTAMP;
            """, (session_id, docs_json))
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Failed to update session drawer in PostgreSQL: {e}")
            return False
        finally:
            self._release_connection(conn)

    def get_session_drawer(self, session_id: str) -> List[str]:
        """
        Retrieve list of attached documents for a specific session.
        """
        if not self.is_connected:
            return self._memory_sessions.get(session_id, {}).get("attached_docs", [])

        conn = self._get_connection()
        if not conn:
            return self._memory_sessions.get(session_id, {}).get("attached_docs", [])
        try:
            cur = conn.cursor()
            cur.execute("SELECT attached_docs FROM session_metadata WHERE id = %s", (session_id,))
            row = cur.fetchone()
            cur.close()
            if row and row[0]:
                val = row[0]
                if isinstance(val, list):
                    return val
                elif isinstance(val, str):
                    try:
                        return json.loads(val)
                    except Exception:
                        return []
            return []
        except Exception as e:
            logger.error(f"Failed to get session drawer for {session_id} from PostgreSQL: {e}")
            return self._memory_sessions.get(session_id, {}).get("attached_docs", [])
        finally:
            self._release_connection(conn)

    def attach_to_session_drawer(self, session_id: str, document_identifier: str) -> List[str]:
        """
        Idempotently attach a document filename/ID to a session drawer.
        Returns the updated list of attached documents.
        """
        current_docs = self.get_session_drawer(session_id)
        if document_identifier not in current_docs:
            current_docs.append(document_identifier)
            self.update_session_drawer(session_id, current_docs)
        return current_docs

    def remove_from_session_drawer(self, session_id: str, document_identifier: str) -> List[str]:
        """
        Remove a document from a session drawer (does NOT delete document from Library).
        Returns the updated list of attached documents.
        """
        current_docs = self.get_session_drawer(session_id)
        updated_docs = [d for d in current_docs if d != document_identifier]
        if len(updated_docs) != len(current_docs):
            self.update_session_drawer(session_id, updated_docs)
        return updated_docs

    def get_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        def _normalize_msg(m: Dict[str, Any]) -> Dict[str, Any]:
            txt = m.get("text") or m.get("content", "")
            srcs = m.get("sources") or m.get("citations", [])
            return {
                **m,
                "role": m.get("role", "user"),
                "content": txt,
                "text": txt,
                "mode": m.get("mode", "fast"),
                "sources": srcs,
                "citations": srcs,
                "response": m.get("response") or ({"sources": srcs} if srcs else None),
                "created_at": m.get("created_at", datetime.now(timezone.utc).isoformat()),
            }

        if not self.is_connected:
            raw = self._memory_chat.get(session_id, [])[-limit:]
            return [_normalize_msg(m) for m in raw]

        conn = self._get_connection()
        if not conn:
            raw = self._memory_chat.get(session_id, [])[-limit:]
            return [_normalize_msg(m) for m in raw]

        try:
            cur = conn.cursor()
            # Sliding window context query: fetch the N latest messages, then sort chronologically
            cur.execute("""
                SELECT role, content, mode, sources, created_at
                FROM (
                    SELECT id, role, content, mode, sources, created_at
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                ) subquery
                ORDER BY subquery.id ASC
            """, (session_id, limit))
            rows = cur.fetchall()
            cur.close()
            result = []
            for r in rows:
                raw_sources = r[3] if isinstance(r[3], list) else (json.loads(r[3]) if r[3] else [])
                text_content = r[1] or ""
                result.append({
                    "role": r[0],
                    "content": text_content,
                    "text": text_content,
                    "mode": r[2],
                    "sources": raw_sources,
                    "citations": raw_sources,
                    "response": {"sources": raw_sources} if raw_sources else None,
                    "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4])
                })
            return result
        except Exception as e:
            logger.error(f"Failed to fetch messages from PostgreSQL: {e}")
            return []
        finally:
            self._release_connection(conn)

    def clear_session(self, session_id: str) -> bool:
        self._memory_chat.pop(session_id, None)
        self._memory_sessions.pop(session_id, None)
        if not self.is_connected:
            return True

        conn = self._get_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM chat_messages WHERE session_id = %s", (session_id,))
            try:
                cur.execute("DELETE FROM message_history WHERE session_id = %s", (session_id,))
                cur.execute("DELETE FROM session_metadata WHERE id = %s", (session_id,))
            except Exception:
                pass
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Failed to clear session in PostgreSQL: {e}")
            return False
        finally:
            self._release_connection(conn)

    def clear_all_sessions(self) -> bool:
        self._memory_chat.clear()
        self._memory_sessions.clear()
        if not self.is_connected:
            return True
        conn = self._get_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM chat_messages;")
            try:
                cur.execute("DELETE FROM message_history;")
                cur.execute("DELETE FROM session_metadata;")
            except Exception:
                pass
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Failed to clear all sessions in PostgreSQL: {e}")
            return False
        finally:
            self._release_connection(conn)

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

    def list_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Retrieve all chat sessions, titles, message counts, and timestamps.
        """
        sessions_dict = {}
        for sid, msgs in self._memory_chat.items():
            first_msg = (msgs[0].get("content") or msgs[0].get("text") or "Untitled Conversation") if msgs else "Untitled Conversation"
            sessions_dict[sid] = {
                "id": sid,
                "thread_id": sid,
                "session_id": sid,
                "title": (first_msg[:60] + "...") if len(first_msg) > 60 else first_msg,
                "message_count": len(msgs),
                "created_at": msgs[0].get("created_at", datetime.now(timezone.utc).isoformat()) if msgs else datetime.now(timezone.utc).isoformat(),
                "updated_at": msgs[-1].get("created_at", datetime.now(timezone.utc).isoformat()) if msgs else datetime.now(timezone.utc).isoformat(),
            }

        if not self.is_connected:
            return list(sessions_dict.values())

        conn = self._get_connection()
        if not conn:
            return list(sessions_dict.values())
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.id, s.title, s.created_at, s.updated_at, COUNT(m.id) as msg_count, s.attached_docs
                FROM session_metadata s
                LEFT JOIN message_history m ON s.id = m.session_id
                GROUP BY s.id, s.title, s.created_at, s.updated_at, s.attached_docs
                ORDER BY s.updated_at DESC
            """)
            for r in cur.fetchall():
                sid = r[0]
                attached = r[5] if (len(r) > 5 and r[5] is not None) else []
                if isinstance(attached, str):
                    try:
                        attached = json.loads(attached)
                    except Exception:
                        attached = []
                sessions_dict[sid] = {
                    "id": sid,
                    "thread_id": sid,
                    "session_id": sid,
                    "title": r[1],
                    "created_at": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2]),
                    "updated_at": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]),
                    "message_count": int(r[4]),
                    "attached_docs": attached,
                }

            cur.execute("""
                SELECT DISTINCT ON (session_id) session_id, content
                FROM chat_messages
                WHERE role = 'user'
                ORDER BY session_id, created_at ASC
            """)
            first_user_msgs = {r[0]: r[1] for r in cur.fetchall()}

            cur.execute("""
                SELECT session_id, COUNT(id), MIN(created_at), MAX(created_at)
                FROM chat_messages
                GROUP BY session_id
                ORDER BY MAX(created_at) DESC
            """)
            for r in cur.fetchall():
                sid = r[0]
                if sid not in sessions_dict:
                    raw_title = first_user_msgs.get(sid) or f"Chat {sid[:8]}"
                    clean_t = (raw_title[:60] + "...") if len(raw_title) > 60 else raw_title
                    sessions_dict[sid] = {
                        "id": sid,
                        "thread_id": sid,
                        "session_id": sid,
                        "title": clean_t,
                        "created_at": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2]),
                        "updated_at": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]),
                        "message_count": int(r[1]),
                        "attached_docs": [],
                    }
            cur.close()
            return list(sessions_dict.values())
        except Exception as e:
            logger.error(f"Failed to list sessions from PostgreSQL: {e}")
            return list(sessions_dict.values())
        finally:
            self._release_connection(conn)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its messages across all tables.
        """
        self._memory_chat.pop(session_id, None)
        self._memory_sessions.pop(session_id, None)
        if not self.is_connected:
            return True

        conn = self._get_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM message_history WHERE session_id = %s", (session_id,))
            cur.execute("DELETE FROM session_metadata WHERE id = %s", (session_id,))
            cur.execute("DELETE FROM chat_messages WHERE session_id = %s", (session_id,))
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id} in PostgreSQL: {e}")
            return False
        finally:
            self._release_connection(conn)

    def save_feedback(
        self,
        session_id: str,
        rating: str,
        reason: Optional[str] = None,
        query: Optional[str] = None,
        message_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> bool:
        """
        Record user feedback on answer quality.
        """
        record = {
            "session_id": session_id,
            "rating": str(rating),
            "reason": reason or "",
            "query": query or "",
            "message_id": message_id or "",
            "client_ip": client_ip or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._memory_feedback.append(record)

        if not self.is_connected:
            return True

        conn = self._get_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chat_feedback (session_id, query, rating, reason, message_id, client_ip)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session_id, query, str(rating), reason, message_id, client_ip))
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save feedback in PostgreSQL: {e}")
            return False
        finally:
            self._release_connection(conn)

    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Returns aggregated thumbs_up, thumbs_down, satisfaction ratio, and total feedback count.
        """
        if not self.is_connected:
            t_up = sum(1 for f in self._memory_feedback if f.get("rating") in ("thumbs_up", "positive"))
            t_down = sum(1 for f in self._memory_feedback if f.get("rating") in ("thumbs_down", "negative"))
            total = len(self._memory_feedback)
            ratio = round(t_up / total, 3) if total > 0 else 1.0
            return {
                "thumbs_up": t_up,
                "thumbs_down": t_down,
                "satisfaction_ratio": ratio,
                "total_feedback": total,
            }

        conn = self._get_connection()
        if not conn:
            raise RuntimeError("Database connection unavailable")
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT rating, COUNT(id)
                FROM chat_feedback
                GROUP BY rating
            """)
            counts = dict(cur.fetchall())
            cur.close()
            t_up = counts.get("thumbs_up", 0) + counts.get("positive", 0)
            t_down = counts.get("thumbs_down", 0) + counts.get("negative", 0)
            total = t_up + t_down
            ratio = round(t_up / total, 3) if total > 0 else 1.0
            return {
                "thumbs_up": t_up,
                "thumbs_down": t_down,
                "satisfaction_ratio": ratio,
                "total_feedback": total,
            }
        except Exception as e:
            logger.error(f"Failed to fetch feedback stats from PostgreSQL: {e}")
            raise
        finally:
            self._release_connection(conn)

    def sync_chat_history(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        title: Optional[str] = None,
        attached_docs: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Idempotently synchronize or restore full chat history and session metadata into PostgreSQL.
        Returns count of synchronized messages.
        """
        if not session_id or not messages:
            return 0

        # Memory fallback update
        normalized_mem = []
        for m in messages:
            txt = m.get("text") or m.get("content", "")
            srcs = (
                m.get("sources")
                or m.get("citations")
                or (m.get("response", {}).get("sources", []) if isinstance(m.get("response"), dict) else [])
            )
            normalized_mem.append({
                **m,
                "role": m.get("role", "user"),
                "content": txt,
                "text": txt,
                "mode": m.get("mode", "fast"),
                "sources": srcs,
                "citations": srcs,
                "response": m.get("response") or ({"sources": srcs} if srcs else None),
                "created_at": m.get("created_at", datetime.now(timezone.utc).isoformat()),
            })
        self._memory_chat[session_id] = normalized_mem
        if attached_docs is not None:
            self._memory_sessions.setdefault(session_id, {})["attached_docs"] = attached_docs

        if not self.is_connected:
            return len(messages)

        conn = self._get_connection()
        if not conn:
            return len(messages)

        synced_count = 0
        try:
            cur = conn.cursor()
            first_user_content = next(
                (m.get("content") or m.get("text", "") for m in messages if m.get("role") == "user"),
                "Restored Session"
            )
            sess_title = title or (first_user_content[:60] + "..." if len(first_user_content) > 60 else first_user_content)
            attached_json = json.dumps(attached_docs) if attached_docs is not None else None

            # 1. Upsert session_metadata
            cur.execute("""
                INSERT INTO session_metadata (id, title, attached_docs, created_at, updated_at)
                VALUES (%s, %s, COALESCE(%s::jsonb, '[]'::jsonb), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    attached_docs = CASE WHEN %s::jsonb IS NOT NULL THEN %s::jsonb ELSE session_metadata.attached_docs END,
                    updated_at = CURRENT_TIMESTAMP;
            """, (session_id, sess_title, attached_json, attached_json, attached_json))

            for idx, msg in enumerate(messages):
                role = msg.get("role", "user")
                content = msg.get("content") or msg.get("text", "")
                if not content:
                    continue
                m_hash = hashlib.sha256(f"{session_id}:{role}:{content.strip()}".encode("utf-8")).hexdigest()
                mode = msg.get("mode", "fast")
                raw_sources = (
                    msg.get("sources")
                    or msg.get("citations")
                    or (msg.get("response", {}).get("sources", []) if isinstance(msg.get("response"), dict) else [])
                )
                raw_citations = msg.get("citations") or raw_sources
                sources_json = json.dumps(raw_sources) if isinstance(raw_sources, list) else json.dumps([])
                citations_json = json.dumps(raw_citations) if isinstance(raw_citations, list) else json.dumps([])
                dur = float(msg.get("durationSec") or msg.get("duration_sec") or 0.0)
                cur.execute("""
                    INSERT INTO chat_messages (session_id, turn_index, role, content, mode, sources, citations, duration_sec, message_hash, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (session_id, message_hash) DO NOTHING
                """, (session_id, idx, role, content, mode, sources_json, citations_json, dur, m_hash))
                try:
                    cur.execute("""
                        INSERT INTO message_history (session_id, role, content, timestamp)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    """, (session_id, role, content))
                except Exception:
                    pass
                if cur.rowcount > 0:
                    synced_count += 1

            conn.commit()
            cur.close()
            return synced_count if synced_count > 0 else len(messages)
        except Exception as e:
            logger.error(f"Failed to sync chat history for {session_id} in PostgreSQL: {e}")
            return len(messages)
        finally:
            self._release_connection(conn)



# -----------------------------------------------------------------------------
# 2. Redis Fast Response Cache Manager
# -----------------------------------------------------------------------------

PostgresDatabase = PostgresManager
