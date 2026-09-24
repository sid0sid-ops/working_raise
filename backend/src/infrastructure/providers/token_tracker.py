"""
RAISE Infrastructure — Token Usage & Accounting Tracker (Per LLM)
Maintains thread-safe, persistent token accounting across all registered LLM providers:
- Prompt / Input Tokens
- Completion / Output Tokens
- Total Tokens & Call Invocations
- Cost Estimation per Provider & Model
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("raise.infrastructure.providers.token_tracker")

# Standardized token pricing per 1K tokens (est. blended USD)
PROVIDER_PRICING_PER_1K: Dict[str, Dict[str, float]] = {
    "groq": {"prompt": 0.00059, "completion": 0.00079},
    "gemini": {"prompt": 0.00015, "completion": 0.00060},
    "deepseek": {"prompt": 0.00014, "completion": 0.00028},
    "nvidia": {"prompt": 0.00070, "completion": 0.00090},
    "openrouter": {"prompt": 0.00150, "completion": 0.00200},
    "cohere": {"prompt": 0.00100, "completion": 0.00200},
    "vllm": {"prompt": 0.00000, "completion": 0.00000},  # Local compute: $0.00 API bill
}


class LLMTokenStats:
    """Token accumulation container for an individual provider."""

    def __init__(self, provider: str):
        self.provider = provider
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0
        self.requests_count: int = 0
        self.last_active_timestamp: Optional[float] = None
        self.active_model: str = "default"

    def record_usage(self, prompt_tokens: int, completion_tokens: int, model: Optional[str] = None) -> None:
        self.prompt_tokens += max(0, prompt_tokens)
        self.completion_tokens += max(0, completion_tokens)
        self.total_tokens = self.prompt_tokens + self.completion_tokens
        self.requests_count += 1
        self.last_active_timestamp = time.time()
        if model:
            self.active_model = model

    @property
    def estimated_cost_usd(self) -> float:
        pricing = PROVIDER_PRICING_PER_1K.get(self.provider.lower(), {"prompt": 0.001, "completion": 0.002})
        cost_in = (self.prompt_tokens / 1000.0) * pricing["prompt"]
        cost_out = (self.completion_tokens / 1000.0) * pricing["completion"]
        return round(cost_in + cost_out, 5)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "active_model": self.active_model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "requests_count": self.requests_count,
            "estimated_cost_usd": self.estimated_cost_usd,
            "last_active": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_active_timestamp)) if self.last_active_timestamp else "Idle",
        }


class TokenTracker:
    """Thread-safe singleton tracking LLM tokens across all multi-cloud inference tasks."""

    _instance: Optional["TokenTracker"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "TokenTracker":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_tracker()
            return cls._instance

    def _init_tracker(self) -> None:
        self.stats: Dict[str, LLMTokenStats] = {
            "groq": LLMTokenStats("groq"),
            "gemini": LLMTokenStats("gemini"),
            "deepseek": LLMTokenStats("deepseek"),
            "nvidia": LLMTokenStats("nvidia"),
            "openrouter": LLMTokenStats("openrouter"),
            "cohere": LLMTokenStats("cohere"),
            "vllm": LLMTokenStats("vllm"),
        }
        self.persist_path = Path(__file__).resolve().parent.parent.parent.parent / "logs" / "token_usage.json"
        self._load_from_disk()

    def record_inference(
        self,
        provider: str,
        prompt_text: str = "",
        completion_text: str = "",
        model: Optional[str] = None,
        exact_prompt_tokens: Optional[int] = None,
        exact_completion_tokens: Optional[int] = None,
    ) -> None:
        """Record tokens from an inference call (using exact metrics or heuristic estimation)."""
        prov_key = provider.lower().strip()
        with self._lock:
            if prov_key not in self.stats:
                self.stats[prov_key] = LLMTokenStats(prov_key)

            p_toks = exact_prompt_tokens if exact_prompt_tokens is not None else max(1, int(len(prompt_text.split()) * 1.33))
            c_toks = exact_completion_tokens if exact_completion_tokens is not None else max(1, int(len(completion_text.split()) * 1.33))

            self.stats[prov_key].record_usage(p_toks, c_toks, model)
            self._save_to_disk_async()

    def get_provider_stats(self, provider: str) -> Dict[str, Any]:
        with self._lock:
            prov_key = provider.lower().strip()
            if prov_key in self.stats:
                return self.stats[prov_key].to_dict()
            return LLMTokenStats(prov_key).to_dict()

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {p: stat.to_dict() for p, stat in self.stats.items()}

    def get_aggregate_totals(self) -> Dict[str, Any]:
        with self._lock:
            total_tokens = sum(s.total_tokens for s in self.stats.values())
            total_requests = sum(s.requests_count for s in self.stats.values())
            total_cost = sum(s.estimated_cost_usd for s in self.stats.values())
            return {
                "total_tokens": total_tokens,
                "total_requests": total_requests,
                "total_cost_usd": round(total_cost, 4),
            }

    def reset_counters(self) -> None:
        with self._lock:
            for s in self.stats.values():
                s.prompt_tokens = 0
                s.completion_tokens = 0
                s.total_tokens = 0
                s.requests_count = 0
                s.last_active_timestamp = None
            self._save_to_disk()

    def _save_to_disk(self) -> None:
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {p: s.to_dict() for p, s in self.stats.items()}
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not persist token stats: {e}")

    def _save_to_disk_async(self) -> None:
        # Run non-blocking save
        t = threading.Thread(target=self._save_to_disk, daemon=True)
        t.start()

    def _load_from_disk(self) -> None:
        if not self.persist_path.exists():
            return
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for p, d in data.items():
                if p not in self.stats:
                    self.stats[p] = LLMTokenStats(p)
                self.stats[p].prompt_tokens = d.get("prompt_tokens", 0)
                self.stats[p].completion_tokens = d.get("completion_tokens", 0)
                self.stats[p].total_tokens = d.get("total_tokens", 0)
                self.stats[p].requests_count = d.get("requests_count", 0)
                self.stats[p].active_model = d.get("active_model", "default")
        except Exception as e:
            logger.debug(f"Could not load persisted token stats: {e}")


def get_token_tracker() -> TokenTracker:
    return TokenTracker()
