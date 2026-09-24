# Memory Architecture: Stateful Sessions and Graph Evolution

## 1. Short-Term Memory: Stateful Sessions & Coreference Resolution
Short-term memory preserves conversational context across multiple conversational turns using thread-scoped checkpointing:

1. **Thread Checkpointing**:
   - State checkpoints are keyed to an external `thread_id` (via LangGraph memory saver).
   - Saves the active entity stack, retrieved citations, and previous query-intent pairs after each execution step.

2. **Coreference Resolution & Pronoun Disambiguation**:
   - When a user asks follow-up questions (e.g., *"What were their primary liabilities?"*, *"Who was the PI on that grant?"*, *"How many patents did they file?"*), the state machine inspects the checkpointed session state.
   - Resolves ambiguous pronouns (`they`, `their`, `it`, `that project`) to the dominant active entity (e.g., `IIT Madras`, `Dr. Sushanta Kumar Panigrahi`) prior to executing Cypher generation or vector search.

```
User Turn 1: "Tell me about Panjab University's budget."
   └─ Entity State: [Institution: "Panjab University"]

User Turn 2: "What were their primary revenue streams?"
   └─ Coreference Resolution: "their" -> "Panjab University"
   └─ Disambiguated Query: "What were Panjab University's primary revenue streams?"
```

---

## 2. Long-Term Memory: Graph-Backed Knowledge Base Evolution
Long-term memory evolves the central Knowledge Graph dynamically through a verified three-stage pipeline:

```
┌────────────────────────────────────────────────────────┐
│ Stage 1: Information Extraction                        │
│ - Parse incoming unstructured text/dialogue            │
│ - Extract candidate entity nodes, properties & triplets│
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Stage 2: Verification Staging                          │
│ - Stage extracted triples in a quarantine buffer       │
│ - Validate against ClaimVerifier and schema constraints│
│ - Detect conflicting or hallucinated assertions        │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Stage 3: Graph Reconciliation                          │
│ - Execute idempotent parameterized MERGE updates       │
│ - Merge verified attributes without destructive write  │
│ - Record timestamped audit trail (created_at/updated_at│
└────────────────────────────────────────────────────────┘
```

### A. Stage 1 — Information Extraction:
Extracts candidate nodes and relational edges conforming strictly to the `GRAPH SCHEMA DEFINITION`.

### B. Stage 2 — Verification Staging:
New claims and triples are held in a staging buffer. The `ClaimVerifier` confirms that:
- Node properties are non-contradictory.
- Source provenance (`chunk_id`, `page_number`, `document_id`) is attached.

### C. Stage 3 — Graph Reconciliation:
Idempotently applies verified staged triplets to Neo4j using parameterized `MERGE` clauses:
```cypher
UNWIND $staged_entities AS item
MERGE (n:Institution {name: item.name})
ON CREATE SET 
    n.type = item.type,
    n.location = item.location,
    n.created_at = timestamp()
ON MATCH SET 
    n.type = coalesce(item.type, n.type),
    n.location = coalesce(item.location, n.location),
    n.updated_at = timestamp();
```
