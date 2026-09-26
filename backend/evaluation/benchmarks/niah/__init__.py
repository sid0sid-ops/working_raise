"""
RAISE Needle-in-a-Haystack (NIAH) Evaluation Framework.
"""

from .needle_catalog import NeedleCase, NeedleType, STANDARD_NEEDLES, get_needle, list_available_needles
from .haystack_generator import HaystackGenerator
from .corpus_builder import CorpusBuilder, AssembledCorpus
from .chunking_simulator import ChunkingSimulator, ChunkedCorpus, SimulatedChunk
from .isolation_harness import NIAHIsolationHarness, IsolatedVectorHarness, IsolatedGraphHarness
from .component_probes import (
    EmbeddingProbe,
    ChromaDBProbe,
    RerankerProbe,
    GraphTraversalProbe,
    LLMGenerationProbe,
)
from .failure_attributor import FailureAttributor, FailureStage, FailureAttribution
from .visualizer import NIAHVisualizer
from .niah_runner import NIAHBenchmarkRunner

__all__ = [
    "NeedleCase",
    "NeedleType",
    "STANDARD_NEEDLES",
    "get_needle",
    "list_available_needles",
    "HaystackGenerator",
    "CorpusBuilder",
    "AssembledCorpus",
    "ChunkingSimulator",
    "ChunkedCorpus",
    "SimulatedChunk",
    "NIAHIsolationHarness",
    "IsolatedVectorHarness",
    "IsolatedGraphHarness",
    "EmbeddingProbe",
    "ChromaDBProbe",
    "RerankerProbe",
    "GraphTraversalProbe",
    "LLMGenerationProbe",
    "FailureAttributor",
    "FailureStage",
    "FailureAttribution",
    "NIAHVisualizer",
    "NIAHBenchmarkRunner",
]
