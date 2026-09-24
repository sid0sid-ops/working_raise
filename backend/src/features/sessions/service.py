"""
Session and Conversational Memory Service.
Encapsulates PostgreSQL and Redis session lifecycle, sliding window history,
persona variables, and session drawer document attachments.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.api.context import _parse_drawer_active_docs, get_library_documents
from src.features.memory.engine import SessionMemoryManager

logger = logging.getLogger("raise.services.session")


class SessionService:
    def __init__(
        self,
        postgres_manager: Any = None,
        redis_cache: Any = None,
        session_memory_manager: Any = None,
    ):
        self.postgres_manager = postgres_manager
        self.redis_cache = redis_cache
        self.session_memory_manager = session_memory_manager

    def get_chat_history(self, session_id: str, limit: int = 50) -> Dict[str, Any]:
        """Retrieve persistent chronological message turns, checking Redis first then PostgreSQL."""
        target_id = session_id or "default"

        # 1. Check Redis Cache
        if self.redis_cache:
            try:
                cached = self.redis_cache.get_session_messages(target_id, limit=limit)
                if cached:
                    return {
                        "id": target_id,
                        "session_id": target_id,
                        "thread_id": target_id,
                        "messages": cached,
                        "total_count": len(cached),
                        "cached": True,
                    }
            except Exception as _re:
                logger.debug(f"Redis cache lookup bypassed: {_re}")

        # 2. Authoritative PostgreSQL retrieval
        messages = self.postgres_manager.get_messages(target_id, limit=limit) if self.postgres_manager else []

        # 3. Backfill Redis Cache
        if messages and self.redis_cache:
            try:
                for t in messages:
                    self.redis_cache.save_session_message(
                        target_id,
                        t.get("role", "user"),
                        t.get("content", ""),
                        mode=t.get("mode", "fast"),
                        sources=t.get("sources", []),
                    )
            except Exception as _re:
                pass

        return {
            "id": target_id,
            "session_id": target_id,
            "thread_id": target_id,
            "messages": messages,
            "total_count": len(messages),
            "cached": False,
        }

    def sync_chat_history(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        title: Optional[str] = None,
        attached_docs: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Idempotently synchronize or save client session history into PostgreSQL."""
        target_id = session_id or "default"
        synced = 0
        if self.postgres_manager:
            synced = self.postgres_manager.sync_chat_history(
                session_id=target_id,
                messages=messages,
                title=title,
                attached_docs=attached_docs,
                preferences=preferences,
            )
        return {
            "status": "synchronized",
            "id": target_id,
            "session_id": target_id,
            "thread_id": target_id,
            "synced_count": synced,
            "total_messages": len(messages),
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all chat sessions from PostgreSQL."""
        if self.postgres_manager:
            return self.postgres_manager.list_all_sessions()
        return []

    def delete_session(self, thread_id: str) -> Dict[str, str]:
        """Delete a session from PostgreSQL, Redis cache, and memory."""
        if self.postgres_manager:
            self.postgres_manager.delete_session(thread_id)
        if self.session_memory_manager and hasattr(self.session_memory_manager, "_threads"):
            self.session_memory_manager._threads.pop(thread_id, None)
        return {"status": "deleted", "thread_id": thread_id}

    def get_session_drawer(self, session_id: str) -> Dict[str, Any]:
        """Returns the list of attached documents for a session drawer with metadata."""
        raw_attached = self.postgres_manager.get_session_drawer(session_id) if self.postgres_manager else []
        cleaned_attached = _parse_drawer_active_docs(raw_attached) or []

        all_docs = get_library_documents(self.postgres_manager).get("documents", [])
        doc_map = {d.get("filename"): d for d in all_docs}
        for d in all_docs:
            if d.get("id"):
                doc_map[d.get("id")] = d
            if d.get("doc_id"):
                doc_map[d.get("doc_id")] = d

        enriched_docs = []
        for item in cleaned_attached:
            matched = doc_map.get(item)
            if matched:
                enriched_docs.append(matched)
            else:
                clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(item).stem)[:40]
                enriched_docs.append({
                    "id": f"doc_{clean_stem}",
                    "doc_id": f"doc_{clean_stem}",
                    "filename": item,
                    "status": "ready",
                    "phase": "ready",
                    "is_protected": False,
                    "can_delete": True,
                    "deletable": True,
                    "owner": "user",
                    "library": "default",
                })

        return {
            "status": "success",
            "session_id": session_id,
            "attached_docs": cleaned_attached,
            "active_docs": cleaned_attached,
            "documents": enriched_docs,
            "count": len(cleaned_attached),
        }

    def attach_document_to_drawer(self, session_id: str, target: str) -> Dict[str, Any]:
        """Idempotently attaches a Library document to the session's drawer."""
        all_docs = get_library_documents(self.postgres_manager).get("documents", [])
        resolved_filename = target
        for d in all_docs:
            if d.get("id") == target or d.get("doc_id") == target:
                resolved_filename = d.get("filename", target)
                break

        updated = self.postgres_manager.attach_to_session_drawer(session_id, resolved_filename) if self.postgres_manager else []
        logger.info(f"[DRAWER] Attached document '{resolved_filename}' to session '{session_id}' (new count: {len(updated)})")
        return {
            "status": "success",
            "action": "attach",
            "session_id": session_id,
            "attached_document": resolved_filename,
            "attached_docs": updated,
            "active_docs": updated,
            "count": len(updated),
        }

    def remove_document_from_drawer(self, session_id: str, target: str) -> Dict[str, Any]:
        """Removes a document from the session drawer (without deleting from Library)."""
        all_docs = get_library_documents(self.postgres_manager).get("documents", [])
        resolved_filename = target
        for d in all_docs:
            if d.get("id") == target or d.get("doc_id") == target:
                resolved_filename = d.get("filename", target)
                break

        updated = self.postgres_manager.remove_from_session_drawer(session_id, resolved_filename) if self.postgres_manager else []
        logger.info(f"[DRAWER] Removed document '{resolved_filename}' from session '{session_id}' (remaining count: {len(updated)})")
        return {
            "status": "success",
            "action": "remove",
            "session_id": session_id,
            "removed_document": resolved_filename,
            "attached_docs": updated,
            "active_docs": updated,
            "count": len(updated),
        }

    def update_session_drawer(self, session_id: str, active_docs: List[str]) -> Dict[str, Any]:
        """Replaces the session drawer document list."""
        all_docs = get_library_documents(self.postgres_manager).get("documents", [])
        doc_lookup = {}
        for d in all_docs:
            if d.get("id"):
                doc_lookup[d.get("id")] = d.get("filename")
            if d.get("doc_id"):
                doc_lookup[d.get("doc_id")] = d.get("filename")
            if d.get("filename"):
                doc_lookup[d.get("filename")] = d.get("filename")

        resolved_list = []
        for item in active_docs:
            res = doc_lookup.get(item, item)
            if res and res not in resolved_list:
                resolved_list.append(res)

        updated = self.postgres_manager.update_session_drawer(session_id, resolved_list) if self.postgres_manager else []
        return {
            "status": "success",
            "session_id": session_id,
            "attached_docs": updated,
            "active_docs": updated,
            "count": len(updated),
        }

