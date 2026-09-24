# Stateful Agentic Orchestration with LangGraph and LangChain Core

## Cyclic Self-Correction and Error Fallback Architecture

The agentic pipeline executes as a stateful, cyclical graph implemented with **LangGraph** and **LangChain Core**, integrating local **Qwen 2.5 7B** and deterministic heuristic engines.

```
       ┌───────────────────────────────┐
       │   Classification & Routing    │
       │         (Qwen 2.5 7B)         │
       └──────────────┬────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
  [Global Community]      [Text-to-Cypher Gen]
  (Hierarchical Summaries)         │
         │                         ▼
         │               [Cypher Execution] ◄──────────────┐
         │                         │                       │
         │                ┌────────┴────────┐              │
         │                ▼                 ▼              │ (Max 3 retries)
         │            [Success]          [Failed]          │
         │                │                 │              │
         │                ▼                 ▼              │
         │       [Relational Critic]   [Cypher Repair] ────┘
         │          (Path Dead-End?         │ (If repair fails > 3)
         │           1-Hop Expand)          ▼
         │                │            [ChromaDB Vector
         │                │             Search Fallback]
         │                │                 │
         └────────────┬───┴─────────────────┘
                      ▼
       ┌───────────────────────────────┐
       │  Fusion & Response Synthesis  │
       │         (Qwen 2.5 7B)         │
       └───────────────────────────────┘
```

---

## 1. Node Specifications

### Node 1: Classification and Routing Node
- **Function**: Natural query decomposition and strategy routing via Qwen 2.5 7B / AgentRouter.
- **Routing Decisions**:
  - `GLOBAL_COMMUNITY`: Broad, multi-section institutional summaries -> routes to NetworkX hierarchical community summaries.
  - `LOCAL_GRAPH_CYPHER`: Entity-specific, relationship, or structural lookups -> routes to Text-to-Cypher generation node.
  - `HYBRID_VECTOR`: Keyword/fact lookups -> routes directly to dense ChromaDB vector search.

### Node 2: Text-to-Cypher Generation Node
- **Function**: Translates natural language questions into strict, read-only, schema-grounded Cypher queries using the `retrieval_qa_chat_prompt` schema.

### Node 3: Cypher Execution & Validation Node
- **Function**: Executes the Cypher query against Neo4j with parameter maps. Captures query execution status, records, or driver syntax exceptions.

### Node 4: Cypher Repair Node (Cyclic Self-Correction)
- **Function**: Corrects failing Cypher queries. Receives:
  - Failing Cypher query string
  - Neo4j driver error traceback / syntax error message
  - Active schema definition (allowed node labels & relationship types)
- **Loop Guard**: Capped at **3 repair iterations**.
- **Fallback**: If unrepairable after 3 attempts, transitions state directly to **ChromaDB Dense Vector Search Fallback**.

### Node 5: Relational Path Critic Node
- **Function**: Analyzes the topology of retrieved Cypher subgraphs.
- **Action**: If the path hits a dead end (disconnected terminal node) without resolving the query entities, automatically triggers a directed **1-hop expansion** around the terminal node.

### Node 6: Fusion & Response Synthesis Node
- **Function**: Synthesizes dense vector text passages, structured facts, and verified graph triples into a grounded, cited response with claim verification contracts.
