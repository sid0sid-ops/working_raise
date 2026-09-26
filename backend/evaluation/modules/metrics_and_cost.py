"""
Resource and Cost Profiling Module
==================================
Measures real performance, latency distributions, hardware memory consumption,
index disk footprint, throughput, and calibrated abstention rate.
Uses strictly real measurements (zero simulated/fake numbers).
"""

from __future__ import annotations

import os
import time
import math
import statistics
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil
try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False


@dataclass
class ResourceCostReport:
    median_latency_ms: float
    p95_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_qps: float
    ram_rss_mb: float
    ram_peak_mb: float
    gpu_allocated_mb: float
    gpu_reserved_mb: float
    gpu_peak_mb: float
    chromadb_size_mb: float
    processed_data_size_mb: float
    total_index_size_mb: float
    abstention_rate: float
    false_refusal_rate: float
    total_queries_tested: int
    unanswerable_tested: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResourceAndCostEvaluator:
    """Evaluates latency, throughput, RAM/GPU memory, index disk footprint, and abstention."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.process = psutil.Process(os.getpid())

    def get_directory_size_bytes(self, directory: Path) -> int:
        """Calculates exact total disk footprint in bytes of a directory."""
        if not directory.exists():
            return 0
        total = 0
        for entry in directory.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except (OSError, PermissionError):
                    pass
        return total

    def profile_memory(self) -> Dict[str, float]:
        """Gathers real RAM and GPU memory metrics."""
        mem_info = self.process.memory_info()
        ram_rss_mb = mem_info.rss / (1024 * 1024)
        ram_peak_mb = getattr(mem_info, "peak_wset", mem_info.rss) / (1024 * 1024)

        gpu_allocated_mb = 0.0
        gpu_reserved_mb = 0.0
        gpu_peak_mb = 0.0

        if _HAS_TORCH and torch.cuda.is_available():
            gpu_allocated_mb = torch.cuda.memory_allocated() / (1024 * 1024)
            gpu_reserved_mb = torch.cuda.memory_reserved() / (1024 * 1024)
            gpu_peak_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)

        return {
            "ram_rss_mb": round(ram_rss_mb, 2),
            "ram_peak_mb": round(ram_peak_mb, 2),
            "gpu_allocated_mb": round(gpu_allocated_mb, 2),
            "gpu_reserved_mb": round(gpu_reserved_mb, 2),
            "gpu_peak_mb": round(gpu_peak_mb, 2),
        }

    def profile_index_sizes(self) -> Dict[str, float]:
        """Gathers real on-disk index sizes."""
        chroma_dir = self.project_root / ".chromadb_bge_large"
        processed_dir = self.project_root / "data" / "processed"

        chroma_mb = self.get_directory_size_bytes(chroma_dir) / (1024 * 1024)
        proc_mb = self.get_directory_size_bytes(processed_dir) / (1024 * 1024)
        total_mb = chroma_mb + proc_mb

        return {
            "chromadb_size_mb": round(chroma_mb, 2),
            "processed_data_size_mb": round(proc_mb, 2),
            "total_index_size_mb": round(total_mb, 2),
        }

    def profile_latency_and_abstention(
        self,
        pipeline: Any,
        in_scope_queries: List[str],
        out_of_scope_queries: List[str],
    ) -> ResourceCostReport:
        """
        Executes real queries through pipeline to measure latency distribution,
        throughput, and calibrated abstention behavior.
        """
        latencies: List[float] = []

        # Warm-up / in-scope query execution
        false_refusals = 0
        start_time = time.perf_counter()

        for q in in_scope_queries:
            t0 = time.perf_counter()
            try:
                hits = pipeline.vector_engine.search(q, top_k=5)
                dt_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(dt_ms)
                if not hits:
                    false_refusals += 1
            except Exception as e:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(dt_ms)

        total_elapsed_sec = time.perf_counter() - start_time
        throughput_qps = len(in_scope_queries) / max(total_elapsed_sec, 0.001)

        # Out-of-scope queries (calibrated abstention)
        refused_count = 0
        from src.features.query.intake import IntentRouterNode

        router = IntentRouterNode()
        for q in out_of_scope_queries:
            route_res = router.route(q)
            # If detected as adversarial or chitchat or bypass retrieval, it correctly abstains
            if route_res.bypass_retrieval or route_res.intent in ("OUT_OF_SCOPE", "GENERAL_CHAT"):
                refused_count += 1
            else:
                # If classified as academic, check if similarity is very low
                hits = pipeline.vector_engine.search(q, top_k=5)
                if not hits or (hits and hits[0].get("similarity", 0.0) < 0.25):
                    refused_count += 1

        abstention_rate = refused_count / max(len(out_of_scope_queries), 1)
        false_refusal_rate = false_refusals / max(len(in_scope_queries), 1)

        # Percentiles
        if latencies:
            sorted_lat = sorted(latencies)
            median_ms = statistics.median(sorted_lat)
            idx_95 = min(int(math.ceil(0.95 * len(sorted_lat))) - 1, len(sorted_lat) - 1)
            p95_ms = sorted_lat[max(idx_95, 0)]
            min_ms = sorted_lat[0]
            max_ms = sorted_lat[-1]
        else:
            median_ms = p95_ms = min_ms = max_ms = 0.0

        mem = self.profile_memory()
        idx_sizes = self.profile_index_sizes()

        return ResourceCostReport(
            median_latency_ms=round(median_ms, 2),
            p95_latency_ms=round(p95_ms, 2),
            min_latency_ms=round(min_ms, 2),
            max_latency_ms=round(max_ms, 2),
            throughput_qps=round(throughput_qps, 2),
            ram_rss_mb=mem["ram_rss_mb"],
            ram_peak_mb=mem["ram_peak_mb"],
            gpu_allocated_mb=mem["gpu_allocated_mb"],
            gpu_reserved_mb=mem["gpu_reserved_mb"],
            gpu_peak_mb=mem["gpu_peak_mb"],
            chromadb_size_mb=idx_sizes["chromadb_size_mb"],
            processed_data_size_mb=idx_sizes["processed_data_size_mb"],
            total_index_size_mb=idx_sizes["total_index_size_mb"],
            abstention_rate=round(abstention_rate, 4),
            false_refusal_rate=round(false_refusal_rate, 4),
            total_queries_tested=len(in_scope_queries),
            unanswerable_tested=len(out_of_scope_queries),
        )
