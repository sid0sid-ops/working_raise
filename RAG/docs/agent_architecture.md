# RAISE Agentic Reasoning & Tool Orchestration Architecture

## 1. Overview
The Agentic layer replaces naive single-shot retrieval with an **autonomous iterative loop** governed by 2026 Google Agentic RAG and ReasoningBank principles.

---

## 2. Logical Agent Roles

The system decomposes complex institutional queries across 5 specialized logical agent roles:

```text
                                USER QUERY
                                    │
                                    ▼
                         1. QUERY PLANNER AGENT
                (Intent Classification & Tool Strategy Selection)
                                    │
                                    ▼
                      2. RETRIEVAL COORDINATOR AGENT
            (Executes Parallel Fact, Cypher, Vector & Table Tools)
                                    │
                                    ▼
                       3. EVIDENCE SUFFICIENCY AGENT
            (Evaluates completeness: If missing -> Re-queries)
                                    │
                                    ▼
                      4. COMPARATIVE ANALYST AGENT
         (Normalizes Units/Currencies/Periods & Calculates Ratios)
                                    │
                                    ▼
                       5. EVIDENCE VERIFIER AGENT
             (Strict Claim Validation against PDF Bounding Boxes)
                                    │
                                    ▼
                       6. ANSWER GENERATOR AGENT
                  (Emits Verified AnswerContract JSON)
```

---

## 3. Implemented Tool Contracts

| Tool Name | Engine Backend | Execution Contract |
| :--- | :--- | :--- |
| `search_structured_facts()` | `fact_engine.py` | Deterministic lookup by university, metric, and normalized year. |
| `cypher_query()` | `neo4j_engine.py` | Direct parameterized Cypher query on live Neo4j database (`bolt://localhost:7687`). |
| `vector_search()` | `vector_engine.py` | Context-enriched dense cosine similarity search in ChromaDB. |
| `search_tables()` | `table_engine.py` | 2D matrix cell retrieval preserving column/row header coordinates. |
| `compare_universities()` | `comparative_engine.py` | Cross-institutional metric normalization and comparability status scoring. |
| `verify_claim()` | `claim_verifier.py` | Validates numeric values, currency bounds, and source page provenance. |

---

## 4. Google ReasoningBank Memory Loop

The `reasoning_memory.py` module records verified query execution trajectories:
* **Query Patterns**: Maps common question structures to successful tool combinations.
* **Entity Disambiguation**: Caches alias mappings (e.g. `PU` $\leftrightarrow$ `Panjab University`).
* **Verification Failures**: Flags ambiguous metrics to guide future query planning without overriding ground truth evidence.
