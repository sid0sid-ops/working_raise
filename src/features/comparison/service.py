"""
RAISE University & Academic Report Comparison Feature
Provides side-by-side metric normalization, ranking, and fact comparison.
"""
from typing import Any, Dict, List, Optional
from src.core.types import AnswerContract
from src.infrastructure.graph.neo4j import Neo4jDatabase
from src.infrastructure.vector.chroma import LocalVectorEngine


class ComparisonService:
    """Compares academic reports, universities, and performance metrics."""

    def __init__(self, neo4j: Optional[Neo4jDatabase] = None, vector: Optional[LocalVectorEngine] = None):
        self.neo4j = neo4j or Neo4jDatabase()
        self.vector = vector or LocalVectorEngine()

    def compare_institutions(self, institutions: List[str], metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """Extracts comparative metrics across specified academic institutions."""
        results = {}
        for inst in institutions:
            query = (
                "MATCH (u:University)-[:REPORTED_METRIC]->(m:MetricFact) "
                "WHERE toLower(u.name) CONTAINS toLower($inst) "
                "RETURN m.metric_name AS metric, m.raw_value AS value, m.academic_year AS year LIMIT 25"
            )
            rows = self.neo4j.run_cypher(query, {"inst": inst})
            results[inst] = rows
        return {
            "status": "success",
            "institutions": institutions,
            "metrics": results,
        }
