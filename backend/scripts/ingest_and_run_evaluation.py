"""
End-to-End RAISE Pipeline Benchmark Runner
1. Ingests all 4 institutional annual reports using AcademicPipelineIngestor
   (SmartDocumentParser + AdaptiveChunkingPipeline -> LocalVectorEngine + Neo4jDatabase).
2. Verifies substrate counts in ChromaDB and Neo4j.
3. Evaluates all 16 benchmark questions via StandaloneRAGPipeline.
4. Generates eval_results.json and eval_report.md containing genuine raise_answers.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.features.ingestion.pipeline import AcademicPipelineIngestor
from src.infrastructure.vector.chroma import LocalVectorEngine
from src.infrastructure.graph.neo4j import Neo4jDatabase
from evaluation.eval_runner import run_evaluation


DOCUMENTS = [
    "AR_2024-25_Combined_English_Mail.pdf",
    "Annual Report 2024-25 final upload.pdf",
    "IITMRP Annual Report.pdf",
    "ARE-2016-17.pdf",
]


def ingest_documents():
    docs_dir = BASE_DIR / "data" / "documents"
    print("=" * 72)
    print(" [1/3] INGESTING BENCHMARK INSTITUTIONAL REPORTS INTO CHROMADB & NEO4J")
    print("=" * 72)

    with AcademicPipelineIngestor() as ingestor:
        for doc_name in DOCUMENTS:
            pdf_path = docs_dir / doc_name
            if not pdf_path.exists():
                print(f"Warning: {doc_name} not found at {pdf_path}")
                continue

            print(f"\n>>> Ingesting: {doc_name} ({round(pdf_path.stat().st_size / (1024*1024), 2)} MB)")
            t0 = time.time()
            res = ingestor.process_pdf(pdf_path, engine="fast", extract_tables=True)
            elapsed = round(time.time() - t0, 2)
            print(f"    Done in {elapsed}s: {res.get('chunks_count', 0)} chunks, {res.get('entities_count', 0)} entities, Neo4j synced={res.get('neo4j_synced')}")


def verify_substrates():
    print("\n" + "=" * 72)
    print(" [2/3] VERIFYING PRODUCTION SUBSTRATES")
    print("=" * 72)

    vector_engine = LocalVectorEngine()
    total_vectors = vector_engine.collection.count()
    print(f" ChromaDB Vector Store: {total_vectors} chunks indexed")

    neo4j = Neo4jDatabase()
    with neo4j.driver.session() as session:
        n_count = session.run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
        r_count = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
        labels_result = session.run(
            "MATCH (n) UNWIND labels(n) AS l RETURN l AS label, count(*) AS count ORDER BY count DESC LIMIT 10"
        )
        labels = {rec["label"]: rec["count"] for rec in labels_result}

    print(f" Neo4j Graph Store: {n_count} nodes, {r_count} relationships")
    print(f" Neo4j Labels Breakdown: {labels}")
    neo4j.close()

    assert total_vectors > 0, "ChromaDB vector store is empty!"
    assert n_count > 0, "Neo4j graph store is empty!"
    print(" Substrate verification passed!")


def run_benchmarks():
    print("\n" + "=" * 72)
    print(" [3/3] EXECUTING RAISE-BENCH-V1 EVALUATION")
    print("=" * 72)

    bench_path = BASE_DIR / "evaluation" / "benchmark_qa.json"
    out_path = BASE_DIR / "evaluation" / "eval_results.json"
    summary = run_evaluation(benchmark_path=bench_path, output_path=out_path)
    return summary


def main():
    start_time = time.time()
    ingest_documents()
    verify_substrates()
    summary = run_benchmarks()

    total_time = round(time.time() - start_time, 2)
    print("\n" + "=" * 72)
    print(f" FULL PIPELINE RUN COMPLETE in {total_time}s")
    print(f" Questions: {summary.get('total_questions')} | Passed: {summary.get('questions_passed')} ({summary.get('pass_rate_percent')}%)")
    print(f" Average Keyword Accuracy: {summary.get('average_keyword_score')*100:.1f}%")
    print(f" Average Latency: {summary.get('average_latency_seconds')}s")
    print("=" * 72)


if __name__ == "__main__":
    main()
