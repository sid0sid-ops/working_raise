"""
Postgres Chat Store Mixin
=========================
Handles chat message persistence, chronological window queries, session listing,
deletion, and idempotent chat history synchronization in PostgreSQL.
"""

from __future__ import annotations

import json
import hashlib
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("raise.infrastructure.database.postgres.chat")


class ChatStoreMixin:
    """Provides methods for chat messaging and session persistence in PostgreSQL."""

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
