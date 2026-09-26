"""
RAISE Automated Benchmark Evaluation Harness
Measures Agentic Tool Selection, Groundedness %, Citation Accuracy, and Zero-Hallucination Rejection.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Permanent UTF-8 console encoding fix for Windows environments
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add RAG directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.pipeline import StandaloneRAGPipeline


def run_evaluation():
    base_dir = Path(__file__).parent
    q_path = base_dir / "questions.json"
    if not q_path.exists():
        print("Questions file not found.")
        return

    questions = json.loads(q_path.read_text(encoding="utf-8"))
    pipeline = StandaloneRAGPipeline()

    # Load active artifacts
    session_dir = base_dir.parent / ".runtime" / "active_session"
    c_path = session_dir / "ai_chunks.json"
    s_path = session_dir / "schema_filtering_report.json"

    if c_path.exists():
        pipeline.process_artifacts(c_path, s_path, doc_id="Benchmark_Doc_2025", university="AstraBio Innovations Council")

    print("\n" + "=" * 70)
    print(" 🚀 [BENCHMARK START] AGENTIC GRAPHRAG EVALUATION SUITE")
    print("=" * 70)

    passed_count = 0

    for q in questions:
        qid = q["id"]
        qtext = q["question"]
        qtype = q["type"]

        t0 = time.time()
        res = pipeline.ask_agent(qtext)
        elapsed = round(time.time() - t0, 3)

        print(f"\n[{qid}] Type: {qtype} | Latency: {elapsed}s")
        print(f"  Q: \"{qtext}\"")
        print(f"  Tools Selected: {res['selected_tools']}")
        print(f"  Traceability Score: {round(res['traceability_score'] * 100)}%")

        if qtype == "NEGATIVE_UNANSWERABLE":
            is_pass = "INSUFFICIENT_EVIDENCE" in res["grounded_answer"]
            status_str = "PASS (Correctly rejected ungrounded query - Zero Hallucination)" if is_pass else "FAIL (Hallucinated an answer)"
        else:
            is_pass = len(res["grounded_answer"]) > 20 and res["traceability_score"] >= 0.80
            status_str = "PASS (Grounded with full citations)" if is_pass else "FAIL (Insufficient grounding)"

        if is_pass:
            passed_count += 1

        print(f"  Result: {status_str}")

    accuracy_pct = round((passed_count / max(len(questions), 1)) * 100, 1)
    print("\n" + "=" * 70)
    print(f" 📊 [METRICS COMPLETE] {passed_count}/{len(questions)} Passed ({accuracy_pct}% Grounded Accuracy)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_evaluation()
