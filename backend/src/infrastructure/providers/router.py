"""
RAISE Infrastructure — Unified Provider Router & Task Policies
Manages task-to-provider mappings, bounded exponential backoff retries,
non-secret fallback logging, and execution modes (LOCAL, CLOUD, AUTOMATIC).
"""

from __future__ import annotations

import os
import logging
import time
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

from src.core.config import settings
from src.infrastructure.providers.base import (
    LLMProvider,
    EmbeddingProvider,
    RerankerProvider,
    ProviderHealth,
)
from src.infrastructure.providers.llm import LocalVLLMProvider, get_llm_provider
from src.infrastructure.providers.gemini import GeminiProvider
from src.infrastructure.providers.groq import GroqProvider
from src.infrastructure.providers.deepseek import DeepSeekProvider
from src.infrastructure.providers.nvidia import NvidiaNIMProvider
from src.infrastructure.providers.cohere import CohereProvider
from src.infrastructure.providers.openrouter import OpenRouterProvider
from src.infrastructure.providers.token_tracker import get_token_tracker
from src.infrastructure.providers.http_client import ProviderHTTPError

logger = logging.getLogger("raise.infrastructure.providers.router")


class InferenceTask(str, Enum):
    """Standardized task categories supported by the router."""
    CHAT = "CHAT"
    RAG_GENERATION = "RAG_GENERATION"
    DOCUMENT_EXTRACTION = "DOCUMENT_EXTRACTION"
    SUMMARIZATION = "SUMMARIZATION"
    STRUCTURED_EXTRACTION = "STRUCTURED_EXTRACTION"
    REASONING = "REASONING"
    CODE = "CODE"
    QUERY_REWRITE = "QUERY_REWRITE"
    EMBEDDING = "EMBEDDING"
    RERANKING = "RERANKING"


class ExecutionMode(str, Enum):
    """Execution target modes."""
    LOCAL = "LOCAL"
    CLOUD = "CLOUD"
    AUTOMATIC = "AUTOMATIC"


class FallbackEvent:
    """Non-secret record of an automated failover event."""
    def __init__(self, from_provider: str, to_provider: str, task: str, reason: str):
        self.timestamp = time.time()
        self.from_provider = from_provider
        self.to_provider = to_provider
        self.task = task
        self.reason = reason

    def __str__(self) -> str:
        return f"Provider {self.from_provider} unavailable -> switched to {self.to_provider} for {self.task}. Reason: {self.reason}"


class ProviderRouter:
    """
    Central router dispatching inference requests across local vLLM and cloud providers.
    """

    def __init__(
        self,
        mode: Optional[ExecutionMode] = None,
        cloud_allowed: Optional[bool] = None,
    ):
        env_backend = os.getenv("LLM_BACKEND", "").lower().strip()
        env_mode = os.getenv("EXECUTION_MODE", "").upper().strip()

        if mode is not None:
            self.mode = mode
        elif env_mode in ("CLOUD", "LOCAL", "AUTOMATIC"):
            self.mode = ExecutionMode(env_mode)
        elif env_backend in ("groq", "gemini", "deepseek", "nvidia", "cohere", "openrouter"):
            self.mode = ExecutionMode.CLOUD
        else:
            self.mode = ExecutionMode.AUTOMATIC

        self.cloud_allowed = cloud_allowed if cloud_allowed is not None else (self.mode != ExecutionMode.LOCAL)
        self.fallback_history: List[FallbackEvent] = []

        # Instantiate provider registry
        self.providers: Dict[str, LLMProvider] = {
            "vllm": LocalVLLMProvider(),
            "gemini": GeminiProvider(),
            "groq": GroqProvider(),
            "deepseek": DeepSeekProvider(),
            "nvidia": NvidiaNIMProvider(),
            "cohere": CohereProvider(),
            "openrouter": OpenRouterProvider(),
        }

        # Active primary provider selection
        primary_cloud = env_backend if env_backend in self.providers else "groq"

        # Task routing policy mapping (Production Defaults for 8 Pipeline Phases)
        self.task_policy: Dict[InferenceTask, str] = {
            InferenceTask.CHAT: "groq" if self.cloud_allowed else "vllm",  # Phase 1: Low-latency chat
            InferenceTask.RAG_GENERATION: primary_cloud if self.mode == ExecutionMode.CLOUD else "vllm",  # Phase 2: RAG Answer Synthesis
            InferenceTask.DOCUMENT_EXTRACTION: "gemini",  # Phase 3: Doc Layout & Vision
            InferenceTask.QUERY_REWRITE: "groq",  # Phase 4: Query Intake & Reformulation
            InferenceTask.REASONING: "deepseek",  # Phase 5: Multi-Hop Relational Reasoning
            InferenceTask.CODE: "deepseek",  # Phase 6: Code & Formal Cypher
            InferenceTask.SUMMARIZATION: "openrouter",  # Phase 7: Community / Executive Summaries
            InferenceTask.RERANKING: "cohere",  # Phase 8: Neural Cross-Attention Reranking
            InferenceTask.STRUCTURED_EXTRACTION: "deepseek",
            InferenceTask.EMBEDDING: "vllm",  # Local BGE-Large
        }

        # Dynamic fallback order
        self.fallback_chain: List[str] = ["vllm", primary_cloud, "groq", "gemini", "nvidia", "openrouter", "cohere", "deepseek"]

    def set_task_provider(self, task: Union[InferenceTask, str], provider_name: str) -> None:
        """Assign specific provider to an inference task."""
        t = InferenceTask(task) if isinstance(task, str) else task
        prov = provider_name.lower().strip()
        if prov in self.providers:
            self.task_policy[t] = prov
            logger.info(f"Router policy updated: {t.value} -> {prov}")
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def set_execution_mode(self, mode: Union[ExecutionMode, str]) -> None:
        """Change global execution target."""
        self.mode = ExecutionMode(mode) if isinstance(mode, str) else mode
        logger.info(f"Router execution mode set to: {self.mode.value}")

    def set_cloud_allowed(self, allowed: bool) -> None:
        """Toggle cloud inference permission safeguard."""
        self.cloud_allowed = allowed
        logger.info(f"Cloud inference permission changed: {allowed}")

    def get_provider_for_task(self, task: Union[InferenceTask, str]) -> LLMProvider:
        """Select primary provider according to execution mode and task policy."""
        t = InferenceTask(task) if isinstance(task, str) else task

        if self.mode == ExecutionMode.LOCAL:
            return self.providers["vllm"]

        target_name = self.task_policy.get(t, "vllm")

        # If Cloud mode or Automatic mode, check billing guardrail
        if target_name != "vllm" and not self.cloud_allowed and self.mode != ExecutionMode.CLOUD:
            logger.info(f"Cloud inference confirmation required for {target_name}. Defaulting to Local vLLM.")
            return self.providers["vllm"]

        return self.providers.get(target_name, self.providers["vllm"])

    def complete(
        self,
        prompt: str,
        task: Union[InferenceTask, str] = InferenceTask.RAG_GENERATION,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        """
        Execute completion with bounded retry and automated non-secret fallback.
        """
        t = InferenceTask(task) if isinstance(task, str) else task
        primary_provider = self.get_provider_for_task(t)

        try:
            result = primary_provider.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )
            # Record token usage per LLM
            get_token_tracker().record_inference(
                provider=primary_provider.name,
                prompt_text=f"{system_prompt or ''}\n{prompt}",
                completion_text=result,
                model=getattr(primary_provider, "model_name", None),
            )
            return result
        except Exception as primary_err:
            err_msg = str(primary_err)
            logger.warning(f"Primary provider '{primary_provider.name}' failed for {t.value}: {err_msg}")

            # Try each provider in the fallback chain
            errors = [f"{primary_provider.name}: {err_msg}"]
            for candidate_name in self.fallback_chain:
                if candidate_name == primary_provider.name:
                    continue
                candidate_prov = self.providers.get(candidate_name)
                if not candidate_prov:
                    continue

                fb_event = FallbackEvent(
                    from_provider=primary_provider.name,
                    to_provider=candidate_name,
                    task=t.value,
                    reason=err_msg,
                )
                self.fallback_history.append(fb_event)
                logger.info(str(fb_event))

                try:
                    return candidate_prov.complete(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        **kwargs,
                    )
                except Exception as fb_err:
                    errors.append(f"{candidate_name}: {fb_err}")
                    logger.warning(f"Fallback candidate '{candidate_name}' failed: {fb_err}")

            return f"Inference execution error: All providers in fallback chain failed: {'; '.join(errors)}"

    async def complete_stream(
        self,
        prompt: str,
        task: Union[InferenceTask, str] = InferenceTask.CHAT,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Execute streaming completion."""
        t = InferenceTask(task) if isinstance(task, str) else task
        primary_provider = self.get_provider_for_task(t)

        try:
            async for chunk in primary_provider.complete_stream(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            ):
                yield chunk
        except Exception as e:
            logger.warning(f"Streaming error on provider '{primary_provider.name}': {e}. Falling back to sync completion.")
            fallback_text = self.complete(prompt, task=t, system_prompt=system_prompt, max_tokens=max_tokens, temperature=temperature, **kwargs)
            yield fallback_text


# Global Singleton Router
_router_instance: Optional[ProviderRouter] = None


def get_provider_router() -> ProviderRouter:
    """Return singleton ProviderRouter instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ProviderRouter()
    return _router_instance
