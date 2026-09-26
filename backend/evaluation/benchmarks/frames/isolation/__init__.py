"""
FRAMES Benchmark Isolation Submodule
Guarantees 100% database isolation and prevents ground-truth answer leakage.
"""

from .harness import IsolatedFramesHarness

__all__ = ["IsolatedFramesHarness"]
