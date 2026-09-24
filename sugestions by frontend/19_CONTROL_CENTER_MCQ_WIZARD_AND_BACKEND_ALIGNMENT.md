# 19. Control Center MCQ Questionnaire Wizard & Substrate Alignment Spec

> **Status**: Verified & Implemented in `src/features/control-center/`  
> **Test Coverage**: 29/29 Vitest Suites (251/251 Tests Passing)  
> **Production Build**: Clean Vite + TypeScript build (1.55s)

---

## 1. Executive Summary & Design Rationale

The RAISE Control Center has been revamped into an ultra-easy, user-friendly **Multiple Choice Question (MCQ) & Card-Selection Questionnaire Wizard**.

### Core Architecture Principles:
1. **Modular Sub-Components**: Located cleanly in `src/features/control-center/steps/`:
   - [`PlatformStep.tsx`](file:///Users/sid/Documents/project/Frontend/src/features/control-center/steps/PlatformStep.tsx): Device & OS selection with live Rust/browser hardware detection badge.
   - [`EngineStep.tsx`](file:///Users/sid/Documents/project/Frontend/src/features/control-center/steps/EngineStep.tsx): Cloud vs Local AI reasoning with explicit download size, setup timing, RAM requirements, and free API key guides.
   - [`DatabaseStep.tsx`](file:///Users/sid/Documents/project/Frontend/src/features/control-center/steps/DatabaseStep.tsx): Neo4j Knowledge Graph, Postgres, and Redis configuration with zero-crash fallback guarantees.
   - [`LaunchStep.tsx`](file:///Users/sid/Documents/project/Frontend/src/features/control-center/steps/LaunchStep.tsx): Workstation scorecard, live pre-flight diagnostic connectivity checks, and 1-click launch.
2. **First-Run Onboarding + On-Demand Settings Access**:
   - Auto-launches upon cloning the repository when `firstRunCompleted === false`.
   - Accessible anytime via **Settings Modal -> About Tab -> "Mission Control" button**.
3. **Explicit Timing, Space, and Key Indicators**:
   - Every choice explicitly displays: **Timing** (e.g. `Instant ~15s` vs `~2-5 min download`), **Disk Space Required** (`0 GB` vs `2.0 GB` vs `4.7 GB`), **RAM Required** (`~1.2 GB` vs `4-8 GB` vs `16 GB+`), and **Direct Free Key Links** (`console.groq.com`, `aistudio.google.com`, `console.neo4j.io`).
4. **Zero-Crash Substrate Guarantee**:
   - If external databases (Neo4j AuraDB, Redis) are offline or keys are omitted, RAISE automatically reroutes to in-memory Python dictionaries and local ChromaDB dense vector search without crashing.

---

## 2. Step-by-Step MCQ Wizard Specifications

### Step 1: Device & Operating System (`PlatformStep.tsx`)
* **Question**: *"Which device and operating system are you configuring?"*
* **Auto-Detected Host Diagnostics**:
  * Real-time hardware telemetry: Active OS, Physical RAM (GB), CPU logical cores, Hardware Acceleration (`Metal / MPS / CUDA`).
* **Selectable Platform Cards**:
  1. `macOS`: Apple Silicon (M1-M4) / Intel • Native Metal acceleration
  2. `Windows`: 10 / 11 64-bit Desktop • DirectX / DirectML / CUDA
  3. `Linux`: Ubuntu, Debian, Fedora, Arch • Native CUDA / ROCm
  4. `Android APK`: Tauri 2.0 Native NDK Build • Mobile & Tablet
  5. `iOS / iPadOS`: Tauri 2.0 Swift Native Package • iPhone & iPad
* **Hardware-Aware Rust Recommendation**:
  * If Physical RAM $\le$ 8 GB: Recommends **100% Free Cloud Profile** (0 GB disk, ~1.2 GB RAM).
  * If Physical RAM $>$ 8 GB: Highlights compatibility for both instant Cloud AI and local private Ollama models.

---

### Step 2: Intelligence Engine (`EngineStep.tsx`)
* **Question**: *"How would you like AI reasoning & LLMs to run?"*
* **Option A: 100% Free Cloud AI (Recommended)**:
  * **Disk Space**: `0 GB (Zero Download)`
  * **Setup Time**: `Instant (~15 seconds)`
  * **RAM Overhead**: `~1.2 GB (Any Laptop)`
  * **Speed**: `~500 tokens/sec (Sub-second ~0.8s generation)`
  * **Primary Engines**: Groq LPU (`llama-3.3-70b-versatile`) or Google Gemini (`gemini-2.5-flash`).
  * **Free API Key Links**:
    * Groq API: [`https://console.groq.com/keys`](https://console.groq.com/keys)
    * Gemini API: [`https://aistudio.google.com/app/apikey`](https://aistudio.google.com/app/apikey)
* **Option B: Sovereign Local AI Engine (Ollama)**:
  * **Disk Space**: `2.0 GB – 4.7 GB`
  * **Setup Time**: `~2 – 5 min download`
  * **RAM Overhead**: `4 GB – 16 GB+ RAM`
  * **Privacy**: `100% Private Local (Zero data leaves device)`
  * **Model Sub-MCQ Cards**:
    * `Llama 3.2 3B`: 2.0 GB download • 4–8 GB RAM (Best for MacBook Air & lightweight laptops)
    * `Qwen 2.5 7B`: 4.7 GB download • 8–16 GB RAM (State-of-the-art precision reasoning)
    * `Llama 3.1 8B`: 4.9 GB download • 16 GB+ RAM (Broad general knowledge)
  * **Download Action**: Integrated SSE / Tauri IPC streaming progress bar showing downloaded %, speed (MB/s), and completed cache state.

---

### Step 3: Databases & Fallbacks (`DatabaseStep.tsx`)
* **Question**: *"Configure Knowledge Graph, Relational Sessions, and Cache"*
* **Section 1: Knowledge Graph (Neo4j Property Graph)**:
  * `Free Cloud Neo4j AuraDB`: 0 GB disk, 0 MB local RAM, 200k nodes free via [`https://console.neo4j.io`](https://console.neo4j.io).
  * `Local Neo4j Bolt Server`: `bolt://localhost:7687` (Docker or Neo4j Desktop).
  * `Vector Search Fallback`: ChromaDB embeddings + BM25 keyword matching (0 GB extra, built-in).
  * **Zero-Crash Notice**: Queries automatically reroute if credentials are unset.
* **Section 2: PostgreSQL (Sessions & History)**:
  * `In-Memory Shield (Recommended)`: 0 MB extra RAM, zero installation, managed in Python memory dictionaries.
  * `Cloud Neon Postgres`: Serverless PostgreSQL via `neon.tech`.
* **Section 3: Redis (Response Cache & Signals)**:
  * `In-Memory Cache (Recommended)`: 0 MB extra RAM, sub-second query repeat hash.
  * `Cloud Upstash Redis`: Serverless TLS cache via `upstash.com`.

---

### Step 4: Summary Scorecard & Launch (`LaunchStep.tsx`)
* **Scorecard**: Displays selected architecture, AI model, knowledge graph substrate, storage mode, total space, and estimated setup time.
* **Pre-Flight Diagnostic Check**: Pings ChromaDB, Neo4j, Redis, and FastAPI/Tauri gateway.
* **1-Click Launch**: Saves configuration to `.env` via `POST /api/system/config` or Tauri Rust `save_configuration`, flags `firstRunCompleted = true`, and enters the workstation.

---

## 3. Backend & Tauri Rust Integration Contract

| Endpoint / Command | Protocol | Input Payload | Output Response |
| :--- | :--- | :--- | :--- |
| `GET /api/system/hardware` or `get_system_hardware` | REST / Tauri IPC | *None* | `{"platform": "macos", "total_ram_gb": 16.0, "cpu_cores": 8, "has_metal_or_cuda": true}` |
| `POST /api/system/config` or `save_configuration` | REST / Tauri IPC | `SystemConfigPayload` (llm_backend, groq_api_key, neo4j_uri, etc.) | `{"success": true, "message": "Configuration applied"}` |
| `POST /api/system/test-connections` | REST | *None* | `{"neo4j": {"online": true}, "redis": {"online": true}}` |
| `POST /api/system/models/pull` or `pull_local_model` | SSE / Tauri IPC | `{"model_name": "llama3.2:3b"}` | Stream: `data: {"percent": 45, "status": "Downloading..."}` |
