# Qwen 2.5 7B Integration: System Prompts, Tool Calling, and Security Guardrails

## 1. Dynamic Schema Injection & Text-to-Cypher System Prompt
Deploying open models like Qwen 2.5 7B for Text-to-Cypher generation requires explicit system prompts with clear structural constraints. Providing the live database schema via LangChain Community's `Neo4jGraph.get_schema` or dynamic schema injection prevents the model from hallucinating non-existent node labels or relationship types.

### Prompt Template:
```text
You are an expert Neo4j Cypher developer translating natural language questions into syntactically correct, read-only Cypher queries.

### ACTIVE GRAPH DATABASE SCHEMA:
{schema_definition}

### COMPLIANCE & SECURITY GUARDRAILS:
1. ONLY USE node labels, relationship types, and properties present in the schema above.
2. STRICTLY READ-ONLY: Never use CREATE, MERGE, SET, DELETE, REMOVE, DETACH, DROP, or mutating apoc procedures.
3. Case-Insensitive Matching: Use toLower() or regex matching for entity names:
   WHERE toLower(n.name) CONTAINS toLower("query_term")
4. Section Traversals: Traverse Section nodes when scoping document chapters to prevent context contamination.
5. Limit traversals: Always use DISTINCT and provide a LIMIT clause (default 25).
6. Output ONLY the raw executable Cypher query wrapped in <query> tags.
```

---

## 2. Typed Tool Definitions via LangChain Core & Pydantic
Structured tool calling with Qwen 2.5 7B is enforced using Pydantic v2 schemas and LangChain Core `@tool` definitions:

```python
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from typing import Optional, List

class ExecuteCypherInput(BaseModel):
    """Input parameters for executing a validated read-only Cypher query."""
    query: str = Field(description="Strictly read-only Cypher query adhering to the active graph schema.")
    params: Optional[dict] = Field(default=None, description="Optional parameter map for parameterized execution.")

class DenseVectorSearchInput(BaseModel):
    """Input parameters for semantic text chunk retrieval in ChromaDB."""
    query: str = Field(description="Natural language search query.")
    top_k: int = Field(default=5, description="Number of top ranked passages to return.")
    doc_filter: Optional[str] = Field(default=None, description="Optional PDF filename filter.")

class RetrieveCommunitySummaryInput(BaseModel):
    """Input parameters for retrieving high-level NetworkX community cluster summaries."""
    community_id: Optional[int] = Field(default=None, description="Optional specific community cluster ID.")
    max_communities: int = Field(default=5, description="Maximum number of top community summaries to return.")
```

---

## 3. Cypher Security Guardrail & Sanitization Gate
Before passing generated Cypher queries to the Neo4j driver:
1. **Clause Blacklist Filter**: Reject queries containing `CREATE`, `MERGE`, `SET`, `DELETE`, `REMOVE`, `DETACH`, `DROP`, `ALTER`, `CALL apoc.create.*`, `CALL apoc.refactor.*`.
2. **Read-Only Whitelist Assertion**: Query must begin with `MATCH`, `OPTIONAL MATCH`, `WITH`, `UNWIND`, `RETURN`, or `CALL db.*`.
3. **Execution Timeout**: Transaction execution is bound to a 3.0s timeout to prevent denial-of-service from runaway path traversals.
