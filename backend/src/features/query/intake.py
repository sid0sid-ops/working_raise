"""
RAISE Query Intake & Reformulation Pipeline
Implements the 4-node preprocessing sequence:
  1. Intent Router & Out-of-Scope Firewall (Zero-DB bypass on general chat / out-of-scope)
  2. Coreference Resolution & Pronoun Disambiguation (Thread-scoped memory)
  3. Query Decomposer & Splitter (Splits compound questions into standalone sub-queries)
  4. Pipeline Stage Telemetry Tracker (Observability & State Machine)
"""

from __future__ import annotations

import os
import re
import json
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple


# =============================================================================
# 1. PIPELINE TELEMETRY & OBSERVABILITY
# =============================================================================

STAGE_NAMES = [
    "RECEIVED",
    "ROUTING",
    "COREFERENCE_RESOLUTION",
    "QUERY_DECOMPOSITION",
    "VECTOR_RETRIEVAL",
    "BM25_RETRIEVAL",
    "GRAPH_RETRIEVAL",
    "FUSION",
    "RERANKING",
    "SYNTHESIS",
    "QUALITY_GATE",
    "COMPLETED",
]

StageStatus = Literal["pending", "running", "completed", "failed", "skipped"]


@dataclass
class StageRecord:
    stage: str
    status: StageStatus = "pending"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    latency_ms: float = 0.0
    detail: Optional[str] = None
    error: Optional[str] = None

    def complete(self, detail: Optional[str] = None):
        self.status = "completed"
        self.end_time = time.time()
        self.latency_ms = round((self.end_time - self.start_time) * 1000, 2)
        if detail:
            self.detail = detail

    def skip(self, reason: Optional[str] = None):
        self.status = "skipped"
        self.end_time = time.time()
        self.latency_ms = 0.0
        self.detail = reason or "Skipped by pipeline policy"

    def fail(self, error: str):
        self.status = "failed"
        self.end_time = time.time()
        self.latency_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "detail": self.detail,
            "error": self.error,
        }


class PipelineTelemetry:
    """
    Tracks state machine execution transitions across all retrieval and synthesis stages.
    """

    def __init__(self):
        self.stages: Dict[str, StageRecord] = {
            s: StageRecord(stage=s, status="pending") for s in STAGE_NAMES
        }
        self.start_time = time.time()
        # Mark RECEIVED as completed immediately
        self.stages["RECEIVED"].complete("Request accepted by backend")

    def start_stage(self, stage: str, detail: Optional[str] = None):
        if stage in self.stages:
            self.stages[stage].status = "running"
            self.stages[stage].start_time = time.time()
            if detail:
                self.stages[stage].detail = detail

    def complete_stage(self, stage: str, detail: Optional[str] = None):
        if stage in self.stages:
            self.stages[stage].complete(detail)

    def skip_stage(self, stage: str, reason: Optional[str] = None):
        if stage in self.stages:
            self.stages[stage].skip(reason)

    def fail_stage(self, stage: str, error: str):
        if stage in self.stages:
            self.stages[stage].fail(error)

    def get_total_latency_sec(self) -> float:
        return round(time.time() - self.start_time, 3)

    def to_list(self) -> List[Dict[str, Any]]:
        return [self.stages[s].to_dict() for s in STAGE_NAMES]


# =============================================================================
# 2. NODE 1: INTENT ROUTER & OUT-OF-SCOPE FIREWALL
# =============================================================================

@dataclass
class IntentRouteResult:
    intent: str  # "ACADEMIC_RESEARCH" | "FINANCIAL_FACT" | "MULTI_HOP_RELATION" | "GENERAL_CHAT" | "OUT_OF_SCOPE"
    datasource: str  # "vector search" | "graph query" | "hybrid" | "general chat"
    is_safe: bool
    bypass_retrieval: bool
    refusal_reason: Optional[str] = None
    direct_response: Optional[str] = None


class IntentRouterNode:
    """
    Classifies query intent and acts as an Out-of-Scope Firewall.
    Bypasses databases entirely for greetings, general conversation, or off-topic prompts.
    """

    ADVERSARIAL_PATTERNS = [
        r"(?i)\b(ignore\s+previous\s+instructions|system\s+prompt|delete\s+database|drop\s+table)\b",
        r"(?i)\b(match\s*\(.*\)\s*detach\s*delete|rm\s+-rf|format\s+c:)\b",
        r"(?i)\b(jailbreak|bypass\s+guardrails)\b",
    ]

    GREETING_PATTERNS = [
        r"(?i)^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening)|howdy)\b",
        r"(?i)\b(?:my\s+name\s+is|call\s+me)\b",
        r"(?i)\b(?:do\s+you\s+know|what\s+is|what's)\s+my\s+name\b",
        r"(?i)\bwho\s+am\s+i\b",
        r"(?i)\bdo\s+you\s+remember\b",
        r"(?i)\b(?:what\s+is|what's)\s+your\s+name\b",
        r"(?i)\bwho\s+are\s+you\b",
        r"(?i)\bwhat\s+can\s+you\s+do\b",
        r"(?i)\bhow\s+are\s+you\b",
        r"(?i)\b(?:thank\s+you|thanks|nice\s+to\s+meet\s+you)\b",
    ]

    OUT_OF_SCOPE_PATTERNS = [
        r"(?i)\b(recipe|bake|cake|poem|lyrics|song|weather\s+in|horoscope|crypto\s+price)\b",
        r"(?i)\b(who\s+is\s+batman|capital\s+of\s+france|prime\s+minister\s+of\s+canada)\b",
        r"(?i)\b(tell\s+me\s+a\s+joke|write\s+a\s+story\s+about)\b",
    ]

    FINANCIAL_KEYWORDS = [
        "revenue", "profit", "ebitda", "income", "expenditure", "budget",
        "crore", "lakh", "turnover", "grant amount", "financial", "balance sheet",
        "funding", "cost", "investment", "valuation"
    ]

    GRAPH_KEYWORDS = [
        "who founded", "who leads", "director", "incubated", "partner",
        "collaborated", "supervises", "invested in", "board member",
        "startup", "spin-off", "connected to", "relationship", "network"
    ]

    ACADEMIC_DOMAIN_TERMS = [
        "university", "institute", "institution", "council", "academy",
        "campus", "faculty", "student", "alumni", "ranking", "rankings",
        "nirf", "qs", "engineering", "science", "biotechnology", "genomics",
        "school", "department", "centre", "center", "lab", "laboratory",
        "degree", "curriculum", "donate", "donation", "endowment", "grant",
        "fellowship", "scholarship", "incubation", "incubator", "startup",
        "patent", "research", "annual report", "audited", "balance sheet",
        "expenditure", "liabilities", "assets", "mandate", "director",
        "page", "pages", "citation", "citations", "document", "documents",
        "report", "reports", "table", "tables", "section", "sections",
        "chapter", "chapters", "figure", "figures", "schedule", "appendix"
    ]

    def __init__(self, vllm_url: Optional[str] = None):
        self.vllm_url = vllm_url or os.getenv("VLLM_BASE_URL", "http://localhost:8002/v1")

    def route(self, query: str) -> IntentRouteResult:
        q_clean = query.strip()
        q_lower = q_clean.lower()

        # Check if query contains explicit academic or institutional domain terms (dynamically loaded from library)
        dynamic_terms = set(self.ACADEMIC_DOMAIN_TERMS)
        try:
            from src.retrieval.fusion import get_library_institutions
            lib_insts = get_library_institutions()
            for aliases in lib_insts.values():
                dynamic_terms.update(aliases)
        except Exception:
            pass

        is_academic_query = any(re.search(rf"\b{re.escape(term)}\b", q_lower) for term in dynamic_terms)

        # 1. Adversarial Injection Check (Always active)
        for pat in self.ADVERSARIAL_PATTERNS:
            if re.search(pat, q_clean):
                return IntentRouteResult(
                    intent="OUT_OF_SCOPE",
                    datasource="general chat",
                    is_safe=False,
                    bypass_retrieval=True,
                    refusal_reason="Adversarial or hazardous instruction detected.",
                    direct_response="I cannot execute system commands or modify operating parameters. How may I assist your academic research?",
                )

        # 2. General Conversational / Greeting Check (Only if not asking a substantive question)
        if not is_academic_query:
            for pat in self.GREETING_PATTERNS:
                if re.search(pat, q_clean, re.IGNORECASE):
                    return IntentRouteResult(
                        intent="GENERAL_CHAT",
                        datasource="general chat",
                        is_safe=True,
                        bypass_retrieval=True,
                        direct_response="Hello! I am RAISE, your institutional intelligence and academic research assistant. How may I assist your research today? Feel free to ask about faculty, departments, publications, patents, admissions, or financial highlights from the reports.",
                    )

            # 3. Off-Topic / Conversational Guidance
            for pat in self.OUT_OF_SCOPE_PATTERNS:
                if re.search(pat, q_clean):
                    return IntentRouteResult(
                        intent="GENERAL_CHAT",
                        datasource="general chat",
                        is_safe=True,
                        bypass_retrieval=True,
                        direct_response="Hello! While I specialize in analyzing academic reports, technology incubation, and institutional research metrics, I'm happy to help guide you. Feel free to ask any question about the uploaded reports or let me know what you're looking for!",
                    )

        # 4. Attempt vLLM Qwen 2.5 14B Intent Routing
        vllm_route = self._query_vllm_intent(q_clean)
        if vllm_route:
            # If query is academic but vLLM mistakenly returned OUT_OF_SCOPE or GENERAL_CHAT, override it
            if is_academic_query and vllm_route.intent in ("OUT_OF_SCOPE", "GENERAL_CHAT"):
                if any(w in q_lower for w in self.FINANCIAL_KEYWORDS) or any(w in q_lower for w in ["donate", "donation", "dollar", "billion", "crore", "lakh", "fund"]):
                    return IntentRouteResult(intent="FINANCIAL_FACT", datasource="graph query", is_safe=True, bypass_retrieval=False)
                elif any(w in q_lower for w in self.GRAPH_KEYWORDS):
                    return IntentRouteResult(intent="MULTI_HOP_RELATION", datasource="graph query", is_safe=True, bypass_retrieval=False)
                else:
                    return IntentRouteResult(intent="ACADEMIC_RESEARCH", datasource="vector search", is_safe=True, bypass_retrieval=False)
            return vllm_route

        # 5. Rule-Based Deterministic Fallback
        if any(w in q_lower for w in self.FINANCIAL_KEYWORDS) or any(w in q_lower for w in ["donate", "donation", "dollar", "billion", "crore", "lakh", "fund"]):
            return IntentRouteResult(
                intent="FINANCIAL_FACT",
                datasource="graph query",
                is_safe=True,
                bypass_retrieval=False,
            )
        if any(w in q_lower for w in self.GRAPH_KEYWORDS):
            return IntentRouteResult(
                intent="MULTI_HOP_RELATION",
                datasource="graph query",
                is_safe=True,
                bypass_retrieval=False,
            )

        return IntentRouteResult(
            intent="ACADEMIC_RESEARCH",
            datasource="vector search",
            is_safe=True,
            bypass_retrieval=False,
        )

    def _query_vllm_intent(self, query: str) -> Optional[IntentRouteResult]:
        """Optionally classify using local Qwen 2.5 14B vLLM."""
        try:
            url = f"{self.vllm_url}/chat/completions"
            sys_msg = (
                "You are an intent classifier for an academic institutional intelligence system. Categorize the user's query into strictly one of:\n"
                "- ACADEMIC_RESEARCH (papers, laboratories, campus overview, rankings, academic programs, document pages, citations, tables, sections)\n"
                "- FINANCIAL_FACT (donations, revenues, endowments, budgets, funding, costs)\n"
                "- MULTI_HOP_RELATION (who founded, directors, startups incubated, partnerships, alumni roles)\n"
                "- GENERAL_CHAT (greetings, chit-chat)\n"
                "- OUT_OF_SCOPE (recipes, movies, pop culture, non-institutional trivia)\n"
                "Note: Any query mentioning universities, IITs, engineering colleges, campuses, alumni donations, academic rankings, or asking about specific document pages (e.g., 'page 4', 'page no 4'), citations, or tables MUST be classified as ACADEMIC_RESEARCH or FINANCIAL_FACT.\n"
                "Respond with only the category name."
            )
            payload = json.dumps({
                "model": os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4"),
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.0,
                "max_tokens": 16,
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ans = data["choices"][0]["message"]["content"].strip().upper()
                if "OUT_OF_SCOPE" in ans:
                    return IntentRouteResult(
                        intent="OUT_OF_SCOPE",
                        datasource="general chat",
                        is_safe=True,
                        bypass_retrieval=True,
                        direct_response="I specialize in analyzing institutional, academic, and financial reports for higher-education and research institutions. While I cannot answer questions outside this domain, I would be glad to help you explore university governance, faculty research, department statistics, patents, or annual reports! What would you like to investigate?"
                    )
                if "GENERAL_CHAT" in ans:
                    return IntentRouteResult(
                        intent="GENERAL_CHAT",
                        datasource="general chat",
                        is_safe=True,
                        bypass_retrieval=True,
                        direct_response="Hello! How may I assist your academic and institutional research today?"
                    )
                if "FINANCIAL" in ans:
                    return IntentRouteResult(intent="FINANCIAL_FACT", datasource="graph query", is_safe=True, bypass_retrieval=False)
                if "RELATION" in ans:
                    return IntentRouteResult(intent="MULTI_HOP_RELATION", datasource="graph query", is_safe=True, bypass_retrieval=False)
                if "ACADEMIC" in ans:
                    return IntentRouteResult(intent="ACADEMIC_RESEARCH", datasource="vector search", is_safe=True, bypass_retrieval=False)
        except Exception:
            pass
        return None


# =============================================================================
# 3. NODE 2: COREFERENCE RESOLUTION & PRONOUN DISAMBIGUATION
# =============================================================================

class CoreferenceResolverNode:
    """
    Inspects thread session memory to resolve ambiguous pronouns and deictic references,
    yielding a self-contained standalone search query.
    """

    PRONOUNS = [
        r"\btheir\b", r"\bthey\b", r"\bits\b", r"\bit\b",
        r"\bthat startup\b", r"\bthat institution\b", r"\bthis university\b",
        r"\bthat project\b", r"\bthat company\b", r"\bthat department\b",
        r"\bshe\b", r"\bhe\b"
    ]

    def __init__(self, session_manager: Optional[Any] = None, vllm_url: Optional[str] = None):
        self.session_manager = session_manager
        self.vllm_url = vllm_url or os.getenv("VLLM_BASE_URL", "http://localhost:8002/v1")

    def resolve(
        self,
        query: str,
        thread_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        Returns: (standalone_query, resolved_entity)
        """
        has_pronoun = any(re.search(pat, query, re.IGNORECASE) for pat in self.PRONOUNS)
        if not has_pronoun:
            return query, None

        # 1. Check SessionMemoryManager if supplied
        if self.session_manager and thread_id:
            resolved, entity = self.session_manager.resolve_coreference(query, thread_id)
            if entity and resolved != query:
                return resolved, entity

        # 2. Check chat_history tuple list
        if chat_history:
            # Extract dominant entity from previous assistant answer or user query
            last_turn = chat_history[-1]
            last_text = last_turn.get("human", "") + " " + last_turn.get("ai", "")
            # Heuristic extraction of capitalized named entities
            candidates = re.findall(r"\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\b", last_text)
            candidates = [c for c in candidates if c not in ("Human", "AI", "Please", "What", "How", "Tell")]
            if candidates:
                dominant = candidates[0]
                resolved = query
                resolved = re.sub(r"\btheir\b", f"{dominant}'s", resolved, flags=re.IGNORECASE)
                resolved = re.sub(r"\bthey\b", dominant, resolved, flags=re.IGNORECASE)
                resolved = re.sub(r"\bits\b", f"{dominant}'s", resolved, flags=re.IGNORECASE)
                resolved = re.sub(r"\bit\b", dominant, resolved, flags=re.IGNORECASE)
                resolved = re.sub(r"\bthat startup\b", dominant, flags=re.IGNORECASE)
                resolved = re.sub(r"\bthat project\b", dominant, flags=re.IGNORECASE)
                resolved = re.sub(r"\bthat institution\b", dominant, flags=re.IGNORECASE)
                return resolved, dominant

        return query, None


# =============================================================================
# 4. NODE 3: QUERY DECOMPOSER & SPLITTER
# =============================================================================

class QueryDecomposerNode:
    """
    Decomposes multi-part or compound user queries into an array of 1 to 3
    targeted standalone sub-queries to prevent semantic vector dilution.
    """

    def __init__(self, vllm_url: Optional[str] = None):
        self.vllm_url = vllm_url or os.getenv("VLLM_BASE_URL", "http://localhost:8002/v1")

    def decompose(self, query: str) -> List[str]:
        q_clean = query.strip()

        # Check if query is actually compound
        is_compound = False
        conjunctions = [" and ", " as well as ", " along with ", "; ", "? "]
        for c in conjunctions:
            if c in q_clean.lower():
                is_compound = True
                break

        if not is_compound:
            return [q_clean]

        # 1. Attempt LLM decomposition via vLLM if available
        llm_subqueries = self._query_vllm_decomposition(q_clean)
        if llm_subqueries and len(llm_subqueries) > 1:
            return llm_subqueries[:3]

        # 2. Rule-Based Deterministic Decomposition
        parts = re.split(r"(?i)\s+(?:and|as well as|along with)\s+|;\s*|\?\s*", q_clean)
        sub_queries = [p.strip() for p in parts if p.strip() and len(p.strip()) > 8]

        if len(sub_queries) > 1:
            # Ensure each part is formatted as a coherent question
            reconstructed = []
            for idx, sq in enumerate(sub_queries[:3]):
                if not re.match(r"^(who|what|when|where|why|how|list|find)\b", sq, re.IGNORECASE):
                    reconstructed.append(f"Find details on {sq}")
                else:
                    reconstructed.append(sq if sq.endswith("?") else f"{sq}?")
            return reconstructed

        return [q_clean]

    def _query_vllm_decomposition(self, query: str) -> Optional[List[str]]:
        try:
            url = f"{self.vllm_url}/chat/completions"
            sys_msg = (
                "You are an expert query decomposition agent. Split the compound question into 1 to 3 "
                "independent, single-focus search queries. Return strictly valid JSON array of strings: "
                "[\"sub query 1\", \"sub query 2\"]. If not compound, return [\"original query\"]."
            )
            payload = json.dumps({
                "model": os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4"),
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.0,
                "max_tokens": 128,
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"].strip()
                # Extract JSON array
                match = re.search(r"\[.*\]", text, re.DOTALL)
                if match:
                    arr = json.loads(match.group(0))
                    if isinstance(arr, list) and all(isinstance(x, str) for x in arr):
                        return arr
        except Exception:
            pass
        return None


# =============================================================================
# 5. QUERY INTAKE ORCHESTRATOR
# =============================================================================

@dataclass
class QueryIntakeResult:
    original_query: str
    standalone_query: str
    decomposed_queries: List[str]
    intent_route: IntentRouteResult
    resolved_entity: Optional[str]
    telemetry: PipelineTelemetry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "standalone_query": self.standalone_query,
            "decomposed_queries": self.decomposed_queries,
            "intent": self.intent_route.intent,
            "datasource": self.intent_route.datasource,
            "is_safe": self.intent_route.is_safe,
            "bypass_retrieval": self.intent_route.bypass_retrieval,
            "direct_response": self.intent_route.direct_response,
            "resolved_entity": self.resolved_entity,
            "pipeline_stages": self.telemetry.to_list(),
        }


class QueryIntakeEngine:
    """
    Orchestrates the entire Query Intake & Reformulation pipeline:
    1. Telemetry start (RECEIVED)
    2. Intent Routing & Firewall (ROUTING)
    3. Coreference Resolution (COREFERENCE_RESOLUTION)
    4. Query Decomposition (QUERY_DECOMPOSITION)
    """

    def __init__(self, session_manager: Optional[Any] = None):
        self.session_manager = session_manager
        self.router = IntentRouterNode()
        self.coref = CoreferenceResolverNode(session_manager=session_manager)
        self.decomposer = QueryDecomposerNode()

    def process(
        self,
        query: str,
        thread_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> QueryIntakeResult:
        telemetry = PipelineTelemetry()

        # Step 1: Intent Routing & Out-of-Scope Firewall
        telemetry.start_stage("ROUTING")
        route_res = self.router.route(query)
        telemetry.complete_stage("ROUTING", f"Classified as {route_res.intent} -> {route_res.datasource}")

        # If Out-of-Scope or General Chat, skip database lookups
        if route_res.bypass_retrieval:
            telemetry.skip_stage("COREFERENCE_RESOLUTION", "Zero-DB bypass for out-of-scope/chat")
            telemetry.skip_stage("QUERY_DECOMPOSITION", "Zero-DB bypass for out-of-scope/chat")
            telemetry.skip_stage("VECTOR_RETRIEVAL", "Bypassed")
            telemetry.skip_stage("BM25_RETRIEVAL", "Bypassed")
            telemetry.skip_stage("GRAPH_RETRIEVAL", "Bypassed")
            telemetry.skip_stage("FUSION", "Bypassed")
            telemetry.skip_stage("RERANKING", "Bypassed")
            telemetry.start_stage("SYNTHESIS")
            telemetry.complete_stage("SYNTHESIS", "Direct general response generated")
            telemetry.complete_stage("COMPLETED", "Bypass flow completed")

            return QueryIntakeResult(
                original_query=query,
                standalone_query=query,
                decomposed_queries=[query],
                intent_route=route_res,
                resolved_entity=None,
                telemetry=telemetry,
            )

        # Step 2: Coreference Resolution
        telemetry.start_stage("COREFERENCE_RESOLUTION")
        standalone, dominant_ent = self.coref.resolve(query, thread_id=thread_id, chat_history=chat_history)
        telemetry.complete_stage(
            "COREFERENCE_RESOLUTION",
            f"Resolved: '{query}' -> '{standalone}'" if dominant_ent else "No pronoun ambiguity"
        )

        # Step 3: Query Decomposition
        telemetry.start_stage("QUERY_DECOMPOSITION")
        decomposed = self.decomposer.decompose(standalone)
        telemetry.complete_stage(
            "QUERY_DECOMPOSITION",
            f"Split into {len(decomposed)} sub-queries: {decomposed}"
        )

        return QueryIntakeResult(
            original_query=query,
            standalone_query=standalone,
            decomposed_queries=decomposed,
            intent_route=route_res,
            resolved_entity=dominant_ent,
            telemetry=telemetry,
        )
