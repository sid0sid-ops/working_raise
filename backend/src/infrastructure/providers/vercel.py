"""
RAISE Infrastructure — Vercel AI Gateway & TypeSafe Jev Provider Adapter
Adapter for Vercel AI Gateway (https://ai-gateway.vercel.sh/v1) and TypeSafe Jev decision models.
Enables routing across Claude, GPT-4o, Llama, and specialized System-1 evaluation models.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from src.infrastructure.credentials.manager import get_credential_manager
from src.infrastructure.providers.base import LLMProvider, ProviderHealth
from src.infrastructure.providers.http_client import safe_http_request, ProviderHTTPError

logger = logging.getLogger("raise.infrastructure.providers.vercel")

DEFAULT_VERCEL_ENDPOINT = "https://ai-gateway.vercel.sh/v1"
DEFAULT_VERCEL_MODEL = "typesafe-ai/jev"


class VercelAIGatewayProvider(LLMProvider):
    """Vercel AI Gateway and TypeSafe decision model provider adapter."""

    name = "vercel"
    cost_mode = "CLOUD / VERCEL GATEWAY"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model_name = model_name or os.getenv("VERCEL_AI_MODEL", os.getenv("TYPESAFE_MODEL", DEFAULT_VERCEL_MODEL))
        self.base_url = (base_url or os.getenv("VERCEL_AI_BASE_URL", DEFAULT_VERCEL_ENDPOINT)).rstrip("/")

    def _resolve_api_key(self) -> Optional[str]:
        if self.api_key:
            return self.api_key
        cm = get_credential_manager()
        return cm.get_credential("vercel") or cm.get_credential("typesafe")

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
            raise ProviderHTTPError("Vercel AI Gateway / TypeSafe API key is not configured.", classification="NOT_CONFIGURED")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

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
        raise ProviderHTTPError("Unexpected response format from Vercel AI Gateway.", classification="UNKNOWN")

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

        # Probe minimal chat completion or models endpoint
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
            return ProviderHealth(
                provider=self.name,
                configured=True,
                credential_valid=True,
                endpoint_reachable=True,
                model_available=True,
                functional_test=True,
                status="READY",
                cost_mode=self.cost_mode,
            )
        except ProviderHTTPError as e:
            return ProviderHealth(
                provider=self.name,
                configured=True,
                credential_valid=e.classification != "AUTH_FAILED",
                endpoint_reachable=e.classification != "ENDPOINT_UNREACHABLE",
                model_available=False,
                functional_test=False,
                status=e.classification,
                error_message=str(e),
                cost_mode=self.cost_mode,
            )
