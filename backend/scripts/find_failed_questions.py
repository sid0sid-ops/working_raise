import json
from pathlib import Path
project_root = Path(__file__).resolve().parents[2]
ckpt = project_root / "Artifacts" / "benchmarks" / "frames" / "checkpoints" / "frames_hybrid_consolidated_824_checkpoint.jsonl"
records = []
with open(ckpt, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            records.append(rec)
        except Exception:
            continue

print(f"Loaded {len(records)} records from checkpoint.")

# Group by primary failure diagnosis
by_failure = {}
for r in records:
    diag = r.get("diagnosis", {}).get("primary_failure", "NONE")
    fact_score = r.get("factuality", {}).get("factuality_score", 0.0)
    if fact_score < 0.5:
        by_failure.setdefault(diag, []).append(r)

for diag, qs in by_failure.items():
    print(f"\nFailure Type: {diag} (Count: {len(qs)})")
    for q in qs[:2]:
        qid = q.get("question_id")
        ref = q.get("reference_answer")
        ans = q.get("generated_answer", "")[:80]
        prompt = q.get("prompt", "")[:120]
        print(f"  QID {qid}: Ref='{ref}' | Prev Ans='{ans}'")
        print(f"    Prompt: {prompt}...")

# Check specifically Q29, Q10, Q24, Q32, Q784
targets = ["29", "10", "24", "32", "784", "717", "724"]
print("\n=== TARGET QUESTIONS ===")
for r in records:
    if str(r.get("question_id")) in targets:
        qid = r.get("question_id")
        diag = r.get("diagnosis", {}).get("primary_failure", "NONE")
        score = r.get("factuality", {}).get("factuality_score", 0.0)
        print(f"\nQID {qid} | Score: {score} | Diag: {diag}")
        print(f"  Prompt: {r.get('prompt')}")
        print(f"  Reference: {r.get('reference_answer')}")
        print(f"  Prev Ans:  {r.get('generated_answer')}")
