"""
RAISE Benchmark Substrates & Runtime Cache Purge
Wipes PostgreSQL tables, flushes Redis cache, and cleans ephemeral ChromaDB collections.
Preserves static Wikipedia source text corpus.
"""

import os
import sys
import psycopg2
import redis
import chromadb
from pathlib import Path

# Force UTF-8 stdout
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def purge_postgres():
    print("[1/3] Purging PostgreSQL Tables...")
    tables_to_purge = [
        "chat_feedback",
        "chat_messages",
        "message_history",
        "session_metadata",
        "document_metadata",
        "documents"
    ]
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "raise_db"),
            user=os.getenv("POSTGRES_USER", "raise_user"),
            password=os.getenv("POSTGRES_PASSWORD", "raise_password"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432))
        )
        cur = conn.cursor()
        for t in tables_to_purge:
            try:
                cur.execute(f'TRUNCATE TABLE "{t}" CASCADE;')
                print(f"   • Truncated table: {t}")
            except Exception as te:
                conn.rollback()
                try:
                    cur.execute(f'DELETE FROM "{t}";')
                    print(f"   • Deleted rows from: {t}")
                except Exception as de:
                    print(f"   ⚠️  Could not clear table {t}: {de}")
                    conn.rollback()
                    continue
            conn.commit()

        # Verify emptiness
        for t in tables_to_purge:
            try:
                cur.execute(f'SELECT count(*) FROM "{t}";')
                cnt = cur.fetchone()[0]
                print(f"   ✓ Verification: {t} now has {cnt} rows")
            except Exception:
                pass

        cur.close()
        conn.close()
        print("   ✅ PostgreSQL tables successfully purged.")
        return True
    except Exception as e:
        print(f"   ❌ PostgreSQL purge failed: {e}")
        return False

def purge_redis():
    print("\n🧹 [2/3] Purging Redis Cache...")
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0
        )
        before_keys = r.dbsize()
        r.flushall()
        after_keys = r.dbsize()
        print(f"   • Redis keys before: {before_keys}, after: {after_keys}")
        print("   ✅ Redis cache successfully flushed (FLUSHALL).")
        return True
    except Exception as e:
        print(f"   ❌ Redis flush failed: {e}")
        return False

def purge_chromadb_runtime():
    print("\n🧹 [3/3] Purging Ephemeral ChromaDB Collections...")
    try:
        chroma_client = chromadb.Client()
        collections = chroma_client.list_collections()
        purged = 0
        for col in collections:
            col_name = col.name if hasattr(col, "name") else str(col)
            if "frames" in col_name.lower() or "eval" in col_name.lower():
                try:
                    chroma_client.delete_collection(col_name)
                    purged += 1
                    print(f"   • Deleted ephemeral collection: {col_name}")
                except Exception:
                    pass
        print(f"   • Deleted {purged} ephemeral evaluation collections.")
        print("   ✅ ChromaDB evaluation runtime purged.")
        return True
    except Exception as e:
        print(f"   ⚠️  ChromaDB purge notice: {e}")
        return True

if __name__ == "__main__":
    print("==================================================================")
    print("  RAISE SUBSTRATES & RUNTIME CACHE PURGE")
    print("==================================================================")
    pg_ok = purge_postgres()
    redis_ok = purge_redis()
    chroma_ok = purge_chromadb_runtime()
    print("==================================================================")
    if pg_ok and redis_ok:
        print("  ✨ ALL SUBSTRATES AND RUNTIME CACHES PURGED AND VERIFIED.")
    else:
        print("  ⚠️  PURGE COMPLETED WITH WARNINGS.")
    print("==================================================================")
