# 🚀 RAISE Academic GraphRAG Studio

A local, offline-first **Hybrid GraphRAG** (ChromaDB + Neo4j + LangGraph) system designed for academic, institutional, and financial annual reports.

---

## 🌟 Architecture Overview

```
                                  [ User Research Query ]
                                             │
                   ┌─────────────────────────┴─────────────────────────┐
                   ▼                                                   ▼
      [ 1. Semantic Vector Search ]                 [ 2. Text-to-Cypher Traversal ]
                   │                                                   │
         ChromaDB (Vector Store)                    Neo4j (Knowledge Graph)
                   │                                                   │
      Returns Top-k Chunk IDs                         Executes Multi-Hop Cypher
                   │                                                   │
                   └─────────────────────────┬─────────────────────────┘
                                             ▼
                                [ 3. Hybrid Context Fusion ]
                     (Neo4j traverses Chunk ID -> Section -> Entities)
                                             │
                                             ▼
                                [ 4. Anti-Hallucination Gate ]
                        (Synthesizes answer with [1], [2] page citations)
```

---

## 📋 Prerequisites

1. **Python 3.10 to 3.13** (Windows / macOS / Linux)
2. **Docker Desktop** (optional, for local Neo4j container)

---

## ⚡ Quick Start (Windows, macOS, Linux)

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/semanticClimate/RAISE.git
cd RAISE/RAG

# Create and activate a virtual environment
python -m venv venv

# Windows (Command Prompt / PowerShell)
.\venv\Scripts\activate

# Linux / macOS / WSL
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Start Databases

#### Option A: 1-Click with Docker (Recommended)
```bash
# Start Neo4j container with default credentials (neo4j / password123)
docker compose up neo4j -d
```
* Access the visual Neo4j Browser at: [http://localhost:7474](http://localhost:7474)

#### Option B: Zero Docker (In-Memory Fallback)
If Docker is not running, the system will automatically and seamlessly fall back to the built-in fast **In-Memory NetworkX Graph Engine**.

---

## 🎮 How to Run

### 1. Interactive Terminal Studio (LangGraph + Neo4j + Vector RAG)
```bash
python main.py
```
This will:
- Auto-detect Neo4j (or use fast in-memory graph fallback)
- Render the LangGraph StateGraph Mermaid topology
- Open an interactive multi-hop research Q&A prompt
- **Linux / macOS**:
  ```bash
  python main.py
  ```

### 2. Interactive Web UI & API Server
```bash
uvicorn app:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🧪 Running Automated Tests

Run the complete 37-test automated benchmark suite:

```bash
pytest tests/ -q
```

---

## 🔧 Environment Configuration (`.env`)

Create or edit `.env` in `RAG/`:

```ini
# Neo4j Settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
NEO4J_DATABASE=neo4j

# LLM & Embedding Settings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_TEMPERATURE=0.1

# Logging
RAISE_LOG_LEVEL=INFO
```

---

## 📂 Project Structure

```
RAG/
├── src/
│   ├── config.py              # Central typed configuration
│   ├── neo4j_schema.py        # 35+ node labels, 50 relationships, index automation
│   ├── neo4j_engine.py        # Neo4j driver, live Cypher & graph sync
│   ├── vector_engine.py       # ChromaDB dense vector store
│   ├── structure_chunker.py   # Contextual chunker with page provenance
│   ├── langgraph_workflow.py  # 5-Node LangGraph StateGraph engine
│   ├── agent_router.py        # Autonomous multi-tool reasoning router
│   ├── claim_verifier.py      # Anti-hallucination citation verifier
│   └── reasoning_memory.py    # Cross-turn trajectory memory
├── tests/                     # 37 Automated pytest test suites
├── data/
│   ├── documents/             # Raw uploaded academic PDFs
│   └── processed/             # Extracted chunks, manifests, and graph triples
├── logs/                      # Rotating pipeline execution logs
├── main.py                    # Terminal Studio runner & graph visualizer
├── app.py                     # FastAPI server & Web UI backend
├── run_cli.bat                # 1-Click Windows execution script
├── docker-compose.yml         # Container stack specification
└── requirements.txt           # Clean, unbloated production dependencies
```
