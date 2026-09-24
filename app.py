"""
RAISE Master Agentic GraphRAG Studio Application
Modular Monolith API Shell.

Routes and domain logic are organized into dedicated routers:
  - routers.health: System liveness and multi-database health diagnostics
  - routers.developer: DeveloperOperator tooling, cache invalidation, audit telemetry
  - routers.chat: Conversational reasoning, SSE streaming, cancellation, feedback
  - routers.query: Headless network query pipeline, streaming, suggestions
  - routers.sessions: Session lifecycle, message trajectory, drawer synchronization
  - routers.documents: PDF upload, parsing, batch ingestion, status SSE, deletion
  - routers.graph: Neo4j Property Graph and NetworkX visualization, search, cypher
  - routers.search: Dense vector search across indexed chunks
  - routers.agent: Autonomous multi-tool agentic reasoning
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional

# Auto-load .env variables
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
    else:
        load_dotenv()
except Exception:
    pass

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_VERBOSITY"] = "error"

# UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.infrastructure.database.postgres import PostgresManager
from src.infrastructure.cache.redis import RedisCacheManager
from src.features.sessions import SessionMemoryManager, SessionService
from src.features.system import DeveloperOperator
from src.retrieval import StandaloneRAGPipeline
from src.features.query import QueryService
from src.features.documents import DocumentService
from src.features.chat import ChatService

from src.api.context import (
    ACTIVE_ABORTS,
    DOCUMENTS_DIR,
    DOWNLOAD_DIR,
    MANIFEST_FILE,
    _parse_drawer_active_docs,
    get_authentic_client_ip,
    get_lan_ip,
    get_library_documents,
    get_ready_documents_list,
    is_aborted,
    is_conversational_or_memory_query,
    purge_all_ready_documents,
    record_abort,
    record_query_metric,
    record_ready_document,
    remove_ready_document,
)
from src.api.dependencies import set_dependencies
from src.api.schemas import (
    AbortRequest,
    BatchChatRequest,
    ChatHistorySyncRequest,
    ChatMessageRequest,
    FeedbackRequest,
    QueryRequest,
)

from src.api.routers import (
    agent_router,
    chat_router,
    developer_router,
    documents_router,
    graph_router,
    health_router,
    query_router,
    search_router,
    sessions_router,
)
from src.api.routers.documents import get_documents

logger = logging.getLogger("raise.app")

# ---------------------------------------------------------------------------
# Core Subsystems Singletons
# ---------------------------------------------------------------------------
postgres_manager = PostgresManager()
redis_cache = RedisCacheManager()
session_memory_manager = SessionMemoryManager()

rag_engine = StandaloneRAGPipeline()
rag_engine.session_manager = session_memory_manager
if hasattr(rag_engine, "langgraph_workflow") and hasattr(rag_engine.langgraph_workflow, "intake_engine"):
    rag_engine.langgraph_workflow.intake_engine.session_manager = session_memory_manager
    rag_engine.langgraph_workflow.intake_engine.coref.session_manager = session_memory_manager

dev_operator = DeveloperOperator(
    postgres_mgr=postgres_manager,
    redis_mgr=redis_cache,
    neo4j_db=rag_engine.neo4j_db,
    vector_engine=rag_engine.vector_engine,
)


# Instantiate Modular Feature Services
from src.api.dependencies import set_service_dependencies

session_service = SessionService(
    postgres_manager=postgres_manager,
    redis_cache=redis_cache,
    session_memory_manager=session_memory_manager,
)
document_service = DocumentService(
    postgres_manager=postgres_manager,
    rag_engine=rag_engine,
    documents_dir=DOCUMENTS_DIR,
)
chat_service = ChatService(
    rag_engine=rag_engine,
    postgres_manager=postgres_manager,
    redis_cache=redis_cache,
    session_memory_manager=session_memory_manager,
)
query_service = QueryService(
    rag_engine=rag_engine,
    postgres_manager=postgres_manager,
    session_memory_manager=session_memory_manager,
)

# Register singletons into shared dependency injection registry
set_dependencies(
    rag_engine=rag_engine,
    postgres_manager=postgres_manager,
    redis_cache=redis_cache,
    dev_operator=dev_operator,
    session_memory_manager=session_memory_manager,
)
set_service_dependencies(
    session_service=session_service,
    document_service=document_service,
    chat_service=chat_service,
    query_service=query_service,
)



# ---------------------------------------------------------------------------
# Background Listeners & Lifespan
# ---------------------------------------------------------------------------
async def _abort_pubsub_listener():
    """Background listener for cross-worker Redis Pub/Sub abort channel."""
    if not redis_cache.is_connected or not redis_cache._client:
        return
    try:
        pubsub = redis_cache._client.pubsub()
        pubsub.subscribe("channel:chat:abort")
        loop = asyncio.get_running_loop()
        while True:
            msg = await loop.run_in_executor(None, lambda: pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0))
            if msg and msg.get("type") == "message":
                try:
                    raw_d = msg["data"].decode("utf-8") if isinstance(msg["data"], bytes) else msg["data"]
                    data = json.loads(raw_d)
                    sid = data.get("session_id")
                    rid = data.get("request_id")
                    if sid:
                        ACTIVE_ABORTS.add(sid)
                    if rid:
                        ACTIVE_ABORTS.add(rid)
                except Exception:
                    pass
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.debug(f"Abort pubsub listener notice: {e}")


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # 1. Background pub/sub abort listener
    abort_task = asyncio.create_task(_abort_pubsub_listener())

    # 2. Auto-synchronize pending documents from disk in background thread
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, dev_operator.auto_synchronize_pending_documents)
    except Exception as exc:
        logger.warning(f"Startup document synchronization notice: {exc}")

    yield

    # Shutdown
    abort_task.cancel()
    try:
        await abort_task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# FastAPI Application Construction
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RAISE (Research Assessment Intelligence & Semantic Extraction) Backend API",
    version="2.5.0",
    description="Research Assessment Intelligence & Semantic Extraction — Multi-PDF GraphRAG, Subgraph Retrieval & Anti-Hallucination Claim Verification",
    lifespan=lifespan,
)

# Attach singletons to app.state for router dependency access and gateway forwarding
app.state.rag_engine = rag_engine
app.state.postgres_manager = postgres_manager
app.state.redis_cache = redis_cache
app.state.session_memory_manager = session_memory_manager
app.state.dev_operator = dev_operator
app.state.session_service = session_service
app.state.document_service = document_service
app.state.chat_service = chat_service
app.state.query_service = query_service



# ---------------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0].get("msg", "Validation error") if errors else "Invalid request payload"
    field = ".".join([str(loc) for loc in errors[0].get("loc", [])]) if errors else "body"
    return JSONResponse(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"{field}: {msg}",
                "details": errors,
            }
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": detail,
            }
        },
        headers=getattr(exc, "headers", None) or {}
    )


# ---------------------------------------------------------------------------
# Cross-Device CORS Configuration
# ---------------------------------------------------------------------------
_cors_env = os.getenv("CORS_ORIGINS") or os.getenv("CORS_ALLOWED_ORIGINS", "")
_configured_origins = _cors_env.split(",") if _cors_env else []
ALLOWED_ORIGINS = [o.strip() for o in _configured_origins if o.strip()]
DEFAULT_ORIGINS = [
    "https://semanticclimate.github.io",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://localhost:8080",
]
for o in DEFAULT_ORIGINS:
    if o not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https:\/\/.*\.github\.io$|^https:\/\/.*\.trycloudflare\.com$|^https:\/\/.*\.workers\.dev$|^http:\/\/localhost:\d+$|^http:\/\/127\.0\.0\.1:\d+$|^http:\/\/(?:192\.168|10|172\.(?:1[6-9]|2[0-9]|3[01]))\.\d+\.\d+(?::\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Redis-Cache", "X-RateLimit-Remaining", "X-Process-Time-Ms", "X-Request-ID", "Accept-Ranges", "Content-Disposition", "Content-Range"],
)


# ---------------------------------------------------------------------------
# Mount Domain Routers
# ---------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(developer_router)
app.include_router(chat_router)
app.include_router(query_router)
app.include_router(sessions_router)
app.include_router(documents_router)
app.include_router(graph_router)
app.include_router(search_router)
app.include_router(agent_router)


# ---------------------------------------------------------------------------
# CLI / Server Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    host = getattr(settings.server, "host", "0.0.0.0")
    port = getattr(settings.server, "port", 8000)
    lan_ip = get_lan_ip()
    print("=" * 70)
    print(f" 🚀 STARTING RAISE GRAPHRAG STUDIO ON PORT {port}")
    print(f" • Local Host     : http://127.0.0.1:{port}")
    print(f" • Remote LAN Host: http://{lan_ip}:{port} (Mac Frontend Access)")
    print("=" * 70)
    uvicorn.run(app, host=host, port=port, log_level="info")
