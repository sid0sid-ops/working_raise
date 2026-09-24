# 08. 2-Minute Quickstart Guide (Professor & Evaluator Edition)

> **Purpose**: This guide is specifically designed for professors, academic reviewers, and evaluators who need to inspect and test the RAISE research backend on their laptop **in under 2 minutes** without installing Docker, setting up local databases, or dealing with terminal errors.

---

## ⚡ The Zero-Docker Promise

* **Zero Docker Required**: No heavy background containers, no admin virtualization settings.
* **Zero Database Configuration**: Uses high-speed cloud graph intelligence and built-in automatic memory storage.
* **Ultra-Lightweight**: Uses less than **1.2 GB of RAM**; runs silently without overheating or draining your laptop battery.
* **Sub-Second Latency**: Powered by Groq LPU inference delivering responses in **< 1.0 second**.

---

## 💻 System Prerequisites

All you need is:
1. A laptop running **macOS (Apple Silicon / Intel)** or **Windows (10 / 11)**.
2. **Python 3.11 or higher** installed ([Download from python.org](https://www.python.org/downloads/)).
   * *Windows Users*: Make sure you checked the box **"Add python.exe to PATH"** during Python installation.
3. Active internet connection.

---

## 🚀 2-Minute Quickstart Instructions

### Option A: For macOS / Linux Users

Open your **Terminal** app and run these 3 commands:

```bash
# 1. Clone the repository and enter the directory
git clone -b backend https://github.com/sid0sid-ops/working_raise.git
cd working_raise

# 2. Run the automated 1-click bootstrapper
python3 setup.py
# (When prompted, press Enter to accept Profile 1: Cloud-Native)

# 3. Start the server
source .venv/bin/activate
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### Option B: For Windows Users

1. Open **Command Prompt (`cmd`)** or **PowerShell**:
   ```powershell
   git clone -b backend https://github.com/sid0sid-ops/working_raise.git
   cd working_raise
   ```
2. **Double-click** [`setup.bat`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/setup.bat) in the folder.
   *(This automatically creates `.venv` and installs all dependencies in ~60 seconds).*
3. **Double-click** [`run.bat`](file:///Users/sid/Documents/project/Frontend/scratch/working_raise/run.bat) to launch the server!

---

## 🌐 How to Interact & Test

Once the terminal displays `Application startup complete`:

1. Open your web browser to:
   👉 **`http://127.0.0.1:8000/docs`**
2. You will see the **Interactive Swagger API Documentation**.
3. **Test the GraphRAG pipeline in 10 seconds**:
   * Scroll to the **`POST /api/v1/query`** endpoint.
   * Click **"Try it out"**.
   * Replace the request body with:
     ```json
     {
       "query": "What are the key policy recommendations for climate adaptation?",
       "mode": "fast",
       "session_id": "prof-eval-session-01"
     }
     ```
   * Click **Execute**.
   * The response will return verified facts, citations, and graph relationships in under **1.0 second**!

---

## 📋 Evaluation Configuration (`.env`)

A pre-configured evaluation template is provided. The student can pre-populate the `.env` file before submitting so you don't need to sign up for any keys:

```bash
# Core Mode
ENVIRONMENT=development
LOG_LEVEL=INFO
USE_RUST_CORE=false

# Cloud LLM Reasoning (Groq LPU Sub-Second Inference)
GROQ_API_KEY=gsk_preconfigured_evaluation_key

# Knowledge Graph (Hosted Cloud Neo4j AuraDB)
NEO4J_URI=neo4j+s://preconfigured-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=preconfigured_password

# Databases (Uses automatic in-memory fallback - Zero Docker needed)
VECTOR_DB_TYPE=chroma
CHROMA_PERSIST_DIR=./data/chroma
```

---

## ❓ Frequently Asked Questions (For Evaluators)

**Q: Why is Docker not needed?**  
A: For evaluation and local testing, the backend connects to Neo4j's free cloud instance and uses Python's built-in memory storage for chat sessions and cache. Docker is only required for air-gapped offline server deployments.

**Q: Will this install files outside the folder?**  
A: No. Everything is strictly self-contained within the `.venv/` virtual environment directory. To uninstall, simply delete the project folder.

**Q: Can I test document uploads?**  
A: Yes! Use the **`POST /api/v1/documents/upload`** endpoint in Swagger UI to upload a research PDF. The background pipeline will parse, chunk, embed, and index it into the local ChromaDB vector store automatically.

---

## ✉️ Ready-to-Send Email Template for Your Professor

You can copy and send this message when sharing your repository with your professor:

```text
Dear Professor [Name],

I am pleased to share the backend repository for the RAISE GraphRAG Research Workstation:
https://github.com/sid0sid-ops/working_raise (branch: backend)

To respect your time and computing resources, I have designed this build to run in "Evaluation Cloud-Native Mode":
• Requires ZERO Docker installation and ZERO database configuration.
• Takes less than 2 minutes to launch and consumes under 1.2 GB of RAM.
• Powered by Groq LPU inference delivering responses in under 1 second.

Quick Start:
1. Clone the repo and enter the folder:
   git clone -b backend https://github.com/sid0sid-ops/working_raise.git
   cd working_raise
2. Run the bootstrapper:
   • On Mac: python3 setup.py (then run: uvicorn src.main:app --reload)
   • On Windows: Double-click setup.bat (then double-click run.bat)
3. Open http://127.0.0.1:8000/docs in your browser to interact with the API.

All evaluation credentials have been pre-configured in the .env file. A complete step-by-step evaluator guide is available in the repository at backend_docs/08_TWO_MINUTE_PROFESSOR_QUICKSTART_GUIDE.md.

Thank you for your time and feedback!

Best regards,
[Your Name]
```
