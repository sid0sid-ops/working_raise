"""
RAISE Complete Test Data & Ephemeral Substrate Purge
Safely clears all transient testing/benchmark data across all layers:
  1. PostgreSQL: document metadata, session records, chat history
  2. Redis: cache, token buckets, and active session keys (FLUSHALL)
  3. ChromaDB: clears academic_chunks collection (resets to 0 vectors)
  4. Neo4j: MATCH (n) DETACH DELETE n (leaves schema indexes intact)
  5. File artifacts: chunks, facts, graph_triples, manifest, and test PDFs
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# Project root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def purge_postgres():
    print("\n[1/5] Purging PostgreSQL Tables...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "raise_db"),
            user=os.getenv("POSTGRES_USER", "raise_user"),
            password=os.getenv("POSTGRES_PASSWORD", "raise_password"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            connect_timeout=3
        )
        cur = conn.cursor()
        tables = [
            "chat_feedback",
            "chat_messages",
            "message_history",
            "session_metadata",
            "document_metadata",
            "documents"
        ]
        for t in tables:
            try:
                cur.execute(f'TRUNCATE TABLE "{t}" CASCADE;')
                print(f"   ✓ Truncated table: {t}")
            except Exception:
                conn.rollback()
                try:
                    cur.execute(f'DELETE FROM "{t}";')
                    print(f"   ✓ Deleted rows from: {t}")
                except Exception:
                    conn.rollback()
            conn.commit()

        # Verification
        counts = {}
        for t in tables:
            try:
                cur.execute(f'SELECT count(*) FROM "{t}";')
                counts[t] = cur.fetchone()[0]
            except Exception:
                pass
        cur.close()
        conn.close()
        print(f"   PostgreSQL Verification: {counts}")
        return True
    except Exception as e:
        print(f"   ⚠️ PostgreSQL purge notice: {e}")
        return False


def purge_redis():
    print("\n[2/5] Purging Redis Cache...")
    try:
        import redis
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            socket_timeout=3
        )
        before = r.dbsize()
        r.flushall()
        after = r.dbsize()
        print(f"   ✓ Redis keys before: {before}, after: {after}")
        return True
    except Exception as e:
        print(f"   ⚠️ Redis purge notice: {e}")
        return False


def purge_chromadb():
    print("\n[3/5] Purging ChromaDB Vector Store...")
    try:
        from src.infrastructure.vector.chroma import LocalVectorEngine
        ve = LocalVectorEngine()
        before_cnt = ve.collection.count()
        ve.client.delete_collection("academic_chunks")
        ve.collection = ve.client.get_or_create_collection("academic_chunks")
        after_cnt = ve.collection.count()
        print(f"   ✓ ChromaDB vectors before: {before_cnt}, after: {after_cnt}")
        return True
    except Exception as e:
        print(f"   ⚠️ ChromaDB purge notice: {e}")
        return False


def purge_neo4j():
    print("\n[4/5] Purging Neo4j Knowledge Graph...")
    try:
        from src.infrastructure.graph.neo4j import Neo4jDatabase
        neo = Neo4jDatabase()
        with neo.driver.session() as session:
            before_n = session.run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
            before_r = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
            session.run("MATCH (n) DETACH DELETE n")
            after_n = session.run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
            after_r = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
        neo.close()
        print(f"   ✓ Neo4j nodes before: {before_n}, after: {after_n}")
        print(f"   ✓ Neo4j relationships before: {before_r}, after: {after_r}")
        return True
    except Exception as e:
        print(f"   ⚠️ Neo4j purge notice: {e}")
        return False


def purge_file_artifacts(delete_test_pdfs: bool = True):
    print("\n[5/5] Purging Processed JSON Artifacts & Test PDFs...")
    processed_dir = BASE_DIR / "data" / "processed"
    subdirs = ["chunks", "facts", "graph_triples", "neo4j"]
    deleted_files = 0
    for s in subdirs:
        sd = processed_dir / s
        if sd.exists():
            for f in sd.glob("*"):
                if f.is_file():
                    f.unlink()
                    deleted_files += 1

    manifest = processed_dir / "ingested_manifest.json"
    if manifest.exists():
        manifest.unlink()
        deleted_files += 1

    print(f"   ✓ Deleted {deleted_files} processed JSON artifacts")

    if delete_test_pdfs:
        doc_dir = BASE_DIR / "data" / "documents"
        pdf_count = 0
        if doc_dir.exists():
            for pdf in doc_dir.glob("*.pdf"):
                pdf.unlink()
                pdf_count += 1
        print(f"   ✓ Deleted {pdf_count} test PDFs from data/documents/")

    return True


def purge_all(delete_test_pdfs: bool = True):
    print("=" * 72)
    print(" 🧹 PURGING ALL TESTING DATA ACROSS ALL SUBSTRATES")
    print("=" * 72)
    p_ok = purge_postgres()
    r_ok = purge_redis()
    c_ok = purge_chromadb()
    n_ok = purge_neo4j()
    f_ok = purge_file_artifacts(delete_test_pdfs=delete_test_pdfs)
    print("\n" + "=" * 72)
    print(" ✨ COMPLETE ZERO-STATE PURGE COMPLETED")
    print("=" * 72)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-pdfs", action="store_true", help="Preserve test PDFs in data/documents/")
    args = parser.parse_args()
    purge_all(delete_test_pdfs=not args.keep_pdfs)
