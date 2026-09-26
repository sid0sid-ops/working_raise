"""
RAISE NIAH Benchmark — Isolation Harness
Guarantees 100% database isolation:
  - Uses ephemeral in-memory ChromaDB or dedicated test directories
  - Prevents test vectors and benchmark artifacts from polluting production collections
  - Provides sandboxed in-memory or document-scoped Neo4j graph environments
  - Automatic teardown ensuring clean state after every test run
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

# Import production vector engine for exact embedding model representation
from src.infrastructure.vector.chroma import LocalVectorEngine
from src.features.graph.engine import GraphRAGEngine
from src.infrastructure.graph.neo4j import Neo4jDatabase
from .chunking_simulator import ChunkedCorpus, SimulatedChunk


class IsolatedVectorHarness:
    """
    Sandboxed ChromaDB vector engine that replicates production embedding and retrieval
    without touching the production collection or persist directory.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        use_in_memory: bool = True,
        persist_dir: Optional[Path | str] = None,
    ):
        self.session_id = str(uuid.uuid4())[:8]
        self.collection_name = f"niah_eval_{self.session_id}"
        self.use_in_memory = use_in_memory
        
        # Dedicated isolated directory under evaluation if disk persistence is requested
        if use_in_memory:
            self.persist_path = None
            self.client = chromadb.EphemeralClient(
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
            )
        else:
            base_test_dir = Path(persist_dir or Path(__file__).resolve().parent.parent.parent / "generated_corpora" / ".chromadb_niah")
            self.persist_path = base_test_dir / f"session_{self.session_id}"
            self.persist_path.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=str(self.persist_path),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
            )

        # Initialize isolated collection with cosine metric matching production
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Re-use production embedding computation logic for 100% fidelity
        self.vector_engine = LocalVectorEngine(
            model_name=model_name or "BAAI/bge-large-en-v1.5"
        )

    def ingest_simulated_chunks(self, chunked_corpus: ChunkedCorpus) -> int:
        """
        Ingest simulated chunks into the isolated collection.
        """
        chunks = chunked_corpus.chunks
        if not chunks:
            return 0

        ids = [c.chunk_id for c in chunks]
        texts = [c.text for c in chunks]
        metadatas = [
            {
                "chunk_id": c.chunk_id,
                "chunk_index": c.chunk_index,
                "contains_needle": c.contains_needle,
                "word_count": c.word_count,
                "char_start": c.char_start,
                "char_end": c.char_end,
                "corpus_id": chunked_corpus.corpus_id,
            }
            for c in chunks
        ]

        # Compute embeddings using production model
        embeddings = self.vector_engine.compute_embeddings(texts)

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(ids)

    def query(
        self,
        query: str,
        top_k: int = 10,
        apply_instruction: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Execute dense vector search against the isolated collection.
        """
        formatted_query = self.vector_engine.format_query_for_embedding(query) if apply_instruction else query
        query_emb = self.vector_engine.compute_embeddings([formatted_query])[0]

        n_results = min(top_k, self.collection.count())
        if n_results == 0:
            return []

        res = self.collection.query(
            query_embeddings=[query_emb],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        if res and res.get("ids") and len(res["ids"][0]) > 0:
            ret_ids = res["ids"][0]
            ret_docs = res["documents"][0]
            ret_meta = res["metadatas"][0]
            ret_dists = res["distances"][0]

            for rank, (cid, doc, meta, dist) in enumerate(zip(ret_ids, ret_docs, ret_meta, ret_dists), start=1):
                # Cosine similarity in ChromaDB: dist in [0, 2], sim = 1 - dist/2
                sim = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                hits.append({
                    "rank": rank,
                    "chunk_id": cid,
                    "text": doc,
                    "distance": round(float(dist), 4),
                    "similarity": round(float(sim), 4),
                    "metadata": meta,
                    "contains_needle": bool(meta.get("contains_needle", False)),
                })

        return hits

    def teardown(self):
        """Cleanly drops test collection and removes temporary files."""
        try:
            if self.client and self.collection_name:
                self.client.delete_collection(self.collection_name)
        except Exception:
            pass

        if self.persist_path and self.persist_path.exists():
            try:
                shutil.rmtree(self.persist_path, ignore_errors=True)
            except Exception:
                pass


class IsolatedGraphHarness:
    """
    Sandboxed Graph harness using in-memory NetworkX GraphRAGEngine or scoped Neo4j document space.
    """

    def __init__(self, use_live_neo4j: bool = False):
        self.session_id = str(uuid.uuid4())[:8]
        self.doc_id = f"niah_eval_{self.session_id}"
        self.use_live_neo4j = use_live_neo4j
        self.in_memory_graph = GraphRAGEngine()
        self.neo4j_db = Neo4jDatabase() if use_live_neo4j else None

    def populate_graph(self, entities: List[Dict[str, Any]], relations: List[Dict[str, Any]]):
        """Populate isolated graph with test entities and relations."""
        # 1. In-memory NetworkX graph
        for ent in entities:
            nid = ent["id"]
            self.in_memory_graph.graph.add_node(
                nid,
                id=nid,
                label=ent.get("name", nid),
                name=ent.get("name", nid),
                type=ent.get("label", "Entity"),
                page=ent.get("page", 1),
                document_id=self.doc_id,
            )

        for rel in relations:
            src = rel["source"]
            tgt = rel["target"]
            rtype = rel.get("relation", "RELATED_TO")
            if self.in_memory_graph.graph.has_node(src) and self.in_memory_graph.graph.has_node(tgt):
                self.in_memory_graph.graph.add_edge(
                    src,
                    tgt,
                    relation=rtype,
                    type=rtype,
                    document_id=self.doc_id,
                )

        # 2. Live Neo4j with strict document_id scoping if enabled
        if self.use_live_neo4j and self.neo4j_db and self.neo4j_db.connected:
            gdata = {
                "nodes": [
                    {
                        "id": e["id"],
                        "name": e.get("name", e["id"]),
                        "label": e.get("name", e["id"]),
                        "type": e.get("label", "Entity"),
                        "page": e.get("page", 1),
                        "document_id": self.doc_id,
                    }
                    for e in entities
                ],
                "edges": [
                    {
                        "source": r["source"],
                        "target": r["target"],
                        "type": r.get("relation", "RELATED_TO"),
                        "document_id": self.doc_id,
                    }
                    for r in relations
                ],
            }
            self.neo4j_db.sync_graph_data(gdata)

    def query_multihop(self, seed_id: str, max_hops: int = 2) -> Dict[str, Any]:
        """Perform multi-hop traversal starting from seed_id."""
        if self.in_memory_graph.graph.has_node(seed_id):
            subgraph = self.in_memory_graph.extract_subgraph(seed_node_ids=[seed_id], hops=max_hops)
            return subgraph

        if self.use_live_neo4j and self.neo4j_db and self.neo4j_db.connected:
            return self.neo4j_db.query_multihop_subgraph(seed_ids=[seed_id], hops=max_hops, doc_id=self.doc_id)

        return {"nodes": [], "edges": []}

    def teardown(self):
        """Purges any temporary test nodes from Neo4j and clears in-memory graph."""
        self.in_memory_graph.clear()
        if self.use_live_neo4j and self.neo4j_db and self.neo4j_db.connected:
            try:
                # Strictly scoped deletion: deletes ONLY nodes matching our unique session doc_id
                self.neo4j_db.run_cypher(
                    "MATCH (n {document_id: $doc_id}) DETACH DELETE n",
                    {"doc_id": self.doc_id}
                )
            except Exception:
                pass


class NIAHIsolationHarness:
    """
    Combined harness providing both isolated vector store and isolated graph database.
    Supports context manager protocol for automatic guaranteed teardown.
    """

    def __init__(self, model_name: Optional[str] = None, use_live_neo4j: bool = False):
        self.vector_harness = IsolatedVectorHarness(model_name=model_name)
        self.graph_harness = IsolatedGraphHarness(use_live_neo4j=use_live_neo4j)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.teardown()

    def teardown(self):
        self.vector_harness.teardown()
        self.graph_harness.teardown()
