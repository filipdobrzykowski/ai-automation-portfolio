import csv
import sys
from pathlib import Path

from parity import EXTRACTION, post  # noqa: E402
from extract import field_matches  # noqa: E402
from validators import FIELDS  # noqa: E402


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


truth = read_csv(EXTRACTION / "dataset" / "truth_dev.csv")
texts = {r["id"]: r["text"] for r in read_csv(EXTRACTION / "dataset" / "invoices_dev.csv")}
review = [r for r in truth if r["expected_route"] == "review"]
auto = [r for r in truth if r["expected_route"] == "auto"][:7]
selected = review + auto

rows = []
for i, t in enumerate(selected, start=1):
    got = post({"id": t["id"], "invoice_text": texts[t["id"]]})
    if "_http_error" in got or "_not_json" in got:
        sys.exit(f"{t['id']}: unexpected response {got}")
    rec = got.get("record") or {}
    wrong = [f for f in FIELDS if not field_matches(f, rec.get(f), t[f])]
    rows.append({"id": t["id"], "kind": t["kind"], "detail": t["detail"],
                 "expected": t["expected_route"], "route": got.get("route"),
                 "failures": ";".join(got.get("failures") or []), "wrong": wrong,
                 "rec": rec, "truth": t})
    print(f"{i}/{len(selected)} {t['id']} route={got.get('route')}", flush=True)

n = len(rows)
route_ok = sum(r["route"] == r["expected"] for r in rows)
all_ok = sum(not r["wrong"] for r in rows)
silent = [r for r in rows if r["wrong"] and r["route"] == "auto"]
print("\n=== END-TO-END ===")
print(f"Selected: {len(review)} expected review + {len(auto)} expected auto = {n}")
print(f"Route accuracy: {route_ok}/{n}")
print(f"Invoice accuracy (all 9 fields): {all_ok}/{n}")
print(f"Silent errors: {len(silent)}")
print(f"Routed auto: {sum(r['route'] == 'auto' for r in rows)} | "
      f"routed review: {sum(r['route'] == 'review' for r in rows)}")
for r in rows:
    if r["wrong"] or r["route"] != r["expected"]:
        print(f"  {r['id']} [{r['kind']}/{r['detail'] or '-'}] route {r['route']} "
              f"(expected {r['expected']}), checks: {r['failures'] or '-'}")
        for f in r["wrong"]:
            print(f"      {f}: n8n {r['rec'].get(f)!r} | printed {r['truth'][f] or None!r}")