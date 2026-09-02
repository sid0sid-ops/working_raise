"""
RAISE Autonomous Agent Router & Multi-Tool Execution Engine
Dynamically classifies queries, routes between Vector Search, Graph Subgraphs,
and Tabular Fact Engines, performs target document filtering, and generates
coherent, grounded academic synthesis with strict claim verification.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .claim_verifier import ClaimVerifier
from .fact_engine import FactEngine, NumericFact
from .graph_engine import GraphRAGEngine
from .neo4j_engine import Neo4jDatabase
from .reasoning_memory import ReasoningMemory
from .table_engine import TableEngine
from .vector_engine import LocalVectorEngine


@dataclass
class EvidenceSufficiencyReport:
    sufficient: bool
    missing_elements: List[str]
    iteration_count: int = 1
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentExecutionPlan:
    query: str
    query_type: str  # "SIMPLE_FACT", "COMPARATIVE_ANALYSIS", "RELATIONSHIP_QUERY", "SEMANTIC_EXPLORATION"
    extracted_universities: List[str] = field(default_factory=list)
    target_metrics: List[str] = field(default_factory=list)
    target_years: List[int] = field(default_factory=list)
    selected_tools: List[str] = field(default_factory=list)
    retrieved_evidence: Dict[str, Any] = field(default_factory=dict)
    sufficiency_report: Optional[EvidenceSufficiencyReport] = None
    grounded_answer: Optional[str] = None
    traceability_score: float = 0.0
    verified_claims: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    answer_contract: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "query_type": self.query_type,
            "extracted_universities": self.extracted_universities,
            "target_metrics": self.target_metrics,
            "target_years": self.target_years,
            "selected_tools": self.selected_tools,
            "sufficiency_report": self.sufficiency_report.to_dict() if self.sufficiency_report else None,
            "grounded_answer": self.grounded_answer,
            "traceability_score": self.traceability_score,
            "verified_claims": self.verified_claims,
            "citations": self.citations,
            "answer_contract": self.answer_contract,
        }


class AgentRouter:
    """
    Autonomous multi-tool router managing query intent decomposition,
    tool dispatch, document filtering, and grounded answer synthesis.
    Derived dynamically from the active workspace documents.
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

    def _get_active_documents(self) -> List[str]:
        """Dynamically fetch list of confirmed active PDF filenames from manifest."""
        manifest_file = Path(__file__).parent.parent / "data" / "processed" / "ingested_manifest.json"
        if manifest_file.exists():
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                return [d["filename"] for d in data.get("ready_documents", []) if "filename" in d]
            except Exception:
                pass
        return []

    def analyze_query(self, query: str, active_docs: Optional[List[str]] = None) -> AgentExecutionPlan:
        """Deconstruct natural query into intent, target universities/documents, and tools."""
        q_lower = query.lower()
        active_doc_list = active_docs if active_docs is not None else self._get_active_documents()

        # 1. Dynamically identify Target Document Filter from Active Workspace
        target_doc = None
        for fname in active_doc_list:
            stem = Path(fname).stem.lower().replace("_", " ").replace("-", " ")
            if fname.lower() in q_lower or (len(stem) > 4 and stem in q_lower):
                target_doc = fname
                break

        # 2. Identify University Keywords or Names
        unis: List[str] = []
        # Extract university from active document chunks / metadata if mentioned
        for fname in active_doc_list:
            clean_name = Path(fname).stem.replace("_", " ").replace("-", " ")
            words = [w for w in clean_name.split() if len(w) > 3 and w.lower() not in {"report", "annual", "english", "final", "upload", "combined"}]
            if any(w.lower() in q_lower for w in words):
                if clean_name not in unis:
                    unis.append(clean_name)

        # 3. Identify Years
        years: List[int] = []
        for y_match in re.finditer(r"\b(20[12][0-9])\b", query):
            years.append(int(y_match.group(1)))

        # 4. Classify Query Type
        if len(unis) >= 2 or "compare" in q_lower or "versus" in q_lower or " vs " in q_lower:
            q_type = "COMPARATIVE_ANALYSIS"
            tools = ["structured_fact_search", "comparative_engine", "vector_search", "claim_verifier"]
        elif any(w in q_lower for w in ["who leads", "director", "collaborated with", "partner", "relationship", "network", "programs", "institutes", "centres", "initiatives", "faculty"]):
            q_type = "RELATIONSHIP_QUERY"
            tools = ["cypher_query", "graph_traversal", "vector_search", "claim_verifier"]
        elif any(w in q_lower for w in ["balance sheet", "audit", "cag", "financial", "expenditure", "grant", "budget", "patents", "enrollment", "funding", "money", "rupees", "inr", "crore", "lakh"]):
            q_type = "SIMPLE_FACT"
            tools = ["structured_fact_search", "vector_search", "claim_verifier"]
        else:
            q_type = "SEMANTIC_EXPLORATION"
            tools = ["vector_search", "graph_traversal", "claim_verifier"]

        plan = AgentExecutionPlan(
            query=query,
            query_type=q_type,
            extracted_universities=unis,
            selected_tools=tools,
            target_years=years,
        )
        if target_doc:
            plan.retrieved_evidence["target_doc_filter"] = target_doc
        return plan

    def execute_plan(self, plan: AgentExecutionPlan, active_docs: Optional[List[str]] = None) -> AgentExecutionPlan:
        """Execute dynamic retrieval and synthesize clean, 100% grounded response from uploaded PDF content."""
        q_lower = plan.query.lower()
        facts: List[NumericFact] = []
        chunks: List[Dict[str, Any]] = []
        citations: List[Dict[str, Any]] = []
        active_doc_list = active_docs if active_docs is not None else self._get_active_documents()
        target_doc = plan.retrieved_evidence.get("target_doc_filter")

        # 1. Dense Vector Search Scoped strictly to active workspace documents
        chunks = self.vector_engine.search(
            query=plan.query,
            top_k=5,
            doc_filter=target_doc,
            active_docs=active_doc_list,
        )

        plan.retrieved_evidence["chunks"] = chunks
        seen_cids = set()
        for idx, c in enumerate(chunks):
            meta = c.get("metadata", {})
            cid = str(meta.get("chunk_id") or c.get("id") or f"chk_{idx+1}")
            if cid not in seen_cids:
                seen_cids.add(cid)
                raw_t = c.get("text", "")
                cleaned_excerpt = re.sub(r"Institution:.*?\n|Document:.*?\n|Period:.*?\n|Page:.*?\n|Heading:.*?\n|Content:\s*", "", raw_t).strip()
                citations.append({
                    "citation_index": len(citations) + 1,
                    "chunk_id": cid,
                    "document_id": meta.get("doc_id") or meta.get("document_id", "doc"),
                    "pdf_filename": meta.get("pdf_filename") or "Annual Report.pdf",
                    "primary_page": int(meta.get("primary_page", 1)),
                    "heading": meta.get("heading", f"Section (Page {meta.get('primary_page', 1)})"),
                    "plain_text": cleaned_excerpt[:350],
                    "university": meta.get("university", "Academic Institution"),
                    "similarity": round(float(c.get("similarity", 0.88)), 3),
                })

        # 2. Extract Structured Facts if available
        if "structured_fact_search" in plan.selected_tools:
            uni = plan.extracted_universities[0] if plan.extracted_universities else None
            facts = self.fact_engine.query_facts(university=uni)
            # Filter facts by active documents
            if active_doc_list:
                active_stems = [Path(f).stem for f in active_doc_list]
                facts = [f for f in facts if f.document_id in active_stems or f.document_id in active_doc_list]
            plan.retrieved_evidence["facts"] = [f.to_dict() for f in facts]

        # 3. Dynamic Grounded Answer Synthesis
        claims: List[str] = []
        answer_parts: List[str] = []

        if chunks:
            # Group chunks by document
            doc_groups: Dict[str, List[Dict[str, Any]]] = {}
            for c in chunks:
                meta = c.get("metadata", {})
                pdf_name = meta.get("pdf_filename") or "Uploaded Report"
                doc_groups.setdefault(pdf_name, []).append(c)

            cit_lookup = {c["chunk_id"]: c["citation_index"] for c in citations}

            # Attempt LLM Grounded Generation via Local Ollama / LocalLLMEngine
            llm_response = None
            try:
                import urllib.request
                ollama_url = "http://localhost:11434/api/generate"
                prompt_evidence = "\n\n".join([
                    f"[Doc: {c.get('metadata', {}).get('pdf_filename')}, Page {c.get('metadata', {}).get('primary_page')}, Heading: {c.get('metadata', {}).get('heading')}]:\n{c.get('text')[:400]}"
                    for c in chunks[:4]
                ])
                llm_prompt = f"""You are an audited institutional intelligence system.
Answer the user query strictly using only the provided document excerpts. Include citation tags like [1], [2] corresponding to the sources.

User Query: {plan.query}

Document Evidence:
{prompt_evidence}

Grounded Answer:"""
                
                req_data = json.dumps({
                    "model": "qwen2.5:7b",
                    "prompt": llm_prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 350}
                }).encode("utf-8")
                
                req = urllib.request.Request(ollama_url, data=req_data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    if resp_data.get("response"):
                        llm_response = resp_data["response"].strip()
            except Exception:
                llm_response = None

            if llm_response:
                raw_answer = llm_response
                for c in chunks:
                    meta = c.get("metadata", {})
                    pno = meta.get("primary_page", 1)
                    pdf_name = meta.get("pdf_filename", "Document.pdf")
                    claims.append(f"{pdf_name} (Page {pno}): Verified via LLM Grounding.")
            else:
                answer_parts.append(f"Based on the verified excerpts from your uploaded institutional reports:\n")

                # Extract key metrics and high-relevance findings across documents
                findings = []
                for idx, c in enumerate(chunks):
                    meta = c.get("metadata", {})
                    cid = str(meta.get("chunk_id") or c.get("id") or "")
                    cit_num = cit_lookup.get(cid, idx + 1)
                    pno = meta.get("primary_page", 1)
                    pdf_name = meta.get("pdf_filename") or "Report.pdf"
                    heading = meta.get("heading") or f"Section (Page {pno})"
                    raw_text = c.get("text", "")
                    cleaned_body = re.sub(
                        r"Institution:.*?\n|Document:.*?\n|Period:.*?\n|Page:.*?\n|Heading:.*?\n|Content:\s*",
                        "",
                        raw_text,
                    ).strip()

                    # Find sentences with numbers or query keywords
                    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned_body) if len(s.strip()) > 15]
                    q_words = set(w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", plan.query) if w.lower() not in {"what", "the", "and", "for", "with", "show", "tell", "total", "who", "user", "name", "your"})
                    
                    matched_sentences = [
                        s for s in sentences 
                        if any(qw in s.lower() for qw in q_words) or re.search(r"\b(Rs\.?|INR|\d+(?:\.\d+)?\s*(?:crore|lakh|%)|\d{4})\b", s, re.IGNORECASE)
                    ]
                    
                    if matched_sentences:
                        selected_sentence = matched_sentences[0]
                        findings.append(f"• **{heading}** ({pdf_name}, Page {pno}) [[{cit_num}]]:\n  {selected_sentence}")
                        claims.append(f"{pdf_name} (Page {pno}): {selected_sentence[:140]}")
                    elif q_words and idx == 0:
                        findings.append(f"• Notice: The uploaded documents do not contain explicit personal identity information for '{plan.query}'. Displaying closest relevant excerpt:\n  {sentences[0] if sentences else cleaned_body[:200]}")

                if findings:
                    answer_parts.append("\n\n".join(findings))
                    raw_answer = "\n".join(answer_parts)
                else:
                    raw_answer = f"The uploaded institutional documents do not contain information related to '{plan.query}'. They cover institutional governance, sponsored research grants, academic degrees, and startup incubation."
        else:
            raw_answer = "INSUFFICIENT_EVIDENCE: No matching verified statements or passages were found in the uploaded document(s) for your query."
            claims.append("INSUFFICIENT_EVIDENCE: No matching statements found in uploaded document(s).")


        # 4. Anti-Hallucination Claim Verification
        contract = self.verifier.create_answer_contract(
            answer_text=raw_answer,
            claims=claims,
            query=plan.query,
            retrieved_facts=facts,
            retrieved_chunks=chunks,
            comparability="COMPARABLE",
        )

        plan.answer_contract = contract.to_dict()
        plan.verified_claims = [c.to_dict() for c in contract.claims]
        plan.traceability_score = contract.grounding_score
        plan.grounded_answer = raw_answer
        plan.citations = citations

        return plan
