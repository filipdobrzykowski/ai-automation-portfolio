import csv
import sys
from pathlib import Path

BASE = Path(__file__).parent
pred_file = sorted((BASE / "results").glob("predictions_v1_*.csv"))[-1]

with open(pred_file, encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
with open(BASE / "dataset" / "label_corrections.csv", encoding="utf-8-sig", newline="") as f:
    corrections = list(csv.DictReader(f))


def acc(field):
    ok = sum(r["true_" + field] == r["pred_" + field] for r in rows)
    return ok, len(rows)


before = {f: acc(f) for f in ("category", "priority")}

by_id = {r["id"]: r for r in rows}
for c in corrections:
    row = by_id[c["id"]]
    key = "true_" + c["field"]
    if row[key] != c["original"]:
        sys.exit(f"{c['id']}: expected {c['original']}, found {row[key]}")
    row[key] = c["corrected"]

after = {f: acc(f) for f in ("category", "priority")}

print(f"Predictions file: {pred_file.name}")
for f in ("category", "priority"):
    b, a = before[f], after[f]
    print(f"{f}: original labels {b[0]}/{b[1]} ({100*b[0]/b[1]:.1f}%)"
          f" -> after {len(corrections)} documented corrections {a[0]}/{a[1]} ({100*a[0]/a[1]:.1f}%)")