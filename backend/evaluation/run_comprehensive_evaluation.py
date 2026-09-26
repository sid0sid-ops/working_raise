"""
RAISE NIAH Comprehensive Evaluation Script
Executes multi-dimensional benchmark matrices across depths, context sizes, chunk sizes, and needles.
Saves comprehensive telemetry to evaluation/reports/niah/.
"""

import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from evaluation.benchmarks.niah.niah_runner import NIAHBenchmarkRunner
from evaluation.benchmarks.niah.visualizer import NIAHVisualizer
from evaluation.benchmarks.niah.needle_catalog import list_available_needles


def run_full_pipeline_evaluation():
    print("=" * 78)
    print(" 🌟 RAISE GRAPHRAG: COMPREHENSIVE NIAH RETRIEVAL EVALUATION")
    print("=" * 78)

    runner = NIAHBenchmarkRunner()
    all_results = []

    # Matrix 1: Standard Factual Needle across 5 Depths x 4 Context Sizes
    print("\n--- [MATRIX 1] Needle: 'fact_quantum_crypt' (Depth vs Context Size Sweep) ---")
    depths = [0.0, 0.25, 0.50, 0.75, 1.00]
    sizes = [1000, 3000, 6000, 10000]
    matrix_1_res = runner.run_sweep(
        needle_id="fact_quantum_crypt",
        depths=depths,
        context_sizes=sizes,
        chunk_size=450,
        chunk_overlap=0.0,
        test_llm=True,
    )
    all_results.extend(matrix_1_res)

    print("\n" + "=" * 78)
    print(" 📊 MATRIX 1 HEATMAP: FACTUAL NEEDLE (Depth vs Context Length)")
    print("=" * 78)
    print(NIAHVisualizer.render_ascii_matrix(matrix_1_res, depths, sizes))

    # Matrix 2: Quantitative Grant Metric Needle
    print("\n--- [MATRIX 2] Needle: 'quant_photonic_grant' (Quantitative Metric Sweep) ---")
    matrix_2_res = runner.run_sweep(
        needle_id="quant_photonic_grant",
        depths=[0.0, 0.50, 1.00],
        context_sizes=[1000, 5000],
        chunk_size=450,
        chunk_overlap=0.0,
        test_llm=True,
    )
    all_results.extend(matrix_2_res)

    # Matrix 3: Multi-Hop Knowledge Graph Traversal Needle
    print("\n--- [MATRIX 3] Needle: 'graph_multihop_carbon' (Multi-Hop Relational Sweep) ---")
    matrix_3_res = runner.run_sweep(
        needle_id="graph_multihop_carbon",
        depths=[0.0, 0.50, 1.00],
        context_sizes=[1000, 5000],
        chunk_size=450,
        chunk_overlap=0.0,
        test_llm=True,
    )
    all_results.extend(matrix_3_res)

    # Matrix 4: Chunk Size Sensitivity Sweep (128 vs 256 vs 450 vs 1024 words)
    print("\n--- [MATRIX 4] Chunk Size Sensitivity Sweep (128w, 256w, 450w, 1024w) ---")
    chunk_sizes = [128, 256, 450, 1024]
    matrix_4_res = []
    for c_size in chunk_sizes:
        res = runner.run_single_experiment(
            needle="fact_quantum_crypt",
            target_words=4000,
            depth=0.50,
            chunk_size=c_size,
            chunk_overlap=0.0,
            test_llm=True,
        )
        matrix_4_res.append(res)
        all_results.append(res)
        print(f"  • Chunk Size: {c_size:>4}w | Chunks: {res['total_chunks']:>2} | Status: {res['failure_stage']:<15} (rank={res['gold_rank']})")

    # Matrix 5: Chunk Overlap Sensitivity Sweep (0%, 10%, 20%, 30%)
    print("\n--- [MATRIX 5] Chunk Overlap Sensitivity Sweep (0%, 10%, 20%, 30%) ---")
    overlaps = [0.0, 0.10, 0.20, 0.30]
    matrix_5_res = []
    for ov in overlaps:
        res = runner.run_single_experiment(
            needle="fact_quantum_crypt",
            target_words=4000,
            depth=0.50,
            chunk_size=300,
            chunk_overlap=ov,
            test_llm=True,
        )
        matrix_5_res.append(res)
        all_results.append(res)
        print(f"  • Overlap: {int(ov*100):>2}% | Chunks: {res['total_chunks']:>2} | Status: {res['failure_stage']:<15} (rank={res['gold_rank']})")

    # Export Unified Master Benchmark Report
    paths = NIAHVisualizer.export_report(
        results=all_results,
        experiment_name="comprehensive_pipeline_evaluation",
    )
    print("\n" + "=" * 78)
    print(" 🏁 COMPREHENSIVE PIPELINE EVALUATION FINISHED")
    print(f" 📄 Full Markdown Report: {paths['markdown']}")
    print(f" 📊 Full JSON Telemetry: {paths['json']}")
    print("=" * 78)


if __name__ == "__main__":
    run_full_pipeline_evaluation()
