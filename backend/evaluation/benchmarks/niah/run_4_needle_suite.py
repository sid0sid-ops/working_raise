import sys
import time
import json
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.benchmarks.niah.niah_runner import NIAHBenchmarkRunner
from evaluation.benchmarks.niah.needle_catalog import list_available_needles, get_needle
from evaluation.benchmarks.niah.visualizer import NIAHVisualizer

def run_suite():
    runner = NIAHBenchmarkRunner()
    needles = list_available_needles()
    depths = [0.0, 0.50, 1.00]
    sizes = [1000, 5000]
    top_k = 4

    print("=" * 78)
    print(" 🏆 RAISE GRAPHRAG — COMPLETE 4-NEEDLE NIAH BENCHMARK SUITE")
    print(f" Target Needles: {len(needles)} ({needles})")
    print(f" Grid: {len(depths)} depths x {len(sizes)} sizes = {len(depths)*len(sizes)} cells per needle")
    print(f" Production Retrieval Budget: Top-K = {top_k}")
    print("=" * 78)

    all_results = {}
    suite_start = time.time()

    for idx, nid in enumerate(needles, 1):
        print(f"\n[{idx}/{len(needles)}] Testing Needle: '{nid}'")
        needle_case = get_needle(nid)
        print(f"     Description: {needle_case.description}")
        t0 = time.time()
        res = runner.run_sweep(
            needle_id=nid,
            depths=depths,
            context_sizes=sizes,
            chunk_size=450,
            chunk_overlap=0.0,
            top_k=top_k,
            test_llm=False,
        )
        elapsed = time.time() - t0
        all_results[nid] = res
        print(f"     Completed {len(res)} tests in {elapsed:.2f}s")

    total_duration = time.time() - suite_start

    print("\n" + "=" * 90)
    print(" 📊 SCIENTIFIC MULTI-METRIC SCORECARD (RECALL@1, RECALL@4, MRR, RANK DISTRIBUTION)")
    print("=" * 90)
    print(f" {'NEEDLE ID':<26} | {'TOP-1 (R@1)':<11} | {'RECALL@4':<9} | {'MRR':<6} | {'MEAN RANK':<9} | {'WORST':<5} | {'DECISION'}")
    print(" " + "-" * 90)

    global_total = 0
    global_top1 = 0
    global_top4 = 0
    global_mrrs = []
    global_latencies = []

    suite_metrics = {}

    for nid, res_list in all_results.items():
        ncase = get_needle(nid)
        total = len(res_list)
        global_total += total

        top1_cnt = sum(1 for r in res_list if r.get('top_1_hit'))
        top4_cnt = sum(1 for r in res_list if r.get('top_k_recall'))
        global_top1 += top1_cnt
        global_top4 += top4_cnt

        r1_pct = (top1_cnt / total) * 100
        r4_pct = (top4_cnt / total) * 100

        mrr_vals = [r.get('reciprocal_rank', 0.0) for r in res_list]
        mrr = sum(mrr_vals) / total if total else 0.0
        global_mrrs.extend(mrr_vals)

        ranks = [r['gold_rank'] for r in res_list if r.get('gold_rank') is not None]
        avg_rank = (sum(ranks) / len(ranks)) if ranks else float('nan')
        worst_rank = max(ranks) if ranks else 999

        # Latency metrics
        cell_lats = [r.get('latency_breakdown', {}).get('total_ms', 0.0) for r in res_list]
        avg_cell_ms = sum(cell_lats) / len(cell_lats) if cell_lats else 0.0
        global_latencies.extend(cell_lats)

        # Scientific Decision Logic
        if top1_cnt == total:
            decision = "✓ PASS (Optimal)"
        elif top4_cnt == total:
            decision = f"⚠️ PARTIAL (Distractor Stressed: {top1_cnt}/{total} R@1)"
        else:
            decision = f"❌ FAIL ({top4_cnt}/{total} R@4)"

        suite_metrics[nid] = {
            "type": ncase.needle_type.value,
            "top1_cnt": top1_cnt,
            "top4_cnt": top4_cnt,
            "total": total,
            "r1_pct": r1_pct,
            "r4_pct": r4_pct,
            "mrr": mrr,
            "avg_rank": avg_rank,
            "worst_rank": worst_rank,
            "decision": decision,
            "avg_cell_ms": avg_cell_ms,
        }

        print(f" {nid:<26} | {r1_pct:>9.1f}% | {r4_pct:>7.1f}% | {mrr:.3f} | #{avg_rank:<8.2f} | #{worst_rank:<4} | {decision}")

    overall_r1 = (global_top1 / global_total) * 100 if global_total else 0.0
    overall_r4 = (global_top4 / global_total) * 100 if global_total else 0.0
    overall_mrr = sum(global_mrrs) / len(global_mrrs) if global_mrrs else 0.0
    overall_cell_ms = sum(global_latencies) / len(global_latencies) if global_latencies else 0.0

    print(" " + "-" * 90)
    print(f" {'OVERALL SUITE BENCHMARK':<26} | {overall_r1:>9.1f}% | {overall_r4:>7.1f}% | {overall_mrr:.3f} | {global_top1}/{global_total} R@1 | {global_top4}/{global_total} R@4 | {'24 Cells Complete'}")
    print("=" * 90)

    # Export unified suite report
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_dir = PROJECT_ROOT / 'evaluation' / 'reports' / 'niah'
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f'niah_4_needle_suite_{ts}.md'

    md_lines = [
        '# 🏆 RAISE NIAH 4-Needle Benchmark Suite Report (Scientific Audit)',
        f'**Executed At**: `{datetime.now().isoformat()}`  ',
        f'**Total Experimental Cells**: `{global_total}`  ',
        f'**Top-1 Accuracy (Recall@1)**: `{global_top1}/{global_total}` (`{overall_r1:.1f}%`)  ',
        f'**Top-4 Retrieval Recall**: `{global_top4}/{global_total}` (`{overall_r4:.1f}%`)  ',
        f'**Mean Reciprocal Rank (MRR)**: `{overall_mrr:.4f}`  ',
        f'**Total Suite Execution Time**: `{total_duration:.2f}s` (Average `{overall_cell_ms/1000:.2f}s`/cell)  ',
        '',
        '---',
        '',
        '## 📊 Executive Scorecard',
        '',
        '| Needle ID | Needle Type | Top-1 Accuracy (R@1) | Recall@4 | MRR | Mean Rank | Worst Rank | System Decision |',
        '| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |',
    ]

    for nid, m in suite_metrics.items():
        md_lines.append(
            f"| `{nid}` | `{m['type']}` | **{m['r1_pct']:.1f}%** ({m['top1_cnt']}/{m['total']}) | **{m['r4_pct']:.1f}%** ({m['top4_cnt']}/{m['total']}) | {m['mrr']:.3f} | #{m['avg_rank']:.2f} | #{m['worst_rank']} | {m['decision']} |"
        )

    md_lines.extend([
        '',
        '---',
        '',
        '## ⏱️ Component Latency Breakdown',
        '> Note: Latency is dominated by CPU-based transformer embedding computation (`BAAI/bge-large-en-v1.5`) across 50 distractors per cell and CrossEncoder reranking (`ms-marco-MiniLM-L-6-v2`), not ChromaDB vector index lookup.',
        '',
        '| Needle ID | Corpus Build | Dense Embed (50 Distractors) | ChromaDB Query | Cross-Encoder Rerank | Total Per Cell |',
        '| :--- | :---: | :---: | :---: | :---: | :---: |',
    ])

    for nid, res_list in all_results.items():
        avg_corpus = sum(r.get('latency_breakdown', {}).get('corpus_build_ms', 0) for r in res_list) / len(res_list)
        avg_emb = sum(r.get('latency_breakdown', {}).get('embedding_probe_ms', 0) for r in res_list) / len(res_list)
        avg_chr = sum(r.get('latency_breakdown', {}).get('chromadb_retrieval_ms', 0) for r in res_list) / len(res_list)
        avg_rerank = sum(r.get('latency_breakdown', {}).get('reranker_ms', 0) for r in res_list) / len(res_list)
        avg_tot = sum(r.get('latency_breakdown', {}).get('total_ms', 0) for r in res_list) / len(res_list)
        md_lines.append(
            f"| `{nid}` | {avg_corpus:.1f}ms | {avg_emb:.1f}ms | {avg_chr:.1f}ms | {avg_rerank:.1f}ms | **{avg_tot/1000:.2f}s** |"
        )

    md_lines.extend([
        '',
        '---',
        '',
        '## 🗺️ Per-Needle 2D Retrieval Heatmaps',
        ''
    ])

    for nid, res_list in all_results.items():
        ncase = get_needle(nid)
        md_lines.append(f'### Needle: `{nid}` ({ncase.needle_type.value})')
        md_lines.append(f'> {ncase.description}')
        md_lines.append('')
        hmap = NIAHVisualizer.render_markdown_heatmap(
            results=res_list,
            depths=depths,
            context_sizes=sizes,
        )
        md_lines.append(hmap)
        md_lines.append('')

    report_file.write_text('\n'.join(md_lines), encoding='utf-8')
    print(f"\n📄 Saved Scientific Benchmark Report: {report_file}")

if __name__ == '__main__':
    run_suite()
