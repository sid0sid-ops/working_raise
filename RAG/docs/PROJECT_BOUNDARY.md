# RAISE Project Boundary & Architectural Invariants

## 1. Canonical Project Root
The single authoritative root of the RAISE Academic GraphRAG codebase is:

```text
C:\Users\Siddharth Tripathi\Documents\raise\RAG
```

All application runtime operations, dependencies, Docker orchestration, data storage, tests, and launchers exist strictly within `RAG/`.

---

## 2. Invariants & Rules

1. **No External Workspaces**:
   * All previous prototype monoliths (e.g. `Document Workspace/`) are decommissioned and removed.
   * Do not create parallel application directories (`app2.py`, `new_rag/`, etc.).
2. **Canonical Document Storage**:
   * All user PDF reports are stored in `RAG/data/documents/`.
   * Test fixture PDFs are stored in `RAG/tests/fixtures/` and never appear in the user research library.
3. **Docker Orchestration Inside `RAG/`**:
   * Canonical command: `cd RAG && docker compose up --build -d`.
   * Volume mounts are strictly relative to `RAG/` (`./data/documents`, `./data/processed`, `./.runtime`).
4. **No Cross-Workspace Imports**:
   * No `sys.path.append(...)` pointing outside `RAG/`.
   * All internal imports use relative imports (`from .config import settings`, `from .neo4j_engine import Neo4jDatabase`) or standard package imports.
5. **Separation of Concerns**:
   * **User Space**: Documents, Chat, Grounded Evidence, Knowledge Graph, Notes, Settings.
   * **Developer Space**: Pytest suites (`tests/`), benchmarks (`evaluation/`), diagnostic logs (`logs/`).
