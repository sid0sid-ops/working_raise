# RAISE Evaluation Framework — Official Dataset Manifest

**Document Version**: 1.0.0  
**Date Verified**: 2026-09-26  
**Status**: ACTIVE & IMMUTABLY AUDITED  

---

## 1. Summary of Benchmark Datasets

| Benchmark | Family / Category | Official Source | Split | Question Count | License |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **RAISE Domain** | In-Domain Academic GraphRAG | RAISE Production Repository (`backend/evaluation/benchmark_qa.json`) | Dev/Locked | 16 | Internal / CC-BY-NC |
| **BEIR (SciFact)** | Scientific IR (Mode A) | UKP Lab Darmstadt (`https://github.com/beir-cellar/beir`) | Test | 300 | CC-BY-4.0 |
| **TREC Deep Learning 2019**| Passage Retrieval (Mode A) | NIST TREC (`https://trec.nist.gov/data/deep2019.html`) | Test (43 topics) | 200 | NIST Open Academic |
| **TREC Deep Learning 2020**| Passage Retrieval (Mode A) | NIST TREC (`https://trec.nist.gov/data/deep2020.html`) | Test (54 topics) | 200 | NIST Open Academic |
| **HotpotQA** | Multi-Hop Reasoning (Mode B)| Yang et al., EMNLP 2018 (`https://hotpotqa.github.io/`) | Dev (Distractor) | 300 | CC BY-SA 4.0 |
| **2WikiMultihopQA** | Graph Reasoning (Mode B) | Ho et al., COLING 2020 (`https://github.com/Alab-NII/2wikimultihopqa`)| Dev | 300 | Apache-2.0 |
| **MuSiQue** | Multi-Hop Reasoning (Mode B)| Trivedi et al., TACL 2022 (`https://github.com/StonyBrookNLP/musique`) | Dev (Ans) | 300 | CC-BY-4.0 |
| **Google FRAMES** | Complex Multi-Hop (Mode B) | Krishna et al., 2024 (`https://github.com/google-research/frames-benchmark`)| Test | 824 | Apache-2.0 |
| **Natural Questions (NQ)** | Open-Domain QA (Mode B) | Google AI (`https://ai.google.com/research/NaturalQuestions`) | Dev | 300 | CC-BY-4.0 |
| **TriviaQA** | Factoid QA (Mode B) | Joshi et al., ACL 2017 (`https://nlp.cs.washington.edu/triviaqa/`) | Dev (Wiki) | 300 | Apache-2.0 |

---

## 2. Granular Benchmark Profiles

### A. In-Domain Benchmark: RAISE Domain
- **Category**: Academic Institutional GraphRAG (Mode B End-to-End)
- **Official Source**: `backend/evaluation/benchmark_qa.json`
- **Corpus**: 9,776 chunks from IITMRP and NIPGR annual reports, 2,580 Neo4j graph nodes.
- **Evaluation Tiers**:
  - Tier 1: Exact Line-Item Financial Extraction
  - Tier 2: Governance & Administrative Cross-Referencing
  - Tier 3: Multi-Year Financial & Expenditure Analysis
  - Tier 4: Out-of-Scope Institutional Traps (Refusal & Abstention)

### B. BEIR — SciFact
- **Category**: Retrieval Evaluation (Mode A)
- **Official Source**: `https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip`
- **Corpus**: 5,183 scientific abstracts verifying biomedical assertions.
- **Metrics**: Recall@1, Recall@5, Recall@10, Recall@20, MRR@10, nDCG@10.
- **Evaluation Semantics**: Binary relevance against SciFact evidence documents.

### C. TREC Deep Learning 2019 & 2020
- **Category**: Graded Passage Ranking (Mode A)
- **Official Source**: NIST TREC Deep Learning Tracks 2019 & 2020
- **Corpus**: MS MARCO passage ranking corpus (8.8M passages).
- **Metrics**: Recall@K, MRR@10, nDCG@10, MAP@100.
- **Graded Relevance Interpretation**:
  - Level 0: Not relevant
  - Level 1: Contextually related (not relevant for binary calculation)
  - Level 2: Highly relevant
  - Level 3: Perfectly relevant

### D. HotpotQA
- **Category**: Multi-Hop Factual Reasoning (Mode B)
- **Official Source**: `https://hotpotqa.github.io/`
- **Corpus**: Full Wikipedia articles; 2 gold supporting facts + 8 distractor paragraphs per question.
- **Metrics**: Answer EM, Token F1, Supporting Fact Precision/Recall/F1, Faithfulness.

### E. 2WikiMultihopQA
- **Category**: Graph-Assisted Multi-Hop Reasoning (Mode B)
- **Official Source**: `https://github.com/Alab-NII/2wikimultihopqa`
- **Corpus**: Wikipedia paired with Wikidata relational triples and entity identifiers.
- **Metrics**: Entity resolution, Cypher execution validity, Path completion, Answer F1.

### F. MuSiQue
- **Category**: Multi-Hop Connected Chains (Mode B)
- **Official Source**: `https://github.com/StonyBrookNLP/musique`
- **Corpus**: 2-hop, 3-hop, and 4-hop multi-hop reasoning chains with contrast unanswerable sets.
- **Metrics**: Hop-level evidence recall, contrast set abstention rate.

### G. Google Research FRAMES
- **Category**: Numerical, Tabular, and Multi-Document Reasoning (Mode B)
- **Official Source**: `https://github.com/google-research/frames-benchmark`
- **Corpus**: Multi-source factual Wikipedia articles requiring comparison across 2–15 sources.
- **Metrics**: Multi-hop answer accuracy, numeric verification, calculation fidelity.

### H. Natural Questions (NQ)
- **Category**: Natural Search Query QA (Mode B)
- **Official Source**: `https://ai.google.com/research/NaturalQuestions`
- **Corpus**: English Wikipedia.
- **Metrics**: Short answer exact match, evidence recall, answer extraction.

### I. TriviaQA
- **Category**: Factoid & Trivia Question Answering (Mode B)
- **Official Source**: `https://nlp.cs.washington.edu/triviaqa/`
- **Corpus**: Trivia league questions with Wikipedia reference texts.
- **Metrics**: Answer string containment, Token F1, hallucination rate.
