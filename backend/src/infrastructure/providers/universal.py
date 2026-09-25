"""
RAISE Infrastructure — Universal Cloud OpenAI-Compatible Provider Adapter
Enables RAISE to seamlessly connect to ANY cloud LLM provider that implements the OpenAI API specification:
(e.g., Together AI, Fireworks AI, Perplexity, OpenAI, Anthropic via proxy, Anyscale, local LM Studio, etc.)
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from src.infrastructure.credentials.manager import get_credential_manager
from src.infrastructure.providers.base import LLMProvider, ProviderHealth
from src.infrastructure.providers.http_client import safe_http_request, ProviderHTTPError

logger = logging.getLogger("raise.infrastructure.providers.universal")


class UniversalCloudProvider(LLMProvider):
    """Universal OpenAI-compatible inference provider for any cloud LLM."""

    name = "universal"
    cost_mode = "CLOUD / CUSTOM PROVIDER"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        custom_name: Optional[str] = None,
    ):
        if custom_name:
            self.name = custom_name
        self.api_key = api_key
        self.model_name = model_name or os.getenv("CUSTOM_LLM_MODEL", os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"))
        self.base_url = (base_url or os.getenv("CUSTOM_LLM_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))).rstrip("/")

    def _resolve_api_key(self) -> Optional[str]:
        if self.api_key:
            return self.api_key
        cm = get_credential_manager()
        return (
            cm.get_credential("custom")
            or cm.get_credential("openai")
            or cm.get_credential("together")
            or cm.get_credential(self.name)
        )

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
            raise ProviderHTTPError(f"API key is not configured for provider '{self.name}'.", classification="NOT_CONFIGURED")

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
        raise ProviderHTTPError(f"Unexpected response format from {self.name} API.", classification="UNKNOWN")

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
