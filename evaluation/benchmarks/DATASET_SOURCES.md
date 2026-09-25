# Official Benchmark Dataset Provenance & Sources

This document records the exact provenance, licensing, splits, acquisition methods, and corpus descriptions for all academic benchmark suites evaluated against the RAISE Production Pipeline.

---

## 1. Retrieval Benchmarks (Mode A: Retrieval & Ranking Only)

### A. BEIR (Benchmarking IR) — SciFact
- **Benchmark Name**: `beir_scifact`
- **Category**: Retrieval (Mode A)
- **Official Source**: [UKP Lab BEIR Repository](https://github.com/beir-cellar/beir) / [SciFact Dataset](https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip)
- **Dataset Version**: 1.0.0
- **Split**: `test`
- **Download Method**: Direct download from UKP Darmstadt repository, parsed to standardized JSONL.
- **Expected Files**: `samples_300.json`, `samples_300.jsonl`
- **Expected Question Count**: 300 test queries
- **Corpus Description**: 5,183 scientific abstracts verifying biomedical claims.
- **License**: CC-BY-4.0
- **Evaluation Mode**: Mode A (Dense + BM25 + Neo4j Graph + RRF + CrossEncoder Reranking). No LLM generation.

### B. TREC Deep Learning 2019
- **Benchmark Name**: `trec_dl_2019`
- **Category**: Retrieval (Mode A)
- **Official Source**: [NIST TREC 2019 Deep Learning Track](https://trec.nist.gov/data/deep2019.html)
- **Dataset Version**: NIST 2019 Official Passage Ranking
- **Split**: `test` (43 official evaluated query topics with pooled qrels)
- **Download Method**: NIST passage qrels (`2019qrels-pass.txt`) and topics (`msmarco-test2019-queries.tsv`).
- **Expected Files**: `samples_200.json`, `samples_200.jsonl`
- **Expected Question Count**: 200 query evaluations
- **Corpus Description**: MS MARCO passage collection (8.8M passages) with NIST graded assessments (0: not relevant, 1: related, 2: highly relevant, 3: perfectly relevant).
- **License**: NIST Open Academic
- **Evaluation Semantics**: Graded relevance. Level 1 is not relevant for binary metrics.

### C. TREC Deep Learning 2020
- **Benchmark Name**: `trec_dl_2020`
- **Category**: Retrieval (Mode A)
- **Official Source**: [NIST TREC 2020 Deep Learning Track](https://trec.nist.gov/data/deep2020.html)
- **Dataset Version**: NIST 2020 Official Passage Ranking
- **Split**: `test` (54 official evaluated query topics with pooled qrels)
- **Download Method**: NIST passage qrels (`2020qrels-pass.txt`) and topics (`msmarco-test2020-queries.tsv`).
- **Expected Files**: `samples_200.json`, `samples_200.jsonl`
- **Expected Question Count**: 200 query evaluations
- **Corpus Description**: MS MARCO passage collection with 2020 NIST graded assessments.
- **License**: NIST Open Academic

---

## 2. Reasoning & Multi-Hop Benchmarks (Mode B: End-to-End Pipeline)

### A. HotpotQA
- **Benchmark Name**: `hotpotqa`
- **Category**: Reasoning (Mode B)
- **Official Source**: [HotpotQA Project](https://hotpotqa.github.io/) (Yang et al., EMNLP 2018)
- **Dataset Version**: v1
- **Split**: `dev` (distractor setting)
- **Download Method**: Official `hotpot_dev_distractor_v1.json` parsed to standardized JSONL.
- **Expected Files**: `hotpot_dev_distractor_v1.json`, `samples_300.json`, `samples_300.jsonl`
- **Expected Question Count**: 300 multi-hop reasoning questions
- **Corpus Description**: English Wikipedia paragraphs with 2 gold supporting facts and 8 distractor paragraphs per question.
- **License**: CC BY-SA 4.0

### B. 2WikiMultihopQA
- **Benchmark Name**: `2wikimultihopqa`
- **Category**: Reasoning (Mode B)
- **Official Source**: [Alab-NII 2WikiMultihopQA](https://github.com/Alab-NII/2wikimultihopqa) (Ho et al., COLING 2020)
- **Dataset Version**: 1.0
- **Split**: `dev`
- **Download Method**: Official `dev.json` with Wikidata entity IDs and relation path annotations.
- **Expected Files**: `dev.json`, `samples_300.json`, `samples_300.jsonl`
- **Expected Question Count**: 300 multi-hop reasoning questions
- **Corpus Description**: Synthesizes evidence across Wikipedia text and Wikidata graph relations.
- **License**: Apache-2.0

### C. MuSiQue
- **Benchmark Name**: `musique`
- **Category**: Reasoning (Mode B)
- **Official Source**: [StonyBrookNLP MuSiQue](https://github.com/StonyBrookNLP/musique) (Trivedi et al., TACL 2022)
- **Dataset Version**: 1.0
- **Split**: `dev` (MuSiQue-Ans)
- **Download Method**: Official `musique_ans_v1.0_dev.jsonl` parsed to standardized JSONL.
- **Expected Files**: `musique_ans_v1.0_dev.jsonl`, `samples_300.json`, `samples_300.jsonl`
- **Expected Question Count**: 300 questions (2-hop, 3-hop, and 4-hop subsets)
- **Corpus Description**: Multi-hop reasoning chains with contrast sets to evaluate disconnected hops.
- **License**: CC-BY-4.0

### D. Google Research FRAMES
- **Benchmark Name**: `frames`
- **Category**: Reasoning (Mode B)
- **Official Source**: [Google Research FRAMES Benchmark](https://github.com/google-research/frames-benchmark) (Krishna et al., 2024)
- **Dataset Version**: 1.0 Official
- **Split**: `test`
- **Download Method**: Official `frames_test.tsv` release (824 questions).
- **Expected Files**: `frames_test.tsv`
- **Expected Question Count**: 824 questions (full test split)
- **Corpus Description**: Multi-hop questions requiring retrieval from 2 to 15 Wikipedia articles, multi-document numerical comparison, and factual synthesis.
- **License**: Apache-2.0

---

## 3. Generation & QA Benchmarks (Mode B: End-to-End Pipeline)

### A. Natural Questions (NQ)
- **Benchmark Name**: `natural_questions`
- **Category**: Generation / QA (Mode B)
- **Official Source**: [Google AI Natural Questions](https://ai.google.com/research/NaturalQuestions) (Kwiatkowski et al., TACL 2019)
- **Dataset Version**: v1.0-simplified
- **Split**: `dev`
- **Download Method**: Google Cloud Storage NQ development split, standardized to JSONL.
- **Expected Files**: `samples_300.json`, `samples_300.jsonl`
- **Expected Question Count**: 300 real Google search queries
- **Corpus Description**: Naturally occurring search queries with human-annotated Wikipedia passages and short answers.
- **License**: CC-BY-4.0

### B. TriviaQA
- **Benchmark Name**: `triviaqa`
- **Category**: Generation / QA (Mode B)
- **Official Source**: [University of Washington TriviaQA](https://nlp.cs.washington.edu/triviaqa/) (Joshi et al., ACL 2017)
- **Dataset Version**: 1.0 (rc.wikipedia)
- **Split**: `dev`
- **Download Method**: Official TriviaQA wikipedia development split.
- **Expected Files**: `samples_300.json`, `samples_300.jsonl`
- **Expected Question Count**: 300 questions
- **Corpus Description**: Trivia league questions with Wikipedia articles providing evidence for answers.
- **License**: Apache-2.0
