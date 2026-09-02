# RAISE GraphRAG & Vector Architecture Guide

## Overview
The `RAG/` workspace provides a high-throughput, 100% offline knowledge system that transforms unstructured academic PDF reports into queryable vector collections and graph networks.

---

## Key Modules

### 1. Vector Search Engine (`RAG/src/vector_engine.py`)
* **Vector Store**: **ChromaDB** persistent in-process store (`.runtime/chroma_db`).
* **Embeddings**: **Sentence-Transformers** (`all-MiniLM-L6-v2`), 384-dimensional dense vectors running locally on CPU / CUDA with zero API keys or costs.
* **Methods**:
  * `ingest_chunks(chunks, doc_id)`: Encodes text and metadata into ChromaDB.
  * `search(query, top_k=5, doc_id=None)`: Performs sub-millisecond cosine similarity retrieval.

### 2. GraphRAG Knowledge Engine (`RAG/src/graph_engine.py`)
* **Graph Structure**: **NetworkX Directed Property Graph**.
* **Entity Extraction**:
  * `Organization` (BRIC-CDFD, AstraBio, DBT, ICMR)
  * `Section` (Document hierarchy with provenance)
  * `IntellectualProperty` (Patents, filings, cultivars)
  * `StrategicInitiative` (BioE3, SAHAJ, One Day One Genome)
  * `TaxonomyDomain` (Uddhav's 10 schema domains)
* **Neo4j Cypher Export**: Generates executable `.cypher` scripts (`knowledge_graph.cypher`) for instant import into Neo4j Browser.

---

## How to Run the RAG Web System

### Windows Batch:
```cmd
RAG\run_rag.bat
```

### PowerShell:
```powershell
.\RAG\run_rag.ps1
```
