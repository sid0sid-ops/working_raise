# RAISE Failure Taxonomy & Forensic Classification System

**Document Status**: AUTHORITATIVE TAXONOMY  
**Version**: 1.0.0  
**Categories**: 23 Exhaustive Root Causes  
**Classification Protocol**: Question-by-Question Deep Trace  

---

## 1. Overview & Classification Mandate

A benchmark that merely outputs a single aggregate score or labels a question as `"WRONG"` is useless for engineering progress. 

In the RAISE evaluation framework, every failed question must be assigned an immutable, machine-readable diagnosis detailing:
- `root_cause`: Primary systemic breakdown leading to the failure.
- `secondary_cause`: Contributing downstream or upstream defect.
- `affected_component`: The exact file, class, or substrate responsible.
- `trace_stage`: Point in the LangGraph workflow where the correct evidence or reasoning was lost.
- `failure_evidence`: Concrete token, chunk ID, Cypher query, or NLI score demonstrating the breakdown.
- `recommended_fix`: Precise architectural or algorithmic correction.
- `confidence`: Evaluator certainty score $[0.0, 1.0]$.

---

## 2. The 23 Exhaustive Failure Categories

### 2.1 Retrieval & Extraction Failures

#### 1. `RETRIEVAL_MISS`
- **Definition**: The gold supporting passage was not retrieved by **any** substrate (Dense Vector, BM25, or Neo4j Subgraph) in the candidate pool ($K \le 50$).
- **Detection Rule**: Gold passage ID $\notin$ `vector_candidates` $\land$ Gold passage ID $\notin$ `bm25_candidates` $\land$ Gold passage ID $\notin$ `graph_candidates`.
- **Affected Component**: `LocalVectorEngine` (ChromaDB), `SelfContainedBM25`, or `Neo4jDatabase`.
- **Remediation**: Adjust embedding model, tune BM25 tokenization/stop words, or expand document ingestion chunking.

#### 2. `WRONG_TOP_K`
- **Definition**: The gold passage was successfully retrieved in the broad candidate pool ($K \le 50$), but failed to reach the top-$K$ cutoff passed to fusion or reranking.
- **Detection Rule**: Gold passage ID $\in \text{Candidates}_{50} \land \text{Rank}_{\text{RRF}} > K_{\text{fusion\_cutoff}}$.
- **Affected Component**: `reciprocal_rank_fusion()` or substrate candidate weighting.
- **Remediation**: Increase initial retrieval $K$, adjust RRF $k$ constant, or enhance dynamic table/entity intent boosts.

#### 3. `RERANKER_ERROR`
- **Definition**: The gold passage was present in the top candidates before reranking, but the cross-encoder suppressed or demoted it below the context injection threshold (False Suppression), or promoted an irrelevant chunk ahead of it (False Promotion).
- **Detection Rule**: $\text{Rank}_{\text{pre\_rerank}} \le 8 \land \text{Rank}_{\text{post\_rerank}} > 8$.
- **Affected Component**: `CrossEncoderReranker` (`BAAI/bge-reranker-large`).
- **Remediation**: Calibrate cross-encoder score thresholds, fine-tune reranker on academic/financial pairs, or apply length normalization.

#### 4. `CHUNK_FRAGMENTATION`
- **Definition**: The gold evidence required to answer the question spans a boundary split created by the chunker, so neither individual chunk contains sufficient semantic context to be answerable.
- **Detection Rule**: Gold evidence sentence split across $\text{Chunk}_A$ and $\text{Chunk}_B$, with token distance across boundary.
- **Affected Component**: GGAHC 8-stage chunking pipeline (`HierarchicalChunkAssembler`, `SemanticBoundaryDetector`).
- **Remediation**: Activate parent macro-chunk retrieval, adjust community boundary cohesion thresholds, or enforce table-preserving blocks.

---

### 2.2 Knowledge Graph & Cypher Failures

#### 5. `ENTITY_LINKING_ERROR`
- **Definition**: Named entities mentioned in the query (e.g., *"National Institute of Plant Genome Research"*, *"BIRAC"*, *"Dr. Subhra Chakraborty"*) failed to resolve to valid canonical nodes in the Neo4j database.
- **Detection Rule**: Query contains recognizable entity $E$, but `seed_node_ids == []` or mapped to unrelated entity.
- **Affected Component**: `QueryIntakeEngine`, `AcademicDomainExtractor`, or entity normalization index.
- **Remediation**: Implement Levenshtein/Jaro-Winkler fuzzy entity resolution and expand alias dictionary in `ingested_manifest.json`.

#### 6. `GRAPH_PATH_MISSING`
- **Definition**: The entities exist in Neo4j, but the relationship or multi-hop edge connecting them was not extracted during ingestion or was pruned during graph filtering.
- **Detection Rule**: $\text{Entity}_A \in V(G) \land \text{Entity}_B \in V(G)$, but shortest path length $= \infty$ or edge type missing.
- **Affected Component**: Ingestion triple extractor (`academic_extractor.py`) or `filter_subgraph_entity_mismatches()`.
- **Remediation**: Expand relationship schema extraction patterns and prevent aggressive institutional boundary pruning.

#### 7. `CYPHER_GENERATION_ERROR`
- **Definition**: The `text_to_cypher_generator` node synthesized invalid Cypher syntax or queried relationship types / properties that do not exist in the Neo4j schema.
- **Detection Rule**: Neo4j driver raises `CypherSyntaxError` or returns empty results due to fictitious label/relationship name.
- **Affected Component**: `AcademicGraphRAGWorkflow._text_to_cypher_generator_node`.
- **Remediation**: Inject verified Neo4j schema labels into generation prompt; enforce few-shot Cypher templates.

#### 8. `CYPHER_EXECUTION_ERROR`
- **Definition**: Cypher syntax was valid, but execution failed due to database timeouts, constraint violations, memory limits, or driver disconnects.
- **Detection Rule**: Neo4j Bolt driver throws `ServiceUnavailable`, `TransientError`, or execution exceeds 5.0s timeout.
- **Affected Component**: `Neo4jDatabase.run_cypher()` connection pool.
- **Remediation**: Tune Neo4j Bolt connection pool size, optimize indexed lookups, and ensure transaction isolation.

---

### 2.3 Query Planning & Multi-Hop Reasoning Failures

#### 9. `QUERY_DECOMPOSITION_ERROR`
- **Definition**: A complex multi-hop or comparative query was either not decomposed or was decomposed into erroneous sub-queries that lost critical entity constraints.
- **Detection Rule**: Multi-hop query ($H \ge 2$) received 0 sub-queries, or sub-query generated missing target institution.
- **Affected Component**: `QueryIntakeEngine.decompose_subqueries()`.
- **Remediation**: Enhance multi-hop intent classification and prompt decomposition with structured dependency trees.

#### 10. `CONTEXT_TRUNCATION`
- **Definition**: Relevant chunks and graph nodes were retrieved, but were truncated or omitted from the final prompt due to strict context window limits.
- **Detection Rule**: Gold passage $\in$ `top_chunks`, but passage text absent from formatted LLM synthesis prompt.
- **Affected Component**: `_fusion_and_response_synthesis_node` prompt formatter or `MAX_TOKENS` budget.
- **Remediation**: Apply dynamic token budgeting, hierarchical parent/child summarization, or structured table serialization.

#### 11. `CONTEXT_ORDERING_ERROR`
- **Definition**: The critical evidence was present in the prompt, but was positioned in the middle of a lengthy context, causing the LLM to overlook it ("Lost in the Middle").
- **Detection Rule**: Gold passage present at context position index $[40\% - 70\%]$, and LLM outputs hallucination or abstention.
- **Affected Component**: Context assembly sort order in `fusion_and_response_synthesis`.
- **Remediation**: Sort evidence with highest-similarity and tabular chunks at the very beginning and very end of the prompt context.

---

### 2.4 Synthesis & Generation Failures

#### 12. `GENERATION_ERROR`
- **Definition**: All required evidence was present in the context in optimal positions, but the LLM synthesized an incorrect, incomplete, or logically invalid answer.
- **Detection Rule**: Context contains complete explicit answer, but normalized generated answer Token F1 $< 0.40$ or EM $= 0$.
- **Affected Component**: Active LLM (`llama-3.3-70b-versatile` / `Qwen2.5-14B`) or prompt instruction contract.
- **Remediation**: Refine synthesis system prompt, enforce chain-of-thought scratchpad, or adjust decoding temperature.

#### 13. `NUMERIC_ERROR`
- **Definition**: The model reported an incorrect number, miscalculated a total, misread a table column, or mixed up fiscal years (e.g., 2023-24 vs 2022-23).
- **Detection Rule**: Extracted numbers in generated answer $\ne$ gold numbers in source table matrix.
- **Affected Component**: `TableIntegrityEngine`, `DeterministicMathEngine`, or LLM table reader.
- **Remediation**: Direct numerical queries to `DeterministicMathEngine` with IEEE-754 verified arithmetic over table cells.

#### 14. `CITATION_ERROR`
- **Definition**: The model produced a correct or plausible answer, but cited a non-existent page, the wrong document, or a chunk that did not contain the supporting assertion.
- **Detection Rule**: Inline citation `[Doc, Page N]` does not contain the claimed proposition, or page index is out of bounds.
- **Affected Component**: `CitationValidator` or synthesis citation prompt format.
- **Remediation**: Bind citation tags strictly to verified chunk metadata IDs before emitting final answer.

---

### 2.5 Verification & Quality Gate Failures

#### 15. `VERIFICATION_FALSE_ACCEPT`
- **Definition**: The model generated an ungrounded or hallucinated claim, but the Runtime Quality Gate mistakenly marked it as verified ($\text{Score} \ge 0.80$).
- **Detection Rule**: Gold truth indicates false claim, but `quality_gate_decision == 'ACCEPT'`.
- **Affected Component**: `FineCatNLIVerifier` / `ModernBERT-Large` NLI engine.
- **Remediation**: Tighten entailment threshold ($P(E) \ge 0.70$), lower contradiction tolerance ($P(C) < 0.10$).

#### 16. `VERIFICATION_FALSE_REJECT`
- **Definition**: The model synthesized a completely correct, well-grounded answer from the source text, but the Quality Gate erroneously classified it as unverified and triggered an unnecessary retry or refusal.
- **Detection Rule**: Answer is objectively correct, but `quality_gate_decision == 'RETRY'` or `'UNABLE_TO_VERIFY'`.
- **Affected Component**: `FineCatNLIVerifier` claim parsing or token-level entailment fallback.
- **Remediation**: Implement atomic claim splitting to prevent multi-clause rejection; improve numerical normalization in NLI.

#### 17. `UNNECESSARY_ABSTENTION`
- **Definition**: The system returned `"INSUFFICIENT_EVIDENCE"` or refused to answer, even though the active corpus contained the necessary information.
- **Detection Rule**: Gold passage exists in ingested documents $\land$ answer text contains refusal keywords.
- **Affected Component**: `_unverified_responder_node` or over-conservative quality gate threshold.
- **Remediation**: Calibrate retry loop to attempt targeted secondary retrieval before triggering terminal refusal.

#### 18. `UNSUPPORTED_ANSWER`
- **Definition**: Critical safety failure: The system asserted a factual answer without having retrieved the supporting evidence, fabricating facts from LLM parametric memory.
- **Detection Rule**: Answer contains concrete factual claims $\land$ claim support rate $< 0.30 \land$ question is an unanswerable trap.
- **Affected Component**: Primary LLM bypass of evidence constraints + quality gate leak.
- **Remediation**: Enforce strict refusal contract in system prompt; block answer output if zero citations are verified.

---

### 2.6 Memory & Caching Failures

#### 19. `MEMORY_MISS`
- **Definition**: A multi-turn conversational query referred to an entity or fact established in a prior turn (e.g., *"What was its total revenue?"*), but the system failed to retrieve or bind the antecedent from PostgreSQL or Redis.
- **Detection Rule**: Coreference resolution left pronoun unbound or resolved to wrong antecedent despite prior turn history.
- **Affected Component**: `PostgresManager`, `RedisCacheManager.get_session_messages()`, or `QueryIntakeEngine.coref`.
- **Remediation**: Fix session history sliding-window retrieval and ensure dual-key (`text` and `content`) compatibility.

#### 20. `MEMORY_CONTAMINATION`
- **Definition**: Context or entities from an earlier, unrelated evaluation session leaked into the current session, causing biased retrieval or hallucinatory answers.
- **Detection Rule**: Generated answer mentions entity from Session $A$ while executing in Session $B$.
- **Affected Component**: Cross-session memory isolation in `session_metadata` or Redis key namespaces.
- **Remediation**: Strictly enforce unique `eval:{run_id}:*` namespaces and isolate session IDs per benchmark case.

#### 21. `CACHE_CONTAMINATION`
- **Definition**: A stale query completion cached in Redis from a previous run or different configuration was mistakenly served for a new run with differing parameters.
- **Detection Rule**: Redis Cache HIT occurs when model, prompt, or corpus configuration hash does not match current run.
- **Affected Component**: `RedisCacheManager._make_completion_key()`.
- **Remediation**: Include full configuration hash (corpus manifest, embedding model, LLM model, prompt version) in cache key.

---

### 2.7 Infrastructure & System Failures

#### 22. `SYSTEM_FAILURE`
- **Definition**: An unhandled exception crashed the execution (e.g., database connection reset, Out-Of-Memory, missing environment variable).
- **Detection Rule**: Python stack trace raised; case status marked as `'ERROR'`.
- **Affected Component**: Docker stack, driver wrapper, or host OS environment.
- **Remediation**: Wrap node execution with safe fallbacks and persistent error logging.

#### 23. `TIMEOUT`
- **Definition**: Query execution exceeded the maximum allowed latency budget ($> 60.0$ seconds for full LangGraph run).
- **Detection Rule**: Execution duration $\ge 60,000\text{ ms}$.
- **Affected Component**: Subgraph traversal, cross-encoder reranker inference, or LLM API timeout.
- **Remediation**: Implement per-stage async timeouts with graceful degradation to dense vector fallback.

---

## 3. Standard Forensic Failure Report Format

For every identified failure case, the evaluation runner must record a structured card matching this standard format:

```text
================================================================================
FAILURE CARD: {case_id}
================================================================================
Failure ID:             FAIL-{run_id}-{question_id}
Dataset:                {dataset} (Split: {split})
Question ID:            {question_id}
Question:               {question_text}

Expected Answer:        {gold_answer}
RAISE Answer:           {generated_answer}

Expected Evidence:      {gold_evidence_summary}
Retrieved Evidence:     {retrieved_evidence_summary}

Correct Evidence Present? {YES / NO}
Highest Relevant Rank:   {highest_rank}

Substrate Ranks:
  - Vector Rank:        {rank_vector}
  - BM25 Rank:          {rank_bm25}
  - Graph Rank:         {rank_graph}
  - RRF Rank:           {rank_rrf}
  - Reranker Rank:      {rank_reranked}

Failure Stage:          {trace_stage}
Root Cause:             {root_cause}
Secondary Cause:        {secondary_cause}
Affected Component:     {affected_component}

Why Current Architecture Failed:
  {detailed_engineering_explanation}

Proposed Fix:
  {actionable_code_or_config_fix}

Expected Effect:        {expected_metric_delta}
Risk:                   {potential_regression_risk}
Verification Plan:      {verification_test_command}
================================================================================
```
