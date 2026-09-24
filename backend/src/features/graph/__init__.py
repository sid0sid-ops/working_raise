"""RAISE Graph Feature Package."""
from .engine import GraphRAGEngine, slugify

# Aliases for backwards compatibility
InvertedIndexEngine = GraphRAGEngine
SubgraphEngine = GraphRAGEngine
AcademicGraphEngine = GraphRAGEngine

__all__ = ["GraphRAGEngine", "slugify", "InvertedIndexEngine", "SubgraphEngine", "AcademicGraphEngine"]
