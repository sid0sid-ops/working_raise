"""
RAISE API Dependency Injection Providers
Extracts shared singletons from request.app.state or global singletons with safe fallbacks.
"""

from typing import Any, Optional
from fastapi import Request

_rag_engine = None
_postgres_manager = None
_redis_cache = None
_dev_operator = None
_session_memory_manager = None


def set_dependencies(
    rag_engine: Any = None,
    postgres_manager: Any = None,
    redis_cache: Any = None,
    dev_operator: Any = None,
    session_memory_manager: Any = None,
):
    """Set global singletons for direct router access and fallback resolution."""
    global _rag_engine, _postgres_manager, _redis_cache, _dev_operator, _session_memory_manager
    if rag_engine is not None:
        _rag_engine = rag_engine
    if postgres_manager is not None:
        _postgres_manager = postgres_manager
    if redis_cache is not None:
        _redis_cache = redis_cache
    if dev_operator is not None:
        _dev_operator = dev_operator
    if session_memory_manager is not None:
        _session_memory_manager = session_memory_manager


def get_rag_engine(request: Request = None) -> Any:
    if request is not None and hasattr(request, "app"):
        engine = getattr(request.app.state, "rag_engine", None)
        if engine is not None:
            return engine
    if _rag_engine is not None:
        return _rag_engine
    try:
        import app
        return getattr(app, "rag_engine", None)
    except Exception:
        return None


def get_postgres_manager(request: Request = None) -> Any:
    if request is not None and hasattr(request, "app"):
        mgr = getattr(request.app.state, "postgres_manager", None)
        if mgr is not None:
            return mgr
    if _postgres_manager is not None:
        return _postgres_manager
    try:
        import app
        return getattr(app, "postgres_manager", None)
    except Exception:
        return None


def get_redis_cache(request: Request = None) -> Any:
    if request is not None and hasattr(request, "app"):
        cache = getattr(request.app.state, "redis_cache", None)
        if cache is not None:
            return cache
    if _redis_cache is not None:
        return _redis_cache
    try:
        import app
        return getattr(app, "redis_cache", None)
    except Exception:
        return None


def get_dev_operator(request: Request = None) -> Any:
    if request is not None and hasattr(request, "app"):
        op = getattr(request.app.state, "dev_operator", None)
        if op is not None:
            return op
    if _dev_operator is not None:
        return _dev_operator
    try:
        import app
        return getattr(app, "dev_operator", None)
    except Exception:
        return None


def get_session_memory(request: Request = None) -> Any:
    if request is not None and hasattr(request, "app"):
        mem = getattr(request.app.state, "session_memory_manager", None)
        if mem is not None:
            return mem
    if _session_memory_manager is not None:
        return _session_memory_manager
    try:
        import app
        return getattr(app, "session_memory_manager", None)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Modular Monolith Service Layer Providers
# ---------------------------------------------------------------------------
_session_service = None
_document_service = None
_chat_service = None
_query_service = None


def set_service_dependencies(
    session_service: Any = None,
    document_service: Any = None,
    chat_service: Any = None,
    query_service: Any = None,
):
    global _session_service, _document_service, _chat_service, _query_service
    if session_service is not None:
        _session_service = session_service
    if document_service is not None:
        _document_service = document_service
    if chat_service is not None:
        _chat_service = chat_service
    if query_service is not None:
        _query_service = query_service


def get_session_service(request: Request = None) -> Any:
    if request is not None and hasattr(request, "app"):
        svc = getattr(request.app.state, "session_service", None)
        if svc is not None:
            return svc
    if _session_service is not None:
        return _session_service
    # Lazy instantiation fallback
    from src.features.sessions.service import SessionService
    return SessionService(
        postgres_manager=get_postgres_manager(request),
        redis_cache=get_redis_cache(request),
        session_memory_manager=get_session_memory(request),
    )


def get_document_service(request: Request = None) -> Any:
    if request is not None and hasattr(request, "app"):
        svc = getattr(request.app.state, "document_service", None)
        if svc is not None:
            return svc
    if _document_service is not None:
        return _document_service
    # Lazy instantiation fallback
    from src.features.documents.service import DocumentService
    return DocumentService(
        postgres_manager=get_postgres_manager(request),
        rag_engine=get_rag_engine(request),
    )


def get_chat_service(request: Request = None) -> Any:
    if request is not None and hasattr(request, "app"):
        svc = getattr(request.app.state, "chat_service", None)
        if svc is not None:
            return svc
    if _chat_service is not None:
        return _chat_service
    # Lazy instantiation fallback
    from src.features.chat.service import ChatService
    return ChatService(
        rag_engine=get_rag_engine(request),
        postgres_manager=get_postgres_manager(request),
        redis_cache=get_redis_cache(request),
        session_memory_manager=get_session_memory(request),
    )


def get_query_service(request: Request = None) -> Any:
    if request is not None and hasattr(request, "app"):
        svc = getattr(request.app.state, "query_service", None)
        if svc is not None:
            return svc
    if _query_service is not None:
        return _query_service
    # Lazy instantiation fallback
    from src.features.query.service import QueryService
    return QueryService(
        rag_engine=get_rag_engine(request),
        postgres_manager=get_postgres_manager(request),
        session_memory_manager=get_session_memory(request),
    )



