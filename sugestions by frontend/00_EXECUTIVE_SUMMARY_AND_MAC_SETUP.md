# RAISE Backend: Mac Air Setup, Resource Estimates & Cloud Migration

**Target Repository**: `https://github.com/sid0sid-ops/working_raise.git` (Branch: `backend`)  
**Target Hardware**: Apple Mac Air Book (Apple Silicon M1 / M2 / M3 / M4, 8 GB – 16 GB Unified Memory)  
**Date**: September 2026  

---

## 1. Executive Feasibility: Running on a MacBook Air

### Can it run on your MacBook Air?
**YES, but NOT with the default `docker-compose.yml` and local vLLM container.**

The repository as uploaded is currently hard-configured for an **NVIDIA Linux/Windows Workstation with 24GB+ VRAM (RTX 3090 / 4090)**. 

### Why the Default Setup Fails on MacBook Air:
1. **NVIDIA GPU Lock-in**: The `docker-compose.yml` file configures the `vllm` service with `capabilities: [gpu]` and `driver: nvidia`. Docker on macOS runs inside a Linux hypervisor and **cannot access Apple Silicon GPU via NVIDIA CUDA drivers**. The container will crash with:
   ```text
   could not select device driver "nvidia" with capabilities: [[gpu]]
   ```
2. **Aggressive Neo4j RAM Allocation**: In `docker-compose.yml`, Neo4j is configured with:
   - Initial Heap: `8 GB`
   - Max Heap: `12 GB`
   - Page Cache: `16 GB`  
   **Total: ~28–36 GB RAM allocated to Neo4j alone.** On an 8GB or 16GB MacBook Air, Docker will either OOM-kill (Out Of Memory) Neo4j or lock the macOS kernel in swap thrashing.
3. **Hardcoded CUDA in Embeddings**: In `src/core/config.py`, `EMBEDDING_DEVICE` defaults to `"cuda"`. On macOS, this triggers PyTorch CUDA errors unless overridden to `"mps"` (Apple Metal) or `"cpu"`.
4. **Service Dependency Chain**: In `docker-compose.yml`, the `backend` container has `depends_on: vllm: condition: service_healthy`. If vLLM fails to start (which it will on macOS), the backend server **refuses to launch entirely**.

---

## 2. Step-by-Step: How to Run RAISE on a MacBook Air

To run RAISE smoothly on your MacBook Air, use **Cloud LLM Mode** (Groq / Gemini) and lightweight database settings:

### Step 1: Install System Prerequisites via Homebrew
Open Terminal on your Mac and install Python 3.11, Docker, and utilities:
```bash
# 1. Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python 3.11 and Rust toolchain (required for raise_engine)
brew install python@3.11 rust cmake

# 3. (Optional) Install Docker Desktop for Mac
brew install --cask docker
```

### Step 2: Clone and Setup Virtual Environment
```bash
git clone --branch backend https://github.com/sid0sid-ops/working_raise.git raise_backend
cd raise_backend

# Create Python 3.11 virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Upgrade pip & install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```
> [!NOTE]
> Remove `httpx2>=2.12.0` from `requirements.txt` before running `pip install` (it is a duplicate/typo of `httpx`).

### Step 3: Configure `.env` for Mac Air & Free Cloud APIs
Create or update `.env` in the root folder with this lightweight, Mac-compatible configuration:

```ini
# ==============================================================================
# MACBOOK AIR LIGHTWEIGHT CONFIGURATION (ZERO-GPU / CLOUD INFERENCE)
# ==============================================================================

# 1. Backend & Inference Mode (Use Groq or Gemini for free high-speed inference)
LLM_BACKEND=groq
EXECUTION_MODE=CLOUD

# Groq API (Get free key from https://console.groq.com)
GROQ_API_KEY=gsk_your_free_groq_key_here
GROQ_MODEL_NAME=qwen/qwen3.8-27b

# OR Google Gemini API (Get free key from https://aistudio.google.com)
# LLM_BACKEND=gemini
# GEMINI_API_KEY=AIzaSy_your_free_gemini_key_here
# GEMINI_MODEL_NAME=gemini-2.0-flash

# 2. Embeddings Hardware (Apple Silicon Metal Acceleration)
EMBEDDING_DEVICE=mps
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5

# 3. Neo4j Graph Database (Tune memory to fit 8GB/16GB Mac)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
NEO4J_HEAP_INITIAL_SIZE=512m
NEO4J_HEAP_MAX_SIZE=1G
NEO4J_PAGECACHE_SIZE=1G

# 4. Redis & Postgres (Local or Cloud)
REDIS_URL=redis://localhost:6379/0
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=raise_user
POSTGRES_PASSWORD=raise_password
POSTGRES_DB=raise_db

# 5. Server Port
PORT=8000
HOST=0.0.0.0
```

### Step 4: Launch Databases (Lightweight Mac Compose)
Run only Postgres, Redis, and tuned Neo4j (skipping the heavy vLLM container):
```bash
docker compose up -d postgres redis neo4j
```

### Step 5: Start the Backend Server
```bash
source .venv/bin/activate
python server.py
# Or for the interactive CLI studio:
# python main.py --llm groq
```
The server will now be live on `http://localhost:8000` and ready to connect with the RAISE React frontend!

---

## 3. Storage (Disk Space) and RAM Requirements

### Disk Space Breakdown:
| Component | Default GPU Setup | MacBook Air (Cloud LLM) | Notes |
| :--- | :--- | :--- | :--- |
| **Codebase & Git** | ~150 MB | ~150 MB | Core repository |
| **Python Virtualenv** | ~8.5 GB | ~5.5 GB | PyTorch, Docling, Transformers |
| **Embedding Weights** | ~1.34 GB | ~1.34 GB | `BAAI/bge-large-en-v1.5` cached locally |
| **Local LLM Model** | ~9.5 GB | **0 GB** | Stored on Groq/Gemini Cloud servers |
| **Database Data** | ~2–5 GB | ~1–2 GB | Ingested PDF chunks, vectors & triples |
| **Docker Images** | ~22 GB (vLLM image) | **~3 GB** | Only lightweight Alpine images |
| **TOTAL DISK SPACE** | **~43 GB** | **~8–10 GB** | **Easily fits on 256GB Mac Air SSD** |

### RAM (Memory) Requirements:
| Subsystem | Local GPU Production | MacBook Air (Cloud Mode) | MacBook Air (Local Ollama) |
| :--- | :--- | :--- | :--- |
| **FastAPI + LangGraph** | ~1.5 GB | ~1.2 GB | Python runtime |
| **BGE-Large Embeddings**| ~2.0 GB (VRAM) | ~1.5 GB (MPS / CPU) | In-memory during ingestion |
| **Neo4j Graph** | 28 GB (heap+cache) | **1.5 GB** (tuned) | Or 0 GB via Neo4j Aura Cloud |
| **Redis Cache** | 4 GB | **256 MB** | In-memory key-value cache |
| **PostgreSQL** | 1 GB | **512 MB** | Relational metadata |
| **LLM Inference** | 16–24 GB VRAM | **0 MB** (Handled in Cloud) | ~5 GB (if running Ollama 7B) |
| **MINIMUM SYSTEM RAM** | **32 GB – 64 GB** | **8 GB – 16 GB** | **16 GB** |

---

## 4. 100% Free Cloud Infrastructure Alternatives

To eliminate local resource constraints on your MacBook Air completely, you can utilize the following verified free cloud tiers:

```mermaid
flowchart TD
    User["MacBook Air / Frontend"] --> API["FastAPI Gateway (Local / Cloud)"]
    API --> LLM["Groq Cloud API (Free LPU) / Gemini Flash"]
    API --> Graph["Neo4j AuraDB Free (Cloud Graph)"]
    API --> DB["Supabase / Neon (Free PostgreSQL)"]
    API --> Cache["Upstash (Free Serverless Redis)"]
    API --> Storage["Cloudflare R2 (10GB Free S3 PDF Storage)"]
```

### 1. Free Cloud LLM Inference:
* **Groq Cloud API** (`https://console.groq.com`):
  * **Cost**: $0.00 / Free tier.
  * **Speed**: **~400–600 tokens/second** (up to 10x faster than local vLLM).
  * **Supported Models**: `qwen/qwen3.8-27b`, `llama-3.3-70b-versatile`, `deepseek-r1-distill-llama-70b`.
  * **Rate Limit**: 30 Requests/Min, 14,400 Requests/Day (more than enough for research).
* **Google Gemini API** (`https://aistudio.google.com`):
  * **Cost**: $0.00 / Free tier.
  * **Supported Models**: `gemini-2.0-flash`, `gemini-1.5-pro`.
  * **Context Window**: 1 Million tokens. Free tier allows 15 RPM / 1,500 RPD.

### 2. Free Cloud Graph Database:
* **Neo4j AuraDB Free** (`https://neo4j.com/cloud/platform/aura-graph-database/`):
  * **Cost**: 100% Free Forever.
  * **Capacity**: 1 free database instance, up to **200,000 nodes** and **400,000 relationships**.
  * **Benefit**: Saves 2 GB – 4 GB RAM on your Mac. You simply set `NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io` in `.env`.

### 3. Free Managed Relational Database:
* **Supabase** (`https://supabase.com`) or **Neon** (`https://neon.tech`):
  * **Cost**: Free tier with 500 MB storage, pooling, and automated backups.
  * **Benefit**: Zero local Postgres process required.

### 4. Free Serverless Redis:
* **Upstash Redis** (`https://upstash.com`):
  * **Cost**: Free tier with 10,000 commands per day.
  * **Benefit**: Zero local Redis process required. Set `REDIS_URL=rediss://default:password@xxx.upstash.io:6379`.

### 5. Free PDF Object Storage:
* **Cloudflare R2** (`https://www.cloudflare.com/developer-platform/products/r2/`):
  * **Cost**: 10 GB free storage per month with **$0 egress fees** (AWS S3 charges egress).
  * **Benefit**: Host academic PDFs on the cloud and stream directly to the browser.

---

## 5. Portability Blueprint: How to Make RAISE "Clone & Run Anywhere"

To allow any developer (on Mac, Windows, Linux, or Cloud) to clone and start RAISE in **1 command**, the backend developer should implement these 4 enhancements:

### A. Docker Compose Profiles
Update `docker-compose.yml` with profiles so GPU services do not block non-GPU users:
```yaml
services:
  # Base services: runs on all machines
  postgres:
    profiles: ["all", "cloud", "local-gpu"]
    ...
  redis:
    profiles: ["all", "cloud", "local-gpu"]
    ...
  neo4j:
    profiles: ["all", "cloud", "local-gpu"]
    ...
  
  # GPU service: only runs when explicitly requested
  vllm:
    profiles: ["local-gpu"]
    ...
  
  backend:
    profiles: ["all", "cloud", "local-gpu"]
    # Remove mandatory dependency on vllm
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      neo4j: { condition: service_healthy }
```
Now:
* **On MacBook Air**: `docker compose --profile cloud up -d` (starts only DBs, uses Cloud LLM).
* **On GPU Server**: `docker compose --profile local-gpu up -d` (starts full stack with local vLLM).

### B. Single-Command Launch Script (`setup.sh`)
Add a cross-platform detection script `run.sh` to the root:
```bash
#!/usr/bin/env bash
set -e

# Detect OS
OS_TYPE="$(uname -s)"
if [ "$OS_TYPE" = "Darwin" ]; then
    echo "🍏 Apple Silicon macOS detected. Configuring MPS acceleration and Cloud LLM..."
    export EMBEDDING_DEVICE="mps"
    export LLM_BACKEND="groq"
fi

# Ensure .env exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️ Created .env from .env.example. Please add your GROQ_API_KEY or GEMINI_API_KEY."
fi

# Start services
python3 server.py
```

### C. Fallback for Local Vector Embeddings
If downloading the 1.34 GB `BAAI/bge-large-en-v1.5` model is too heavy for casual users, support a lightweight fallback:
* Default to `sentence-transformers/all-MiniLM-L6-v2` (only 80 MB download, runs instantly on any Mac CPU).
