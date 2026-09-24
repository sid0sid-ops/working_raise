import json
from pathlib import Path
project_root = Path(__file__).resolve().parents[2]
ckpt = project_root / "Artifacts" / "benchmarks" / "frames" / "checkpoints" / "frames_hybrid_consolidated_824_checkpoint.jsonl"
insufficient_qs = []
with open(ckpt, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        ans = rec.get("generated_answer", "")
        if "INSUFFICIENT REASONING PATH" in ans:
            insufficient_qs.append({
                "qid": rec.get("question_id"),
                "prompt": rec.get("prompt", ""),
                "ref": rec.get("reference_answer", ""),
                "diag": rec.get("diagnosis", {}).get("primary_failure"),
                "trigger": rec.get("audit", {}).get("exact_fallback_trigger"),
                "reasoning_types": rec.get("reasoning_types", []),
                "wiki_links": rec.get("wiki_links", [])
            })

print(f"Total INSUFFICIENT REASONING PATH questions: {len(insufficient_qs)}")

# Group by trigger
by_trigger = {}
for q in insufficient_qs:
    by_trigger.setdefault(q["trigger"], []).append(q)

print("\nBreakdown by trigger:")
for trig, qs in by_trigger.items():
    print(f"  {trig}: {len(qs)}")
    for q in qs[:3]:
        print(f"    [QID {q['qid']}] Ref='{q['ref']}' | Prompt='{q['prompt'][:85]}...'")
