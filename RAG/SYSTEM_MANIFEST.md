# 🗺️ RAISE Academic GraphRAG — System Storage, Versions & Model Manifest

This document provides an inventory of where models, databases, processed data, and configuration files are stored across your system, including their exact versions, paths, and operational status.

---

## 📦 1. Downloaded Model Weights & Cache Locations

| Model | Type | Stored Path | Version / Weights | Status |
| :--- | :--- | :--- | :--- | :---: |
| **`sentence-transformers/all-MiniLM-L6-v2`** | Dense Embedding (384-dim) | `C:\Users\Siddharth Tripathi\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2` | Pre-downloaded, 100% Offline PyTorch | **ACTIVE** |
| **`Docling Local ML Models`** | LayoutLM + TableFormer + RapidOCR | `~/.cache/docling/models` (WSL / Linux) | Local Weights, Offline ONNX / PyTorch | **ACTIVE** |
| **`Qwen2.5:7b` (Ollama)** | Generative LLM | `C:\Users\Siddharth Tripathi\.ollama\models` *(optional)* | 7B Parameter GGUF | **READY** |

---

## 🗄️ 2. Databases & Persistent Runtime Storage

| Database / Store | Storage Type | Local Filesystem Path | Current State / Details |
| :--- | :--- | :--- | :--- |
| **ChromaDB Vector Store** | Dense Cosine Index | `C:\Users\Siddharth Tripathi\Documents\raise\RAG\.runtime\.chromadb` | **ACTIVE** (`v1.5.9`), Indexed Chunks with Provenance |
| **Neo4j Property Graph** | Graph Database | `bolt://localhost:7687` | **ACTIVE (Docker `local-neo4j`)**, 287 Nodes & 325 Relationships Synced |
| **Reasoning Trajectory Memory** | Graph Memory Store | `C:\Users\Siddharth Tripathi\Documents\raise\RAG\.runtime\reasoning_memory.json` | **ACTIVE**, Persistent Cross-Turn Strategy Cache |
| **Workspace Manifest** | Authoritative Registry | `C:\Users\Siddharth Tripathi\Documents\raise\RAG\data\processed\ingested_manifest.json` | **ACTIVE**, Registered Academic Reports |
| **Rotating Log Handler** | File Logging | `C:\Users\Siddharth Tripathi\Documents\raise\RAG\logs\pipeline.log` | **ACTIVE**, 5MB max, 3 backups |

---

## 📄 3. Document Repository & Processed Artifacts

| Category | Description | Local Filesystem Path |
| :--- | :--- | :--- |
| **Raw Academic PDFs** | Uploaded and benchmark PDF reports | `C:\Users\Siddharth Tripathi\Documents\raise\RAG\data\documents` |
| **Extracted Semantic Chunks** | Structured chunks with provenance | `C:\Users\Siddharth Tripathi\Documents\raise\RAG\data\processed\chunks` |
| **Entity & Relation Triples** | Academic domain knowledge graphs | `C:\Users\Siddharth Tripathi\Documents\raise\RAG\data\processed\graph_triples` |

---

## ⚙️ 4. Installed Framework & Library Versions

| Package | Version | Purpose in RAISE |
| :--- | :--- | :--- |
| **`Python`** | `3.13.13` (64-bit AMD64) | Host Runtime |
| **`LangGraph`** | `>=0.2.0` | 5-Node Cyclical StateGraph State Machine |
| **`LangChain Core`** | `>=0.3.0` | Lightweight Tool and Message Data Contracts |
| **`FastAPI`** | `>=0.110.0` | High-Performance REST & HTML API Server |
| **`ChromaDB`** | `1.5.9` | Embedded HNSW Vector Database |
| **`Neo4j Driver`** | `5.18.0` | Bolt Protocol Driver for Neo4j Database |
| **`Docling`** | `2.124.0` | Layout-Aware PDF & Markdown Table Structure Parser |
| **`Sentence-Transformers`**| `>=2.6.0` | Dense Local Vector Embeddings |
| **`NetworkX`** | `>=3.2.0` | Local In-Memory Graph Engine & Neo4j Fallback |
| **`PyMuPDF` (`fitz`)** | `>=1.24.0` | PDF Text, Table & Page Provenance Extractor |

---

## 🛠️ 5. Key Entrypoint & Runner Scripts

* **`run_cli.bat`**: 1-Click Interactive Studio Launcher with Docker auto-detect.
* **`main.py`**: Direct Terminal Interactive Studio (Graph visualizer + Live Multi-Hop Q&A + Reasoning Memory).
* **`app.py`**: FastAPI Web Server & REST API backend.
* **`tests/test_full_system.py`**: Complete Automated Benchmark & Validation Suite.
* **`docker-compose.yml`**: Full container stack orchestration (Neo4j, Ollama, Backend).
