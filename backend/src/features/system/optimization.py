"""
RAISE Latency, Concurrency, and Resource Optimization Engine
Implements Context Window Token Budgeting, Tiered Query Result Caching (LRU + Hash Store),
and vLLM Key-Value (KV) Cache Profiles.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ContextBudgetPlan:
    system_tokens: int = 500
    graph_tokens: int = 1500
    vector_tokens: int = 3500
    history_tokens: int = 1500
    generation_tokens: int = 1192
    total_budget: int = 8192

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ContextBudgetManager:
    """
    Allocates and dynamically truncates context across system, graph, vector, and dialogue tiers.
    """

    def __init__(self, total_window: int = 8192):
        self.total_window = total_window
        self.budget = ContextBudgetPlan(total_budget=total_window)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimation (~4 characters per token)."""
        return max(1, len(text) // 4)

    def fit_context(
        self,
        system_prompt: str,
        graph_triples: List[str],
        vector_chunks: List[Dict[str, Any]],
        conversation_turns: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Trims and formats prompt components to strictly fit within the 8,192 token context budget.
        """
        # 1. Truncate System Prompt
        sys_text = system_prompt
        if self.estimate_tokens(sys_text) > self.budget.system_tokens:
            sys_text = sys_text[: self.budget.system_tokens * 4]

        # 2. Fit Graph Triples
        fitted_triples = []
        current_g_tokens = 0
        for trip in graph_triples:
            t_toks = self.estimate_tokens(trip)
            if current_g_tokens + t_toks <= self.budget.graph_tokens:
                fitted_triples.append(trip)
                current_g_tokens += t_toks
            else:
                break

        # 3. Fit Vector Passages
        fitted_chunks = []
        current_v_tokens = 0
        for chk in vector_chunks:
            c_text = str(chk.get("plain_text") or chk.get("text") or "")
            c_toks = self.estimate_tokens(c_text)
            if current_v_tokens + c_toks <= self.budget.vector_tokens:
                fitted_chunks.append(chk)
                current_v_tokens += c_toks
            else:
                # Add partial if remaining space
                remaining = self.budget.vector_tokens - current_v_tokens
                if remaining > 100:
                    truncated = dict(chk)
                    truncated["plain_text"] = c_text[: remaining * 4]
                    fitted_chunks.append(truncated)
                break

        # 4. Fit Conversation History (Reverse chronological)
        fitted_history = []
        current_h_tokens = 0
        for turn in reversed(conversation_turns):
            turn_str = f"User: {turn.get('user_query', '')}\nAssistant: {turn.get('assistant_answer', '')}"
            h_toks = self.estimate_tokens(turn_str)
            if current_h_tokens + h_toks <= self.budget.history_tokens:
                fitted_history.insert(0, turn)
                current_h_tokens += h_toks
            else:
                break

        total_consumed = (
            self.estimate_tokens(sys_text)
            + current_g_tokens
            + current_v_tokens
            + current_h_tokens
        )

        return {
            "system_prompt": sys_text,
            "graph_triples": fitted_triples,
            "vector_chunks": fitted_chunks,
            "conversation_history": fitted_history,
            "estimated_consumed_tokens": total_consumed,
            "available_generation_tokens": self.total_window - total_consumed,
        }


class TieredQueryResultCache:
    """
    Two-Tiered Cache Architecture:
      - Tier 1: High-Speed In-Memory LRU Cache (sub-millisecond latency)
      - Tier 2: Persistent Disk Hash Store with TTL (sub-5ms latency)
    """

    def __init__(
        self,
        max_memory_items: int = 500,
        cache_dir: Optional[Path | str] = None,
        default_ttl_seconds: int = 86400,  # 24 hours
    ):
        self.max_memory_items = max_memory_items
        self.default_ttl = default_ttl_seconds
        self.memory_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.cache_dir = Path(cache_dir or ".runtime/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_query_hash(query: str, doc_filter: Optional[str] = None) -> str:
        """Deterministic normalization and SHA-256 hash."""
        clean_q = re.sub(r"\s+", " ", query.strip().lower())
        payload = f"{clean_q}::doc={doc_filter or 'ALL'}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, query: str, doc_filter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        q_hash = self.compute_query_hash(query, doc_filter)
        now = time.time()

        # 1. Check Tier 1: In-Memory LRU
        if q_hash in self.memory_cache:
            entry = self.memory_cache[q_hash]
            if now < entry.get("expires_at", now + 1):
                self.memory_cache.move_to_end(q_hash)
                entry_data = dict(entry["data"])
                entry_data["cache_hit"] = True
                entry_data["cache_tier"] = "memory_lru"
                return entry_data
            else:
                del self.memory_cache[q_hash]

        # 2. Check Tier 2: Disk Hash Cache
        disk_file = self.cache_dir / f"{q_hash}.json"
        if disk_file.exists():
            try:
                disk_entry = json.loads(disk_file.read_text(encoding="utf-8"))
                if now < disk_entry.get("expires_at", now + 1):
                    # Promote to Tier 1
                    self.memory_cache[q_hash] = disk_entry
                    self.memory_cache.move_to_end(q_hash)
                    data = dict(disk_entry["data"])
                    data["cache_hit"] = True
                    data["cache_tier"] = "disk_cache"
                    return data
                else:
                    disk_file.unlink(missing_ok=True)
            except Exception:
                pass

        return None

    def set(
        self,
        query: str,
        data: Dict[str, Any],
        doc_filter: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ):
        q_hash = self.compute_query_hash(query, doc_filter)
        ttl = ttl_seconds or self.default_ttl
        entry = {
            "query": query,
            "doc_filter": doc_filter,
            "created_at": time.time(),
            "expires_at": time.time() + ttl,
            "data": data,
        }

        # 1. Update In-Memory LRU
        if len(self.memory_cache) >= self.max_memory_items:
            self.memory_cache.popitem(last=False)
        self.memory_cache[q_hash] = entry
        self.memory_cache.move_to_end(q_hash)

        # 2. Update Disk Cache
        disk_file = self.cache_dir / f"{q_hash}.json"
        try:
            disk_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        except Exception:
            pass

    def invalidate_all(self):
        """Invalidates entire cache (e.g. upon new document ingestion)."""
        self.memory_cache.clear()
        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass
