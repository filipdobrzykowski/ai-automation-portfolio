import csv
from pathlib import Path

BASE = Path(__file__).parent

with open(BASE / "dataset" / "emails.csv", encoding="utf-8-sig", newline="") as f:
    emails = {r["id"]: r["email"] for r in csv.DictReader(f)}

pred_file = sorted((BASE / "results").glob("predictions_v1_*.csv"))[-1]
with open(pred_file, encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

for r in rows:
    if (r["true_category"] != r["pred_category"]
            or r["true_priority"] != r["pred_priority"]):
        print("=" * 70)
        print(r["id"], "| category:", r["true_category"], "->", r["pred_category"],
              "| priority:", r["true_priority"], "->", r["pred_priority"])
        print(emails[r["id"]])
        print("model summary:", r["summary"])