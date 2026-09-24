"""
FRAMES Benchmark Head-to-Head Comparative Auditor
Compares baseline run vs consolidated run question-by-question across all 824 questions.
Computes metric deltas, win/loss/tie matrices, failure category migrations, and edge-case resolutions.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Force UTF-8 stdout
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = PROJECT_ROOT.parent / "Artifacts" / "benchmarks" / "frames" / "checkpoints" / "frames_hybrid_full_824_fresh_checkpoint.jsonl"
DEFAULT_CONSOLIDATED = PROJECT_ROOT.parent / "Artifacts" / "benchmarks" / "frames" / "checkpoints" / "frames_hybrid_consolidated_824_checkpoint.jsonl"
DEFAULT_OUTPUT_REPORT = PROJECT_ROOT.parent / "Artifacts" / "benchmarks" / "frames" / "reports" / "FRAMES_CONSOLIDATED_VS_BASELINE_COMPARISON_REPORT.md"

def load_checkpoint(file_path: Path) -> Dict[str, Dict[str, Any]]:
    records = {}
    if not file_path.exists():
        return records
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("\x00"):
                try:
                    rec = json.loads(line)
                    qid = str(rec.get("question_id"))
                    records[qid] = rec
                except Exception:
                    continue
    return records

def compare_runs(baseline_file: Path, consolidated_file: Path, output_report: Path) -> Dict[str, Any]:
    base_data = load_checkpoint(baseline_file)
    cons_data = load_checkpoint(consolidated_file)

    common_qids = [qid for qid in base_data if qid in cons_data]
    # Sort numerically if possible
    def sort_key(q):
        try:
            return int(q)
        except Exception:
            return q
    common_qids.sort(key=sort_key)

    total_compared = len(common_qids)
    if total_compared == 0:
        print(f"⚠️  No common questions found between {baseline_file.name} ({len(base_data)}) and {consolidated_file.name} ({len(cons_data)}).")
        return {}

    wins = 0      # Cons correct, Base incorrect
    losses = 0    # Cons incorrect, Base correct
    ties_both_win = 0
    ties_both_fail = 0

    base_fact_scores = []
    cons_fact_scores = []
    base_reas_scores = []
    cons_reas_scores = []
    base_cov_scores = []
    cons_cov_scores = []
    base_latencies = []
    cons_latencies = []

    type_stats: Dict[str, Dict[str, Any]] = {}
    failure_migration: Dict[str, Dict[str, int]] = {}
    changed_answers = []

    for qid in common_qids:
        b = base_data[qid]
        c = cons_data[qid]

        b_fact = b.get("factuality", {})
        c_fact = c.get("factuality", {})
        b_reas = b.get("reasoning", {})
        c_reas = c.get("reasoning", {})
        b_ret = b.get("retrieval", {})
        c_ret = c.get("retrieval", {})
        b_diag = b.get("diagnosis", {})
        c_diag = c.get("diagnosis", {})

        b_corr = b_fact.get("answer_status") == "correct" or b_fact.get("reference_correctness_score", 0.0) >= 0.85
        c_corr = c_fact.get("answer_status") == "correct" or c_fact.get("reference_correctness_score", 0.0) >= 0.85

        if c_corr and not b_corr:
            wins += 1
            changed_answers.append({
                "question_id": qid,
                "type": "WIN (Improved)",
                "prompt": c.get("prompt", ""),
                "ref": c.get("reference_answer", ""),
                "base_ans": b.get("generated_answer", ""),
                "cons_ans": c.get("generated_answer", ""),
            })
        elif not c_corr and b_corr:
            losses += 1
            changed_answers.append({
                "question_id": qid,
                "type": "LOSS (Regressed)",
                "prompt": c.get("prompt", ""),
                "ref": c.get("reference_answer", ""),
                "base_ans": b.get("generated_answer", ""),
                "cons_ans": c.get("generated_answer", ""),
            })
        elif c_corr and b_corr:
            ties_both_win += 1
        else:
            ties_both_fail += 1

        b_fs = float(b_fact.get("factuality_score", 0.0))
        c_fs = float(c_fact.get("factuality_score", 0.0))
        b_rs = float(b_reas.get("overall_reasoning_score", 0.0))
        c_rs = float(c_reas.get("overall_reasoning_score", 0.0))
        b_cs = float(b_ret.get("evidence_coverage", 0.0))
        c_cs = float(c_ret.get("evidence_coverage", 0.0))
        b_lat = float(b.get("total_latency_ms", 0.0))
        c_lat = float(c.get("total_latency_ms", 0.0))

        base_fact_scores.append(b_fs)
        cons_fact_scores.append(c_fs)
        base_reas_scores.append(b_rs)
        cons_reas_scores.append(c_rs)
        base_cov_scores.append(b_cs)
        cons_cov_scores.append(c_cs)
        base_latencies.append(b_lat)
        cons_latencies.append(c_lat)

        # Category stats
        for rtype in c.get("reasoning_types", []):
            if rtype not in type_stats:
                type_stats[rtype] = {"count": 0, "base_wins": 0, "cons_wins": 0}
            type_stats[rtype]["count"] += 1
            if b_corr:
                type_stats[rtype]["base_wins"] += 1
            if c_corr:
                type_stats[rtype]["cons_wins"] += 1

        # Failure migration
        b_fail = b_diag.get("primary_failure") or ("NONE" if b_corr else "UNKNOWN_FAILURE")
        c_fail = c_diag.get("primary_failure") or ("NONE" if c_corr else "UNKNOWN_FAILURE")
        if b_fail not in failure_migration:
            failure_migration[b_fail] = {}
        failure_migration[b_fail][c_fail] = failure_migration[b_fail].get(c_fail, 0) + 1

    # Aggregates
    import statistics
    b_mean_fact = statistics.mean(base_fact_scores) if base_fact_scores else 0.0
    c_mean_fact = statistics.mean(cons_fact_scores) if cons_fact_scores else 0.0
    b_mean_reas = statistics.mean(base_reas_scores) if base_reas_scores else 0.0
    c_mean_reas = statistics.mean(cons_reas_scores) if cons_reas_scores else 0.0
    b_mean_cov = statistics.mean(base_cov_scores) if base_cov_scores else 0.0
    c_mean_cov = statistics.mean(cons_cov_scores) if cons_cov_scores else 0.0
    b_med_lat = statistics.median(base_latencies) if base_latencies else 0.0
    c_med_lat = statistics.median(cons_latencies) if cons_latencies else 0.0

    b_overall = (b_mean_fact * 0.4) + (b_mean_reas * 0.4) + (b_mean_cov * 0.2)
    c_overall = (c_mean_fact * 0.4) + (c_mean_reas * 0.4) + (c_mean_cov * 0.2)

    # Markdown report generation
    report_lines = [
        "# FRAMES Benchmark: Consolidated Architecture vs Baseline Comparative Audit Report",
        "",
        f"**Audit Timestamp**: {Path(output_report).stat().st_mtime if output_report.exists() else 'Real-time'}",
        f"**Baseline Ledger**: `{baseline_file.name}` ({len(base_data)} questions total)",
        f"**Consolidated Ledger**: `{consolidated_file.name}` ({len(cons_data)} evaluated so far)",
        f"**Sample Comparison Window**: **{total_compared} questions evaluated head-to-head**",
        "",
        "---",
        "",
        "## 1. Executive Summary & Win/Loss Matrix",
        "",
        "| Metric | Baseline Run | Consolidated Run | Delta (Δ) | Direction |",
        "| :--- | :---: | :---: | :---: | :---: |",
        f"| **Overall Benchmark Score** | **{b_overall*100:.2f}%** | **{c_overall*100:.2f}%** | **{(c_overall - b_overall)*100:+.2f}%** | {'🟢 IMPROVED' if c_overall >= b_overall else '🔴 REGRESSED'} |",
        f"| **Factuality Score** | {b_mean_fact*100:.2f}% | {c_mean_fact*100:.2f}% | {(c_mean_fact - b_mean_fact)*100:+.2f}% | {'🟢' if c_mean_fact >= b_mean_fact else '🔴'} |",
        f"| **Reasoning Score** | {b_mean_reas*100:.2f}% | {c_mean_reas*100:.2f}% | {(c_mean_reas - b_mean_reas)*100:+.2f}% | {'🟢' if c_mean_reas >= b_mean_reas else '🔴'} |",
        f"| **Evidence Retrieval Coverage** | {b_mean_cov*100:.2f}% | {c_mean_cov*100:.2f}% | {(c_mean_cov - b_mean_cov)*100:+.2f}% | {'🟢' if c_mean_cov >= b_mean_cov else '🔴'} |",
        f"| **Median Latency** | {b_med_lat:.1f} ms | {c_med_lat:.1f} ms | {(c_med_lat - b_med_lat):+.1f} ms | {'⚡ FASTER' if c_med_lat <= b_med_lat else '⏱️ SLOWER'} |",
        "",
        "### Head-to-Head Question Match Outcomes",
        "",
        f"- **Consolidated Wins (Flipped from Incorrect to Correct)**: **{wins}** ({wins/total_compared*100:.1f}%)",
        f"- **Consolidated Losses (Regressed)**: **{losses}** ({losses/total_compared*100:.1f}%)",
        f"- **Ties (Both Correct)**: **{ties_both_win}** ({ties_both_win/total_compared*100:.1f}%)",
        f"- **Ties (Both Incorrect)**: **{ties_both_fail}** ({ties_both_fail/total_compared*100:.1f}%)",
        f"- **Net Correctness Shift**: **{wins - losses:+d} net correct questions**",
        "",
        "---",
        "",
        "## 2. Breakdown by Reasoning Category",
        "",
        "| Reasoning Dimension | Sample Count | Baseline Correct % | Consolidated Correct % | Accuracy Shift |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]

    for rtype, stats in sorted(type_stats.items(), key=lambda x: x[1]["count"], reverse=True):
        cnt = stats["count"]
        b_pct = (stats["base_wins"] / cnt) * 100
        c_pct = (stats["cons_wins"] / cnt) * 100
        diff = c_pct - b_pct
        report_lines.append(f"| **{rtype}** | {cnt} | {b_pct:.1f}% | {c_pct:.1f}% | **{diff:+.1f}%** |")

    report_lines.extend([
        "",
        "---",
        "",
        "## 3. Failure Taxonomy Migration Matrix",
        "Tracks how diagnostic failure categories transformed under the consolidated architecture:",
        "",
        "| Baseline Failure Attribution | Consolidated Outcome | Frequency |",
        "| :--- | :--- | :---: |",
    ])

    for b_fail, c_map in sorted(failure_migration.items()):
        for c_fail, freq in sorted(c_map.items(), key=lambda x: x[1], reverse=True):
            status_tag = "🟢 RESOLVED TO CORRECT" if c_fail == "NONE" else f"🔄 Reclassified to `{c_fail}`"
            report_lines.append(f"| `{b_fail}` | {status_tag} | {freq} |")

    if changed_answers:
        report_lines.extend([
            "",
            "---",
            "",
            "## 4. Representative Sample Transitions",
            "",
            "| QID | Type | Question Prompt | Reference Answer | Baseline Answer | Consolidated Answer |",
            "| :---: | :---: | :--- | :--- | :--- | :--- |",
        ])
        for ex in changed_answers[:15]:
            q_clean = ex["prompt"].replace("\n", " ")[:60]
            ref_clean = ex["ref"].replace("\n", " ")[:30]
            b_clean = ex["base_ans"].replace("\n", " ")[:35]
            c_clean = ex["cons_ans"].replace("\n", " ")[:35]
            report_lines.append(f"| **Q{ex['question_id']}** | {ex['type']} | {q_clean}... | {ref_clean} | {b_clean} | {c_clean} |")

    report_lines.append("")
    output_report.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report, "w", encoding="utf-8") as rf:
        rf.write("\n".join(report_lines) + "\n")

    print(f"📊 Comparative report written to: {output_report}")
    return {
        "total_compared": total_compared,
        "wins": wins,
        "losses": losses,
        "net_gain": wins - losses,
        "base_overall": round(b_overall, 4),
        "cons_overall": round(c_overall, 4),
        "delta_overall": round(c_overall - b_overall, 4),
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FRAMES Run Comparative Auditor")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--consolidated", type=Path, default=DEFAULT_CONSOLIDATED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_REPORT)
    args = parser.parse_args()

    compare_runs(args.baseline, args.consolidated, args.output)
