"""
FRAMES Benchmark Data Submodule
Handles dataset loading, validation, schema normalization, and metadata tracking.
"""

from .schema import FramesQuestion, ReasoningType
from .loader import FramesDatasetLoader

__all__ = ["FramesQuestion", "ReasoningType", "FramesDatasetLoader"]
