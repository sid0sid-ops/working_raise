# RAISE Multi-Backend AI Inference & Cloud Infrastructure Setup Guide
=============================================================================

> **Architecture Overview**: RAISE supports both high-throughput local inference (**vLLM** and **Ollama**) and **zero-GPU Cloud APIs** (Groq, Google Gemini, DeepSeek, Neo4j AuraDB, Upstash Redis, Neon Postgres). Anyone who clones this repository can run the entire workstation immediately on standard laptops, MacBooks, workstations, or servers.

---

## 1. Inference Profiles: Cloud vs. Local Matrix

RAISE features two core operational profiles that can be selected in the **Control Center GUI** or configured in `.env`:

| Feature | ☁️ 100% Cloud Profile (Zero Hardware Required) | 💻 Local / Offline Profile (100% Private) |
| :--- | :--- | :--- |
| **Primary LLM** | **Groq Cloud** (Llama 3.3 70B) or **Google Gemini 2.5 Flash** | **Local Ollama** (Llama 3.2 3B / Qwen 2.5 7B) or **vLLM** (Qwen 2.5 14B) |
| **Graph DB** | **Neo4j AuraDB Cloud** (`neo4j+s://...`) | Local Neo4j Bolt (`bolt://localhost:7687`) or **Dense Vector + BM25 Fallback** |
| **Cache & Pub/Sub** | **Upstash Cloud Redis** (`rediss://...` with TLS) | Local Redis (`localhost:6379`) or **Zero-dependency In-Memory Cache** |
| **Relational DB** | **Neon Cloud PostgreSQL** | Local Postgres or **Zero-dependency In-Memory Session Store** |
| **Vector DB** | **Local ChromaDB** (`BAAI/bge-large-en-v1.5`) | **Local ChromaDB** (`BAAI/bge-large-en-v1.5`) |
| **Target Hardware** | Any Laptop (Mac, Windows, Linux, 4GB+ RAM) | Dedicated GPU (vLLM) or 8GB–16GB RAM CPU (Ollama) |
| **Setup Time** | **< 2 minutes** | 5–15 minutes (model download dependent) |

---

## 2. Supported LLM Providers & Current Models

### A. Cloud Inference Providers

1. **Groq Cloud API (Recommended for Cloud Speed)**
   * **Base URL**: `https://api.groq.com/openai/v1`
   * **Supported Models**:
     * `llama-3.3-70b-versatile` (State-of-the-art reasoning, ultra-fast LPU generation)
     * `llama-3.1-8b-instant` (Fastest completion speed)
   * **Latency**: **~0.4s – 0.8s** (200–500 tokens/sec)
   * **Environment Variables**:
     ```ini
     LLM_BACKEND=groq
     GROQ_API_KEY=gsk_your_groq_api_key_here
     GROQ_MODEL_NAME=llama-3.3-70b-versatile
     ```

2. **Google Gemini API**
   * **Base URL**: `https://generativelanguage.googleapis.com/v1beta/openai`
   * **Supported Models**:
     * `gemini-2.5-flash` (High-speed multimodal, large context window)
     * `gemini-2.0-flash` / `gemini-1.5-pro`
   * **Latency**: **~1.2s – 1.8s**
   * **Environment Variables**:
     ```ini
     LLM_BACKEND=gemini
     GEMINI_API_KEY=your_gemini_api_key_here
     GEMINI_MODEL_NAME=gemini-2.5-flash
     ```

3. **DeepSeek API**
   * **Base URL**: `https://api.deepseek.com/v1`
   * **Supported Models**: `deepseek-chat`, `deepseek-reasoner`
   * **Environment Variables**:
     ```ini
     LLM_BACKEND=deepseek
     DEEPSEEK_API_KEY=your_deepseek_api_key_here
     ```

---

### B. Local Inference Engines

1. **Local Ollama Engine (Consumer Hardware / Mac / Laptops)**
   * **Base URL**: `http://localhost:11434/v1`
   * **Recommended Models**:
     * `llama3.2:3b` (~2.0 GB download — runs smoothly on 8GB RAM laptops)
     * `qwen2.5:7b` (~4.7 GB download — strong reasoning balance)
     * `llama3.1:8b` (~4.9 GB download)
   * **Installation**:
     * **Windows**: Download installer from [ollama.com/download/windows](https://ollama.com/download/windows)
     * **macOS**: `brew install ollama` or download DMG from [ollama.com/download/mac](https://ollama.com/download/mac)
     * **Linux**: `curl -fsSL https://ollama.com/install.sh | sh`
   * **Command to Run**:
     ```bash
     ollama run llama3.2:3b
     ```
   * **Environment Variables**:
     ```ini
     LLM_BACKEND=ollama
     LLM_MODEL_NAME=llama3.2:3b
     LLM_BASE_URL=http://localhost:11434/v1
     ```

2. **Local vLLM Engine (High-End Dedicated GPUs >= 16GB VRAM)**
   * **Base URL**: `http://localhost:8002/v1`
   * **Supported Model**: `Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4`
   * **Hardware Requirements**: NVIDIA RTX 3090, 4090, A5000, or A100.
   * **Launch Script**:
     ```powershell
     # Windows PowerShell
     .\backend\scripts\launch_vllm.ps1
     ```

---

## 3. Cloud Database Configuration

### A. Upstash Cloud Redis (Sub-Millisecond Query Caching)
Upstash provides serverless Redis with TLS encryption.

1. **Get Credentials**:
   * Create an account at [console.upstash.com](https://console.upstash.com).
   * Create a free Redis database and copy the **Node/Python Redis Connection URL** (`rediss://...`).
2. **Configure `.env`**:
   ```ini
   REDIS_URL=rediss://default:YOUR_TOKEN@your-host.upstash.io:6379
   UPSTASH_REDIS_REST_URL=https://your-host.upstash.io
   UPSTASH_REDIS_REST_TOKEN=YOUR_TOKEN
   ```
3. **Graceful Fallback**:
   * If `REDIS_URL` is omitted or disconnected, RAISE automatically switches to its built-in in-memory dictionary cache. Zero crashes occur.

---

### B. Neo4j AuraDB Cloud (Managed Property Graph)
Neo4j AuraDB provides cloud-hosted Neo4j graph instances.

1. **Get Credentials**:
   * Go to [console.neo4j.io](https://console.neo4j.io) and create an **AuraDB Free** instance.
   * Note down your **Instance ID** (e.g., `7639347a`), **Connection URI** (`neo4j+s://...`), and **Password**.
2. **Configure `.env`**:
   ```ini
   NEO4J_URI=neo4j+s://<YOUR_INSTANCE_ID>.databases.neo4j.io
   NEO4J_USER=<YOUR_INSTANCE_ID>
   NEO4J_PASSWORD=YOUR_PASSWORD
   NEO4J_DATABASE=<YOUR_INSTANCE_ID>
   NEO4J_CONNECTION_TIMEOUT=10.0
   ```
   > ⚠️ **Important AuraDB Free Note**: On Aura Free Tier instances, the database name is typically your **Instance ID** (not `neo4j`).

3. **Graceful Fallback**:
   * If Neo4j is offline or credentials are missing, RAISE retrieves context using **Dense Vector Search (ChromaDB) + Sparse Lexical Search (BM25)** without breaking the pipeline.

---

### C. Neon Cloud PostgreSQL (Session & Chat History Storage)
Neon provides serverless PostgreSQL with connection pooling.

1. **Get Credentials**:
   * Go to [neon.tech](https://neon.tech) and copy your connection string.
2. **Configure `.env`**:
   ```ini
   POSTGRES_HOST=ep-your-endpoint-id.ap-southeast-1.aws.neon.tech
   POSTGRES_PORT=5432
   POSTGRES_DB=neondb
   POSTGRES_USER=your_neon_user
   POSTGRES_PASSWORD=your_neon_password
   ```
3. **Graceful Fallback**:
   * If Postgres is offline, `PostgresManager` transparently falls back to in-memory session arrays (`_memory_chat`, `_memory_docs`).

---

## 4. Control Center GUI & First-Run Wizard

RAISE includes a dedicated **Universal Control Center** accessible in two ways:
1. **Web Browser (`npm run dev`)**: Connects to the FastAPI backend API at `http://localhost:8000/api/system`.
2. **Native Desktop App (`npm run tauri dev`)**: Built with Tauri 2.0 Rust IPC for hardware probing and model downloads.

### Available System Endpoints:
* `GET /api/system/hardware` — Real-time telemetry (CPU cores, RAM usage, GPU/VRAM, Ollama status, and profile recommendation).
* `GET /api/system/config` — View active configuration with masked API keys.
* `POST /api/system/config` — Hot-update `.env` and active memory settings without restarting Python.
* `POST /api/system/test-connections` — Test live connectivity to Upstash, Neo4j AuraDB, and LLM inference.

---

## 5. Automated Zero-Crash Failover Architecture

If a user selects `vllm` or `ollama` on a computer without the required software running:
1. The backend tests the port connection before invoking generation.
2. If the local endpoint is unreachable, RAISE **does not crash**.
3. It logs a clean fallback event and automatically shifts down the fallback chain:
   $$\text{Local vLLM / Ollama} \longrightarrow \text{Groq Cloud} \longrightarrow \text{Google Gemini} \longrightarrow \text{DeepSeek}$$
4. The synthesized response undergoes the exact same mathematical validation, citation verification, and faithfulness quality gate.

---

## 6. Common Troubleshooting & FAQs

### Q1: Groq returns `HTTP 404 (MODEL_UNAVAILABLE)`
* **Fix**: Ensure your `GROQ_MODEL_NAME` is set to an active model such as `llama-3.3-70b-versatile` or `llama-3.1-8b-instant`. Deprecated model identifiers like `llama-3.1-70b-versatile` may be discontinued.

### Q2: Neo4j Aura returns `Unable to get a routing table for database 'neo4j'`
* **Fix**: In AuraDB Free, set `NEO4J_DATABASE` to your **Instance ID** (e.g., `7639347a`) rather than the default `neo4j`.

### Q3: Upstash Redis connection error
* **Fix**: Verify your URL starts with `rediss://` (with double 's' for TLS) and ends with `:6379`. If you are behind a corporate proxy, check that outbound port `6379` is open.

### Q4: How do I switch back from Cloud to Local?
* In the frontend header, click **`[ Control Center ⚙️ ]`**, choose **"Local Ollama"**, select your model (`llama3.2:3b`), and click **"Save & Apply"**.
