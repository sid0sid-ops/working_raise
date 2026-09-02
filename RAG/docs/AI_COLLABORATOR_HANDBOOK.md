# 🤖 RAISE Agentic GraphRAG & Dual-Workload AI Collaborator Handbook
> **Authoritative System Guide for AI Agents, Developers, and Upstream Contributors**
> **Last Updated:** 31 August 2026 | **Branch:** `siddharth-semantification`

---

## 1. Executive Summary & Machine Context

This repository (`RAISE`) hosts the **Master University Annual Report Agentic GraphRAG System**, a document-grounded intelligence platform designed to extract, index, verify, and comparatively reason across complex, multi-year university annual reports and financial audits.

### Hardware & Local Infrastructure
* **GPU**: NVIDIA GeForce RTX 3090 (24,576 MiB VRAM / Driver 616.56 / CUDA 12.4 & 13.4 Host Layer)
* **System RAM**: ~64 GB DDR4/DDR5
* **Docker Database**: Neo4j Community Edition on `bolt://localhost:7687` (HTTP Browser on `http://localhost:7474`, Auth: `neo4j` / `password123`)
* **Vector Database**: Local ChromaDB embedded collection (`RAG/.chromadb`)
* **Local Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` cached at `C:\Users\Siddharth Tripathi\.cache\huggingface\hub`

---

## 2. ⚠️ STRICT DUAL-WORKLOAD ISOLATION RULES

The host machine runs **TWO completely separate AI workloads**. Every AI agent or developer MUST respect these boundaries:

```text
                             NVIDIA RTX 3090 (24 GB VRAM)
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
   ┌─────────────────────────────┐                 ┌─────────────────────────────┐
   │ WORKLOAD 1: MANGA RECAP AI  │                 │ WORKLOAD 2: GraphRAG AI     │
   │ (WSL2 Ubuntu Subsystem)     │                 │ (WSL2 & Windows Workspaces) │
   ├─────────────────────────────┤                 ├─────────────────────────────┤
   │ Path:                       │                 │ Path:                       │
   │ /home/siddharth_tripathi/   │                 │ /home/siddharth_tripathi/   │
   │ Desktop/MangaRecapAI/       │                 │ Desktop/GraphRAG/           │
   │ tts_env                     │                 │ graphrag_env                │
   │                             │                 │                             │
   │ Status: STRICTLY LOCKED     │                 │ Status: ACTIVE GraphRAG     │
   │ DO NOT TOUCH / MODIFY / PIP │                 │ Independent PyTorch & LLM   │
   └─────────────────────────────┘                 └─────────────────────────────┘
```

### Golden Rule for AI Agents:
> [!CAUTION]
> **NEVER** modify, upgrade, downgrade, install packages into, or delete anything inside `/home/siddharth_tripathi/Desktop/MangaRecapAI/tts_env`. It is locked and operating with Qwen3-TTS.

---

## 3. Two-Folder Clean Repository Architecture

```text
raise/
├── Document Workspace/               # Upstream 5-Star Semantic HTML5 & Layout Ingestion (Port 8000)
│   ├── RAISE_PDF_Parsing/            # PyMuPDF span, font, and bounding box parser
│   ├── RAISE_HTML5_Semantification/  # 10-domain heuristic classifier & semantic HTML5 generator
│   ├── app.py                        # FastAPI upstream app (run_app.bat)
│   └── templates/ & static/          # Side-by-side PDF split viewer
│
├── RAG/                              # Downstream Master Agentic GraphRAG System (Port 8080)
│   ├── app.py                        # FastAPI master RAG app (run_rag.bat)
│   ├── src/
│   │   ├── fact_engine.py            # Deterministic numeric/temporal normalizer (INR, USD, Lakhs, Crores, FY vs AY)
│   │   ├── table_engine.py           # 2D table matrix grid parser preserving row/col header coordinates
│   │   ├── structure_chunker.py      # Context-enriched chunker (Anthropic Contextual Retrieval pattern)
│   │   ├── claim_verifier.py         # Anti-hallucination layer emitting machine-readable AnswerContract JSON
│   │   ├── comparative_engine.py     # Cross-institutional comparison evaluator (comparability matrix)
│   │   ├── reasoning_memory.py       # Trajectory memory store inspired by Google ReasoningBank 2026
│   │   ├── agent_router.py           # Multi-tool planner with Google Agentic RAG Evidence Sufficiency checks
│   │   ├── neo4j_engine.py           # Neo4j Bolt driver & live Cypher transaction executor
│   │   ├── vector_engine.py          # Local ChromaDB dense semantic vector store
│   │   ├── ingestion_adapter.py      # Canonical Document Model (CDM) & Docling/PyMuPDF adapter
│   │   ├── batch_ingest.py           # Batch discovery & ingestion of PDFs from Download/
│   │   └── rag_pipeline.py           # Master RAG pipeline coordinator
│   ├── evaluation/
│   │   ├── evaluate.py               # Automated benchmark harness (100% Grounded Accuracy baseline)
│   │   └── questions.json            # Golden benchmark test dataset
│   ├── docs/                         # Comprehensive architectural specifications & ADRs
│   ├── inspiration/                  # Cloned gold-standard repos & 2026 master inspiration brief
│   ├── static/ & templates/          # Agentic AI & Neo4j Cypher interactive dashboard
│   └── THIRD_PARTY_NOTICES.md        # Open-source licenses & research attributions
│
└── Download/                         # Staging vault for real university annual report PDFs
    ├── Annual Report 2024-25 final upload.pdf
    ├── BRIC-Annual-Report-2025-English.pdf
    ├── NIPGR_Annual_Report_2024-25.pdf
    └── Taxonomy_Stress_Test_Demo.pdf
```

---

## 4. End-to-End Pipeline & Data Flow

```text
                           RAW PDF IN DOWNLOAD/
                                    │
                                    ▼
                       CANONICAL DOCUMENT ADAPTER
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
     STRUCTURED JSON          SEMANTIC HTML5          PAGE EVIDENCE
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    │
                                    ▼
                         MULTI-SUBSTRATE INDEXING
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
       NEO4J GRAPH            CHROMADB VECTOR         FACT ENGINE
    (Community Nodes)       (Contextual Prefix)     (Numeric & FY)
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    │
                                    ▼
                         AGENTIC REASONING ROUTER
                                    │
                             ITERATIVE LOOP
                     (Evidence Sufficiency Check)
                                    │
                                    ▼
                         ANTI-HALLUCINATION LAYER
                         (Claim Verifier Badges)
                                    │
                                    ▼
                             ANSWER CONTRACT
```

---

## 5. Key Port & Service Allocations

| Service | Port / Protocol | Working Directory | Command to Run |
| :--- | :--- | :--- | :--- |
| **Document Workspace** | `http://127.0.0.1:8000` | `Document Workspace/` | `python app.py` or `run_app.bat` |
| **Master GraphRAG** | `http://127.0.0.1:8080` | `RAG/` | `python app.py` or `run_rag.bat` |
| **Neo4j Bolt Engine** | `bolt://localhost:7687` | Docker | Managed by Docker Desktop |
| **Neo4j Web Browser** | `http://localhost:7474` | Docker | Open in browser (neo4j / password123) |

---

## 6. How to Run the Automated Benchmark
To test tool selection, citation accuracy, and zero-hallucination enforcement:
```powershell
cd RAG
python evaluation/evaluate.py
```
Expected output: **4/4 Passed (100.0% Grounded Accuracy, Latency < 0.04s)**.
