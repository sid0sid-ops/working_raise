# 🚀 RAISE: Research Assessment Intelligence & Semantic Extraction

Welcome to the **RAISE** repository (`semanticClimate/RAISE`).

RAISE is an automated pipeline that parses unstructured PDF annual research reports into **traceable, semantified HTML5 documents** (`report.html`) and **structured knowledge chunks** (`ai_chunks.json`) for **Agentic AI** and LLM Retrieval-Augmented Generation (RAG) models.

---

## 📌 Architecture & Pipeline Stages

The end-to-end semantification process operates across **3 core stages**:

```text
📄 Annual Report PDF
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: PDF Layout Parsing (raise_pdf_parsing)             │
│ • Extracts text blocks, font sizes, tables & bounding boxes │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: Noise Filtering & Target Block Extraction          │
│ • Filters out financial audit pages, balance sheets,        │
│   photo galleries, staff rosters & running headers/footers  │
│ • Generates high-density target_blocks.json                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 3: HTML5 Semantification & Agentic AI Chunking        │
│ (raise_html5_semantification)                               │
│ • Validates JSON schema input quality                       │
│ • Learns document typography profile (semantic_profile.json)│
│ • Constructs hierarchical section trees                     │
│ • Generates traceable HTML5 report (report.html)            │
│ • Extracts structured RAG chunks (ai_chunks.json)           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
📦 Deliverables: report.html, ai_chunks.json, source_map.json
```

---

## ⚡ Google Colab End-to-End Notebook

You can run the entire pipeline interactively in **Google Colab** using the unified notebook:

- **Notebook Path**: [`RAISE_PDF_Parsing_and_Semantification_Colab.ipynb`](RAISE_PDF_Parsing_and_Semantification_Colab.ipynb)
- **Branch**: `siddharth-semantification`
- **One-Click Colab Launch**:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/semanticClimate/RAISE/blob/siddharth-semantification/RAISE_PDF_Parsing_and_Semantification_Colab.ipynb)

---

## 🛠️ Repository & Branch Structure

- **`siddharth-semantification`**: Contains the HTML5 Semantification engine (`RAISE_HTML5_Semantification/`) and the unified Google Colab notebook (`RAISE_PDF_Parsing_and_Semantification_Colab.ipynb`).
- **`Harsh-semantification`**: Contains the PDF Layout Parsing engine (`RAISE_PDF_Parsing/`).

---

## 💻 Local Installation & Usage

### 1. Install `raise_html5_semantification` locally
```bash
git clone https://github.com/semanticClimate/RAISE.git
cd RAISE/RAISE_HTML5_Semantification
pip install -e .
```

### 2. Run the HTML5 Semantification CLI
```bash
raise-html5-semantify --input target_blocks.json --output report.html --ai-chunks ai_chunks.json
```

### 3. Run Quality & Development Tests
```bash
# Run pytest unit tests
uv run pytest

# Code linting
uv run ruff check .

# Code formatting
uv run black --check .
```
