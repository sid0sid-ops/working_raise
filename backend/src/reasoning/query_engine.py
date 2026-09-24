"""
RAISE Query Engine: Multi-Hop Query Agent
Author: Principal AI Architect / Senior Python Engineer
Description: Decomposes complex multi-hop queries into a dependency graph, 
executes searches sequentially, and resolves intermediate entity variables.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional
from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger("raise.query_engine")


# ==========================================
# 1. PYDANTIC SCHEMAS FOR STRUCTURED OUTPUTS
# ==========================================

class SubQueryStep(BaseModel):
    hop_id: str = Field(..., description="Unique identifier for the hop, e.g., 'hop_1', 'hop_2'")
    query_template: str = Field(
        ..., 
        description="Atomic search query template. May contain placeholder tokens referencing prior hops, e.g., '{hop_1_entity}'"
    )
    description: str = Field(..., description="Explanation of what specific information this sub-query aims to retrieve")
    depends_on: List[str] = Field(default_factory=list, description="List of hop_ids that this step depends on")


class QueryPlan(BaseModel):
    steps: List[SubQueryStep] = Field(..., description="Ordered sequence of atomic steps required to resolve the complex query")


class EntityExtractionResult(BaseModel):
    extracted_entity: str = Field(
        ..., 
        description="The precise entity name, value, or answer extracted from the retrieved context to resolve the sub-query"
    )
    rationale: str = Field(..., description="Brief explanation of how the entity was extracted from the provided document context")


class MultiHopStepTrace(BaseModel):
    hop_id: str
    query: str
    description: str
    extracted_entity: str
    rationale: str = ""
    retrieved_chunk_ids: List[str] = Field(default_factory=list)


class MultiHopExecutionResult(BaseModel):
    all_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    prioritized_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    resolved_variables: Dict[str, str] = Field(default_factory=dict)
    execution_trace: List[MultiHopStepTrace] = Field(default_factory=list)
    plan: Optional[QueryPlan] = None


# ==========================================
# 2. SYSTEM PROMPTS
# ==========================================

DECOMPOSITION_SYSTEM_PROMPT = """You are an expert AI Query Planner for an advanced GraphRAG system.
Your objective is to analyze complex, multi-hop riddles, questions, or prompts and break them down into an ordered, sequential execution plan of atomic search steps.

Guidelines:
1. Break multi-clause questions into sequential single-entity or single-fact lookup steps.
2. For composite or nested references (e.g. "X's mother", "the second assassinated president's mother's maiden name", "the 15th first lady's mother", "the vocalist of the band that made album Y"), ALWAYS split into two atomic hops:
   - Hop A: Identify the bridge entity itself (e.g. "15th first lady of the United States", "second assassinated president of the United States", "third studio album of Dismal Euphony").
   - Hop B: Retrieve the target attribute using the bridge placeholder (e.g. "{hop_1_entity} mother", "{hop_3_entity} mother maiden name", "record label that produced {hop_1_entity}").
   NEVER combine the title/description and the attribute in a single search phrase.
3. For hypothetical, comparative, or imaginary entities (e.g. "Imagine there is a building called Bronte tower whose height in feet is the same number as the dewey decimal classification for... Where would this building rank...?"), DO NOT search for the imaginary entity name ("Bronte tower"). Instead, resolve the underlying real attributes and retrieve the reference ranking table or list for comparison.
4. When a query asks for the "last time", "most recent", or "latest" occurrence of an event (e.g. "the last time the UEFA Champions League was won by a club from London"), ensure the sub-query explicitly seeks the "most recent / last year or season" rather than a generic year.
5. Use placeholder tokens like {hop_1_entity}, {hop_2_entity} in subsequent query templates where upstream information is required.
6. Keep the search query short and specific for BM25 and Vector search. Do NOT include final synthesis steps or full-sentence questions as search hops.
7. Keep the number of hops minimal and strictly necessary.

Examples:
Example 1:
User: "If my future wife has the same first name as the 15th first lady of the United States' mother and her surname is the same as the second assassinated president's mother's maiden name, what is my future wife's name?"
Assistant Plan:
- hop_1: query_template="15th first lady of the United States", description="Find the 15th first lady."
- hop_2: query_template="{hop_1_entity} mother", description="Find the mother of the 15th first lady to get her first name.", depends_on=["hop_1"]
- hop_3: query_template="second assassinated president of the United States", description="Find the second assassinated president."
- hop_4: query_template="{hop_3_entity} mother maiden name", description="Find the maiden name of the mother of the second assassinated president.", depends_on=["hop_3"]

Example 2:
User: "What is the name of the vocalist from the first band to make it in the top 200 under the record label that produced the third studio album for Dismal Euphony?"
Assistant Plan:
- hop_1: query_template="third studio album of Dismal Euphony", description="Find the third studio album of Dismal Euphony."
- hop_2: query_template="record label for {hop_1_entity}", description="Find the record label that produced that album.", depends_on=["hop_1"]
- hop_3: query_template="first band in top 200 under {hop_2_entity}", description="Find the first band to chart under that record label.", depends_on=["hop_2"]
- hop_4: query_template="vocalist of {hop_3_entity}", description="Find the vocalist of that band.", depends_on=["hop_3"]

Example 3:
User: "As of August 1, 2024, which country were holders of the FIFA World Cup the last time the UEFA Champions League was won by a club from London?"
Assistant Plan:
- hop_1: query_template="clubs from London UEFA Champions League winners", description="Find the clubs from London that have won the UEFA Champions League."
- hop_2: query_template="UEFA Champions League winners seasons list {hop_1_entity}", description="Find the most recent / last year or season {hop_1_entity} won the UEFA Champions League.", depends_on=["hop_1"]
- hop_3: query_template="FIFA World Cup winners champions list {hop_2_entity}", description="Find the reigning FIFA World Cup holders as of the year {hop_2_entity}.", depends_on=["hop_2"]

Example 4:
User: "Imagine there is a building called Bronte tower whose height in feet is the same number as the dewey decimal classification for the Charlotte Bronte book that was published in 1847. Where would this building rank among tallest buildings in New York City, as of August 2024?"
Assistant Plan:
- hop_1: query_template="Charlotte Bronte novel published in 1847", description="Find the Charlotte Bronte book published in 1847."
- hop_2: query_template="{hop_1_entity} Dewey Decimal classification", description="Find the Dewey Decimal classification for {hop_1_entity}.", depends_on=["hop_1"]
- hop_3: query_template="Table of tallest buildings in New York City height rank", description="Retrieve the ranking table of tallest buildings in New York City with heights in feet.", depends_on=["hop_2"]
"""

EXTRACTION_SYSTEM_PROMPT = """You are an expert Information Extraction and Entity Resolution agent.
Given an atomic sub-query and the retrieved document context, your task is to extract the single precise entity, name, date, or fact requested by the sub-query.

Guidelines:
1. Be extremely concise and accurate. Do not write full sentences in your extracted_entity output unless the entity itself is a phrase (e.g. "Harriet Lane", "James A. Garfield", "Jane", "Ballou", "Jens Kidman").
2. TEMPORAL SUPERLATIVES & MOST RECENT DATES: When a sub-query asks for the "last", "most recent", or "latest" year, season, or tournament won by an entity, scan the entire context and all table rows to find the MAXIMUM / MOST RECENT year or date (e.g. if an entity won in 2012 and 2021, the last time was 2021, NOT 2012).
3. STRUCTURED TABLES: When tables appear with rows or columns, scan all rows carefully.
4. If the exact answer is not present in the context, extract the closest matching proxy entity or state "UNKNOWN".
5. Provide a clear, concise rationale referencing the retrieved text.
"""


# ==========================================
# 3. MULTI-HOP QUERY AGENT
# ==========================================

class MultiHopQueryAgent:
    """
    Agent responsible for breaking down complex multi-hop prompts, executing
    sequential hybrid search steps, and resolving intermediate entities.
    """

    def __init__(
        self,
        search_func: Callable[[str], List[Dict[str, Any]]],
        model_name: str = "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4",
        vllm_url: Optional[str] = None,
        openai_client: Optional[OpenAI] = None,
    ):
        """
        Args:
            search_func: Injected hybrid search function taking a query string and returning retrieved chunk dictionaries.
            model_name: Model identifier supporting chat completions.
            vllm_url: Optional vLLM base URL (defaults to http://127.0.0.1:8002/v1).
            openai_client: Optional pre-configured OpenAI client instance.
        """
        self.search_func = search_func
        self.model_name = model_name
        base_url = vllm_url or "http://127.0.0.1:8002/v1"
        self.client = openai_client or OpenAI(base_url=base_url, api_key="EMPTY")

    def decompose_query(self, complex_query: str) -> QueryPlan:
        """Step 1: Decompose complex query into a sequential dependency plan."""
        logger.info("Decomposing complex query into sequential execution plan...")

        # Primary: client.beta.chat.completions.parse
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": DECOMPOSITION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Complex Query: {complex_query}"},
                ],
                response_format=QueryPlan,
                temperature=0.0,
            )
            plan = response.choices[0].message.parsed
            if plan and plan.steps:
                logger.info(f"Successfully generated execution plan with {len(plan.steps)} hops via structured parse.")
                return plan
        except Exception as e:
            logger.warning(f"beta.chat.completions.parse failed ({e}), falling back to json_object...")

        # Secondary fallback: json_object
        schema_str = json.dumps(QueryPlan.model_json_schema())
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": f"{DECOMPOSITION_SYSTEM_PROMPT}\nOutput JSON matching:\n{schema_str}"},
                {"role": "user", "content": f"Complex Query: {complex_query}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = response.choices[0].message.content or "{}"
        plan = QueryPlan.model_validate_json(content)
        logger.info(f"Successfully generated execution plan with {len(plan.steps)} hops via json_object.")
        return plan

    def extract_entity(self, sub_query: str, context: str) -> EntityExtractionResult:
        """Step 2 & 3: Extract precise entity/answer from retrieved document context."""
        prompt = f"Sub-Query: {sub_query}\n\nRetrieved Document Context:\n{context}"

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format=EntityExtractionResult,
                temperature=0.0,
            )
            result = response.choices[0].message.parsed
            if result:
                logger.info(f"Extracted Entity -> '{result.extracted_entity}' (Rationale: {result.rationale})")
                return result
        except Exception as e:
            logger.warning(f"Structured entity extraction failed ({e}), falling back to json_object...")

        # Secondary fallback: json_object
        schema_str = json.dumps(EntityExtractionResult.model_json_schema())
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": f"{EXTRACTION_SYSTEM_PROMPT}\nOutput JSON matching:\n{schema_str}"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = response.choices[0].message.content or "{}"
        result = EntityExtractionResult.model_validate_json(content)
        logger.info(f"Extracted Entity via fallback -> '{result.extracted_entity}'")
        return result

    def execute(self, complex_query: str) -> MultiHopExecutionResult:
        """
        Executes the full multi-hop retrieval loop:
        Decomposition -> Iterative Search -> Entity Extraction -> Context Compilation.
        """
        plan = self.decompose_query(complex_query)
        resolved_variables: Dict[str, str] = {}
        all_chunks: List[Dict[str, Any]] = []
        prioritized_chunks: List[Dict[str, Any]] = []
        execution_trace: List[MultiHopStepTrace] = []
        seen_chunk_ids = set()
        step_chunks_by_hop: Dict[str, List[Dict[str, Any]]] = {}

        for step in plan.steps:
            logger.info(f"--- Executing Step [{step.hop_id}]: {step.description} ---")

            # Format query template with resolved upstream entities
            query = step.query_template
            try:
                query = query.format(**resolved_variables)
            except KeyError as e:
                logger.warning(f"Template formatting KeyError {e} on query '{query}'. Applying fallback substitution.")
                for key, val in resolved_variables.items():
                    query = query.replace(f"{{{key}}}", val)

            logger.info(f"Formatted Search Query: '{query}'")

            # Execute hybrid search via dependency injection
            step_chunks = self.search_func(query)

            # Record chunks into all_chunks
            for c in step_chunks:
                cid = c.get("chunk_id")
                if cid and cid not in seen_chunk_ids:
                    seen_chunk_ids.add(cid)
                    all_chunks.append(c)

            # Assemble step context for entity extraction (top 5 chunks)
            step_context_blocks = []
            step_chunk_ids = []
            for c in step_chunks[:5]:
                doc_name = c.get("document") or c.get("title") or "Source"
                sec_name = c.get("section") or c.get("heading") or "Overview"
                txt = c.get("text") or c.get("plain_text") or ""
                step_context_blocks.append(f"[{doc_name} | Section: {sec_name}]\n{txt}")
                if c.get("chunk_id"):
                    step_chunk_ids.append(c["chunk_id"])

            step_context = "\n\n".join(step_context_blocks)

            # Extract entity for downstream hops
            extraction = self.extract_entity(query, step_context)
            extracted_entity = extraction.extracted_entity.strip().strip('"').strip("'")

            # Register resolved variables in multiple naming conventions
            resolved_variables[step.hop_id] = extracted_entity
            resolved_variables[f"{step.hop_id}_entity"] = extracted_entity
            resolved_variables[f"{step.hop_id}_desc"] = step.description

            step_chunks_by_hop[step.hop_id] = list(step_chunks[:5])

            execution_trace.append(
                MultiHopStepTrace(
                    hop_id=step.hop_id,
                    query=query,
                    description=step.description,
                    extracted_entity=extracted_entity,
                    rationale=extraction.rationale,
                    retrieved_chunk_ids=step_chunk_ids,
                )
            )

        # Interleave prioritized chunks across all hops so every hop has fair representation
        max_depth = max((len(chks) for chks in step_chunks_by_hop.values()), default=0)
        seen_prio_cids = set()
        for depth in range(max_depth):
            for hop_id in [s.hop_id for s in plan.steps]:
                h_chks = step_chunks_by_hop.get(hop_id, [])
                if depth < len(h_chks):
                    chk = h_chks[depth]
                    cid = chk.get("chunk_id")
                    if cid and cid not in seen_prio_cids:
                        seen_prio_cids.add(cid)
                        prioritized_chunks.append(chk)

        # Check if the plan requires deterministic mathematical/temporal operations
        if hasattr(plan, "operators") and plan.operators:
            from src.reasoning.operators import UnifiedOperatorEngine
            for op in plan.operators:
                logger.info(f"Executing deterministic operator: {op.type}")
                op_inputs = [
                    resolved_variables.get(f"{var}_entity", resolved_variables.get(var, var))
                    for var in op.inputs
                ]
                op_result = UnifiedOperatorEngine.execute(
                    operator_name=op.type,
                    operands=op_inputs,
                )
                resolved_variables[op.output_var] = str(op_result.result)
                resolved_variables[f"{op.output_var}_entity"] = str(op_result.result)
                execution_trace.append(
                    MultiHopStepTrace(
                        hop_id=op.id,
                        query=f"CALCULATE {op.type}",
                        description=op_result.explanation,
                        extracted_entity=str(op_result.result),
                    )
                )

        return MultiHopExecutionResult(
            all_chunks=all_chunks,
            prioritized_chunks=prioritized_chunks,
            resolved_variables=resolved_variables,
            execution_trace=execution_trace,
            plan=plan,
        )
