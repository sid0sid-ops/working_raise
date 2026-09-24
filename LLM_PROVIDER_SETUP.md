# RAISE Multi-Backend AI Inference & Cloud LLM Setup Guide
=============================================================================

> **Architecture Overview**: RAISE supports both high-throughput local GPU inference via **vLLM** (defaulting to 16GB–24GB VRAM hardware) and **zero-GPU Cloud LLM APIs** (Groq, Google Gemini, DeepSeek, etc.). Anyone who clones this repository can run the entire pipeline seamlessly without needing an expensive dedicated GPU.

---

## 1. Quick Start: Choosing Your Inference Engine

When starting RAISE (`python dev_main.py` or `python main.py`), you can select your inference engine interactively or via CLI flags.

### Interactive CLI Menu
When launched in an interactive terminal, RAISE displays:
```text
╔══════════════════════════════════════════════════════════════════════════╗
║ 🤖  RAISE MULTI-BACKEND AI INFERENCE SELECTOR                            ║
║ Select your LLM engine. Works offline on GPU or via free Cloud APIs.     ║
╠══════════════════════════════════════════════════════════════════════════╣
║  1. Local vLLM Engine (Qwen 2.5 14B) — [OFFLINE / GPU REQUIRED]          ║
║  2. Groq Cloud API    (Ultra-fast LPU) — [READY - RECOMMENDED]           ║
║  3. Google Gemini API (Gemini 3.6 Flash) — [READY]                       ║
║  4. DeepSeek API      (Cloud / User Account)                             ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Command-Line Execution
Run headlessly with your chosen provider directly:
```powershell
# Run with Groq Cloud API (fastest, free tier available)
python main.py --llm groq -q "What is the mission of IIT Madras Research Park?"

# Run with Google Gemini API
python main.py --llm gemini -q "What is the mission of IIT Madras Research Park?"

# Run with Local vLLM Engine (Requires GPU with >= 16GB VRAM)
python main.py --llm vllm

# Run with graphical popup dialog
python main.py --gui
```

---

## 2. Supported Providers & Diagnostic Status

| Provider | Supported Models | Latency | Hardware Required | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **Groq Cloud** | `qwen/qwen3.8-27b`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b` | **< 1.0s** | None (CPU / Cloud) | ✅ **ACTIVE & VERIFIED** |
| **Google Gemini** | `gemini-3.6-flash`, `gemini-2.5-pro` | **~1.5s** | None (CPU / Cloud) | ✅ **ACTIVE & VERIFIED** |
| **Local vLLM** | `Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4` | **~1.2s** | RTX 3090 / 4090 (24GB) | ⚠️ Standby (Container requires restart/memory tuning) |
| **DeepSeek** | `deepseek-chat`, `deepseek-reasoner` | **~2.5s** | None (CPU / Cloud) | 💳 Requires Top-up Balance (HTTP 402) |
| **Cohere** | `command-r-plus`, `command-r` | **~1.8s** | None (CPU / Cloud) | 🔑 Requires Valid Key |

---

## 3. Environment Configuration (`.env`)

To configure your cloud API keys, copy `.env.example` to `.env` (or edit existing `.env`). **Never commit `.env` to Git.**

```ini
# Active Inference Provider: 'groq', 'gemini', 'deepseek', or 'vllm'
LLM_BACKEND=groq
EXECUTION_MODE=CLOUD

# Groq Cloud API (Free high-speed LPU)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL_NAME=qwen/qwen3.8-27b

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_NAME=gemini-3.6-flash

# DeepSeek Cloud API
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Local vLLM Engine (When running offline with GPU)
VLLM_BASE_URL=http://localhost:8002/v1
VLLM_MODEL_NAME=Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4
```

---

## 4. Automated Zero-Crash Failover Architecture

If a user selects `vllm` (or runs on a new clone without a GPU), RAISE's `ProviderRouter` automatically probes connection health:
1. If the local vLLM port is unresponsive or unreachable, RAISE **does not crash**.
2. It automatically logs a non-secret fallback event:
   ```text
   Primary provider 'vllm' failed for RAG_GENERATION: Connection refused -> Switched to 'groq'
   ```
3. It seamlessly routes the synthesis request through the next available healthy cloud provider in the fallback chain:
   $$\text{vLLM} \longrightarrow \text{Groq} \longrightarrow \text{Gemini} \longrightarrow \text{DeepSeek}$$
4. The synthesized answer undergoes the exact same mathematical auditing, citation deep-linking, and NLI quality gating as the local engine.

---

## 5. Security & Masking Guarantee

- **Zero Plaintext Secret Exposure**: API keys are loaded via layered precedence:
  1. Process Environment Variables
  2. Windows Credential Locker (DPAPI via `keyring`)
  3. Untracked `.env` file
- **Strict Masking**: Diagnostic health tables, terminal logs, and trace exports mask all tokens:
  ```text
  Key: gsk_ULNY... (Configured: YES, Auth: VALID)
  ```
- **Git Exclusions**: `.env` and `.env.*` are strictly excluded in `.gitignore` and protected against repository commits.
