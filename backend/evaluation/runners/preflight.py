"""
Pre-Flight Infrastructure & Model Health Checker for RAISE Evaluation Framework
Enforces fail-fast validation of databases, local models, and offline cache before benchmark execution.
"""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

logger = logging.getLogger("raise.eval.preflight")

EVAL_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = EVAL_ROOT.parent
PROJECT_ROOT = BACKEND_ROOT.parent


class PreflightHealthChecker:
    """
    Validates infrastructure prerequisites, offline model caches, and database connectivity.
    Aborts execution early if critical dependencies are missing or misconfigured.
    """

    @staticmethod
    def check_neo4j(uri: str, user: str, password: str) -> Tuple[bool, str]:
        """Validates Neo4j connectivity and verifies node count."""
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=3.0)
            driver.verify_connectivity()
            with driver.session() as session:
                res = session.run("MATCH (n) RETURN count(n) as cnt").single()
                node_cnt = res["cnt"] if res else 0
            driver.close()
            if node_cnt == 0:
                return False, f"Neo4j connected at {uri}, but database contains 0 nodes."
            return True, f"Neo4j operational ({node_cnt} nodes verified at {uri})"
        except Exception as e:
            return False, f"Neo4j connection failed at {uri}: {e}"

    @staticmethod
    def check_redis(redis_url: str) -> Tuple[bool, str]:
        """Validates Redis connection, preferring local Redis with cloud fallback."""
        # 1. Prefer local Redis (localhost:6379)
        try:
            import redis
            r_local = redis.Redis(host="localhost", port=6379, socket_timeout=1.5)
            r_local.ping()
            return True, "Local Redis cache operational (localhost:6379)"
        except Exception:
            pass

        # 2. Fall back to cloud Redis (e.g. Upstash)
        try:
            import redis
            cloud_url = os.getenv("UPSTASH_REDIS_URL") or redis_url
            r_cloud = redis.from_url(cloud_url, socket_timeout=3.0, socket_connect_timeout=3.0)
            r_cloud.ping()
            return True, f"Cloud Redis operational ({cloud_url.split('@')[-1] if '@' in cloud_url else cloud_url})"
        except Exception as e:
            return False, f"Redis unreachable ({e}); falling back to in-memory TTL cache"

    @staticmethod
    def check_chromadb(persist_dir: Path | str, collection_name: str) -> Tuple[bool, str]:
        """Validates local ChromaDB vector store."""
        p = Path(persist_dir).resolve()
        if not p.exists():
            return False, f"ChromaDB persist directory not found at {p}"
        try:
            from src.infrastructure.vector.chroma import get_shared_chroma_client
            client = get_shared_chroma_client(p)
            if client is None:
                return False, f"Could not acquire shared ChromaDB client for {p}"
            colls = [c.name for c in client.list_collections()]
            if collection_name not in colls:
                return False, f"Collection '{collection_name}' not found in ChromaDB. Available: {colls}"
            col = client.get_collection(collection_name)
            count = col.count()
            return True, f"ChromaDB operational ({count} chunks in collection '{collection_name}')"
        except Exception as e:
            return False, f"ChromaDB initialization error: {e}"

    @staticmethod
    def enforce_offline_model_environment() -> None:
        """Sets environment variables to eliminate runtime HuggingFace network pings."""
        # Enable offline mode for verified cached models
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
        # Set default cache folder to user's huggingface cache
        default_hf_home = str(Path.home() / ".cache" / "huggingface" / "hub")
        os.environ.setdefault("HF_HOME", default_hf_home)

    @classmethod
    def run_all_checks(cls, ablation_config: Any, fail_fast: bool = True) -> Dict[str, Any]:
        """
        Executes complete pre-flight health suite.
        If fail_fast is True and a required component fails, exits with non-zero status.
        """
        print("\n" + "=" * 80)
        print("  RAISE PRE-FLIGHT INFRASTRUCTURE & MODEL HEALTH CHECK")
        print("=" * 80)

        cls.enforce_offline_model_environment()
        results: Dict[str, Any] = {}
        fatal_errors = []

        # 1. Neo4j Check
        use_neo4j = getattr(ablation_config, "use_neo4j", True)
        if use_neo4j:
            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_pwd = os.getenv("NEO4J_PASSWORD", "password123")
            ok, msg = cls.check_neo4j(neo4j_uri, neo4j_user, neo4j_pwd)
            results["neo4j"] = {"status": "PASS" if ok else "FAIL", "detail": msg}
            icon = "[PASS]" if ok else "[FAIL]"
            print(f"  {icon} Neo4j Graph DB       : {msg}")
            if not ok:
                fatal_errors.append(f"Neo4j: {msg}")
        else:
            print("  [SKIP] Neo4j Graph DB       : Disabled by ablation config.")

        # 2. Redis Check
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        ok_redis, msg_redis = cls.check_redis(redis_url)
        results["redis"] = {"status": "PASS" if ok_redis else "WARN", "detail": msg_redis}
        icon_redis = "[PASS]" if ok_redis else "[WARN]"
        print(f"  {icon_redis} Redis Cache Layer    : {msg_redis}")

        # 3. ChromaDB Check
        chroma_env = os.getenv("CHROMA_PERSIST_DIRECTORY", ".chromadb_bge_large")
        candidate_paths = [
            BACKEND_ROOT / chroma_env.lstrip("./\\"),
            PROJECT_ROOT / chroma_env.lstrip("./\\"),
            Path(chroma_env),
            BACKEND_ROOT / ".chromadb_bge_large",
        ]
        resolved_chroma = None
        for cp in candidate_paths:
            if cp.resolve().exists():
                resolved_chroma = cp.resolve()
                break
        chroma_dir = resolved_chroma or Path(chroma_env).resolve()
        chroma_coll = os.getenv("CHROMA_COLLECTION_NAME", "raise_docling_bge_large")
        ok_chroma, msg_chroma = cls.check_chromadb(chroma_dir, chroma_coll)
        results["chromadb"] = {"status": "PASS" if ok_chroma else "FAIL", "detail": msg_chroma}
        icon_chroma = "[PASS]" if ok_chroma else "[FAIL]"
        print(f"  {icon_chroma} Chroma Vector DB     : {msg_chroma}")
        if not ok_chroma:
            fatal_errors.append(f"ChromaDB: {msg_chroma}")

        # 4. LLM API Key Check
        groq_key = os.getenv("GROQ_API_KEY")
        mistral_key = os.getenv("MISTRAL_API_KEY")
        nvidia_key = os.getenv("NVIDIA_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        active_keys = [k for k, v in [("Groq", groq_key), ("Mistral", mistral_key), ("NVIDIA", nvidia_key), ("Gemini", gemini_key)] if v]
        if active_keys:
            print(f"  [PASS] LLM Cloud Providers  : Active credentials found for {', '.join(active_keys)}")
            results["llm"] = {"status": "PASS", "active_providers": active_keys}
        else:
            print("  [WARN] LLM Cloud Providers  : No cloud API keys found. Checking local vLLM...")
            results["llm"] = {"status": "WARN", "detail": "Local only"}

        print("=" * 80 + "\n")

        if fatal_errors and fail_fast:
            logger.error("Pre-flight health check FAILED. Aborting evaluation run to prevent degraded benchmarks:")
            for err in fatal_errors:
                logger.error(f"  - {err}")
            sys.exit(1)

        return results
