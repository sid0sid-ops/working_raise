"""
RAISE Infrastructure — Cohere Provider Adapter
Provides multi-modal LLM generation, vector embeddings, and neural reranking via Cohere API.
"""

from __future__ import annotations

import os
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from src.infrastructure.credentials.manager import get_credential_manager
from src.infrastructure.providers.base import (
    LLMProvider,
    EmbeddingProvider,
    RerankerProvider,
    ProviderHealth,
)
from src.infrastructure.providers.http_client import safe_http_request, ProviderHTTPError

logger = logging.getLogger("raise.infrastructure.providers.cohere")

DEFAULT_COHERE_ENDPOINT = "https://api.cohere.com"
DEFAULT_COHERE_CHAT_MODEL = "command-r-plus-08-2024"
DEFAULT_COHERE_EMBED_MODEL = "embed-english-v3.0"
DEFAULT_COHERE_RERANK_MODEL = "rerank-english-v3.0"


class CohereProvider(LLMProvider, EmbeddingProvider, RerankerProvider):
    """Unified Cohere provider for chat, embeddings, and reranking."""

    name = "cohere"
    cost_mode = "CLOUD / USER ACCOUNT"
    dimension = 1024

    def __init__(
        self,
        api_key: Optional[str] = None,
        chat_model: Optional[str] = None,
        embed_model: Optional[str] = None,
        rerank_model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.chat_model = chat_model or os.getenv("COHERE_CHAT_MODEL", DEFAULT_COHERE_CHAT_MODEL)
        self.model_name = self.chat_model
        self.embed_model = embed_model or os.getenv("COHERE_EMBED_MODEL", DEFAULT_COHERE_EMBED_MODEL)
        self.rerank_model = rerank_model or os.getenv("COHERE_RERANK_MODEL", DEFAULT_COHERE_RERANK_MODEL)
        self.base_url = (base_url or os.getenv("COHERE_BASE_URL", DEFAULT_COHERE_ENDPOINT)).rstrip("/")

    def _resolve_api_key(self) -> Optional[str]:
        if self.api_key:
            return self.api_key
        return get_credential_manager().get_credential("cohere")

    # 1. LLM Generation
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        key = self._resolve_api_key()
        if not key:
            raise ProviderHTTPError("Cohere API key is not configured.", classification="NOT_CONFIGURED")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Cohere v2 chat payload
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {key}"}

        resp, _ = safe_http_request(
            f"{self.base_url}/v2/chat",
            payload=payload,
            headers=headers,
            timeout=kwargs.get("timeout", 60.0),
        )
        content_items = resp.get("message", {}).get("content", [])
        if content_items and isinstance(content_items, list):
            return content_items[0].get("text", "")
        return ""

    async def complete_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        text = self.complete(prompt, system_prompt, max_tokens, temperature, **kwargs)
        yield text

    # 2. Embedding Generation
    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        key = self._resolve_api_key()
        if not key:
            raise ProviderHTTPError("Cohere API key is not configured.", classification="NOT_CONFIGURED")

        payload = {
            "model": self.embed_model,
            "texts": texts,
            "input_type": "search_document",
            "embedding_types": ["float"],
        }
        headers = {"Authorization": f"Bearer {key}"}

        resp, _ = safe_http_request(
            f"{self.base_url}/v1/embed",
            payload=payload,
            headers=headers,
            timeout=30.0,
        )
        embeddings = resp.get("embeddings", {}).get("float", [])
        return embeddings

    # 3. Neural Reranking
    def rerank(self, query: str, documents: List[str], top_n: int = 5) -> List[Tuple[int, float]]:
        key = self._resolve_api_key()
        if not key:
            raise ProviderHTTPError("Cohere API key is not configured.", classification="NOT_CONFIGURED")

        payload = {
            "model": self.rerank_model,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents)),
        }
        headers = {"Authorization": f"Bearer {key}"}

        resp, _ = safe_http_request(
            f"{self.base_url}/v1/rerank",
            payload=payload,
            headers=headers,
            timeout=30.0,
        )
        results = resp.get("results", [])
        return [(r["index"], float(r["relevance_score"])) for r in results]

    # 4. Diagnostic Health Check
    def health_check(self, timeout: float = 5.0) -> ProviderHealth:
        key = self._resolve_api_key()
        if not key:
            return ProviderHealth(
                provider=self.name,
                configured=False,
                credential_valid=False,
                endpoint_reachable=False,
                model_available=False,
                functional_test=False,
                status="NOT_CONFIGURED",
                error_message="API key missing from environment and Windows Credential Locker",
                cost_mode=self.cost_mode,
            )

        payload = {
            "model": self.chat_model,
            "messages": [{"role": "user", "content": "Return exactly: PROVIDER_TEST_OK"}],
            "max_tokens": 5,
            "temperature": 0.0,
        }
        headers = {"Authorization": f"Bearer {key}"}

        try:
            resp, latency_ms = safe_http_request(
                f"{self.base_url}/v2/chat",
                payload=payload,
                headers=headers,
                timeout=timeout,
                max_retries=0,
            )
            content_items = resp.get("message", {}).get("content", [])
            content = content_items[0].get("text", "") if content_items else ""
            return ProviderHealth(
                provider=self.name,
                configured=True,
                credential_valid=True,
                endpoint_reachable=True,
                model_available=True,
                functional_test="PROVIDER_TEST_OK" in content or len(content) > 0,
                status="READY",
                latency_ms=round(latency_ms, 1),
                cost_mode=self.cost_mode,
            )
        except ProviderHTTPError as e:
            return ProviderHealth(
                provider=self.name,
                configured=True,
                credential_valid=(e.classification != "AUTH_FAILED"),
                endpoint_reachable=(e.classification != "ENDPOINT_UNREACHABLE"),
                model_available=(e.classification != "MODEL_UNAVAILABLE"),
                functional_test=False,
                status=e.classification,
                error_message=str(e),
                cost_mode=self.cost_mode,
            )
        except Exception as e:
            return ProviderHealth(
                provider=self.name,
                configured=True,
                credential_valid=False,
                endpoint_reachable=False,
                model_available=False,
                functional_test=False,
                status="UNKNOWN",
                error_message=f"Error: {type(e).__name__}",
                cost_mode=self.cost_mode,
            )
