# RAISE Backend: Developer Action Plan & Implementation Checklist

**Audience**: Backend Development Team  
**Objective**: Hardening, Bug Resolution, MacBook Air / Zero-GPU Portability & Frontend Feature Parity  
**Date**: September 2026  

---

## 🎯 Priority 1: Critical Security Vulnerabilities (Immediate Action)

- [ ] **SEC-01: Remove or Restrict `/api/neo4j/query`**
  - **File**: `src/api/routers/graph.py`
  - **Action**: Delete the unauthenticated arbitrary Cypher execution route, or protect it with `X-Admin-Key` header and strictly enforce a read-only keyword check (ban `DELETE`, `DETACH`, `CREATE`, `SET`, `DROP`, `CALL`).
- [ ] **SEC-02: Protect Document Deletion Routes**
  - **File**: `src/api/routers/documents.py`
  - **Action**: Add session or user token verification to `DELETE /api/documents/{id}` and `POST /api/documents/delete`.
- [ ] **SEC-03: Restrict Developer Audit Endpoints**
  - **File**: `src/api/routers/developer.py`
  - **Action**: Secure `/api/dev/recent-chats` and `/api/dev/clean-cache` with admin authentication.
- [ ] **SEC-04: Fix IP Header Spoofing in `ip_resolver.py`**
  - **File**: `src/security/ip_resolver.py`
  - **Action**: Do not blindly trust `cf-connecting-ip` or `x-forwarded-for` unless the direct socket connection originates from a trusted reverse proxy or Cloudflare CIDR range.
- [ ] **SEC-05: Prevent Path Traversal in `/api/pdf/{filename}`**
  - **File**: `src/api/routers/documents.py`
  - **Action**: Remove the `~/Downloads/` fallback search. Sanitize filenames using `Path(filename).name` and verify that the target path `is_relative_to(DOCUMENTS_DIR)`.
- [ ] **SEC-06: Remove `httpx2` Dependency**
  - **File**: `requirements.txt`
  - **Action**: Delete line 44 (`httpx2>=2.12.0`).

---

## 🛠️ Priority 2: Fix Bugs in `main.py` and Rust Build

- [ ] **BUG-01: Fix Docker Auto-Starter Process Freeze**
  - **File**: `main.py`
  - **Action**: Disable `subprocess.run(["docker", "start", ...])` by default. Only run it if an environment flag `AUTO_START_CONTAINERS=true` is set.
- [ ] **BUG-02: Fix Conversational Intent Classification False-Positives**
  - **File**: `main.py`
  - **Action**: Replace loose substring search (`"what are you"` in `t_lower`) with anchored regular expressions so research questions (e.g. *"What are you observing in Table 2?"*) are not hijacked as bot identity queries.
- [ ] **BUG-03: Replace Manual `sys.argv` with `argparse`**
  - **File**: `main.py`
  - **Action**: Use standard `argparse.ArgumentParser` to parse flags (`--query`, `-q`, `--llm`, `--status`, `--clear-cache`, `--gui`) cleanly without false-triggering PDF file ingestion.
- [ ] **BUG-04: Support Non-Interactive Headless Mode in `main.py`**
  - **File**: `main.py`
  - **Action**: Wrap `prompt_llm_backend()` with `if not cli_query and sys.stdin.isatty():` so headless test scripts and automated benchmarks run without blocking for user keyboard input.
- [ ] **BUG-05: Correct Page Range Parsing in PDF Ingestion**
  - **File**: `main.py`
  - **Action**: Parse start and end page numbers from ranges (e.g. `"15-30"` $\rightarrow$ `start=15, end=30`) instead of always starting from page 1.
- [ ] **BUG-06: Atomic Write for `ingested_manifest.json`**
  - **File**: `main.py` and `src/api/context.py`
  - **Action**: Write to a temporary file (`manifest.json.tmp`) and atomically rename it (`os.replace`) to prevent file corruption during concurrent operations.
- [ ] **BUG-07: Fix Rust `Cargo.toml` Missing Binary Path**
  - **File**: `rust/raise_engine/Cargo.toml`
  - **Action**: Remove `[[bin]] name = "raise-cli" path = "src/bin/main.rs"` or create `rust/raise_engine/src/bin/main.rs`.

---

## 💻 Priority 3: MacBook Air & Zero-GPU Portability

- [ ] **MAC-01: Update `docker-compose.yml` with Profiles**
  - **File**: `docker-compose.yml`
  - **Action**: Add `profiles: ["local-gpu"]` to the `vllm` service. Remove `vllm` from the mandatory `depends_on` list of `backend`. Allow `docker compose --profile cloud up -d` to run on any MacBook Air.
- [ ] **MAC-02: Reduce Default Neo4j Memory in `docker-compose.yml`**
  - **File**: `docker-compose.yml`
  - **Action**: Change default heap and pagecache from 28 GB to 1 GB each:
    ```yaml
    NEO4J_server_memory_heap_initial__size: ${NEO4J_HEAP_INITIAL_SIZE:-512m}
    NEO4J_server_memory_heap_max__size: ${NEO4J_HEAP_MAX_SIZE:-1G}
    NEO4J_server_memory_pagecache_size: ${NEO4J_PAGECACHE_SIZE:-1G}
    ```
- [ ] **MAC-03: Dynamic Hardware Acceleration for Embeddings**
  - **File**: `src/core/config.py` and `src/infrastructure/vector/chroma.py`
  - **Action**: Detect hardware dynamically:
    ```python
    import torch
    if torch.cuda.is_available():
        default_device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        default_device = "mps"  # Apple Silicon Metal
    else:
        default_device = "cpu"
    ```
- [ ] **MAC-04: Single-Command Quickstart Script (`run.sh`)**
  - **Action**: Provide a root shell script `run.sh` that checks OS, verifies `.env`, activates virtualenv, and starts `server.py`.

---

## 🌐 Priority 4: Free Cloud Services Integration

- [ ] **CLOUD-01: Verified Groq and Gemini Cloud Defaults**
  - Ensure `.env.example` documents free API setup with Groq (`qwen/qwen3.8-27b`) and Google Gemini (`gemini-2.0-flash`).
- [ ] **CLOUD-02: Neo4j AuraDB Free Connection Support**
  - Ensure the Neo4j driver handles `neo4j+s://` protocol and certificate verification cleanly for cloud databases.
- [ ] **CLOUD-03: Supabase & Upstash Serverless Support**
  - Verify that Postgres connection pooling (`sslmode=require`) works seamlessly with managed cloud databases.

---

## 🧹 Priority 5: Codebase Cleanup & Redundancy Removal

- [ ] **CLEAN-01: Remove Dead `from RAG...` Imports**
  - Search and replace all fallback imports referencing `RAG.` in:
    - `src/features/agent/workflow.py`
    - `src/features/agent/router.py`
    - `src/features/query/service.py`
    - `src/api/routers/chat.py`
- [ ] **CLEAN-02: Consolidate Duplicate Folders**
  - Deprecate `src/services/` (redirect calls to `src/features/*`).
  - Merge `src/features/chunking/` into `src/chunking/`.
  - Merge `src/features/retrieval/` into `src/retrieval/`.

---

## 🚀 Priority 6: Frontend Feature Parity (From `backend_improvement.md`)

- [ ] **FE-01: Document-Scoped Dynamic Suggestions (`GET /api/suggestions`)**
  - Ensure suggestions strictly honor `?active_docs=...` and return `[]` when no documents are attached (prevent cross-document citation bleed).
- [ ] **FE-02: Follow-Up Inquiries in Chat SSE Payload**
  - In terminal SSE event `data: {"status": "completed", ...}`, include a `follow_up_inquiries: ["...", "..."]` array synthesized during the final reasoning step.
- [ ] **FE-03: 1-Indexed Physical Page Citations**
  - Ensure all citations emit `primary_page` matching physical PDF page numbers for exact `#page=N` browser deep-linking.
- [ ] **FE-04: Strict HTTP 206 Byte-Range PDF Streaming**
  - Ensure `GET /api/pdf/{filename}` properly handles `Range: bytes=...` headers for smooth loading of 25MB+ institutional PDFs.
