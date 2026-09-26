"""
PostgreSQL Storage Manager
==========================
Manages persistent relational storage for chat sessions, message histories,
document metadata, ingestion pipelines, and user feedback.

Assembled modularly from specialized mixins:
  - ChatStoreMixin: message persistence, sliding window queries, history sync
  - SessionDrawerMixin: active session document drawer attachments
  - DocumentStoreMixin: document metadata and ingestion progress tracking
  - FeedbackStoreMixin: answer quality ratings and telemetry metrics
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, List, Optional
from src.storage.interfaces import ISessionStore

from .mixins import (
    ChatStoreMixin,
    SessionDrawerMixin,
    DocumentStoreMixin,
    FeedbackStoreMixin,
)

logger = logging.getLogger("raise.infrastructure.database.postgres")

__all__ = ["PostgresManager", "PostgresDatabase"]


class PostgresManager(
    ChatStoreMixin,
    SessionDrawerMixin,
    DocumentStoreMixin,
    FeedbackStoreMixin,
    ISessionStore,
):
    """
    Manages long-term chat sessions, message logs, and document metadata in PostgreSQL.
    Falls back gracefully to memory-backed storage when PostgreSQL is unreachable.
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


PostgresDatabase = PostgresManager
