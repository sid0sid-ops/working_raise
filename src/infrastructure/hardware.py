"""
RAISE Dynamic System Hardware & Subsystem Telemetry Engine
Authoritative module for zero-hardcoding dynamic discovery of:
- Host RAM, CPU, and Platform Architecture (via psutil & platform)
- GPU Accelerators and VRAM (via torch.cuda / nvidia-smi / MPS)
- Multi-Backend LLM Orchestration & Fallback Chain
- Database Substrates (PostgreSQL, Redis, Neo4j, ChromaDB)

Strict Security & Privacy Guarantees:
- Zero hardcoded host specs (RAM, GPU names, user home directories).
- Never exposes sensitive credentials, secret tokens, or API keys.
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_ram_info() -> Dict[str, Any]:
    """Dynamically detects physical and virtual memory using psutil without hardcoded fallbacks."""
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {
            "detected": True,
            "total_gb": round(vm.total / (1024 ** 3), 2),
            "available_gb": round(vm.available / (1024 ** 3), 2),
            "used_gb": round(vm.used / (1024 ** 3), 2),
            "percent_used": vm.percent,
        }
    except Exception as e:
        return {
            "detected": False,
            "total_gb": None,
            "available_gb": None,
            "used_gb": None,
            "percent_used": None,
            "error": str(e),
        }


def get_cpu_info() -> Dict[str, Any]:
    """Dynamically detects host CPU cores and architecture."""
    cpu_data: Dict[str, Any] = {
        "architecture": platform.machine(),
        "processor": platform.processor() or "Unknown",
        "system": platform.system(),
        "release": platform.release(),
        "python_version": platform.python_version(),
    }
    try:
        import psutil
        cpu_data["physical_cores"] = psutil.cpu_count(logical=False)
        cpu_data["logical_cores"] = psutil.cpu_count(logical=True)
        cpu_data["cpu_percent"] = psutil.cpu_percent(interval=None)
    except Exception:
        cpu_data["physical_cores"] = os.cpu_count()
        cpu_data["logical_cores"] = os.cpu_count()
        cpu_data["cpu_percent"] = None
    return cpu_data


def get_gpu_info() -> Dict[str, Any]:
    """
    Dynamically interrogates available GPU hardware and VRAM allocation.
    Never hardcodes GPU model names, memory capacities, or device vendors.
    """
    devices: List[Dict[str, Any]] = []
    cuda_available = False
    mps_available = False

    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        if hasattr(torch.backends, "mps"):
            mps_available = bool(torch.backends.mps.is_available())

        if cuda_available:
            count = torch.cuda.device_count()
            for idx in range(count):
                name = torch.cuda.get_device_name(idx)
                props = torch.cuda.get_device_properties(idx)
                total_vram_bytes = getattr(props, "total_memory", getattr(props, "total_mem", 0))
                total_vram_gb = round(total_vram_bytes / (1024 ** 3), 2)

                free_vram_gb = None
                try:
                    free_bytes, total_bytes = torch.cuda.mem_get_info(idx)
                    free_vram_gb = round(free_bytes / (1024 ** 3), 2)
                except Exception:
                    pass

                allocated_vram_gb = round(torch.cuda.memory_allocated(idx) / (1024 ** 3), 2)

                devices.append({
                    "device_index": idx,
                    "name": name,
                    "total_vram_gb": total_vram_gb,
                    "free_vram_gb": free_vram_gb,
                    "allocated_vram_gb": allocated_vram_gb,
                    "compute_capability": f"{props.major}.{props.minor}",
                    "multi_processor_count": getattr(props, "multi_processor_count", None),
                })
    except Exception as e:
        return {
            "detected": False,
            "cuda_available": False,
            "mps_available": False,
            "device_count": 0,
            "devices": [],
            "error": str(e),
        }

    primary_name = devices[0]["name"] if devices else ("Apple MPS" if mps_available else "CPU Only (No GPU)")
    primary_vram = devices[0]["total_vram_gb"] if devices else None

    return {
        "detected": True,
        "cuda_available": cuda_available,
        "mps_available": mps_available,
        "device_count": len(devices),
        "devices": devices,
        "primary_device_name": primary_name,
        "primary_vram_gb": primary_vram,
    }


def get_llm_telemetry() -> Dict[str, Any]:
    """
    Dynamically interrogates active and configured LLM providers.
    Ensures zero key exposure - only checks whether keys are configured.
    """
    active_backend = os.getenv("LLM_BACKEND", "vllm").lower().strip()
    fallback_chain = ["vllm", "groq", "cohere", "gemini", "deepseek", "nvidia"]

    providers_status: Dict[str, Dict[str, Any]] = {
        "vllm": {
            "configured": True,
            "url": os.getenv("VLLM_BASE_URL", "http://localhost:8002/v1"),
            "model": os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4"),
        },
        "groq": {
            "configured": bool(os.getenv("GROQ_API_KEY")),
            "model": os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
        },
        "cohere": {
            "configured": bool(os.getenv("COHERE_API_KEY")),
            "model": os.getenv("COHERE_CHAT_MODEL", "command-r-plus-08-2024"),
        },
        "gemini": {
            "configured": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        },
        "deepseek": {
            "configured": bool(os.getenv("DEEPSEEK_API_KEY")),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner"),
        },
        "nvidia": {
            "configured": bool(os.getenv("NVIDIA_API_KEY")),
            "model": os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
        },
    }

    return {
        "active_backend": active_backend,
        "fallback_chain": fallback_chain,
        "providers": providers_status,
    }


def get_database_telemetry() -> Dict[str, Any]:
    """
    Dynamically interrogates status of all primary databases (Neo4j, Chroma, Redis, Postgres).
    Catches all exceptions gracefully to ensure zero disruption.
    """
    db_status: Dict[str, Any] = {
        "neo4j": {"online": False, "nodes": 0, "relationships": 0},
        "chroma": {"online": False, "chunks": 0},
        "redis": {"online": False, "keys": 0},
        "postgres": {"online": False},
    }

    # Neo4j
    try:
        from src.infrastructure.graph.neo4j import Neo4jDatabase
        with Neo4jDatabase() as db:
            conn = db.check_connection()
            if conn.get("connected"):
                db_status["neo4j"] = {
                    "online": True,
                    "nodes": conn.get("total_nodes", 0),
                    "relationships": conn.get("total_relationships", 0),
                    "latency_ms": conn.get("latency_ms"),
                }
    except Exception as e:
        db_status["neo4j"]["error"] = str(e)

    # ChromaDB
    try:
        from src.infrastructure.vector.chroma import LocalVectorEngine
        vec = LocalVectorEngine()
        if vec.collection is not None:
            db_status["chroma"] = {
                "online": True,
                "chunks": vec.collection.count(),
                "collection_name": vec.collection_name,
                "dimension": vec.dimension,
            }
    except Exception as e:
        db_status["chroma"]["error"] = str(e)

    # Redis
    try:
        from src.infrastructure.cache.redis import RedisCacheManager
        rd = RedisCacheManager()
        if getattr(rd, "is_connected", False) and rd._client:
            info = rd._client.info()
            db_status["redis"] = {
                "online": True,
                "keys": rd._client.dbsize(),
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
        else:
            db_status["redis"] = {"online": False, "mode": "in-memory fallback"}
    except Exception as e:
        db_status["redis"]["error"] = str(e)

    # PostgreSQL
    try:
        from src.infrastructure.database.postgres import PostgresManager
        pg = PostgresManager()
        conn = pg._get_connection()
        if conn:
            conn.close()
            db_status["postgres"] = {"online": True}
        else:
            db_status["postgres"] = {"online": False, "mode": "in-memory fallback"}
    except Exception as e:
        db_status["postgres"] = {"online": False, "error": str(e)}

    return db_status


def get_system_manifest() -> Dict[str, Any]:
    """
    Produces a complete, sanitized hardware and subsystem specification manifest.
    Contains zero user paths, zero sensitive tokens, and zero hardcoded specs.
    """
    ram = get_ram_info()
    cpu = get_cpu_info()
    gpu = get_gpu_info()
    llm = get_llm_telemetry()
    db = get_database_telemetry()

    return {
        "host": {
            "os": cpu.get("system"),
            "os_release": cpu.get("release"),
            "arch": cpu.get("architecture"),
            "python": cpu.get("python_version"),
        },
        "memory": ram,
        "cpu": cpu,
        "gpu": gpu,
        "llm": llm,
        "databases": db,
    }


def format_hardware_summary() -> str:
    """Returns a one-line human-readable hardware string for CLI banners and logs."""
    ram = get_ram_info()
    gpu = get_gpu_info()

    ram_str = f"{ram['total_gb']}GB RAM" if ram.get("total_gb") else "RAM N/A"
    if gpu.get("cuda_available") and gpu.get("devices"):
        primary = gpu["devices"][0]
        gpu_str = f"{primary['name']} ({primary['total_vram_gb']}GB VRAM)"
    elif gpu.get("mps_available"):
        gpu_str = "Apple Silicon MPS"
    else:
        gpu_str = "CPU Mode (No CUDA GPU)"

    return f"{gpu_str} | {ram_str} | {platform.system()} ({platform.machine()})"
