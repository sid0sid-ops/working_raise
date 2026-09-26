"""
FRAMES Benchmark Runners & Reporting Submodule
"""

from .reporter import FramesReporter

def __getattr__(name):
    if name == "FramesBenchmarkRunner":
        from .runner import FramesBenchmarkRunner
        return FramesBenchmarkRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["FramesReporter", "FramesBenchmarkRunner"]
