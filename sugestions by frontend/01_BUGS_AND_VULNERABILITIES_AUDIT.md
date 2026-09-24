# RAISE Backend: Security Vulnerabilities & Code Bug Audit

**Audited Repository**: `https://github.com/sid0sid-ops/working_raise.git` (Branch: `backend`)  
**Auditor**: Senior Security & Systems Architect  
**Date**: September 2026  

---

## 1. Executive Security & Vulnerability Summary

The RAISE backend contains impressive academic retrieval mechanisms (hybrid graph traversal, BM25, and semantic reranking). However, our forensic audit identified **4 Critical/High Security Vulnerabilities** and **8 Architectural Bugs** that must be resolved before deploying or sharing the backend publicly.

| ID | Category | Severity | File Location | Summary |
| :--- | :--- | :--- | :--- | :--- |
| **VULN-01** | Remote DB Execution | 🚨 **CRITICAL** | `src/api/routers/graph.py:132` | Unauthenticated raw Cypher query execution endpoint |
| **VULN-02** | Access Control | 🚨 **HIGH** | `src/api/routers/documents.py:348` | Unauthenticated document purge & deletion endpoints |
| **VULN-03** | Information Disclosure | ⚠️ **HIGH** | `src/api/routers/developer.py:42` | Unauthenticated access to full conversation history & audit logs |
| **VULN-04** | Security Bypass | ⚠️ **HIGH** | `src/security/ip_resolver.py:24` | IP header spoofing bypasses Redis blacklisting |
| **VULN-05** | Path Traversal / LFI | ⚠️ **HIGH** | `src/api/routers/documents.py:263` | PDF streaming endpoint exposes server's `~/Downloads` |
| **VULN-06** | Supply Chain Risk | 🟡 **MEDIUM** | `requirements.txt:44` | Non-standard package `httpx2>=2.12.0` declared |
| **BUG-01** | Process Lock / Freeze | 🚨 **HIGH** | `main.py:92-150` | Hardcoded Docker container start freezes on Mac/non-NVIDIA |
| **BUG-02** | Classification Bug | 🚨 **HIGH** | `main.py:334-398` | Research questions falsely classified as bot identity questions |
| **BUG-03** | CLI Crash | 🟡 **MEDIUM** | `main.py:695-716` | Brittle `sys.argv` parsing conflicts with CLI flags |
| **BUG-04** | Headless Automation | 🟡 **MEDIUM** | `main.py:640-648` | Interactive LLM prompt blocks automated scripts & CI |
| **BUG-05** | Ingestion Error | 🟡 **MEDIUM** | `main.py:477-486` | Page range parsing always starts from page 1 |
| **BUG-06** | Data Loss / Race | 🟡 **MEDIUM** | `main.py:505-544` | Manifest write without file locking |
| **BUG-07** | Build Failure | 🟡 **MEDIUM** | `rust/raise_engine/Cargo.toml:13` | Missing `src/bin/main.rs` breaks `cargo build` |
| **BUG-08** | Import Regression | 🟡 **LOW** | Multiple files (`src/features/...`) | Broken legacy `from RAG.prompts...` imports |

---

## 2. In-Depth Vulnerability Analysis & Defensive Remediations

### VULN-01: Unauthenticated Raw Cypher Query Execution
* **Location**: [`src/api/routers/graph.py`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/src/api/routers/graph.py#L132-L143)
* **Vulnerable Code**:
  ```python
  @router.post("/api/neo4j/query")
  async def neo4j_run_query(request: Request, rag_engine: Any = Depends(get_rag_engine)):
      """Execute raw Cypher query against live Neo4j."""
      try:
          body = await request.json()
          cypher_query = body.get("query", "").strip()
          if not cypher_query:
              return {"records": [], "error": "Query cannot be empty"}
          records = rag_engine.execute_cypher(cypher_query)
          return {"records": records, "query": cypher_query}
      except Exception as e:
          return {"records": [], "error": str(e)}
  ```
* **Impact**: **Arbitrary Database Manipulation & Drop**. Any anonymous client can send:
  ```json
  POST /api/neo4j/query
  {"query": "MATCH (n) DETACH DELETE n"}
  ```
  This immediately wipes out all knowledge graph nodes, relationships, and metadata. Attackers can also execute APOC procedures or dump sensitive entities.
* **Remediation**:
  1. Either **delete** this endpoint entirely if it is not required in production, OR
  2. Protect it behind an admin API key and enforce **read-only** query validation:
  ```python
  from fastapi import Security, HTTPException, status
  from fastapi.security import APIKeyHeader
  
  api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)
  
  @router.post("/api/neo4j/query")
  async def neo4j_run_query(
      request: Request,
      admin_key: str = Security(api_key_header),
      rag_engine: Any = Depends(get_rag_engine)
  ):
      if admin_key != os.getenv("ADMIN_SECRET_KEY"):
          raise HTTPException(status_code=403, detail="Forbidden: Admin credentials required")
      
      body = await request.json()
      cypher_query = body.get("query", "").strip()
      # Enforce strictly read-only Cypher
      forbidden_keywords = ["DELETE", "CREATE", "SET", "REMOVE", "MERGE", "DROP", "CALL"]
      if any(re.search(rf"\b{kw}\b", cypher_query, re.I) for kw in forbidden_keywords):
          raise HTTPException(status_code=400, detail="Only read-only MATCH/RETURN queries are permitted")
      ...
  ```

---

### VULN-02: Unauthenticated Document Deletion & Purge
* **Location**: [`src/api/routers/documents.py`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/src/api/routers/documents.py#L348-L399) (`DELETE /api/documents/{id}` and `POST /api/documents/delete`)
* **Impact**: Anyone who discovers the API endpoint can delete any user-uploaded research document, its ChromaDB vectors, and its Neo4j graph nodes.
* **Remediation**: Check session authorization or require a secret key before allowing document purges:
  ```python
  # Ensure the session_id or user token matches the document's uploaded_by metadata
  ```

---

### VULN-03: Information Disclosure in `/api/dev/recent-chats`
* **Location**: [`src/api/routers/developer.py`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/src/api/routers/developer.py#L42-L47)
* **Vulnerable Code**:
  ```python
  @router.get("/api/dev/recent-chats", response_class=JSONResponse)
  async def dev_operator_recent_chats(limit: int = 10, operator: Any = Depends(get_dev_operator)):
      if operator:
          return {"chats": operator.get_recent_chat_audit(limit=limit)}
      return {"chats": []}
  ```
* **Impact**: Exposes chat messages, user queries, session IDs, and responses from all users across the entire database to unauthenticated requests.
* **Remediation**: Restrict all `/api/dev/*` routes to local loopback (`127.0.0.1`) or require an admin Bearer token.

---

### VULN-04: IP Header Spoofing Bypasses Blacklisting
* **Location**: [`src/security/ip_resolver.py`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/src/security/ip_resolver.py#L24-L35)
* **Vulnerable Code**:
  ```python
  # 1. Cloudflare WAN header
  cf_ip = headers.get("cf-connecting-ip")
  if cf_ip and cf_ip.strip():
      return cf_ip.strip()

  # 2. X-Forwarded-For (leftmost element)
  xff = headers.get("x-forwarded-for")
  if xff and xff.strip():
      parts = [p.strip() for p in xff.split(",") if p.strip()]
      if parts:
          return parts[0]
  ```
* **Impact**: When the server is accessed directly (or behind a non-validating proxy), an attacker can supply an arbitrary `CF-Connecting-IP: 1.2.3.4` or `X-Forwarded-For: 8.8.8.8` header.
  - This completely bypasses the Redis IP blacklist `blacklist:ip:{ip}`.
  - An attacker can cause another user's IP to be blacklisted (Denial of Service).
* **Remediation**:
  Only trust `CF-Connecting-IP` or `X-Forwarded-For` if the raw socket connection `scope["client"][0]` originates from a verified trusted proxy or Cloudflare IP block. If accessed directly on LAN, fallback to the socket client IP.

---

### VULN-05: Path Traversal & File Disclosure in `/api/pdf/{filename}`
* **Location**: [`src/api/routers/documents.py`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/src/api/routers/documents.py#L263-L274)
* **Vulnerable Code**:
  ```python
  clean_name = urllib.parse.unquote(filename).strip()
  candidates = [
      DOWNLOAD_DIR / clean_name,
      DOCUMENTS_DIR / clean_name,
      Path(os.path.expanduser(f"~/Downloads/{clean_name}")),
  ]
  ```
* **Impact**:
  1. Searching `~/Downloads/` directly leaks personal files from the developer's local machine Downloads folder to the web.
  2. If `clean_name` contains path traversal characters (`../../`), it can traverse parent directories.
* **Remediation**:
  ```python
  safe_name = Path(clean_name).name  # Strips directory traversal like '../../'
  target_path = (DOCUMENTS_DIR / safe_name).resolve()
  if not target_path.is_relative_to(DOCUMENTS_DIR.resolve()) or not target_path.is_file():
      raise HTTPException(status_code=404, detail="Document not found")
  ```

---

### VULN-06: Suspicious Package `httpx2` in `requirements.txt`
* **Location**: [`requirements.txt`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/requirements.txt#L44)
* **Issue**: Line 44 lists `httpx2>=2.12.0` right after `httpx>=0.27.0`. The standard Python HTTP client is `httpx`. `httpx2` is not part of the standard library or Encode ecosystem and poses a potential typosquatting or supply-chain hazard.
* **Remediation**: Delete line 44 (`httpx2>=2.12.0`) from `requirements.txt`.

---

## 3. Bugs in `main.py` & Codebase (Detailed Review)

### BUG-01: Auto-Start Docker Containers Freezes `main.py` on Mac
* **Location**: [`main.py:92-150`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/main.py#L92-L150)
* **Mechanism**:
  On startup, `main.py` checks if Neo4j port 7687 is open. If closed, it invokes:
  ```python
  subprocess.run(["docker", "start", "raise-neo4j-prod", "raise-vllm-prod"], ...)
  ```
  On a MacBook Air:
  - If Docker Desktop is stopped, this command hangs for up to 8–15 seconds before timing out.
  - If Docker Desktop is running, `raise-vllm-prod` fails to start because there is no NVIDIA CUDA GPU driver on macOS.
  - It then loops for 8 seconds polling port 7687, producing annoying timeout warning messages.
* **Fix**: Check `os.getenv("AUTO_START_CONTAINERS", "false").lower() == "true"` before attempting Docker operations, and allow users to run purely against Cloud LLMs or standalone databases.

---

### BUG-02: Intent Classifier False-Positive on Natural Research Queries
* **Location**: [`main.py:334-398`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/main.py#L334-L398)
* **Mechanism**:
  ```python
  bot_identity_phrases = ["your name", "who are you", "what are you", ...]
  if (has_question_mark or has_interrogative_start or has_domain_term) and not any(p in t_lower for p in bot_identity_phrases):
      return {"type": "research_query"}
  ```
  If a user asks:
  - *"What are you observing in the solar energy sector at IITM?"*
  - *"Tell me what are your key insights from Table 4?"*
  
  Because `"what are you"` or `"your"` is in `bot_identity_phrases`, the research query guardrail is **negated**! The function then matches line 386 (`bot_identity`) and returns:
  ```text
  RAISE: My name is RAISE. I'm here to help you with your research. How can I assist you today?
  ```
  **The RAG pipeline is never executed!**
* **Fix**: Use regex boundaries for identity queries:
  ```python
  bot_identity_patterns = [
      r"^(?:who|what)\s+are\s+you\b(?:\s*\?)?$",
      r"^(?:what\s+is\s+your\s+name|who\s+made\s+you)\b(?:\s*\?)?$",
      r"^introduce\s+yourself\b(?:\s*\.)?$"
  ]
  if any(re.match(p, t_lower) for p in bot_identity_patterns):
      return {"type": "bot_identity"}
  ```

---

### BUG-03: Brittle `sys.argv` Handling Intercepts CLI Flags as PDF Paths
* **Location**: [`main.py:705-716`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/main.py#L705-L716)
* **Mechanism**:
  `main.py` loops over `sys.argv[1:]`:
  ```python
  for arg in sys.argv[1:]:
      if cli_arg.lower().endswith(".pdf") or Path(cli_arg).is_file():
          new_doc = ingest_pdf_from_path(cli_arg, pipeline)
  ```
  If a user runs:
  ```bash
  python main.py --llm groq -q "Hello"
  ```
  `sys.argv` has `["--llm", "groq", "-q", "Hello"]`. If a file or directory named `"groq"` or `"Hello"` happens to exist in the current working directory, `Path(cli_arg).is_file()` triggers and attempts to ingest it as a PDF!
* **Fix**: Replace manual parsing with `argparse.ArgumentParser`.

---

### BUG-04: Non-Interactive CLI Query Prompts User Interactively
* **Location**: [`main.py:640-648`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/main.py#L640-L648)
* **Mechanism**:
  When invoked headlessly via `python main.py -q "What is IITM?"`, `main.py` still invokes `prompt_llm_backend()`, which halts execution waiting for user keyboard input `[1-4]`. This completely breaks CI pipelines and automated testing.
* **Fix**: Wrap `prompt_llm_backend()` with `if not cli_query and sys.stdin.isatty():`.

---

### BUG-05: Page Range Slicing Always Starts at Page 1
* **Location**: [`main.py:477-486`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/main.py#L477-L486)
* **Mechanism**:
  When user inputs `"15-30"`, `re.findall(r"\b\d+\b", pages_inp)` returns `[15, 30]`. `pages_to_process` is set to `max(numbers)` (30), and passed as `max_pages=30`. The ingestor then ingests pages **1 to 30** instead of pages **15 to 30**.
* **Fix**: Parse both `start_page` and `end_page` and pass a tuple or slice to the ingestion pipeline.

---

### BUG-06: Manifest Write Race Condition
* **Location**: [`main.py:505-544`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/main.py#L505-L544)
* **Mechanism**:
  `manifest_file.write_text(json.dumps(manifest, indent=2))` is executed directly without file locking (`fcntl` / `portalocker`) or atomic tempfile replacement. If `server.py` and `main.py` write simultaneously, `ingested_manifest.json` is truncated or corrupted.
* **Fix**: Use atomic write (write to `ingested_manifest.json.tmp` and `os.replace`).

---

### BUG-07: Missing Binary Entry Point in `Cargo.toml`
* **Location**: [`rust/raise_engine/Cargo.toml:13`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/rust/raise_engine/Cargo.toml#L12-L15)
* **Issue**:
  `Cargo.toml` defines:
  ```toml
  [[bin]]
  name = "raise-cli"
  path = "src/bin/main.rs"
  ```
  However, the `src/bin` directory does not exist in the repository! Running `cargo build` in `rust/raise_engine/` fails with:
  ```text
  error: failed to resolve path ".../src/bin/main.rs": No such file or directory
  ```
* **Fix**: Either remove `[[bin]]` from `Cargo.toml` (if it's purely a PyO3 Python extension library) or create the missing `src/bin/main.rs` file.

---

### BUG-08: Broken Legacy `from RAG.prompts...` Imports
* **Locations**:
  - `src/features/agent/workflow.py:497`
  - `src/features/agent/router.py:223, 725`
  - `src/features/query/service.py:19`
  - `src/api/routers/chat.py:28`
* **Issue**: Legacy fallback `from RAG.prompts...` and `from RAG.src...` references an old folder structure that is not in `sys.path`. If the primary import fails, the fallback crashes with `ModuleNotFoundError: No module named 'RAG'`.
* **Fix**: Replace with standard relative or `src.` package imports.
