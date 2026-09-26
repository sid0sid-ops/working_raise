"""
RAISE Autonomous Agent Router & Multi-Tool Execution Engine
===========================================================
Autonomous multi-tool router managing query intent decomposition, tool dispatch,
document workspace filtering, and grounded answer synthesis.

Modular Architecture Breakdown:
--------------------------------
  - router_models.py: Data classes (`EvidenceSufficiencyReport`, `AgentExecutionPlan`)
  - router_analyzer.py: Query analysis, entity/metric extraction, BM25 lookup (`QueryAnalyzerMixin`)
  - router_executor.py: Multi-tool plan execution, context sandwiching, LLM synthesis (`PlanExecutorMixin`)

All symbols are cleanly re-exported here for 100% backward compatibility across all pipelines,
benchmark suites, and test harnesses.
"""

from __future__ import annotations

from typing import Optional

from .router_models import (
    EvidenceSufficiencyReport,
    AgentExecutionPlan,
)
from .router_analyzer import QueryAnalyzerMixin
from .router_executor import PlanExecutorMixin

from src.features.verification.claim_verifier import ClaimVerifier
from src.features.verification.fact_engine import FactEngine
from src.features.graph.engine import GraphRAGEngine
from src.infrastructure.graph.neo4j import Neo4jDatabase
from src.features.memory.reasoning import ReasoningMemory
from src.retrieval.fusion import CrossEncoderReranker
from src.features.verification.table_engine import TableEngine
from src.infrastructure.vector.chroma import LocalVectorEngine

__all__ = [
    "EvidenceSufficiencyReport",
    "AgentExecutionPlan",
    "AgentRouter",
]


class AgentRouter(QueryAnalyzerMixin, PlanExecutorMixin):
    """
    Autonomous multi-tool router managing query intent decomposition,
    tool dispatch, document filtering, and grounded answer synthesis.
    Assembled modularly from specialized mixins for query analysis and plan execution.
    """

    def __init__(
        self,
        fact_engine: FactEngine,
        vector_engine: LocalVectorEngine,
        graph_engine: GraphRAGEngine,
        neo4j_db: Optional[Neo4jDatabase] = None,
        table_engine: Optional[TableEngine] = None,
        reasoning_memory: Optional[ReasoningMemory] = None,
    ):
        self.fact_engine = fact_engine
        self.vector_engine = vector_engine
        self.graph_engine = graph_engine
        self.neo4j_db = neo4j_db or Neo4jDatabase()
        self.table_engine = table_engine or TableEngine()
        self.reasoning_memory = reasoning_memory or ReasoningMemory()
        self.verifier = ClaimVerifier()
        self.reranker = CrossEncoderReranker()
