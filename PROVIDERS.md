# Multi-Backend AI Inference & Provider Architecture

RAISE features a modular, enterprise-grade multi-provider inference runtime designed for low-latency local execution, resilient cloud bursting, and zero credential leakage.

---

## 1. Supported Providers & Cost Models

| Provider | Type | Default Endpoint | Cost Model | Recommended Tasks |
| :--- | :--- | :--- | :--- | :--- |
| **Local vLLM** | Local GPU | `http://localhost:8002/v1` | **LOCAL / NO EXTERNAL API BILLING** | `RAG_GENERATION`, Default Local Inference |
| **Google Gemini** | Cloud API | `https://generativelanguage.googleapis.com/v1beta/openai` | **CLOUD / USER ACCOUNT** | `DOCUMENT_EXTRACTION`, Large-Context RAG |
| **Groq** | Cloud API | `https://api.groq.com/openai/v1` | **CLOUD / USER ACCOUNT** | `CHAT`, `QUERY_REWRITE`, Ultra-low latency |
| **DeepSeek** | Cloud API | `https://api.deepseek.com` | **CLOUD / USER ACCOUNT** | `REASONING`, `CODE`, `STRUCTURED_EXTRACTION` |
| **NVIDIA NIM** | Cloud API | `https://integrate.api.nvidia.com/v1` | **CLOUD / USER ACCOUNT** | High-throughput enterprise models |
| **Cohere** | Cloud API | `https://api.cohere.com` | **CLOUD / USER ACCOUNT** | `RERANKING`, `EMBEDDING`, Multi-modal Chat |
| **OpenRouter** | Cloud API | `https://openrouter.ai/api/v1` | **CLOUD / USER ACCOUNT** | `CHAT`, `RAG_GENERATION`, Multi-model Hub |

> [!NOTE]
> All cloud providers are explicitly categorized under **CLOUD / USER ACCOUNT**. No cloud service is labeled as "free" or "zero-cost".

---

## 2. Secure Credential Architecture

Credentials are never stored in plaintext within source code, git history, or application logs. Resolution follows a strict three-tier precedence hierarchy:

```text
 1. Process OS Environment Variables (e.g., GROQ_API_KEY, GEMINI_API_KEY)
                   │  (Overrides everything for CI/automation)
                   ▼
 2. Local Secure OS Store (Windows Credential Locker via DPAPI / WinVaultKeyring)
                   │  (Persisted securely per-user on Windows)
                   ▼
 3. Untracked Local .env File Fallback
```

### Managing Credentials via CLI

```powershell
# View masked credential status (zero secrets exposed)
python -m src.cli runtime credentials list

# Safely store an API key in the Windows Credential Locker (masked prompt)
python -m src.cli runtime credentials set groq

# Remove a stored credential from the Windows Credential Locker
python -m src.cli runtime credentials delete groq
```

---

## 3. Task-Based Routing Engine

The `ProviderRouter` (`src/infrastructure/providers/router.py`) dynamically maps query intents to the optimal inference engine:

```python
from src.infrastructure.providers.router import get_provider_router, InferenceTask

router = get_provider_router()

# Execute task-routed completion
answer = router.complete(
    prompt="Explain quantum entanglement",
    task=InferenceTask.CHAT, # Dispatches to Groq LPU (or local vLLM fallback)
    temperature=0.3
)
```

### Supported Tasks:
* `CHAT`: Fast interactive conversational responses.
* `RAG_GENERATION`: Grounded document synthesis with citation constraints.
* `REASONING`: Multi-step formal logic and mathematical deduction (DeepSeek Reasoner).
* `DOCUMENT_EXTRACTION`: Vision and document structured table extraction.
* `SUMMARIZATION`: Fast executive summary generation.
* `QUERY_REWRITE`: Intent normalization and query expansion.
* `EMBEDDING`: Vector representations (Local BGE-Large or Cohere).
* `RERANKING`: Neural passage scoring (Cohere Rerank v3 or local cross-encoders).

---

## 4. Resilient Fallback & Bounded Retries

To prevent infinite loops and rate-limit storms:
* **HTTP 429 (Rate Limit)** and **HTTP 503**: Bounded to a single exponential backoff retry (max 3 seconds).
* **Automatic Failover**: If a cloud provider is unavailable, the router automatically fails over to the local vLLM instance.
* **Audit Logging**: Every fallback event is recorded non-secretly:
  ```text
  Provider groq unavailable -> switched to vllm for CHAT. Reason: HTTP 429 (RATE_LIMITED)
  ```

---

## 5. Exhaustive Provider Diagnostics

Run safe, micro-token diagnostics across all registered providers:

```powershell
python -m src.cli runtime diagnostics
```

Example output:
```text
----------------------------------------------------------------------------------------------------------------------
Provider         Config   Auth     Model    Test     Latency    Cost Mode                    Status            
----------------------------------------------------------------------------------------------------------------------
Local vLLM       YES      YES      YES      PASS     110.0 ms   LOCAL / NO EXTERNAL BILLING  READY             
Google Gemini    YES      YES      YES      PASS     420.0 ms   CLOUD / USER ACCOUNT         READY             
Groq             YES      YES      YES      PASS     180.0 ms   CLOUD / USER ACCOUNT         READY             
DeepSeek         NO       --       --       --       --         CLOUD / USER ACCOUNT         NOT_CONFIGURED    
NVIDIA NIM       NO       --       --       --       --         CLOUD / USER ACCOUNT         NOT_CONFIGURED    
Cohere           NO       --       --       --       --         CLOUD / USER ACCOUNT         NOT_CONFIGURED    
----------------------------------------------------------------------------------------------------------------------
```

---

## 6. Lightweight Operator Desktop GUI

Launch the native operator control panel:

```powershell
python -m src.cli runtime gui
```

Features:
* Sub-second startup via native Python Tkinter / ttk (zero Electron overhead).
* Substrate status monitoring (PostgreSQL, Redis, Neo4j, ChromaDB, vLLM).
* Graphical task policy routing configuration.
* Secure Windows DPAPI Credential Manager with password-masked input fields.
* Interactive provider diagnostics runner with modal output.

---

## 7. Isolated Testing & Regression Suite

* **Offline Test Suite**: `pytest` executes 100% offline using deterministic provider mocks.
* **Live Cloud Tests**: Strictly isolated behind `RUN_LIVE_PROVIDER_TESTS=1`.

```powershell
# Run offline unit tests
pytest tests/test_credentials.py tests/test_providers.py -v

# Run optional live cloud provider diagnostics (requires valid keys)
$env:RUN_LIVE_PROVIDER_TESTS="1"; pytest tests/test_providers_live.py -v
```
