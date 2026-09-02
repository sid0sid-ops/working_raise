# RAISE Test & User Experience Separation Standard

This document establishes the strict separation between **Developer Diagnostics/Testing** and the **User-Facing Research Interface**.

---

## 1. Core Rule
**Developer test outputs, regression logs, test reports, and agent chain-of-thought MUST NEVER be presented in the user-facing chat UI or library source list.**

---

## 2. Separation Matrix

| Feature Area | Developer Space (`tests/`, `logs/`, CMD) | User Space (Web Studio UI) |
| :--- | :--- | :--- |
| **Chat Output** | Benchmark metrics, Cypher queries, raw JSON | Synthesized, evidence-backed scientific answers with citations. |
| **Progress / Status** | `test_graphrag_subgraph_query_grounding PASSED` | Calm, genuine statuses: `Reading PDF…`, `Traversing knowledge graph…`, `Synthesizing answer…`. |
| **Source Library** | Fixture PDFs (`Taxonomy_Stress_Test_Demo.pdf`) | Genuine user-imported documents only (`RAG/data/documents/`). |
| **Debug Data** | Terminal ANSI traces showing Top-$k$ chunk scores | Hidden from UI accordion (clean pill: `✓ Grounded 95% · 2 sources`). |
| **Databases** | Mock / isolated fixtures in `pytest` | Persistent production ChromaDB & Neo4j stores. |

---

## 3. Safe Telemetry Standards
* **Allowed in UI**:
  * Real document counts (`6 indexed documents`).
  * Real citation counts (`4 citations`).
  * Real grounding status (`Evidence-backed`).
* **Forbidden in UI**:
  * `Test Case 1`, `Expected vs Actual`.
  * `Gemini tested...` / `Antigravity tested...`.
  * Raw vector cosine distance numbers.
  * Internal agent routing debug JSON blobs.
