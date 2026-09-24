"""
Command-Line Interface for RAISE Scientific Evaluation Framework
Usage:
    python RAG/evaluation/run_eval.py --benchmark raise-domain --mode MODE_B_END_TO_END
    python RAG/evaluation/run_eval.py --all-baseline
"""

from __future__ import annotations

import argparse
import sys
import json
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_ROOT.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"

for p in [str(PROJECT_ROOT), str(BACKEND_ROOT), str(EVAL_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from evaluation.runners.baseline_runner import BaselineEvaluationRunner


def main():
    parser = argparse.ArgumentParser(description="RAISE Scientific Evaluation Framework")
    parser.add_argument("--benchmark", type=str, default="raise-domain",
                        choices=["raise-domain", "frames", "nq", "hotpotqa", "2wiki", "musique"],
                        help="Benchmark suite to evaluate")
    parser.add_argument("--mode", type=str, default="MODE_B_END_TO_END",
                        choices=["MODE_A_RETRIEVAL", "MODE_B_END_TO_END"],
                        help="Evaluation mode: Mode A (Retrieval only) or Mode B (End-to-End RAG)")
    parser.add_argument("--ablation", type=str, default="ABL-G",
                        help="Ablation configuration ID (ABL-A through ABL-H)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of evaluation questions")
    parser.add_argument("--experiment-id", type=str, default="EXP-BASELINE",
                        help="Experiment tracking identifier")
    parser.add_argument("--run-tag", type=str, default=None,
                        help="Custom tag for run ID, e.g. improved")
    parser.add_argument("--all-baseline", action="store_true",
                        help="Executes complete baseline battery across all tiers and ablations")
    args = parser.parse_args()

    runner = BaselineEvaluationRunner(
        ablation_id=args.ablation,
        experiment_id=args.experiment_id,
    )

    if args.all_baseline:
        print("=== EXECUTING COMPLETE BASELINE BATTERY ACROSS ALL TIERS ===")
        suites = ["raise-domain", "nq", "hotpotqa", "2wiki", "musique"]
        master_results = {}
        for s in suites:
            print(f"\n>>> Running Benchmark: {s} <<<")
            res = runner.run_benchmark(s, mode=args.mode, limit=10 if s != "raise-domain" else None, run_tag=args.run_tag)
            master_results[s] = res

        print("\n=== MASTER BASELINE BATTERY COMPLETE ===")
        print(json.dumps(master_results, indent=2))
    else:
        print(f"=== EXECUTING EVALUATION: {args.benchmark} ({args.mode}) ===")
        res = runner.run_benchmark(args.benchmark, mode=args.mode, limit=args.limit, run_tag=args.run_tag)
        print("\n=== EVALUATION RUN RESULT SCORECARD ===")
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
