"""
RAISE — Full System Purge & Clean Slate
Completely resets:
1. Neo4j Knowledge Graph (MATCH (n) DETACH DELETE n)
2. ChromaDB Vector Store (.chromadb_bge_large)
3. Processed Chunks, Triples, Facts, Manifests
4. Documents Library in data/documents
"""
import os
import sys
import shutil
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def reset_all():
    print("=" * 70)
    print("⚡ [PURGE] Initiating complete system purge...")
    print("=" * 70)

    # 1. Neo4j Purge
    print("\n1. Purging Neo4j Database...")
    try:
        from src.infrastructure.graph.neo4j import Neo4jDatabase
        neo = Neo4jDatabase()
        if neo.connected:
            res = neo.purge_all_nodes()
            print(f"   ✅ Neo4j purged: {res.get('nodes_deleted', 0)} nodes deleted.")
        else:
            print("   ⚠️ Neo4j offline / not connected.")
        neo.close()
    except Exception as e:
        print(f"   ⚠️ Neo4j purge notice: {e}")

    # 2. ChromaDB Purge
    print("\n2. Purging ChromaDB Vector Store...")
    try:
        from src.core.config import settings
        chroma_dir = Path(settings.vector.persist_directory) if settings else BASE_DIR / ".chromadb_bge_large"
        from src.infrastructure.vector.chroma import LocalVectorEngine
        ve = LocalVectorEngine()
        if hasattr(ve, "client") and ve.client is not None:
            try:
                ve.client.delete_collection("bge_large")
                print("   ✅ Collection 'bge_large' deleted.")
            except Exception as e:
                print(f"   Notice deleting collection: {e}")
        del ve
    except Exception as e:
        print(f"   ⚠️ ChromaDB client purge notice: {e}")

    # Remove Chroma persistence directory if desired
    chroma_path = BASE_DIR / ".chromadb_bge_large"
    if chroma_path.exists():
        try:
            shutil.rmtree(chroma_path)
            print(f"   ✅ Removed directory: {chroma_path}")
        except Exception as e:
            print(f"   Notice removing chroma dir: {e}")

    # 3. Clean Processed Data Directory
    print("\n3. Cleaning processed data artifacts...")
    processed_dir = BASE_DIR / "data" / "processed"
    for sub in ["chunks", "facts", "graph_triples", "neo4j"]:
        sub_path = processed_dir / sub
        if sub_path.exists():
            shutil.rmtree(sub_path)
            sub_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ Cleared data/processed/{sub}/")

    manifest_file = processed_dir / "ingested_manifest.json"
    manifest_file.write_text('{"ready_documents": [], "deleted_documents": []}', encoding="utf-8")
    print("   ✅ Reset data/processed/ingested_manifest.json")

    # 4. Clean Staged Documents Library
    print("\n4. Clearing data/documents/ staged library...")
    docs_dir = BASE_DIR / "data" / "documents"
    if docs_dir.exists():
        for f in docs_dir.glob("*"):
            if f.is_file():
                try:
                    f.unlink()
                    print(f"   🗑️ Removed: {f.name}")
                except Exception as e:
                    print(f"   Notice removing {f.name}: {e}")
    docs_dir.mkdir(parents=True, exist_ok=True)

    # 5. Flush Redis if connected
    print("\n5. Checking Redis cache...")
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, db=0, socket_timeout=0.5)
        r.flushdb()
        print("   ✅ Redis cache flushed (FLUSHDB).")
        r.close()
    except Exception:
        print("   Notice: Redis offline or flushed.")

    print("\n" + "=" * 70)
    print("✨ [PURGE COMPLETE] System is at pristine ZERO state.")
    print("=" * 70)

if __name__ == "__main__":
    reset_all()
