"""
Targeted Verification Script:
Executes previously failed FRAMES questions on the newly updated production pipeline.
Compares previous failure answers against new answers and prints a side-by-side audit.
"""

import os
import sys
import json
import time
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.benchmarks.frames.data.loader import FramesDatasetLoader
from evaluation.benchmarks.frames.isolation.harness import IsolatedFramesHarness
from evaluation.benchmarks.frames.evaluators.factuality import FactualityEvaluator
from evaluation.benchmarks.frames.evaluators.reasoning import ReasoningEvaluator
from evaluation.benchmarks.frames.evaluators.retrieval import RetrievalEvaluator
from evaluation.benchmarks.frames.evaluators.diagnostician import FailureDiagnostician
from evaluation.benchmarks.frames.runners.runner import FramesBenchmarkRunner

TARGET_QIDS = ["29", "724", "10", "24", "14", "6"]

def main():
    print("==================================================================", flush=True)
    print("🚀 RUNNING PREVIOUSLY FAILED FRAMES QUESTIONS ON UPDATED PIPELINE", flush=True)
    print("==================================================================", flush=True)

    # 1. Load baseline / consolidated checkpoint to extract old answers
    ckpt_path = PROJECT_ROOT.parent / "Artifacts" / "benchmarks" / "frames" / "checkpoints" / "frames_hybrid_consolidated_824_checkpoint.jsonl"
    prev_results = {}
    if ckpt_path.exists():
        with open(ckpt_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    prev_results[str(rec.get("question_id"))] = rec
                except Exception:
                    continue
    print(f"Loaded {len(prev_results)} previous records for comparison.", flush=True)

    # 2. Load dataset questions
    loader = FramesDatasetLoader()
    all_questions = loader.get_questions()
    target_questions = [q for q in all_questions if str(q.question_id) in TARGET_QIDS]
    # Sort in order of TARGET_QIDS
    target_questions.sort(key=lambda q: TARGET_QIDS.index(str(q.question_id)))
    print(f"Selected {len(target_questions)} target questions for execution.\n", flush=True)

    # 3. Instantiate Runner and Sandbox Harness
    runner = FramesBenchmarkRunner(mode="hybrid", experiment_name="sample_failed_verification")
    harness = IsolatedFramesHarness(
        session_id="sample_failed_verification",
        device="cpu" if runner.use_cpu_embeddings else None,
    )

    try:
        # 4. Ingest evaluation corpus for target questions
        print("📥 Ingesting evaluation corpus from local Wikipedia cache...", flush=True)
        t_ingest_start = time.perf_counter()
        corpus_count = runner.prepare_evaluation_corpus(target_questions, harness)
        print(f"✅ Ingested {corpus_count} passages in {time.perf_counter() - t_ingest_start:.2f}s.\n", flush=True)

        factuality_eval = FactualityEvaluator()
        reasoning_eval = ReasoningEvaluator()
        retrieval_eval = RetrievalEvaluator()
        diagnostician = FailureDiagnostician()

        comparison_results = []

        # 5. Execute each target question
        for idx, q in enumerate(target_questions, 1):
            qid = str(q.question_id)
            prev_rec = prev_results.get(qid, {})
            prev_ans = prev_rec.get("generated_answer", "N/A")
            prev_fact = prev_rec.get("factuality", {})
            prev_score = prev_fact.get("factuality_score", 0.0)
            prev_status = prev_fact.get("answer_status", "failed")

            print(f"------------------------------------------------------------------", flush=True)
            print(f"[{idx}/{len(target_questions)}] Executing Question ID {qid}", flush=True)
            print(f"  Prompt: {q.prompt}", flush=True)
            print(f"  Reference Answer: {q.reference_answer}", flush=True)
            print(f"  Previous Answer:  {prev_ans[:90]} (Status: {prev_status}, Score: {prev_score})", flush=True)

            t0 = time.perf_counter()
            trace = harness.execute_question(q, mode="hybrid", top_k=14)
            exec_latency = time.perf_counter() - t0

            chunks = trace.get("retrieval_trace", {}).get("retrieved_chunks", [])
            context = trace.get("full_context") or "\n\n".join(c.get("text", "") for c in chunks) or trace.get("context_preview", "")
            new_ans = trace.get("generated_answer", "")
            new_mode = trace.get("generation_mode", "")
            proof_edges = trace.get("proof_ledger", {}).get("proof_edges", [])

            # Run Evaluators
            fact_res = factuality_eval.evaluate(q, new_ans, context)
            reas_res = reasoning_eval.evaluate(q, new_ans, context)
            ret_res = retrieval_eval.evaluate(q, chunks)
            diag_res = diagnostician.diagnose(q, fact_res, reas_res, ret_res, trace)

            print(f"  ✨ New Pipeline Answer: {new_ans}", flush=True)
            print(f"  Mode: {new_mode} | Proof Edges: {len(proof_edges)} | Latency: {exec_latency:.2f}s", flush=True)
            print(f"  New Status: {fact_res.answer_status} | Factuality Score: {fact_res.factuality_score:.2f} | Diag: {diag_res.primary_failure}", flush=True)

            is_improved = fact_res.factuality_score > prev_score
            is_correct = fact_res.answer_status in ["correct", "fuzzy_match"] or fact_res.factuality_score >= 0.75

            print(f"  Outcome: {'🟢 RESOLVED / IMPROVED!' if is_improved or is_correct else '⚪ Outcome recorded'}", flush=True)

            comparison_results.append({
                "qid": qid,
                "prompt": q.prompt,
                "reference": q.reference_answer,
                "prev_answer": prev_ans,
                "prev_status": prev_status,
                "prev_score": prev_score,
                "new_answer": new_ans,
                "new_status": fact_res.answer_status,
                "new_score": fact_res.factuality_score,
                "is_improved": is_improved,
                "is_correct": is_correct,
                "proof_edges_count": len(proof_edges),
                "latency_s": round(exec_latency, 2),
            })
            time.sleep(1.0)

        print("\n==================================================================", flush=True)
        print("📊 TARGETED VERIFICATION RUN SUMMARY", flush=True)
        print("==================================================================", flush=True)
        for res in comparison_results:
            status_icon = "🟢" if res["is_correct"] else ("🟡" if res["is_improved"] else "🔴")
            print(f"{status_icon} QID {res['qid']}: Ref='{res['reference'][:30]}' | New='{res['new_answer'][:40]}' | Score: {res['prev_score']:.2f} -> {res['new_score']:.2f}", flush=True)

        # Save summary report
        out_file = PROJECT_ROOT.parent / "Artifacts" / "benchmarks" / "frames" / "reports" / "TARGETED_FAILED_QUESTIONS_VERIFICATION_REPORT.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(comparison_results, f, indent=2)
        print(f"\nReport saved to: {out_file}", flush=True)

    finally:
        # Teardown sandbox harness
        harness.teardown()
        print("✅ Sandbox harness cleanly torn down (zero residual data).", flush=True)

if __name__ == "__main__":
    main()
