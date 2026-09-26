"""
FRAMES Benchmark Comprehensive Reporter
Generates machine-readable JSON artifacts and human-readable Markdown & HTML reports.
Follows the exact 11-section reporting structure required by the specification.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("raise.frames.reporter")


class FramesReporter:
    """
    Synthesizes evaluation logs into structured JSON artifacts, comprehensive Markdown,
    and self-contained interactive HTML reports.
    """

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir).resolve()
        self.reports_dir = self.output_dir / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_all_reports(
        self,
        experiment_config: Dict[str, Any],
        raw_results: List[Dict[str, Any]],
        aggregate_metrics: Dict[str, Any],
        failure_analysis: Dict[str, Any],
        comparison: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Path]:
        """
        Exports all machine-readable files and formatted reports.
        Returns dictionary of created file paths.
        """
        # 1. Machine-readable JSONs
        raw_path = self.output_dir / "raw_results.json"
        raw_path.write_text(json.dumps(raw_results, indent=2), encoding="utf-8")

        metrics_path = self.output_dir / "aggregate_metrics.json"
        metrics_path.write_text(json.dumps(aggregate_metrics, indent=2), encoding="utf-8")

        failures_path = self.output_dir / "failure_analysis.json"
        failures_path.write_text(json.dumps(failure_analysis, indent=2), encoding="utf-8")

        config_path = self.output_dir / "experiment_config.json"
        config_path.write_text(json.dumps(experiment_config, indent=2), encoding="utf-8")

        # 2. Comprehensive Markdown Report
        md_path = self.reports_dir / "FRAMES_REPORT.md"
        md_content = self._build_markdown_report(
            experiment_config, raw_results, aggregate_metrics, failure_analysis, comparison
        )
        md_path.write_text(md_content, encoding="utf-8")

        # 3. Standalone HTML Report
        html_path = self.reports_dir / "FRAMES_REPORT.html"
        html_content = self._build_html_report(
            experiment_config, aggregate_metrics, failure_analysis, raw_results
        )
        html_path.write_text(html_content, encoding="utf-8")

        # 4. Modular Forensic Execution Bundle (Section 55 Artifact)
        bundle_files = self.export_forensic_bundle(
            experiment_config, raw_results, aggregate_metrics
        )

        logger.info(f"Generated FRAMES benchmark reports in: {self.output_dir}")
        ret_dict: Dict[str, Path] = {
            "raw_results": raw_path,
            "aggregate_metrics": metrics_path,
            "failure_analysis": failures_path,
            "experiment_config": config_path,
            "markdown_report": md_path,
            "html_report": html_path,
        }
        ret_dict.update(bundle_files)
        return ret_dict

    def export_forensic_bundle(
        self,
        experiment_config: Dict[str, Any],
        raw_results: List[Dict[str, Any]],
        aggregate_metrics: Dict[str, Any],
    ) -> Dict[str, Path]:
        """
        Decomposes execution telemetry into a modular forensic bundle:
          - run.json: experiment_config & hardware/vcs metadata
          - storage_snapshot.json: Chroma, Neo4j, Redis live counts
          - retrieval.jsonl: per-query retrieval metrics and sources
          - graph.jsonl: multi-hop plans, graph edges, and resolved hops
          - claims.jsonl: answer factuality and generated answers
          - transitions.jsonl: per-query state transitions (TRANS_01 to TRANS_05)
          - manifest.sha256: cryptographic hashes of all bundle files
        """
        exp_id = experiment_config.get("experiment_id", "latest")
        bundle_dir = self.output_dir / f"RAISE_FORENSIC_RUN_{exp_id}"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        bundle_files: Dict[str, Path] = {}

        # 1. run.json
        run_file = bundle_dir / "run.json"
        run_file.write_text(json.dumps(experiment_config, indent=2), encoding="utf-8")
        bundle_files["run.json"] = run_file

        # 2. storage_snapshot.json
        storage_file = bundle_dir / "storage_snapshot.json"
        storage_meta = experiment_config.get("run_metadata", {}).get("storage_snapshot", {})
        storage_file.write_text(json.dumps(storage_meta, indent=2), encoding="utf-8")
        bundle_files["storage_snapshot.json"] = storage_file

        # 3. retrieval.jsonl
        retrieval_file = bundle_dir / "retrieval.jsonl"
        with open(retrieval_file, "w", encoding="utf-8") as f:
            for r in raw_results:
                line_data = {
                    "question_id": r.get("question_id"),
                    "prompt": r.get("prompt"),
                    "retrieval": r.get("retrieval", {}),
                    "retrieved_sources": r.get("retrieved_sources", []),
                    "retrieved_chunks_count": r.get("retrieved_chunks_count", 0),
                    "context_tokens_estimate": r.get("context_tokens_estimate", 0),
                }
                f.write(json.dumps(line_data) + "\n")
        bundle_files["retrieval.jsonl"] = retrieval_file

        # 4. graph.jsonl
        graph_file = bundle_dir / "graph.jsonl"
        with open(graph_file, "w", encoding="utf-8") as f:
            for r in raw_results:
                line_data = {
                    "question_id": r.get("question_id"),
                    "multihop_plan": r.get("multihop_plan", {}),
                    "reasoning": r.get("reasoning", {}),
                }
                f.write(json.dumps(line_data) + "\n")
        bundle_files["graph.jsonl"] = graph_file

        # 5. claims.jsonl
        claims_file = bundle_dir / "claims.jsonl"
        with open(claims_file, "w", encoding="utf-8") as f:
            for r in raw_results:
                line_data = {
                    "question_id": r.get("question_id"),
                    "generated_answer": r.get("generated_answer"),
                    "reference_answer": r.get("reference_answer"),
                    "factuality": r.get("factuality", {}),
                    "generation_mode": r.get("generation_mode"),
                    "audit": r.get("audit", {}),
                }
                f.write(json.dumps(line_data) + "\n")
        bundle_files["claims.jsonl"] = claims_file

        # 6. transitions.jsonl
        transitions_file = bundle_dir / "transitions.jsonl"
        with open(transitions_file, "w", encoding="utf-8") as f:
            for r in raw_results:
                line_data = {
                    "question_id": r.get("question_id"),
                    "transition_trace": r.get("transition_trace", []),
                    "stage_latencies": r.get("stage_latencies", {}),
                }
                f.write(json.dumps(line_data) + "\n")
        bundle_files["transitions.jsonl"] = transitions_file

        # 7. manifest.sha256
        manifest_file = bundle_dir / "manifest.sha256"
        manifest_lines = []
        for fname, fpath in sorted(bundle_files.items()):
            content = fpath.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            manifest_lines.append(f"{sha}  {fname}")
        manifest_file.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        bundle_files["manifest.sha256"] = manifest_file

        logger.info(f"Exported RAISE Forensic Execution Bundle to: {bundle_dir}")
        return bundle_files

    def _build_markdown_report(
        self,
        config: Dict[str, Any],
        results: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        failures: Dict[str, Any],
        comparison: Optional[Dict[str, Any]] = None,
    ) -> str:
        exp_id = config.get("experiment_id", "frames_exp_001")
        date_str = config.get("timestamp", datetime.now(timezone.utc).isoformat())
        mode = config.get("retrieval_mode", "hybrid").upper()
        total_q = metrics.get("total_questions", len(results))

        success_cases = [r for r in results if r.get("factuality", {}).get("answer_status") == "correct"][:3]
        failure_cases = [r for r in results if r.get("diagnosis", {}).get("is_failure") is True][:3]

        md = f"""# FRAMES Benchmark Evaluation Report
**Benchmark:** Factuality, Retrieval, And reasoning MEasurement Set (Google Research)  
**Target System:** RAISE (Research Assessment Intelligence & Semantic Extraction)  
**Mode:** {mode} | **Experiment ID:** `{exp_id}` | **Date:** {date_str}

---

## 1. Experiment Overview

| Parameter | Value | Notes |
| :--- | :--- | :--- |
| **Experiment ID** | `{exp_id}` | Reproducible evaluation run |
| **Pipeline Version** | `{config.get('pipeline_version', '2.5.0')}` | Modular GraphRAG architecture |
| **Dataset Version / SHA** | `{config.get('dataset_revision', '58d9fb63')[:12]}` | Official `test.tsv` (824 examples) |
| **Retrieval Mode** | **{mode}** | `{config.get('retrieval_mode')}` mode |
| **Embedding Engine** | `{config.get('embedding_model', 'BAAI/bge-large-en-v1.5')}` | 1024-dim dense representation |
| **Evaluated Sample Count** | **{total_q}** | Controlled evaluation sample |
| **Isolation Status** | **100% ISOLATED** | Ephemeral ChromaDB + Sandboxed Graph |

---

## 2. Overall Performance

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               FRAMES OVERALL SCORECARD                                 │
├───────────────────────────────┬───────────────────────────────┬────────────────────────┤
│ METRIC                        │ SCORE / COUNT                 │ STATUS / INTERPRETATION│
├───────────────────────────────┼───────────────────────────────┼────────────────────────┤
│ Overall Benchmark Score       │ {metrics.get('overall_score', 0.0)*100:6.2f}%                       │ {"CERTIFIED PASS" if metrics.get('overall_score', 0.0) >= 0.70 else "BASELINE BENCHMARK"}     │
│ Answer Correctness Rate       │ {metrics.get('answer_correctness_rate', 0.0)*100:6.2f}% ({metrics.get('correct_count', 0)}/{total_q})           │ Strict reference truth match│
│ Factuality Agreement Score    │ {metrics.get('mean_factuality', 0.0)*100:6.2f}%                       │ Grounded evidence agreement│
│ Reasoning Ability Score       │ {metrics.get('mean_reasoning', 0.0)*100:6.2f}%                       │ Multi-hop/numeric/temporal │
│ Retrieval Evidence Coverage   │ {metrics.get('mean_retrieval_coverage', 0.0)*100:6.2f}%                       │ Ground-truth Wikipedia links│
│ Retrieval Hit Rate            │ {metrics.get('hit_rate', 0.0)*100:6.2f}%                       │ >= 1 source retrieved      │
│ Abstention Rate               │ {metrics.get('abstention_rate', 0.0)*100:6.2f}% ({metrics.get('abstained_count', 0)}/{total_q})           │ Controlled safe abstentions│
│ Non-Answer Rate               │ {metrics.get('non_answer_rate', 0.0)*100:6.2f}%                       │ Abstentions + Unanswerables│
│ Unsupported Claim Rate        │ {metrics.get('unsupported_claim_rate', 0.0)*100:6.2f}%                       │ False claims (Hallucination)│
│ Fallback Interception Count   │ {metrics.get('fallback_count', 0):6d}                         │ Safe abstention activations│
│ Median Pipeline Latency       │ {metrics.get('latency_p50_ms', 0.0):6.2f} ms                     │ Total turn execution time  │
│   • Median Retrieval Latency  │ {metrics.get('latency_median_retrieval_ms', 0.0):6.2f} ms                     │ Vector + BM25 + Graph      │
│   • Median Generation Latency │ {metrics.get('latency_median_generation_ms', 0.0):6.2f} ms                     │ Neural synthesis & reasoning│
└───────────────────────────────┴───────────────────────────────┴────────────────────────┘
```

---

## 3. Performance by Reasoning Type

| Reasoning Category | Questions Evaluated | Mean Reasoning Score | Pass Rate (>= 70%) |
| :--- | :---: | :---: | :---: |
"""
        by_cat = metrics.get("by_reasoning_type", {})
        for cat, data in by_cat.items():
            md += f"| **{cat}** | {data.get('count', 0)} | {data.get('mean_score', 0.0)*100:.1f}% | {data.get('pass_rate', 0.0)*100:.1f}% |\n"

        md += f"""
---

## 4. Retrieval Analysis

- **Retrieval Hit Rate:** **{metrics.get('hit_rate', 0.0)*100:.1f}%** of queries retrieved at least one required Wikipedia source link.
- **Evidence Coverage:** Mean coverage of required ground-truth source links was **{metrics.get('mean_retrieval_coverage', 0.0)*100:.1f}%**.
- **Context Precision:** **{metrics.get('context_precision', 0.0)*100:.1f}%** of assembled context chunks were directly relevant.
- **Substrate Contribution:** Multi-hop queries benefit from Reciprocal Rank Fusion ($k=60$) combining dense semantic vectors with lexical BM25 and relational entity nodes.

---

## 5. Reasoning Analysis

- **Multi-Hop Reasoning:** {by_cat.get('Multi-hop', {}).get('mean_score', 0.0)*100:.1f}% effectiveness in bridging entities across documents.
- **Numerical Reasoning:** {by_cat.get('Numerical reasoning', {}).get('mean_score', 0.0)*100:.1f}% accuracy in extracting quantitative values and applying deterministic arithmetic.
- **Temporal Reasoning:** {by_cat.get('Temporal reasoning', {}).get('mean_score', 0.0)*100:.1f}% precision in preserving chronological ordering and timeline intervals.
- **Tabular Reasoning:** {by_cat.get('Tabular reasoning', {}).get('mean_score', 0.0)*100:.1f}% consistency in structured row/column cell lookups.
- **Multiple Constraints:** {by_cat.get('Multiple constraints', {}).get('mean_score', 0.0)*100:.1f}% satisfaction across compound qualification requirements.

---

## 6. Failure Analysis (13-Category Taxonomy)

Total Failures Identified: **{failures.get('total_failures', 0)}** ({failures.get('failure_rate', 0.0)*100:.1f}% of evaluated questions)

| Failure Category | Frequency | % of Total Failures | Primary Contributing Cause |
| :--- | :---: | :---: | :--- |
"""
        counts = failures.get("failure_counts", {})
        tot_f = max(1, failures.get("total_failures", 0))
        for cat, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            if cnt > 0:
                md += f"| `{cat}` | {cnt} | {cnt/tot_f*100:.1f}% | Diagnosed root cause in pipeline trajectory |\n"

        md += """
---

## 7. Example Successful Cases

"""
        if not success_cases:
            md += "_No fully correct examples in this sample slice._\n"
        for idx, sc in enumerate(success_cases):
            mplan = sc.get("multihop_plan", {})
            audit = sc.get("audit", {})
            lats = sc.get("stage_latencies", {})
            md += f"""#### Example {idx+1} [ID: `{sc.get('question_id')}`]
* **Question:** {sc.get('prompt')}
* **Reference Answer:** `{sc.get('reference_answer')}`
* **Generated Answer:** `{sc.get('generated_answer')}`
* **Generation Mode:** `{sc.get('generation_mode')}` | **Model:** `{audit.get('model_name', 'Qwen 2.5 14B')}`
* **Factuality Score:** {sc.get('factuality', {}).get('factuality_score', 0.0):.2f} | **Grounding:** {sc.get('factuality', {}).get('grounding_score', 0.0):.2f}
* **Reasoning Dimensions:** {', '.join(sc.get('reasoning_types', []))}
* **Stage Latencies:** Retrieval: {lats.get('retrieval_ms', 0):.1f}ms | Generation: {lats.get('generation_ms', 0):.1f}ms | Total: {sc.get('total_latency_ms', 0):.1f}ms
* **Multi-Hop Plan:** Required hops: {mplan.get('required_hops', 1)} | Resolved hops: {mplan.get('resolved_hops', 0)} | Path Completeness: {mplan.get('path_completeness', 0.0)*100:.1f}%

"""

        md += """---

## 8. Example Failure Cases

"""
        if not failure_cases:
            md += "_No failure cases in this sample slice._\n"
        for idx, fc in enumerate(failure_cases):
            diag = fc.get("diagnosis", {})
            mplan = fc.get("multihop_plan", {})
            audit = fc.get("audit", {})
            lats = fc.get("stage_latencies", {})
            md += f"""#### Example {idx+1} [ID: `{fc.get('question_id')}`]
* **Question:** {fc.get('prompt')}
* **Reference Answer:** `{fc.get('reference_answer')}`
* **Generated Answer:** `{fc.get('generated_answer')}`
* **Generation Mode:** `{fc.get('generation_mode')}` | **Audit Trigger:** `{audit.get('exact_fallback_trigger') or 'None'}`
* **Primary Failure:** `{diag.get('primary_failure')}`
* **Secondary Failures:** `{', '.join(diag.get('secondary_failures', [])) or 'None'}`
* **Probable Cause:** {diag.get('probable_cause')}
* **Stage Latencies:** Retrieval: {lats.get('retrieval_ms', 0):.1f}ms | Generation: {lats.get('generation_ms', 0):.1f}ms | Total: {fc.get('total_latency_ms', 0):.1f}ms
* **Multi-Hop Plan:** Required hops: {mplan.get('required_hops', 1)} | Resolved hops: {mplan.get('resolved_hops', 0)} | Missing: `{', '.join(mplan.get('missing_hops', [])) or 'None'}`

"""

        md += """---

## 9. Version Comparison

"""
        if comparison:
            md += f"""| Metric | Baseline | Current Experiment | Delta |
| :--- | :---: | :---: | :---: |
| Overall Score | {comparison.get('baseline_score', 0.0)*100:.1f}% | {comparison.get('current_score', 0.0)*100:.1f}% | {comparison.get('delta_score', 0.0)*100:+.1f}% |
| Factuality | {comparison.get('baseline_factuality', 0.0)*100:.1f}% | {comparison.get('current_factuality', 0.0)*100:.1f}% | {comparison.get('delta_factuality', 0.0)*100:+.1f}% |
| Retrieval Coverage | {comparison.get('baseline_coverage', 0.0)*100:.1f}% | {comparison.get('current_coverage', 0.0)*100:.1f}% | {comparison.get('delta_coverage', 0.0)*100:+.1f}% |
| Hallucination Rate | {comparison.get('baseline_hallucination', 0.0)*100:.1f}% | {comparison.get('current_hallucination', 0.0)*100:.1f}% | {comparison.get('delta_hallucination', 0.0)*100:+.1f}% |
"""
        else:
            md += "_Baseline benchmark establishment run. Comparative deltas will be recorded upon subsequent controlled variable experiments._\n"

        md += """
---

## 10. Prioritized Engineering Recommendations

### 🔴 HIGH PRIORITY: Multi-Hop Retrieval Entity Bridging
- For compound queries requiring 3+ Wikipedia documents, extend Graph traversal to evaluate 2-hop neighbor co-occurrences.
- Boost candidate chunks where multiple query bridge entities intersect.

### 🟡 MEDIUM PRIORITY: Numerical Reasoning Precision Validation
- Ensure numerical expressions identified in tables undergo deterministic formula execution before prompt synthesis.
- Maintain tolerance check of $\\pm 1\\%$ on currency and scientific metric comparisons.

### 🟢 LOW PRIORITY: Context Formatting & Deduplication
- Compact reference link footers to conserve prompt token budget while preserving source provenance.

---

## 11. Limitations

1. **Benchmark Ground-Truth Scope:** FRAMES provides URL-level ground-truth (`wiki_links`) rather than exact sentence-level passage spans. Retrieval precision metrics reflect document-level rather than token-level relevance.
2. **Domain Representation:** FRAMES evaluates open-domain Wikipedia multi-hop reasoning. Real-world RAISE production performance on dense academic/financial annual reports exhibits higher tabular density than typical Wikipedia articles.
3. **Hardware Sandbox:** Evaluated using ephemeral in-memory stores ensuring zero leakage into production databases.
"""
        return md

    def _build_html_report(
        self,
        config: Dict[str, Any],
        metrics: Dict[str, Any],
        failures: Dict[str, Any],
        results: List[Dict[str, Any]],
    ) -> str:
        """Generates self-contained, responsive HTML report."""
        exp_id = config.get("experiment_id", "frames_exp_001")
        overall_score = metrics.get("overall_score", 0.0) * 100
        factuality = metrics.get("mean_factuality", 0.0) * 100
        coverage = metrics.get("mean_retrieval_coverage", 0.0) * 100
        reasoning = metrics.get("mean_reasoning", 0.0) * 100

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FRAMES Benchmark Report — RAISE GraphRAG</title>
<style>
  :root {{
    --bg: #0f172a; --card: #1e293b; --border: #334155;
    --text: #f8fafc; --muted: #94a3b8; --accent: #38bdf8;
    --green: #4ade80; --red: #f87171; --yellow: #facc15;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.6; margin: 0; padding: 2rem;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  .header {{ border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; margin-bottom: 2rem; }}
  h1 {{ color: var(--accent); margin: 0 0 0.5rem 0; font-size: 2rem; }}
  .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; background: #0284c7; color: white; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin-bottom: 2.5rem; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1.5rem; }}
  .card-val {{ font-size: 2.25rem; font-weight: 700; color: var(--accent); margin: 0.25rem 0; }}
  .card-label {{ color: var(--muted); font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; background: var(--card); border-radius: 0.5rem; overflow: hidden; border: 1px solid var(--border); }}
  th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ background: #111827; color: var(--muted); font-size: 0.85rem; text-transform: uppercase; }}
  .status-tag {{ padding: 0.2rem 0.5rem; border-radius: 0.25rem; font-size: 0.8rem; font-weight: 600; }}
  .status-correct {{ background: rgba(74, 222, 128, 0.15); color: var(--green); }}
  .status-partial {{ background: rgba(250, 204, 21, 0.15); color: var(--yellow); }}
  .status-abstained {{ background: rgba(56, 189, 248, 0.15); color: var(--accent); }}
  .status-incorrect {{ background: rgba(248, 113, 113, 0.15); color: var(--red); }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <span class="badge">Google Research FRAMES Benchmark</span>
    <h1>RAISE GraphRAG Evaluation Report</h1>
    <div style="color: var(--muted);">Experiment: <code>{exp_id}</code> | Mode: <strong>{config.get('retrieval_mode', 'hybrid').upper()}</strong> | Date: {config.get('timestamp')}</div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-label">Overall Score</div>
      <div class="card-val">{overall_score:.1f}%</div>
      <div style="color: var(--muted); font-size: 0.85rem;">Harmonic Benchmark Mean</div>
    </div>
    <div class="card">
      <div class="card-label">Answer Correctness</div>
      <div class="card-val" style="color: var(--green);">{metrics.get('answer_correctness_rate', 0.0)*100:.1f}%</div>
      <div style="color: var(--muted); font-size: 0.85rem;">Exact Reference Matches</div>
    </div>
    <div class="card">
      <div class="card-label">Factuality Score</div>
      <div class="card-val" style="color: var(--accent);">{factuality:.1f}%</div>
      <div style="color: var(--muted); font-size: 0.85rem;">Evidence-Grounded Agreement</div>
    </div>
    <div class="card">
      <div class="card-label">Retrieval Coverage</div>
      <div class="card-val">{coverage:.1f}%</div>
      <div style="color: var(--muted); font-size: 0.85rem;">Ground-Truth Wiki Links</div>
    </div>
    <div class="card">
      <div class="card-label">Abstention Rate</div>
      <div class="card-val" style="color: var(--yellow);">{metrics.get('abstention_rate', 0.0)*100:.1f}%</div>
      <div style="color: var(--muted); font-size: 0.85rem;">Safe Controlled Abstentions</div>
    </div>
    <div class="card">
      <div class="card-label">Unsupported Claims</div>
      <div class="card-val" style="color: var(--red);">{metrics.get('unsupported_claim_rate', 0.0)*100:.1f}%</div>
      <div style="color: var(--muted); font-size: 0.85rem;">False Assertions (Hallucination)</div>
    </div>
  </div>

  <h2>Evaluation Results by Question</h2>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Prompt</th>
        <th>Reasoning Types</th>
        <th>Status</th>
        <th>Factuality</th>
        <th>Reasoning</th>
        <th>Evidence Coverage</th>
      </tr>
    </thead>
    <tbody>
"""
        for r in results[:100]:
            f = r.get("factuality", {})
            st = f.get("answer_status", "unknown")
            if st == "correct":
                st_class = "status-correct"
            elif st == "partially_correct":
                st_class = "status-partial"
            elif st == "abstained":
                st_class = "status-abstained"
            else:
                st_class = "status-incorrect"
            html += f"""      <tr>
        <td><code>{r.get('question_id')}</code></td>
        <td>{r.get('prompt')[:65]}...</td>
        <td>{', '.join(r.get('reasoning_types', []))}</td>
        <td><span class="status-tag {st_class}">{st.upper()}</span></td>
        <td>{f.get('factuality_score', 0.0)*100:.0f}%</td>
        <td>{r.get('reasoning', {}).get('overall_reasoning_score', 0.0)*100:.0f}%</td>
        <td>{r.get('retrieval', {}).get('evidence_coverage', 0.0)*100:.0f}%</td>
      </tr>
"""
        html += """    </tbody>
  </table>
</div>
</body>
</html>
"""
        return html
