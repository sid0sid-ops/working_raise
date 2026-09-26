import sys
import json
from pathlib import Path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
from evaluation.metrics.qa_metrics import compute_exact_match, compute_token_f1

dataset_path = Path(r"C:\Users\Siddharth Tripathi\Downloads\diagnostic_benchmark_dataset.json")
with open(dataset_path, "r", encoding="utf-8") as f:
    data = json.load(f)

by_tier = {}
overall_f1 = []
overall_em = []
overall_faith = []

for d in data:
    tier = d.get("query_classification", "Unknown")
    if tier not in by_tier:
        by_tier[tier] = {"f1": [], "em": [], "lat": [], "faith": []}
    gold = d.get("gold_answer", "")
    gen = d.get("generated_answer", "")
    em = 1.0 if compute_exact_match(gen, gold) else 0.0
    _, _, f1 = compute_token_f1(gen, gold)
    lat = d.get("latency_by_stage", {}).get("total_ms", 0.0) / 1000.0
    faith = d.get("verification_result", {}).get("report", {}).get("faithfulness", 1.0)
    
    by_tier[tier]["f1"].append(f1)
    by_tier[tier]["em"].append(em)
    by_tier[tier]["lat"].append(lat)
    by_tier[tier]["faith"].append(faith)

    overall_f1.append(f1)
    overall_em.append(em)
    overall_faith.append(faith)

print("=" * 70)
print(f"{'Tier':<10} | {'Questions':<10} | {'Token F1':<10} | {'Faithfulness':<12} | {'Avg Latency (s)':<15}")
print("-" * 70)
for t in sorted(by_tier.keys()):
    vals = by_tier[t]
    n = len(vals["f1"])
    avg_f1 = sum(vals["f1"]) / n
    avg_faith = sum(vals["faith"]) / n
    avg_lat = sum(vals["lat"]) / n
    print(f"{t:<10} | {n:<10} | {avg_f1:<10.4f} | {avg_faith:<12.4f} | {avg_lat:<15.2f}")
print("=" * 70)
n_all = len(overall_f1)
print(f"{'OVERALL':<10} | {n_all:<10} | {sum(overall_f1)/n_all:<10.4f} | {sum(overall_faith)/n_all:<12.4f} | {sum([sum(v['lat']) for v in by_tier.values()])/n_all:<15.2f}")
