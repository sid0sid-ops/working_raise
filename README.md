# 🏛️ RAISE: Research Assessment Intelligence & Semantic Extraction

> **Enterprise-Grade Multi-Hop Knowledge Graph & Vector Hybrid Retrieval-Augmented Generation Engine**  
> Tailored for institutional research parks, university annual reports, patent records, and complex cross-document academic queries.

---

## 🌟 Overview

**RAISE (Research Assessment Intelligence & Semantic Extraction)** is an academic-grade GraphRAG system designed to synthesize verifiable answers from dense, multi-hundred-page institutional reports. By orchestrating a hybrid retrieval architecture—coupling dense embeddings, BM25 keyword matching, property graph traversal, and deterministic verification—RAISE eliminates hallucinations and provides cryptographically traceable citations down to the exact page and paragraph.

### Key Capabilities
- **Dual-Engine Retrieval**: Combines dense vector search (`BAAI/bge-large-en-v1.5`) with multi-hop property graph traversal (Neo4j 5.26).
- **Local Neural Inference**: Zero data leakage via local vLLM serving `Qwen2.5-14B-Instruct-GPTQ-Int4` on modern GPUs.
- **Strict Quality Gating**: Automated claim verification with citation provenance and quality classification (`accept`, `retry`, `unable_to_verify`).
- **High-Performance Caching & Persistence**: Sub-millisecond query caching in Redis and persistent audit trails in PostgreSQL 16.
- **Secure Zero-Trust Connectivity**: Outbound-only Cloudflare Tunnel connection allowing remote static frontends (e.g. GitHub Pages) to access the local GPU backend securely without opening firewall ports.
- **Zero-Cost Free-Tier Storage**: Cloudflare R2 integration with automatic software circuit breakers guaranteeing $0 billing.

---

## 🏗️ Heterogeneous Tri-Engine Architecture

```
                                 RAISE
                                   │
                         Python / FastAPI Layer
                         (Orchestration & APIs)
                                   │
                   ┌───────────────┴───────────────┐
                   ↓                               ↓
              Layer 2: Rust                  Layer 3: GPU/CUDA
             (CPU Acceleration)                 (AI Engine)
                   │                               │
            ┌──────┴──────┐                 ┌──────┴──────┐
            ↓             ↓                 ↓             ↓
      GGAHC Chunking    BM25 Search   BGE Embeddings   vLLM / Qwen
      Graph Analytics   RRF Ranking   Tensor Ops       Local Inference
      Text Dedup/Hash   Deterministic
                        Evaluations
                   │                               │
                   └───────────────┬───────────────┘
                                   ↓
                       Storage & Database Layer
             ┌─────────────────────┼─────────────────────┐
             ↓                     ↓                     ↓
         ChromaDB                Neo4j               PostgreSQL
     (Dense Vectors)        (Property Graph)      (Audit / Relational)
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   ↓
                              Redis Cache
                           (Sub-ms Sessions)
```

### Layer Responsibilities

| Layer | Technology | Key Components & Responsibilities |
| :--- | :--- | :--- |
| **Layer 1: Python Application** | FastAPI, LangGraph, Python 3.12 | • **Keep**: FastAPI REST & SSE endpoints, Docling layout ingestion, PyTorch / Transformers / Sentence-Transformers integration, Provider SDKs, vLLM / Ollama clients, Neo4j driver, ChromaDB / Qdrant driver, LangGraph cyclical workflows, Configuration, Ingestion pipeline orchestration. |
| **Layer 2: Rust Acceleration** | `raise_engine` (PyO3 + C-ABI + CLI) | • **Optimize**: Graph-Guided Adaptive Hierarchical Chunking (GGAHC), Text normalization & PDF hyphen repair, Chunk deduplication (SimHash + FNV-1a), SHA-256 fingerprinting, Compact Inverted Index & Okapi BM25, Candidate pre-ranking (QuickSelect), Reciprocal Rank Fusion (RRF), Adjacency graph construction & Label Propagation (LPA), Deterministic formula evaluations. |
| **Layer 3: GPU / CUDA** | vLLM, TensorRT / AutoAWQ, CUDA | • **Delegate**: Local LLM inference (`Qwen2.5-14B-Instruct-GPTQ-Int4`), Dense vector embeddings (`BAAI/bge-large-en-v1.5`), Batch tensor operations, GPU-accelerated neural attention. |
| **Storage Layer** | PostgreSQL, Neo4j, ChromaDB, Redis | • Multi-hop knowledge graph (Neo4j 5.26 with APOC), Dense vector store (ChromaDB HNSW), Relational audit logs & sessions (PostgreSQL 16 / SQLite fallback), Sub-millisecond cache (Redis 7). |


---

## 📁 Repository Structure

```text
raise/
├── app.py                          # Workspace root launcher forwarding to RAG
├── main.py                         # Root entrypoint
├── operator_checkup.py             # CLI diagnostics and operator health checkup
├── pytest.ini                      # Unified test suite configuration
├── .env.example                    # Complete sanitized environment variable template
├── .gitignore                      # Hardened ignore rules (zero secrets / zero binaries)
├── BACKEND_DEPLOYMENT.md           # Step-by-step production Docker & bare-metal deployment
├── BACKEND_CONFIGURATION.md        # Comprehensive configuration & environment reference
├── BACKEND_API.md                  # REST & SSE API contracts for frontend developers
├── SECURITY.md                     # Security audit, secret handling, & R2 cost guardrails
├── TROUBLESHOOTING.md              # Diagnostics, failure modes, and recovery procedures
├── Artifacts/                      # Canonical documentation, architecture ADRs & benchmarks
├── data/                           # Data decoupling guide
│   └── README.md
├── models/                         # Model weights and inference decoupling guide
│   └── README.md
└── RAG/                            # Master backend implementation
    ├── app.py                      # FastAPI application server (REST + SSE)
    ├── Dockerfile                  # Production container definition
    ├── docker-compose.yml          # Container orchestration stack
    ├── requirements.txt            # Host Python dependencies
    ├── requirements-docker.txt     # Minimal containerized dependencies
    ├── SYSTEM_MANIFEST.md          # Runtime database and model manifest
    ├── data/
    │   ├── documents/              # Source PDF reports (e.g. IIT Madras Annual Report)
    │   └── processed/              # Extracted semantic chunks and graph triples
    ├── evaluation/
    │   └── benchmarks/             # Baseline verifier, ablation & FRAMES benchmarks
    ├── src/
    │   ├── api/                    # Pydantic v2 schemas, dependencies, and API routers
    │   ├── chunking/               # GGAHC 8-stage hierarchical adaptive chunking pipeline
    │   ├── cli/                    # CLI models, interactive console, and audit ledgers
    │   ├── core/                   # Typed settings, state graph, and invariants
    │   ├── features/               # Evaluation (FineCat-NLI), claim verification, math engine
    │   ├── infrastructure/         # Neo4j, ChromaDB, PostgreSQL, Redis, and vLLM clients
    │   ├── parsers/                # Docling deep vision & PyMuPDF structure parsers
    │   ├── retrieval/              # Hybrid BM25/Dense/Graph fusion & BGE reranker
    │   ├── security/               # AST injection firewall and input sanitization
    │   ├── services/               # Telemetry service, document drawer, session management
    │   └── storage/                # Cloudflare R2 client with free-tier circuit breakers
    └── tests/                      # 31+ automated regression, benchmark, and unit test suites
```

---

## 🏆 Project Certification Status

```text
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                        PROJECT CERTIFICATION STATUS                         │
  ├───────────────────────────────┬─────────────────────────────────────────────┤
  │ CODE REGRESSION TESTS         │ 187/187 PASS (100% Deterministic Baseline)  │
  │ SYSTEM READINESS GATE         │ 11/11 PASS (100% Certified Release Gate)    │
  │ RETRIEVAL ABLATION (M2)       │ CERTIFIED (Hybrid +17.9% Boost, M5 Deferred)│
  │ GROUNDING BASELINE (M1)       │ BENCHMARKED (1,000 Claims: 37.0% FAR, 0.56ms)│
  │ RAG SEMANTIC QUALITY (M3)     │ CERTIFIED (25-Probe NIAH 84% + 5-PDF Vault) │
  │ FRAMES MULTI-HOP (100 Qs)     │ CERTIFIED (32.0% Acc, 0.0% Halluc, 41.0% Abst)|
  └───────────────────────────────┴─────────────────────────────────────────────┘
```

---

## ⚡ Quickstart

### Prerequisites
- Docker Engine & Docker Compose (v2.20+)
- NVIDIA GPU with >=16GB VRAM (recommended for local vLLM) or Ollama on CPU
- Git

### 1. Clone & Configure
```bash
git clone https://github.com/semanticClimate/RAISE.git
cd raise

# Copy environment template
cp .env.example .env
```

### 2. Launch Stack with Docker Compose
```bash
cd RAG
docker compose up -d
```

### 3. Verify System Health
Run the built-in diagnostic tool from the host or container:
```bash
python operator_checkup.py
```
Or check the HTTP health check:
```bash
curl http://localhost:8000/api/health
```
Expected output:
```json
{
  "status": "healthy",
  "databases": {
    "postgres": true,
    "redis": true,
    "neo4j": true,
    "vllm": true,
    "chroma": true
  }
}
```

---

## 📚 Documentation Index

| Guide | Description |
| :--- | :--- |
| **[BACKEND_DEPLOYMENT.md](BACKEND_DEPLOYMENT.md)** | Production deployment procedures, Docker Compose setup, and Cloudflare Tunnel configurations. |
| **[BACKEND_CONFIGURATION.md](BACKEND_CONFIGURATION.md)** | Exhaustive reference of all environment variables, ports, and runtime options. |
| **[BACKEND_API.md](BACKEND_API.md)** | Complete HTTP and SSE API contracts for frontend integration (Mac / GitHub Pages). |
| **[SECURITY.md](SECURITY.md)** | Secret management policies, CORS policies, and strict zero-cost R2 billing guardrails. |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Error codes, memory management, recovery procedures, and common failure modes. |
| **[data/README.md](data/README.md)** | Raw document ingestion, semantic chunking, and knowledge graph triple generation. |
| **[models/README.md](models/README.md)** | Embedding and generative LLM models, quantization specs, and vLLM execution. |

---

## 📄 License
This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.
