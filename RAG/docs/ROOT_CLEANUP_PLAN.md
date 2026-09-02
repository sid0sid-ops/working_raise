# RAISE Root Cleanup Plan

This document establishes the authoritative inventory and disposition of all assets currently located in the root repository folder (`C:\Users\Siddharth Tripathi\Documents\raise\`).

The objective is to consolidate the entire project into a single, self-contained application located strictly within `RAG/`.

---

## 1. Inventory & Classification Matrix

| Item | Type | Current Location | Classification | Destination / Action | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`RAG/`** | Directory | Root | **KEEP** | `raise\RAG\` | Canonical project root containing all code, frontend, backend, models, and databases. |
| **`.git/`** | Directory | Root | **KEEP** | `raise\.git\` | Git version control repository metadata. |
| **`.gitignore`** | File | Root | **KEEP** | `raise\.gitignore` | Git ignore rules for the repository. |
| **`README.md`** | File | Root | **KEEP** | `raise\README.md` | Top-level repository overview pointing to `RAG/`. |
| **`LICENSE`** | File | Root | **KEEP** | `raise\LICENSE` | Apache 2.0 / Open Source Project License. |
| **`Download/` (PDFs)** | Directory | Root | **MIGRATE** | `RAG\data\documents\` & `RAG\tests\fixtures\` | 6 academic PDFs migrated to `RAG\data\documents\`. 1 test PDF (`Taxonomy_Stress_Test_Demo.pdf`) migrated to `RAG\tests\fixtures\`. Then delete root `Download/`. |
| **`docker-compose.yml`** | File | Root | **MIGRATE** | `RAG\docker-compose.yml` | Move Docker orchestration inside `RAG/` with relative volumes. Delete root copy. |
| **`Dockerfile`** | File | Root | **MIGRATE** | `RAG\Dockerfile` | Move container buildfile inside `RAG/`. Delete root copy. |
| **`requirements.txt`** | File | Root | **MIGRATE** | `RAG\requirements.txt` | Move Python dependencies inside `RAG/`. Delete root copy. |
| **`.env` & `.env.example`** | File | Root | **MIGRATE** | `RAG\.env` & `RAG\.env.example` | Move environment configuration inside `RAG/`. Delete root copy. |
| **`ui inspiration/`** | Directory | Root | **MIGRATE** | `RAG\inspiration\ui_inspiration\` | Archive reference designs into `RAG\inspiration\`. Then delete from root. |
| **`Document Workspace/`** | Directory | Root | **DELETE** | *None* | Discarded monolithic prototype workspace. |
| **`outputs/`** | Directory | Root | **DELETE** | *None* | Obsolete output directory outside `RAG/`. |
| **`data/` (Root)** | Directory | Root | **DELETE** | *None* | Stale root data folder. Active data lives in `RAG\data\`. |
| **`.runtime/` (Root)** | Directory | Root | **DELETE** | *None* | Stale root runtime cache. Active runtime lives in `RAG\.runtime\`. |
| **`app.py` (Root)** | File | Root | **DELETE** | *None* | Legacy root script. Canonical application is `RAG\app.py`. |
| **`pyproject.toml` (Root)** | File | Root | **DELETE** | *None* | Legacy root package config. |
| **`run_app.bat` & `.ps1`** | File | Root | **DELETE** | *None* | Obsolete root launcher scripts. Canonical launchers are in `RAG\`. |
| **`run_studio.bat` & `stop`**| File | Root | **DELETE** | *None* | Duplicate root launchers. Canonical copies exist in `RAG\`. |
| **`SYSTEM_TOPOLOGY_AND_ENV_MAP.md`** | File | Root | **MIGRATE** | `RAG\docs\SYSTEM_TOPOLOGY_AND_ENV_MAP.md` | Move documentation into `RAG\docs\`. Delete root copy. |

---

## 2. Detailed Breakdown

### KEEP
* `RAG/`: The single canonical application directory.
* `.git/`: Version control history.
* `README.md`, `LICENSE`, `.gitignore`: Repository meta files.

### MIGRATE
1. **Academic PDF Documents** (from `Download/`):
   * `Annual Report 2024-25 final upload.pdf` -> `RAG\data\documents\`
   * `AR_2024-25_Combined_English_Mail.pdf` -> `RAG\data\documents\`
   * `ARE-2016-17.pdf` -> `RAG\data\documents\`
   * `BRIC-Annual-Report-2025-English.pdf` -> `RAG\data\documents\`
   * `IITMRP Annual Report.pdf` -> `RAG\data\documents\`
   * `NIPGR_Annual_Report_2024-25.pdf` -> `RAG\data\documents\`
2. **Test Fixtures**:
   * `Taxonomy_Stress_Test_Demo.pdf` -> `RAG\tests\fixtures\Taxonomy_Stress_Test_Demo.pdf`
3. **Docker & Runtime Config**:
   * `docker-compose.yml` -> `RAG\docker-compose.yml`
   * `Dockerfile` -> `RAG\Dockerfile`
   * `requirements.txt` -> `RAG\requirements.txt`
   * `.env` -> `RAG\.env`
   * `.env.example` -> `RAG\.env.example`
4. **Design References**:
   * `ui inspiration\` -> `RAG\inspiration\ui_inspiration\`

### DELETE
* `Document Workspace\`
* `Download\` (after migration)
* `outputs\`
* `data\` (root)
* `.runtime\` (root)
* `app.py` (root)
* `pyproject.toml` (root)
* `run_app.bat`, `run_app.ps1`, `run_studio.bat`, `stop_studio.bat` (root)

### UNKNOWN
* None. Every item in the root workspace has been audited and classified.

---

## 3. Safety Verification
* `RAG/` will never be targeted by cleanup routines.
* Active databases (`RAG/.runtime/.chromadb`, `RAG/data/processed/`) will remain untouched.
* All scripts will require explicit confirmation or flags before performing deletions.
