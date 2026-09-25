# RAISE Network Security, Gateway Observability & Privacy Audit

**Document Version**: 1.0.0  
**Status**: Production Security Reference  
**Scope**: Cloudflare Gateway, Cloudflare AI Gateway, Zero Trust / WARP Inspection, Reverse Proxies, and Model Privacy  

---

## 1. Executive Summary & The Core Question

> **Question**: *"If someone is connected through Cloudflare Gateway, will they be able to see which LLM we are using and other metadata?"*

### The Direct Answer:
Whether an observer can see which LLM you are using depends entirely on **which type of Cloudflare connection** is in place:

1. **If a user visits your app through Cloudflare CDN / Tunnel (Reverse Proxy)**:  
   - In standard chat interactions (`POST /api/chat`, `POST /api/chat/rag`), **NO**, they cannot see which LLM was used. The API returns only the verified text answer, sources, citations, and execution latency.  
   - **However**, if they open their browser console and inspect `GET /api/system/config` or `GET /api/system/dynamic-llms`, these administrative endpoints currently surface the provider name and model catalog.
2. **If your backend routes LLM requests through Cloudflare AI Gateway**:  
   - **YES**. Any administrator with access to the Cloudflare AI Gateway dashboard will see the exact model name (e.g. `llama-3.3-70b-versatile`, `open-mistral-nemo`), token usage, latency, and costs. If request logging is enabled, they can also read full prompts and completions.
3. **If the user or server is on a corporate network with Cloudflare Zero Trust (Forward Proxy / WARP)**:  
   - **Without TLS Inspection (Default)**: They can only see the domain name (e.g. `api.groq.com`, `api.mistral.ai`), but **CANNOT** see the model name, prompt, or response.  
   - **With TLS Inspection Enabled (Root CA installed)**: The network administrator **CAN** decrypt the HTTPS traffic and see the exact model name, prompts, and headers.

---

## 2. In-Depth Multi-Layer Visibility Matrix

The table below breaks down exactly what is visible across every connection archetype:

| Observability Layer | What the Observer Sees | Can They See the LLM Model Name? | Can They See the Prompts / Answers? | Can They See API Keys? |
| :--- | :--- | :--- | :--- | :--- |
| **Layer 1: End-User via Cloudflare Proxy / Tunnel** (`browser -> Cloudflare -> RAISE`) | HTTP status, SSE tokens, parsed answer, page citations, execution latency | **NO** in `/api/chat`; **YES** if they call `/api/system/config` | Only the final synthesized answer (never the raw LLM prompt) | **NO** (Strictly masked on backend) |
| **Layer 2: Cloudflare AI Gateway** (`RAISE -> CF Gateway -> Cloud LLM`) | Full request logs, token count, upstream provider, model parameter, latency | **YES** (Explicitly tracked in CF Dashboard) | **YES** (If "Log Request & Response Bodies" is ON); **NO** (If toggled OFF) | **NO** (Stored encrypted or bypassed) |
| **Layer 3: Corporate Cloudflare Zero Trust / WARP (No TLS Decryption)** | DNS queries, SNI Hostnames (`api.groq.com`, `databases.neo4j.io`) | **NO** (Encrypted in TLS 1.3 tunnel) | **NO** (Encrypted in TLS 1.3 tunnel) | **NO** (Encrypted in TLS 1.3 tunnel) |
| **Layer 4: Corporate Cloudflare Zero Trust / WARP (TLS Decryption Active)** | Full HTTP request/response payloads decrypted at the corporate firewall | **YES** (Visible in raw JSON payload) | **YES** (Full prompt & response visible) | **YES** in `Authorization: Bearer` (unless DLP rule redacts it) |

---

## 3. Deep Architectural Breakdown by Scenario

### Scenario A: Public Web User / Client Connecting via Cloudflare Tunnel or Reverse Proxy

When a user interacts with the RAISE Web UI hosted behind Cloudflare (`https://raise.yourdomain.com`):

```
[User Browser]
      │
      ▼ (HTTPS)
[Cloudflare Edge / Tunnel]
      │
      ▼ (Encrypted Tunnel)
[FastAPI Backend :8000]
      │
      ├─► POST /api/chat ──────────► Returns { "reply", "sources", "citations" } (MODEL HIDDEN)
      └─► GET /api/system/config ──► Returns { "last_used_model", "available_providers" } (MODEL VISIBLE)
```

1. **Standard Chat Endpoints (`/api/chat`, `/api/chat/stream`, `/api/chat/rag`)**:
   - The response payload contains:
     ```json
     {
       "reply": "According to the financial schedule, total revenue was...",
       "grounded_answer": "...",
       "sources": [...],
       "citations": ["[1]"],
       "verified_claims": [...],
       "subgraph": {...},
       "quality_gate_decision": "accept",
       "execution_time": 1.42,
       "mode_used": "hybrid"
     }
     ```
   - **Notice**: Neither `"provider"` nor `"model"` is included in the chat response. An ordinary user inspecting the Network tab in Chrome DevTools during chat **cannot determine which LLM generated the text**.

2. **System Control Endpoints (`/api/system/config`, `/api/system/dynamic-llms`)**:
   - These administrative endpoints return:
     ```json
     {
       "llm_model_name": "llama-3.3-70b-versatile",
       "last_used_provider": "groq",
       "last_used_model": "llama-3.3-70b-versatile",
       "available_providers": ["groq", "mistral", "nvidia", "cohere", "gemini"]
     }
     ```
   - If an inquisitive user inspects API calls or manually curls `/api/system/config`, they will see the active provider and model.
   - **Recommended Action**: Enable production admin mode or privacy masking to suppress model names from public API responses.

---

### Scenario B: Routing Outbound Backend Requests Through Cloudflare AI Gateway

If the RAISE backend routes inference through **Cloudflare AI Gateway** using `UniversalCloudProvider`:

```
[RAISE Backend] 
      │
      ▼ (HTTPS)
[Cloudflare AI Gateway: gateway.ai.cloudflare.com/v1/{account_id}/{gateway_slug}/...]
      │
      ▼
[Upstream Provider: Groq / Mistral / OpenAI / Anthropic]
```

1. **What Cloudflare AI Gateway Records**:
   - **Model Identifier**: Cloudflare AI Gateway parses the JSON body `"model": "..."` to index and group usage statistics. The dashboard explicitly graphs: *"Queries by Model: llama-3.3-70b-versatile vs open-mistral-nemo"*.
   - **Upstream Endpoint**: The destination provider (e.g. Groq, Mistral, OpenAI) is visible.
   - **Token Consumption**: Input tokens, output tokens, and cache hits.
   - **Cost Estimation**: Calculated automatically based on the model ID.
2. **Payload Visibility (Prompts & Answers)**:
   - Cloudflare AI Gateway provides a setting: **"Log Request and Response Bodies"**.
   - **If Enabled**: Any team member with Cloudflare dashboard access can click on any request in the log stream and read the exact user question, the retrieved context passages, and the generated response.
   - **If Disabled**: Cloudflare stores only the quantitative metrics (token counts, duration, status code, model name), but drops the text payload.

---

### Scenario C: Client or Server on a Cloudflare Zero Trust Enterprise Network

When an end-user or the server hosting RAISE connects through an enterprise network monitored by **Cloudflare Gateway / WARP**:

```
[Host Machine]
      │
      ▼ (WARP Client)
[Cloudflare Secure Web Gateway (SWG)]
      │
      ├─► Case 1: TLS Decryption Disabled ──► Sees destination IP & SNI domain ONLY
      └─► Case 2: TLS Decryption Enabled  ──► Intercepts & decrypts full HTTPS payload
```

1. **Case 1: Standard Mode (No HTTPS Inspection / Decryption)**:
   - Connections to `https://api.groq.com/openai/v1/chat/completions` or `https://api.mistral.ai/v1/chat/completions` establish an end-to-end TLS 1.3 tunnel between the RAISE backend and the provider.
   - Cloudflare Gateway inspects only the unencrypted TLS handshake (SNI: Server Name Indication).
   - **What the Admin Sees in Gateway Logs**:
     - *Client IP `192.168.1.50` connected to `api.groq.com:443` (Allowed by Policy: AI Services).*
   - **What is Completely Hidden**:
     - The URL path (`/openai/v1/chat/completions`).
     - The request body (`"model": "llama-3.3-70b-versatile"`).
     - The prompt and question text.
     - The API key in the `Authorization` header.

2. **Case 2: Enterprise Deep Packet Inspection (HTTPS Decryption Enabled)**:
   - If the machine has an enterprise **Cloudflare Root Certificate** installed in the OS trust store, Cloudflare performs a man-in-the-middle TLS interception:
     `Host Machine <--- [CF Local TLS] ---> Cloudflare Gateway <--- [CF Upstream TLS] ---> Upstream Provider`
   - In this enterprise mode, Cloudflare Gateway decrypts every packet.
   - **What the Admin Sees**:
     - The full HTTP request headers and payload.
     - The exact model name (`model: "llama-3.3-70b-versatile"`).
     - The user's query and the RAG document chunks in the prompt.
     - The `Authorization: Bearer <API_KEY>` header (unless masked by Cloudflare Data Loss Prevention rules).

---

## 4. Hardening & Privacy Configuration Guide

To ensure zero-leakage and protect against model fingerprinting, implement the following security configurations:

### 1. Restrict `/api/system/config` in Production
Set an environment variable or toggle in `backend/.env`:
```bash
# Enable production mode to mask internal provider and model names
PUBLIC_TELEMETRY_ENABLED=false
```
When `PUBLIC_TELEMETRY_ENABLED=false`, the backend masks model names to generic labels (e.g. `"RAISE Enterprise Intelligence Engine"`, `"Neural Reasoning Pipeline"`) in public GET responses.

### 2. Configure Cloudflare AI Gateway for Zero-Payload Logging
If you choose to use Cloudflare AI Gateway for high-speed edge caching and analytics:
1. Navigate to **Cloudflare Dashboard > AI > AI Gateway > [Your Gateway] > Settings**.
2. Set **"Log Request and Response Bodies"** to **Disabled (OFF)**.
3. Set **"Cache TTL"** to your desired window (e.g. 1 hour).
4. This ensures that Cloudflare logs only numeric tokens and performance latencies, while zero proprietary text or document chunks are stored on Cloudflare servers.

### 3. Corporate Zero Trust Pinning (Bypassing TLS Decryption)
If running RAISE on a machine managed by corporate Cloudflare WARP:
- In the Cloudflare Zero Trust Dashboard, navigate to **Gateway > HTTP Policies**.
- Add a bypass rule:
  - **Selector**: `Domain` in `{api.groq.com, api.mistral.ai, integrate.api.nvidia.com, api.cohere.com, *.databases.neo4j.io}`
  - **Action**: `Do Not Decrypt` (Bypass Inspection).
- This prevents corporate firewalls from decrypting and logging prompt payloads or API keys.

---

## 5. Summary Checklist

| Security Objective | Current RAISE Status | Verification Command |
| :--- | :--- | :--- |
| **Model hidden from `/api/chat` responses** | **PROTECTED** (Model parameter omitted) | Inspect `POST /api/chat` response JSON |
| **Model hidden from `/api/system/config`** | **EXPOSED** for admin dashboard | Inspect `GET /api/system/config` |
| **Encrypted Transit to Cloud Providers** | **PROTECTED** (TLS 1.3 enforced) | Inspect `safe_http_request` HTTPS calls |
| **Zero Prompt Leakage to Reverse Proxy** | **PROTECTED** (Zero reverse-logging) | Cloudflare Tunnel proxying `/api` |
| **AuraDB Cloud Database Isolation** | **PROTECTED** (Encrypted Bolt port 7687) | `neo4j+s://` TLS handshake |
