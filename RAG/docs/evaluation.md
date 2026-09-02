# RAISE Evaluation & Benchmarking Methodology

## 1. Benchmarking Objectives
Measure Grounded Accuracy, Citation Precision, Retrieval Recall, and Zero-Hallucination Rejection across multi-university annual reports.

---

## 2. Benchmark Query Taxonomy (`RAG/evaluation/questions.json`)

1. **Exact Numeric Facts (`SIMPLE_FACT`)**: E.g., *"What was the total research expenditure reported by AstraBio Innovations Council in 2025?"*
2. **Cross-Institutional Comparisons (`COMPARATIVE_ANALYSIS`)**: E.g., *"Compare Panjab University and Delhi University in research funding and patent filings during 2024."*
3. **Multi-Hop Graph Relationships (`RELATIONSHIP_QUERY`)**: E.g., *"Which national strategic initiatives and programs did the institute participate in during 2025?"*
4. **Out-of-Domain / Negative Queries (`NEGATIVE_UNANSWERABLE`)**: E.g., *"What was the total expenditure on underwater nuclear submarine research in 2024?"* $\to$ Enforces strict `INSUFFICIENT_EVIDENCE` zero-hallucination rejection.

---

## 3. Evaluation Harness (`RAG/evaluation/evaluate.py`)
* Automatically runs all test queries.
* Assesses latency, tools invoked, grounded claims count, and citation integrity.
* Current baseline score: **4/4 Scenarios Passed (100.0% Grounded Accuracy, Avg Latency < 0.04s)**.
