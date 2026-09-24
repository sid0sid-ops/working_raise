# Frontend Engineering Response & Architecture Audit (`conv` branch)
=============================================================================

> **Collaborative Communication**: This document is the frontend engineering team's response to [`THOUGHTS_FOR_FRONTEND.md`](./THOUGHTS_FOR_FRONTEND.md). It outlines remediations executed against the 6 backend audit findings, introduces the **Workstation Mission Control Installer Wizard**, and proposes shared contracts for upcoming Rust/Tauri 2.0 integration.

---

## 1. Response & Remediation to Backend Audit Findings

We conducted a comprehensive audit of the frontend codebase against the backend specifications. All 6 issues highlighted in `THOUGHTS_FOR_FRONTEND.md` have been resolved on `working/frontend`:

### ✅ ISSUE 1: Hardcoded Institute Fallback (`'IIT Madras'`)
* **Remediation**: In [`src/utils/citationParser.ts`](file:///src/utils/citationParser.ts), removed all hardcoded `'IIT Madras'` defaults.
* **Updated Implementation**:
  ```typescript
  university: raw.university || raw.metadata?.university || '',
  ```
* **Impact**: Multi-institute research documents (NIPGR, BRIC, DBT, ICGEB) now display their verified institutional origins with zero bias.

---

### ✅ ISSUE 2: Compound Citation Parsing (`[1, 2, 3]`)
* **Remediation**: Upgraded `parseCitations` regex to match multi-index brackets:
  ```typescript
  const citationRegex = /\[(\d+(?:\s*,\s*\d+)*)\]/g;
  ```
* **Updated Logic**: Emits individual `CitationToken` items for each cited index. When text contains `...findings [1, 3].`, the UI renders two discrete, interactive citation badges `[1]` and `[3]` linking directly to page deep-links.

---

### ✅ ISSUE 3: Deprecated Endpoint Drift (`/api/graphrag/subgraph-query`)
* **Remediation**: Deprecated route fallbacks in `src/api/endpoints.ts` and `src/services/ChatService.ts` have been removed.
* **Production Standard**: All chat queries (both `fast` and `expert` GraphRAG modes) target `POST /api/chat` exclusively with Server-Sent Events (SSE) streaming.

---

### ✅ ISSUE 4: Deprecated Request Payload Properties
* **Remediation**: In `src/services/ChatService.ts`, purged legacy flags `parser: 'docling'` and `full_potential: boolean`.
* **Clean Production Payload**:
  ```json
  {
    "message": "What are the primary findings in the report?",
    "mode": "expert",
    "session_id": "sess-20260925-001",
    "active_docs": ["Report.pdf"],
    "hops": 3,
    "top_k": 8,
    "stream": true
  }
  ```

---

### ✅ ISSUE 5: Page Number Standardization
* **Remediation**: Standardized citation typing and extraction:
  * `primary_page`: **Integer (1-indexed)** — Used directly for PDF viewer deep-linking `#page={primary_page}`.
  * `printed_page`: **String** — Used for document header/footer page labels (e.g. `"xvii"` or `"12"`).

---

### ✅ ISSUE 6: Markdown Stream Boundary Sanitation
* **Remediation**: Protected token boundaries in `sanitizeStreamText` and KaTeX mathematical formulas with `throwOnError: false` to ensure partial equation blocks during streaming never cause layout shifts.

---

## 2. Introducing the Workstation Mission Control Installer Wizard 🚀

To make RAISE immediately accessible to non-technical users and cross-platform researchers on any operating system, we created the **Mission Control Setup Wizard** (`src/features/control-center/`).

### Key Design Pillars:
1. **Classic Installer Wizard Semantics**:
   * Uses clear `← Previous` and `Next →` navigation buttons.
   * Completely avoids confusing filler words, nested tabs, or ambiguous terminology.
2. **Fixed Rigid Dimensions (Zero Bouncing)**:
   * Centered `860px × 680px` uniform dialog box (`max-h-[90vh]`).
   * The window frame remains strictly fixed across all steps so there is zero jitter, resizing, or jumping between screens.
3. **Transparent Download Sizes on Every Card**:
   * **100% Free Cloud Profile**: Displays `0 GB (Zero Download)` and `~1.2 GB RAM`.
   * **Local Ollama Models**: Displays `2.0 GB Download` (Llama 3.2 3B) or `4.7 GB Download` (Qwen 2.5 7B).
   * **Neo4j Storage Options**: Displays `0 GB` (Cloud AuraDB) vs `1.5 GB` (Local Bolt Server) vs `0 GB Extra` (ChromaDB Fallback).
4. **Dynamic Footprint Calculator (`resourceCalculator.ts`)**:
   * Dynamically sums total disk space and memory footprint in real time based on active user selections—zero hardcoding.
5. **Zero-Crash Fallback Matrix**:
   * If Neo4j credentials are empty or local server is unreachable, the system automatically falls back to ChromaDB Dense Vector Search + BM25 keyword matching.
   * PostgreSQL and Redis include in-memory session protection.

---

## 3. Recommended Backend Endpoints for Mission Control

To transition the setup wizard from mock/local fallback to live FastAPI integration, we propose the following 3 lightweight endpoints on the FastAPI gateway:

### 1. Host Hardware Diagnostics
* **Endpoint**: `GET /api/system/hardware`
* **Response**:
  ```json
  {
    "platform": "macos",
    "os_name": "macOS 15.1 Darwin",
    "total_ram_gb": 16.0,
    "cpu_cores": 8,
    "has_metal_or_cuda": true
  }
  ```

### 2. Substrate Configuration & Secret Locker
* **Endpoint**: `POST /api/system/config`
* **Request**:
  ```json
  {
    "llm_backend": "groq",
    "groq_api_key": "gsk_...",
    "gemini_api_key": "",
    "ollama_model": "llama3.2:3b",
    "neo4j_mode": "cloud",
    "neo4j_uri": "neo4j+s://...",
    "neo4j_password": "...",
    "postgres_mode": "in_memory_fallback",
    "redis_mode": "in_memory_fallback"
  }
  ```
* **Behavior**: Atomically updates `.env` and reloads connection pools without dropping client connections.

### 3. Ollama Model Pull with SSE Progress
* **Endpoint**: `POST /api/system/pull-model`
* **Request**: `{"model": "llama3.2:3b"}`
* **SSE Stream**:
  ```text
  data: {"status": "downloading", "percent": 45, "speed": "12.4 MB/s"}
  data: {"status": "completed", "percent": 100}
  ```

---

## 4. Verification & Quality Gates

* **TypeScript Compilation**: `npm run typecheck` passed (0 errors).
* **Test Suite**: **29/29 Vitest test suites passing (251/251 tests passing)**.
* **Production Build**: `vite build` completed in **874ms**.

---

## 5. Shared Folder Structure on `conv` Branch

```
conv/
├── README.md                                             # Collaboration protocol and overview
├── THOUGHTS_FOR_FRONTEND.md                              # Backend team audit & contract requirements
├── THOUGHTS_FROM_FRONTEND.md                             # Frontend team remediations & installer specs
└── sugestions by frontend/
    ├── 17_FRONTEND_MODEL_MANAGER_AND_RUST_BACKEND_SPEC.md # React 19 + Rust IPC specification
    ├── 18_TAURI_RUST_CONTROL_CENTER_ARCHITECTURE_SPEC.md  # Tauri 2.0 desktop & mobile setup
    ├── 19_CONTROL_CENTER_MCQ_WIZARD_AND_BACKEND_ALIGNMENT.md # Substrate alignment matrix
    └── 20_INSTALLER_WIZARD_AND_DYNAMIC_FOOTPRINT_SPEC.md # Installer UI dimensions & calculator
```

*We invite the backend engineering team to review these updates and test the new Mission Control wizard on `working/frontend`!*
