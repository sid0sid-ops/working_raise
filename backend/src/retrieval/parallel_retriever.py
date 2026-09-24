"""
Asynchronous Parallel Multi-Substrate Retriever for RAISE.
Concurrently executes:
  1. Dense Vector Search (ChromaDB using BGE-Large / all-MiniLM)
  2. Sparse Lexical Search (BM25 keyword/entity matching)
  3. Graph Traversal / Cypher Queries (Neo4j / NetworkX property graph)
Merges candidates using Reciprocal Rank Fusion (RRF, k=60) and applies BGE-Reranker-Large.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.retrieval.fusion import reciprocal_rank_fusion, CrossEncoderReranker

BASE_DIR = Path(__file__).parent.parent.resolve()
_bin_dir = BASE_DIR / "bin"
if _bin_dir.exists() and str(_bin_dir) not in sys.path:
    sys.path.insert(0, str(_bin_dir))

try:
    import raise_engine
    HAS_RUST_ENGINE = True
except Exception:
    HAS_RUST_ENGINE = False


class SelfContainedBM25:
    """
    An independent, zero-dependency implementation of the Okapi BM25 
    document ranking algorithm. Completely offline-compatible.
    """
    def __init__(self, corpus_chunks: list, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks = corpus_chunks
        self.corpus_size = len(corpus_chunks)
        
        # Tokenize corpus
        self.tokenized_corpus = [self._tokenize(c.get("plain_text") or c.get("text") or "") for c in corpus_chunks]
        self.avg_doc_len = (
            sum(len(doc) for doc in self.tokenized_corpus) / self.corpus_size 
            if self.corpus_size > 0 else 1.0
        )
        
        # Calculate document frequencies
        self.doc_freqs = []
        self.doc_lens = []
        self.df = Counter()
        
        for doc in self.tokenized_corpus:
            self.doc_lens.append(len(doc))
            freqs = Counter(doc)
            self.doc_freqs.append(freqs)
            for word in freqs.keys():
                self.df[word] += 1
                
        # Precompute IDF scores
        self.idf = {}
        for word, freq in self.df.items():
            self.idf[word] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)
            
    def _tokenize(self, text: str) -> list:
        return re.findall(r'\b\w+\b', text.lower())
        
    def search(self, query: str, top_k: int = 6, active_docs: Optional[List[str]] = None) -> list:
        # Strict drawer isolation: If active_docs is explicitly empty, return zero hits
        if active_docs is not None and len(active_docs) == 0:
            return []
        query_tokens = [t for t in self._tokenize(query) if len(t) > 2]
        if not query_tokens:
            return []
            
        scores = []
        for i in range(self.corpus_size):
            chunk = self.chunks[i]
            if active_docs:
                doc_name = str(chunk.get("pdf_filename") or (chunk.get("metadata") or {}).get("pdf_filename") or chunk.get("document_id") or (chunk.get("metadata") or {}).get("doc_id") or "")
                if not any(ad.lower() in doc_name.lower() or Path(ad).stem.lower() in doc_name.lower() for ad in active_docs):
                    continue

            score = 0.0
            doc_len = self.doc_lens[i]
            freqs = self.doc_freqs[i]
            
            for token in query_tokens:
                if token in freqs:
                    tf = freqs[token]
                    idf = self.idf.get(token, 0.0)
                    
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                    score += idf * (numerator / denominator)
                    
            if score > 0.0:
                item = dict(chunk)
                item["bm25_score"] = float(score)
                scores.append((score, item))
            
        # Sort descending by BM25 score
        scores.sort(key=lambda x: x[0], reverse=True)
        return [chunk for score, chunk in scores[:top_k]]


class AsyncParallelRetriever:
    """
    Executes dense, sparse, and graph retrieval paths concurrently using asyncio.gather.
    """

    def __init__(self, rag_pipeline: Any, reranker_model: Optional[str] = None):
        self.pipeline = rag_pipeline
        self.reranker = CrossEncoderReranker(model_name=reranker_model or "BAAI/bge-reranker-large")

    async def _search_dense_vector(
        self,
        query: str,
        top_k: int = 6,
        doc_filter: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Run dense vector search in non-blocking threadpool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.pipeline.vector_engine.search(
                query=query,
                top_k=top_k,
                doc_filter=doc_filter,
                active_docs=active_docs,
            )
        )

    async def _search_sparse_lexical(
        self,
        query: str,
        top_k: int = 6,
        active_docs: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Run sparse BM25 search independently across the entire document chunk corpus."""
        loop = asyncio.get_running_loop()

        def _bm25_search():
            # Check cached BM25 index on self
            cached_index = getattr(self, "_cached_bm25", None)
            cached_count = getattr(self, "_cached_chunk_count", 0)

            # 1. Gather all corpus chunks from disk or vector engine
            corpus_chunks = []
            chunks_dir = Path(__file__).parent.parent / "data" / "processed" / "chunks"
            if chunks_dir.exists():
                for cf in chunks_dir.glob("*_chunks.json"):
                    try:
                        c_list = json.loads(cf.read_text(encoding="utf-8"))
                        if isinstance(c_list, list):
                            corpus_chunks.extend(c_list)
                    except Exception:
                        pass

            if not corpus_chunks and hasattr(self.pipeline, "vector_engine") and self.pipeline.vector_engine.collection:
                try:
                    cdata = self.pipeline.vector_engine.collection.get()
                    for idx, cid in enumerate(cdata.get("ids", [])):
                        corpus_chunks.append({
                            "chunk_id": cid,
                            "plain_text": cdata["documents"][idx] if idx < len(cdata["documents"]) else "",
                            "metadata": cdata["metadatas"][idx] if idx < len(cdata["metadatas"]) else {},
                        })
                except Exception:
                    pass

            if not corpus_chunks:
                # Fallback to token count if no chunks are indexable
                clean_q = re.sub(r"[^a-zA-Z0-9\s]", "", query.lower())
                query_tokens = [t for t in clean_q.split() if len(t) > 2]
                return self.pipeline.vector_engine.search(
                    query=" ".join(query_tokens) if query_tokens else query,
                    top_k=top_k,
                    active_docs=active_docs,
                )

            # Reuse or rebuild cache
            if cached_index is None or cached_count != len(corpus_chunks):
                cached_index = SelfContainedBM25(corpus_chunks)
                self._cached_bm25 = cached_index
                self._cached_chunk_count = len(corpus_chunks)

            results = cached_index.search(query, top_k=top_k, active_docs=active_docs)
            return results

        return await loop.run_in_executor(None, _bm25_search)

    async def _traverse_graph_entities(
        self,
        query: str,
        hops: int = 2,
        active_docs: Optional[List[str]] = None,
        chunk_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Run dynamic graph traversal across live Neo4j knowledge graph using chunk neighborhoods or token fallback."""
        loop = asyncio.get_running_loop()

        def _graph_search():
            # Strict drawer isolation: If active_docs is explicitly empty, return zero hits
            if active_docs is not None and len(active_docs) == 0:
                return []
            clean_q = re.sub(r"[^a-zA-Z0-9\s]", "", query.lower())
            tokens = [t for t in clean_q.split() if len(t) > 2 and t not in {
                "what", "tell", "which", "with", "from", "were", "this", "some", "show", "about", "have", "that"
            }]
            
            doc_filter = active_docs[0] if (active_docs and len(active_docs) > 0) else None
            records = []
            if self.pipeline.neo4j_db and self.pipeline.neo4j_db.connected:
                # 1. Step 3: Dynamic GraphRAG Traversal (Neighborhood-hop by chunk IDs)
                if chunk_ids:
                    dynamic_cypher = """
                        MATCH (c:Chunk) WHERE (c.id IN $chunk_ids OR c.chunk_id IN $chunk_ids)
                        MATCH (c)-[r]-(e)
                        WHERE NOT e:Section AND NOT e:Chunk
                        RETURN DISTINCT coalesce(c.id, c.chunk_id) AS chunk_id,
                                        labels(e)[0] AS entity_label,
                                        coalesce(e.name, e.label, e.id) AS entity_name,
                                        type(r) AS rel_type
                        LIMIT 30
                    """
                    try:
                        dynamic_recs = self.pipeline.neo4j_db.run_cypher(dynamic_cypher, {"chunk_ids": chunk_ids})
                        seen_ent = set()
                        for r in dynamic_recs:
                            ename = r.get("entity_name")
                            cid = r.get("chunk_id")
                            if not ename or (cid, ename) in seen_ent:
                                continue
                            seen_ent.add((cid, ename))
                            elabel = r.get("entity_label") or "Entity"
                            rtype = r.get("rel_type") or "CONNECTED_TO"
                            doc_val = r.get("doc_id") or doc_filter or "general_graph"
                            records.append({
                                "chunk_id": f"neo4j_{cid}_{ename}",
                                "plain_text": f"Knowledge Graph Dynamic Entity [{elabel}]: {ename} (Relation: -[{rtype}]- with Chunk {cid})",
                                "heading": f"Neo4j Knowledge Graph: {ename}",
                                "metadata": {
                                    "doc_id": doc_val,
                                    "primary_page": 1,
                                    "heading": f"Graph Entity: {ename}",
                                    "pdf_filename": doc_val if doc_val.endswith(".pdf") else f"{doc_val}.pdf",
                                },
                            })
                    except Exception:
                        pass

                # 2. Schema / Token-based graph search fallback if dynamic traversal yielded fewer hits
                if len(records) < 5:
                    cypher = """
                        MATCH (n)
                        WHERE (n:Entity OR any(l IN labels(n) WHERE NOT l IN ['Chunk', 'Section']))
                          AND (size($tokens) = 0 OR any(tok IN $tokens WHERE toLower(coalesce(n.label, n.name, n.id, '')) CONTAINS tok))
                        OPTIONAL MATCH (n)-[r]-(m)
                        OPTIONAL MATCH (n)-[:HAS_FACT|REPORTED_METRIC|MENTIONS|CONTAINS_CHUNK]-(c:Chunk)
                        WHERE $doc_filter IS NULL OR toLower(coalesce(n.document_id, c.document_id, '')) CONTAINS toLower($doc_filter)
                        RETURN 
                            coalesce(n.id, elementId(n)) AS id,
                            coalesce(n.label, n.name, n.id) AS name,
                            labels(n)[0] AS type,
                            coalesce(n.page, c.page, 1) AS page,
                            coalesce(n.document_id, c.document_id, 'general_graph') AS doc_id,
                            type(r) AS rel_type,
                            coalesce(m.label, m.name, m.id) AS neighbor_name,
                            labels(m)[0] AS neighbor_type,
                            coalesce(n.raw_value, n.context, '') AS fact_detail,
                            c.chunk_id AS chunk_id
                        LIMIT 20
                    """
                    try:
                        raw_recs = self.pipeline.neo4j_db.run_cypher(cypher, {"tokens": tokens[:8], "doc_filter": doc_filter})
                        seen_nodes = set()
                        for r in raw_recs:
                            nid = r.get("id")
                            if not nid or nid in seen_nodes:
                                continue
                            seen_nodes.add(nid)
                            name = r.get("name")
                            ntype = r.get("type", "Entity")
                            page = r.get("page", 1)
                            doc = r.get("doc_id") or doc_filter or "general_graph"
                            rel = r.get("rel_type")
                            nbr = r.get("neighbor_name")
                            detail = r.get("fact_detail")
                            
                            rel_info = f" -> [{rel}] -> ({nbr})" if rel and nbr else ""
                            fact_info = f" (Details: {detail})" if detail else ""
                            
                            records.append({
                                "chunk_id": f"neo4j_{nid}",
                                "plain_text": f"Knowledge Graph Entity [{ntype}]: {name}{rel_info}{fact_info}",
                                "heading": f"Neo4j Knowledge Graph: {name}",
                                "metadata": {
                                    "doc_id": doc,
                                    "primary_page": page,
                                    "heading": f"Graph Entity: {name}",
                                    "pdf_filename": doc if doc.endswith(".pdf") else f"{doc}.pdf",
                                },
                            })
                    except Exception:
                        pass
            
            if not records:
                # In-memory graph entity search fallback
                centrality = self.pipeline.graph_engine.compute_centrality_metrics(exclude_super_hubs=True)
                gdata = self.pipeline.graph_engine.get_graph_data()
                
                nodes_to_search = gdata.get("nodes", [])
                nodes_to_search.sort(key=lambda n: centrality.get(n.get("id"), {}).get("pagerank", 0.0), reverse=True)

                for node in nodes_to_search:
                    name = str(node.get("name") or node.get("label") or node.get("id") or "").lower()
                    ntype = str(node.get("type") or "Entity")
                    if any(t in name for t in tokens) or (ntype != "Chunk" and ntype != "Section"):
                        records.append({
                            "chunk_id": f"graph_entity_{node.get('id')}",
                            "plain_text": f"Graph Entity [{ntype}]: {node.get('name', node.get('id'))} (Page {node.get('page', 1)})",
                            "provenance": node.get("provenance", {}),
                            "heading": f"Graph Entity: {node.get('name', node.get('id'))}",
                        })

            return records[:15]

        return await loop.run_in_executor(None, _graph_search)

    @staticmethod
    def classify_retrieval_intent(query: str) -> Tuple[str, List[float]]:
        """
        Dynamically classifies query intent into retrieval modalities:
        - NUMERICAL_OR_FACTUAL: High density of digits, dates, currencies, schedule/census/budget keywords.
          Weights: [Dense: 0.30, Sparse BM25: 0.50, Neo4j Graph: 0.20]
        - RELATIONAL_OR_LINEAGE: Entity hierarchies, directors, organizations, faculties, dependencies.
          Weights: [Dense: 0.25, Sparse BM25: 0.20, Neo4j Graph: 0.55]
        - THEMATIC_OR_OVERVIEW: Broad summaries, conceptual research, comparative narratives.
          Weights: [Dense: 0.55, Sparse BM25: 0.25, Neo4j Graph: 0.20]
        """
        q_lower = query.lower()

        # 1. Numerical & Quantitative indicators
        has_numbers = bool(re.search(r"\b\d+(?:\.\d+)?%?\b", query))
        has_financial = any(k in q_lower for k in [
            "expenditure", "revenue", "budget", "cost", "crore", "lakh", "million", "billion",
            "schedule", "fee", "penalty", "population", "census", "growth", "metric", "count",
            "how many", "total", "percentage", "amount", "rupees", "inr", "$", "₹", "€"
        ])
        if has_financial or (has_numbers and ("how" in q_lower or "what" in q_lower or "which" in q_lower)):
            return "NUMERICAL_OR_FACTUAL", [0.30, 0.50, 0.20]

        # 2. Relational & Multi-hop Lineage indicators
        has_relational = any(k in q_lower for k in [
            "director", "dean", "faculty", "professor", "head", "department", "centre",
            "alumnus", "alumni", "founder", "incubated", "startup", "partner", "collaborat",
            "subsidiary", "who is", "who was", "affiliated", "connected", "lineage", "parent of",
            "born in", "founded by", "led by", "awarded to"
        ])
        if has_relational:
            return "RELATIONAL_OR_LINEAGE", [0.25, 0.20, 0.55]

        # 3. Default Thematic / Conceptual
        return "THEMATIC_OR_OVERVIEW", [0.55, 0.25, 0.20]

    async def retrieve_parallel_and_fuse(
        self,
        query: str,
        top_k: int = 6,
        hops: int = 2,
        doc_filter: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
        rerank_top_n: int = 5,
    ) -> Dict[str, Any]:
        """
        Triggers Dense, Sparse, and Graph retrievers in parallel with asyncio.gather,
        applies Reciprocal Rank Fusion, and contextually reranks candidates with BGE-Reranker-Large.
        """
        dense_task = self._search_dense_vector(query, top_k=top_k, doc_filter=doc_filter, active_docs=active_docs)
        sparse_task = self._search_sparse_lexical(query, top_k=top_k, active_docs=active_docs)
        graph_task = self._traverse_graph_entities(query, hops=hops, active_docs=active_docs, chunk_ids=None)

        # 1. Execute Dense, Sparse, and Graph retrieval concurrently
        dense_res, sparse_res, graph_res = await asyncio.gather(dense_task, sparse_task, graph_task)

        # 2. If graph results are sparse, expand with candidate chunk IDs from dense/sparse hits
        if len(graph_res) < 5:
            candidate_chunk_ids: List[str] = []
            for item in (dense_res or []) + (sparse_res or []):
                cid = item.get("chunk_id") or item.get("id") or (item.get("metadata") or {}).get("chunk_id")
                if cid and cid not in candidate_chunk_ids:
                    candidate_chunk_ids.append(str(cid))

            if candidate_chunk_ids:
                dyn_res = await self._traverse_graph_entities(
                    query,
                    hops=hops,
                    active_docs=active_docs,
                    chunk_ids=candidate_chunk_ids[:15],
                )
                if dyn_res:
                    graph_res = (graph_res or []) + dyn_res

        # 3. Classify query intent to dynamically weight modalities
        intent_type, raw_intent_weights = self.classify_retrieval_intent(query)

        # 4. Reciprocal Rank Fusion with Adaptive Intent Weights
        ranked_candidates_list = [dense_res or [], sparse_res or [], graph_res or []]
        active_lists = []
        active_weights = []
        for l_res, w in zip(ranked_candidates_list, raw_intent_weights):
            if l_res:
                active_lists.append(l_res)
                active_weights.append(w)

        fused_candidates = reciprocal_rank_fusion(
            active_lists,
            k=60,
            weights=active_weights if active_weights else None,
            id_key="chunk_id",
            table_boost=True,
        )

        # 5. Contextual Reranking with BGE-Reranker-Large (or cached fallback)
        reranked_chunks = self.reranker.rerank(
            query=query,
            candidates=fused_candidates,
            text_key="plain_text",
            top_n=rerank_top_n,
        )

        return {
            "reranked_chunks": reranked_chunks,
            "dense_count": len(dense_res),
            "sparse_count": len(sparse_res),
            "graph_count": len(graph_res),
            "fused_count": len(fused_candidates),
            "intent_type": intent_type,
            "intent_weights": raw_intent_weights,
        }

    def retrieve_sync(
        self,
        query: str,
        top_k: int = 6,
        hops: int = 2,
        doc_filter: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
        rerank_top_n: int = 5,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for integration into standard pipeline interfaces."""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Inside existing event loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(
                        asyncio.run,
                        self.retrieve_parallel_and_fuse(
                            query=query,
                            top_k=top_k,
                            hops=hops,
                            doc_filter=doc_filter,
                            active_docs=active_docs,
                            rerank_top_n=rerank_top_n,
                        )
                    ).result()
            else:
                return asyncio.run(
                    self.retrieve_parallel_and_fuse(
                        query=query,
                        top_k=top_k,
                        hops=hops,
                        doc_filter=doc_filter,
                        active_docs=active_docs,
                        rerank_top_n=rerank_top_n,
                    )
                )
        except Exception:
            return asyncio.run(
                self.retrieve_parallel_and_fuse(
                    query=query,
                    top_k=top_k,
                    hops=hops,
                    doc_filter=doc_filter,
                    active_docs=active_docs,
                    rerank_top_n=rerank_top_n,
                )
            )


# Compatibility alias
ParallelRetriever = AsyncParallelRetriever

