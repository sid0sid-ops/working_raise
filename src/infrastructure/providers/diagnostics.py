"""
RAISE Infrastructure — Provider Diagnostics Engine
Performs safe, micro-token connectivity, authentication, and latency diagnostics
across all registered local and cloud providers without leaking credentials.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from src.infrastructure.providers.base import ProviderHealth
from src.infrastructure.providers.llm import LocalVLLMProvider
from src.infrastructure.providers.gemini import GeminiProvider
from src.infrastructure.providers.groq import GroqProvider
from src.infrastructure.providers.deepseek import DeepSeekProvider
from src.infrastructure.providers.nvidia import NvidiaNIMProvider
from src.infrastructure.providers.cohere import CohereProvider
from src.infrastructure.providers.openrouter import OpenRouterProvider

logger = logging.getLogger("raise.infrastructure.providers.diagnostics")


class ProviderDiagnostics:
    """Exhaustive diagnostic runner for inference providers."""

    def __init__(self):
        self.providers = {
            "Local vLLM": LocalVLLMProvider(),
            "Google Gemini": GeminiProvider(),
            "Groq": GroqProvider(),
            "DeepSeek": DeepSeekProvider(),
            "NVIDIA NIM": NvidiaNIMProvider(),
            "Cohere": CohereProvider(),
            "OpenRouter": OpenRouterProvider(),
        }

    def run_all(self, timeout: float = 4.0) -> Dict[str, ProviderHealth]:
        """Run diagnostic health check across all registered providers."""
        results = {}
        for name, prov in self.providers.items():
            try:
                health = prov.health_check(timeout=timeout)
                results[name] = health
            except Exception as e:
                logger.error(f"Diagnostic error testing {name}: {e}")
                results[name] = ProviderHealth(
                    provider=prov.name,
                    configured=False,
                    credential_valid=False,
                    endpoint_reachable=False,
                    model_available=False,
                    functional_test=False,
                    status="UNKNOWN",
                    error_message=str(e),
                    cost_mode=prov.cost_mode,
                )
        return results

    def format_table(self, results: Dict[str, ProviderHealth]) -> str:
        """
        Format diagnostic results into a clean, masked CLI table according to Section 26.
        """
        lines = []
        header = f"{'Provider':<16} {'Config':<8} {'Auth':<8} {'Model':<8} {'Test':<8} {'Latency':<10} {'Cost Mode':<28} {'Status':<18}"
        sep = "-" * len(header)
        lines.append(sep)
        lines.append(header)
        lines.append(sep)

        for name, h in results.items():
            cfg_str = "YES" if h.configured else "NO"
            auth_str = "YES" if h.credential_valid else ("--" if not h.configured else "FAIL")
            model_str = "YES" if h.model_available else "--"
            test_str = "PASS" if h.functional_test else "--"
            lat_str = f"{h.latency_ms} ms" if h.latency_ms > 0 else "--"
            cost_str = h.cost_mode
            status_str = h.status

            line = f"{name:<16} {cfg_str:<8} {auth_str:<8} {model_str:<8} {test_str:<8} {lat_str:<10} {cost_str:<28} {status_str:<18}"
            lines.append(line)

        lines.append(sep)
        return "\n".join(lines)


def run_provider_diagnostics(timeout: float = 4.0) -> str:
    """Run diagnostics and return formatted table string."""
    diag = ProviderDiagnostics()
    res = diag.run_all(timeout=timeout)
    return diag.format_table(res)
