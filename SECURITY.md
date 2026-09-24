# 🛡️ RAISE: Research Assessment Intelligence & Semantic Extraction — Security Policy & Guardrails

> **Security Posture:** Zero Cloud AI Data Leakage | Zero Exposed Secrets | $0 Cost Guarantee

---

## 🔒 1. Architecture Security Model

RAISE (Research Assessment Intelligence & Semantic Extraction) is designed for privacy-preserving, institutional, and defense-grade academic research environments:

1. **100% Local Inference**: All language model inference (`Qwen2.5-14B-Instruct-GPTQ-Int4`) runs locally on private GPU hardware via vLLM. No institutional documents, internal queries, or chat logs are ever transmitted to third-party proprietary APIs (OpenAI, Anthropic, or Google).
2. **Zero Inbound Port Forwarding**: External access via remote frontends (e.g. GitHub Pages) is routed through outbound-only Cloudflare QUIC Tunnels (`cloudflared`). The local host requires zero open firewall ports or static public IPs.
3. **Internal Docker Network Isolation**: PostgreSQL, Redis, Neo4j, and vLLM run on an isolated Docker bridge network (`raise-production_raise-prod-network`). Only the FastAPI backend and Cloudflare tunnel communicate with the outside world.

---

## 🔑 2. Secret Management Policy

### Strict Rules
- **No Credentials in Version Control**: API keys, Cloudflare tokens, database passwords, and private certificates must never be committed to Git.
- **Gitignore Enforcement**: The root [`.gitignore`](.gitignore) and [`RAG/.gitignore`](RAG/.gitignore) files strictly ignore:
  - All `.env` and `.env.*` files (except `.env.example`).
  - All binary databases (`*.sqlite3`, `.chromadb_bge_large/`, `.runtime/`).
  - Compiled executables and binary installers (`*.exe`, `*.msi`, `bin/`).
- **Sanitized Templates**: Only [`.env.example`](.env.example) containing sanitized placeholders is permitted in the repository.

### Verifying Git Cleanliness
To verify that no secrets or tokens exist in Git commit history or working tree:
```bash
# Check for Cloudflare token prefixes or tokens
git log -p | grep -E "eyJh|cfat_|b35b7d7b"
# Check working tree for uncommitted secrets
git diff | grep -E "eyJh|CLOUDFLARE_R2_SECRET"
```

---

## 💳 3. Cloudflare R2 Zero-Cost Billing Guardrails

To prevent accidental credit card charges on Cloudflare accounts, RAISE implements **hardcoded software circuit breakers** in [`RAG/src/storage_engine.py`](RAG/src/storage_engine.py).

### Enforced Safety Thresholds

| Metric | Cloudflare Free Monthly Allowance | RAISE Hard Safety Ceiling | Status |
| :--- | :--- | :--- | :--- |
| **Object Storage** | 10 GB / month free | **5.0 GB** (50% safety buffer) | **ENFORCED** |
| **Class A Operations** (write/list) | 1,000,000 ops / month free | **100,000 ops** (10% safety buffer) | **ENFORCED** |
| **Class B Operations** (read) | 10,000,000 ops / month free | **1,000,000 ops** (10% safety buffer) | **ENFORCED** |

### Automated Circuit Breaker & Local Disk Fallback
1. **Real-time Counter Tracking**: Storage size and operation counters are tracked in Redis and memory.
2. **Automatic Tripping**: If any operation would exceed the safety ceiling, the engine automatically trips the circuit breaker:
   - R2 cloud uploads are halted immediately.
   - Files are automatically routed to local storage disk (`data/documents/`).
   - A warning log is dispatched: `Free tier safety limit exceeded; fallback to local storage`.
   - The user's credit card is protected from any charges.

---

## 🌐 4. CORS & Web Security

FastAPI enforces strict Cross-Origin Resource Sharing (CORS):
- **Dynamic Regex Whitelisting**: Matches exact GitHub Pages domains (`^https:\/\/.*\.github\.io$`) and Cloudflare Quick Tunnels (`^https:\/\/.*\.trycloudflare\.com$`).
- **Credential Protection**: Wildcard origins (`*`) are disallowed when credentials/cookies are enabled, preventing CSRF or credential leakage.
- **Keep-Alive SSE Heartbeats**: SSE streaming streams `: keepalive\n\n` comments to prevent connection dropouts or malicious buffer saturation attacks.

---

## 🚨 Reporting a Vulnerability

If you identify any security issue or vulnerability in the RAISE codebase, please open a private GitHub Security Advisory or report it directly to the repository maintainers.
