# 🗺️ RAISE Master System Topology & Environment Connection Map
> **Authoritative Connection Blueprint for AI Agents & Developers**
> **Do not modify without updating this central specification.**

---

## 1. Physical Directory & Environment Mapping

```text
====================================================================================================
ENVIRONMENT / WORKSPACE       PHYSICAL PATH                                ROLE & RULES
====================================================================================================
1. Root Workspace (Windows)   C:\Users\Siddharth Tripathi\Documents\raise  Master Project Root
2. Upstream Document Service  ...\raise\Document Workspace                 Port 8000 (Semantic HTML5)
3. Master GraphRAG Service    ...\raise\RAG                                Port 8080 (Agentic AI & UI)
4. Raw Source Vault           ...\raise\Download                           READ-ONLY PDF Reports
5. Processed Data Artifacts   ...\raise\RAG\data\processed                 Chunks, Facts & Triples
6. Windows HuggingFace Cache  C:\Users\Siddharth Tripathi\.cache\huggingface Pre-cached MiniLM-L6-v2
7. WSL2 GraphRAG Workspace    ~/Desktop/GraphRAG/                          WSL2 GraphRAG & LLM Stack
8. WSL2 MangaRecap AI         ~/Desktop/MangaRecapAI/tts_env               STRICTLY LOCKED (DO NOT TOUCH)
====================================================================================================
```

---

## 2. Network Ports, Databases & Service Endpoints

```text
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ SERVICE NAME         ENDPOINT PROTOCOL            DEFAULT CREDENTIALS     PURPOSE                 │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Master GraphRAG UI   http://127.0.0.1:8080        None                    Interactive RAG Web UI  │
│ Document Workspace   http://127.0.0.1:8000        None                    Upstream Viewer         │
│ Neo4j Bolt Driver    bolt://localhost:7687        neo4j / password123     Cypher Property Graph   │
│ Neo4j Browser Console http://localhost:7474       neo4j / password123     Visual Database Web UI  │
│ ChromaDB Vector DB   Embedded in RAG/.chromadb    Local File Lock         Dense Cosine Embeddings │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Strict Dual-Workload Isolation Contract

```text
                             NVIDIA GeForce RTX 3090 (24 GB VRAM)
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
   ┌─────────────────────────────┐                 ┌─────────────────────────────┐
   │ WORKLOAD 1: MANGA RECAP AI  │                 │ WORKLOAD 2: GraphRAG AI     │
   │ (WSL2 Ubuntu Subsystem)     │                 │ (Windows & WSL2 Workspaces) │
   ├─────────────────────────────┤                 ├─────────────────────────────┤
   │ Path:                       │                 │ Windows Path:               │
   │ /home/siddharth_tripathi/   │                 │ C:\Users\Siddharth Tripathi\│
   │ Desktop/MangaRecapAI/       │                 │ Documents\raise\RAG         │
   │ tts_env                     │                 │                             │
   │                             │                 │ WSL2 Path:                  │
   │ Model: Qwen3-TTS-1.7B       │                 │ ~/Desktop/GraphRAG/         │
   │                             │                 │                             │
   │ Status: LOCKED / UNTOUCHED  │                 │ Model: Qwen2.5 Text LLM     │
   │ DO NOT MODIFY ANYTHING      │                 │ Database: Docker Neo4j      │
   └─────────────────────────────┘                 └─────────────────────────────┘
```

> [!CAUTION]
> **RULE FOR ALL AI AGENTS**: Never touch, upgrade, downgrade, or run pip inside `/home/siddharth_tripathi/Desktop/MangaRecapAI/tts_env`.

---

## 4. End-to-End Data & Execution Flow

```text
                               RAW PDF IN DOWNLOAD/
             (IIT Madras, BRIC, IITMRP, NIPGR, AstraBio Annual Reports)
                                       │
                                       ▼
                       ACADEMIC INGESTION PIPELINE
                     (RAG/src/pipeline_academic_ingest.py)
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
     CHROMA VECTOR STORE          NEO4J GRAPH               FACT ENGINE
    (114 Context Chunks)     (bolt://localhost:7687)     (INR, Lakhs, Crores,
    (MiniLM-L6-v2 Embeds)    (58 Academic Triples)        FY vs AY Normalizer)
            │                          │                          │
            └──────────────────────────┼──────────────────────────┘
                                       │
                                       ▼
                           AGENTIC REASONING ROUTER
                         (RAG/src/agent_router.py)
                                       │
                       EVIDENCE SUFFICIENCY CHECK
                       (Iterative Retrieval Loop)
                                       │
                                       ▼
                           CLAIM VERIFICATION LAYER
                        (RAG/src/claim_verifier.py)
                                       │
                                       ▼
                            ANSWER CONTRACT (JSON)
                 (Grounded Answer + Page Citations + BBoxes)
                                       │
                                       ▼
                       INTERACTIVE DASHBOARD (PORT 8080)
```

---

## 5. Required Environment Variables

When executing scripts or starting server services, the following environment variables are used:

| Variable Name | Default Value | Purpose |
| :--- | :--- | :--- |
| `NEO4J_URI` | `bolt://localhost:7687` | Connection URI to Docker Neo4j |
| `NEO4J_USER` | `neo4j` | Neo4j database username |
| `NEO4J_PASSWORD` | `password123` | Neo4j database password |
| `NEO4J_DATABASE` | `neo4j` | Target database name |
| `PYTHONIOENCODING` | `utf-8` | Fixes Windows console charmap encoding for emojis and symbols |
| `PYTHONUTF8` | `1` | Enables strict UTF-8 mode across all Python subprocesses |

---

## 6. Common Command Quick-Reference

### A. Run Master Agentic GraphRAG System (Port 8080):
```powershell
cd "C:\Users\Siddharth Tripathi\Documents\raise\RAG"
python app.py
```

### B. Run Upstream Document Semantification (Port 8000):
```powershell
cd "C:\Users\Siddharth Tripathi\Documents\raise\Document Workspace"
python app.py
```

### C. Run Full Academic PDF Ingestion on `Download/`:
```powershell
cd "C:\Users\Siddharth Tripathi\Documents\raise\RAG"
python src/pipeline_academic_ingest.py
```

### D. Run Automated Benchmark Evaluation:
```powershell
cd "C:\Users\Siddharth Tripathi\Documents\raise\RAG"
python evaluation/evaluate.py
```
*(Expected Score: 4/4 Passed - 100% Grounded Accuracy)*

### E. Start Docker Neo4j Container:
```powershell
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:latest
```
*(Or `docker start neo4j` if already created)*
