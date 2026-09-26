# RAISE Multi-Substrate & LLM Provider Setup Guide

**Last Updated**: September 26, 2026, 04:40 PM IST  
**Version**: 3.0 (Enterprise RAG & Control Center Specification)  
**Applicability**: RAISE Backend (`FastAPI`), Desktop (`Tauri 2.0`), and Web Workstation  

---

## 1. Executive Summary & Architecture Matrix

RAISE (Reflective Agentic Intelligence & Synthesis Engine) is designed with a **pluggable, substrate-agnostic architecture**. It supports both **100% offline air-gapped local execution** and **sub-second cloud inference**, as well as a **Zero-Local-Download Web Client** operating through dynamic remote Cloudflare tunnels.

### Substrate Comparison Matrix

| Architectural Layer | Remote Cloud / Tunnel Mode | Local Workstation Mode | Zero-Dependency In-Memory Fallback |
| :--- | :--- | :--- | :--- |
| **Reasoning Engine** | Groq LPU, Gemini 2.5, NVIDIA NIM, OpenAI, Claude, DeepSeek | Local Ollama (`llama3.2:3b`, `qwen2.5:7b`) or vLLM | Failover down the provider priority chain |
| **Knowledge Graph** | Neo4j AuraDB Cloud (`neo4j+s://...`) | Local Neo4j Bolt (`bolt://localhost:7687`) | In-process Vector + Lexical RRF fallback |
| **Session Memory** | Neon Cloud PostgreSQL | Local Postgres (`localhost:5432`) | In-process Python session array |
| **Response Cache** | Upstash Cloud Redis (`rediss://...`) | Local Redis (`localhost:6379`) | In-memory key-value dictionary |
| **Vector DB** | Remote Tunnel Gateway | Local ChromaDB (`raise_docling_bge_large`) | In-process HNSW index |
| **Disk Footprint** | **0 GB** (Remote Tunnel) | **~4.6 GB** (Models + Embeddings) | Minimal |
| **Client Requirement**| Any modern browser or laptop | 8GB–16GB RAM (CPU) or 16GB+ VRAM (GPU) | 4GB RAM minimum |

---

## 2. Supported LLM Providers & Model Specifications

RAISE natively integrates 12 inference backends managed via `src.infrastructure.providers.llm.get_llm_provider()` and reactive frontend key detection.

### A. High-Speed Cloud Inference Providers

#### 1. Groq Cloud LPU (Recommended for Ultra-Low Latency)
- **Base URL**: `https://api.groq.com/openai/v1`
- **Key Prefix**: `gsk_...`
- **Supported Models**:
  - `llama-3.3-70b-versatile` (Primary production reasoning model)
  - `llama-3.1-8b-instant` (Sub-second triage & query routing)
- **Latency**: ~250–500ms (250–500 tokens/sec)
- **Configuration**:
  ```ini
  LLM_BACKEND=groq
  GROQ_API_KEY=gsk_your_groq_api_key_here
  GROQ_MODEL_NAME=llama-3.3-70b-versatile
  ```

#### 2. Google Gemini API
- **Base URL**: `https://generativelanguage.googleapis.com/v1beta/openai`
- **Key Prefix**: `AIzaSy...`
- **Supported Models**:
  - `gemini-2.5-flash` (Next-gen speed & long context)
  - `gemini-2.0-flash`
  - `gemini-1.5-pro` (Complex multi-document synthesis)
- **Configuration**:
  ```ini
  LLM_BACKEND=gemini
  GEMINI_API_KEY=AIzaSy_your_key_here
  GEMINI_MODEL_NAME=gemini-2.5-flash
  ```

#### 3. NVIDIA NIM Microservices
- **Base URL**: `https://integrate.api.nvidia.com/v1`
- **Key Prefix**: `nvapi-...`
- **Supported Models**:
  - `meta/llama-3.1-70b-instruct`
  - `mistralai/mixtral-8x22b-instruct`
  - `nvidia/nemotron-4-340b-instruct`
- **Configuration**:
  ```ini
  LLM_BACKEND=nvidia
  NVIDIA_API_KEY=nvapi-your_key_here
  NVIDIA_MODEL_NAME=meta/llama-3.1-70b-instruct
  ```

#### 4. Anthropic Claude
- **Base URL**: `https://api.anthropic.com/v1`
- **Key Prefix**: `sk-ant-...`
- **Supported Models**:
  - `claude-3-5-sonnet-20241022` (Superior code and complex relational logic)
  - `claude-3-5-haiku-20241022`
- **Configuration**:
  ```ini
  LLM_BACKEND=anthropic
  ANTHROPIC_API_KEY=sk-ant-your_key_here
  ANTHROPIC_MODEL_NAME=claude-3-5-sonnet-20241022
  ```

#### 5. OpenAI
- **Base URL**: `https://api.openai.com/v1`
- **Key Prefix**: `sk-...` / `sk-proj-...`
- **Supported Models**:
  - `gpt-4o` (Omni multi-modal)
  - `gpt-4o-mini` (Fast, cost-efficient evaluation)
  - `o3-mini` / `o1-mini` (Deep reasoning)
- **Configuration**:
  ```ini
  LLM_BACKEND=openai
  OPENAI_API_KEY=sk-your_key_here
  OPENAI_MODEL_NAME=gpt-4o
  ```

#### 6. DeepSeek API
- **Base URL**: `https://api.deepseek.com/v1`
- **Supported Models**: `deepseek-chat` (V3), `deepseek-reasoner` (R1)
- **Configuration**:
  ```ini
  LLM_BACKEND=deepseek
  DEEPSEEK_API_KEY=your_key_here
  DEEPSEEK_MODEL_NAME=deepseek-chat
  ```

#### 7. Mistral AI & Cohere
- **Mistral**: Key is 32-character hex; model: `mistral-large-latest`, `open-mistral-nemo`.
- **Cohere**: Key starts with `co-`; model: `command-r-plus-08-2024`.
- **OpenRouter**: Key starts with `sk-or-`; model: `anthropic/claude-3.5-sonnet`.

---

### B. Local On-Device Inference Engines

#### 1. Local Ollama Engine (Consumer Desktop / Laptop)
- **Endpoint**: `http://localhost:11434/v1`
- **Recommended Models**:
  - `llama3.2:3b` (~2.0 GB — optimal for 8 GB RAM machines)
  - `qwen2.5:7b` (~4.7 GB — balanced reasoning for 16 GB RAM machines)
  - `llama3.1:8b` (~4.9 GB)
- **Install & Start**:
  ```bash
  # Start Ollama service
  ollama run llama3.2:3b
  ```
- **Configuration**:
  ```ini
  LLM_BACKEND=ollama
  LLM_MODEL_NAME=llama3.2:3b
  LLM_BASE_URL=http://localhost:11434/v1
  ```

#### 2. Local vLLM Engine (Workstation with Dedicated GPU >= 16GB VRAM)
- **Endpoint**: `http://localhost:8002/v1`
- **Recommended Model**: `Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4`
- **Launch Command**:
  ```powershell
  python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4 --port 8002
  ```

---

## 3. Cloud Database Substrates

### A. Neo4j AuraDB Cloud (Property Graph)
1. Create a free instance at [console.neo4j.io](https://console.neo4j.io).
2. Note your **Instance ID** (e.g., `a1b2c3d4`), Connection URI, and Password.
3. Configure `.env`:
   ```ini
   NEO4J_URI=neo4j+s://a1b2c3d4.databases.neo4j.io
   NEO4J_USER=a1b2c3d4
   NEO4J_PASSWORD=your_password
   NEO4J_DATABASE=a1b2c3d4
   ```
   > ℹ️ *AuraDB Free Note*: On free instances, set `NEO4J_DATABASE` to your **Instance ID**.

### B. Upstash Cloud Redis (Sub-Millisecond Cache & Pub/Sub)
1. Create a free serverless Redis DB at [console.upstash.com](https://console.upstash.com).
2. Configure `.env`:
   ```ini
   REDIS_URL=rediss://default:YOUR_TOKEN@your-host.upstash.io:6379
   ```

### C. Neon Cloud PostgreSQL (Session & Turn Memory)
1. Create a project at [neon.tech](https://neon.tech) and copy your pooled connection URI.
2. Configure `.env`:
   ```ini
   POSTGRES_HOST=ep-cool-fog.ap-southeast-1.aws.neon.tech
   POSTGRES_PORT=5432
   POSTGRES_DB=neondb
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_password
   ```

---

## 4. Ephemeral Web Gateway Tunnel Mode

When accessing RAISE over the web or mobile without running local heavy models:
- **No Local Downloads**: All neural models (`bge-large-en-v1.5`, `bge-reranker-large`, `FineCat-NLI`) and vector databases execute on the gateway.
- **Dynamic Ephemeral URLs**: Cloudflare tunnels (`https://xxxx.trycloudflare.com`) change periodically. Enter the active URL in the Control Center; zero URLs are hardcoded or permanently saved into git or `.env`.
- **1-Click Switching**: Use `Clear URL` or `(×)` to update links instantly with live round-trip latency checks.

---

## 5. Universal Control Center (Mission Control) Features

The frontend Control Center modal provides:
1. **Device & OS Auto-Detection**: Accurately recognizes macOS (Metal), Windows (DirectML/CUDA), Linux (CUDA/ROCm), and Web Client.
2. **Multi-Key Intelligence Engine**:
   - Live format detection (`keyDetector.ts`) identifying provider from prefix (`gsk_`, `AIzaSy`, `nvapi-`, `sk-ant-`, `sk-`).
   - Per-key **`Check Connection`** button measuring round-trip latency in milliseconds.
   - Dynamic `+ Add Key` and delete controls.
3. **Connection Health Gating**:
   - When any database substrate is set to `Cloud`, the wizard **disables the Next button** until the connection is actively tested and verified healthy.
4. **Summary & Pre-Flight Scorecard**:
   - Full breakdown of memory footprint, storage usage, and network isolation before clicking **`Start`**.

---

## 6. Zero-Crash Fallback Architecture

If an inference backend becomes unreachable:
1. The backend evaluates socket availability before triggering generation.
2. If the chosen model is offline, it cascades down the fallback ladder:
   $$\text{Local vLLM / Ollama} \longrightarrow \text{Groq LPU} \longrightarrow \text{Google Gemini} \longrightarrow \text{NVIDIA NIM} \longrightarrow \text{OpenAI}$$
3. Outputs continue to pass through the **Runtime Faithfulness Quality Gate** and citation verification shield.
