# MASTER ANTIGRAVITY PROMPT — RAISE ACADEMIC GRAPHRAG UI/UX OVERHAUL
## Offline-First Scientific Research Workspace — UI Audit, Redesign & Implementation Specification

> **Purpose:** This is the definitive UI/UX specification for the RAISE Academic GraphRAG application.
>
> **Primary objective:** Transform the current interface from a generic/partially broken chatbot UI into a **premium, offline-first academic research workspace** designed specifically for reading, indexing, understanding, connecting, verifying, and citing information from uploaded academic PDFs.
>
> **IMPORTANT:** The application is intended to run **offline/local-first**. Do not introduce dependency on cloud AI APIs, remote search, Google services, external analytics, or network-only UI functionality unless explicitly required and clearly optional.

---

# 0. NON-NEGOTIABLE PRODUCT IDENTITY

RAISE is NOT:

- a generic chat application
- a web search engine
- a cloud-only AI assistant
- a simple PDF text extractor
- a demo dashboard

RAISE IS:

> **An offline academic research environment that turns local PDFs into searchable, structured, traceable scientific knowledge and lets the user interact with that knowledge conversationally.**

The visual language must communicate:

**PDF → Structure → Chunks → Embeddings → Knowledge Graph → Evidence → Verified Answer**

The interface should make the user feel that they are working with a **research instrument**, not a toy chatbot.

---

# 1. SOURCE-BASED CURRENT SYSTEM CONTEXT

The currently audited implementation contains:

- FastAPI backend
- ChromaDB local vector retrieval
- Neo4j local graph database
- academic PDF extraction
- structure-aware chunks
- claim verification
- grounded answers
- document manifest handling
- answer streaming
- thinking/retrieval animation
- inline citations
- grounded evidence drawer
- voice input
- read-aloud via browser speech
- document upload UI
- question editing/version behavior
- clear chat
- PDF deletion
- source refresh concepts

The current audit identified major functional gaps including:

- broken upload flow caused by backend failure
- Annual Report Vault action incorrectly calling an upload endpoint without files
- confusing multi-file picker behavior
- broken settings interaction
- broken grounded evidence interaction
- broken citation/page navigation
- duplicate evidence entries
- incorrect source counts
- incorrect/misleading grounding numbers
- insufficient document scoping in graph retrieval
- hardcoded/stale values in places
- overly artificial frontend thinking timing
- unwanted Command Palette and Open Neo4j Browser controls
- inconsistent visual/color system
- incomplete linkage between document processing and UI status

This prompt therefore has TWO purposes:

1. Define the desired final UI.
2. Make Antigravity implement it only after respecting the actual backend/data architecture.

---

# 2. IMPLEMENTATION PRINCIPLE

DO NOT simply make the current screen prettier.

Redesign the application around the mental model:

```text
MY RESEARCH
│
├── Documents
│
├── One document / selected documents
│
├── Knowledge graph
│
├── Search + retrieval
│
├── Conversation
│
├── Evidence
│
└── Traceable answer
```

Every visual element should support this workflow.

---

# 3. CURRENT UI — POSITIVE ELEMENTS TO KEEP

The existing application already has useful foundations.

Keep and improve these:

### 3.1 Dual-card / floating workspace concept

The current rounded-card workspace concept is useful.

Keep the visual separation between:

- research/source area
- conversation/answer area

but remove unnecessary visual clutter.

### 3.2 Current progressive answer streaming

The application already supports progressive token/chunk rendering.

KEEP THIS.

Improve it to:

- actual stream chunks where possible
- smooth Markdown rendering
- no duplicated chunks
- no artificial character-by-character typing
- subtle streaming caret
- reliable final answer reconciliation

### 3.3 Thinking/retrieval stages

The current stages are conceptually useful:

```text
Analyzing
Graph search
Vector search
Verification
Synthesis
```

Keep the idea.

BUT:

- do not fake backend activity
- do not pretend exact operations occurred
- synchronize with actual backend states where possible
- otherwise use honest generic statuses

### 3.4 Inline citations

Keep inline citations.

Make them significantly more useful and traceable.

### 3.5 Grounded Evidence Drawer

Keep the drawer concept.

Fix:

- duplicate entries
- page 1 fallback
- incorrect source grouping
- dead interactions

### 3.6 Document/source list

Keep the concept.

Make each source a real live document object.

### 3.7 Voice input

Keep microphone functionality where browser support permits.

### 3.8 Clear Chat

Keep the working Clear Chat behavior.

### 3.9 Delete source

Keep the document deletion interaction and make synchronization reliable.

---

# 4. CURRENT UI — NEGATIVE / REMOVE / FIX

The following should NOT remain in their current form.

## 4.1 Remove Command Palette

Remove:

- Command Palette button
- Ctrl/Cmd+K shortcut
- command palette modal
- dead event handlers
- unnecessary CSS/JS

Normal navigation is sufficient.

## 4.2 Remove Open Neo4j Browser

Remove from user-facing UI:

- Open Neo4j Browser
- related menu entries
- associated dead handlers

Neo4j remains a backend engine.

## 4.3 Reconsider "Sync Indexed Vault"

Do NOT expose confusing developer terminology.

Replace with:

```text
Refresh Sources
```

only if it performs a real synchronization.

If it is redundant with source refresh, remove it.

## 4.4 Remove fake/static metrics

Never display:

- fixed source counts
- fixed grounding percentages
- demo chunk counts
- fake graph node counts
- fake page numbers
- fake citation counts
- stale example questions

## 4.5 Remove confusing technical language from normal UI

Do not expose terms like:

```text
top_k=4
BFS
APOC
embedding dimension
Neo4j traversal
```

to normal users.

Technical diagnostics can exist in an advanced/debug area.

---

# 5. CORE UI ARCHITECTURE

Design the desktop application approximately as:

```text
┌───────────────────────────────────────────────────────────────────┐
│ RAISE    Research Notebook                       Search   ⚙       │
├───────────────┬───────────────────────────────────────────────────┤
│               │                                                   │
│ RESEARCH      │                  CHAT / ANSWER                    │
│               │                                                   │
│ + New Research│                                                   │
│               │                                                   │
│ Documents     │                                                   │
│ ┌───────────┐ │                                                   │
│ │ PDF A     │ │                   Answer                          │
│ │ PDF B     │ │                                                   │
│ │ PDF C     │ │                                                   │
│ └───────────┘ │                                                   │
│               │                                                   │
│ Knowledge     │                                                   │
│ Graph         │                                                   │
│               │                                                   │
│ History       │                                                   │
│               │                                                   │
│ Settings      │                                                   │
│               │                                                   │
├───────────────┴───────────────────────────────────────────────────┤
│                    ASK YOUR RESEARCH                              │
└───────────────────────────────────────────────────────────────────┘
```

The exact geometry can differ, but the information hierarchy should remain.

---

# 6. TOP BAR

Top bar should contain:

LEFT:

```text
RAISE
Academic Research
```

CENTER:

Current notebook/research name.

RIGHT:

- source/search indicator
- settings
- user-independent local/offline status

Potential status:

```text
● Local
```

or:

```text
● Offline mode
```

This is a positive differentiator.

Do not display "online" if external services are not being used.

---

# 7. OFFLINE-FIRST STATUS

Because RAISE is intended to operate locally, make this an intentional part of the UI.

Show a subtle status such as:

```text
● Running locally
```

or:

```text
● Offline-ready
```

On hover:

```text
AI processing, vector search, graph retrieval and document indexing
are running on this computer.
```

Do not claim a model is local unless it actually is.

The status must reflect real application configuration.

---

# 8. OFFLINE-FIRST PRODUCT FEATURES TO SUPPORT

Design for these capabilities:

- local PDF storage
- local extraction
- local embeddings
- local ChromaDB
- local Neo4j
- local retrieval
- local graph processing
- local answer generation when configured
- no cloud dependency for normal document Q&A
- local audio assets
- local settings persistence

The UI should not require a network connection for basic functionality.

---

# 9. OFFLINE MODE FAILURE UX

If the network is disconnected:

do NOT show a scary red error if the application is supposed to work offline.

Instead:

```text
Offline mode
Your local research tools are still available.
```

Only surface errors for components that genuinely require external connectivity.

---

# 10. SIDEBAR INFORMATION ARCHITECTURE

Use:

```text
NEW RESEARCH

RESEARCH
  Documents
  Knowledge Graph
  Conversation History

TOOLS
  Evidence
  Notes

SYSTEM
  Settings
  About
```

Keep sidebar compact.

Do not overload navigation with technical backend controls.

---

# 11. NEW RESEARCH FLOW

"Create New" MUST perform a real action.

Preferred behavior:

click:

```text
+ New Research
```

opens a clean dialog:

```text
Create research notebook

Name
[____________________________]

Description (optional)
[____________________________]

[Cancel] [Create]
```

On create:

- create real notebook/session state
- show it in sidebar
- switch active workspace
- update title
- clear old chat unless the application deliberately retains it
- show toast

If the application currently does not have a persistent notebook entity, implement the smallest coherent local workspace abstraction rather than pretending to create one.

---

# 12. EXISTING RESEARCH / VAULT FLOW

The Annual Report Vault or any other pre-indexed vault must be an actual selectable research collection.

Clicking a vault should:

```text
Open vault
↓
Load its actual document manifest
↓
Load source list
↓
Show available indexed data
↓
Show relevant document graph(s)
↓
Allow asking questions
```

Never send an empty upload request simply because the user clicked a vault.

---

# 13. DOCUMENT MANAGEMENT

Document panel should show actual PDFs.

Each document card:

```text
┌───────────────────────────────────────────┐
│ PDF icon                                  │
│                                           │
│ TP53_review.pdf                            │
│ Research article                          │
│                                           │
│ 18 pages                                  │
│ ✓ Indexed                                 │
│                                           │
│ [Open]                         ⋯           │
└───────────────────────────────────────────┘
```

Metadata must come from actual document state.

---

# 14. DOCUMENT STATUS SYSTEM

Use clear states:

```text
Uploading
Reading PDF
Extracting structure
Creating chunks
Generating embeddings
Building knowledge graph
Finalizing index
Ready
Failed
```

For a document in progress:

```text
TP53_review.pdf

Building knowledge graph…

██████████████░░░░
```

Only show percentages when real progress exists.

Otherwise:

```text
Building knowledge graph…
◌
```

---

# 15. PROCESSING DETAIL VIEW

Clicking a processing document should optionally show:

```text
Processing TP53_review.pdf

✓ File received
✓ PDF validated
✓ Text extracted
✓ Structure detected
✓ 114 chunks created
◌ Generating embeddings
○ Building knowledge graph
○ Finalizing index
```

Again, values must be actual.

This view is especially useful for large academic PDFs.

---

# 16. UPLOAD UX

Upload must clearly distinguish:

### Upload one PDF

```text
Upload academic PDF
```

### Upload multiple PDFs

```text
Upload multiple PDFs
```

Do not silently provide multi-select without telling the user.

Suggested drop area:

```text
Drop academic PDFs here

or

[ Browse files ]

PDF, PDF batch upload supported
All processing stays local
```

---

# 17. MULTI-PDF UPLOAD

When several files are selected:

display:

```text
3 documents selected

✓ paper_A.pdf
◌ paper_B.pdf
◌ paper_C.pdf
```

Each file gets its own progress/status.

Never make a multi-file process appear as a single mysterious spinner.

---

# 18. DUPLICATE UPLOAD

If a document already exists:

display:

```text
This document is already in the research library.

[Keep existing] [Re-index]
```

Do not silently create duplicate embeddings.

---

# 19. DOCUMENT SOURCES

Show source count correctly.

Separate:

```text
Documents in notebook: 3
```

from:

```text
Sources used in this answer: 2
```

and:

```text
Evidence passages: 5
```

Do not mix these concepts.

---

# 20. SOURCE OF TRUTH

All document/source UI must derive from a real document manifest or equivalent backend source of truth.

Never use frontend constants for source counts.

---

# 21. CHAT WORKSPACE

The chat should remain central.

Use a readable maximum width:

approximately:

```text
760–960px
```

depending on screen size.

Do not make answers span the entire monitor.

---

# 22. EMPTY CHAT STATE

Use an academic research zero state.

Example:

```text
Explore your literature

Ask questions across your indexed PDFs,
compare findings, trace evidence, and
follow concepts through the knowledge graph.

What would you like to investigate?

[ Compare two studies ]
[ Explain a mechanism ]
[ Find supporting evidence ]
[ Summarize key findings ]
```

Suggested prompts must be based on available content where possible.

Never show stale demo questions.

---

# 23. QUESTION COMPOSER

The composer should feel like a premium research input tool.

```text
┌──────────────────────────────────────────────────────────────┐
│ Ask about your indexed research…                            │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ + File     Sources: All ▾          🎙       ↑                │
└──────────────────────────────────────────────────────────────┘
```

Functions:

- text input
- auto-resize
- upload
- source scope
- microphone
- send
- stop generation
- keyboard shortcuts where useful

---

# 24. QUESTION SOURCE SCOPE

Add a source selector:

```text
Sources: All documents ▾
```

Options:

```text
All documents
TP53_review.pdf
Annual_Report.pdf
Methods.pdf
```

When a document is selected:

retrieval and graph context must respect that scope.

---

# 25. SINGLE-DOCUMENT RESEARCH MODE

This is a first-class feature.

When the user is reading one PDF:

```text
Reading:
TP53_review.pdf
```

Question:

```text
What evidence does this paper provide for mitochondrial apoptosis?
```

The answer should be grounded primarily/only in this document according to selection semantics.

The UI should make that clear.

---

# 26. MULTI-DOCUMENT RESEARCH MODE

When "All documents" or selected multiple documents is active:

```text
Researching 3 documents
```

Answer provenance must indicate:

```text
According to TP53_review.pdf…[1]

Annual_Report.pdf reports…[2]
```

Do not blur multiple documents into one source.

---

# 27. USER MESSAGE

Keep it compact.

Example:

```text
How does TP53 regulate apoptosis?                         ✎
```

Actions appear on hover.

---

# 28. EDIT QUESTION

Clicking edit should transform the message into:

```text
┌────────────────────────────────────────────────────┐
│ How does TP53 regulate apoptosis?                  │
│                                                    │
│ Cancel                             Save & ask ↑    │
└────────────────────────────────────────────────────┘
```

Editing must use actual message state.

---

# 29. QUESTION VERSION HISTORY

Provide an unobtrusive version history.

Example:

```text
Question history

V1  How does TP53 regulate apoptosis?
V2  How does TP53 regulate mitochondrial apoptosis?
V3  What evidence supports mitochondrial TP53 apoptosis?
```

Each version:

- timestamp if available
- question text
- source scope
- ability to restore/use

Do not clutter the normal conversation.

---

# 30. ANSWER DESIGN

Assistant answers should visually communicate scientific structure.

Recommended hierarchy:

```text
Answer

Overview

Mechanism

Evidence

Interpretation

Limitations

Sources
```

But sections should be generated only when useful.

Do not force every answer into six sections.

---

# 31. ANSWER TYPOGRAPHY

Use:

- 15–16px body
- 1.6–1.7 line height
- generous paragraph spacing
- 18–22px section headings
- restrained bold
- high readability

The answer should resemble a high-quality digital scientific document.

---

# 32. STREAMING ANSWERS

Keep progressive streaming.

Requirements:

- actual incremental chunks where possible
- smooth update
- no duplicate text
- no lost text
- no whole-DOM re-render every chunk
- streaming caret
- correct final Markdown
- correct final citation mapping

Use chunks/tokens, not one-character animation.

---

# 33. STREAMING CARET

During answer generation:

```text
...
current sentence▌
```

When complete:

fade out.

Keep it subtle.

---

# 34. STOP GENERATION

During generation:

send button becomes:

```text
■ Stop
```

Clicking:

- cancels request
- preserves already received answer text
- removes loading state
- enables normal controls

---

# 35. AUTO-SCROLL

While streaming:

if user is at bottom:

scroll automatically.

If user scrolls upward:

stop auto-scroll.

Show:

```text
↓ New answer content
```

Clicking returns to bottom.

---

# 36. ANSWER ACTIONS

After each answer:

```text
Copy
Read aloud
Save to notes
Regenerate
Sources
More
```

Only show actions that are actually implemented.

---

# 37. READ ALOUD

Keep read-aloud.

Requirements:

- local/browser TTS preferred
- no cloud dependency
- strip Markdown noise
- strip citation syntax
- pause/resume where available
- stop
- visible state

When speaking:

```text
🔊 Reading
```

or a clear stop icon.

---

# 38. LOCAL AUDIO LIBRARY

Audit the existing local Qwen3-TTS / realistic voice resources.

Use local assets where appropriate.

Architecture:

```text
Answer text
↓
Local TTS/audio layer
↓
Audio player
↓
Play / pause / stop
```

Do not send academic text to a cloud TTS provider unless explicitly enabled.

---

# 39. AUDIO PLAYER

For generated/local audio:

use a compact player:

```text
◀  00:14 ━━━━━━━──── 00:42  🔊
```

Controls:

- play/pause
- seek
- volume
- stop
- playback speed if appropriate

Do not make audio UI dominate the answer.

---

# 40. VOICE INPUT

Keep microphone.

Visual states:

```text
🎙 Start
```

then:

```text
● Listening…
```

then:

```text
✓ Insert transcript
```

Do not require network speech recognition if the installed architecture can support local transcription.

If browser-native recognition requires a network-dependent implementation, clearly treat it as optional rather than core offline functionality.

---

# 41. SOURCE / EVIDENCE PANEL

The evidence panel is one of the most important components.

Use:

```text
Grounded evidence

2 sources · 5 passages

SOURCE 1
TP53_review.pdf
Pages 14, 22

SOURCE 2
Apoptosis_review.pdf
Page 31
```

Then expand individual passages.

---

# 42. EVIDENCE DE-DUPLICATION

Never show identical evidence repeatedly.

Stable identity should use something such as:

```text
document_id + page + chunk_id
```

when available.

Do not deduplicate solely using visible text if stable IDs exist.

---

# 43. CITATION DESIGN

Inline citation:

```text
TP53 can induce pro-apoptotic transcription.[1]
```

Make `[1]`:

- clickable
- hoverable
- keyboard accessible

---

# 44. CITATION HOVER

Hover:

```text
TP53_review.pdf
Page 14
```

Optionally:

```text
Relevant excerpt:
"......"
```

Keep the tooltip compact.

---

# 45. CITATION CLICK

Click `[1]`:

Open evidence drawer to the exact evidence item.

Example:

```text
SOURCE 1

TP53_review.pdf

Page 14

Relevant excerpt:
<real extracted text>

[Open PDF page]
```

---

# 46. PAGE NUMBER ACTION

Page numbers must be interactive.

Clicking:

```text
Page 14
```

must navigate to the actual PDF page.

Do NOT display decorative page numbers.

---

# 47. PDF PAGE DEEP LINKING

Where technically reliable:

```text
document.pdf#page=14
```

or equivalent viewer navigation.

Prefer actual page navigation.

---

# 48. PAGE METADATA

Page numbers must originate from PDF extraction/chunk metadata.

Never use:

```text
page = 1
```

as a silent fallback for unknown pages.

If unavailable:

```text
Page unavailable
```

is preferable to fabricated data.

---

# 49. EVIDENCE EXCERPT

The evidence UI should quote/paraphrase only the actual stored/retrieved source passage.

Do not synthesize a fake "excerpt."

---

# 50. SOURCE GROUPING

If one PDF contributes multiple chunks:

show:

```text
TP53_review.pdf
Pages 14, 22

2 evidence passages
```

not:

```text
Source 1
Source 2
Source 3
```

for the same document.

---

# 51. SOURCE COUNT RULE

A "source" means a distinct contributing document unless a UI label explicitly says otherwise.

Example:

```text
3 PDFs loaded
2 PDFs cited
5 evidence passages
```

This prevents the current "3 PDFs but 4 sources" problem.

---

# 52. TRACEABILITY

For every cited claim, the user should be able to walk:

```text
Claim
↓
Citation
↓
Evidence
↓
Chunk
↓
PDF
↓
Page
↓
Original passage
```

This is a defining feature of RAISE.

---

# 53. GROUNDING / TRACEABILITY METRIC

Only display a percentage if the backend genuinely computes it.

Otherwise display:

```text
Source grounded
```

or:

```text
Evidence-backed answer
```

Do not show a fake "84%" merely because a design mockup has one.

---

# 54. EVIDENCE QUALITY INDICATOR

Use qualitative labels where percentages are unavailable:

```text
Strong source support
Partial source support
Limited source support
Insufficient source evidence
```

Only if the backend can responsibly support such labels.

---

# 55. GRAPH EXPLORER

Expose Knowledge Graph as a normal research feature, not a developer debugging feature.

Navigation:

```text
Knowledge Graph
```

Header:

```text
Document:
[ TP53_review.pdf ▾ ]
```

Controls:

```text
Zoom
Fit
Reset
Expand
```

---

# 56. PER-PDF GRAPH REQUIREMENT

This is mandatory.

Default graph view:

```text
Selected PDF
→ only its relevant graph
```

Do NOT combine all PDFs into a single indistinguishable graph.

---

# 57. GRAPH DATA ISOLATION

Every graph node/relationship should be traceable to:

```text
document_id
```

or equivalent source identity.

Graph queries must be document-scoped when a document is selected.

---

# 58. MULTI-PDF GRAPH MODE

A deliberate "Compare documents" mode may exist later.

Do not silently merge graphs.

If combined graph is supported:

label it explicitly:

```text
Cross-document graph
```

and visually distinguish document provenance.

---

# 59. GRAPH NODE TYPES

Use visually distinguishable but restrained styles for:

- document
- gene
- protein
- pathway
- disease
- compound
- method
- institution
- concept
- result

Do not use rainbow colors for everything.

Use category accents sparingly.

---

# 60. GRAPH INTERACTION

Click node:

show:

```text
TP53

Mentioned in:
TP53_review.pdf

Pages:
14, 17, 28

Related concepts:
BAX
MDM2
apoptosis
```

The node panel should connect directly to evidence.

---

# 61. RESEARCH CONTEXT BAR

When viewing a source:

show:

```text
Researching:
TP53_review.pdf
```

When multiple:

```text
Researching:
3 selected documents
```

This prevents source ambiguity.

---

# 62. DOCUMENT READER

Provide an optional document reading mode.

Suggested layout:

```text
┌──────────────────┬─────────────────────────────────────┐
│ Sections         │ PDF                                 │
│                  │                                     │
│ Abstract         │                                     │
│ Introduction     │        Actual PDF content           │
│ Methods          │                                     │
│ Results          │                                     │
│ Discussion       │                                     │
└──────────────────┴─────────────────────────────────────┘
```

The user can read the paper and ask questions alongside it.

---

# 63. READER + CHAT MODE

A powerful research interaction:

```text
PDF viewer                     Chat

Page 14                        Explain this section

Highlighted excerpt            Why is this important?
```

The selected passage can become question context.

This is a high-value feature for academic use.

---

# 64. HIGHLIGHT → ASK

Allow:

Select text in PDF/read mode
→

```text
Ask RAISE about this
```

Then composer receives:

```text
Selected passage:
"..."

Question:
Why is this finding important?
```

The selected source and page remain attached.

---

# 65. SEARCH WITHIN DOCUMENTS

Add local source search.

Search:

```text
Search your research library…
```

Search should operate locally over:

- filenames
- titles
- extracted metadata
- indexed chunks

No external search required.

---

# 66. SEMANTIC SEARCH UI

Optional research search mode:

```text
Semantic search

[ mitochondrial apoptosis ]

5 matching passages
```

Each result:

```text
TP53_review.pdf
Page 14
Similarity: <actual value if appropriate>

Excerpt…
```

Do not expose raw cosine values to normal users unless useful.

---

# 67. RESEARCH HISTORY

History should store:

- notebook/session
- question
- answer
- source scope
- citations
- timestamp

Allow reopening previous research.

---

# 68. SAVE TO NOTES

Add:

```text
Save to notes
```

for useful answer sections.

A note should contain:

- title
- text
- source references
- PDF/page provenance where available
- creation date

This turns RAISE into a research workspace rather than a disposable chat.

---

# 69. NOTES PANEL

Navigation:

```text
Notes
```

Display:

```text
TP53 mitochondrial pathway
Created today

BRCA1 repair mechanism
Created yesterday
```

Click opens note with sources preserved.

---

# 70. ANSWER BOOKMARK

A lighter alternative to notes:

```text
Save answer
```

Saved answers should remain tied to source evidence.

---

# 71. EXPORT

Support offline exports where implemented:

- Markdown
- TXT
- PDF

For academic use, a future BibTeX/reference export could be useful.

Never show an export option before implementing it.

---

# 72. ACADEMIC REFERENCE FORMATTING

Where source metadata exists, allow:

```text
Copy citation
```

Potential formats:

- APA
- Vancouver
- Harvard

Only generate complete bibliographic metadata when actually available.

Do not invent authors/DOIs/journal information.

---

# 73. SETTINGS

Settings should actually work.

Recommended sections:

### Appearance

Light
Dark
System

### Chat

Streaming
Auto-scroll
Show retrieval trace

### Audio

Read aloud
Sound effects
Voice settings

### Research

Default source scope
Evidence detail level

### Accessibility

Font size
Reduced motion

### Storage

Show local storage information
Clear cache where safe

---

# 74. LOCAL STORAGE SETTINGS

Because the application is offline-first, consider a storage page:

```text
Local research storage

Documents
1.4 GB

Embeddings
286 MB

Knowledge graph
92 MB

Audio
180 MB
```

Only show actual measured values.

Useful actions:

```text
Open data folder
Rebuild index
Clear cache
```

Only expose if implemented safely.

---

# 75. INDEX HEALTH

Create an optional status card:

```text
Research index

Documents      3
Indexed        3
Embedding DB   Ready
Graph DB       Ready
```

This is more useful than opaque technical controls.

---

# 76. INDEX REPAIR

If index inconsistencies exist:

show:

```text
Index status

3 documents
2 fully indexed

1 requires attention

[Repair index]
```

Only show when detected.

---

# 77. DATABASE DISCONNECTED STATE

If ChromaDB/Neo4j is unavailable:

do not make buttons silently do nothing.

Show:

```text
Knowledge graph unavailable

Your documents are still available.
Reconnect the local graph service to use graph retrieval.

[Retry]
```

Use exact component-specific messaging.

---

# 78. LOCAL MODEL LOADING

If an offline model must load:

show:

```text
Preparing local research model…

Loading model
██████████░░

This may take longer the first time.
```

After successful load:

```text
✓ Local model ready
```

Never pretend the model is loaded if it is not.

---

# 79. FIRST-RUN INITIALIZATION

On first launch:

```text
Welcome to RAISE

Your local research workspace

1. Choose/create a research notebook
2. Add academic PDFs
3. RAISE builds local search + knowledge structures
4. Ask grounded questions
```

Do not make onboarding mandatory every launch.

---

# 80. OFFLINE-FIRST ONBOARDING MESSAGE

Clearly communicate:

```text
Your research data stays on this computer
during normal local operation.
```

Only use this statement if accurate for the entire configured pipeline.

---

# 81. SECURITY / PRIVACY UI

Provide a simple information panel:

```text
Local processing

Your indexed PDFs, embeddings and graph data
are stored in the local RAISE environment.

No external search is required for document Q&A.
```

Do not make stronger privacy guarantees than the implementation supports.

---

# 82. LOADING LANGUAGE

Never display:

```text
Loading…
```

when a more meaningful status is available.

Use:

```text
Reading your PDF…
Extracting academic structure…
Generating embeddings…
Building knowledge graph…
Finding supporting evidence…
Preparing answer…
```

---

# 83. THINKING TRACE

The user should see system progress, not hidden model reasoning.

Good:

```text
✓ Reading indexed sources
✓ Finding relevant passages
◌ Checking supporting evidence
○ Preparing response
```

Not good:

```text
<private chain of thought>
```

Never expose hidden reasoning.

---

# 84. REAL-TIME TELEMETRY

Useful safe telemetry:

```text
3 documents searched
6 passages retrieved
2 documents cited
5 evidence items
```

Only show actual values.

---

# 85. RETRIEVAL TRANSPARENCY

Optional expandable section:

```text
How this answer was grounded ▾
```

When opened:

```text
Documents searched
3

Evidence passages
6

Documents cited
2

Knowledge graph
Used

Claim verification
Used
```

This is user-friendly transparency.

---

# 86. NO FALSE PRECISION

Avoid unnecessary:

```text
95.27%
0.928321 similarity
1,837 nodes
```

unless these numbers are genuinely useful.

Academic users need traceability, not gaming-style metrics.

---

# 87. ANSWER CONFIDENCE DESIGN

Avoid language:

```text
AI confidence: 98%
```

Prefer:

```text
Strongly supported by indexed sources
```

when the backend can support the interpretation.

---

# 88. INSUFFICIENT EVIDENCE

When documents do not support the question:

```text
I couldn't find enough evidence in the indexed documents
to answer this reliably.

Try:
• narrowing the question
• selecting another document
• adding relevant literature
```

This is a core trust feature.

---

# 89. OUT-OF-SCOPE QUESTION

If the user asks something unrelated to the uploaded PDFs:

```text
This research workspace is currently grounded in your indexed documents.

I couldn't find supporting evidence in the active sources.
```

Do not pretend the answer came from PDFs.

---

# 90. CONFLICTING SOURCES

For academic research, source disagreement is valuable.

Display:

```text
Conflicting evidence

Paper A reports…
Paper B reports…
```

Use separate citations.

Never merge contradictory findings into one generic claim.

---

# 91. COMPARISON VIEW

For questions like:

```text
Compare these two studies.
```

Provide a structured comparison:

```text
                    Paper A              Paper B

Method              …                    …
Sample              …                    …
Finding             …                    …
Limitation          …                    …
Evidence            [1]                  [2]
```

This is particularly useful for academic work.

---

# 92. SUMMARY VIEW

When asking:

```text
Summarize this paper
```

show:

```text
Key findings
Methods
Results
Limitations
Important concepts
Sources
```

Ground every factual section in the actual paper.

---

# 93. METHOD EXTRACTION VIEW

Academic users may ask:

```text
What methods were used?
```

Present:

```text
Methods detected

1. RNA-seq
2. Western blot
3. Co-immunoprecipitation
4. Statistical analysis
```

Only where supported by source evidence.

---

# 94. ENTITY VIEW

When RAISE recognizes entities:

```text
Entities

Genes       TP53 · BAX · MDM2
Proteins    …
Pathways    …
Diseases    …
Institutions …
```

Clicking an entity should show source context.

---

# 95. CONCEPT LINKING

When a user clicks a scientific term:

show:

```text
TP53

Mentioned in:
3 sources

Related:
BAX
MDM2
DNA damage
Apoptosis

Evidence:
5 passages
```

This can bridge chat and graph.

---

# 96. DOCUMENT RELATIONSHIP VIEW

Show relationships at document level:

```text
Research library

Paper A ───── references ───── Paper B
   │
   └──────── related concept ───── Paper C
```

Only when actual relationships exist.

Do not fabricate citation relationships.

---

# 97. SEARCH RESULTS DESIGN

Search result card:

```text
TP53_review.pdf
Page 14

"...relevant passage..."

Open
Ask about this
```

Buttons must work.

---

# 98. ASK ABOUT PASSAGE

A retrieved passage should support:

```text
Ask about this
```

This should create a question context bound to:

- document
- page
- chunk
- excerpt

---

# 99. SOURCE OPEN

Opening a PDF should not throw the user back to the file system unexpectedly.

Prefer an in-app viewer or reliable system viewer flow.

---

# 100. SOURCE REMOVAL

Delete interaction:

```text
Remove TP53_review.pdf?

This document and its active index references
will be removed according to your configured
storage/index policy.

Cancel
Remove
```

After successful deletion:

```text
✓ Document removed
```

and refresh live state.

---

# 101. ERROR TOASTS

Use concise notifications:

```text
✓ PDF indexed
✓ Answer copied
✓ Question updated
✓ Source removed
```

Error:

```text
Unable to index this PDF
```

Clicking details can open technical information.

---

# 102. TECHNICAL ERROR DETAILS

Advanced users can open:

```text
Technical details ▾
```

showing:

- endpoint
- error code
- stack-safe message
- timestamp
- component

Do not expose confusing backend details by default.

---

# 103. UI COLOR SYSTEM

The current color combination needs a complete redesign.

Use a restrained system.

Conceptual dark mode:

```text
Background      #0B0D10
Surface         #11151A
Raised          #171C22
Border          #242A32
Primary text    #F2F4F7
Secondary text  #A9B0BA
Muted text      #737B87
Accent          #6D7CFF / equivalent restrained indigo
Success         semantic green
Warning         semantic amber
Error           semantic red
```

Do not use these values blindly.

Use CSS variables.

---

# 104. LIGHT MODE

Use:

- off-white/neutral background
- clean white surfaces
- subtle cool-gray borders
- dark charcoal text
- restrained indigo accent

Avoid neon.

---

# 105. SEMANTIC COLOR RULE

Use colors only for:

- state
- action
- focus
- hierarchy

Do not color every card.

---

# 106. GRADIENT RULE

Gradients should be rare.

A subtle background accent is acceptable.

Avoid bright AI-purple gradients across buttons/cards.

---

# 107. GLASSMORPHISM RULE

Use minimal or no glassmorphism.

Academic software benefits from:

- strong hierarchy
- readability
- stable surfaces
- clear borders

rather than translucent decorative panels.

---

# 108. TYPOGRAPHY

Primary:

```text
Inter
```

Technical:

```text
JetBrains Mono
```

Optional academic serif:

```text
Source Serif 4
```

Do not use more than necessary.

---

# 109. FONT HIERARCHY

Suggested:

Application title:
20–24px

Page title:
28–34px

Section:
18–22px

Body:
15–16px

Metadata:
12–13px

Citation:
11–12px

Technical diagnostics:
11–12px JetBrains Mono

---

# 110. ICON SYSTEM

Use one consistent SVG/icon family.

Material Symbols Rounded is suitable if loaded locally or already packaged.

Recommended:

```text
home
library_books
upload_file
picture_as_pdf
search
edit
delete
content_copy
volume_up
stop
refresh
menu_book
fact_check
hub
travel_explore
psychology
auto_awesome
settings
more_horiz
close
expand_more
expand_less
mic
send
```

Do not mix random emojis as primary controls.

---

# 111. ICON-ONLY ACCESSIBILITY

Every icon-only control needs:

```text
aria-label
```

and tooltip.

---

# 112. BUTTON DESIGN

Primary button:

- clear contrast
- 10–12px vertical padding
- 14px text
- 8–12px radius
- subtle interaction

Avoid oversized pill buttons everywhere.

---

# 113. CARD DESIGN

Main research card:

16–20px radius.

Small utility card:

8–12px radius.

Not every element should be a card.

---

# 114. BORDER SYSTEM

Prefer subtle 1px borders.

Avoid multiple nested border boxes.

---

# 115. SHADOW SYSTEM

Use low-elevation shadows.

Dark mode should rely primarily on:

- contrast
- borders
- surface differentiation

---

# 116. MICRO-ANIMATIONS

Use:

- 120–200ms button transitions
- 180–280ms drawer transitions
- 150–250ms text fades
- subtle status pulses

Avoid:

- bouncing
- excessive spinning
- giant transitions
- particles
- animation for animation's sake

---

# 117. DOCUMENT PROCESSING ANIMATION

Good:

```text
✓ Extracting structure
✓ Creating chunks
◌ Generating embeddings
```

Subtle animated dot on current stage.

---

# 118. GRAPH LOADING ANIMATION

Use:

```text
Loading research graph…
```

with subtle skeleton/graph placeholder.

Do NOT animate hundreds of nodes unnecessarily before data arrives.

---

# 119. ANSWER SKELETON

Before first token:

```text
Researching your documents…

[short skeleton]
[short skeleton]
```

Once answer begins, replace skeleton with actual text.

---

# 120. LATENCY PERCEPTION

UI should respond immediately to user action.

Within the first visual moment:

```text
Question submitted
Researching sources…
```

Never leave a blank gap.

---

# 121. TIMING PRINCIPLE

Do not add artificial 3–5 second waits simply to make AI "feel intelligent."

Show real work.

If processing is genuinely fast:

let it be fast.

Fast is good.

---

# 122. LOCAL PERFORMANCE

The application may perform CPU/GPU-intensive work.

UI must stay responsive during:

- embedding
- graph building
- PDF extraction
- local generation

Use asynchronous operations/background tasks where architecture permits.

---

# 123. LARGE DOCUMENT UX

For a 500+ page paper/report:

the UI must not freeze.

Show:

```text
Processing 520-page document…

12% extracted
```

only when real progress exists.

Allow user to continue navigating the UI if technically possible.

---

# 124. PROGRESSIVE DOCUMENT AVAILABILITY

Where safely supported:

document can move through stages independently.

Example:

```text
PDF uploaded
Text extraction complete
Embedding in progress
```

Do not let "ready" appear before complete indexing.

---

# 125. SOURCE REFRESH

Refresh Sources should:

```text
Read manifest
↓
reconcile actual files
↓
reconcile indexed state
↓
update UI
```

No useless animation.

---

# 126. SETTINGS INTERACTION

Settings must open.

Preferred:

right-side drawer or modal.

Use:

```text
Settings

Appearance
○ Light
● Dark
○ System

Chat
☑ Streaming
☑ Auto-scroll
☐ Retrieval trace

Audio
☑ Read aloud enabled
☐ Sound effects

Accessibility
☐ Reduced motion
```

Every setting must produce a real behavior change.

---

# 127. REDUCED MOTION

Respect:

```css
@media (prefers-reduced-motion: reduce)
```

and provide optional manual setting.

---

# 128. RESPONSIVE DESIGN

Desktop:

sidebar + chat + optional evidence drawer.

Tablet:

collapsible sidebar.

Mobile:

single-column chat.

Source/evidence drawer becomes full-screen sheet.

Composer fixed to bottom with keyboard-safe spacing.

---

# 129. MOBILE COMPOSER

Minimum:

```text
┌──────────────────────────────┐
│ Ask your research…           │
│                              │
├──────────────────────────────┤
│ +       🎙                ↑  │
└──────────────────────────────┘
```

Do not allow keyboard to cover Send.

---

# 130. MOBILE EVIDENCE

Evidence drawer:

```text
Evidence
────────────────────

TP53_review.pdf
Page 14

Excerpt…

[Open page]
```

Full-screen sheet.

---

# 131. ACCESSIBILITY

Must include:

- keyboard navigation
- visible focus
- semantic controls
- labels
- reduced motion
- sufficient contrast
- accessible drawers/modals
- Escape to close
- screen-reader-friendly state changes

---

# 132. KEYBOARD NAVIGATION

At minimum:

Enter:
send

Shift+Enter:
newline

Esc:
cancel editing/close dialog

Tab:
logical navigation

Do NOT reintroduce global command palette just for keyboard shortcuts.

---

# 133. TOOLTIP SYSTEM

For icons:

- Copy answer
- Read aloud
- Regenerate
- Edit
- Delete
- Sources
- Graph
- Settings

Tooltips should be short.

---

# 134. COMMAND PALETTE DECISION

Explicit final decision:

**REMOVE COMMAND PALETTE.**

Normal navigation must be sufficient.

---

# 135. NEO4J BROWSER DECISION

Explicit final decision:

**REMOVE OPEN NEO4J BROWSER FROM USER UI.**

Neo4j remains internal infrastructure.

---

# 136. GRAPH PRESENTATION DECISION

The user should see:

```text
Knowledge Graph
```

not:

```text
Open Neo4j Browser
```

This makes the backend implementation an invisible engineering detail.

---

# 137. SOURCE MANAGEMENT TERMINOLOGY

Prefer:

```text
Research library
Documents
Sources
Evidence
Knowledge graph
```

Avoid:

```text
Vault sync
Neo4j browser
BFS
APOC
subgraph query
```

unless in Diagnostics.

---

# 138. DIAGNOSTICS PANEL

For development only, add an optional:

```text
Diagnostics
```

panel.

It can show:

```text
Backend
ChromaDB
Neo4j
Documents
Retrieved chunks
Graph nodes
Graph edges
Response latency
```

This should not dominate normal UI.

---

# 139. DIAGNOSTICS MUST NOT SHOW PRIVATE REASONING

Allowed:

```text
Retrieved 5 chunks
```

Not allowed:

internal model chain-of-thought.

---

# 140. DEBUGGING MODE

A developer/test mode may expose:

```text
Query
Selected document IDs
Retrieved chunk IDs
Pages
Similarity
Graph nodes
Graph edges
Citation IDs
Evidence IDs
```

This is extremely valuable for fixing the current source-traceability bugs.

---

# 141. OFFLINE AUDIO STATUS

Show if local voice library is available:

```text
Local voice
Ready
```

or:

```text
Local voice
Unavailable
```

Do not silently fall back to an external network TTS service.

---

# 142. NETWORK USAGE TRANSPARENCY

An optional Settings/About panel can state:

```text
Local processing enabled

No external document search is required.
```

Only claim what the actual implementation guarantees.

---

# 143. VISUAL RESEARCH INDICATOR

Use a subtle visual identity:

```text
RAISE
● Local research
```

This can become the product's equivalent of a status badge.

---

# 144. DOCUMENT ICONS

PDF:

Material icon `picture_as_pdf`

Knowledge graph:

`hub`

Evidence:

`fact_check`

Research:

`menu_book`

Use monochrome/semantic icon styling rather than rainbow icons.

---

# 145. DATA DENSITY

Do not fill every available pixel.

Academic software needs whitespace.

Recommended:

- 8px minimum small spacing
- 16px standard
- 24px section spacing
- 32px major sections

---

# 146. ANSWER WIDTH

Long-form scientific content should have a controlled line length.

Avoid:

```text
full 1920px paragraph width
```

Use:

```text
760–900px
```

or equivalent.

---

# 147. TABLES

Scientific tables:

- scroll horizontally on mobile
- clear header
- compact rows
- copy option where useful
- no excessive card-within-card styling

---

# 148. CODE / TERMINAL CONTENT

Use JetBrains Mono.

Copy control.

Horizontal scroll.

Do not let code break page width.

---

# 149. EQUATIONS

If supported:

use KaTeX/MathJax.

Do not display raw LaTeX when renderer exists.

---

# 150. SCIENTIFIC MARKDOWN

Markdown renderer should support:

- headings
- lists
- tables
- blockquotes
- inline code
- code
- equations
- citations

Streaming should not break Markdown.

---

# 151. ANSWER CONCLUSION

For long answers, show an optional compact conclusion:

```text
In brief
...
```

Only when useful.

---

# 152. SOURCE FOOTER

At end of answer:

```text
2 sources cited · 5 evidence passages
```

This should be live data.

---

# 153. SOURCE DETAIL

Clicking source count opens Evidence drawer.

Example:

```text
2 sources cited
```

should be interactive.

---

# 154. RESEARCH TRACE FOOTER

Optional:

```text
Grounded in your local research library
```

This reinforces product identity.

---

# 155. EMPTY EVIDENCE

If no evidence found:

```text
No supporting passages were retrieved from the active sources.
```

Do not render an empty drawer.

---

# 156. NO-GRAPH STATE

If graph unavailable:

```text
Knowledge graph is not available for this document yet.
```

with actual action if repair/reindex exists.

---

# 157. SOURCE-SCOPED ANSWER BADGE

For selected PDF:

```text
Grounded in:
TP53_review.pdf
```

For multiple:

```text
Grounded in:
3 selected documents
```

This is very useful for trust.

---

# 158. ANSWER PROVENANCE FOOTER

Example:

```text
Evidence-backed answer
TP53_review.pdf · pp. 14, 22
```

This is more useful than generic confidence badges.

---

# 159. SOURCE CHIP

Use compact chips such as:

```text
TP53_review.pdf
```

But do not turn every source into a pill if there are many.

---

# 160. RESEARCH MODE INDICATOR

Header:

```text
Mode: Research across 3 PDFs
```

or:

```text
Mode: TP53_review.pdf
```

---

# 161. DOCUMENT SELECTOR

When many files exist:

```text
Search documents…
```

Use virtualized lists if needed for very large libraries.

---

# 162. LARGE LIBRARY

For 100+ PDFs:

group by:

- recent
- alphabetical
- research collection
- selected

Do not render huge lists into DOM unnecessarily.

---

# 163. DOCUMENT METADATA

Useful:

- title
- filename
- page count
- indexed status
- modified time
- processing status

Do not show metadata that does not exist.

---

# 164. FILE SIZE

File size is optional.

Use actual value.

---

# 165. PROCESSING ERROR

Example:

```text
Could not index Annual_Report.pdf

PDF extraction failed.

[Retry]
[Technical details]
```

---

# 166. PARTIAL PROCESSING FAILURE

If embedding succeeded but graph failed:

show:

```text
Partially indexed

Semantic search: Ready
Knowledge graph: Needs repair
```

Do not label entire document simply "Ready."

---

# 167. RECOVERY ACTIONS

A document error card should include:

```text
Retry
Re-index
Remove
```

only when those operations are truly supported.

---

# 168. INDEX CONSISTENCY

Source UI should not show:

```text
Ready
```

if ChromaDB/graph state does not correspond to the document.

---

# 169. DOCUMENT GRAPH STATUS

Optional:

```text
Graph
Ready
```

or:

```text
Graph
Not indexed
```

Useful for debugging and transparency.

---

# 170. DOCUMENT SEARCH STATUS

Optional:

```text
Semantic index
Ready
```

---

# 171. CHAT SOURCE CONSISTENCY

When a document is deleted:

previous answers can remain visible.

But new source lists/citations should not pretend the deleted document remains active.

If old answer provenance is retained intentionally, label it as historical.

---

# 172. QUESTION VERSION SOURCE CONSISTENCY

Each question version should preserve source scope.

Example:

```text
V1
All documents

V2
TP53_review.pdf
```

This is valuable research traceability.

---

# 173. REGENERATE SOURCE CONSISTENCY

Regenerate should use the currently valid source scope.

Do not accidentally switch from one PDF to all PDFs.

---

# 174. COPY ANSWER

Copy clean rendered answer text.

Do not include:

- UI buttons
- hidden metadata
- loading text
- citation tooltip text

Citations can remain in textual form.

---

# 175. COPY CITATION

Optional action:

```text
Copy source citation
```

Useful for academic writing.

---

# 176. SAVE TO NOTES

When saved:

```text
✓ Saved to notes
```

and retain provenance.

---

# 177. DELETE CHAT MESSAGE

Optional future feature.

If implemented, deleting a message should not silently remove source files.

---

# 178. RESEARCH SESSION EXPORT

Optional:

```text
Export research session
```

Could include:

- questions
- answers
- citations
- evidence
- source list

This is valuable for academic work.

---

# 179. ACADEMIC REPORT MODE

Optional advanced future feature:

```text
Generate literature briefing
```

Output:

- topic
- key findings
- consensus
- conflicting evidence
- limitations
- source mapping

Always grounded in selected PDFs.

---

# 180. PAPER COMPARISON MODE

Optional:

```text
Compare documents
```

Select:

```text
Paper A
Paper B
```

Then generate structured comparison.

---

# 181. RESEARCH COLLECTIONS

Instead of one giant vault, support collections:

```text
Cancer Biology
Structural Biology
Systems Biology
Annual Reports
```

Each collection has independent document scope.

---

# 182. COLLECTION UI

Example:

```text
Research collections

Cancer Biology       12 PDFs
Annual Reports        8 PDFs
Protein Structure     5 PDFs
```

This is more scalable than a single global list.

---

# 183. DOCUMENT-SPECIFIC GRAPH

Each collection may contain multiple document graphs.

UI should support:

```text
Collection
→ Documents
→ individual graphs
→ optional comparison graph
```

---

# 184. NO GLOBAL GRAPH BY ACCIDENT

A global cross-document graph may exist internally.

But the user must consciously choose:

```text
Cross-document graph
```

rather than receiving a mixed graph unexpectedly.

---

# 185. GRAPH FILTERS

Useful:

```text
Entity type
Document
Relationship
```

Example:

```text
Show:
☑ Genes
☑ Proteins
☐ Institutions
```

Only if graph visualization can support it.

---

# 186. GRAPH SEARCH

Search entity:

```text
Find in graph…
```

Then focus node.

---

# 187. GRAPH TO EVIDENCE

Click graph edge/node:

```text
View evidence
```

must open the actual supporting passages.

This connects the conceptual graph back to source truth.

---

# 188. RESEARCH WORKFLOW

Ideal flow:

```text
Create Research
↓
Upload PDF
↓
Watch real processing
↓
PDF becomes Ready
↓
Open document
↓
View graph
↓
Ask question
↓
Watch real retrieval
↓
Read streamed answer
↓
Click citation
↓
Open exact page/evidence
↓
Save useful answer
```

---

# 189. VISUAL PRIORITY

The most visually important components are:

1. answer
2. question composer
3. evidence
4. documents
5. research context
6. graph
7. settings

Do not give backend/database controls the same visual importance as the answer.

---

# 190. USER TRUST

The interface should always answer:

```text
Where did this come from?
```

Clicking any factual answer citation should reveal:

```text
Which PDF?
Which page?
Which passage?
```

---

# 191. SCIENTIFIC TRUST MODEL

UI language should distinguish:

```text
Retrieved
Supported
Verified
Inferred
Unknown
```

Only use these labels when backed by actual pipeline semantics.

---

# 192. CLAIM VERIFICATION DISPLAY

If actual claim verification exists:

```text
Claim support

✓ Supported by indexed evidence
```

Click for evidence.

Do not imply external scientific peer review or universal truth.

---

# 193. CLAIM WITH WEAK SUPPORT

Use:

```text
Limited support in indexed sources
```

when applicable.

---

# 194. CONFLICTING EVIDENCE DISPLAY

Use neutral language:

```text
The indexed literature contains differing findings.
```

Then separate sources.

---

# 195. ANSWER GENERATED FROM NO SOURCES

If no source retrieved:

do not present a normal "grounded" answer.

Instead show:

```text
No relevant evidence was found in the active documents.
```

---

# 196. SOURCE FILTER ZERO RESULT

If selected PDF doesn't support question:

```text
No supporting passage was found in:
TP53_review.pdf
```

with action:

```text
Search all documents
```

if desired.

---

# 197. RESEARCH MODE TRANSITION

Changing source scope must be visible:

```text
Sources: All documents
↓
Sources: TP53_review.pdf
```

Do not let scope silently change.

---

# 198. ACTIVE DOCUMENT HIGHLIGHT

Selected document should have clear visual state.

Not just a tiny color difference.

Use:

- accent border
- subtle background
- checkmark

---

# 199. SOURCE SELECTION

Support:

single select
multi-select
all

Avoid confusing checkbox/radio behavior.

---

# 200. DOCUMENT CHIP

For one selected PDF:

```text
📄 TP53_review.pdf ×
```

Remove with x.

---

# 201. SOURCE DROPDOWN

Dropdown should show:

```text
All documents
3 documents

TP53_review.pdf
Annual_Report.pdf
Methods.pdf
```

No fake counts.

---

# 202. SEARCH BOX EMPTY STATE

When no documents:

```text
Upload a PDF to search your research library.
```

---

# 203. SEARCH RESULT PROVENANCE

Each search result must preserve:

```text
document_id
page
chunk_id
excerpt
```

where available.

---

# 204. CACHE BEHAVIOR

UI should reflect actual persisted state after:

- reload
- backend restart
- source refresh

No phantom documents.

---

# 205. RELOAD SAFETY

Reload application:

- documents persist
- index state persists
- selected notebook restores if appropriate
- settings restore
- chat may restore according to session policy

---

# 206. BACKEND HEALTH

Show component status only when useful:

```text
Local engine
● Ready
```

Advanced:

```text
Vector index ● Ready
Graph index ● Ready
Model ● Ready
```

---

# 207. FIRST QUESTION EXPERIENCE

After indexing:

show useful suggested actions:

```text
Explore this paper

Summarize the main findings
Explain the methodology
Find the key mechanisms
What evidence supports the conclusion?
```

Generate from actual document content where possible.

---

# 208. SUGGESTED QUESTION RULE

Do not use stale hardcoded questions associated with unrelated sample documents.

Suggestions should be:

- current document-derived
- collection-derived
- generic but clearly generic

---

# 209. AI UI ELEMENTS WORTH IMPLEMENTING

The following modern AI-product interaction patterns are recommended because they materially help research rather than merely decorating the screen:

### Inline citation hover cards
Instant provenance preview.

### Evidence drawer
Full source trail.

### Retrieval status
Communicates what the system is doing.

### Source scope selector
Makes grounding explicit.

### Suggested research questions
Reduces blank-page friction.

### Streaming answer
Feels responsive.

### Stop generation
User control.

### Regenerate
Useful alternate formulation.

### Save to notes
Research continuity.

### Selected-passage questioning
Highly useful for PDF study.

### Compare documents
Academic workflow.

### Knowledge graph explorer
Makes relationships visible.

### Local/offline status
Communicates architecture.

### Index health
Helps users trust availability.

### Local document search
Avoids external search dependency.

### Reading + chat split view
Excellent for paper analysis.

### Evidence-to-answer linking
Core scientific traceability.

---

# 210. GOOGLE-LIKE / MODERN AI UX ELEMENTS THAT FIT RAISE

Borrow interaction principles, not branding.

Useful patterns include:

- clean omnibar-style search
- command-like source selector
- suggestion chips
- hover preview cards
- compact action rows
- contextual side panels
- smooth expandable sections
- document thumbnails
- clear "working" states
- unobtrusive progress
- contextual actions beside selected content
- keyboard-friendly composer
- clear status indicators
- responsive bottom composer
- large readable result surface

Do NOT copy Google's branding, exact visual language, logos, proprietary assets, or page structure.

---

# 211. NOTEBOOKLM-LIKE PATTERNS THAT FIT RAISE

Use the useful ideas:

- source-first workspace
- document-centric context
- research questions
- source-backed answers
- citations
- research summaries
- source panel

Do not clone branding or exact visuals.

---

# 212. PERPLEXITY-LIKE PATTERNS THAT FIT RAISE

Useful:

- source transparency
- compact citation references
- answer/source relationship
- clear retrieval feedback

But RAISE must remain PDF/local research focused.

---

# 213. CHATGPT-LIKE PATTERNS THAT FIT RAISE

Useful:

- familiar composer
- streaming
- stop
- regenerate
- copy
- edit question
- responsive chat
- voice

Avoid unnecessary cloud-oriented controls.

---

# 214. LINEAR-LIKE PATTERNS THAT FIT RAISE

Useful:

- excellent spacing
- restrained colors
- keyboard efficiency
- clear state
- dense but readable interfaces
- intentional animation

---

# 215. SCIENTIFIC SOFTWARE INSPIRATION

Use concepts from research tools:

- source provenance
- document context
- page navigation
- citation references
- entity relationships
- evidence traceability

---

# 216. THE UI SHOULD FEEL "QUIETLY INTELLIGENT"

Use:

- calm motion
- strong hierarchy
- subtle accents
- concise status language
- high readability

Avoid:

- flashy AI effects
- glowing borders everywhere
- spinning brains
- robot imagery
- noisy particle effects

---

# 217. AI VISUAL IDENTITY

The AI identity can be represented through:

```text
RAISE
✦ Research intelligence for your documents
```

rather than a robot avatar.

---

# 218. AVATAR RULE

Do not use a cartoon AI avatar.

Academic product is stronger when system intelligence is represented through behavior and evidence.

---

# 219. LOADING ICONS

Use semantic icons:

```text
psychology
travel_explore
hub
fact_check
auto_awesome
```

Only when they correspond to actual application stage.

---

# 220. THINKING TRACE FINAL STATE

When complete:

```text
✓ Research completed

3 documents searched
2 documents cited
5 evidence passages
```

Only actual metrics.

---

# 221. ERROR STATE FINAL DESIGN

Never:

```text
Unknown error
```

by itself.

Use:

```text
RAISE couldn't complete this research request.

<simple explanation>

[Retry]
```

with optional technical details.

---

# 222. BACKEND TIMEOUT

If slow:

```text
Still working…

The local research engine is processing this request.
```

Include Cancel.

Do not falsely say "AI is thinking" if the backend is actually stuck.

---

# 223. OFFLINE MODEL FIRST LOAD

If the local model requires a large load:

provide an honest one-time message.

Example:

```text
Preparing local AI model

The first run may take longer while model weights are loaded.
```

This is especially useful on local hardware.

---

# 224. MEMORY / RESOURCE STATUS

Optional advanced indicator:

```text
Local processing
CPU  /  GPU
```

Only include if actual telemetry is available.

Do not overload normal UI with hardware information.

---

# 225. RESOURCE-PRESSURE UX

If local system is under heavy processing:

the UI may say:

```text
Local indexing is using significant system resources.
```

only if real monitoring exists.

---

# 226. DOCUMENT QUEUE

When uploading multiple PDFs:

```text
Processing queue

1. Paper A       ✓ Ready
2. Paper B       ◌ Indexing
3. Paper C       ⏳ Waiting
```

This is much clearer than a single global spinner.

---

# 227. CANCEL UPLOAD

Where supported:

```text
Cancel
```

per document.

Do not pretend cancellation works if backend cannot cancel.

---

# 228. RETRY INDEXING

Failed document:

```text
Retry indexing
```

should re-run the actual pipeline.

---

# 229. INDEXED DOCUMENT BADGE

Use:

```text
✓ Indexed
```

not vague:

```text
Available
```

---

# 230. DOCUMENT READY BADGE

Use:

```text
Ready for research
```

only after all required indexing is complete.

---

# 231. SOURCE DELETE UX

Keep delete accessible but visually secondary.

Use a more menu:

```text
⋯
Open
View graph
Re-index
Remove
```

---

# 232. DOCUMENT CARD ACTIONS

Avoid showing five visible buttons on every card.

Use:

- Open
- status
- More menu

---

# 233. SOURCE PREVIEW

Hover/click could show:

```text
TP53_review.pdf

18 pages
Indexed
5 relevant passages in recent research
```

Only if values are real.

---

# 234. PDF THUMBNAILS

Optional local preview thumbnail can make source selection easier.

Do not generate thumbnails for every page unnecessarily.

---

# 235. DOCUMENT ICON COLOR

Use subtle PDF red only when desired.

Avoid a multicolor rainbow source list.

---

# 236. ACTIVE STATE

Use one accent color consistently.

---

# 237. DARK MODE CONTRAST

Do not use dark-gray text on dark-gray backgrounds.

---

# 238. LIGHT MODE CONTRAST

Do not use ultra-light gray body text.

---

# 239. FOCUS STATE

Use visible accent outline.

---

# 240. DIALOG DESIGN

Modal:

- clear title
- concise description
- content
- primary action
- secondary action
- close

No huge oversized empty modal.

---

# 241. DRAWER DESIGN

Source drawer should slide from right.

Research/navigation drawer may slide from left.

Keep transitions ~200–280ms.

---

# 242. MODAL VS DRAWER

Use modal for:

- create notebook
- delete confirmation
- upload workflow

Use drawer for:

- sources
- evidence
- settings
- document details

---

# 243. TOAST POSITION

Desktop:

bottom-right.

Mobile:

bottom-center.

---

# 244. TOAST TIMING

Approx:

1.5–3 seconds for normal success.

Longer for errors.

---

# 245. CLIPBOARD FEEDBACK

After copy:

```text
✓ Copied
```

---

# 246. AUDIO FEEDBACK

Do not autoplay sounds by default.

Respect a user sound setting.

---

# 247. SOUND SYSTEM

Optional local sound assets can be used for:

- upload complete
- error
- answer complete
- recording state

Keep them extremely subtle.

---

# 248. AUDIO ASSET DISCOVERY

Antigravity should locate the actual existing manga/audio/Qwen TTS assets and determine what is reusable.

Do not hardcode an invented path.

---

# 249. LOCAL ASSET PACKAGING

Preferred:

```text
RAG/static/audio/
```

or project-appropriate static asset directory.

Track which assets are actually used.

---

# 250. AUDIO LEGALITY

Do not blindly copy third-party/proprietary model files into the project without confirming they are available for reuse.

If the assets are user-owned/local, use them according to their licenses and project requirements.

---

# 251. AUDIO FALLBACK

If local neural audio is unavailable:

use browser SpeechSynthesis as a local fallback where possible.

---

# 252. VOICE PREFERENCES

Settings can include:

```text
Voice:
[Local Voice ▼]

Speed:
0.8 — 1.0 — 1.2
```

Only list installed voices.

---

# 253. RESEARCH NOTES

Notes should preserve source links.

Example:

```text
TP53 mitochondrial apoptosis

Note:
...

Sources:
TP53_review.pdf · p.14
Apoptosis_review.pdf · p.31
```

---

# 254. CITATION COPY

Allow:

```text
Copy citation
```

where bibliographic metadata exists.

---

# 255. ACADEMIC WORKFLOW SHORTCUTS

Useful contextual buttons:

```text
Summarize
Explain
Compare
Find evidence
Find limitations
Find methodology
```

These are better than generic chatbot starter buttons.

---

# 256. CONTEXTUAL QUICK ACTIONS

After an answer:

```text
Explain this
Find contradictory evidence
Show supporting passages
Compare with another document
Summarize in notes
```

These should submit real, grounded actions.

---

# 257. SUGGESTION CHIP DESIGN

Compact, muted background.

Do not use giant colored pills.

---

# 258. ANSWER LENGTH CONTROL

Optional:

```text
Answer style:
Concise / Detailed
```

Only add if the backend actually supports it.

---

# 259. TECHNICAL DEPTH CONTROL

Optional future feature:

```text
Technical level:
Overview / Graduate / Expert
```

Useful for academic audiences.

Must affect generation behavior if implemented.

---

# 260. LANGUAGE CONTROL

Optional:

```text
Answer language
```

Only include if supported.

---

# 261. RESEARCH RESPONSE MODES

Potential future modes:

```text
Explain
Summarize
Compare
Extract
Critique
Find evidence
```

These can improve academic usability.

---

# 262. CRITIQUE MODE

Could output:

```text
Strengths
Weaknesses
Evidence
Limitations
Open questions
```

Only when requested.

---

# 263. EVIDENCE-FIRST MODE

Could show:

```text
Evidence first
```

with source passages before synthesis.

This would be highly useful for rigorous academic work.

---

# 264. "WHY THIS ANSWER?" VIEW

A safe transparency panel:

```text
Why this answer?

Documents searched: 3
Relevant passages: 6
Cited documents: 2
Knowledge graph: Used
Claim verification: Used
```

No hidden model reasoning.

---

# 265. ANSWER SOURCE HIGHLIGHT

When user clicks citation, visually highlight the relevant sentence in answer and evidence passage.

This creates a direct claim → evidence relationship.

---

# 266. BIDIRECTIONAL TRACEABILITY

Evidence panel:

click evidence

→ highlight citation in answer.

Answer:

click citation

→ highlight evidence.

This is one of the strongest UI features for RAISE.

---

# 267. CURRENT SOURCE FILTER DISPLAY

Always make active scope visible.

Example:

```text
Using:
TP53_review.pdf
```

or:

```text
Using:
3 selected documents
```

---

# 268. CHAT CONTEXT INDICATOR

At top of chat:

```text
Research context
3 documents
```

This helps avoid accidental context confusion.

---

# 269. SOURCE COUNT CONSISTENCY

A single query should have internally consistent values.

Example:

```text
3 documents searched
2 documents cited
5 passages retrieved
```

All UI locations should derive from the same response object.

---

# 270. NO STATIC "4 SOURCES"

Search and remove any remaining static/fallback values equivalent to:

```text
4 sources
```

---

# 271. NO STATIC "84%"

Search and remove any static/fallback value equivalent to:

```text
84%
```

unless the backend genuinely produces exactly that value for the current query.

---

# 272. NO PAGE-1 FALLBACK

Search for all citation/page defaults.

Replace silent defaults with explicit unknown handling.

---

# 273. EVIDENCE STABLE IDs

Every evidence item should have a stable identity.

Recommended:

```text
evidence_id
```

or:

```text
document_id + chunk_id
```

---

# 274. CITATION STABLE IDS

Every citation should map to stable evidence IDs.

---

# 275. FRONTEND DATA CONTRACT

Do not make the UI infer source identity from filenames where a stable ID exists.

Prefer:

```text
document_id
```

---

# 276. BACKEND DATA CONTRACT RECOMMENDATION

Where possible, evidence objects should expose:

```json
{
  "evidence_id": "...",
  "document_id": "...",
  "filename": "...",
  "chunk_id": "...",
  "page": 14,
  "excerpt": "...",
  "similarity": 0.92
}
```

Only use fields that actually exist.

---

# 277. CITATION CONTRACT RECOMMENDATION

Potential:

```json
{
  "citation_id": 1,
  "evidence_ids": ["evidence_abc"]
}
```

This makes duplicate handling much safer.

---

# 278. DOCUMENT CONTRACT RECOMMENDATION

Potential:

```json
{
  "document_id": "...",
  "filename": "...",
  "status": "ready",
  "page_count": 18
}
```

Only implement if compatible with existing backend.

---

# 279. GRAPH NODE CONTRACT

Potential:

```json
{
  "node_id": "...",
  "document_id": "...",
  "type": "gene",
  "label": "TP53"
}
```

Again, adapt to the current data model.

---

# 280. DATA VALIDATION

Frontend must defensively validate response structures.

If citations malformed:

do not crash chat.

Show a graceful evidence warning.

---

# 281. UI FAILURE ISOLATION

A broken evidence item must not break the entire answer.

A broken graph must not break chat.

A broken audio asset must not break source browsing.

---

# 282. BROWSER CONSOLE

Final implementation should have:

- no uncaught exceptions
- no repeated missing-element errors
- no noisy debug statements in production UI

---

# 283. NETWORK REQUESTS

Every user-visible action should produce a meaningful response.

No:

```text
click
→ nothing
```

---

# 284. BUTTON AUDIT

Before finalizing, inspect every visible button.

For each:

```text
Button
Action
Handler
API
State update
Result
```

Delete non-functional controls.

---

# 285. NO DEAD UI

A visually beautiful dead button is still a bug.

Priority:

**working > decorative**

---

# 286. UI QA MATRIX

Test:

```text
Create New
Annual Report Vault
Upload
Multiple Upload
Refresh Sources
Settings
Grounded Evidence
Citation
Page Number
Read Aloud
Voice
Regenerate
Stop
Clear Chat
Delete PDF
Knowledge Graph
Source Selector
Question Edit
Question Versions
```

---

# 287. LIVE THREE-PDF TEST

Use exactly 3 real PDFs.

Verify:

```text
Documents = 3
```

Then ask a question.

Verify:

```text
retrieved passages = real count
cited documents = distinct real count
evidence entries = unique real items
```

---

# 288. LIVE SINGLE-PDF TEST

Select only PDF A.

Answer must not cite B/C.

Graph must belong to A.

---

# 289. LIVE TWO-PDF TEST

Select A+B.

Ask comparison question.

Answer should identify provenance.

---

# 290. LIVE PAGE TEST

Choose a citation from page > 1.

Click it.

Verify actual page.

---

# 291. LIVE DUPLICATE TEST

Open evidence panel.

Verify no duplicate evidence item.

---

# 292. LIVE RELOAD TEST

Upload PDF.

Reload.

Verify persistence.

---

# 293. LIVE RESTART TEST

Restart application.

Verify source/index state persists as designed.

---

# 294. LIVE DELETE TEST

Delete PDF.

Reload.

Verify it remains deleted.

---

# 295. LIVE OFFLINE TEST

Disable network.

Verify:

- local UI loads
- local sources remain available
- local retrieval works where configured
- voice/local audio behavior follows configuration
- no mandatory cloud API appears

---

# 296. FIRST-PAINT QUALITY

Application should render meaningful UI quickly.

Avoid blank white/black page while JavaScript initializes.

---

# 297. FONT LOADING

Use local fonts or already available assets when offline operation is a requirement.

Do not rely on Google Fonts/CDNs for essential typography in offline mode.

If Inter/other fonts are already bundled, use them.

---

# 298. ICON LOADING

Likewise avoid relying on an external icon CDN for core UI if the app must work offline.

Bundle/localize the icon library where practical.

---

# 299. EXTERNAL ASSETS

Search for:

- CDN scripts
- Google Fonts
- external CSS
- remote icon packages
- remote audio
- external analytics

Classify:

```text
Core dependency
Optional enhancement
Should remove
```

The application should remain usable without internet.

---

# 300. OFFLINE PACKAGING AUDIT

Antigravity must audit:

```text
HTML
CSS
JS
Fonts
Icons
Audio
Models
Libraries
PDF viewer
TTS
```

and identify any hidden remote dependency.

---

# 301. LOCAL PDF VIEWER

Prefer a local/bundled viewer implementation when possible.

Do not require a cloud document viewer.

---

# 302. LOCAL FONT STRATEGY

Bundle:

- primary UI font
- technical font
- optional serif

only if licenses permit.

---

# 303. LOCAL ICON STRATEGY

Bundle one icon set.

---

# 304. LOCAL TTS STRATEGY

Prefer:

1. existing local Qwen TTS/audio assets
2. browser local SpeechSynthesis
3. optional other locally installed engine

Avoid cloud TTS by default.

---

# 305. OFFLINE ERROR MESSAGE

If any optional remote feature is unavailable:

```text
This optional feature is unavailable offline.
Your local research workspace is still available.
```

---

# 306. NO ANALYTICS

Do not add external analytics/tracking by default.

The application is an academic local research tool.

---

# 307. PRIVACY-RESPECTING UI

Do not include advertising UI, tracking banners, or unrelated cloud account flows.

---

# 308. APPLICATION SETTINGS PERSISTENCE

Settings can be stored locally.

Use localStorage/session state carefully.

Do not store huge PDF content in localStorage.

---

# 309. CHAT STATE PERSISTENCE

If implemented:

store only appropriate local metadata.

Large source documents remain in their proper storage layer.

---

# 310. RESEARCH SESSION MODEL

Distinguish:

```text
Documents
Research notebook
Conversation
Evidence
Notes
Graphs
```

Do not collapse all these into one giant frontend object.

---

# 311. COMPONENT STRUCTURE

Suggested:

```text
AppShell
├── TopBar
├── Sidebar
│   ├── ResearchList
│   ├── DocumentList
│   └── Navigation
├── MainWorkspace
│   ├── ResearchHeader
│   ├── Chat
│   │   ├── MessageList
│   │   ├── UserMessage
│   │   ├── ThinkingTrace
│   │   ├── AssistantAnswer
│   │   └── AnswerToolbar
│   └── Composer
├── EvidenceDrawer
├── DocumentViewer
├── GraphViewer
├── SettingsDrawer
├── UploadDialog
└── ToastSystem
```

Adapt to current project architecture rather than blindly introducing a framework.

---

# 312. STATE ARCHITECTURE

Central state should distinguish:

```text
activeResearch
documents
activeDocumentIds
messages
streamingState
questionVersions
evidence
citations
processingDocuments
settings
graphState
audioState
```

Avoid duplicated state.

---

# 313. API EVENT FLOW

Recommended:

```text
User action
↓
set pending state immediately
↓
call API
↓
validate response
↓
update source-of-truth state
↓
render
↓
toast/status
```

---

# 314. NO SILENT FAILURES

Any failed promise must be handled.

Avoid:

```javascript
.catch(() => {})
```

for user-critical actions.

---

# 315. ERROR LOGGING

Development logs can exist.

Production UI should show concise useful errors.

---

# 316. CSS ARCHITECTURE

Use semantic variables.

Example:

```css
:root {
  --bg-app: ...;
  --bg-surface: ...;
  --bg-raised: ...;
  --border: ...;
  --text-primary: ...;
  --text-secondary: ...;
  --text-muted: ...;
  --accent: ...;
  --accent-soft: ...;
  --success: ...;
  --warning: ...;
  --danger: ...;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;

  --transition-fast: 120ms;
  --transition-normal: 180ms;
  --transition-slow: 280ms;
}
```

---

# 317. NO HARD-CODED COLORS

Do not scatter colors across selectors.

---

# 318. RESPONSIVE TOKENS

Use CSS clamp/media queries for:

- padding
- font sizes
- chat width
- sidebar width

---

# 319. DESIGN CONSISTENCY

Use one spacing system.

One radius system.

One shadow system.

One icon system.

One typography system.

---

# 320. VISUAL POLISH ORDER

When polishing the UI prioritize:

1. layout
2. typography
3. spacing
4. source hierarchy
5. answer readability
6. citation design
7. controls
8. animation
9. decorative accents

Do not start with gradients.

---

# 321. ANIMATION POLISH ORDER

Most important:

1. response streaming
2. document processing
3. drawers
4. buttons
5. citation interactions
6. graph transitions

---

# 322. REDUCE ANIMATION ON LOW-END DEVICES

Do not assume a powerful GPU.

---

# 323. GPU/CPU FRIENDLY ANIMATION

Prefer:

- opacity
- transform

Avoid constant:

- box-shadow animation
- blur animation
- huge canvas effects
- expensive filters

---

# 324. GRAPH PERFORMANCE

Only render visible/relevant graph.

Virtualize large node sets where practical.

---

# 325. CHAT PERFORMANCE

Do not continuously recreate the entire message list during streaming.

Update only active message.

---

# 326. LONG CHAT PERFORMANCE

If conversation becomes large:

virtualize message list or otherwise prevent DOM explosion.

---

# 327. SOURCE DRAWER PERFORMANCE

Load excerpts lazily.

Do not load every full PDF passage into DOM.

---

# 328. PDF VIEWER PERFORMANCE

Load PDF viewer when needed, not necessarily at startup.

---

# 329. AUDIO PERFORMANCE

Load large audio assets on demand.

---

# 330. APPLICATION STARTUP

Startup should prioritize:

```text
UI
→ local manifest
→ document states
→ chat
```

then lazy-load heavier tools.

---

# 331. MODEL STARTUP

If model loading is slow:

initialize asynchronously.

UI remains usable.

---

# 332. BACKEND AVAILABILITY

If backend unavailable at startup:

show:

```text
Local research engine unavailable
Retry
```

but keep shell UI visible.

---

# 333. INDEX AVAILABILITY

If database unavailable:

source list can still show stored PDFs if available.

---

# 334. RECOVERY

All important failure states should offer recovery where technically possible.

---

# 335. VISUAL QA CHECKLIST

Inspect at:

```text
1440 × 900
1280 × 800
1024 × 768
768 × 1024
390 × 844
```

Check:

- no overflow
- no clipping
- no dead controls
- no accidental horizontal scrolling
- readable citations
- working composer
- working drawers

---

# 336. BROWSER COMPATIBILITY

Test the application's intended Chromium/Edge environment.

Do not use browser APIs without feature detection where necessary.

---

# 337. VOICE FEATURE FALLBACK

Speech APIs vary.

Gracefully handle unavailable APIs.

---

# 338. LOCAL FILE PATH SAFETY

Never expose sensitive absolute filesystem paths in normal UI.

Use friendly names.

---

# 339. TECHNICAL DEBUG PATHS

Only show exact filesystem path inside developer diagnostics if useful.

---

# 340. DATA MIGRATION

If changing data contracts:

do not invalidate existing indexed PDFs unnecessarily.

Provide migration/rebuild strategy.

---

# 341. GRAPH MIGRATION

If moving from global to document-scoped graph behavior:

preserve/rebuild existing graph data carefully.

Do not simply duplicate all nodes.

---

# 342. CHROMADB MIGRATION

Do not wipe ChromaDB blindly.

Back up before schema changes.

---

# 343. BACKUP SAFETY

Before destructive indexing changes:

create backup or use version control where practical.

---

# 344. DOCUMENT IDENTITY

Use stable IDs.

Filename is not sufficient identity.

---

# 345. SOURCE IDENTITY

Each evidence item maps to one source document.

---

# 346. GRAPH IDENTITY

Each graph can be linked to:

```text
document_id
collection_id
```

depending on architecture.

---

# 347. RESEARCH COLLECTION IDENTITY

If collections exist:

documents belong to a collection.

---

# 348. ANSWER IDENTITY

Each answer/message can have a stable ID.

Useful for:

- citations
- evidence mapping
- regenerate
- notes
- history

---

# 349. QUESTION IDENTITY

Each question version should have stable ID/version.

---

# 350. FRONTEND MESSAGE MODEL

Conceptually:

```javascript
{
  id,
  role,
  content,
  createdAt,
  editedFrom,
  version,
  sourceScope,
  citationIds,
  evidenceIds,
  status
}
```

Adapt to current architecture.

---

# 351. ANSWER STATUS

Use:

```text
queued
researching
streaming
complete
stopped
error
```

instead of many unrelated boolean flags.

---

# 352. DOCUMENT STATUS

Use:

```text
uploading
extracting
chunking
embedding
graph_indexing
ready
failed
```

---

# 353. AUDIO STATUS

Use:

```text
idle
loading
playing
paused
stopped
error
```

---

# 354. DRAWER STATE

Use:

```text
closed
opening
open
closing
```

if needed.

CSS transitions should generally handle animation rather than complex state.

---

# 355. UI DATA INTEGRITY

Any displayed number should be traceable to state.

Examples:

```text
3 Documents
```

must map to:

```text
documents.length
```

or equivalent authoritative source.

---

# 356. EVIDENCE COUNT

Do not count citations to determine document count.

---

# 357. CITATION COUNT

Do not count documents to determine citation count.

---

# 358. PAGE COUNT

Do not confuse PDF page count with cited pages.

---

# 359. GRAPH NODE COUNT

Do not confuse graph node count with evidence passages.

---

# 360. TRACEABILITY SCORE

Do not confuse traceability score with source count.

---

# 361. SOURCE LABELING

Use explicit language:

```text
3 documents
2 cited documents
5 evidence passages
```

This eliminates ambiguity.

---

# 362. SOURCE PANEL HEADER

Example:

```text
Evidence

2 cited documents
5 passages
```

---

# 363. EVIDENCE CARD

```text
TP53_review.pdf
Page 14

Relevant passage
────────────────
...
```

Action:

```text
Open page
```

---

# 364. SOURCE GROUP EXPANSION

Click:

```text
TP53_review.pdf
```

to show all cited passages from that document.

---

# 365. DUPLICATE PROTECTION

Before rendering evidence:

deduplicate by stable evidence identity.

Before rendering documents:

deduplicate by document identity.

---

# 366. PAGINATION METADATA

Preserve page from extraction to UI.

Do not drop metadata at intermediate steps.

---

# 367. METADATA PROPAGATION

Required conceptual path:

```text
PDF
→ extractor metadata
→ chunk metadata
→ embedding metadata
→ retrieval result
→ synthesis/citation
→ UI
```

---

# 368. EXTRACTION VALIDATION

After extraction, inspect:

- page mapping
- section headings
- content
- metadata

---

# 369. CHUNK VALIDATION

Every chunk should retain source provenance.

---

# 370. EMBEDDING VALIDATION

Every embedding record must map to chunk/document identity.

---

# 371. RETRIEVAL VALIDATION

Every retrieved result must map to a known indexed source.

---

# 372. CITATION VALIDATION

Every citation should map to real retrieved evidence.

---

# 373. FRONTEND VALIDATION

The UI should reject or hide malformed citation objects instead of inventing defaults.

---

# 374. ANSWER RENDERING VALIDATION

Sanitize HTML/Markdown.

Prevent unsafe arbitrary HTML injection.

---

# 375. OFFLINE SECURITY

The local app should still validate uploaded files.

Do not trust filename alone.

---

# 376. PDF VALIDATION

Validate MIME/content where practical.

---

# 377. LARGE FILE HANDLING

Avoid loading giant PDFs entirely into browser memory.

---

# 378. FILE UPLOAD FEEDBACK

Immediately show filename and state.

---

# 379. UPLOAD COMPLETE

Once stored:

```text
✓ PDF uploaded
Indexing started…
```

---

# 380. INDEXING COMPLETE

```text
✓ Ready for research
```

---

# 381. SOURCE REFRESH COMPLETE

```text
✓ Sources refreshed
3 documents available
```

Actual number only.

---

# 382. SETTINGS SAVE

Settings should save instantly where simple.

No unnecessary "Save" button for basic toggles.

---

# 383. THEME SWITCH

Theme transition should be subtle.

---

# 384. COLOR TOKENS

One accent family.

Semantic state colors only.

---

# 385. FONTS

If offline is mandatory, essential fonts should be locally available.

---

# 386. ICONS

Essential icons should be local.

---

# 387. AUDIO

Essential audio fallback should work locally where practical.

---

# 388. THIRD-PARTY DEPENDENCIES

Antigravity must identify every external runtime dependency.

---

# 389. OFFLINE AUDIT RESULT

Create a report:

```text
Offline dependency audit

Core feature
Local / External
Status
```

---

# 390. EXTERNAL NETWORK CALL TEST

Disable network and launch.

Record every failure.

Remove network requirement for non-essential UI.

---

# 391. LOCAL MODEL TEST

Run configured local model with network disabled.

Verify generation.

---

# 392. LOCAL VECTOR TEST

Run ChromaDB without network.

Verify retrieval.

---

# 393. LOCAL GRAPH TEST

Run Neo4j locally without internet.

Verify graph query.

---

# 394. LOCAL PDF TEST

Upload PDF offline.

Verify full pipeline.

---

# 395. LOCAL AUDIO TEST

Run read-aloud/audio offline.

Verify configured method.

---

# 396. CORE OFFLINE DEFINITION

Core workflow:

```text
Open app
Upload PDF
Index PDF
Ask question
Retrieve evidence
Generate answer
View citations
Open PDF page
```

must work without internet in the intended environment.

---

# 397. OPTIONAL NETWORK FEATURES

If any are retained:

label clearly:

```text
Optional online feature
```

Do not make them silently mandatory.

---

# 398. PRODUCT MESSAGE

Optional tagline:

```text
RAISE
Read deeply. Connect evidence. Research locally.
```

Keep copy restrained.

---

# 399. BRAND TONE

Use:

- intelligent
- calm
- precise
- academic
- trustworthy

Avoid:

- hype
- salesy language
- "magic"
- "revolutionary"
- childish AI language

---

# 400. FINAL VISUAL TARGET

The final interface should resemble:

```text
A modern research laboratory instrument
+
a premium document reader
+
a serious AI assistant
+
a transparent evidence system
```

not:

```text
a colorful chatbot demo
```

---

# 401. IMPLEMENTATION ORDER

Antigravity MUST implement in this order.

## Phase 1 — Functional foundation

Fix:

- upload
- file picker
- Annual Report Vault
- source refresh
- settings
- evidence opening
- citations
- page navigation
- source count
- grounding score
- duplicate evidence
- document-scoped graph retrieval

## Phase 2 — Data integrity

Fix:

- document IDs
- chunk provenance
- page metadata
- citation/evidence mapping
- graph document scoping
- response schema

## Phase 3 — Offline integrity

Fix:

- fonts
- icons
- PDF viewer
- audio assets
- remote dependencies
- local model flow

## Phase 4 — UI redesign

Then implement:

- layout
- typography
- colors
- document cards
- composer
- evidence drawer
- graph UI
- settings

## Phase 5 — micro-interactions

Then:

- streaming
- progress
- drawers
- tooltips
- toasts
- loading
- transitions

## Phase 6 — research features

Then:

- notes
- compare
- selected passage questioning
- research history
- advanced evidence tools

Do not reverse this order.

---

# 402. DO NOT POLISH BROKEN FUNCTIONALITY FIRST

A dead Upload button with beautiful CSS is still a broken Upload button.

---

# 403. REQUIRED LIVE QA

Before saying complete:

Run:

```text
Create New
Open Annual Report Vault
Upload one PDF
Upload multiple PDFs
Refresh Sources
Open Settings
Change a setting
Ask question
Stream answer
Stop answer
Edit question
Restore question version
Open citation
Open evidence
Open exact page
Read aloud
Clear chat
Delete PDF
Open graph
Change document scope
Reload
Restart
Run offline
```

---

# 404. REQUIRED DATA QA

Use exactly three real PDFs.

Validate:

```text
3 documents
correct indexed states
correct source count
correct citation count
correct evidence count
correct pages
correct graph scope
correct provenance
```

---

# 405. REQUIRED OFFLINE QA

Disable network.

Run:

```text
Upload
Index
Search
Ask
Retrieve
Answer
Citation
PDF page
Voice/local audio
```

All core features must remain functional.

---

# 406. REQUIRED VISUAL QA

Inspect screenshots at:

```text
Desktop
Laptop
Tablet
Mobile
Light
Dark
Upload
Processing
Ready
Error
Empty
Answer
Evidence
Graph
Settings
```

---

# 407. REQUIRED CONSOLE QA

No:

- uncaught errors
- missing selectors
- undefined handlers
- dead API calls
- repetitive warnings

---

# 408. REQUIRED NETWORK QA

Document unexpected external calls.

Core offline workflow must not depend on them.

---

# 409. REQUIRED API QA

Confirm request/response contracts for:

- upload
- refresh
- query
- evidence
- document deletion
- graph
- settings where backend-backed

---

# 410. REQUIRED DATABASE QA

Verify:

### ChromaDB

- active collection
- source metadata
- chunk identity
- duplicate behavior

### Neo4j

- document ownership
- graph isolation
- relationship provenance

---

# 411. REQUIRED FORENSIC QA

Compare implementation against the previously generated audit files:

```text
AUDIT_01_FRONTEND.md
AUDIT_02_BACKEND_PIPELINE.md
AUDIT_03_DATA_AND_DATABASE.md
AUDIT_04_CITATIONS_EVIDENCE.md
AUDIT_05_UI_UX.md
AUDIT_06_PERFORMANCE.md
AUDIT_07_FINAL_ROOT_CAUSE_MATRIX.md
```

Every critical root cause must be explicitly resolved or documented as blocked by a genuine architectural dependency.

---

# 412. REQUIRED FINAL IMPLEMENTATION REPORT

After implementation, Antigravity must produce:

```text
UI_IMPLEMENTATION_FINAL_REPORT.md
```

Include:

1. changed files
2. removed files/controls
3. API changes
4. database/schema changes
5. offline dependency changes
6. new UI components
7. fixed bugs
8. known limitations
9. live test results
10. offline test results
11. visual QA results

---

# 413. FINAL ACCEPTANCE CHECKLIST

## Core function

[ ] Create New works

[ ] Annual Report Vault works

[ ] Upload PDF works

[ ] Multiple PDF behavior is explicit

[ ] Processing state works

[ ] Refresh Sources works

[ ] Settings works

[ ] Toggles work

[ ] Grounded Evidence works

[ ] Citations work

[ ] Page navigation works

[ ] Clear Chat works

[ ] Voice works where supported

[ ] Read aloud works

[ ] Regenerate works

[ ] Stop generation works

[ ] Question edit works

[ ] Question versions work

[ ] Delete document works

[ ] Knowledge Graph works

[ ] Per-PDF graph isolation works

---

# 414. DATA INTEGRITY

[ ] No fake source counts

[ ] No fake grounding score

[ ] No page 1 fallback presented as fact

[ ] No duplicate evidence

[ ] No stale demo questions

[ ] No hardcoded document state

[ ] Stable document IDs

[ ] Stable evidence IDs

[ ] Source provenance retained

[ ] Citation provenance retained

---

# 415. OFFLINE

[ ] Core app works without internet

[ ] Fonts available offline

[ ] Icons available offline

[ ] PDF processing local

[ ] Embeddings local

[ ] ChromaDB local

[ ] Neo4j local

[ ] Local generation works where configured

[ ] Audio works locally where configured

[ ] No hidden cloud dependency for core Q&A

---

# 416. UI

[ ] Professional typography

[ ] Good color harmony

[ ] Dark mode

[ ] Light mode

[ ] Responsive

[ ] Good spacing

[ ] Good loading states

[ ] Good error states

[ ] Accessible

[ ] Reduced motion

[ ] Consistent icons

[ ] No dead buttons

---

# 417. REMOVE

[ ] Command Palette removed

[ ] Open Neo4j Browser removed

[ ] Redundant sync control removed/renamed

[ ] Unused event listeners removed

[ ] Dead CSS removed

[ ] Dead JavaScript removed

---

# 418. FINAL PRODUCT EXPERIENCE

A user should be able to perform this journey naturally:

```text
RAISE
  ↓
Create Research
  ↓
Upload academic paper
  ↓
Watch document become indexed
  ↓
See its research graph
  ↓
Ask:
"How does TP53 regulate apoptosis?"
  ↓
RAISE shows:
Researching sources…
  ↓
Relevant passages retrieved
  ↓
Evidence checked
  ↓
Answer streams
  ↓
Sentence ends with [1]
  ↓
Click [1]
  ↓
TP53_review.pdf · Page 14
  ↓
See exact evidence excerpt
  ↓
Click "Open page"
  ↓
PDF opens at page 14
```

That is the product.

---

# 419. FINAL DESIGN PRINCIPLE

Do not optimize for the appearance of intelligence.

Optimize for:

**clarity + provenance + responsiveness + scientific usefulness + offline reliability.**

The strongest AI UI is not the one with the most animation.

It is the one that makes the user trust:

```text
I know what RAISE is doing.
I know which document it used.
I can inspect the evidence.
I can open the exact page.
I can see the knowledge structure.
My local research environment remains under my control.
```

---

# 420. FINAL ANTIGRAVITY INSTRUCTION

Before writing or significantly modifying code:

1. Read all existing audit files.
2. Inspect the current frontend.
3. Inspect all relevant backend routes.
4. Inspect ChromaDB usage.
5. Inspect Neo4j usage.
6. Inspect PDF extraction metadata.
7. Inspect citation/evidence construction.
8. Inspect the current response schema.
9. Inspect local audio resources.
10. Inspect external/CDN dependencies.
11. Run the application.
12. Reproduce the reported failures.

Then implement.

Do NOT assume the existing "100% active" UI audit was correct merely because a feature was claimed implemented.

Verify reality.

Do NOT use hardcoded values to make the UI appear intelligent.

Do NOT fabricate source data.

Do NOT merge per-document graphs by accident.

Do NOT expose hidden chain-of-thought.

Do NOT introduce cloud dependencies into the core offline workflow.

Do NOT leave dead buttons in the interface.

Do NOT finish until functional QA and visual QA have both passed.

---

# 421. END STATE

RAISE should ultimately feel like:

> **A local academic research operating environment — where PDFs become structured knowledge, knowledge becomes evidence, evidence becomes traceable answers, and every important claim can be followed back to its exact source.**

This is the final design direction.
