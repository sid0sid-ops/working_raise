"""
RAISE Local ChromaDB Vector Store Engine — Layer A: Dense Embedding
===================================================================
Manages persistent local ChromaDB indexing, embeddings, and cosine similarity retrieval.

Architectural Guarantees & Modular Assembly:
--------------------------------------------
Composed modularly from specialized mixins:
  - VectorEmbeddingsMixin: SentenceTransformer model loading, dense vector encoding, dimension verification
  - VectorIngestionMixin: Production chunk ingestion, proposition indexing, and benchmark test isolation
  - VectorSearchMixin: Dense cosine similarity search, workspace filtering, intent-aware candidate boosting
  - VectorLifecycleMixin: Granular document vector deletion, collection reset, and IVectorStore contracts

Tripartite Collection Naming Convention:
----------------------------------------
All ChromaDB collections follow the tripartite formula:
  `{dataset_slug}_{parser_slug}_{model_slug}`
Examples:
  - `raise_docling_bge_large` (Production RAISE academic index)
  - `bric_pymupdf_minilm` (Benchmark/experimental index)

How to Update or Extend:
------------------------
- To adjust embedding models or device routing, see `mixins/embeddings_mixin.py`.
- To modify chunk ingestion or benchmark isolation rules, see `mixins/ingestion_mixin.py`.
- To tune retrieval heuristics and intent boosting weights, see `mixins/search_mixin.py`.
- To adjust document purging and collection lifecycle, see `mixins/lifecycle_mixin.py`.
"""

from __future__ import annotations

import os
import re
import warnings
import threading
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.storage.interfaces import IVectorStore

from .mixins import (
    VectorEmbeddingsMixin,
    VectorIngestionMixin,
    VectorSearchMixin,
    VectorLifecycleMixin,
    should_ingest,
)

# Auto-load .env variables if not already loaded
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
    else:
        load_dotenv()
except Exception:
    pass

# Suppress telemetry noise while allowing authenticated HF Hub requests
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")
warnings.filterwarnings("ignore", message=".*unauthenticated requests.*")

try:
    import huggingface_hub
    huggingface_hub.utils.logging.set_verbosity_error()
except Exception:
    pass

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

# Suppress ChromaDB internal telemetry and initialization notice logging
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
logging.getLogger("chromadb.api.client").setLevel(logging.ERROR)

SHARED_CHROMA_SETTINGS = Settings(
    anonymized_telemetry=False,
    is_persistent=True,
    allow_reset=True,
) if HAS_CHROMADB else None

_GLOBAL_CHROMA_CLIENTS: Dict[str, Any] = {}
_CHROMA_INIT_LOCK = threading.Lock()


def get_shared_chroma_client(persist_directory: str | Path) -> Any:
    """Returns a single canonical ChromaDB client per path with identical settings."""
    if not HAS_CHROMADB:
        return None
    norm_path = str(Path(persist_directory).resolve())
    with _CHROMA_INIT_LOCK:
        if norm_path not in _GLOBAL_CHROMA_CLIENTS:
            try:
                _GLOBAL_CHROMA_CLIENTS[norm_path] = chromadb.PersistentClient(
                    path=norm_path,
                    settings=SHARED_CHROMA_SETTINGS,
                )
            except Exception:
                try:
                    from chromadb.api.client import SharedSystemClient
                    for _, sys_client in getattr(SharedSystemClient, "_instances", {}).items():
                        _GLOBAL_CHROMA_CLIENTS[norm_path] = sys_client
                        break
                    if norm_path not in _GLOBAL_CHROMA_CLIENTS:
                        _GLOBAL_CHROMA_CLIENTS[norm_path] = chromadb.PersistentClient(path=norm_path)
                except Exception:
                    pass
        return _GLOBAL_CHROMA_CLIENTS.get(norm_path)


try:
    from src.core.config import settings
except Exception:
    settings = None


class LocalVectorEngine(
    VectorEmbeddingsMixin,
    VectorIngestionMixin,
    VectorSearchMixin,
    VectorLifecycleMixin,
    IVectorStore,
):
    """
    Manages persistent local ChromaDB indexing, embeddings, and cosine similarity retrieval.
    Assembled modularly from specialized mixins for embeddings, ingestion, search, and lifecycle.
    """

    @staticmethod
    def format_collection_name(
        dataset: str,
        parser: str = "docling",
        embedding_model: str = "bge_large",
    ) -> str:
        """
        Enforces Standardized Tripartite ChromaDB Collection Naming:
        Formula: {dataset_slug}_{parser_slug}_{model_slug}

        Examples:
          - ("raise", "docling", "bge-large-en-v1.5") -> "raise_docling_bge_large"
          - ("bric", "pymupdf", "all-MiniLM-L6-v2")    -> "bric_pymupdf_minilm"
        """
        def _slugify(val: str) -> str:
            if not val:
                return ""
            s = str(val).split("/")[-1].split("\\")[-1]
            s = re.sub(r"[^a-zA-Z0-9]+", "_", s.strip().lower())
            return s.strip("_")

        dataset_slug = _slugify(dataset) or "default"
        parser_slug = _slugify(parser) or "docling"

        raw_model = _slugify(embedding_model) or "bge_large"
        if "bge_large" in raw_model:
            model_slug = "bge_large"
        elif "bge_m3" in raw_model:
            model_slug = "bge_m3"
        elif "minilm" in raw_model:
            model_slug = "minilm"
        elif "qwen" in raw_model:
            model_slug = "qwen"
        else:
            model_slug = raw_model

        return f"{dataset_slug}_{parser_slug}_{model_slug}"

    @staticmethod
    def parse_collection_name(name: str) -> Dict[str, str]:
        """
        Deconstructs a tripartite collection name into its constituent segments:
        Returns: {'dataset': ..., 'parser': ..., 'embedding_model': ...}
        """
        if not name:
            return {"dataset": "default", "parser": "docling", "embedding_model": "bge_large"}
        parts = name.split("_")
        if len(parts) >= 3:
            return {
                "dataset": parts[0],
                "parser": parts[1],
                "embedding_model": "_".join(parts[2:]),
            }
        elif len(parts) == 2:
            return {
                "dataset": parts[0],
                "parser": parts[1],
                "embedding_model": "bge_large",
            }
        return {"dataset": name, "parser": "unknown", "embedding_model": "unknown"}

    def __init__(
        self,
        persist_directory: Optional[Path | str] = None,
        collection_name: Optional[str] = None,
        dataset: Optional[str] = None,
        parser: Optional[str] = None,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ):
        if settings:
            default_dir = settings.vector.persist_directory
            default_coll = settings.vector.collection_name
            default_model = settings.vector.embedding_model
        else:
            default_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", str(Path(__file__).resolve().parents[3] / ".chromadb_bge_large"))
            default_coll = os.getenv("CHROMA_COLLECTION_NAME", "raise_docling_bge_large")
            default_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")

        self.persist_dir = Path(persist_directory or default_dir).resolve()
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        resolved_model = model_name or default_model
        self.model_key = resolved_model
        self.model_path = self.AVAILABLE_MODELS.get(resolved_model, resolved_model)
        self.device_override = device or os.getenv("RAISE_EMBEDDING_DEVICE")

        # Systematic Tripartite Naming Convention:
        if dataset:
            self.collection_name = self.format_collection_name(
                dataset=dataset,
                parser=parser or "docling",
                embedding_model=resolved_model,
            )
        else:
            self.collection_name = collection_name or default_coll

        self.client = None
        self.collection = None
        self.embed_model = None
        self._init_db()

    def switch_collection(
        self,
        collection_name: Optional[str] = None,
        dataset: Optional[str] = None,
        parser: Optional[str] = None,
    ) -> Any:
        """Switch active collection dynamically following the tripartite naming convention."""
        if dataset:
            target_name = self.format_collection_name(
                dataset=dataset,
                parser=parser or "docling",
                embedding_model=self.model_key,
            )
        elif collection_name:
            target_name = collection_name
        else:
            return self._get_collection()

        self.collection_name = target_name
        if HAS_CHROMADB:
            if getattr(self, "client", None) is None:
                self._init_db()
            if getattr(self, "client", None) is not None:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
        return getattr(self, "collection", None)

    def _get_collection(self):
        """Retrieve valid collection handle, refreshing if stale or invalidated."""
        if not HAS_CHROMADB:
            return None
        try:
            if getattr(self, "client", None) is None:
                self._init_db()
            if getattr(self, "collection", None) is not None:
                try:
                    self.collection.count()
                    return self.collection
                except Exception:
                    pass
            if getattr(self, "client", None) is not None:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
        except Exception as e:
            print(f"ChromaDB collection refresh notice: {e}")
        return getattr(self, "collection", None)

    def count(self) -> int:
        """Return the count of vector items in ChromaDB collection with self-healing recovery."""
        col = self._get_collection()
        if col is not None:
            try:
                return col.count()
            except Exception:
                return 0
        return 0

    def _init_db(self):
        if not HAS_CHROMADB:
            return

        try:
            self.client = get_shared_chroma_client(self.persist_dir)
            if self.client:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
        except Exception:
            pass


DenseVectorEngine = LocalVectorEngine
ChromaVectorStore = LocalVectorEngine
ChromaDBEngine = LocalVectorEngine

__all__ = [
    "LocalVectorEngine",
    "DenseVectorEngine",
    "ChromaVectorStore",
    "ChromaDBEngine",
    "get_shared_chroma_client",
    "should_ingest",
]
