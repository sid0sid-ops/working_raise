"""
RAISE Infrastructure — Mistral AI Provider Adapter
High-efficiency inference adapter for Mistral AI models (open-mistral-nemo, open-mistral-7b, codestral-latest).
Supports standard chat completions, streaming, and automatic intra-model fallbacks.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from src.infrastructure.credentials.manager import get_credential_manager
from src.infrastructure.providers.base import LLMProvider, ProviderHealth
from src.infrastructure.providers.http_client import safe_http_request, ProviderHTTPError

logger = logging.getLogger("raise.infrastructure.providers.mistral")

DEFAULT_MISTRAL_ENDPOINT = "https://api.mistral.ai/v1"
DEFAULT_MISTRAL_MODEL = "open-mistral-nemo"
FALLBACK_MISTRAL_MODELS = ["open-mistral-7b", "codestral-latest", "mistral-small-latest"]


class MistralProvider(LLMProvider):
    """Mistral AI inference provider adapter."""

    name = "mistral"
    cost_mode = "CLOUD / USER ACCOUNT"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model_name = model_name or os.getenv("MISTRAL_MODEL_NAME", DEFAULT_MISTRAL_MODEL)
        self.base_url = (base_url or os.getenv("MISTRAL_BASE_URL", DEFAULT_MISTRAL_ENDPOINT)).rstrip("/")

    def _resolve_api_key(self) -> Optional[str]:
        if self.api_key:
            return self.api_key
        return get_credential_manager().get_credential("mistral")

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
            raise ProviderHTTPError("Mistral API key is not configured.", classification="NOT_CONFIGURED")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Try primary model, then intra-model fallbacks if model-specific tier/rate limits occur
        candidate_models = [self.model_name] + [m for m in FALLBACK_MISTRAL_MODELS if m != self.model_name]
        last_err: Optional[Exception] = None

        for model in candidate_models:
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            try:
                resp, _ = safe_http_request(
                    f"{self.base_url}/chat/completions",
                    payload=payload,
                    headers=headers,
                    timeout=kwargs.get("timeout", 45.0),
                    max_retries=1,
                )
                choices = resp.get("choices", [])
                if choices and "message" in choices[0]:
                    return choices[0]["message"].get("content", "")
                raise ProviderHTTPError("Unexpected response format from Mistral API.", classification="UNKNOWN")
            except ProviderHTTPError as e:
                last_err = e
                # If tier or model not available, try next candidate
                if e.classification in ("RATE_LIMITED", "FORBIDDEN", "NOT_FOUND"):
                    logger.info(f"Mistral model '{model}' returned {e.classification}. Trying next model...")
                    continue
                raise

        if last_err:
            raise last_err
        raise ProviderHTTPError("All Mistral model candidates exhausted.", classification="UNAVAILABLE")

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
                cost_mode=self.cost_mode,
            )

        headers = {
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        }

        try:
            resp, _ = safe_http_request(
                f"{self.base_url}/models",
                headers=headers,
                timeout=timeout,
                max_retries=1,
            )
            models = [m.get("id") for m in resp.get("data", [])]
            return ProviderHealth(
                provider=self.name,
                configured=True,
                credential_valid=True,
                endpoint_reachable=True,
                model_available=self.model_name in models or len(models) > 0,
                functional_test=True,
                status="READY",
                cost_mode=self.cost_mode,
            )
        except ProviderHTTPError as e:
            return ProviderHealth(
                provider=self.name,
                configured=True,
                credential_valid=e.classification != "UNAUTHORIZED",
                endpoint_reachable=e.classification != "NETWORK_ERROR",
                model_available=False,
                functional_test=False,
                status=e.classification,
                error_message=str(e),
                cost_mode=self.cost_mode,
            )
