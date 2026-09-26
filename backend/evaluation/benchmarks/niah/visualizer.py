"""
RAISE NIAH Benchmark — 2D Matrix Visualizer & Report Generator
Generates:
  - 2D Depth vs Context Length Markdown heatmaps
  - ASCII terminal visualizer matrices
  - Comprehensive scientific diagnostic evaluation reports
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class NIAHVisualizer:
    """
    Renders 2D retrieval heatmaps and exports structured evaluation reports.
    """

    STAGE_EMOJIS = {
        "SUCCESS": "🟩 PASS",
        "ADVERSARIAL_RANKING_DEMOTION": "🟨 STRESSED",
        "RETRIEVAL_FAILURE": "🟥 RETR",
        "RERANKING_FAILURE": "🟨 RANK",
        "EMBEDDING_REPRESENTATION_FAILURE": "🟦 EMBED",
        "GRAPH_TRAVERSAL_FAILURE": "🟪 GRAPH",
        "CONTEXT_ASSEMBLY_FAILURE": "🟧 CTX",
        "GENERATION_FAILURE": "🟫 GEN",
    }

    @classmethod
    def render_markdown_heatmap(
        cls,
        results: List[Dict[str, Any]],
        depths: List[float],
        context_sizes: List[int],
    ) -> str:
        """
        Generates a 2D Markdown table of Needle Depth (%) vs Context Length (words/tokens).
        """
        # Build lookup table: (depth, size) -> result
        matrix: Dict[float, Dict[int, Dict[str, Any]]] = {}
        for r in results:
            d = round(float(r.get("depth_requested", r.get("depth", 0.0))), 2)
            s = int(r.get("target_words", r.get("corpus_size", 0)))
            matrix.setdefault(d, {})[s] = r

        headers = ["Depth (%)"] + [f"{s:,} words" for s in context_sizes]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]

        for d in depths:
            row_label = f"**{int(d * 100)}%**"
            cells = [row_label]
            for s in context_sizes:
                res = matrix.get(round(d, 2), {}).get(s)
                if not res:
                    cells.append("⬜ N/A")
                else:
                    stage = res.get("failure_stage", "SUCCESS" if res.get("success") else "RETRIEVAL_FAILURE")
                    emoji_label = cls.STAGE_EMOJIS.get(stage, "❓ UNK")
                    rank = res.get("gold_rank")
                    rank_str = f" (r={rank})" if rank else ""
                    cells.append(f"{emoji_label}{rank_str}")
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)

    @classmethod
    def render_ascii_matrix(
        cls,
        results: List[Dict[str, Any]],
        depths: List[float],
        context_sizes: List[int],
    ) -> str:
        """
        Renders clean ASCII table suitable for console output.
        """
        matrix: Dict[float, Dict[int, str]] = {}
        for r in results:
            d = round(float(r.get("depth_requested", r.get("depth", 0.0))), 2)
            s = int(r.get("target_words", r.get("corpus_size", 0)))
            stage = r.get("failure_stage", "SUCCESS" if r.get("success") else "RETRIEVAL_FAILURE")
            code = "PASS" if stage == "SUCCESS" else stage[:4]
            matrix.setdefault(d, {})[s] = code

        col_w = 12
        header_row = f"{'Depth':<10}" + "".join(f"{f'{s}w':>{col_w}}" for s in context_sizes)
        divider = "-" * len(header_row)

        rows = [divider, header_row, divider]
        for d in depths:
            row_str = f"{f'{int(d*100)}%':<10}"
            for s in context_sizes:
                val = matrix.get(round(d, 2), {}).get(s, "N/A")
                row_str += f"{val:>{col_w}}"
            rows.append(row_str)
        rows.append(divider)
        return "\n".join(rows)

    @classmethod
    def export_report(
        cls,
        results: List[Dict[str, Any]],
        output_dir: Optional[Path | str] = None,
        experiment_name: str = "niah_standard_sweep",
    ) -> Dict[str, Path]:
        """
        Writes comprehensive JSON and Markdown reports to evaluation/reports/niah/.
        """
        out_path = Path(output_dir or Path(__file__).resolve().parent.parent.parent / "reports" / "niah")
        out_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = out_path / f"{experiment_name}_{timestamp}.json"
        md_file = out_path / f"{experiment_name}_{timestamp}.md"

        # 1. Export JSON raw telemetry
        json_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

        # Extract unique depths and sizes
        depths = sorted(list({round(float(r.get("depth_requested", r.get("depth", 0.0))), 2) for r in results}))
        sizes = sorted(list({int(r.get("target_words", r.get("corpus_size", 0))) for r in results}))

        heatmap_md = cls.render_markdown_heatmap(results, depths=depths, context_sizes=sizes)

        # Compute summary metrics
        total = len(results)
        passed = sum(1 for r in results if r.get("success", False))
        retrieval_passed = sum(1 for r in results if r.get("top_k_recall", False))
        pass_rate = (passed / total * 100) if total else 0.0
        retrieval_rate = (retrieval_passed / total * 100) if total else 0.0

        stage_counts = {}
        for r in results:
            st = r.get("failure_stage", "SUCCESS" if r.get("success") else "RETRIEVAL_FAILURE")
            stage_counts[st] = stage_counts.get(st, 0) + 1

        md_content = f"""# 🔬 RAISE NIAH Benchmark Evaluation Report
**Experiment**: `{experiment_name}`  
**Executed At**: `{datetime.now().isoformat()}`  
**Total Tests**: `{total}` | **End-to-End Passed**: `{passed}/{total}` (`{pass_rate:.1f}%`) | **Retrieval Recall**: `{retrieval_passed}/{total}` (`{retrieval_rate:.1f}%`)

---

## 🗺️ 2D Retrieval Robustness Heatmap (Depth vs Context Length)

{heatmap_md}

**Legend**:
* `🟩 PASS` : Needle successfully retrieved and verified in generated answer.
* `🟥 RETR` : Retrieval Failure (Needle missing from vector top-k candidates).
* `🟨 RANK` : Reranker Failure (Needle demoted outside top candidates by Cross-Encoder).
* `🟦 EMBED`: Embedding Failure (Distractor paragraphs had higher cosine similarity than the needle).
* `🟪 GRAPH`: Knowledge Graph Failure (Multi-hop relational path not found in Neo4j / NetworkX).
* `🟧 CTX`  : Context Budget Failure (Needle retrieved but truncated during prompt assembly).
* `🟫 GEN`  : Generation Failure (Needle in context, but LLM failed to extract or refused).

---

## 📊 Diagnostic Failure Breakdown

| Failure Stage | Count | Percentage |
| :--- | :--- | :--- |
"""
        for stage, count in sorted(stage_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total else 0.0
            md_content += f"| `{stage}` | {count} | {pct:.1f}% |\n"

        md_content += "\n---\n\n## 📝 Detailed Test Execution Log\n\n"
        for idx, r in enumerate(results, start=1):
            md_content += (
                f"### Test #{idx}: Needle `{r.get('needle_id')}` | Depth {r.get('depth_requested')} | Size {r.get('target_words')}w\n"
                f"- **Status**: `{r.get('failure_stage', 'SUCCESS')}`\n"
                f"- **Top-K Recall**: `{r.get('top_k_recall')}` (Gold Rank: `{r.get('gold_rank')}`, Sim: `{r.get('gold_similarity')}`)\n"
                f"- **Query**: \"{r.get('query')}\"\n"
                f"- **Expected Answer**: `{r.get('expected_answer')}`\n"
                f"- **Root Cause**: {r.get('root_cause', 'N/A')}\n\n"
            )

        md_file.write_text(md_content, encoding="utf-8")

        return {"json": json_file, "markdown": md_file}
