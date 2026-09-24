"""
RAISE API Pydantic Schemas
Strict request and response contracts for all endpoints.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    chat_history: Optional[List[Dict[str, str]]] = None
    hops: Optional[int] = 2
    top_k: Optional[int] = 4
    document_filter: Optional[str] = None
    active_docs: Optional[List[str]] = None
    mode: Optional[str] = "fast"
    library: Optional[str] = None
    parser: Optional[str] = None
    engine: Optional[str] = None
    parse_mode: Optional[str] = None
    extract_tables: Optional[Union[bool, str]] = None
    full_potential: Optional[Union[bool, str]] = None


class ChatMessageRequest(BaseModel):
    message: Optional[str] = None
    query: Optional[str] = None
    mode: Optional[str] = "fast"
    session_id: Optional[str] = None
    thread_id: Optional[str] = None
    request_id: Optional[str] = None
    stream: Optional[bool] = False
    library: Optional[str] = None
    hops: Optional[int] = 2
    top_k: Optional[int] = 4
    chat_history: Optional[List[Dict[str, Any]]] = None
    active_docs: Optional[List[str]] = None
    document_filter: Optional[str] = None
    format: Optional[str] = "sse"
    parser: Optional[str] = None
    engine: Optional[str] = None
    parse_mode: Optional[str] = None
    extract_tables: Optional[Union[bool, str]] = None
    full_potential: Optional[Union[bool, str]] = None


class AbortRequest(BaseModel):
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    thread_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    rating: Any
    reason: Optional[str] = None
    query: Optional[str] = None
    message_id: Optional[str] = None


class BatchChatRequest(BaseModel):
    query: str
    doc_filters: Optional[List[str]] = None
    documents: Optional[List[str]] = None
    mode: Optional[str] = "fast"


class ChatHistorySyncRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    session_id: Optional[str] = None
    thread_id: Optional[str] = None
    title: Optional[str] = None
    messages: List[Dict[str, Any]] = []
    attached_docs: Optional[List[str]] = None
    selectedSourceIds: Optional[List[str]] = None
    sources: Optional[List[Any]] = None
    username: Optional[str] = None
    is_saved: Optional[bool] = None

