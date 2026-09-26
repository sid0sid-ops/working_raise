"""
Postgres Session Drawer Mixin
=============================
Handles attaching, detaching, and querying workspace documents bound to active chat sessions.
"""

from __future__ import annotations

import json
import logging
from typing import List

logger = logging.getLogger("raise.infrastructure.database.postgres.drawer")


class SessionDrawerMixin:
    """Provides methods for managing drawer-attached documents in PostgreSQL."""

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
