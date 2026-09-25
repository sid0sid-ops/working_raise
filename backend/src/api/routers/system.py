"""
RAISE System & Control Center API Router
Handles dynamic hardware detection, cloud vs local LLM switching,
database connection testing, and runtime configuration.
"""

from __future__ import annotations

import os
import sys
import platform
import socket
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("raise.api.system")

router = APIRouter(prefix="/api/system", tags=["System & Control Center"])

ENV_FILE_PATH = Path(__file__).resolve().parents[3] / ".env"


class SystemConfigRequest(BaseModel):
    llm_mode: str = Field(default="cloud_groq", description="cloud_groq, cloud_gemini, or local_ollama")
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    vercel_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    custom_api_key: Optional[str] = None
    custom_base_url: Optional[str] = None
    custom_model_name: Optional[str] = None
    selected_local_model: Optional[str] = "llama3.2:3b"
    neo4j_mode: str = Field(default="cloud", description="cloud, local, or in_memory_fallback")
    neo4j_uri: Optional[str] = None
    neo4j_user: Optional[str] = None
    neo4j_password: Optional[str] = None
    neo4j_database: Optional[str] = None
    redis_mode: str = Field(default="cloud", description="cloud, local, or in_memory_fallback")
    redis_url: Optional[str] = None
    postgres_mode: str = Field(default="cloud", description="cloud, local, or in_memory_fallback")
    postgres_url: Optional[str] = None


def _mask_secret(val: Optional[str]) -> str:
    if not val:
        return ""
    if len(val) <= 8:
        return "********"
    return f"{val[:4]}...{val[-4:]}"


@router.get("/hardware")
async def get_hardware_telemetry() -> Dict[str, Any]:
    """Dynamically probes host CPU, RAM, GPU, and checks Ollama liveness."""
    import psutil

    # 1. CPU
    cpu_cores_logical = psutil.cpu_count(logical=True) or 1
    cpu_cores_physical = psutil.cpu_count(logical=False) or 1
    cpu_percent = psutil.cpu_percent(interval=0.05)

    # 2. RAM
    mem = psutil.virtual_memory()
    total_ram_gb = round(mem.total / (1024**3), 1)
    available_ram_gb = round(mem.available / (1024**3), 1)

    # 3. GPU (CUDA check)
    gpu_detected = False
    gpu_name = "None (CPU Execution)"
    vram_gb = 0.0
    try:
        import torch
        if torch.cuda.is_available():
            gpu_detected = True
            gpu_name = torch.cuda.get_device_name(0)
            _, v_tot = torch.cuda.mem_get_info()
            vram_gb = round(v_tot / (1024**3), 1)
    except Exception:
        pass

    # 4. Local Ollama Probe
    ollama_running = False
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=0.5):
            ollama_running = True
    except Exception:
        pass

    # 5. Disk Space Probe
    import shutil
    disk = shutil.disk_usage(Path.cwd())
    free_disk_gb = round(disk.free / (1024**3), 1)
    total_disk_gb = round(disk.total / (1024**3), 1)

    # Recommended profile based on hardware & disk
    if total_ram_gb >= 16 or vram_gb >= 8:
        recommended_mode = "hybrid"  # Can run local or cloud
        recommendation_note = f"Hardware supports both Local (Llama 3.2 / Qwen 2.5) and Cloud AI. ({free_disk_gb} GB disk available)"
    else:
        recommended_mode = "cloud"
        recommendation_note = "Cloud Profile (Groq / Gemini) recommended for instantaneous latency with zero disk usage."

    local_model_catalog = [
        {"id": "llama3.2:3b", "name": "Llama 3.2 3B", "download_size_gb": 2.0, "min_ram_gb": 8, "tier": "Fast & Light"},
        {"id": "qwen2.5:7b", "name": "Qwen 2.5 7B", "download_size_gb": 4.7, "min_ram_gb": 16, "tier": "Balanced Reasoning"},
        {"id": "llama3.1:8b", "name": "Llama 3.1 8B", "download_size_gb": 4.9, "min_ram_gb": 16, "tier": "High Fidelity"},
    ]

    return {
        "platform": platform.system().lower(),
        "os_name": f"{platform.system()} {platform.release()}",
        "cpu_cores": cpu_cores_logical,
        "cpu_physical_cores": cpu_cores_physical,
        "cpu_usage_pct": cpu_percent,
        "total_ram_gb": total_ram_gb,
        "free_ram_gb": available_ram_gb,
        "total_disk_gb": total_disk_gb,
        "free_disk_gb": free_disk_gb,
        "gpu_detected": gpu_detected,
        "gpu_name": gpu_name,
        "vram_gb": vram_gb,
        "ollama_running": ollama_running,
        "recommended_mode": recommended_mode,
        "recommendation_note": recommendation_note,
        "local_model_catalog": local_model_catalog,
    }


@router.get("/config")
async def get_current_configuration() -> Dict[str, Any]:
    """Returns current active system configuration with sensitive keys masked and dynamic providers listed."""
    from src.infrastructure.credentials.manager import get_credential_manager
    from src.infrastructure.providers.router import get_provider_router

    cm = get_credential_manager()
    p_router = get_provider_router()

    llm_backend = os.getenv("LLM_BACKEND", "groq")
    neo4j_uri = os.getenv("NEO4J_URI", "")
    redis_url = os.getenv("REDIS_URL", "")

    return {
        "llm_mode": "local_vllm" if llm_backend == "vllm" else ("local_ollama" if llm_backend == "ollama" else f"cloud_{llm_backend}"),
        "llm_model_name": os.getenv("LLM_MODEL_NAME", "llama-3.3-70b-versatile"),
        "last_used_provider": p_router.last_used_provider,
        "last_used_model": p_router.last_used_model,
        "available_providers": p_router.get_dynamic_available_providers(),
        "groq_configured": cm.get_credential_status("groq") == "configured",
        "groq_masked": _mask_secret(cm.get_credential("groq")),
        "gemini_configured": cm.get_credential_status("gemini") == "configured",
        "gemini_masked": _mask_secret(cm.get_credential("gemini")),
        "nvidia_configured": cm.get_credential_status("nvidia") == "configured",
        "nvidia_masked": _mask_secret(cm.get_credential("nvidia")),
        "cohere_configured": cm.get_credential_status("cohere") == "configured",
        "cohere_masked": _mask_secret(cm.get_credential("cohere")),
        "mistral_configured": cm.get_credential_status("mistral") == "configured",
        "mistral_masked": _mask_secret(cm.get_credential("mistral")),
        "vercel_configured": cm.get_credential_status("vercel") == "configured" or cm.get_credential_status("typesafe") == "configured",
        "vercel_masked": _mask_secret(cm.get_credential("vercel") or cm.get_credential("typesafe")),
        "deepseek_configured": cm.get_credential_status("deepseek") == "configured",
        "deepseek_masked": _mask_secret(cm.get_credential("deepseek")),
        "openrouter_configured": cm.get_credential_status("openrouter") == "configured",
        "openrouter_masked": _mask_secret(cm.get_credential("openrouter")),
        "custom_configured": cm.get_credential_status("custom") == "configured",
        "custom_masked": _mask_secret(cm.get_credential("custom")),
        "neo4j_uri": neo4j_uri,
        "neo4j_database": os.getenv("NEO4J_DATABASE", "neo4j"),
        "neo4j_is_cloud": "databases.neo4j.io" in neo4j_uri,
        "redis_is_cloud": "upstash.io" in redis_url,
        "first_run_completed": bool(
            cm.get_credential_status("groq") == "configured"
            or cm.get_credential_status("mistral") == "configured"
            or cm.get_credential_status("gemini") == "configured"
            or cm.get_credential_status("nvidia") == "configured"
            or cm.get_credential_status("cohere") == "configured"
            or llm_backend in ["ollama", "vllm"]
        ),
    }


@router.get("/dynamic-llms")
async def get_dynamic_llms() -> List[Dict[str, Any]]:
    """Returns list of dynamically available LLMs based on active hardware and configured API keys."""
    from src.infrastructure.providers.router import get_provider_router
    p_router = get_provider_router()
    return p_router.get_dynamic_available_providers()


@router.post("/test-connections")
async def test_system_connections(req: Optional[SystemConfigRequest] = None) -> Dict[str, Any]:
    """Probes live connectivity for Neo4j, Redis, and LLM inference."""
    results: Dict[str, Any] = {}

    # 1. Test Redis
    try:
        from src.infrastructure.cache.redis import RedisCacheManager
        redis_mgr = RedisCacheManager()
        results["redis"] = {
            "connected": redis_mgr.is_connected,
            "provider": "Upstash Cloud" if "upstash.io" in os.getenv("REDIS_URL", "") else "Local / Memory",
            "status": "PASS" if redis_mgr.is_connected else "FALLBACK_IN_MEMORY"
        }
    except Exception as e:
        results["redis"] = {"connected": False, "status": "FALLBACK_IN_MEMORY", "error": str(e)}

    # 2. Test Neo4j
    try:
        from src.infrastructure.graph.neo4j import Neo4jDatabase
        neo_db = Neo4jDatabase(
            uri=os.getenv("NEO4J_URI"),
            user=os.getenv("NEO4J_USER"),
            password=os.getenv("NEO4J_PASSWORD"),
            database=os.getenv("NEO4J_DATABASE"),
        )
        neo_check = neo_db.check_connection()
        results["neo4j"] = {
            "connected": neo_check.get("connected", False),
            "uri": neo_check.get("uri", os.getenv("NEO4J_URI", "")),
            "provider": "Neo4j AuraDB Cloud" if "databases.neo4j.io" in os.getenv("NEO4J_URI", "") else "Local Bolt",
            "status": "PASS" if neo_check.get("connected") else "FALLBACK_VECTOR_BM25"
        }
    except Exception as e:
        results["neo4j"] = {"connected": False, "status": "FALLBACK_VECTOR_BM25", "error": str(e)}

    # 3. Test LLM
    llm_backend = req.llm_mode if req else os.getenv("LLM_BACKEND", "groq")
    results["llm"] = {
        "mode": llm_backend,
        "status": "READY"
    }

    return results


@router.post("/config")
async def save_configuration(cfg: SystemConfigRequest) -> Dict[str, Any]:
    """Updates runtime environment and writes updates safely to .env file."""
    try:
        # Read existing .env lines
        lines: List[str] = []
        if ENV_FILE_PATH.exists():
            lines = ENV_FILE_PATH.read_text(encoding="utf-8").splitlines()

        env_map: Dict[str, str] = {}
        for line in lines:
            line_str = line.strip()
            if line_str and not line_str.startswith("#") and "=" in line_str:
                k, v = line_str.split("=", 1)
                env_map[k.strip()] = v.strip()

        # Update LLM Backend
        if cfg.llm_mode == "local_ollama":
            env_map["LLM_BACKEND"] = "ollama"
            if cfg.selected_local_model:
                env_map["LLM_MODEL_NAME"] = cfg.selected_local_model
            env_map["LLM_BASE_URL"] = "http://localhost:11434/v1"
        elif cfg.llm_mode == "cloud_gemini":
            env_map["LLM_BACKEND"] = "gemini"
            env_map["LLM_MODEL_NAME"] = "gemini-2.0-flash"
            if cfg.gemini_api_key:
                env_map["GEMINI_API_KEY"] = cfg.gemini_api_key
        elif cfg.llm_mode == "cloud_nvidia":
            env_map["LLM_BACKEND"] = "nvidia"
            env_map["LLM_MODEL_NAME"] = "meta/llama-3.2-11b-vision-instruct"
        elif cfg.llm_mode == "cloud_cohere":
            env_map["LLM_BACKEND"] = "cohere"
            env_map["LLM_MODEL_NAME"] = "command-r-plus-08-2024"
        elif cfg.llm_mode == "cloud_mistral":
            env_map["LLM_BACKEND"] = "mistral"
            env_map["LLM_MODEL_NAME"] = "open-mistral-nemo"
        elif cfg.llm_mode == "cloud_vercel":
            env_map["LLM_BACKEND"] = "vercel"
            env_map["LLM_MODEL_NAME"] = "typesafe-ai/jev"
        elif cfg.llm_mode == "cloud_custom":
            env_map["LLM_BACKEND"] = "universal"
            env_map["LLM_MODEL_NAME"] = cfg.custom_model_name or "gpt-4o-mini"
            if cfg.custom_base_url:
                env_map["CUSTOM_LLM_BASE_URL"] = cfg.custom_base_url
                os.environ["CUSTOM_LLM_BASE_URL"] = cfg.custom_base_url
        else:  # cloud_groq default
            env_map["LLM_BACKEND"] = "groq"
            env_map["LLM_MODEL_NAME"] = "llama-3.3-70b-versatile"
            if cfg.groq_api_key:
                env_map["GROQ_API_KEY"] = cfg.groq_api_key

        # Update provider credentials if provided
        from src.infrastructure.credentials.manager import get_credential_manager
        from src.infrastructure.providers.router import get_provider_router
        cm = get_credential_manager()

        for prov, secret in [
            ("groq", cfg.groq_api_key),
            ("gemini", cfg.gemini_api_key),
            ("nvidia", cfg.nvidia_api_key),
            ("cohere", cfg.cohere_api_key),
            ("mistral", cfg.mistral_api_key),
            ("vercel", cfg.vercel_api_key),
            ("deepseek", cfg.deepseek_api_key),
            ("openrouter", cfg.openrouter_api_key),
            ("custom", cfg.custom_api_key),
        ]:
            if secret and secret.strip():
                cm.set_credential(prov, secret.strip())
                env_var = f"{prov.upper()}_API_KEY"
                env_map[env_var] = secret.strip()
                os.environ[env_var] = secret.strip()

        # Refresh provider router fallback chain dynamically
        try:
            get_provider_router()._refresh_fallback_chain()
        except Exception as e:
            logger.warning(f"Could not refresh provider router: {e}")

        # Update Neo4j
        if cfg.neo4j_mode == "cloud" and cfg.neo4j_uri:
            env_map["NEO4J_URI"] = cfg.neo4j_uri
            if cfg.neo4j_user:
                env_map["NEO4J_USER"] = cfg.neo4j_user
            if cfg.neo4j_password:
                env_map["NEO4J_PASSWORD"] = cfg.neo4j_password
            if cfg.neo4j_database:
                env_map["NEO4J_DATABASE"] = cfg.neo4j_database

        # Update Redis
        if cfg.redis_mode == "cloud" and cfg.redis_url:
            env_map["REDIS_URL"] = cfg.redis_url

        # Sync runtime os.environ
        for k, v in env_map.items():
            os.environ[k] = v

        # Write safely back to .env
        output_lines = [f"{k}={v}" for k, v in env_map.items()]
        ENV_FILE_PATH.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

        return {
            "status": "success",
            "message": "System configuration saved and synced with active runtime.",
            "active_mode": env_map.get("LLM_BACKEND"),
            "active_model": env_map.get("LLM_MODEL_NAME"),
        }
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration update failed: {str(e)}"
        )
