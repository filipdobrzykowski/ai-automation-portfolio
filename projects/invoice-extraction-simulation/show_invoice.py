import csv
import sys
from pathlib import Path

filename = sys.argv[1]
ids = set(sys.argv[2:])
path = Path(__file__).parent / "dataset" / filename
with open(path, encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        if not ids or row["id"] in ids:
            print("=" * 60, row["id"])
            print(row["text"])