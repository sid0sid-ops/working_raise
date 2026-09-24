"""
RAISE Features Layer — Canonical Domain Capabilities
"""
from .documents import DocumentService
from .ingestion import AcademicPipelineIngestor
from .chunking import AdaptiveChunkingPipeline
from .verification import ClaimVerifier, DeterministicMathEngine
from .comparison import ComparisonService
from .sessions import SessionService, SessionMemoryManager, ReasoningMemory
from .query import QueryService
from .chat import ChatService
from .system import DeveloperOperator

__all__ = [
    "DocumentService",
    "AcademicPipelineIngestor",
    "AdaptiveChunkingPipeline",
    "ClaimVerifier",
    "DeterministicMathEngine",
    "ComparisonService",
    "SessionService",
    "SessionMemoryManager",
    "ReasoningMemory",
    "QueryService",
    "ChatService",
    "DeveloperOperator",
]
