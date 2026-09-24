"""
Unified Storage & Persistence Interfaces for RAISE.
Defines abstract contracts for SessionStore, CacheStore, VectorStore, and GraphStore,
decoupling business services from concrete database clients (PostgreSQL, Redis, Chroma, Neo4j).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class ISessionStore(ABC):
    """Abstract interface for session metadata, message history, and drawer attachments."""

    @abstractmethod
    def get_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        mode: str = "fast",
        sources: Optional[List[Any]] = None,
        active_docs: Optional[List[str]] = None,
    ) -> bool:
        pass

    @abstractmethod
    def sync_chat_history(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        title: Optional[str] = None,
    ) -> int:
        pass

    @abstractmethod
    def list_all_sessions(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        pass

    @abstractmethod
    def get_session_drawer(self, session_id: str) -> List[str]:
        pass

    @abstractmethod
    def attach_to_session_drawer(self, session_id: str, filename: str) -> List[str]:
        pass

    @abstractmethod
    def remove_from_session_drawer(self, session_id: str, filename: str) -> List[str]:
        pass

    @abstractmethod
    def update_session_drawer(self, session_id: str, active_docs: List[str]) -> List[str]:
        pass


class ICacheStore(ABC):
    """Abstract interface for fast ephemeral caching, rate limiting, and session memory."""

    @abstractmethod
    def check_rate_limit(self, client_ip: str) -> Tuple[bool, int]:
        pass

    @abstractmethod
    def semantic_get(
        self,
        query: str,
        mode: str = "fast",
        embedding: Optional[List[float]] = None,
        threshold: float = 0.95,
        library: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def semantic_set(
        self,
        query: str,
        data: Dict[str, Any],
        mode: str = "fast",
        embedding: Optional[List[float]] = None,
        ttl_seconds: int = 86400,
        library: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
    ) -> bool:
        pass

    @abstractmethod
    def get_session_memory(self, session_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def set_session_memory(self, session_id: str, key: str, value: Any) -> bool:
        pass


class IVectorStore(ABC):
    """Abstract interface for dense chunk vector indexing and semantic retrieval."""

    @abstractmethod
    def compute_embeddings(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def ingest_chunks(self, chunks: List[Dict[str, Any]], doc_id: str) -> int:
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 4,
        document_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def purge_document_vectors(self, doc_id: str) -> int:
        pass


class IGraphStore(ABC):
    """Abstract interface for Property Graph traversal, neighborhood search, and schema validation."""

    @abstractmethod
    def sync_graph_data(self, graph_data: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def query_neighborhood(
        self,
        entity_ids: List[str],
        hops: int = 1,
        limit: int = 25,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def purge_document_nodes(self, doc_id: str) -> Dict[str, int]:
        pass

