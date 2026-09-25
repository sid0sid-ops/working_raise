"""
RAISE Infrastructure — Unified Multi-Provider LLM Interface
Supports local inference engines (vLLM, Ollama) and cloud-compatible APIs (Gemini, Groq, DeepSeek, NVIDIA NIM, Cohere).
"""

from __future__ import annotations

import os
import json
import logging
import time
import urllib.request
import urllib.error
from typing import Any, AsyncGenerator, Dict, List, Optional

from src.core.config import settings, LLMConfig
from src.infrastructure.providers.base import LLMProvider, ProviderHealth
from src.infrastructure.providers.http_client import safe_http_request, ProviderHTTPError

logger = logging.getLogger("raise.infrastructure.providers.llm")


class BaseLLMProvider(LLMProvider):
    """Abstract baseline for local and cloud LLM inference providers."""

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError

    async def complete_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError
        yield ""

    def health_check(self, timeout: float = 5.0) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            configured=True,
            credential_valid=True,
            endpoint_reachable=False,
            model_available=False,
            functional_test=False,
            status="UNKNOWN",
            cost_mode=self.cost_mode,
        )


class LocalVLLMProvider(BaseLLMProvider):
    """Local high-throughput vLLM engine running on GPU."""

    name = "vllm"
    cost_mode = "LOCAL / NO EXTERNAL API BILLING"

    def __init__(self, base_url: Optional[str] = None, model_name: Optional[str] = None):
        self.base_url = (base_url or os.getenv("VLLM_BASE_URL", "http://localhost:8002/v1")).rstrip("/")
        self.model_name = model_name or os.getenv("VLLM_MODEL_NAME", "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4")

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
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

        try:
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "RAISE-Provider"},
            )
            with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 60.0)) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"Local vLLM completion failed: {e}")
            raise RuntimeError(f"Error executing inference: {e}")

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
        """Ping local vLLM endpoint and perform micro inference."""
        t_start = time.perf_counter()
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": "Ping"}],
            "max_tokens": 5,
            "temperature": 0.0,
        }
        try:
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                return ProviderHealth(
                    provider=self.name,
                    configured=True,
                    credential_valid=True,
                    endpoint_reachable=True,
                    model_available=True,
                    functional_test=True,
                    status="READY",
                    latency_ms=round(elapsed_ms, 1),
                    cost_mode=self.cost_mode,
                )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return ProviderHealth(
                provider=self.name,
                configured=True,
                credential_valid=True,
                endpoint_reachable=False,
                model_available=False,
                functional_test=False,
                status="ENDPOINT_UNREACHABLE",
                latency_ms=round(elapsed_ms, 1),
                error_message=f"Local vLLM offline: {type(e).__name__}",
                cost_mode=self.cost_mode,
            )


class CloudOpenAICompatibleProvider(BaseLLMProvider):
    """
    Cloud-compatible LLM provider for OpenAI or generic OpenAI-compatible gateways.
    """

    name = "openai-compatible"
    cost_mode = "CLOUD / USER ACCOUNT"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
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

        try:
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "RAISE-CloudProvider",
                },
            )
            with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 60.0)) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Cloud LLM completion failed: {e}")
            raise RuntimeError(f"Cloud LLM error: {e}")

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


class LocalOllamaProvider(BaseLLMProvider):
    """Local Ollama instance on port 11434."""

    name = "ollama"
    cost_mode = "LOCAL / NO EXTERNAL API BILLING"

    def __init__(self, base_url: Optional[str] = None, model_name: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 60.0)) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")
        except Exception as e:
            logger.warning(f"Ollama completion failed: {e}")
            raise RuntimeError(f"Ollama error: {e}")

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


def get_llm_provider(config: Optional[LLMConfig] = None, provider_name: Optional[str] = None) -> LLMProvider:
    """
    Factory creating configured LLM provider according to environment settings or explicit name.
    Preserves existing signature and semantics while supporting all new providers.
    """
    cfg = config or settings.llm
    backend = (provider_name or cfg.backend).lower().strip()

    if backend in ("cloud", "openai", "openai-compatible"):
        return CloudOpenAICompatibleProvider(
            api_key=cfg.api_key,
            base_url=cfg.base_url,
            model_name=cfg.model_name,
        )
    elif backend == "gemini":
        from src.infrastructure.providers.gemini import GeminiProvider
        return GeminiProvider()
    elif backend == "groq":
        from src.infrastructure.providers.groq import GroqProvider
        return GroqProvider()
    elif backend == "deepseek":
        from src.infrastructure.providers.deepseek import DeepSeekProvider
        return DeepSeekProvider()
    elif backend in ("nvidia", "nvidia-nim", "nim"):
        from src.infrastructure.providers.nvidia import NvidiaNIMProvider
        return NvidiaNIMProvider()
    elif backend == "cohere":
        from src.infrastructure.providers.cohere import CohereProvider
        return CohereProvider()
    elif backend == "mistral":
        from src.infrastructure.providers.mistral import MistralProvider
        return MistralProvider()
    elif backend in ("vercel", "typesafe", "jev"):
        from src.infrastructure.providers.vercel import VercelAIGatewayProvider
        return VercelAIGatewayProvider()
    elif backend == "openrouter":
        from src.infrastructure.providers.openrouter import OpenRouterProvider
        return OpenRouterProvider()
    elif backend in ("universal", "custom", "together", "fireworks", "perplexity"):
        from src.infrastructure.providers.universal import UniversalCloudProvider
        return UniversalCloudProvider(custom_name=backend)
    elif backend == "ollama":
        return LocalOllamaProvider(base_url=cfg.base_url, model_name=cfg.model_name)
    else:
        # Default local vLLM
        return LocalVLLMProvider(base_url=cfg.base_url, model_name=cfg.model_name)
