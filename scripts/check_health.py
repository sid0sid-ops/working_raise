import os
import time
import psycopg2
import redis
import requests
from neo4j import GraphDatabase

print("=== CHECKING SERVICES AND DATABASES ===", flush=True)

# 1. Postgres
try:
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "raise_db"),
        user=os.getenv("POSTGRES_USER", "raise_user"),
        password=os.getenv("POSTGRES_PASSWORD", "raise_password"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        connect_timeout=5,
    )
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = [r[0] for r in cur.fetchall()]
    counts = {}
    for t in tables:
        cur.execute(f'SELECT count(*) FROM "{t}";')
        counts[t] = cur.fetchone()[0]
    conn.close()
    print(f"[POSTGRES] OK! Connected on port 5432. Tables found: {len(tables)}. Row counts: {counts}", flush=True)
except Exception as e:
    print(f"[POSTGRES] ERROR: {e}", flush=True)

# 2. Redis
try:
    r = redis.Redis(host="localhost", port=6379, db=0, socket_timeout=5)
    pong = r.ping()
    keys = r.dbsize()
    # test write and read
    r.set("health_check_test_key", "healthy_and_fast", ex=10)
    val = r.get("health_check_test_key").decode("utf-8")
    print(f"[REDIS] OK! Connected on port 6379. Ping={pong}, Total Keys={keys}, Read/Write Test Value='{val}'", flush=True)
except Exception as e:
    print(f"[REDIS] ERROR: {e}", flush=True)

# 3. Neo4j
try:
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"), connection_timeout=5)
    with driver.session() as s:
        res = s.run("RETURN 1 as val").single()
        cnt = s.run("MATCH (n) RETURN count(n) as cnt").single()["cnt"]
    driver.close()
    print(f"[NEO4J] OK! Connected on port 7687. Total Nodes in Graph={cnt}", flush=True)
except Exception as e:
    print(f"[NEO4J] ERROR: {e}", flush=True)

# 4. vLLM
try:
    resp = requests.get("http://localhost:8002/v1/models", timeout=5)
    if resp.status_code == 200:
        models = [m["id"] for m in resp.json().get("data", [])]
        print(f"[vLLM] OK! Service responsive on port 8002. Models: {models}", flush=True)
    else:
        print(f"[vLLM] Status {resp.status_code}: {resp.text}", flush=True)
except Exception as e:
    print(f"[vLLM] Starting or connecting: {e}", flush=True)

# 5. Wiki Cache
project_root = Path(__file__).resolve().parents[2]
wiki_cache_dir = project_root / "Artifacts" / "benchmarks" / "cache" / "wiki"
if wiki_cache_dir.exists():
    files = [f for f in os.listdir(wiki_cache_dir) if f.endswith(".json")]
    print(f"[WIKI CACHE] OK! Cached Wikipedia documents found: {len(files)} files in {wiki_cache_dir}", flush=True)
else:
    print(f"[WIKI CACHE] NOT FOUND at {wiki_cache_dir}", flush=True)
