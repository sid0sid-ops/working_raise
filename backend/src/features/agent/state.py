"""
GraphRAG State Definitions & Document Converters
================================================
TypedDict State schema for LangGraph agentic orchestration across all retrieval,
verification, and multi-hop reasoning nodes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage

from src.retrieval.fusion import chunk_to_document, document_to_chunk


def chunks_to_langchain_documents(chunks: List[Dict[str, Any] | Document]) -> List[Document]:
    """Helper to convert a list of chunks into canonical LangChain Document objects."""
    return [chunk_to_document(c) for c in chunks]


def langchain_documents_to_chunks(docs: List[Document | Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Helper to convert a list of LangChain Document objects into chunk dictionaries."""
    return [document_to_chunk(d) for d in docs]


class GraphRAGState(TypedDict, total=False):
    """LangGraph State Container for GraphRAG Query Lifecycle."""
    query: str
    original_query: str
    hops: int
    top_k: int
    document_filter: Optional[str]
    active_docs: Optional[List[str]]

    # Session & Multi-Turn State (Dicts & LangChain Messages)
    thread_id: Optional[str]
    chat_history: Optional[List[Dict[str, str]]]
    messages: Optional[List[BaseMessage]]

    # Query Intake & Decomposition
    standalone_query: str
    decomposed_queries: List[str]
    bypass_retrieval: bool
    direct_response: Optional[str]
    resolved_entity: Optional[str]
    telemetry: Optional[Any]
    pipeline_stages: List[Dict[str, Any]]

    # Iterative Multi-Hop Query Planning State
    current_sub_query: Optional[str]
    accumulated_context: Optional[List[str]]
    hop_count: int
    max_hops: int
    is_fully_resolved: bool
    hop_history: Optional[List[Dict[str, Any]]]

    # Routing & Planning
    routing_strategy: str  # "GLOBAL_COMMUNITY", "LOCAL_GRAPH_CYPHER", "HYBRID_VECTOR"
    query_intent: str
    selected_tools: List[str]

    # Cypher Lifecycle & Error Correction
    cypher_query: str
    cypher_error: Optional[str]
    cypher_records: List[Dict[str, Any]]
    cypher_repair_count: int
    cypher_status: str  # "SUCCESS", "FAILED", "FALLBACK"

    # Graph & Vector Evidence (Raw Dictionaries & Canonical LangChain Documents)
    seed_node_ids: List[str]
    subgraph: Dict[str, Any]
    relevant_chunks: List[Dict[str, Any]]
    top_chunks: List[Dict[str, Any]]
    documents: List[Document]
    community_summaries: List[Dict[str, Any]]

    # Path Critic
    path_critic_expanded: bool

    # Synthesis, Verification & Quality Gate
    grounded_answer: str
    traceability_score: float
    verified_claims: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    data_lineage: List[Dict[str, Any]]
    answer_contract: Dict[str, Any]
    synthesis_metadata: Optional[Dict[str, Any]]
    
    # Runtime Quality Gate State
    retry_count: int
    quality_gate_decision: str  # "accept", "retry", "unable_to_verify", "empty_workspace"
    quality_gate_report: Dict[str, Any]
    execution_time: float
