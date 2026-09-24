"""
RAISE Evaluation Framework — Default Configuration & Manifest Generator
Version: 1.0.0
"""

from __future__ import annotations

import os
import json
import hashlib
import platform
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

EVAL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = EVAL_ROOT.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"


@dataclass
class DatabaseConfig:
    pg_host: str = os.getenv("POSTGRES_HOST", "localhost")
    pg_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    pg_db: str = os.getenv("POSTGRES_DB", "raise_db")
    pg_user: str = os.getenv("POSTGRES_USER", "raise_user")
    pg_password: str = os.getenv("POSTGRES_PASSWORD", "raise_password")

    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))

    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password123")

    chroma_dir: str = str(BACKEND_ROOT / ".chromadb_bge_large")
    chroma_collection: str = "iitmrp_docling_bge_large"


@dataclass
class QualityGateConfig:
    faithfulness_threshold: float = 0.80
    max_retries: int = 1
    table_integrity_enabled: bool = True
    citation_validation_enabled: bool = True


@dataclass
class AblationConfig:
    config_id: str = "ABL-G"  # ABL-A to ABL-H
    name: str = "Full Verified RAG"
    use_dense: bool = True
    use_bm25: bool = True
    use_neo4j: bool = True
    use_rrf: bool = True
    rrf_k: int = 60
    table_boost_enabled: bool = True
    use_reranker: bool = True
    reranker_top_k: int = 6
    use_langgraph: bool = True
    use_quality_gate: bool = True
    use_memory: bool = False


ABLATION_REGISTRY: Dict[str, AblationConfig] = {
    "ABL-A": AblationConfig(
        config_id="ABL-A", name="BM25 Only",
        use_dense=False, use_bm25=True, use_neo4j=False, use_rrf=False,
        use_reranker=False, use_langgraph=False, use_quality_gate=False, use_memory=False
    ),
    "ABL-B": AblationConfig(
        config_id="ABL-B", name="Dense Only",
        use_dense=True, use_bm25=False, use_neo4j=False, use_rrf=False,
        use_reranker=False, use_langgraph=False, use_quality_gate=False, use_memory=False
    ),
    "ABL-C": AblationConfig(
        config_id="ABL-C", name="Dense + BM25",
        use_dense=True, use_bm25=True, use_neo4j=False, use_rrf=True,
        use_reranker=False, use_langgraph=False, use_quality_gate=False, use_memory=False
    ),
    "ABL-D": AblationConfig(
        config_id="ABL-D", name="Dense + BM25 + Neo4j",
        use_dense=True, use_bm25=True, use_neo4j=True, use_rrf=True,
        use_reranker=False, use_langgraph=False, use_quality_gate=False, use_memory=False
    ),
    "ABL-E": AblationConfig(
        config_id="ABL-E", name="Full Retrieval (Dense + BM25 + Neo4j + RRF + Reranker)",
        use_dense=True, use_bm25=True, use_neo4j=True, use_rrf=True,
        use_reranker=True, use_langgraph=False, use_quality_gate=False, use_memory=False
    ),
    "ABL-F": AblationConfig(
        config_id="ABL-F", name="Full RAG (Retrieval + LangGraph + LLM)",
        use_dense=True, use_bm25=True, use_neo4j=True, use_rrf=True,
        use_reranker=True, use_langgraph=True, use_quality_gate=False, use_memory=False
    ),
    "ABL-G": AblationConfig(
        config_id="ABL-G", name="Full Verified RAG (Production Default)",
        use_dense=True, use_bm25=True, use_neo4j=True, use_rrf=True,
        use_reranker=True, use_langgraph=True, use_quality_gate=True, use_memory=False
    ),
    "ABL-H": AblationConfig(
        config_id="ABL-H", name="Full Verified RAG + Memory (PG 16 + Redis 7)",
        use_dense=True, use_bm25=True, use_neo4j=True, use_rrf=True,
        use_reranker=True, use_langgraph=True, use_quality_gate=True, use_memory=True
    ),
}


def get_git_commit() -> str:
    try:
        import subprocess
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "UNKNOWN_GIT_COMMIT"


def get_runtime_manifest() -> Dict[str, Any]:
    return {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "git_commit": get_git_commit(),
        "embedding_model": "BAAI/bge-large-en-v1.5",
        "embedding_dimension": 1024,
        "reranker_model": "BAAI/bge-reranker-large",
        "llm_backend": os.getenv("LLM_BACKEND", "groq"),
        "llm_model": os.getenv("LLM_MODEL_NAME", "llama-3.3-70b-versatile"),
        "quality_gate_model": "dleemiller/finecat-nli-l",
        "chroma_dir": str(BACKEND_ROOT / ".chromadb_bge_large"),
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "postgres_db": os.getenv("POSTGRES_DB", "raise_db"),
        "redis_host": os.getenv("REDIS_HOST", "localhost"),
    }


def compute_config_hash(ablation: AblationConfig, gate: QualityGateConfig) -> str:
    raw = json.dumps({
        "ablation": asdict(ablation),
        "gate": asdict(gate),
        "runtime": get_runtime_manifest(),
    }, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
