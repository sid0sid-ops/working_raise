# RAISE : Research Assessment Intelligence & Semantic Extraction (Frontend)

[![Build & Static Test](https://img.shields.io/badge/Build-Passing-emerald.svg)]()
[![Vitest](https://img.shields.io/badge/Tests-27%20Suites%20Passed-blue.svg)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-Strict-blue.svg)]()

Client-side research workstation for **RAISE (Research Assessment Intelligence & Semantic Extraction)**, engineered to synthesize institutional reports, annual filings, university incubator portfolios, and technology transfer audits with mathematical rigor, zero factual fabrication, and end-to-end citation provenance.

---

## 1. System Topology & Architecture Boundaries

The RAISE architecture strictly separates the client presentation layer from the high-throughput generative reasoning and knowledge graph substrates:

```text
                  RAISE WEB CLIENT
┌─────────────────────────────────────────────────────────┐
│                 RAISE React 19 Client                   │
│                                                         │
│   Vite | TypeScript | Tailwind CSS | Radix UI           │
│   Zustand (UI State) | TanStack Query (Server State)    │
│   Zod Runtime Validation | Lucide Icons                 │
│                                                         │
│   Modes: MOCK | CONNECTED | DEGRADED | OFFLINE          │
└────────────────────────────┬────────────────────────────┘
                             │
                             │ HTTP REST (Port 8000)
                             ▼
                 FASTAPI BACKEND GATEWAY
┌─────────────────────────────────────────────────────────┐
│               FastAPI Gateway (app.py)                  │
│                                                         │
│   ├── LangGraph 15-Node Cyclical StateGraph             │
│   ├── Dense Vectors: ChromaDB (.chromadb_bge_large)     │
│   ├── Property Graph: Neo4j (bolt://localhost:7687)     │
│   ├── Hybrid Fusion: BM25 + BGE-Reranker-Large          │
│   ├── LLM Core: vLLM (Qwen 2.5 14B Int4, Port 8002)     │
│   └── Quality Gate: LocalHeuristicEvaluator (>=0.80)    │
└─────────────────────────────────────────────────────────┘
```

> **Strict Boundary Mandate:** The frontend client communicates exclusively through the FastAPI gateway on port 8000.

---

## 2. Verified Backend APIs

| Endpoint | Method | Status | Purpose |
|---|---|---|---|
| `/api/graphrag/subgraph-query` | `POST` | **VERIFIED** | 15-Node LangGraph multi-hop query |
| `/api/agent/query` | `POST` | **VERIFIED** | Direct multi-tool autonomous agent query |
| `/api/documents` | `GET` | **VERIFIED** | Manifest of active ready research PDFs |
| `/api/upload-academic-pdfs` | `POST` | **VERIFIED** | Synchronous Docling + vector + graph indexing |
| `/api/documents/delete` | `POST` | **VERIFIED** | Prunes chunks from ChromaDB and detaches Neo4j graph |
| `/api/pdf/{filename}` | `GET` | **VERIFIED** | Physical PDF stream with `#page=N` deep-linking |
| `/api/graph` | `GET` | **VERIFIED** | Knowledge graph node-link payload for 2D canvas |
| `/api/neo4j/status` | `GET` | **VERIFIED** | Neo4j Bolt connection health & node count |
| `/api/hardware-telemetry` | `GET` | **VERIFIED** | GPU allocations & host RAM statistics |
| `/api/chat/stream` | `POST` | **OPTIONAL** | Native token SSE streaming |
| `/api/chat/history` | `GET/POST/DELETE` | **VERIFIED** | Cross-session chat history persistence |

---

## 3. Operational Modes

Configured via environment variables (`.env`) or live via the **Settings** modal:

1. **`MOCK`:** Runs 100% locally with verified production fixtures simulating real synthesis, empty workspaces, quality gate refusals, Neo4j outages, and graph structures.
2. **`CONNECTED`:** Dispatches requests to the live FastAPI gateway (`http://<BACKEND_IP>:8000`).
3. **`AUTO` (Default):** Probes the gateway on initialization. If unreachable, smoothly operates in mock mode while notifying the researcher with actionable network diagnostics.
4. **`DEGRADED`:** Explicitly identifies partial substrate failures (e.g. Neo4j down while semantic vector search remains operational).

---

## 4. Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Run local development server
npm run dev

# 3. Run complete test suite (27 unit & integration tests)
npm run test:run

# 4. Perform production static bundle build
npm run build

# 5. Preview production build locally
npm run preview
```
