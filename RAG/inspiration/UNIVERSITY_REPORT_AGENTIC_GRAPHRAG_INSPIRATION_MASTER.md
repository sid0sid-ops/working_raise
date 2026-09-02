# UNIVERSITY REPORT AGENTIC GraphRAG
## Master Inspiration + Architecture + Implementation Specification for Google Antigravity

**Version:** 1.0
**Date:** 31 August 2026
**Purpose:** Place this file inside the project's `inspiration/` directory and use it as the authoritative architectural brief for the GraphRAG + Agentic AI portion of the university-report comparison project.

---

# 0. READ THIS FIRST — MISSION

You are building an AI system for comparing information contained in difficult, heterogeneous university reports such as:

- Annual reports
- Audited financial reports
- Institutional reports
- Research reports
- Accreditation reports
- Performance reports
- Statistical reports
- Other official university documents

The central problem is not simply retrieval.

The central problem is **reliable transformation of visually and semantically complex documents into a traceable evidence system**, followed by **multi-step retrieval, comparison, verification, and explanation**.

The final system must be able to answer questions such as:

> Compare University A and University B in research expenditure between 2021–22 and 2024–25.

or:

> Which university showed stronger growth in externally funded research, and what evidence in their annual reports supports that conclusion?

or:

> How many international collaborations did each university report in 2024, and which departments were involved?

The system must not behave like a generic PDF chatbot.

It must behave like a **document-grounded research analyst** whose every important claim can be traced back to the original source document.

---

# 1. MOST IMPORTANT ARCHITECTURAL CHANGE TO CONSIDER

## Do not assume that `JSON -> Semantic HTML5 -> GraphRAG` is the ideal canonical pipeline.

The existing team appears to have a pipeline where:

```text
PDF
  -> PDF parser
  -> filtered/schema-based JSON
  -> JSON -> semantic HTML5
  -> GraphRAG
```

This should be reviewed before further implementation.

A better conceptual architecture is likely:

```text
                       ORIGINAL PDF
                            |
                            v
                  DOCUMENT UNDERSTANDING
                     (Docling or existing
                      high-quality parser)
                            |
                            v
                CANONICAL DOCUMENT MODEL
               /         |          \
              /          |           \
             v           v            v
        Structured      Semantic     Visual/page
           JSON          HTML5       evidence
             |             |            |
             +-------------+------------+
                           |
                           v
                    SCHEMA / DOMAIN
                     EXTRACTION LAYER
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
          FACTS        ENTITIES      RELATIONS
             |             |             |
             +-------------+-------------+
                           |
                           v
                     PROVENANCE LAYER
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
        KNOWLEDGE       VECTOR        LEXICAL
          GRAPH         INDEX          INDEX
             |             |             |
             +-------------+-------------+
                           |
                           v
                 AGENTIC RETRIEVAL LAYER
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
         GRAPH          VECTOR        STRUCTURED
         TOOLS          TOOLS          TOOLS
            |              |              |
            +--------------+--------------+
                           |
                           v
                    EVIDENCE FUSION
                           |
                           v
                  CLAIM VERIFICATION
                           |
                           v
                  GROUNDED RESPONSE
```

## Core principle

**Semantic HTML should be a high-quality, traceable representation/export of the document — not automatically the only representation used downstream.**

Docling currently provides a structured document representation, JSON serialization, HTML output, and RAG-oriented chunk output, and supports advanced PDF understanding including layout, reading order, and table structure. Therefore the agent must evaluate whether the project should use a canonical document representation first and generate semantic HTML from that representation, rather than treating HTML as the sole intermediate representation. (See References.)

Do not delete the existing team's HTML module. Instead, make it an **explicit semantic representation/export layer** and preserve stable IDs so downstream graph/vector records can point back to HTML nodes and original PDF pages.

---

# 2. NON-NEGOTIABLE DESIGN GOALS

The system must optimize for:

1. **Traceability**
2. **Factual accuracy**
3. **Evidence grounding**
4. **Comparability**
5. **Temporal correctness**
6. **Table accuracy**
7. **Entity resolution**
8. **Multi-document reasoning**
9. **Low hallucination rate**
10. **Local/free-first execution**
11. **Incremental indexing**
12. **Maintainability by a solo developer**

The system must not optimize merely for:

- maximum framework count,
- maximum number of agents,
- maximum graph size,
- impressive-looking demos,
- unnecessary microservices,
- cloud dependence,
- opaque end-to-end LLM processing.

---

# 3. EXISTING TEAM CONTEXT

There are already team-built modules.

## Module A — Domain/schema design

A team member is designing the schema that decides what information should be extracted from the reports.

## Module B — PDF parser/filtering

A team member is working on parsing PDFs and filtering/extracting their content into JSON.

## Module C — Semantic HTML5 (current responsibility)

The current objective is to turn structured JSON into semantically meaningful HTML5 with excellent provenance and traceability.

## Module D — GraphRAG + Agentic AI (current task)

This specification concerns the architecture around:

- canonical document representation,
- semantic HTML integration,
- chunking,
- graph construction,
- embeddings,
- vector retrieval,
- hybrid retrieval,
- agentic query planning,
- verification,
- comparison,
- source citation.

### CRITICAL TEAM-INTEGRATION RULE

Do not rewrite other people's modules merely because a different architecture is preferred.

Instead:

1. inspect their interfaces,
2. preserve compatible APIs,
3. create adapters where necessary,
4. add validation around their outputs,
5. document assumptions,
6. only request upstream changes when technically necessary.

---

# 4. FIRST ACTION: RECONNAISSANCE, NOT CODING

Before implementing major GraphRAG functionality, recursively inspect the entire repository.

Inspect:

- all source code,
- existing parsers,
- schemas,
- Pydantic models,
- JSON examples,
- HTML generation code,
- tests,
- configuration,
- Docker setup,
- database code,
- notebooks,
- scripts,
- documentation.

Also recursively inspect the complete `inspiration/` directory.

For each inspiration project:

- identify its architecture,
- identify its useful patterns,
- identify its retrieval approach,
- identify graph construction,
- identify entity extraction,
- identify chunking,
- identify embedding strategy,
- identify reranking,
- identify agent strategy,
- identify provenance,
- identify evaluation,
- identify local-model support,
- identify licensing,
- identify outdated/deprecated parts,
- decide whether to borrow the idea, adapt the implementation, or reject it.

Create:

```text
/ docs/inspiration_analysis.md
```

Do not blindly copy repositories.

Check licenses before reusing code.

Prefer architectural reuse over wholesale copying.

---

# 5. CURRENT RESEARCH SIGNALS TO INCORPORATE

This project should explicitly evaluate current 2026 work rather than relying only on older RAG recipes.

## 5.1 Google Research — Agentic RAG

On 5 June 2026, Google Research published work on an Agentic RAG framework developed with Google Cloud. The framework is explicitly designed for multi-source and multi-hop enterprise queries, with multiple agents iteratively searching until enough context is available for a dependable answer. Google reports up to a 34% accuracy improvement on factuality datasets compared with standard RAG in its evaluation. 

**Architecture lesson for this project:**

Do not use a fixed one-shot retrieval pipeline for complex university comparisons.

Use a loop like:

```text
Query
 -> understand
 -> plan
 -> retrieve
 -> inspect evidence sufficiency
 -> retrieve again if necessary
 -> verify
 -> answer
```

Reference:
- https://research.google/blog/unlocking-dependable-responses-with-gemini-enterprise-agent-platforms-agentic-rag/

## 5.2 Google Research — ReasoningBank

Google Research published ReasoningBank on 21 April 2026. It treats successful and failed agent trajectories as sources of reusable reasoning strategies and introduces a memory loop involving retrieval, reflection, extraction, and consolidation.

**Architecture lesson for this project:**

Do not immediately build a large persistent memory system.

Instead introduce an optional `reasoning_memory` layer that can record:

- successful retrieval strategies,
- failed retrieval strategies,
- recurring ambiguity patterns,
- university-specific naming patterns,
- query-routing corrections,
- verification failures.

Use this later for iterative improvement and evaluation.

Reference:
- https://research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/

## 5.3 Google ADK — Agent-oriented development

Google's current Agent Development Kit documentation provides agent tooling, evaluation support, MCP connectivity, multi-language support, and an Agents CLI intended to assist AI coding environments, including Antigravity.

**Architecture lesson:**

Study ADK's patterns for:

- tool calling,
- agent decomposition,
- evaluation,
- sessions/state,
- capability loading.

Do not introduce ADK solely for branding. Use it only where it reduces implementation complexity.

Reference:
- https://google.github.io/adk-docs/
- https://google.github.io/adk-docs/tutorials/coding-with-ai/

## 5.4 Google Agent Executor

Google Cloud introduced Agent Executor in May 2026 as an open-source runtime approach for durable, resumable, distributed agent execution.

**Architecture lesson:**

Do not build durable distributed execution in version 1.

However, keep agent state and task events separated from business logic so future durable execution can be added without redesigning the retrieval layer.

Reference:
- https://cloud.google.com/blog/products/ai-machine-learning/agent-executor-googles-distributed-agent-runtime/

## 5.5 Google research direction — long-context + multi-agent aggregation

Google Research's Chain-of-Agents work demonstrated a different approach to long-context tasks: multiple agents process pieces of a large input and an aggregator combines intermediate results. The work reported improvements over RAG, multi-agent baselines, and naïve full-context approaches on its evaluated long-context tasks.

**Architecture lesson:**

For extremely large annual-report corpora, do not always attempt to pass all retrieved evidence into one model context. Use hierarchical evidence aggregation when necessary.

Reference:
- https://research.google/blog/chain-of-agents-large-language-models-collaborating-on-long-context-tasks/

## 5.6 Google Research — TabFM

Google Research introduced TabFM in June 2026 as a foundation model for tabular classification/regression.

This is not automatically a component of the RAG stack, but it is a useful research signal:

**Tables should be treated as first-class data, not merely flattened prose.**

For university reports, table extraction and structured numeric comparison should remain separate from ordinary semantic retrieval.

Reference:
- https://research.google/blog/introducing-tabfm-a-zero-shot-foundation-model-for-tabular-data/

## 5.7 Google Research — current agentic research direction

Google's 2026 research portfolio shows a broader movement toward systems that combine models, tools, iterative reasoning, agents, and scientific/data workflows rather than one-shot prompting.

Relevant overview:
- https://research.google/blog/a-new-era-of-innovation-google-research-at-io-2026/

---

# 6. DOCLING — EXPLICITLY ADD TO INSPIRATION

## Why Docling is important here

Docling is an open-source document-processing framework designed to convert complex documents into structured representations for AI and document understanding.

Current Docling capabilities include:

- PDF processing,
- layout understanding,
- reading-order understanding,
- table structure understanding,
- OCR-related workflows,
- images and other document formats,
- structured JSON serialization,
- HTML output,
- Markdown output,
- RAG-oriented chunk output,
- a universal document representation.

Reference:
- https://github.com/docling-project/docling
- https://github.com/docling-project/docling/blob/main/docs/index.md
- https://github.com/docling-project/docling/blob/main/docs/usage/supported_formats.md

## Architectural conclusion

Docling should be investigated as a **document-understanding engine**, not just as a PDF-to-HTML utility.

The correct question is not:

> "Can Docling replace our JSON-to-HTML module?"

The correct question is:

> "Can Docling give us a stronger canonical document representation, from which our project can produce controlled JSON, semantic HTML5, page evidence, table evidence, and RAG chunks?"

### Preferred design

```text
PDF
 |
 v
Docling / existing parser
 |
 v
Canonical document model
 |
 +--> structured extraction JSON
 |
 +--> semantic HTML5
 |
 +--> source/page evidence
 |
 +--> table representation
 |
 +--> RAG chunks
 |
 +--> graph extraction input
```

### Existing-module compatibility strategy

If the existing team parser already performs domain-specific filtering that Docling does not:

```text
Docling
   |
   v
layout-aware canonical document
   |
   v
existing parser/filtering adapter
   |
   v
team JSON schema
```

If the existing parser performs better on some document classes:

```text
Document classifier
  |
  +--> Parser A
  |
  +--> Docling
  |
  +--> OCR fallback
```

Do not force one parser onto every PDF.

---

# 7. CANONICAL DOCUMENT MODEL

Create a stable internal document representation.

It should be richer than plain JSON text.

At minimum represent:

```text
Document
Page
Section
Heading
Paragraph
List
Table
TableRow
TableCell
Figure
Caption
Footnote
Reference
EntityMention
MetricMention
Fact
SourceSpan
```

Every object should have a stable ID.

Example:

```json
{
  "node_id": "docA_p087_sec04_tbl02_row07",
  "document_id": "universityA_annual_report_2024",
  "page": 87,
  "element_type": "table_row",
  "section_id": "research",
  "source_span": {
    "page": 87,
    "bbox": [72, 310, 524, 402]
  }
}
```

Where bounding boxes are available, preserve them.

This enables future click-to-source UI and visual verification.

---

# 8. SEMANTIC HTML5 — KEEP IT, BUT MAKE IT A TRACEABILITY LAYER

Semantic HTML should use meaningful tags.

Preferred elements include:

```html
<article>
<header>
<section>
h1
h2
h3
<p>
<table>
thead
tbody
tr
th
td
<figure>
<figcaption>
<aside>
time
<data>
```

Avoid meaningless `<div>` structures when semantic elements are available.

Every semantic object should preserve IDs from the canonical document model.

Example:

```html
<section
  id="docA_p087_research_funding"
  data-document-id="universityA_annual_report_2024"
  data-page-start="87"
  data-page-end="88"
  data-section-type="research">

  <h2 data-node-id="docA_p087_heading_04">
    Research Funding
  </h2>

  <table
    id="docA_p087_table_02"
    data-source-page="87">

    ...

  </table>
</section>
```

For numeric values:

```html
<data
  id="fact_00125"
  value="125.7"
  data-unit="million-INR"
  data-period="2024"
  data-metric="research-expenditure"
  data-confidence="0.97">
  ₹125.7 million
</data>
```

### HTML is not decorative

The semantic HTML must be machine-readable and source-aware.

It should support:

- DOM-level retrieval,
- source navigation,
- evidence rendering,
- chunk anchoring,
- graph provenance,
- citation generation.

---

# 9. PROVENANCE-FIRST ARCHITECTURE

The original PDF remains the ultimate source of truth.

Every derived object must be traceable.

Ideal chain:

```text
Final Answer
     |
     v
Claim
     |
     v
Evidence Record
     |
     +--> Graph Fact
     +--> Vector Chunk
     +--> Structured Fact
     +--> Semantic HTML node
     |
     v
Document element
     |
     v
Page
     |
     v
Original PDF
```

Every important fact should preserve:

```text
document_id
source_file
page
section_id
table_id
row_id
column_id
html_node_id
chunk_id
fact_id
entity_ids
metric_id
temporal_scope
extraction_method
confidence
parser_version
schema_version
```

---

# 10. KNOWLEDGE GRAPH MODEL

Neo4j is the preferred first graph database to evaluate.

Potential entities:

```text
University
Report
ReportPeriod
Page
Section
Table
Person
Department
Faculty
School
Centre
Institute
Programme
ResearchProject
Publication
Patent
Grant
FundingAgency
ResearchFunding
Audit
Budget
Income
Expenditure
Metric
Indicator
Ranking
Accreditation
Collaboration
PartnerInstitution
Country
Campus
Laboratory
Infrastructure
Event
Achievement
Policy
```

Potential relationships:

```text
UNIVERSITY_PUBLISHED_REPORT
REPORT_CONTAINS_SECTION
SECTION_CONTAINS_TABLE
TABLE_CONTAINS_FACT
FACT_ABOUT_ENTITY
ENTITY_HAS_ALIAS
UNIVERSITY_HAS_DEPARTMENT
DEPARTMENT_BELONGS_TO_FACULTY
FACULTY_HAS_RESEARCH_PROJECT
UNIVERSITY_RECEIVED_GRANT
GRANT_FUNDED_PROJECT
UNIVERSITY_COLLABORATED_WITH
UNIVERSITY_REPORTED_METRIC
METRIC_VALID_FOR_PERIOD
REPORT_COVERS_PERIOD
FACT_SUPPORTED_BY_SOURCE
```

Do not create a graph node for every word.

Use a domain ontology that represents meaningful, reusable concepts.

---

# 11. TEMPORAL MODEL — EXTREMELY IMPORTANT FOR UNIVERSITY REPORTS

Never assume these are interchangeable:

```text
Calendar year
Academic year
Financial year
Report year
Publication date
Reporting period
```

Examples:

```text
2024
2023-24
FY2024
AY2023-24
2024-25 financial year
```

All must have explicit semantics.

A comparison must first establish that the periods are comparable.

---

# 12. NUMERIC + FINANCIAL FACT MODEL

University reports contain many quantities where semantic context matters.

A fact must preserve:

```text
value
unit
scale
currency
metric
period
scope
university
definition
source
page
table
confidence
```

Example:

```json
{
  "fact_id": "fact_00125",
  "metric": "research_expenditure",
  "value": 125.7,
  "scale": "million",
  "currency": "INR",
  "period": "2023-24",
  "university": "University A",
  "source": {
    "document_id": "uniA_ar_2024",
    "page": 87,
    "table_id": "docA_p087_table_02"
  },
  "confidence": 0.97
}
```

Do not compare values until:

- unit is normalized,
- currency is normalized where necessary,
- period is aligned,
- metric definitions are compatible,
- scope is compatible.

---

# 13. ENTITY RESOLUTION

The same institution or department may appear under different names.

Example:

```text
PU
Panjab University
Panjab University, Chandigarh
The University
University
```

Store:

```text
canonical_name
aliases
entity_type
confidence
source_mentions
```

Use deterministic rules before LLM similarity.

Possible progression:

```text
exact normalized match
        |
        v
alias dictionary
        |
        v
structured metadata
        |
        v
fuzzy/string similarity
        |
        v
embedding similarity
        |
        v
LLM adjudication only when ambiguous
```

Do not merge merely because names look similar.

---

# 14. CHUNKING — STRUCTURE-AWARE, NOT BLIND FIXED TOKENS

Do not rely solely on fixed-size token chunks.

Prefer chunks based on:

- section boundaries,
- heading hierarchy,
- table boundaries,
- paragraph grouping,
- entity continuity,
- metric continuity,
- page boundaries,
- semantic units.

A chunk should have:

```text
chunk_id
document_id
section_id
page_start
page_end
html_node_ids
text
context_prefix
metadata
```

## Contextual retrieval

A useful pattern from modern RAG practice is to attach missing local context to a chunk before embedding/retrieval. Anthropic's contextual retrieval work describes contextual embeddings plus contextual BM25 specifically to reduce failures caused by chunks losing their document context.

Reference:
- https://www.anthropic.com/engineering/contextual-retrieval

For this project, consider generating a deterministic context prefix such as:

```text
University: University A
Report: Annual Report 2024
Reporting period: 2023-24
Section: Research > Funding
Table: Research Funding by Source
Page: 87

[chunk text]
```

Do this before embedding.

---

# 15. TABLES MUST BE FIRST-CLASS OBJECTS

This is one of the most important requirements.

Do not simply convert every table into a paragraph.

Preserve:

- table ID,
- title,
- caption,
- header hierarchy,
- row headers,
- column headers,
- units,
- merged cells,
- cell values,
- row/column coordinates,
- page,
- source span,
- semantic interpretation.

A table can generate both:

1. structured facts,
2. textual retrieval representations.

Do not force the LLM to reconstruct a table from flattened text when a structured table object is available.

---

# 16. VECTOR EMBEDDINGS

Start by benchmarking strong local embedding candidates rather than hard-coding one model permanently.

A sensible baseline is:

```text
BAAI/bge-m3
```

BGE-M3 is a useful candidate because it supports multilingual retrieval and multiple retrieval modes.

Reference:
- https://huggingface.co/BAAI/bge-m3

The embedding interface must be replaceable:

```text
EmbeddingProvider
  |- BGE-M3
  |- SentenceTransformers provider
  |- Future local model
```

Do not make the whole application depend on one model.

---

# 17. VECTOR DATABASE OPTIONS

Evaluate in this order:

## Option 1 — Neo4j vector indexes

Because Neo4j is already planned for the graph, first determine whether a unified graph + vector architecture is sufficient.

The official Neo4j GraphRAG Python package currently supports vector retrieval, hybrid retrieval, Cypher-aware retrieval, Text-to-Cypher, and tool-based retrieval.

Neo4j 2026.01+ also adds in-index filtering for compatible vector filters through the `SEARCH` clause.

Reference:
- https://neo4j.com/docs/neo4j-graphrag-python/current/
- https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html

## Option 2 — Qdrant

Consider Qdrant if vector/lexical hybrid search needs become substantially more sophisticated than Neo4j's current implementation.

Qdrant supports dense + sparse hybrid search and metadata filtering.

References:
- https://qdrant.tech/documentation/search/text-search/hybrid-search/
- https://qdrant.tech/documentation/search/hybrid-queries/
- https://qdrant.tech/documentation/search/filtering/

## Option 3 — FAISS

Use FAISS for an extremely simple local vector layer when advanced metadata filtering is not needed.

## Option 4 — LanceDB

Evaluate if local embedded vector/data workflows are attractive.

### Default recommendation

Start with **Neo4j for graph + vector**.

Add Qdrant only if measured retrieval requirements justify the additional system.

---

# 18. LEXICAL SEARCH

Do not rely on embeddings alone.

University documents frequently contain exact names, codes, abbreviations, numeric strings, funder names, program names, and metric labels.

Use:

```text
vector search
+
full-text / BM25-style search
```

Neo4j currently provides a HybridRetriever that combines vector and full-text search, as well as hybrid Cypher retrieval.

Reference:
- https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html

---

# 19. GRAPH RETRIEVAL

Graph retrieval is especially important for:

- multi-hop questions,
- department -> faculty -> research project relationships,
- funding -> project -> department links,
- institution -> collaboration -> country chains,
- university -> metric -> period relationships.

Example:

```text
University A
  -> Department X
  -> Research Project Y
  -> Grant Z
  -> Funding Agency Q
```

A vector search may retrieve only a relevant paragraph.

A graph traversal can expose relationships that are not contiguous in the source text.

---

# 20. AGENTIC RAG — REQUIRED ARCHITECTURE

The final system should not be:

```text
User
 -> vector search
 -> LLM
```

The preferred architecture is:

```text
                         USER QUERY
                              |
                              v
                     QUERY UNDERSTANDING
                              |
                              v
                      QUERY DECOMPOSITION
                              |
                              v
                       RETRIEVAL PLANNER
                              |
            +-----------------+-----------------+
            |                 |                 |
            v                 v                 v
       STRUCTURED          GRAPH             VECTOR
          TOOL              TOOL              TOOL
            |                 |                 |
            +-----------------+-----------------+
                              |
                              v
                       EVIDENCE FUSION
                              |
                              v
                     EVIDENCE SUFFICIENCY?
                         /            \
                       NO              YES
                       |                |
                       v                v
                 ITERATE QUERY       VERIFY
                       |                |
                       +------->-------+
                              |
                              v
                       CLAIM GENERATION
                              |
                              v
                      CLAIM VERIFICATION
                              |
                              v
                       ANSWER GENERATION
                              |
                              v
                      CITATION VALIDATION
                              |
                              v
                         FINAL ANSWER
```

This matches the current direction of Google's 2026 Agentic RAG work: iterative retrieval, multi-source/multi-hop decomposition, and an explicit check that the evidence is sufficient before generating a dependable answer.

---

# 21. AGENT ROLES

Avoid creating agents simply for the sake of having many agents.

A practical initial design is:

## Agent 1 — Query Planner

Responsibilities:

- understand the question,
- identify entities,
- identify periods,
- identify metrics,
- classify the query,
- produce a retrieval plan.

## Agent 2 — Retrieval Coordinator

Responsibilities:

- select graph/vector/structured tools,
- execute searches,
- request more context,
- stop when sufficient evidence is found.

## Agent 3 — Evidence Verifier

Responsibilities:

- check source support,
- verify numbers,
- verify dates,
- check entity identity,
- check unit consistency,
- identify contradictions.

## Agent 4 — Comparative Analyst

Use only when the query asks for a comparison or analysis.

Responsibilities:

- normalize metrics,
- calculate differences,
- explain trends,
- distinguish observation from interpretation.

## Agent 5 — Answer Generator

Produces the final human-readable answer from verified evidence only.

### Important

These can initially be implemented as logical agent roles inside one process.

Do not automatically deploy five independent services.

---

# 22. AGENT TOOL CONTRACTS

Implement explicit tools such as:

```text
search_structured_facts()
search_vector()
search_lexical()
search_graph()
run_cypher()
search_tables()
resolve_entity()
retrieve_document()
retrieve_page()
retrieve_section()
retrieve_source_span()
compare_metrics()
normalize_unit()
verify_claim()
```

Each tool should return structured output.

Example:

```json
{
  "tool": "search_structured_facts",
  "results": [
    {
      "fact_id": "fact_00125",
      "value": 125.7,
      "unit": "million INR",
      "period": "2023-24",
      "source": {
        "document_id": "uniA_ar_2024",
        "page": 87,
        "table_id": "table_02"
      }
    }
  ]
}
```

Never return only free-form strings from critical retrieval tools.

---

# 23. QUERY ROUTING

Examples:

## Exact fact

Question:

> What was University A's research expenditure in 2024?

Preferred path:

```text
structured facts
-> source verification
-> answer
```

## Semantic narrative

Question:

> What major research initiatives did University A undertake?

Preferred path:

```text
vector search
+
graph context
+
source verification
```

## Relationship

Question:

> Which departments collaborated with international institutions?

Preferred path:

```text
graph search
+
source evidence
```

## Comparison

Question:

> Compare research funding between University A and University B from 2021–2024.

Preferred path:

```text
query decomposition
+
structured facts
+
semantic retrieval
+
graph context
+
unit/period normalization
+
comparison
+
verification
```

## Multi-hop explanation

Question:

> Why did University A's research expenditure change between 2022 and 2024?

Preferred path:

```text
structured values
+
trend calculation
+
vector search for explanatory narratives
+
graph search for funding/project relationships
+
source verification
```

---

# 24. EVIDENCE SUFFICIENCY CHECK

This is a central Agentic RAG component.

After each retrieval cycle ask:

```text
Do we have sufficient evidence to answer the user's question accurately?
```

Check:

- entity coverage,
- period coverage,
- metric coverage,
- source authority,
- citation availability,
- numeric consistency,
- contradictory evidence,
- comparison compatibility.

Return a structured result:

```json
{
  "sufficient": false,
  "missing": [
    "University B 2022 research expenditure",
    "definition of research expenditure"
  ],
  "reason": "comparison is incomplete"
}
```

Then retrieve again.

Do not generate an answer merely because some evidence was found.

---

# 25. CLAIM VERIFICATION

Every material claim must be tested before final generation.

Example:

```text
Claim:
University A spent ₹125.7 crore on research in 2024.

Verifier:
- Does the source contain ₹125.7 crore?
- Is the period 2024 or 2023-24?
- Is this expenditure or allocation?
- Is the unit crore or million?
- Is the source audited or unaudited?
- Is the figure university-wide?
- Can the page/table be cited?
```

If verification fails:

```text
reject claim
```

or:

```text
qualify claim
```

---

# 26. SOURCE AUTHORITY MODEL

Suggested configurable ordering:

```text
Official audited report
>
Official annual report
>
Official institutional report
>
Official university web publication
>
Secondary source
>
Model inference
```

This should be a score, not a rigid rule.

A model inference should never silently look like an official fact.

---

# 27. CONFLICT RESOLUTION

Conflicts are expected.

Example:

```text
Annual Report 2023:
Research funding = 120 crore

Annual Report 2024:
Research funding = 118 crore
```

Possible reasons:

- different reporting periods,
- different metric definition,
- revised figure,
- gross vs net value,
- project-specific vs university-wide scope.

The system must investigate before choosing a value.

If unresolved, expose the conflict.

---

# 28. COMPARABILITY ENGINE

Do not compare values simply because they have similar names.

A comparison should evaluate:

```text
same metric definition?
same reporting period?
same unit?
same currency?
same institutional scope?
same aggregation level?
```

Return:

```text
COMPARABLE
PARTIALLY_COMPARABLE
NOT_COMPARABLE
```

Example:

```json
{
  "comparability": "PARTIALLY_COMPARABLE",
  "reason": "University A reports gross research expenditure while University B reports externally funded research only."
}
```

---

# 29. MULTI-UNIVERSITY DATA ISOLATION

Every document and fact must be associated with a university identity.

At minimum:

```text
university_id
document_id
report_type
report_year
reporting_period
```

Never allow a retrieval query for University A to accidentally merge University B's evidence.

---

# 30. MULTI-PDF SUPPORT

The architecture must support:

```text
one PDF
multiple PDFs
multiple years
multiple universities
mixed report types
incremental uploads
```

New documents should be added incrementally.

Avoid full re-indexing unless necessary.

---

# 31. UNIVERSITY-SPECIFIC REPORT DIALECTS

Different universities structure reports differently.

The system should learn reusable document patterns such as:

- repeated section titles,
- metric synonyms,
- organization naming patterns,
- table labels,
- recurring abbreviations.

Use configuration and metadata before fine-tuning.

Example:

```yaml
university:
  canonical_name: "University A"
  aliases:
    - "University A"
    - "UA"
  metrics:
    research_funding:
      aliases:
        - "research funding"
        - "research support"
        - "externally funded research"
```

Do not hard-code one university into the retrieval engine.

---

# 32. MEMORY — OPTIONAL PHASE, INSPIRED BY REASONINGBANK

After the base system is reliable, create an optional reasoning memory store.

Possible memory items:

```text
retrieval strategy
query decomposition insight
failed tool selection
successful source path
entity ambiguity pattern
metric normalization rule
university-specific reporting pattern
verification failure pattern
```

Example:

```json
{
  "memory_id": "mem_00012",
  "title": "University A uses gross research expenditure wording",
  "content": "For this report family, 'research expenditure' is often distinguished from 'externally funded research'. Verify metric definition before comparison.",
  "source": "verified_trajectory",
  "confidence": 0.91
}
```

Do not allow memory to override source evidence.

Memory should guide retrieval, not become an unverified knowledge source.

---

# 33. A2A — FUTURE INTEROPERABILITY, NOT VERSION-1 REQUIREMENT

The Agent2Agent (A2A) protocol is an open protocol designed for agent interoperability and collaboration.

Current A2A specification:
- https://github.com/a2aproject/A2A

Use A2A only when there is a real need to connect independently deployed agents.

For version 1, keep logical agents within one application unless external interoperability is needed.

---

# 34. MCP — TOOL INTEROPERABILITY

Model Context Protocol can be evaluated for exposing tools/resources to the agent.

Potential MCP resources/tools:

```text
Neo4j
source documents
retrieval engine
evaluation engine
file store
browser/search when explicitly allowed
```

However, do not turn every internal Python function into an MCP service.

Use MCP where a stable tool/resource boundary is genuinely helpful.

---

# 35. NEO4J RECOMMENDATION

Neo4j should be the primary graph platform to test.

Use the current official Neo4j GraphRAG Python package rather than old/deprecated package names.

The package documentation states that `neo4j-genai` is deprecated and that `neo4j-graphrag` is the maintained continuation.

Reference:
- https://neo4j.com/docs/neo4j-graphrag-python/current/

As of Neo4j 2026.01+, evaluate in-index vector filtering using `SEARCH` for suitable metadata constraints.

This is particularly valuable for university queries constrained by:

```text
university
report_year
report_type
metric
```

---

# 36. LOCAL DATABASE STRATEGY

For a free project, first attempt:

```text
Neo4j Community Edition
+
Neo4j vector index
+
local model
+
local embedding model
```

Neo4j provides official Docker images for Community Edition.

Reference:
- https://neo4j.com/docs/operations-manual/current/docker/introduction/

If vector requirements become specialized, introduce Qdrant.

Do not run multiple databases without a measured reason.

---

# 37. LOCAL LLM STRATEGY FOR 64 GB RAM + RTX 3090 24 GB

Available hardware:

```text
RAM: ~64 GB
GPU: NVIDIA RTX 3090
VRAM: 24 GB
```

Use local inference as the default design target.

Do not assume a large dense model will fit comfortably in 24 GB VRAM.

Benchmark multiple quantized models.

Candidate families to test:

```text
Qwen
Gemma
Mistral
Llama-family models
```

One model worth benchmarking is a Qwen3 MoE/instruct variant appropriate to the available VRAM and inference engine, but model choice MUST be evidence-based from actual local tests.

Track:

```text
VRAM usage
RAM usage
tokens/sec
first-token latency
structured-output reliability
tool-calling quality
retrieval-grounded answering
numeric reasoning
citation discipline
```

Do not select a model based only on benchmark reputation.

---

# 38. LOCAL INFERENCE ENGINES

Evaluate:

## llama.cpp

Good baseline for lightweight local GPU inference and quantized models.

Reference:
- https://github.com/ggml-org/llama.cpp

## vLLM

Evaluate if higher throughput or server-style batching becomes important.

Do not require vLLM if llama.cpp is sufficient for the solo-developer workflow.

---

# 39. EMBEDDING + LLM SEPARATION

Never couple the LLM to the embedding implementation.

The architecture should look like:

```text
LLMProvider
EmbeddingProvider
RerankerProvider
GraphProvider
VectorProvider
DocumentProvider
```

All should have interfaces.

---

# 40. RERANKING

Initial retrieval should maximize recall.

Then rerank a smaller candidate set.

Possible pipeline:

```text
query
 |
 +--> lexical retrieval
 |
 +--> vector retrieval
 |
 +--> graph retrieval
 |
 v
candidate fusion
 |
 v
reranker
 |
 v
top evidence
```

Benchmark whether a cross-encoder/reranker materially improves answer accuracy.

Do not add a heavyweight reranker unless evaluation demonstrates value.

---

# 41. GRAPH + VECTOR + STRUCTURED FUSION

A good default candidate architecture is:

```text
                Query
                  |
          Query understanding
                  |
       +----------+----------+
       |          |          |
       v          v          v
   Structured   Vector     Graph
       |          |          |
       +----------+----------+
                  |
           Candidate fusion
                  |
               Rerank
                  |
          Evidence verifier
                  |
            Answer planner
                  |
           Grounded answer
```

The system should not force all three retrieval modes for every question.

Choose dynamically.

---

# 42. LONG-CONTEXT STRATEGY

Do not assume that a larger context window automatically solves document reasoning.

Use hierarchical aggregation for large evidence sets.

Possible approach:

```text
100 chunks
  |
  v
10 local evidence groups
  |
  v
3 evidence summaries
  |
  v
final reasoning context
```

But do not summarize away exact numeric evidence.

Keep source facts separately available.

---

# 43. ANSWER CONTRACT

The internal answer object should be structured.

Example:

```json
{
  "answer": "...",
  "claims": [
    {
      "claim_id": "claim_001",
      "text": "University A reported research expenditure of ...",
      "support": [
        {
          "document_id": "uniA_ar_2024",
          "page": 87,
          "section_id": "research",
          "table_id": "table_02",
          "fact_id": "fact_00125"
        }
      ],
      "confidence": 0.96,
      "verification": "passed"
    }
  ],
  "uncertainties": [],
  "comparability": "COMPARABLE"
}
```

This object should be validated before presentation.

---

# 44. FINAL ANSWER STYLE

User-facing responses should distinguish:

### Reported fact
Directly supported by the source.

### Derived calculation
Calculated from reported values.

### Interpretation
Reasoned from multiple verified facts.

### Uncertainty
Evidence is incomplete or conflicting.

Do not blur these categories.

---

# 45. CITATIONS

For each important answer claim, show:

```text
Document
Page
Section/Table
```

Where practical, make the UI capable of linking directly to the semantic HTML node and, ideally, the PDF page/bounding box.

The provenance model should permit:

```text
Answer -> Claim -> Fact -> HTML node -> PDF page
```

---

# 46. COMPARISON OUTPUT

For comparison queries, support:

```text
metric
University A
University B
difference
percentage change
period
comparability status
source evidence
```

But do not show percentage changes when the underlying measures are not comparable.

---

# 47. QUERY TYPES TO SUPPORT

At minimum:

1. Exact fact retrieval
2. Definition retrieval
3. Narrative retrieval
4. Table lookup
5. Time-series comparison
6. University-vs-university comparison
7. Department-vs-department comparison
8. Multi-hop relationship question
9. Why/explanation question
10. Cross-document synthesis
11. Evidence verification
12. Unanswerable question

---

# 48. UNANSWERABLE QUESTIONS

The system must support:

```text
INSUFFICIENT_EVIDENCE
```

rather than hallucinating.

Example:

> Which university had the highest research impact in 2020?

If the reports do not define or report a comparable research-impact measure, the correct answer is that the available sources do not support that comparison.

---

# 49. SECURITY + PRIVACY

Prefer local document processing.

Do not send uploaded PDFs to external APIs unless explicitly configured.

Keep:

- secrets in environment variables,
- document data local,
- logs free of sensitive raw document contents where possible.

---

# 50. OBSERVABILITY

Every ingestion/query should have a trace ID.

Log stages:

```text
ingestion
parsing
canonicalization
schema extraction
HTML generation
chunking
embedding
graph insertion
retrieval
agent decisions
tool calls
reranking
verification
answer generation
citation generation
```

Make debugging possible without reading model internals.

---

# 51. EVALUATION — DO NOT SKIP

Create a golden evaluation dataset.

Example directory:

```text
evaluation/
  questions.json
  answers.json
  sources.json
  metrics.json
```

Question categories:

```text
fact
number
table
comparison
multi-hop
temporal
cross-document
negative/unanswerable
ambiguous
```

Metrics:

### Retrieval

- recall@k
- precision@k
- MRR/nDCG where useful

### Answer

- factual accuracy
- groundedness
- citation correctness
- completeness
- hallucination rate

### Agent

- tool-selection accuracy
- unnecessary calls
- retrieval iterations
- verification failures
- latency

### Pipeline

- parsing success
- page coverage
- table preservation
- provenance coverage

---

# 52. TESTING REQUIREMENTS

Implement:

```text
unit tests
integration tests
parser adapter tests
HTML provenance tests
graph schema tests
vector retrieval tests
hybrid retrieval tests
agent tool tests
claim verification tests
citation tests
comparison tests
regression tests
```

A feature is not complete merely because the demo works.

---

# 53. FAILURE MODES TO EXPECT

Design explicitly for:

- scanned PDFs,
- broken OCR,
- repeated headers,
- repeated footers,
- split tables,
- multi-page tables,
- multi-column layouts,
- ambiguous metrics,
- inconsistent years,
- contradictory reports,
- aliases,
- missing values,
- malformed JSON,
- unsupported PDF features,
- hallucinated entity links,
- graph overpopulation,
- poor chunk boundaries,
- irrelevant retrieval.

---

# 54. PARSER FALLBACK ARCHITECTURE

Do not assume a single parser will dominate every document.

Implement a parser abstraction:

```text
DocumentParser
  |
  +--> DoclingParser
  +--> ExistingTeamParser
  +--> OCRParser
  +--> FutureParser
```

Use document classification or confidence scoring to select/fallback.

Store parser provenance.

---

# 55. CONFIDENCE MUST BE DECOMPOSED

Avoid a single vague confidence score when possible.

Prefer:

```text
extraction_confidence
entity_confidence
relation_confidence
source_authority
retrieval_score
verification_status
```

A final answer confidence can be derived from these components.

---

# 56. LICENSE AND REUSE POLICY

Before borrowing code from inspiration repositories:

1. inspect license,
2. inspect dependency licenses,
3. preserve required notices,
4. avoid copying proprietary code,
5. document borrowed components.

Create:

```text
THIRD_PARTY_NOTICES.md
```

---

# 57. RECOMMENDED INITIAL STACK TO BENCHMARK

## Document layer

```text
Docling
+
existing team parser
```

## Canonical representation

```text
Pydantic domain/document model
```

## Semantic representation

```text
semantic HTML5
```

## Graph

```text
Neo4j Community Edition
```

## GraphRAG library

Start by evaluating:

```text
neo4j-graphrag
```

and compare it with:

```text
LightRAG
LlamaIndex Property Graph
Haystack
custom orchestration
```

## Embedding

```text
BGE-M3 baseline
```

## Vector

```text
Neo4j vector index first
```

## Lexical

```text
Neo4j full-text / BM25-style search
```

## LLM

```text
local quantized Qwen/Gemma/Mistral/Llama-family candidate
```

## Inference

```text
llama.cpp baseline
vLLM benchmark
```

## Agent

```text
custom lightweight orchestrator
OR
Google ADK / Haystack / LlamaIndex if they materially simplify the system
```

---

# 58. FRAMEWORK DECISION MATRIX

The coding agent must benchmark rather than blindly choose.

| Candidate | Strong point | Risk | Project role |
|---|---|---|---|
| Neo4j GraphRAG Python | Official Neo4j graph/vector/retrieval tooling | Tied to Neo4j ecosystem | Primary baseline |
| LightRAG | Lightweight graph + vector RAG | More custom integration may be needed | Strong alternative |
| LlamaIndex | Broad indexing/property-graph/agent ecosystem | Can become abstraction-heavy | Alternative |
| Haystack | Explicit pipelines + agents + retrieval | More framework surface area | Alternative |
| Microsoft GraphRAG | Important research/reference architecture | Current repo is largely maintenance mode | Inspiration/reference |
| Custom | Maximum control/provenance | More engineering responsibility | Likely final custom layer around stable components |

Microsoft's current GraphRAG repository explicitly says the project is largely in maintenance mode and will not be accepting new feature work, so do not make it the automatic foundation. It remains highly useful as an architectural/reference implementation.

Reference:
- https://github.com/microsoft/graphrag

---

# 59. WHAT MICROSOFT GraphRAG IS STILL USEFUL FOR

Study its:

- entity extraction concepts,
- relationship extraction,
- community concepts,
- claims,
- graph-based context construction,
- global/local search ideas.

But do not assume its full current pipeline is the only or best implementation for this project.

---

# 60. LIGHTRAG — STUDY CAREFULLY

Repository:

- https://github.com/HKUDS/LightRAG

Study:

- graph + vector retrieval,
- local model support,
- Neo4j integration,
- incremental updates,
- entity graphs,
- query modes.

Do not copy it wholesale.

Use it to inform architecture and benchmark against the Neo4j-native route.

---

# 61. NEO4J — CURRENT INDUSTRIAL SIGNALS

Current Neo4j materials increasingly position GraphRAG as a context/knowledge layer for agents.

A July 2026 independent study sponsored by Neo4j reported that vector+graph RAG improved truthfulness and answered more questions than vector-only RAG on its tested agent benchmark. The source is vendor-sponsored, so treat the exact percentages as evidence to investigate, not as an unconditional universal claim.

Reference:
- https://neo4j.com/blog/agentic-ai/study-graphrag-ai-agents-80-percent-more-truthful/

Neo4j's March 2026 GraphRAG overview also emphasizes graph-based contextual retrieval, relationships, and multi-hop reasoning.

Reference:
- https://neo4j.com/blog/genai/what-is-graphrag/

---

# 62. INDUSTRIAL PATTERN — KNOWLEDGE LAYER, NOT CHATBOT MEMORY

A strong modern architecture is:

```text
Source systems/documents
        |
        v
Knowledge/context layer
        |
   +----+----+
   |         |
 Graph     Structured
   |         |
   +----+----+
        |
     Retrieval
        |
       Agent
```

This means the graph should store reusable domain knowledge and provenance, while the model is the reasoning layer.

Do not let the LLM become the database.

---

# 63. AGENT MEMORY POLICY

Separate memory into:

```text
Working memory
Conversation state
Retrieval state
Source evidence
Reasoning memory
Long-term domain knowledge
```

The graph is not automatically the same as agent memory.

---

# 64. ZERO-COPY / VIRTUAL DATA IDEA

Modern graph architecture is also moving toward querying existing enterprise data without unnecessary duplication.

Neo4j's 2026 Virtual Graph work is relevant conceptually here.

For this project, the equivalent principle is:

> Do not duplicate the original PDF unnecessarily just to create graph data.

Keep stable references to the canonical source representation.

Reference:
- https://neo4j.com/blog/graph-database/introducing-neo4j-virtual-graph-graph-reasoning-on-the-data-you-already-have/

---

# 65. UI / DEBUG MODE

The eventual UI should allow the user to inspect:

```text
Question
 |
 v
Agent plan
 |
 v
Tools used
 |
 v
Retrieved evidence
 |
 v
Graph path
 |
 v
Verified claims
 |
 v
Final answer
```

Do not expose chain-of-thought.

Show only useful, user-safe evidence and decision metadata such as:

- sources searched,
- retrieval mode,
- evidence count,
- verification state,
- citations.

---

# 66. EXPLAINABILITY REQUIREMENT

The system should answer:

> "Why did you give me this answer?"

with:

```text
Because these official sources contained these facts...
```

not:

```text
Because the model reasoned that...
```

The explanation should be evidence-centric.

---

# 67. AGENT STOP CONDITIONS

The Agent must stop when:

- evidence is sufficient,
- all major claims are verified,
- contradictions are resolved or explicitly reported,
- tool budget is reached,
- the answer is provably unavailable.

Prevent infinite retrieval loops.

Example configuration:

```yaml
agent:
  max_steps: 8
  max_retrieval_rounds: 4
  verification_required: true
```

---

# 68. COST POLICY

Free/local-first is a hard requirement.

Paid APIs may exist as optional adapters.

Core project functionality must not depend on paid services.

---

# 69. REPOSITORY ORGANIZATION

Adapt to the current codebase, but a clean target structure may look like:

```text
app/
  ingestion/
  document_model/
  extraction/
  semantic_html/
  chunking/
  provenance/
  embeddings/
  graph/
  vector/
  lexical/
  retrieval/
  agents/
  verification/
  comparison/
  evaluation/
  api/

configs/
docs/
evaluation/
inspiration/
scripts/
tests/
```

Do not reorganize the repository blindly.

---

# 70. REQUIRED DOCUMENTATION FILES

Create/update:

```text
docs/architecture.md
docs/architecture_decision.md
docs/inspiration_analysis.md
docs/document_model.md
docs/semantic_html.md
docs/provenance.md
docs/graph_schema.md
docs/retrieval.md
docs/agent_architecture.md
docs/comparison_engine.md
docs/evaluation.md
docs/local_setup.md
docs/troubleshooting.md
THIRD_PARTY_NOTICES.md
```

---

# 71. REQUIRED DECISION LOG

Maintain a short architecture decision record.

For every major choice:

```text
Decision
Alternatives
Reason
Evidence
Trade-off
Date
```

Example:

```text
Decision:
Use Neo4j vector index first.

Alternatives:
Qdrant, FAISS.

Reason:
Graph and vector data can remain in one retrieval substrate and current Neo4j versions support in-index filtering.

Trade-off:
Less specialized vector capability than a dedicated vector DB.
```

---

# 72. PHASED IMPLEMENTATION ROADMAP

## Phase 0 — Repository audit

Deliver:

- architecture map,
- module map,
- inspiration analysis,
- dependency map,
- risk register.

## Phase 1 — Canonical document model

Define stable IDs and provenance.

## Phase 2 — Parser comparison

Benchmark:

- existing parser,
- Docling,
- fallback/OCR path.

Use actual project PDFs.

## Phase 3 — Semantic HTML

Make HTML a traceable representation/export.

## Phase 4 — Structured fact layer

Build normalized facts and metric models.

## Phase 5 — Chunking

Structure-aware + contextual chunks.

## Phase 6 — Embeddings

BGE-M3 baseline and benchmark alternatives.

## Phase 7 — Neo4j graph

Insert:

- entities,
- relations,
- facts,
- document hierarchy,
- provenance.

## Phase 8 — Vector + lexical retrieval

Implement hybrid retrieval.

## Phase 9 — Agent router

Implement logical agents and tools.

## Phase 10 — Evidence sufficiency + verification

Make source validation mandatory.

## Phase 11 — Comparison engine

Metric/period/unit normalization.

## Phase 12 — Evaluation

Golden dataset + retrieval + answer + agent metrics.

## Phase 13 — Optimization

Only after evaluation:

- reranker,
- reasoning memory,
- multi-agent parallelism,
- advanced caching,
- additional vector store.

---

# 73. CLI TARGET

Provide commands analogous to:

```bash
python -m app.ingest ./reports
python -m app.index
python -m app.query "Compare University A and University B in research funding from 2021 to 2024"
python -m app.inspect-source --document uniA_ar_2024 --page 87
python -m app.verify
python -m app.evaluate
```

Adapt to existing project structure.

---

# 74. DEV SAMPLE DATA

Create a lightweight sample corpus for development.

The system must not require the complete corpus every time a developer wants to test one component.

---

# 75. PERFORMANCE PRINCIPLES

Use the RTX 3090 intelligently:

- GPU embeddings where supported,
- batch embeddings,
- local quantized LLM inference,
- cache embeddings,
- asynchronous independent retrieval calls,
- incremental graph updates,
- incremental indexing,
- avoid reprocessing unchanged documents.

Measure before optimizing.

---

# 76. CACHING

Consider caching:

```text
PDF parsing
canonical document model
embeddings
entity resolution
frequent graph queries
retrieval results
verification results
```

Cache keys must include relevant versions.

Example:

```text
embedding_model_version
parser_version
schema_version
chunking_version
```

---

# 77. VERSIONED PROVENANCE

If the parser or extraction schema changes, do not silently overwrite provenance.

Store:

```text
parser_version
schema_version
embedding_version
ontology_version
agent_version
```

This allows reproducibility.

---

# 78. REPRODUCIBILITY

A reported answer should be reproducible from:

```text
document IDs
source versions
retrieval configuration
model versions
query
```

Store enough metadata to rerun the retrieval process.

---

# 79. DO NOT USE LLM FOR EVERY DETERMINISTIC TASK

Use code/rules for:

- unit conversion,
- percentage calculations,
- date normalization,
- schema validation,
- exact matching,
- stable ID generation,
- citation formatting,
- deterministic comparisons.

Use LLMs for:

- semantic interpretation,
- ambiguous entity resolution,
- relation extraction where necessary,
- query planning,
- evidence synthesis.

This improves both accuracy and cost.

---

# 80. CRITICAL NUMERIC RULE

Never let the final LLM perform important arithmetic from prose when deterministic code can do it.

Example:

```python
percentage_change = ((new - old) / old) * 100
```

Then the LLM explains the result.

---

# 81. CRITICAL CITATION RULE

Never generate citations after the answer as a cosmetic step.

Citations must originate from the evidence records that supported each claim.

Therefore:

```text
retrieve evidence
 -> create evidence IDs
 -> generate claims linked to evidence IDs
 -> validate claim/evidence links
 -> render citations
```

---

# 82. ANTI-HALLUCINATION RULE

For document-grounded questions:

```text
No evidence = no factual claim.
```

The model must not substitute its pretrained world knowledge for missing university-report evidence unless the user explicitly asks for outside knowledge.

---

# 83. ANTI-BIAS RULE FOR UNIVERSITY COMPARISON

The system must not produce rankings from vague model impressions.

Comparative conclusions must be tied to:

- explicit metrics,
- defined periods,
- source evidence,
- transparent calculations.

Use labels such as:

```text
Reported
Calculated
Derived
Interpretive
Uncertain
```

---

# 84. WHAT SUCCESS LOOKS LIKE

A successful answer should look approximately like:

```text
University A reported ₹125.7 crore in research expenditure for FY2023-24, while University B reported ₹109.4 crore for the comparable period.

University A therefore reported ₹16.3 crore more expenditure (~14.9%).

This comparison is marked COMPARABLE because both reports define the measure at university-wide level and report the same financial period.

Sources:
- University A Annual Report 2024, p. 87, Table 2
- University B Annual Report 2024, p. 91, Table 4
```

Every number must have evidence.

---

# 85. WHAT FAILURE LOOKS LIKE

Bad output:

> University A is better than University B because its research ecosystem seems stronger.

Reason:

- vague,
- subjective,
- unsupported,
- non-comparable.

Another bad output:

> University A spent 125.7 crore in 2024.

when the source actually says:

> 125.7 million INR in FY2023-24.

Reason:

- unit error,
- period error,
- potentially a 100x interpretation error.

---

# 86. RESEARCH / REFERENCE LIST

## Google Research

Agentic RAG — June 5, 2026
https://research.google/blog/unlocking-dependable-responses-with-gemini-enterprise-agent-platforms-agentic-rag/

ReasoningBank — April 21, 2026
https://research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/

Google Research at I/O 2026
https://research.google/blog/a-new-era-of-innovation-google-research-at-io-2026/

TabFM — June 30, 2026
https://research.google/blog/introducing-tabfm-a-zero-shot-foundation-model-for-tabular-data/

Chain-of-Agents
https://research.google/blog/chain-of-agents-large-language-models-collaborating-on-long-context-tasks/

Google Research NLP current index
https://research.google/blog/label/natural-language-processing/

## Google Agent/Platform

Google ADK
https://google.github.io/adk-docs/

ADK coding with AI / Antigravity-related guidance
https://google.github.io/adk-docs/tutorials/coding-with-ai/

Agent Executor
https://cloud.google.com/blog/products/ai-machine-learning/agent-executor-googles-distributed-agent-runtime/

## Document understanding

Docling
https://github.com/docling-project/docling

Supported formats/output
https://github.com/docling-project/docling/blob/main/docs/usage/supported_formats.md

## GraphRAG / Knowledge Graph

Neo4j GraphRAG Python
https://neo4j.com/docs/neo4j-graphrag-python/current/

Neo4j RAG user guide
https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html

Neo4j GraphRAG overview
https://neo4j.com/blog/genai/what-is-graphrag/

Neo4j agentic GraphRAG study
https://neo4j.com/blog/agentic-ai/study-graphrag-ai-agents-80-percent-more-truthful/

LightRAG
https://github.com/HKUDS/LightRAG

Microsoft GraphRAG
https://github.com/microsoft/graphrag

## Retrieval

Anthropic Contextual Retrieval
https://www.anthropic.com/engineering/contextual-retrieval

Qdrant hybrid search
https://qdrant.tech/documentation/search/text-search/hybrid-search/

## Local inference

llama.cpp
https://github.com/ggml-org/llama.cpp

BGE-M3
https://huggingface.co/BAAI/bge-m3

## Agent interoperability

A2A Protocol
https://github.com/a2aproject/A2A

---

# 87. FINAL COMMAND TO THE CODING AGENT

You are not being asked to simply "build GraphRAG."

You are being asked to build a **traceable university-report evidence intelligence system**.

Before writing large amounts of code:

1. Inspect the repository.
2. Inspect all team-built modules.
3. Inspect the entire `inspiration/` directory.
4. Inspect current documentation for the reference projects above.
5. Compare the existing parser with Docling.
6. Decide whether the project's canonical representation should be richer than plain JSON.
7. Preserve the semantic HTML work, but treat it as a traceable representation/export layer rather than assuming it must be the only downstream input.
8. Design the provenance chain before building the graph.
9. Design the ontology before extracting thousands of nodes.
10. Build structured facts before asking the LLM to reason over them.
11. Implement graph + vector + lexical retrieval.
12. Add an Agentic RAG planner with iterative retrieval.
13. Add evidence sufficiency checking.
14. Add claim verification.
15. Add deterministic comparison and arithmetic.
16. Add citations linked to evidence IDs.
17. Evaluate with real representative university reports.
18. Benchmark alternatives instead of assuming a framework is best.
19. Keep the entire system local/free-first.
20. Document every major architectural decision.

The target architecture is:

```text
                COMPLEX UNIVERSITY PDFS
                         |
                         v
             DOCUMENT UNDERSTANDING LAYER
               Docling / Team Parser / OCR
                         |
                         v
                CANONICAL DOCUMENT MODEL
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
     STRUCTURED       SEMANTIC        SOURCE
       JSON             HTML5         EVIDENCE
          |              |              |
          +--------------+--------------+
                         |
                         v
                  DOMAIN EXTRACTION
                         |
        +----------------+----------------+
        |                |                |
        v                v                v
      FACTS           ENTITIES         RELATIONS
        |                |                |
        +----------------+----------------+
                         |
                         v
                    PROVENANCE
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
           NEO4J       VECTOR      LEXICAL
            GRAPH       INDEX       INDEX
             |           |           |
             +-----------+-----------+
                         |
                         v
                   AGENTIC RAG
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
       STRUCTURED      GRAPH          VECTOR
         TOOL          TOOL           TOOL
          |              |              |
          +--------------+--------------+
                         |
                         v
                  EVIDENCE FUSION
                         |
                         v
                 SUFFICIENCY CHECK
                    /          \
                  no            yes
                  |              |
                  +---->--------+
                         |
                         v
                    VERIFICATION
                         |
                         v
                 COMPARISON / REASONING
                         |
                         v
                  GROUNDED ANSWER
                         |
                         v
             SOURCE + PAGE + TABLE + FACT
```

Build the system so that a future developer can replace:

- parser,
- embedding model,
- LLM,
- graph database,
- vector database,
- agent framework

without rebuilding the entire application.

The source document is the truth.

The graph is a reasoning structure.

The vector index is a semantic retrieval structure.

The structured store is the precision layer.

The semantic HTML is the traceability/document representation layer.

The Agent is the orchestration and reasoning layer.

The verifier is the reliability layer.

That separation is the core design principle of this project.
