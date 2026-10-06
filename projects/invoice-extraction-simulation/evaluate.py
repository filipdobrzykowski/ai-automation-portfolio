import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from extract import field_matches
from validators import FIELDS

BASE = Path(__file__).parent


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=["dev", "test"], default="dev")
    parser.add_argument("--prompt", default="v1")
    parser.add_argument("--file", default="")
    args = parser.parse_args()

    results_dir = BASE / "results"
    if args.file:
        pred_path = Path(args.file)
    else:
        files = sorted(results_dir.glob(f"predictions_{args.prompt}_{args.set}_*.csv"))
        if not files:
            sys.exit("No predictions file found.")
        pred_path = files[-1]

    truth = {r["id"]: r for r in read_csv(BASE / "dataset" / f"truth_{args.set}.csv")}
    preds = {r["id"]: r for r in read_csv(pred_path)}
    if set(preds) != set(truth):
        sys.exit(f"{pred_path.name} has {len(preds)} invoices, the ground truth has "
                 f"{len(truth)}. Use --file with the file from the full run.")

    records = []
    field_ok = Counter()
    for inv_id, t in truth.items():
        p = preds[inv_id]
        wrong = [f for f in FIELDS if not field_matches(f, p.get(f"pred_{f}"), t[f])]
        for f in FIELDS:
            if f not in wrong:
                field_ok[f] += 1
        records.append({"id": inv_id, "kind": t["kind"], "detail": t["detail"],
                        "expected": t["expected_route"], "route": p["route"],
                        "failures": p["failures"], "wrong": wrong,
                        "pred": p, "truth": t, "parse_ok": p["parse_ok"]})

    n = len(records)
    all_ok = [r for r in records if not r["wrong"]]
    route_ok = [r for r in records if r["route"] == r["expected"]]
    ext_err = [r for r in records if r["wrong"]]
    caught = [r for r in ext_err if r["route"] == "review"]
    silent = [r for r in ext_err if r["route"] == "auto"]
    clean_docs_ok = [r for r in records if r["expected"] == "auto" and not r["wrong"]]
    needless = [r for r in clean_docs_ok if r["route"] == "review"]
    bad_docs = [r for r in records if r["expected"] == "review"]
    bad_docs_caught = [r for r in bad_docs if r["route"] == "review"]
    parse_fail = sum(r["parse_ok"] == "no" for r in records)

    print("=== EVALUATION ===")
    print(f"Predictions: {pred_path.name} | prompt: {args.prompt} | set: {args.set} | n = {n}")
    print("\nField accuracy:")
    for f in FIELDS:
        print(f"  {f.ljust(15)} {field_ok[f]}/{n} ({pct(field_ok[f], n)})")
    print(f"\nInvoice accuracy (all 9 fields correct): {len(all_ok)}/{n} ({pct(len(all_ok), n)})")
    print(f"Route accuracy: {len(route_ok)}/{n} ({pct(len(route_ok), n)})")
    print(f"Unparseable responses: {parse_fail}")

    print(f"\nInvoices with at least one wrong field: {len(ext_err)}")
    print(f"  caught by checks (routed review): {len(caught)}")
    print(f"  SILENT ERRORS (routed auto): {len(silent)}/{n} ({pct(len(silent), n)})")
    print(f"Needless reviews (all fields correct, document correct, routed review): "
          f"{len(needless)}/{len(clean_docs_ok)}")
    print(f"Documents with an injected error or missing field routed review: "
          f"{len(bad_docs_caught)}/{len(bad_docs)}")

    print("\nBy kind:")
    by_kind = defaultdict(list)
    for r in records:
        by_kind[r["kind"]].append(r)
    for kind, rs in by_kind.items():
        ok = sum(not r["wrong"] for r in rs)
        rt = sum(r["route"] == r["expected"] for r in rs)
        sl = sum(1 for r in rs if r["wrong"] and r["route"] == "auto")
        print(f"  {kind.ljust(10)} n={len(rs)} invoice accuracy {pct(ok, len(rs))}, "
              f"route accuracy {pct(rt, len(rs))}, silent errors {sl}")

    print("\nDetails (invoices with a wrong field or a wrong route):")
    for r in records:
        if r["wrong"] or r["route"] != r["expected"]:
            print(f"  {r['id']} [{r['kind']}/{r['detail'] or '-'}] "
                  f"route {r['route']} (expected {r['expected']}), checks: {r['failures'] or '-'}")
            for f in r["wrong"]:
                print(f"      {f}: predicted {r['pred'].get('pred_' + f) or 'null'!r}"
                      f" | printed {r['truth'][f] or 'null'!r}")

    metrics = {"predictions": pred_path.name, "prompt": args.prompt, "set": args.set,
               "n": n, "field_correct": dict(field_ok), "invoice_correct": len(all_ok),
               "route_correct": len(route_ok), "wrong_field_invoices": len(ext_err),
               "caught": len(caught), "silent_errors": len(silent),
               "needless_reviews": len(needless),
               "clean_documents_all_correct": len(clean_docs_ok),
               "bad_documents": len(bad_docs), "bad_documents_caught": len(bad_docs_caught),
               "unparseable": parse_fail}
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = results_dir / f"eval_{args.prompt}_{args.set}_{stamp}.json"
    out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nSaved: {out.name}")


if __name__ == "__main__":
    main()