# 07. Cloud PostgreSQL & Cloud Redis: Providers, Limits, & Setup Guide

This guide details how to pair the RAISE backend with **100% Free Cloud Databases** (PostgreSQL and Redis) alongside Cloud LLMs (Groq, Google Gemini).

Using cloud databases allows any developer on an **8GB MacBook Air** or **Windows laptop** to achieve full persistence (saved chat history, document metadata, and sub-millisecond semantic caching) with **zero local background processes, 0 MB local RAM usage, and zero risk of surprise bills**.

---

## 1. Complete Free Cloud Substrate Matrix

| Database Type | Recommended Cloud Provider | Free Tier Allowance | Inactivity Policy | Credit Card Needed? |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL (Primary)** | **[Neon.tech](https://neon.tech)** | **0.5 GB** Storage<br>• Unlimited database branches<br>• Built-in PgBouncer connection pooling | Scales to zero after 5 min idle (wakes instantly in ~500ms) | ❌ **No** |
| **PostgreSQL (Alternative)** | **[Supabase](https://supabase.com)** | **0.5 GB** Storage<br>• 2 active free projects<br>• 5 GB monthly bandwidth | Pauses after 7 days of inactivity (1-click unpause) | ❌ **No** |
| **Redis (Primary)** | **[Upstash](https://upstash.com)** | **10,000 commands / day**<br>• **256 MB** RAM storage<br>• Max 100 concurrent connections | **Never sleeps** (Always-on serverless) | ❌ **No** |
| **Redis (Alternative)** | **[Redis Cloud](https://redis.io/cloud/)** | **30 MB** RAM storage<br>• 30 concurrent connections | **Never sleeps** (Always-on fixed instance) | ❌ **No** |
| **Graph DB** | **[Neo4j AuraDB](https://neo4j.com/cloud/platform/aura-graph-database/)** | **200,000 Nodes**<br>• **400,000 Relationships** | Pauses after 3 days of no queries (1-click unpause) | ❌ **No** |

---

## 2. Cloud PostgreSQL: Neon.tech (Recommended)

### Why Neon?
Neon is a serverless PostgreSQL built specifically for cloud-native apps. It separates storage from compute, meaning when your laptop closes or the server is idle, it uses **zero compute hours**.

### Exact Free Limits
* **Storage**: 0.5 GB (500 MB).
  * *Capacity Estimate*: Enough to store **~500,000 chat messages** and metadata for **~5,000 uploaded research PDFs**.
* **Compute**: 100 Compute Hours per month (more than enough for daily development).
* **Connection Pooling**: Neon provides an integrated PgBouncer pooler (`-pooler` in hostname) so hundreds of async FastAPI workers won't exhaust connection limits.

### Step-by-Step Setup (2 Minutes)
1. Sign up for free at [neon.tech](https://neon.tech) using GitHub or Google.
2. Click **Create Project** $\rightarrow$ Name it `raise-db`.
3. Neon will display your **Connection Details**:
   ```text
   postgres://alex:AbCd1234EfGh@ep-cool-fog-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Map these values into your RAISE `.env`:
   ```bash
   POSTGRES_HOST=ep-cool-fog-123456-pooler.us-east-2.aws.neon.tech
   POSTGRES_PORT=5432
   POSTGRES_DB=neondb
   POSTGRES_USER=alex
   POSTGRES_PASSWORD=AbCd1234EfGh
   POSTGRES_SSLMODE=require
   ```

---

## 3. Cloud Redis: Upstash (Recommended)

### Why Upstash?
Standard Redis servers require continuous virtual machines that consume RAM 24/7. **Upstash is 100% Serverless**; you pay only per command, and the free tier gives you **10,000 requests every single day for free**.

### Exact Free Limits
* **Daily Commands**: 10,000 commands/day.
  * *Capacity Estimate*: Each chat interaction performs 1–3 cache lookups. 10,000 commands allows for **3,000+ research queries per day**.
* **Memory Capacity**: 256 MB.
  * *Capacity Estimate*: Holds ~50,000 cached semantic answers or ~100,000 active session rate tokens.
* **Max Concurrent Connections**: 100 simultaneous connections.
* **Max Request Size**: 1 MB per value.

### Step-by-Step Setup (2 Minutes)
1. Sign up for free at [upstash.com](https://upstash.com) with GitHub.
2. Go to **Redis** $\rightarrow$ Click **Create Database**.
3. Choose:
   * **Name**: `raise-cache`
   * **Region**: Select the region closest to you (e.g., `us-east-1` or `eu-west-1`).
   * **Type**: Serverless.
4. Under **Connect Details**, select the **`redis-py`** tab. You will see:
   ```text
   Host: useful-elephant-12345.upstash.io
   Port: 6379
   Password: your_upstash_password_here
   ```
5. Map these into your RAISE `.env`:
   ```bash
   REDIS_HOST=useful-elephant-12345.upstash.io
   REDIS_PORT=6379
   REDIS_PASSWORD=your_upstash_password_here
   REDIS_SSL=true
   ```

---

## 4. How RAISE Protects You From Hitting Free Limits

The RAISE backend contains built-in defensive architecture to ensure you never exceed free quotas:

```mermaid
flowchart TD
    Req(["Incoming Query / Upload"]) --> Guard{"Free Tier Guardrail\n(src/infrastructure/storage/r2.py)"}
    
    %% Storage Guard
    Guard -->|Under 500MB / 10K Ops| ExecDB["Execute in Cloud DB\n(Neon Postgres / Upstash Redis)"]
    
    %% Over Limit Fallback
    Guard -->|Quota Threshold Warning| AutoFallback["Graceful Fallback Mode\n(Auto-switches to Python In-Memory)"]
    
    AutoFallback --> AlertUser["Log Warning in Terminal\n('Cloud quota reached; using in-memory session')"]
    ExecDB --> Success(["Response Returned"])
    AlertUser --> Success
```

1. **Auto-Expiry / LRU Eviction in Redis**:
   - The cache manager ([`src/infrastructure/cache/redis.py`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/src/infrastructure/cache/redis.py)) sets strict **24-hour TTL (Time-To-Live)** on session memory and **7-day TTL** on query completions.
   - Stale data automatically expires, preventing your 256 MB Upstash limit from ever filling up.
2. **Postgres In-Memory Fallback Shield**:
   - If Neon goes into deep sleep or the connection drops momentarily, [`PostgresManager`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/src/infrastructure/database/postgres.py) catches the connection timeout within 2 seconds and switches to in-memory dictionaries without crashing the user session.
3. **Zero Credit Card Guarantee**:
   - Neither Neon nor Upstash requires a credit card to activate the free tier. If you somehow hit 10,000 commands in a single day, Upstash simply rejects additional commands until midnight UTC, and RAISE seamlessly falls back to local memory. **You cannot be charged.**

---

## 5. Master Ready-to-Copy `.env` for 100% Free Cloud Deployment

Copy and paste this into `.env` for a fully functional, zero-local-resource cloud setup:

```bash
# ==============================================================================
# RAISE 100% FREE CLOUD STACK CONFIGURATION
# (Zero Docker, Zero Local Models, Zero Local RAM)
# ==============================================================================

# 1. Environment & Operational Mode
ENVIRONMENT=development
LOG_LEVEL=INFO
USE_RUST_CORE=false

# 2. Cloud LLM Inference (Free Tier)
# Get free Groq key (500 tokens/sec): https://console.groq.com/keys
GROQ_API_KEY=gsk_your_groq_api_key_here

# Get free Gemini key (1M token context): https://aistudio.google.com/
GEMINI_API_KEY=your_gemini_api_key_here

# 3. Cloud Graph Database (Neo4j AuraDB Free)
# Free at: https://neo4j.com/cloud/platform/aura-graph-database/
NEO4J_URI=neo4j+s://your-subdomain.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password_here

# 4. Cloud Relational Database (Neon Serverless Postgres)
# Free at: https://neon.tech
POSTGRES_HOST=ep-your-endpoint-pooler.us-east-2.aws.neon.tech
POSTGRES_PORT=5432
POSTGRES_DB=neondb
POSTGRES_USER=your_neon_user
POSTGRES_PASSWORD=your_neon_password
POSTGRES_SSLMODE=require

# 5. Cloud Fast Cache (Upstash Serverless Redis)
# Free at: https://upstash.com
REDIS_HOST=your-endpoint.upstash.io
REDIS_PORT=6379
REDIS_PASSWORD=your_upstash_password
REDIS_SSL=true

# 6. Local Vector Storage (Pure In-Memory / File SQLite - Zero Server)
VECTOR_DB_TYPE=chroma
CHROMA_PERSIST_DIR=./data/chroma
```

---

## 6. Verification Checklist

To verify your cloud connections after updating `.env`:

```bash
# 1. Test Cloud Redis connection
python -c "from src.infrastructure.cache.redis import RedisCacheManager; rd = RedisCacheManager(); print('Redis Online:', rd.is_connected)"

# 2. Test Cloud Postgres connection
python -c "from src.infrastructure.database.postgres import PostgresManager; pg = PostgresManager(); print('Postgres Online:', pg.is_connected)"

# 3. Test Cloud Neo4j connection
python -c "from src.core.graph_database import Neo4jClient; neo = Neo4jClient(); print('Neo4j Online:', neo.verify_connectivity())"
```
If any show `False`, the backend will **automatically fallback to in-memory mode** without halting the application!
