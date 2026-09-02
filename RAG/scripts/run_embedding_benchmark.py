"""
RAISE Real Embedding Benchmark (Separate ChromaDB Collections)
Collection 1: raise_graphrag_chunks (MiniLM baseline - Untouched)
Collection 2: raise_graphrag_qwen4b_test (Test collection)
Measures actual Recall@K, Precision@K, MRR on real university benchmark queries.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

# Real University Ground Truth Benchmark Queries
EVAL_QUERIES = [
    {
        "query_id": "EQ_01",
        "query": "What initiatives were recommended by the Institute Curriculum Task Force (CTF) under the National Education Policy at IIT Madras?",
        "expected_doc": "Annual Report 2024-25 final upload.pdf",
        "expected_page": 10
    },
    {
        "query_id": "EQ_02",
        "query": "Which autonomous research institutes and centres operate under the Biotechnology Research and Innovation Council (BRIC)?",
        "expected_doc": "BRIC-Annual-Report-2025-English.pdf",
        "expected_page": 11
    },
    {
        "query_id": "EQ_03",
        "query": "What audited financial balance sheet and CAG reconciliation statement was reported by NIPGR in 2024-25?",
        "expected_doc": "NIPGR_Annual_Report_2024-25.pdf",
        "expected_page": 3
    }
]

rag_dir = Path("RAG").resolve()
chroma_path = rag_dir / ".chromadb"
client = chromadb.PersistentClient(path=str(chroma_path))

# 1. Baseline Collection: MiniLM
minilm_col = client.get_collection("raise_graphrag_chunks")
print(f"Baseline MiniLM Collection Count: {minilm_col.count()} vectors")

# Run Baseline Retrieval
minilm_results = []
minilm_hits = 0
minilm_mrr = 0.0

for q in EVAL_QUERIES:
    t0 = time.time()
    res = minilm_col.query(
        query_texts=[q["query"]],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )
    latency = round(time.time() - t0, 4)
    
    retrieved_items = []
    hit_rank = None
    for rank, (doc, meta, dist) in enumerate(zip(res["documents"][0], res["metadatas"][0], res["distances"][0])):
        sim = round(max(0.0, 1.0 - dist/2.0), 4)
        is_relevant = (meta.get("pdf_filename") == q["expected_doc"] and abs(int(meta.get("primary_page", 1)) - q["expected_page"]) <= 2)
        if is_relevant and hit_rank is None:
            hit_rank = rank + 1
        retrieved_items.append({
            "rank": rank + 1,
            "pdf_filename": meta.get("pdf_filename"),
            "page": meta.get("primary_page"),
            "similarity": sim,
            "relevant": is_relevant
        })
    
    if hit_rank:
        minilm_hits += 1
        minilm_mrr += 1.0 / hit_rank
        
    minilm_results.append({
        "query_id": q["query_id"],
        "query": q["query"],
        "latency_seconds": latency,
        "hit_rank": hit_rank,
        "retrieved_chunks": retrieved_items
    })

minilm_metrics = {
    "model_id": "sentence-transformers/all-MiniLM-L6-v2",
    "embedding_dimension": 384,
    "collection": "raise_graphrag_chunks",
    "precision_at_3": round(minilm_hits / (len(EVAL_QUERIES) * 3), 4),
    "recall_at_3": round(minilm_hits / len(EVAL_QUERIES), 4),
    "mrr": round(minilm_mrr / len(EVAL_QUERIES), 4),
    "queries": minilm_results
}

out_bench = rag_dir / "data" / "processed" / "llm_tests" / "embedding_benchmark_results.json"
out_bench.parent.mkdir(parents=True, exist_ok=True)
out_bench.write_text(json.dumps(minilm_metrics, indent=2), encoding="utf-8")

print(f"\nEmbedding Benchmark Completed! Results saved to: {out_bench}")
print(f"Recall@3: {minilm_metrics['recall_at_3']} | MRR: {minilm_metrics['mrr']}")
