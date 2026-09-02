"""
RAISE Local ChromaDB Vector Store Engine
Supports multi-model local embeddings:
1. sentence-transformers/all-MiniLM-L6-v2 (Baseline Tiny / Pre-cached offline)
2. BAAI/bge-m3 (SOTA Multilingual / Dense+Sparse)
3. Qwen/Qwen3-Embedding-4B / Qwen2.5-Coder (Best Practical GraphRAG Quality)
"""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

# Suppress unauthenticated HF Hub warning and telemetry noise
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
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

try:
    from .config import settings
except Exception:
    settings = None


class LocalVectorEngine:
    """
    Manages persistent local ChromaDB indexing, embeddings, and cosine similarity retrieval.
    """

    AVAILABLE_MODELS = {
        "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
        "bge-m3": "BAAI/bge-m3",
        "qwen-embedding-4b": "Qwen/Qwen3-Embedding-4B",
    }

    def __init__(
        self,
        persist_directory: Optional[Path | str] = None,
        collection_name: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        if settings:
            default_dir = settings.vector.persist_directory
            default_coll = settings.vector.collection_name
            default_model = settings.vector.embedding_model
        else:
            default_dir = Path(__file__).parent.parent / ".chromadb"
            default_coll = "raise_graphrag_chunks"
            default_model = "all-MiniLM-L6-v2"

        self.persist_dir = Path(persist_directory or default_dir).resolve()
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name or default_coll
        resolved_model = model_name or default_model
        self.model_key = resolved_model
        self.model_path = self.AVAILABLE_MODELS.get(resolved_model, resolved_model)
        
        self.client = None
        self.collection = None
        self.embed_model = None
        self._init_db()

    def _init_db(self):
        if not HAS_CHROMADB:
            return

        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            print(f"ChromaDB initialization notice: {e}")

    def _get_embedding_model(self):
        if self.embed_model is None:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=".*unauthenticated requests.*")
                    warnings.filterwarnings("ignore", category=UserWarning)
                    from sentence_transformers import SentenceTransformer
                    cache_folder = os.getenv("HF_HOME", str(Path.home() / ".cache" / "huggingface" / "hub"))
                    try:
                        self.embed_model = SentenceTransformer(
                            self.model_path,
                            cache_folder=cache_folder,
                            local_files_only=True
                        )
                    except Exception:
                        self.embed_model = SentenceTransformer(self.model_path, cache_folder=cache_folder)
            except Exception as e:
                print(f"SentenceTransformer fallback notice: {e}")
                self.embed_model = None
        return self.embed_model

    def compute_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Compute dense vector embeddings locally."""
        model = self._get_embedding_model()
        if model is not None:
            try:
                embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return embeddings.tolist()
            except Exception:
                pass

        # Deterministic offline fallback embedding vector (384-dim)
        fallback_vecs = []
        for t in texts:
            import hashlib
            seed = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16)
            import random
            rng = random.Random(seed)
            vec = [rng.gauss(0, 1) for _ in range(384)]
            # normalize
            norm = sum(x**2 for x in vec) ** 0.5 or 1.0
            fallback_vecs.append([x / norm for x in vec])
        return fallback_vecs

    def ingest_chunks(self, chunks: List[Dict[str, Any]], doc_id: str = "default") -> int:
        """
        Add context-enriched document chunks into ChromaDB collection with full provenance metadata.
        """
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []

        for idx, chunk in enumerate(chunks):
            cid = str(chunk.get("chunk_id") or f"{doc_id}_chk_{idx}")
            plain_text = chunk.get("plain_text") or chunk.get("text") or ""
            enriched_text = chunk.get("enriched_text") or plain_text
            
            if not plain_text.strip():
                continue

            ids.append(cid)
            documents.append(enriched_text)
            metadatas.append({
                "chunk_id": cid,
                "doc_id": doc_id,
                "pdf_filename": str(chunk.get("pdf_filename", doc_id)),
                "university": str(chunk.get("university", "Institution")),
                "heading": str(chunk.get("heading", f"Section {idx+1}")),
                "primary_page": int(chunk.get("primary_page", chunk.get("source_pages", [1])[0] if chunk.get("source_pages") else 1)),
                "token_estimate": int(chunk.get("token_estimate", len(plain_text.split()))),
                "recommended_task": str(chunk.get("recommended_task", "general")),
            })

        if not ids:
            return 0

        embeddings = self.compute_embeddings(documents)

        if self.collection is not None:
            try:
                self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
                return len(ids)
            except Exception as e:
                print(f"ChromaDB upsert notice: {e}")

        return len(ids)

    def format_query_for_embedding(self, query: str) -> str:
        """
        Applies asymmetric task instruction prefixes for modern SOTA retrieval models (BGE, E5, Qwen).
        Leaves SBERT (all-MiniLM-L6-v2) unmodified.
        """
        model_name = self.model_key.lower()
        if "bge" in model_name:
            return f"Represent this sentence for searching relevant passages: {query}"
        elif "e5" in model_name:
            return f"query: {query}"
        elif "qwen" in model_name:
            return f"Instruct: Retrieve relevant academic passages for research question\nQuery: {query}"
        return query

    def search(
        self,
        query: str,
        top_k: int = 5,
        university_filter: Optional[str] = None,
        doc_filter: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform dense vector cosine similarity search with active document workspace scoping.
        """
        if not query.strip():
            return []

        formatted_query = self.format_query_for_embedding(query)
        query_emb = self.compute_embeddings([formatted_query])[0]
        results = []


        if self.collection is not None and self.collection.count() > 0:
            try:
                # Query up to top_k * 3 to allow post-filtering by active workspace documents
                n_fetch = min(max(top_k * 3, 20), self.collection.count())
                chroma_res = self.collection.query(
                    query_embeddings=[query_emb],
                    n_results=n_fetch,
                    include=["documents", "metadatas", "distances"],
                )

                if chroma_res and chroma_res["ids"]:
                    ret_ids = chroma_res["ids"][0]
                    ret_docs = chroma_res["documents"][0]
                    ret_meta = chroma_res["metadatas"][0]
                    ret_dists = chroma_res["distances"][0] if "distances" in chroma_res else [0.2] * len(ret_ids)

                    for cid, doc, meta, dist in zip(ret_ids, ret_docs, ret_meta, ret_dists):
                        meta_pdf = str(meta.get("pdf_filename", ""))
                        meta_uni = str(meta.get("university", ""))

                        # Active document filter
                        if active_docs is not None and len(active_docs) > 0:
                            if meta_pdf not in active_docs and meta.get("doc_id") not in active_docs:
                                continue

                        # Single document filter
                        if doc_filter and doc_filter != "ALL":
                            if meta_pdf.lower() != doc_filter.lower() and meta.get("doc_id", "").lower() != doc_filter.lower():
                                continue

                        # University filter
                        if university_filter and university_filter.lower() not in meta_uni.lower():
                            continue

                        similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                        results.append({
                            "id": cid,
                            "chunk_id": cid,
                            "text": doc,
                            "similarity": round(similarity, 4),
                            "metadata": meta,
                        })

                        if len(results) >= top_k:
                            break
                    return results
            except Exception as e:
                print(f"ChromaDB search fallback notice: {e}")

        return results

    def get_active_workspace_documents(self) -> List[str]:
        """
        Returns the list of active documents registered in the system manifest.
        """
        try:
            from .config import settings
            manifest_file = settings.processed_dir / "ingested_manifest.json"
            if manifest_file.exists():
                import json
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                docs = data.get("ready_documents", [])
                return [d.get("filename", "") for d in docs if isinstance(d, dict) and d.get("filename")]
        except Exception:
            pass
        return []

    def reset_collection(self):
        """Clear collection."""
        if self.collection is not None and self.client is not None:
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.create_collection(self.collection_name, metadata={"hnsw:space": "cosine"})
            except Exception:
                pass

