"""
RAISE Master Standalone GraphRAG Pipeline
Coordinates multi-substrate ingestion, dense vector search, Neo4j graph synchronization,
multi-hop subgraph traversal, and agentic grounded answering.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .vector_engine import LocalVectorEngine
from .graph_engine import GraphRAGEngine
from .neo4j_engine import Neo4jDatabase
from .fact_engine import FactEngine
from .table_engine import TableEngine
from .reasoning_memory import ReasoningMemory
from .claim_verifier import ClaimVerifier
from .agent_router import AgentRouter
from .academic_extractor import AcademicDomainExtractor
from .langgraph_workflow import AcademicGraphRAGWorkflow

__all__ = ["StandaloneRAGPipeline", "AcademicGraphRAGWorkflow", "query_graph_rag"]


def query_graph_rag(
    query: str,
    hops: int = 2,
    top_k: int = 4,
    temperature: float = 0.1,
    document_filter: str = None,
    verbose: bool = False,
):
    """
    Convenience function to execute the complete GraphRAG multi-substrate query.
    Matches inspiration repository patterns with temperature and verbose telemetry.
    """
    pipeline = StandaloneRAGPipeline()
    result = pipeline.query_subgraph_graphrag(
        query=query,
        hops=hops,
        top_k=top_k,
        document_filter=document_filter
    )
    if verbose:
        print(f" [GraphRAG Telemetry] Query: '{query}' | Grounded Score: {result.get('traceability_score')}")
    return result


class StandaloneRAGPipeline:
    """
    Master pipeline orchestrating all vector, graph, tabular, and agentic operations.
    """

    def __init__(self, persist_dir: Optional[Path | str] = None):
        self.persist_dir = Path(persist_dir or Path(__file__).parent.parent / ".runtime").resolve()
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.vector_engine = LocalVectorEngine()
        self.graph_engine = GraphRAGEngine()
        self.neo4j_db = Neo4jDatabase()
        self.fact_engine = FactEngine()
        self.table_engine = TableEngine()
        self.reasoning_memory = ReasoningMemory()
        self.academic_extractor = AcademicDomainExtractor()

        self.agent_router = AgentRouter(
            fact_engine=self.fact_engine,
            vector_engine=self.vector_engine,
            graph_engine=self.graph_engine,
            neo4j_db=self.neo4j_db,
            table_engine=self.table_engine,
            reasoning_memory=self.reasoning_memory,
        )

        # Load processed artifacts into memory on startup
        self._load_processed_data()

        # Initialize LangGraph cyclical StateGraph Workflow
        self.langgraph_workflow = AcademicGraphRAGWorkflow(self)

    def _load_processed_data(self):
        """Auto-load all processed academic chunks and triples into memory."""
        processed_chunks_dir = Path(__file__).parent.parent / "data" / "processed" / "chunks"
        processed_triples_dir = Path(__file__).parent.parent / "data" / "processed" / "graph_triples"

        if processed_chunks_dir.exists():
            for f in processed_chunks_dir.glob("*_chunks.json"):
                try:
                    chunks = json.loads(f.read_text(encoding="utf-8"))
                    self.vector_engine.ingest_chunks(chunks, doc_id=f.stem)
                except Exception:
                    pass

        if processed_triples_dir.exists():
            triples_list = []
            for f in processed_triples_dir.glob("*_triples.json"):
                try:
                    tdata = json.loads(f.read_text(encoding="utf-8"))
                    triples_list.append(tdata)
                except Exception:
                    pass
            if triples_list:
                self.graph_engine.build_from_academic_triples(triples_list)

    def process_artifacts(
        self,
        ai_chunks_path: Path | str,
        schema_report_path: Optional[Path | str] = None,
        doc_id: str = "default",
        university: str = "University",
    ) -> Dict[str, Any]:
        """
        Ingest chunks, extract facts & knowledge graph, and sync with Neo4j.
        """
        cpath = Path(ai_chunks_path)
        chunks = []
        if cpath.exists():
            chunks = json.loads(cpath.read_text(encoding="utf-8"))

        spath = Path(schema_report_path) if schema_report_path else None
        schema_report = json.loads(spath.read_text(encoding="utf-8")) if spath and spath.exists() else None

        # 1. Fact Extraction
        facts = []
        for c in chunks:
            text = c.get("plain_text") or ""
            sec_id = c.get("section_id") or "sec_0"
            page_no = c.get("source_pages", [1])[0] if c.get("source_pages") else 1
            efacts = self.fact_engine.extract_facts_from_text(
                text=text,
                document_id=doc_id,
                university=university,
                page_number=page_no,
                section_id=sec_id,
            )
            facts.extend(efacts)

        # 2. Vector Indexing
        vec_count = self.vector_engine.ingest_chunks(chunks, doc_id=doc_id)

        # 3. Knowledge Graph
        gdata = self.graph_engine.build_from_chunks(chunks, taxonomy_report=schema_report, doc_id=doc_id)

        # 4. Neo4j Sync
        neo4j_res = self.neo4j_db.sync_graph_data(gdata)

        return {
            "status": "success",
            "doc_id": doc_id,
            "university": university,
            "fact_count": len(facts),
            "vector_count": vec_count,
            "node_count": gdata.get("node_count", 0),
            "edge_count": gdata.get("edge_count", 0),
            "neo4j_sync": neo4j_res,
        }

    def query_subgraph_graphrag(
        self,
        query: str,
        hops: int = 2,
        top_k: int = 4,
        max_nodes: int = 35,
        document_filter: Optional[str] = None,
        active_docs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Complete GraphRAG Retrieval Flow executed via LangGraph cyclical StateGraph:
        1. intent_analyzer node
        2. vector_retriever node
        3. graph_traverser node
        4. synthesizer_verifier node
        5. corrective_expander conditional loop
        """
        return self.langgraph_workflow.run(
            query=query,
            hops=hops,
            top_k=top_k,
            document_filter=document_filter,
            active_docs=active_docs,
        )

    def ask_agent(self, query: str, active_docs: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute autonomous agentic multi-tool reasoning."""
        plan = self.agent_router.analyze_query(query, active_docs=active_docs)
        res = self.agent_router.execute_plan(plan, active_docs=active_docs)
        return {
            "query": res.query,
            "query_type": res.query_type,
            "selected_tools": res.selected_tools,
            "grounded_answer": res.grounded_answer,
            "traceability_score": res.traceability_score,
            "verified_claims": res.verified_claims,
            "citations": res.citations,
            "answer_contract": res.answer_contract,
        }

    def search_vectors(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.vector_engine.search(query=query, top_k=top_k)

    def get_graph_data(self) -> Dict[str, Any]:
        return self.graph_engine.get_graph_data()

    def get_cypher_script(self) -> str:
        return self.graph_engine.generate_cypher_script()

    def check_neo4j(self) -> Dict[str, Any]:
        return self.neo4j_db.check_connection()

    def sync_to_neo4j(self) -> Dict[str, Any]:
        gdata = self.graph_engine.get_graph_data()
        return self.neo4j_db.sync_graph_data(gdata)

    def execute_cypher(self, query: str) -> List[Dict[str, Any]]:
        return self.neo4j_db.run_cypher(query)
