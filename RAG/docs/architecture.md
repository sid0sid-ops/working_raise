# RAISE University Agentic GraphRAG Architecture

## 1. System Overview
The **RAISE University Agentic GraphRAG System** is a production-grade, local-first intelligence engine designed for comparative analysis across complex university annual reports, institutional audits, and financial statements.

Unlike conventional RAG chatbots that flatten text into naive token chunks, RAISE enforces a **Grounded Multi-Substrate Architecture**:
1. **Document Understanding Layer**: Ingests multi-column, irregular PDFs with tables via PyMuPDF and IBM Research Docling.
2. **Canonical Document Model (CDM)**: Produces Structured JSON, 5-Star Semantic HTML5 (`<article>`, `<section>`, `<table data-page="...">`, `<data>`), and visual bounding box evidence simultaneously.
3. **Structured Numeric Fact Store**: Deterministic, zero-hallucination normalization for currencies (INR, USD), scales (Lakhs, Crores, Millions), and temporal reporting periods (FY vs AY).
4. **Neo4j Property Knowledge Graph**: Real-time multi-hop graph traversal over university entities, leadership, patents, grants, and strategic initiatives.
5. **ChromaDB Contextual Vector Store**: Dense semantic embeddings enriched with document hierarchy prefixes (Anthropic Contextual Retrieval pattern).
6. **Agentic Router & Iterative Loop**: Autonomous query planner executing multi-tool searches with Google Agentic RAG **Evidence Sufficiency Checks**.
7. **Anti-Hallucination Claim Verifier**: Rejects ungrounded statements and enforces a strict 7-tier provenance chain ($\text{Answer} \to \text{Claim} \to \text{Fact} \to \text{HTML5 Node} \to \text{Page} \to \text{PDF BBox}$).

---

## 2. End-to-End Data Flow

```text
               COMPLEX UNIVERSITY PDFS (1 to 100+ Documents)
                                     │
                                     ▼
                      DOCUMENT UNDERSTANDING LAYER
                    (Docling / PyMuPDF Layout Engine)
                                     │
                                     ▼
                         CANONICAL DOCUMENT MODEL
                  ┌──────────────────┼──────────────────┐
                  ▼                  ▼                  ▼
           STRUCTURED JSON     SEMANTIC HTML5     SOURCE EVIDENCE
          (Schema Filtering)  (5-Star Accessible)   (BBoxes & Pages)
                  │                  │                  │
                  └──────────────────┼──────────────────┘
                                     │
                                     ▼
                         DOMAIN EXTRACTION LAYER
                  ┌──────────────────┼──────────────────┐
                  ▼                  ▼                  ▼
            NUMERIC FACTS        ENTITIES          RELATIONSHIPS
           (Values/Currencies) (Institutes/Deans) (Grants/Patents)
                  │                  │                  │
                  └──────────────────┼──────────────────┘
                                     │
                                     ▼
                          7-TIER PROVENANCE LAYER
                  ┌──────────────────┼──────────────────┐
                  ▼                  ▼                  ▼
             NEO4J GRAPH        VECTOR INDEX       TABLE ENGINE
            (Community Nodes)  (Dense ChromaDB)   (2D Matrix Grids)
                  │                  │                  │
                  └──────────────────┼──────────────────┘
                                     │
                                     ▼
                         AGENTIC REASONING ROUTER
                                     │
                  ┌──────────────────┴──────────────────┐
                  ▼                                     ▼
           REASONING MEMORY                      MULTI-TOOL DISPATCH
         (Google ReasoningBank)                (Fact/Cypher/Vector/Table)
                  │                                     │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                              EVIDENCE FUSION
                                     │
                                     ▼
                          EVIDENCE SUFFICIENCY?
                              /             \
                            NO               YES
                            │                 │
                            ▼                 ▼
                     ITERATE QUERY     CLAIM VERIFIER
                            │                 │
                            └────────>────────┤
                                              ▼
                                     COMPARATIVE ENGINE
                                     (Unit/Period Norm)
                                              │
                                              ▼
                                       ANSWER CONTRACT
                                  (Verified Machine JSON)
                                              │
                                              ▼
                                    GROUNDED CITATION UI
```
