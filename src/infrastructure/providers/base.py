"""
RAISE Infrastructure — Multi-Backend Provider Base Interfaces & Health Contracts
Defines standard contracts for LLMs, Embedding engines, and Rerankers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple


@dataclass
class ProviderHealth:
    """Standardized health state contract according to Section 8 of runtime specification."""
    provider: str
    configured: bool
    credential_valid: bool
    endpoint_reachable: bool
    model_available: bool
    functional_test: bool
    status: str  # READY, NOT_CONFIGURED, INVALID_CONFIGURATION, AUTH_FAILED, ENDPOINT_UNREACHABLE, MODEL_UNAVAILABLE, RATE_LIMITED, QUOTA_EXHAUSTED, BILLING_RESTRICTED, UNKNOWN
    latency_ms: float = 0.0
    error_message: Optional[str] = None
    cost_mode: str = "CLOUD / USER ACCOUNT"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LLMProvider:
    """Base abstract provider interface for all local and cloud generative models."""

    name: str = "base"
    cost_mode: str = "CLOUD / USER ACCOUNT"

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        """Execute synchronous completion."""
        raise NotImplementedError

    async def complete_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Execute streaming completion yielding chunks."""
        raise NotImplementedError
        yield ""

    def health_check(self, timeout: float = 5.0) -> ProviderHealth:
        """Perform non-destructive configuration, connectivity, and auth check."""
        raise NotImplementedError


class EmbeddingProvider:
    """Base abstract interface for embedding providers."""

    name: str = "base_embedding"
    dimension: int = 1024
    cost_mode: str = "LOCAL / NO EXTERNAL API BILLING"

    def embed(self, text: str) -> List[float]:
        """Embed single text string into vector."""
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed batch of texts into vector list."""
        raise NotImplementedError


class RerankerProvider:
    """Base abstract interface for cross-encoder and neural rerankers."""

    name: str = "base_reranker"
    cost_mode: str = "LOCAL / NO EXTERNAL API BILLING"

    def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[Tuple[int, float]]:
        """
        Rerank candidate documents against query.
        Returns list of tuples: (original_index, relevance_score).
        """
        raise NotImplementedError
