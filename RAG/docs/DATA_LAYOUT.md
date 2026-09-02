# RAISE Data Layout & Storage Architecture

This document specifies the authoritative directory layout and database storage paths for all artifacts in `RAG/`.

---

## 1. Directory Tree

```text
RAG/
├── data/
│   ├── documents/                         # Canonical User PDF Document Store
│   │   ├── Annual Report 2024-25 final upload.pdf
│   │   ├── ARE-2016-17.pdf
│   │   ├── AR_2024-25_Combined_English_Mail.pdf
│   │   ├── BRIC-Annual-Report-2025-English.pdf
│   │   ├── IITMRP Annual Report.pdf
│   │   └── NIPGR_Annual_Report_2024-25.pdf
│   └── processed/                         # Processed Structured Knowledge
│       ├── chunks/                        # Rich context-anchored chunk JSON files
│       │   ├── *_chunks.json
│       ├── graph_triples/                 # Extracted entity & relationship JSON files
│       │   ├── *_triples.json
│       └── ingested_manifest.json         # Authoritative document manifest & state
├── .runtime/
│   ├── .chromadb/                         # Persistent Local ChromaDB HNSW Vector Store
│   └── audio/                             # Local cached TTS speech audio files
├── tests/
│   ├── fixtures/                          # Isolated Test PDF Fixtures
│   │   └── Taxonomy_Stress_Test_Demo.pdf  # (Never exposed in user library)
│   └── test_full_system.py
└── logs/                                  # Execution & diagnostic audit logs
```

---

## 2. Storage Roles & Provenance

| Subsystem | Storage Path | Technology | Description |
| :--- | :--- | :--- | :--- |
| **Original PDFs** | `RAG/data/documents/` | Physical Files | Single authoritative store for deep linking (`#page=N`). |
| **Document Manifest** | `RAG/data/processed/ingested_manifest.json` | JSON | Tracks `document_id`, `filename`, `pages`, `status`, and `deleted_documents`. |
| **Vector DB** | `RAG/.runtime/.chromadb/` | ChromaDB HNSW | Stores 384-dim dense cosine embeddings with page & institution metadata. |
| **Property Graph** | `bolt://localhost:7687` | Neo4j (Cypher) | Live graph nodes (`Organization`, `Person`, `Section`, `IntellectualProperty`) and edges. |
| **Offline Graph Triples** | `RAG/data/processed/graph_triples/` | JSON | Local offline serialization of graph entities and relations. |
| **Test Fixtures** | `RAG/tests/fixtures/` | Physical Files | Isolated test materials strictly excluded from production retrieval. |
