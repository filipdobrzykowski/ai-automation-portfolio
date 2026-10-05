import csv
from collections import Counter
from pathlib import Path
import sys

path = Path(__file__).parent / "dataset" / (sys.argv[1] if len(sys.argv) > 1 else "labels.csv")
CATEGORIES = {"return_complaint", "order_status", "product_question",
              "invoice_payment", "partnership_spam", "other"}
PRIORITIES = {"high", "medium", "low"}

with open(path, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print("Rows:", len(rows))
bad = [r["id"] for r in rows
       if r["category"] not in CATEGORIES or r["priority"] not in PRIORITIES]
print("Rows with invalid label:", bad if bad else "none")
print("Category distribution:", dict(Counter(r["category"] for r in rows)))
print("Priority distribution:", dict(Counter(r["priority"] for r in rows)))