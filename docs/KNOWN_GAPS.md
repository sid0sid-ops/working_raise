# RAISE Critical System Gap Analysis & Technical Debt Ledger

**Version**: 2.5.0  
**Status**: CANONICAL & AUTHORITATIVE  
**Verification Date**: 2026-09-14  

---

## 1. Overview

This document provides the exhaustive diagnostic analysis of **why multi-hop questions in the Google Research FRAMES benchmark fail or trigger controlled abstentions**, covering the 14 critical pipeline dimensions audited across the codebase.

---

## 2. The 14 Critical FRAMES Failure Dimensions

### 1. Entity Resolution
- **Status**: `PARTIAL`
- **Actual File**: `RAG/evaluation/benchmarks/frames/runners/runner.py`
- **Actual Function**: `prepare_evaluation_corpus()` (lines 240-248)
- **What Works**: Identifies Wikipedia article titles that appear as exact substrings in other articles.
- **What Is Broken**: Fails when entities use aliases, acronyms, nicknames, or alternate name orders (e.g. *"Emperor Guangxu"* vs *"Zaitian"*, or *"Warner Music"* vs *"Warner Music Group"*). Zero coreference resolution across sentences.
- **What Is Missing**: Entity linking model or alias registry mapping surface mentions to canonical entity IDs.
- **Dependencies**: `spacy` / Wikipedia redirect APIs.
- **Next Required Fix**: Query the MediaWiki redirect API and include redirect titles as entity aliases.

---

### 2. Graph Seed Selection
- **Status**: `PARTIAL`
- **Actual File**: `RAG/evaluation/benchmarks/frames/isolation/harness.py`
- **Actual Function**: `retrieve_graph_only()` (lines 246-253)
- **What Works**: Matches capitalized tokens and 4-digit years from the question against graph node names.
- **What Is Broken**: Fails when query entities contain lowercase keywords, multi-word phrases, or subtle entity mentions (e.g. *"the premier of France in 1968"* fails to seed *"Georges Pompidou"*).
- **What Is Missing**: Embedding-based or BM25-based entity linking to retrieve graph seeds based on semantic proximity.
- **Dependencies**: ChromaDB node index or fast TF-IDF entity matcher.
- **Next Required Fix**: Run BM25 search over graph node labels to select seeds rather than regex capitalized tokens.

---

### 3. Graph Relation Quality
- **Status**: `BROKEN / HEURISTIC`
- **Actual File**: `RAG/evaluation/benchmarks/frames/isolation/harness.py`
- **Actual Function**: `ingest_evaluation_passages()` (lines 180-187)
- **What Works**: Creates edges when one article mentions another.
- **What Is Broken**: Edges are completely uninformative. There is no relationship taxonomy; all connections are labeled `MENTIONS` or `RELATED_TO`.
- **What Is Missing**: Predicate typing (e.g. `BORN_IN`, `EDUCATED_AT`, `DIRECTED_BY`, `TENURE_YEAR`).
- **Dependencies**: LLM OpenIE triplet extractor or Wikidata entity relations.
- **Next Required Fix**: Ingest Wikipedia infobox key-value pairs as typed edges rather than raw text co-occurrences.

---

### 4. `MENTIONS` vs. Semantic/Typed Relationships
- **Status**: `UNSUPPORTED IN BENCHMARK`
- **Actual File**: `RAG/evaluation/benchmarks/frames/isolation/harness.py`
- **Actual Function**: `retrieve_graph_only()`
- **What Works**: Production campus graph has rich typed predicates (`INCUBATED`, `AWARDED_TO`, `AFFILIATED_WITH`).
- **What Is Broken**: The benchmark evaluation sandbox generates only co-occurrence `MENTIONS` edges. The graph cannot filter by relationship semantics (e.g. "find the spouse of X").
- **What Is Missing**: Predicate-aware path traversal.
- **Dependencies**: Wikidata API or structured Wikipedia infobox extraction.
- **Next Required Fix**: Parse Wikipedia infobox tables into typed relational triples during corpus preparation.

---

### 5. Multi-Hop Planning
- **Status**: `DISCONNECTED`
- **Actual File**: `RAG/src/features/memory/reasoning.py` (Production) vs `RAG/evaluation/benchmarks/frames/runners/runner.py` (Benchmark)
- **Actual Function**: `decompose_query()` vs `execute_question()`
- **What Works**: `MultiHopReasoningEngine` in `src/features/memory/reasoning.py` knows how to split complex questions into sub-queries.
- **What Is Broken**: In the FRAMES benchmark runner, `reasoning.py` is **disconnected**. The harness attempts single-turn retrieval with static 2-hop graph expansion.
- **What Is Missing**: An active multi-turn agent loop where hop $N+1$ is generated from intermediate facts gathered at hop $N$.
- **Dependencies**: `LangGraph` agent workflow connected to `IsolatedFramesHarness`.
- **Next Required Fix**: Wire `src/features/agent/workflow.py` directly into the FRAMES execution harness.

---

### 6. Hop-by-Hop Evidence Resolution
- **Status**: `MISSING`
- **Actual File**: `RAG/evaluation/benchmarks/frames/isolation/harness.py`
- **Actual Function**: `retrieve_hybrid()`
- **What Works**: Gathers top-k candidates upfront in a single pass.
- **What Is Broken**: If the bridge entity connecting Document A to Document B is not mentioned in the original question, Document B cannot be retrieved on hop 1.
- **What Is Missing**: Sequential retrieval loop: Query $ightarrow$ Retrieve Hop 1 $ightarrow$ Extract Bridge Entity $ightarrow$ Formulate Query 2 $ightarrow$ Retrieve Hop 2.
- **Dependencies**: LangGraph cyclic execution.
- **Next Required Fix**: Implement an iterative 2-step retrieval loop for multi-hop questions.

---

### 7. Context Assembly
- **Status**: `PARTIAL`
- **Actual File**: `RAG/evaluation/benchmarks/frames/isolation/harness.py`
- **Actual Function**: `retrieve_hybrid()` (lines 342-364) & `assemble_context()`
- **What Works**: Diversification caps passages to max 2 chunks per Wikipedia URL, ensuring broad coverage.
- **What Is Broken**: When an article contains critical facts split across 3 sections (e.g. Early Life, Career, Death), the 2-chunk cap prematurely drops the third fact.
- **What Is Missing**: Dynamic chunk budget allocation based on cross-reference entity density.
- **Dependencies**: Passage ranker.
- **Next Required Fix**: Increase max chunks per article from 2 to 3 for seed articles, while keeping peripheral articles at 1.

---

### 8. Deterministic Numeric & Temporal Reasoning
- **Status**: `DISCONNECTED FOR NARRATIVE`
- **Actual File**: `RAG/src/features/verification/math_engine.py` vs `harness.py`
- **Actual Function**: `DeterministicMathEngine.calculate()`
- **What Works**: Production math engine computes IEEE-754 calculations over structured table matrices.
- **What Is Broken**: In FRAMES narrative questions (e.g. *"How many years elapsed between event A and event B?"*), the math engine is not called. Qwen 2.5 14B must perform mental arithmetic, occasionally making off-by-one or subtraction errors.
- **What Is Missing**: Narrative date/span extraction and arithmetic evaluation injected into the prompt.
- **Dependencies**: `python-dateutil` / regex date parser.
- **Next Required Fix**: Parse extracted dates from retrieved passages and compute differences deterministically before prompting the LLM.

---

### 9. Qwen Synthesis
- **Status**: `OPERATIONAL BUT FRAGILE ON DENSE CONSTRAINTS`
- **Actual File**: `RAG/evaluation/benchmarks/frames/isolation/harness.py`
- **Actual Function**: `generate_answer()` (lines 438-518)
- **What Works**: Generates clean, structured chains of thought and emits `Final Answer: <entity>`. Runs fast on vLLM (~2-4s).
- **What Is Broken**: On multi-attribute intersection questions (e.g. "which of these 4 authors won prize X AND was born before 1920"), the LLM occasionally chooses a candidate that satisfies only one of the two constraints.
- **What Is Missing**: Constraint verification checklist in prompt.
- **Dependencies**: Prompt engineering.
- **Next Required Fix**: Inject explicit constraint validation instructions into system prompt.

---

### 10. FineCat-NLI Grounding
- **Status**: `OPERATIONAL IN PRODUCTION / BYPASSED IN BENCHMARK`
- **Actual File**: `RAG/src/features/evaluation/nli_verifier.py`
- **Actual Function**: `FineCatNLIVerifier.verify()`
- **What Works**: ModernBERT-large FP16 on `cuda:0` accurately classifies entailment/contradiction with sub-15ms latency.
- **What Is Broken**: The FRAMES benchmark harness runs token-based `FactualityEvaluator` rather than neural NLI to avoid CUDA contention with vLLM streaming on a single GPU.
- **What Is Missing**: Sequential batched NLI scoring post-generation.
- **Dependencies**: CUDA stream synchronization.
- **Next Required Fix**: Run FineCat NLI verifier sequentially after vLLM finishes completion.

---

### 11. ClaimVerification Contract
- **Status**: `OPERATIONAL`
- **Actual File**: `RAG/src/features/evaluation/engine.py`
- **Actual Function**: `verify_claims()`
- **What Works**: Populates `verification_path`, `decision_reason`, `raw_logits`, `softmax_probs`, `calibration_status`.
- **What Is Broken**: Softmax probabilities are uncalibrated on out-of-domain text.
- **What Is Missing**: Temperature scaling or Platt scaling calibration on NLI logits.
- **Dependencies**: Scikit-learn calibrator.
- **Next Required Fix**: Calibrate logits using validation split before downstream thresholding.

---

### 12. Quality-Gate Consistency
- **Status**: `OPERATIONAL`
- **Actual File**: `RAG/src/features/evaluation/quality_gate.py`
- **Actual Function**: `evaluate_quality_gate()`
- **What Works**: Discrepancies eliminated in M0; canonical claim results strictly dictate quality gate acceptance.
- **What Is Broken**: Does not check multi-hop path completeness (only individual claim entailment).
- **What Is Missing**: Graph connectivity validation in quality gate.
- **Dependencies**: NetworkX.
- **Next Required Fix**: Require that the reasoning graph forms a continuous connected component from query entities to target answer entity.

---

### 13. Benchmark Evaluator Correctness
- **Status**: `OPERATIONAL (FIXED IN SESSION)`
- **Actual File**: `RAG/evaluation/benchmarks/frames/evaluators/factuality.py`
- **Actual Function**: `evaluate()` & `_extract_tokens()`
- **What Works**: Token matching preserves decimals and digits; ignores trailing punctuation.
- **What Is Broken**: Partial credit matching on complex names (e.g. *"Warner Music"* vs *"Warner Music Group"*) gives 0.0 unless exact token overlap is high.
- **What Is Missing**: Alias-aware fuzzy evaluation.
- **Dependencies**: `rapidfuzz` or token set ratio.
- **Next Required Fix**: Add token set ratio fuzzy matching (> 85%) for reference answer entity matching.

---

### 14. Fallback & Abstention Logic
- **Status**: `OPERATIONAL (CERTIFIED)`
- **Actual File**: `RAG/evaluation/benchmarks/frames/isolation/harness.py`
- **Actual Function**: `generate_answer()`
- **What Works**: Sentence dumping eliminated. Emits honest `INSUFFICIENT REASONING PATH` safe abstention.
- **What Is Broken**: Model occasionally abstains on answerable queries if prompt is slightly ambiguous.
- **What Is Missing**: Abstention confidence thresholding.
- **Dependencies**: Logprob extraction from vLLM.
- **Next Required Fix**: Request logprobs from vLLM to gauge whether abstention was high-confidence or edge-case.

---

## 3. Recommended Implementation Order for FRAMES Remediation

To elevate FRAMES multi-hop accuracy from 32% toward state-of-the-art (> 50%):

1. **Step 1: Wire Multi-Turn Retrieval Loop (Gaps 5 & 6)**:
   Connect `LangGraph` cyclical subquery decomposition so hop $N+1$ dynamically queries entities discovered in hop $N$.
2. **Step 2: Infobox Triplet Extraction for Typed Edges (Gaps 3 & 4)**:
   Extract Wikipedia infobox tables into typed relational edges (`BORN_IN`, `DIRECTED_BY`, `TENURE`) rather than generic `MENTIONS` edges.
3. **Step 3: BM25/Embedding-Based Seed Node Resolution (Gap 2)**:
   Replace regex capitalized token seed selection with BM25 lexical search over node titles.
4. **Step 4: MediaWiki Alias & Redirect Integration (Gap 1)**:
   Query Wikipedia redirect tables to map alternate names and aliases to canonical entity IDs.
5. **Step 5: Narrative Date & Math Pre-Computation (Gap 8)**:
   Extract dates and numbers from retrieved passages and compute chronological spans deterministically before calling Qwen.
