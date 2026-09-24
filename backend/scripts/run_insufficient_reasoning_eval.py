"""
Evaluation Script for All Questions that previously produced 'INSUFFICIENT REASONING PATH'.
Runs them through the updated next-generation production pipeline and evaluates the answer rate,
factuality rate, and resolution of previous abstentions.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Force UTF-8 on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.benchmarks.frames.data.loader import FramesDatasetLoader
from evaluation.benchmarks.frames.data.schema import FramesQuestion
from evaluation.benchmarks.frames.isolation.harness import IsolatedFramesHarness
from evaluation.benchmarks.frames.evaluators.factuality import FactualityEvaluator
from evaluation.benchmarks.frames.evaluators.reasoning import ReasoningEvaluator
from evaluation.benchmarks.frames.evaluators.retrieval import RetrievalEvaluator
from evaluation.benchmarks.frames.evaluators.diagnostician import FailureDiagnostician
from evaluation.benchmarks.frames.runners.runner import FramesBenchmarkRunner


def get_all_insufficient_reasoning_questions() -> List[Dict[str, Any]]:
    """Extracts all records where 'INSUFFICIENT REASONING PATH' was emitted."""
    ckpt_path = PROJECT_ROOT.parent / "Artifacts" / "benchmarks" / "frames" / "checkpoints" / "frames_hybrid_consolidated_824_checkpoint.jsonl"
    insufficient_records = []
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint file not found: {ckpt_path}")

    with open(ckpt_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                ans = rec.get("generated_answer", "")
                if "INSUFFICIENT REASONING PATH" in ans:
                    insufficient_records.append(rec)
            except Exception:
                continue

    return insufficient_records


def main():
    parser = argparse.ArgumentParser(description="Evaluate all INSUFFICIENT REASONING PATH questions on updated pipeline.")
    parser.add_argument("--limit", type=int, default=None, help="Number of questions to evaluate (default: all)")
    parser.add_argument("--offset", type=int, default=0, help="Offset into the question list")
    parser.add_argument("--stratified", action="store_true", help="Sample evenly across the 4 fallback trigger types")
    args = parser.parse_args()

    print("==================================================================", flush=True)
    print("🔍 EXTRACTING ALL 'INSUFFICIENT REASONING PATH' QUESTIONS", flush=True)
    print("==================================================================", flush=True)

    records = get_all_insufficient_reasoning_questions()
    print(f"Total 'INSUFFICIENT REASONING PATH' questions extracted: {len(records)}", flush=True)

    # Trigger breakdown
    by_trigger = {}
    for r in records:
        trig = r.get("audit", {}).get("exact_fallback_trigger", "OTHER")
        by_trigger.setdefault(trig, []).append(r)

    print("\nTrigger Distribution:")
    for trig, qs in sorted(by_trigger.items(), key=lambda x: -len(x[1])):
        print(f"  • {trig}: {len(qs)} questions", flush=True)

    loader = FramesDatasetLoader()
    all_dataset_questions = {str(q.question_id): q for q in loader.get_questions()}

    # Select target questions
    if args.stratified and args.limit:
        selected_records = []
        per_type = max(1, args.limit // len(by_trigger))
        for trig, qs in by_trigger.items():
            selected_records.extend(qs[:per_type])
        selected_records = selected_records[:args.limit]
    else:
        selected_records = records[args.offset : (args.offset + args.limit) if args.limit else None]

    target_questions = [all_dataset_questions[str(r["question_id"])] for r in selected_records if str(r["question_id"]) in all_dataset_questions]
    print(f"\nSelected {len(target_questions)} questions for evaluation run.", flush=True)

    # Output paths
    output_dir = PROJECT_ROOT.parent / "Artifacts" / "benchmarks" / "frames"
    ckpt_dir = output_dir / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    eval_ckpt_file = ckpt_dir / "insufficient_reasoning_rerun_checkpoint.jsonl"

    completed_ids = set()
    if eval_ckpt_file.exists():
        with open(eval_ckpt_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    c_rec = json.loads(line)
                    completed_ids.add(str(c_rec.get("question_id")))
                except Exception:
                    continue
        print(f"Loaded {len(completed_ids)} already completed questions from {eval_ckpt_file.name}.", flush=True)

    runner = FramesBenchmarkRunner(mode="hybrid", experiment_name="insufficient_reasoning_rerun")
    harness = IsolatedFramesHarness(
        session_id="insufficient_reasoning_rerun",
        device="cpu" if runner.use_cpu_embeddings else None,
    )

    factuality_eval = FactualityEvaluator()
    reasoning_eval = ReasoningEvaluator()
    retrieval_eval = RetrievalEvaluator()
    diagnostician = FailureDiagnostician()

    try:
        # Ingest corpus
        pending_questions = [q for q in target_questions if str(q.question_id) not in completed_ids]
        if pending_questions:
            print(f"\n📥 Ingesting evaluation corpus for {len(pending_questions)} questions...", flush=True)
            t_ingest = time.perf_counter()
            count = runner.prepare_evaluation_corpus(pending_questions, harness)
            print(f"✅ Ingested {count} passages in {time.perf_counter() - t_ingest:.2f}s.\n", flush=True)

        results = []
        flipped_to_correct = 0
        flipped_to_answered = 0
        still_abstained = 0

        for idx, q in enumerate(target_questions, 1):
            qid = str(q.question_id)
            orig_rec = next((r for r in selected_records if str(r.get("question_id")) == qid), {})
            orig_trig = orig_rec.get("audit", {}).get("exact_fallback_trigger", "UNKNOWN")

            if qid in completed_ids:
                continue

            print(f"[{idx}/{len(target_questions)}] QID {qid} (Prior Trigger: {orig_trig})", flush=True)
            print(f"  Prompt: {q.prompt[:95]}...", flush=True)
            print(f"  Ref:    {q.reference_answer}", flush=True)

            t0 = time.perf_counter()
            trace = harness.execute_question(q, mode="hybrid", top_k=14)
            exec_time = time.perf_counter() - t0

            chunks = trace.get("retrieval_trace", {}).get("retrieved_chunks", [])
            context = trace.get("full_context") or "\n\n".join(c.get("text", "") for c in chunks) or trace.get("context_preview", "")
            new_ans = trace.get("generated_answer", "")
            new_mode = trace.get("generation_mode", "")
            proof_edges = trace.get("proof_ledger", {}).get("proof_edges", [])

            fact_res = factuality_eval.evaluate(q, new_ans, context)
            reas_res = reasoning_eval.evaluate(q, new_ans, context)
            ret_res = retrieval_eval.evaluate(q, chunks)
            diag_res = diagnostician.diagnose(q, fact_res, reas_res, ret_res, trace)

            is_correct = fact_res.answer_status in ["correct", "fuzzy_match"] or fact_res.factuality_score >= 0.75
            is_answered = "insufficient" not in str(new_ans).lower()

            if is_correct:
                status_icon = "🟢 CORRECT"
                flipped_to_correct += 1
                flipped_to_answered += 1
            elif is_answered:
                status_icon = "🟡 ANSWERED (Factual delta)"
                flipped_to_answered += 1
            else:
                status_icon = "⚪ ABSTAINED"
                still_abstained += 1

            print(f"  ✨ Ans: {new_ans[:75]} | {status_icon} (Score: {fact_res.factuality_score:.2f}) [{exec_time:.2f}s]\n", flush=True)

            res_record = {
                "question_id": qid,
                "prompt": q.prompt,
                "reference_answer": q.reference_answer,
                "prior_trigger": orig_trig,
                "prior_answer": "INSUFFICIENT REASONING PATH",
                "prior_score": 0.0,
                "new_answer": new_ans,
                "new_mode": new_mode,
                "new_status": fact_res.answer_status,
                "new_factuality_score": fact_res.factuality_score,
                "is_correct": is_correct,
                "is_answered": is_answered,
                "primary_failure": diag_res.primary_failure,
                "latency_s": round(exec_time, 2)
            }
            results.append(res_record)

            # Atomic commit to checkpoint
            with open(eval_ckpt_file, "a", encoding="utf-8") as cf:
                cf.write(json.dumps(res_record, ensure_ascii=False) + "\n")
                cf.flush()

            time.sleep(0.5)

        # Print Final Summary
        total_eval = len(results)
        print("==================================================================", flush=True)
        print("📊 'INSUFFICIENT REASONING PATH' EVALUATION SUMMARY", flush=True)
        print("==================================================================", flush=True)
        print(f"Total Questions Evaluated: {total_eval}", flush=True)
        if total_eval > 0:
            print(f"🟢 Flipped to CORRECT:           {flipped_to_correct} ({flipped_to_correct/total_eval*100:.1f}%)", flush=True)
            print(f"🟡 Flipped to ANSWERED (Non-abs): {flipped_to_answered} ({flipped_to_answered/total_eval*100:.1f}%)", flush=True)
            print(f"⚪ Remained Controlled Abstain:   {still_abstained} ({still_abstained/total_eval*100:.1f}%)", flush=True)

        report_file = output_dir / "reports" / "INSUFFICIENT_REASONING_EVALUATION_REPORT.json"
        with open(report_file, "w", encoding="utf-8") as rf:
            json.dump({
                "total_evaluated": total_eval,
                "flipped_to_correct": flipped_to_correct,
                "flipped_to_answered": flipped_to_answered,
                "still_abstained": still_abstained,
                "results": results,
            }, rf, indent=2)
        print(f"\nDetailed report saved to: {report_file}", flush=True)

    finally:
        harness.teardown()
        print("✅ Harness cleanly torn down.", flush=True)


if __name__ == "__main__":
    main()
