"""
RAISE Infrastructure — DeepSeek Provider Adapter
Supports DeepSeek API (deepseek-chat, deepseek-reasoner) with reasoning token preservation.
"""

from __future__ import annotations

import os
import logging
from typing import Any, AsyncGenerator, Dict, Optional

from src.infrastructure.credentials.manager import get_credential_manager
from src.infrastructure.providers.base import LLMProvider, ProviderHealth
from src.infrastructure.providers.http_client import safe_http_request, ProviderHTTPError

logger = logging.getLogger("raise.infrastructure.providers.deepseek")

DEFAULT_DEEPSEEK_ENDPOINT = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"


class DeepSeekProvider(LLMProvider):
    """DeepSeek LLM provider adapter supporting chat and reasoning models."""

    name = "deepseek"
    cost_mode = "CLOUD / USER ACCOUNT"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model_name = model_name or os.getenv("DEEPSEEK_MODEL_NAME", DEFAULT_DEEPSEEK_MODEL)
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_ENDPOINT)).rstrip("/")

    def _resolve_api_key(self) -> Optional[str]:
        if self.api_key:
            return self.api_key
        return get_credential_manager().get_credential("deepseek")

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
            raise ProviderHTTPError("DeepSeek API key is not configured.", classification="NOT_CONFIGURED")

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
        headers = {"Authorization": f"Bearer {key}"}

        resp, _ = safe_http_request(
            f"{self.base_url}/chat/completions",
            payload=payload,
            headers=headers,
            timeout=kwargs.get("timeout", 60.0),
        )
        choice = resp["choices"][0]["message"]
        content = choice.get("content", "")
        # Optionally preserve reasoning content from deepseek-reasoner
        reasoning = choice.get("reasoning_content")
        if reasoning and kwargs.get("include_reasoning", False):
            return f"<think>\n{reasoning}\n</think>\n{content}"
        return content

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
        """Perform non-destructive configuration, connectivity, and minimal functional test."""
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
            "model": self.model_name,
            "messages": [{"role": "user", "content": "Return exactly: PROVIDER_TEST_OK"}],
            "max_tokens": 5,
            "temperature": 0.0,
        }
        headers = {"Authorization": f"Bearer {key}"}

        try:
            resp, latency_ms = safe_http_request(
                f"{self.base_url}/chat/completions",
                payload=payload,
                headers=headers,
                timeout=timeout,
                max_retries=0,
            )
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
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
