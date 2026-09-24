"""
Query Service
Encapsulates headless network query execution, SSE streaming event generation,
LangGraph multi-engine subgraph reasoning, and dynamic research suggestions.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from src.api.context import _parse_drawer_active_docs, get_ready_documents_list
try:
    from prompts.system_synthesis import sanitize_rag_text
except ImportError:
    from RAG.prompts.system_synthesis import sanitize_rag_text

logger = logging.getLogger("raise.services.query")


class QueryService:
    def __init__(
        self,
        rag_engine: Any = None,
        postgres_manager: Any = None,
        session_memory_manager: Any = None,
    ):
        self.rag_engine = rag_engine
        self.postgres_manager = postgres_manager
        self.session_memory_manager = session_memory_manager

    def execute_query(
        self,
        query: str,
        thread_id: str = "default",
        active_docs: Optional[List[str]] = None,
        hops: int = 2,
        top_k: int = 4,
        document_filter: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Primary synchronous/headless query execution.
        """
        if active_docs is None:
            ready_docs = get_ready_documents_list()
            active_docs = [d["filename"] for d in ready_docs if "filename" in d]

        if not self.rag_engine:
            raise RuntimeError("RAG engine is not initialized in QueryService")

        result = self.rag_engine.query_subgraph_graphrag(
            query=query,
            hops=hops,
            top_k=top_k,
            document_filter=document_filter,
            active_docs=active_docs,
            thread_id=thread_id,
            chat_history=chat_history,
        )

        if "grounded_answer" in result and result["grounded_answer"]:
            result["grounded_answer"] = sanitize_rag_text(result["grounded_answer"])
        if "answer" in result and result["answer"]:
            result["answer"] = sanitize_rag_text(result["answer"])

        if thread_id and self.session_memory_manager:
            active_entities = []
            if result.get("resolved_entity"):
                active_entities.append(result["resolved_entity"])
            for node in result.get("subgraph", {}).get("nodes", []):
                nl = node.get("label") or node.get("id") or node.get("name")
                if nl and nl not in active_entities:
                    active_entities.append(str(nl))
            assistant_ans = result.get("grounded_answer") or result.get("answer", "")
            self.session_memory_manager.record_turn(
                thread_id=thread_id,
                user_query=query,
                resolved_query=result.get("resolved_query") or query,
                active_entities=active_entities[:10],
                citations=result.get("citations", []),
                assistant_answer=assistant_ans,
            )

        result["thread_id"] = thread_id
        result["session_id"] = thread_id
        return result

    async def stream_query_events(
        self,
        query: str,
        thread_id: str = "default",
        active_docs: Optional[List[str]] = None,
        hops: int = 2,
        top_k: int = 4,
        document_filter: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Server-Sent Events generator yielding stage updates, answer chunks, and final payload.
        """
        if active_docs is None:
            ready_docs = get_ready_documents_list()
            active_docs = [d["filename"] for d in ready_docs if "filename" in d]

        try:
            # 1. Intake stage
            yield f"event: stage\ndata: {json.dumps({'stage': 'RECEIVED', 'status': 'completed', 'detail': 'Query received by backend'})}\n\n"

            # 2. Execute RAG pipeline
            result = self.execute_query(
                query=query,
                thread_id=thread_id,
                active_docs=active_docs,
                hops=hops,
                top_k=top_k,
                document_filter=document_filter,
                chat_history=chat_history,
            )

            # Emit all intermediate pipeline stages
            for stage_item in result.get("pipeline_stages", []):
                if stage_item.get("stage") != "RECEIVED":
                    yield f"event: stage\ndata: {json.dumps(stage_item)}\n\n"

            # 3. Stream answer tokens
            answer_text = result.get("grounded_answer") or result.get("answer", "")
            words = re.findall(r"\S+|\s+", answer_text)
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                token_chunk = "".join(words[i : i + chunk_size])
                yield f"data: {json.dumps({'token': token_chunk})}\n\n"

            # 4. Emit final completion event
            yield f"event: final\ndata: {json.dumps(result)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    def execute_subgraph_workflow(
        self,
        query: str,
        session_id: Optional[str] = None,
        hops: int = 2,
        top_k: int = 4,
        doc_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute LangGraph StateGraph Workflow with Coreference Resolution & Quality Gate.
        """
        if not self.rag_engine:
            raise RuntimeError("RAG engine is not initialized in QueryService")

        # Multi-Turn Coreference Resolution
        resolved_query = query
        resolved_entity = None
        if session_id and self.session_memory_manager:
            resolved_query, resolved_entity = self.session_memory_manager.resolve_coreference(query, session_id)
            if resolved_entity and resolved_query != query:
                logger.info(f"[SESSION MEMORY] Coreference Resolved: '{query}' -> '{resolved_query}' (Referent: {resolved_entity})")

        ready_docs = get_ready_documents_list()
        if not ready_docs:
            empty_resp = {
                "query": query,
                "query_type": "EMPTY_WORKSPACE",
                "grounded_answer": "Please upload an academic PDF to begin your research.",
                "answer": "Please upload an academic PDF to begin your research.",
                "grounded": False,
                "traceability_score": 0.0,
                "verified_claims": [],
                "citations": [],
                "top_chunks": [],
                "subgraph": {"nodes": [], "edges": []},
                "sources_count": 0,
                "execution_time": 0.0,
                "message": "Please upload an academic PDF to begin your research."
            }
            if session_id:
                empty_resp["session_id"] = session_id
                empty_resp["resolved_query"] = resolved_query
            return empty_resp

        active_filenames = [d["filename"] for d in ready_docs if "filename" in d]

        # Run compiled LangGraph state machine
        result = self.rag_engine.query_subgraph_graphrag(
            query=resolved_query,
            hops=hops,
            top_k=top_k,
            document_filter=doc_filter,
            active_docs=active_filenames,
        )

        if "grounded_answer" in result and result["grounded_answer"]:
            result["grounded_answer"] = sanitize_rag_text(result["grounded_answer"])
        if "answer" in result and result["answer"]:
            result["answer"] = sanitize_rag_text(result["answer"])

        # Record conversational turn
        if session_id and self.session_memory_manager:
            active_entities = []
            if resolved_entity:
                active_entities.append(resolved_entity)
            for node in result.get("subgraph", {}).get("nodes", []):
                nl = node.get("label") or node.get("id")
                if nl and nl not in active_entities:
                    active_entities.append(str(nl))
            for claim in result.get("verified_claims", []):
                for ent in claim.get("entities", []):
                    if ent not in active_entities:
                        active_entities.append(str(ent))

            assistant_ans = result.get("grounded_answer") or result.get("answer", "")
            self.session_memory_manager.record_turn(
                thread_id=session_id,
                user_query=query,
                resolved_query=resolved_query,
                active_entities=active_entities[:10],
                citations=result.get("citations", []),
                assistant_answer=assistant_ans,
            )
            result["session_id"] = session_id
            result["resolved_query"] = resolved_query

        return result

    def get_dynamic_suggestions(
        self,
        raw_candidates: List[str],
        has_explicit_drawer_param: bool,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate dynamic, complex graph-grounded research questions based strictly on active drawer documents.
        Zero-hardcoding policy: If active_docs is empty or missing, returns [] immediately.
        """
        if not has_explicit_drawer_param or not raw_candidates:
            return []

        parsed_active = _parse_drawer_active_docs(raw_candidates)
        if not parsed_active:
            return []

        effective_docs = parsed_active
        suggestions: List[Dict[str, Any]] = []
        seen = set()

        # Build document prefixes for chunk scoping in Neo4j
        doc_prefixes = [
            re.sub(r"[^a-zA-Z0-9_-]", "_", Path(d).stem).replace("-", "_")
            for d in effective_docs
        ]

        extracted_entities = []
        extracted_headings = []
        extracted_relations = []

        if self.rag_engine and getattr(self.rag_engine, "neo4j_db", None) and getattr(self.rag_engine.neo4j_db, "connected", False):
            try:
                # 1. Scoped entity extraction: only entities mentioned by chunks belonging to the active documents
                ent_query = """
                MATCH (c:Chunk)
                WHERE any(p IN $prefixes WHERE c.id STARTS WITH p)
                MATCH (c)-[r]->(e)
                WHERE NOT e:Chunk AND NOT e:Section 
                  AND NOT e.name STARTS WITH 'Passage' 
                  AND NOT e.name STARTS WITH 'Metric:'
                  AND size(coalesce(e.name, '')) > 2
                RETURN coalesce(e.name, e.label) AS name, labels(e) AS labels, count(c) AS freq
                ORDER BY freq DESC LIMIT 20
                """
                ent_records = self.rag_engine.neo4j_db.run_cypher(ent_query, {"prefixes": doc_prefixes})
                for r in ent_records:
                    if r.get("name") and r["name"].strip() and not r.get("error"):
                        extracted_entities.append({
                            "name": r["name"].strip(),
                            "labels": [l for l in r.get("labels", []) if l not in ("Entity", "Chunk")],
                            "freq": r.get("freq", 1)
                        })

                # 2. Scoped section heading extraction
                head_query = """
                MATCH (c:Chunk)
                WHERE any(p IN $prefixes WHERE c.id STARTS WITH p)
                MATCH (s:Section)-[:CONTAINS_CHUNK]->(c)
                WHERE NOT s.name STARTS WITH 'Passage' AND size(s.name) > 3
                RETURN DISTINCT s.name AS heading, count(c) AS freq
                ORDER BY freq DESC LIMIT 15
                """
                head_records = self.rag_engine.neo4j_db.run_cypher(head_query, {"prefixes": doc_prefixes})
                for r in head_records:
                    h_val = r.get("heading")
                    if h_val and not r.get("error"):
                        clean_h = re.sub(r"^\d+\s*\|\s*|\s*\|\s*\d+$", "", h_val).strip()
                        if clean_h and len(clean_h) > 3 and clean_h.lower() not in [x.lower() for x in extracted_headings]:
                            extracted_headings.append(clean_h)

                # 3. Scoped relation extraction
                rel_query = """
                MATCH (c:Chunk)
                WHERE any(p IN $prefixes WHERE c.id STARTS WITH p)
                MATCH (c)-[:MENTIONS]->(a)
                MATCH (a)-[rel]->(b)
                WHERE NOT type(rel) IN ['CONTAINS_CHUNK', 'HAS_SECTION', 'MENTIONS', 'HAS_FACT']
                  AND a <> b
                RETURN coalesce(a.name, a.label) AS a_name, labels(a)[0] AS a_type,
                       type(rel) AS rel,
                       coalesce(b.name, b.label) AS b_name, labels(b)[0] AS b_type
                LIMIT 10
                """
                rel_records = self.rag_engine.neo4j_db.run_cypher(rel_query, {"prefixes": doc_prefixes})
                for gr in rel_records:
                    if gr.get("a_name") and gr.get("b_name") and not gr.get("error"):
                        extracted_relations.append(gr)

            except Exception as e:
                logger.info(f"[Document-Scoped Suggestions Neo4j Notice]: {e}")

        # Try fast LLM question generation grounded in extracted scoped entities
        if (extracted_entities or extracted_headings or extracted_relations) and self.rag_engine:
            try:
                from src.infrastructure.providers.router import get_provider_router, InferenceTask
                llm_router = get_provider_router()
                topics = []
                for e in extracted_entities[:8]:
                    topics.append(e["name"])
                for h in extracted_headings[:5]:
                    topics.append(h)

                topic_context = "\n".join(f"- {t}" for t in topics)
                prompt = (
                    f"Based on the following active research document topics and entities:\n"
                    f"{topic_context}\n\n"
                    f"Generate {limit} concise, high-value exploratory questions that an investigator or analyst would ask.\n"
                    f"Rules:\n"
                    f"- Every question must be directly grounded in the provided topics.\n"
                    f"- Questions must be natural, diverse, and under 90 characters.\n"
                    f"- Return valid JSON array of objects only: [{{\"query\": \"...\", \"category\": \"...\"}}]\n"
                )
                llm_resp = llm_router.complete(
                    prompt=prompt,
                    task=InferenceTask.QUERY_DECOMPOSITION,
                    max_tokens=300,
                    temperature=0.2,
                )
                if llm_resp and "[" in llm_resp and "]" in llm_resp:
                    clean_json = llm_resp[llm_resp.find("["):llm_resp.rfind("]")+1]
                    parsed_qs = json.loads(clean_json)
                    for item in parsed_qs:
                        q_str = item.get("query", "").strip()
                        if q_str and q_str not in seen:
                            seen.add(q_str)
                            suggestions.append({
                                "query": q_str,
                                "category": item.get("category") or "Institutional Research",
                                "complexity": "intermediate"
                            })
                            if len(suggestions) >= limit:
                                break
            except Exception as e:
                logger.debug(f"LLM suggestion generation notice: {e}")

        # Deterministic grounded fallback if LLM synthesis is offline or returned fewer items
        if len(suggestions) < limit and extracted_relations:
            for gr in extracted_relations:
                an = gr.get("a_name")
                bn = gr.get("b_name")
                rel = gr.get("rel", "RELATED_TO").replace("_", " ").lower()
                q = f"How does {an} {rel} {bn} and what are the strategic implications?"
                if q not in seen:
                    seen.add(q)
                    suggestions.append({
                        "query": q,
                        "category": "Relational Synthesis",
                        "complexity": "intermediate"
                    })
                    if len(suggestions) >= limit:
                        break

        if len(suggestions) < limit and extracted_entities:
            for ent in extracted_entities:
                ename = ent["name"]
                lbls = ent.get("labels", [])
                lbl_str = lbls[0] if lbls else "Entity"
                q = f"What key initiatives, mandates, or outcomes are associated with {ename} ({lbl_str})?"
                if q not in seen:
                    seen.add(q)
                    suggestions.append({
                        "query": q,
                        "category": "Key Entity Analysis",
                        "complexity": "intermediate"
                    })
                    if len(suggestions) >= limit:
                        break

        if len(suggestions) < limit and extracted_headings:
            for h in extracted_headings:
                q = f"What specific findings and performance metrics are detailed under '{h}'?"
                if q not in seen:
                    seen.add(q)
                    suggestions.append({
                        "query": q,
                        "category": "Section Deep-Dive",
                        "complexity": "intermediate"
                    })
                    if len(suggestions) >= limit:
                        break

        if len(suggestions) < limit:
            for fn in effective_docs[:limit]:
                clean_name = Path(fn).stem.replace("_", " ").title()
                q = f"Synthesize the overarching strategic and institutional conclusions documented in {clean_name}"
                if q not in seen:
                    seen.add(q)
                    suggestions.append({
                        "query": q,
                        "category": "Document Overview",
                        "complexity": "basic"
                    })
                    if len(suggestions) >= limit:
                        break

        return suggestions[:limit]
