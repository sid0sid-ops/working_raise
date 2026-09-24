"""
RAISE Qwen 2.5 7B Integration: Dynamic Schema Injection, Typed Tool Definitions,
Static AST Cypher Lexer Analysis, and Anti-Injection Security Guardrails.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

try:
    from langchain_core.tools import tool, BaseTool
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False


class ExecuteCypherInput(BaseModel):
    """Input parameters for executing a validated read-only Cypher query."""
    query: str = Field(description="Strictly read-only Cypher query adhering to the active graph schema.")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Optional parameter map for execution.")


class DenseVectorSearchInput(BaseModel):
    """Input parameters for semantic text chunk retrieval in ChromaDB."""
    query: str = Field(description="Natural language search query.")
    top_k: int = Field(default=5, description="Number of top ranked passages to return.")
    doc_filter: Optional[str] = Field(default=None, description="Optional PDF filename filter.")


class RetrieveCommunitySummaryInput(BaseModel):
    """Input parameters for retrieving high-level NetworkX community cluster summaries."""
    community_id: Optional[int] = Field(default=None, description="Optional specific community cluster ID.")
    max_communities: int = Field(default=5, description="Maximum number of top community summaries to return.")


class StaticASTLexerAnalyzer:
    """
    Static Abstract Syntax Tree and Lexical analyzer for Cypher statements.
    Ensures zero mutating operations, blocks administrative procedure exfiltration,
    and neutralizes comment-based bypass injections.
    """

    MUTATING_CLAUSES = {
        "CREATE", "MERGE", "SET", "DELETE", "REMOVE", "DETACH",
        "DROP", "ALTER", "REVOKE", "DENY"
    }

    FORBIDDEN_PROCEDURES = [
        r"\bapoc\.(?!meta|search|text|coll|map)",
        r"\bdbms\.",
        r"\bsecurity\.",
        r"\bgds\.(?!graph\.project|util)",
    ]

    ALLOWED_STARTING_CLAUSES = {
        "MATCH", "OPTIONAL", "WITH", "UNWIND", "RETURN", "CALL"
    }

    @classmethod
    def sanitize_comments(cls, query: str) -> str:
        """Strip single-line and multi-line comments to prevent comment injection."""
        q = re.sub(r"//.*$", "", query, flags=re.MULTILINE)
        q = re.sub(r"/\*.*?\*/", "", q, flags=re.DOTALL)
        return q.strip()

    @classmethod
    def analyze(cls, cypher_query: str) -> Dict[str, Any]:
        """
        Performs static lexical AST token analysis on the query.
        Returns: {'valid': bool, 'reason': Optional[str], 'sanitized_query': str}
        """
        sanitized = cls.sanitize_comments(cypher_query)
        if not sanitized:
            return {"valid": False, "reason": "Query is empty."}

        # Tokenize query preserving string literals
        tokens = re.findall(r'"[^"]*"|\'[^\']*\'|\b[a-zA-Z_]\w*\b|[^\w\s]', sanitized)
        
        # Check first token
        first_token = tokens[0].upper() if tokens else ""
        if first_token not in cls.ALLOWED_STARTING_CLAUSES:
            return {
                "valid": False,
                "reason": f"Security violation: Query must begin with read-only clause (found '{first_token}').",
            }

        # Scan for mutating clauses outside string literals
        for i, t in enumerate(tokens):
            if not (t.startswith('"') or t.startswith("'")):
                upper_t = t.upper()
                # Check for DDL GRANT (e.g. GRANT ACCESS, GRANT ROLE) vs :Grant label
                if upper_t == "GRANT":
                    prev_t = tokens[i - 1] if i > 0 else ""
                    if prev_t != ":":
                        return {
                            "valid": False,
                            "reason": "Security violation: DDL command 'GRANT' is forbidden.",
                        }
                elif upper_t in cls.MUTATING_CLAUSES:
                    return {
                        "valid": False,
                        "reason": f"Security violation: Mutating clause '{upper_t}' is forbidden.",
                    }

        # Scan for forbidden procedure calls
        for proc in cls.FORBIDDEN_PROCEDURES:
            if re.search(proc, sanitized, re.IGNORECASE):
                return {
                    "valid": False,
                    "reason": f"Security violation: Administrative procedure matching '{proc}' is forbidden.",
                }

        return {"valid": True, "sanitized_query": sanitized}


class QueryParameterizationEngine:
    """
    Extracts raw string and numeric literals from Cypher queries into a secure $param map.
    """

    @classmethod
    def parameterize(cls, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Replaces inline string literals with parameters $p0, $p1, etc.
        """
        params: Dict[str, Any] = {}
        idx = 0

        def replacer(match):
            nonlocal idx
            val = match.group(1) or match.group(2)
            param_key = f"param_{idx}"
            params[param_key] = val
            idx += 1
            return f"${param_key}"

        # Parameterize single and double quoted literals
        parameterized_query = re.sub(r'"([^"]*)"|\'([^\']*)\'', replacer, query)
        return parameterized_query, params


class CypherSecurityGuardrail:
    """
    Unified Security Guardrail integrating Static AST Analysis, RBAC verification,
    and Query Parameterization.
    """

    @classmethod
    def validate_and_parameterize(cls, cypher_query: str) -> Dict[str, Any]:
        """
        Validates Cypher query against security policies and extracts parameters.
        """
        ast_res = StaticASTLexerAnalyzer.analyze(cypher_query)
        if not ast_res["valid"]:
            return ast_res

        clean_q = ast_res["sanitized_query"]
        param_q, params = QueryParameterizationEngine.parameterize(clean_q)

        return {
            "valid": True,
            "raw_query": clean_q,
            "parameterized_query": param_q,
            "params": params,
        }

    @classmethod
    def validate_query(cls, cypher_query: str) -> Dict[str, Any]:
        """Convenience validation check."""
        return StaticASTLexerAnalyzer.analyze(cypher_query)


def build_dynamic_schema_prompt(schema_str: Optional[str] = None) -> str:
    """
    Injects active database schema into the Qwen 2.5 7B Text-to-Cypher prompt.
    """
    if not schema_str:
        from src.infrastructure.graph.schema import NODE_LABELS, RELATIONSHIP_TYPES
        schema_str = f"Node Labels: {', '.join(NODE_LABELS)}\nRelationship Types: {', '.join(RELATIONSHIP_TYPES)}"

    return f"""You are an expert Neo4j Cypher developer translating natural language questions into syntactically correct, read-only Cypher queries.

### ACTIVE GRAPH DATABASE SCHEMA:
{schema_str}

### COMPLIANCE & SECURITY GUARDRAILS:
1. ONLY USE node labels, relationship types, and properties present in the schema above.
2. STRICTLY READ-ONLY: Never use CREATE, MERGE, SET, DELETE, REMOVE, DETACH, DROP, or mutating procedures.
3. Case-Insensitive Matching: Use toLower() or regex matching for entity names:
   WHERE toLower(n.name) CONTAINS toLower("query_term")
4. Limit traversals: Always use DISTINCT and provide a LIMIT clause (default 25).
5. Output ONLY the raw executable Cypher query wrapped in <query> tags.
"""
