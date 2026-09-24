"""
RAISE API Routers Package.
Canonical home for all modular FastAPI endpoints.
"""
from .health import router as health_router
from .developer import router as developer_router
from .chat import router as chat_router
from .query import router as query_router
from .sessions import router as sessions_router
from .documents import router as documents_router, get_documents
from .graph import router as graph_router
from .search import router as search_router
from .agent import router as agent_router
from .system import router as system_router

__all__ = [
    "health_router",
    "developer_router",
    "chat_router",
    "query_router",
    "sessions_router",
    "documents_router",
    "get_documents",
    "graph_router",
    "search_router",
    "agent_router",
    "system_router",
]
