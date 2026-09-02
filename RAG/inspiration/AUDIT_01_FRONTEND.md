# 🔬 AUDIT 01: FRONTEND EVENT HANDLERS, DOM SELECTORS & UI CONTROLS

## Executive Summary
This document provides a forensic audit of all frontend controls, DOM elements, event listeners, modal workflows, and client-side state transitions in `RAG/templates/index.html` and `RAG/static/app.js`.

---

## 1. Comprehensive Control & Button Inspection Matrix

| UI Label / Control | DOM Selector / ID | Registered Handler | Target API Endpoint | Expected Behavior | Actual Observed Behavior | Forensic Severity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Create new research notebook** | `.create-notebook-card` | `onclick="AppRouter.createNewNotebook()"` | None (Client routing) | Clears chat, updates title to "Untitled", opens upload modal | Switches to workspace and opens modal, but fails to create clean notebook session state or persist notebook ID | **HIGH** |
| **Academic Reports Vault** | `.upload-option-card:nth-child(2)` | `onclick="AppRouter.ingestVaultAndOpen()"` | `POST /api/upload-academic-pdfs` | Ingests pre-indexed PDFs in `Download/` and opens workspace | Fails with **HTTP 422 Unprocessable Entity** because backend requires non-empty `files: List[UploadFile]` | **CRITICAL** |
| **Upload academic PDFs (Modal)** | `#modalFileInput` | `onchange="handleModalFileUpload(event)"` | `POST /api/upload-academic-pdfs` | Uploads selected PDF, shows indexing progress, renders source item | Crashes on backend (`NameError: shutil is not defined`) and file input has unwanted `multiple` attribute | **CRITICAL** |
| **Refresh Sources** | `button[title='Refresh Sources']` | `onclick="SourcesModule.loadDocuments()"` | `GET /api/documents` | Re-scans `Download/` and updates source list & counters | Fetches stale `ingested_manifest.json` without re-scanning actual physical files in directory | **HIGH** |
| **Tune Settings** | `button[title='Tune Settings']` | *None* | None | Opens settings drawer/modal for temperature, auto-scroll, theme | **Dead Button**: No `onclick` or event listener attached | **MEDIUM** |
| **View Grounded Evidence** | `button[title='View Grounded Evidence']` | `onclick="EvidenceDrawer.open()"` | None (Reads local state) | Opens right-side drawer with cited passage excerpts | Drawer opens, but displays duplicate cards all hardcoded to "Page 1" due to missing page metadata in synthesis payload | **HIGH** |
| **Inline Citation Badges `[1]`** | `.citation-badge` | `onclick="EvidenceDrawer.highlightCitation(idx)"` | None (Client DOM) | Slides open drawer and smooth-scrolls to cited card | Scrolls to duplicate "Page 1" cards without jumping to verified PDF page | **MEDIUM** |
| **Command Palette (Ctrl+K)** | `button[title='Command Palette']` | `onclick="CommandPalette.open()"` | None | Opens terminal command search | **Unwanted Feature**: User explicitly requested removal of Command Palette button & modal | **LOW (REMOVE)** |
| **Open Neo4j Browser** | `a[title='Open Neo4j Browser']` | Native link `href="http://localhost:7474"` | External `7474` | Opens Neo4j web console | **Unwanted Feature**: User explicitly requested removal of direct database button from UI | **LOW (REMOVE)** |
| **Sync Ingested Vault** | `button[title='Sync Ingested Vault']` | `onclick="triggerBatchIngest()"` | `POST /api/upload-academic-pdfs` | Re-synchronizes entire indexed graph | Fails with HTTP 422 (empty FormData payload) | **HIGH (REPAIR/REMOVE)** |
| **Clear Chat** | `button[title='Clear Chat']` | `onclick="clearConversation()"` | None | Resets message container & state | ✅ **Working Correctly** |
| **Voice Dictation** | `#voiceInputBtn` | `onclick="VoiceModule.toggleInput()"` | Web Speech API | Transcribes spoken audio into Omnibar | ✅ **Working Correctly** (browser permitting) |
| **Read Aloud** | `button[title='Read aloud']` | `onclick="VoiceModule.toggleReadAloud()"` | `speechSynthesis` | Reads answer text cleanly aloud | ✅ **Working**, but lacks realistic local neural TTS engine integration | **MEDIUM** |

---

## 2. Detailed Root Cause Analysis for Core Failures

### 2.1 Failure: "Create New" Appears to Do Nothing
* **File & Line**: `RAG/templates/index.html` (Line 46), `RAG/static/app.js` (Line 115)
* **Code Trace**:
  ```javascript
  createNewNotebook() {
      this.currentNotebook = "Untitled research notebook";
      const titleInput = document.getElementById("projectTitleInput");
      if (titleInput) titleInput.value = "Untitled research notebook";
      HeaderModule.handleTitleChange("Untitled research notebook");
      ChatModule.clear();
      this.showWorkspace();
      this.openUploadModal();
  }
  ```
* **Exact Root Cause**:
  1. `AppRouter.createNewNotebook()` changes the title in memory and clears the chat messages, but does not allocate an isolated session/notebook ID.
  2. Because the active document source list (`#documentListContainer`) is global and loaded from `ingested_manifest.json`, the new notebook immediately displays the old documents from the previous session, making it appear that nothing happened.

### 2.2 Failure: "Annual Report Vault" Does Nothing / Crashes
* **File & Line**: `RAG/templates/index.html` (Line 230), `RAG/static/app.js` (Line 132), `RAG/app.py` (Line 151)
* **Code Trace**:
  ```javascript
  // app.js
  async ingestVaultAndOpen() {
      this.closeUploadModal();
      ToastSystem.show("Ingesting academic vault reports...");
      await SourcesModule.syncVault(); // Calls fetch("/api/upload-academic-pdfs", { method: "POST", body: new FormData() })
  }
  ```
* **Exact Root Cause**:
  1. `POST /api/upload-academic-pdfs` in `app.py` is defined as:
     ```python
     @app.post("/api/upload-academic-pdfs")
     async def upload_academic_pdfs(files: List[UploadFile] = File(...)):
     ```
  2. Sending an empty `FormData()` without files causes FastAPI to reject the request with `422 Unprocessable Entity`.
  3. The promise rejects or receives an error JSON, leaving the UI state unchanged.

### 2.3 Failure: PDF File Picker Allows Multiple PDFs Unexpectedly
* **File & Line**: `RAG/templates/index.html` (Line 223)
* **Code Trace**:
  ```html
  <input type="file" id="modalFileInput" multiple accept=".pdf" style="display:none;" onchange="handleModalFileUpload(event)">
  ```
* **Exact Root Cause**:
  The `multiple` attribute is hardcoded on the file input, causing the native OS file picker to allow multi-file selection even when the user intends to upload a single document. Furthermore, the upload handler does not provide individual per-file progress cards when multiple files are selected.

### 2.4 Failure: PDF Uploading Fails Silently (Plus -> Upload -> PDF Selected -> Nothing Happens)
* **File & Line**: `RAG/app.py` (Line 172)
* **Code Trace**:
  ```python
  with open(dest_path, "wb") as buffer:
      shutil.copyfileobj(upload_file.file, buffer)
  ```
* **Exact Root Cause**:
  `shutil` was not imported in `RAG/app.py`. When a user selects a PDF and submits the multipart request, the FastAPI endpoint throws an unhandled `NameError: name 'shutil' is not defined`, returning HTTP 500. The frontend catch block logs the error to the browser console but does not display an actionable error dialog to the user.

### 2.5 Failure: "Refresh Sources" Does Not Synchronize Physical Files
* **File & Line**: `RAG/static/app.js` (Line 487), `RAG/app.py` (Line 62)
* **Code Trace**:
  ```python
  @app.get("/api/documents")
  async def get_documents():
      if not MANIFEST_FILE.exists():
          return {"documents": []}
      manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
      return {"documents": manifest.get("ready_documents", [])}
  ```
* **Exact Root Cause**:
  `/api/documents` purely reads `ingested_manifest.json`. It never inspects the actual `Download/` directory on disk. If a PDF is placed in `Download/` externally or removed, clicking "Refresh Sources" returns stale manifest data.

---

## 3. Required Action Items for Frontend

1. **Remove Unwanted Controls**:
   * Delete Command Palette button (`terminal` icon), modal, and `Ctrl+K` keylistener.
   * Delete "Open Neo4j Browser" button (`hub` icon).
2. **Fix Upload Multi/Single Configuration**:
   * Provide a clear single-file `<input type="file" accept=".pdf">` by default.
   * Add real-time indeterminate progress feedback (`Uploading...` -> `Extracting...` -> `Indexing...` -> `Ready`).
3. **Connect Dead Settings Controls**:
   * Wire `#tuneSettingsBtn` to a clean Settings drawer supporting Theme, Sound, Auto-scroll, and Source Scope.
4. **Fix Vault Synchronization Endpoint**:
   * Create dedicated endpoint `POST /api/vault/sync` that processes existing files in `Download/` without requiring file uploads.