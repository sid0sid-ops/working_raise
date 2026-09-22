# RAISE — Advanced RAG Pipeline System

> **Trial & Experimental Research Workstation**

RAISE is an advanced Retrieval-Augmented Generation (RAG) system and interactive research workstation designed for semantic document exploration, contextual intelligence, and knowledge graph analysis. This project represents trial and exploratory work on the RAISE pipeline architecture.

---

## Repository Structure & Branches

This repository coordinates the modular components of the RAISE system across dedicated branches:

| Branch | Purpose | Status |
| :--- | :--- | :--- |
| **`main`** | Repository governance, licensing, and coordination overview. | Active |
| **`frontend`** | Production React 19 + TypeScript research workstation client (deployed to GitHub Pages). | Active |
| **`backend`** | FastAPI gateway, cyclical LangGraph RAG pipeline, ChromaDB vector store, and Neo4j knowledge graph. | Pending / Future initialization |

---

## Collaboration & Modular Development Guidelines

To ensure strict modular separation between the frontend workstation and backend pipeline services, the following cross-branch development protocol is established:

1. **Strict Branch Isolation**:
   - **Backend Developers**: Work exclusively on the `backend` branch. Backend engineers must **not** directly edit, commit to, or push code into the `frontend` branch. Any frontend UI requests, features, or design adjustments should be communicated through issue tickets or architectural recommendations.
   - **Frontend Developers**: Work exclusively on the `frontend` branch. Frontend engineers must **not** directly edit, commit to, or push code into the `backend` branch. Any backend gateway endpoints, schema contracts, or pipeline enhancements should be suggested through issue tickets or contract specifications.

2. **Backend Development Status**:
   - The backend service is being developed independently. The backend developer has **not yet pushed** code to this repository and will initialize and push their work to the dedicated `backend` branch in a future update.

---

## Deployment

The frontend application is continuously built and deployed from the **`frontend`** branch via GitHub Actions to GitHub Pages.

---

## License

This project is licensed under the terms of the Apache License 2.0. See the [LICENSE](LICENSE) file for complete terms and conditions.
