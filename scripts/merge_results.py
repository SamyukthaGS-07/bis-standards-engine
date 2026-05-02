"""
Merges your inference output with the public test set
to create a file the eval_script.py can evaluate.

Usage:
    python merge_results.py
"""
import json

# Load public test set (has expected_standards)
with open("data/public_test_set.json", encoding="utf-8") as f:
    test_set = json.load(f)

# Load your inference output (has retrieved_standards + latency)
with open("data/public_results.json", encoding="utf-8") as f:
    your_results = json.load(f)

# Build lookup by id
your_lookup = {r["id"]: r for r in your_results}

# Merge
merged = []
for item in test_set:
    qid = item["id"]
    your = your_lookup.get(qid, {})
    merged.append({
        "id": qid,
        "query": item.get("query", ""),
        "expected_standards": item.get("expected_standards", []),
        "retrieved_standards": your.get("retrieved_standards", []),
        "latency_seconds": your.get("latency_seconds", 0.0),
    })

with open("data/eval_ready.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)

print(f"Merged {len(merged)} results → data/eval_ready.json")
print("Now run: python eval_script.py --results data/eval_ready.json")
