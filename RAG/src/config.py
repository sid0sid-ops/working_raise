"""
RAISE GraphRAG — Centralized Typed Configuration System
Provides unified, validated settings for Neo4j, Vector DB, LLM backends (Ollama / HuggingFace),
and LangGraph pipeline state orchestration.
Loads from .env, environment variables, or sensible offline defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, Field


# Base canonical paths inside RAG
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # .../RAG
DATA_DIR = PROJECT_ROOT / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
PROCESSED_DIR = DATA_DIR / "processed"
CHUNKS_DIR = PROCESSED_DIR / "chunks"
GRAPH_DIR = PROCESSED_DIR / "graph_triples"
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
VECTOR_DB_DIR = RUNTIME_DIR / ".chromadb"
UPLOAD_DIR = DOCUMENTS_DIR
AUDIO_DIR = RUNTIME_DIR / "audio"
LOG_DIR = PROJECT_ROOT / "logs"
TESTS_DIR = PROJECT_ROOT / "tests"
FIXTURES_DIR = TESTS_DIR / "fixtures"

# Ensure directories exist
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


class Neo4jConfig(BaseModel):
    """Neo4j Graph Database Configuration."""
    uri: str = Field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user: str = Field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    password: str = Field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password123"))
    database: str = Field(default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"))
    max_connection_lifetime: int = Field(default_factory=lambda: int(os.getenv("NEO4J_MAX_CONNECTION_LIFETIME", "3600")))
    max_connection_pool_size: int = Field(default_factory=lambda: int(os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "50")))
    connection_timeout: float = Field(default_factory=lambda: float(os.getenv("NEO4J_CONNECTION_TIMEOUT", "5.0")))


class VectorConfig(BaseModel):
    """Local ChromaDB Vector Index & Embedding Configuration."""
    persist_directory: Path = Field(default_factory=lambda: Path(os.getenv("CHROMA_PERSIST_DIRECTORY", str(VECTOR_DB_DIR))))
    collection_name: str = Field(default_factory=lambda: os.getenv("CHROMA_COLLECTION_NAME", "raise_graphrag_chunks"))
    embedding_model: str = Field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    embedding_device: str = Field(default_factory=lambda: os.getenv("EMBEDDING_DEVICE", "cpu"))
    embedding_dimension: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_DIMENSION", "384")))
    hnsw_space: str = Field(default_factory=lambda: os.getenv("CHROMA_HNSW_SPACE", "cosine"))


class LLMConfig(BaseModel):
    """Local & Remote Large Language Model Configuration."""
    backend: Literal["ollama", "huggingface", "openai-compatible"] = Field(
        default_factory=lambda: os.getenv("LLM_BACKEND", "ollama")  # type: ignore
    )
    model_name: str = Field(default_factory=lambda: os.getenv("LLM_MODEL_NAME", "qwen2.5:7b"))
    base_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    temperature: float = Field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.1")))
    max_tokens: int = Field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "1024")))
    top_p: float = Field(default_factory=lambda: float(os.getenv("LLM_TOP_P", "0.9")))
    request_timeout: float = Field(default_factory=lambda: float(os.getenv("LLM_REQUEST_TIMEOUT", "60.0")))


class LangGraphConfig(BaseModel):
    """LangGraph StateGraph Execution Parameters."""
    default_hops: int = Field(default_factory=lambda: int(os.getenv("GRAPHRAG_DEFAULT_HOPS", "2")))
    max_hops: int = Field(default_factory=lambda: int(os.getenv("GRAPHRAG_MAX_HOPS", "3")))
    default_top_k: int = Field(default_factory=lambda: int(os.getenv("GRAPHRAG_DEFAULT_TOP_K", "4")))
    max_nodes: int = Field(default_factory=lambda: int(os.getenv("GRAPHRAG_MAX_NODES", "35")))
    max_retries: int = Field(default_factory=lambda: int(os.getenv("LANGGRAPH_MAX_RETRIES", "1")))
    trace_level: str = Field(default_factory=lambda: os.getenv("LANGGRAPH_TRACE_LEVEL", "DEBUG"))


class ServerConfig(BaseModel):
    """FastAPI Application Server Configuration."""
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    reload: bool = Field(default_factory=lambda: os.getenv("RELOAD", "false").lower() in ("true", "1"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "info"))


class Settings(BaseModel):
    """Unified Settings Root."""
    app_name: str = "RAISE Academic GraphRAG Studio"
    version: str = "1.0.0"
    project_root: Path = PROJECT_ROOT
    base_dir: Path = PROJECT_ROOT
    rag_dir: Path = PROJECT_ROOT
    data_dir: Path = DATA_DIR
    documents_dir: Path = DOCUMENTS_DIR
    processed_dir: Path = PROCESSED_DIR
    chunks_dir: Path = CHUNKS_DIR
    graph_dir: Path = GRAPH_DIR
    vector_db_dir: Path = VECTOR_DB_DIR
    upload_dir: Path = UPLOAD_DIR
    audio_dir: Path = AUDIO_DIR
    log_dir: Path = LOG_DIR
    fixtures_dir: Path = FIXTURES_DIR
    download_dir: Path = DOCUMENTS_DIR  # Backward-compatible alias pointing to canonical documents_dir
    
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    vector: VectorConfig = Field(default_factory=VectorConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    langgraph: LangGraphConfig = Field(default_factory=LangGraphConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)


# Load environment variables from .env if present
def _load_env_file():
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        env_file = PROJECT_ROOT.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k not in os.environ:
                        os.environ[k] = v.strip("\"'")
        except Exception:
            pass


_load_env_file()
settings = Settings()
