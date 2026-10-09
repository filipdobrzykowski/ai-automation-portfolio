import csv
import glob
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
EXTRACTION = ROOT / "projects" / "invoice-extraction-simulation"
sys.path.insert(0, str(EXTRACTION))
load_dotenv(ROOT / ".env")

from extract import clean_record, parse_json  # noqa: E402
from validators import nip_check_digit, validate  # noqa: E402

for name in ("N8N_WEBHOOK_URL_PROD", "N8N_WEBHOOK_KEY"):
    if name not in os.environ:
        sys.exit(f"Missing {name} in .env")
URL = os.environ["N8N_WEBHOOK_URL_PROD"]
KEY = os.environ["N8N_WEBHOOK_KEY"]


def post(payload):
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Api-Key": KEY},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode("utf-8")[:300]}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"_not_json": body[:300]}


def expected(raw):
    data, ok = parse_json(raw)
    rec = clean_record(data)
    failures = validate(rec)
    route = "auto" if not failures else "review"
    if not ok:
        failures = ["parse_error"] + failures
    return {"parse_ok": ok, "record": rec, "failures": failures, "route": route}


def make_nip(first9):
    return first9 + str(nip_check_digit(first9))


N1, N2 = make_nip("526025099"), make_nip("111111111")
BASE = {"invoice_number": "FV/1", "issue_date": "2026-03-15",
        "seller_name": "Test Sp. z o.o.", "seller_nip": N1, "buyer_nip": N2,
        "net_amount": "100.00", "vat_rate": 23, "vat_amount": "23.00",
        "gross_amount": "123.00"}


def variant(**changes):
    d = dict(BASE)
    d.update(changes)
    return d


EDGE = {
    "edge_ok": json.dumps(BASE),
    "edge_rate_percent_sign": json.dumps(variant(vat_rate="23%")),
    "edge_rate_not_allowed": json.dumps(variant(vat_rate=22, vat_amount="22.00", gross_amount="122.00")),
    "edge_amount_format": json.dumps(variant(net_amount="abc")),
    "edge_date_out_of_range": json.dumps(variant(issue_date="2024-12-31")),
    "edge_date_invalid": json.dumps(variant(issue_date="2026-02-30")),
    "edge_bad_nip": json.dumps(variant(seller_nip=N1[:-1] + str((int(N1[-1]) + 1) % 10))),
    "edge_sum_mismatch": json.dumps(variant(gross_amount="125.00")),
    "edge_vat_mismatch": json.dumps(variant(vat_amount="20.00", gross_amount="120.00")),
    "edge_missing_field": json.dumps(variant(invoice_number=None)),
    "edge_rate_zero": json.dumps(variant(vat_rate=0, vat_amount="0.00", gross_amount="100.00")),
    "edge_numeric_types": json.dumps(variant(net_amount=100, vat_amount=23.0, gross_amount=123)),
    "edge_code_fence": "```json\n" + json.dumps(BASE) + "\n```",
    "edge_not_json": "Sorry, I cannot do that.",
    "edge_text_around_json": "Here is the JSON: " + json.dumps(BASE) + " Done.",
}


def compare(label, items):
    same, diffs = 0, []
    for inv_id, raw in items:
        exp = expected(raw)
        got = post({"id": inv_id, "raw_response": raw})
        if "_http_error" in got or "_not_json" in got:
            sys.exit(f"{inv_id}: unexpected response {got}")
        if {k: got.get(k) for k in exp} == exp:
            same += 1
        else:
            diffs.append((inv_id, exp, got))
    print(f"{label}: {same}/{len(items)} identical")
    for inv_id, exp, got in diffs:
        print(f"  DIFFERENT: {inv_id}")
        print(f"    python: failures={exp['failures']} route={exp['route']}")
        print(f"    n8n:    failures={got.get('failures')} route={got.get('route')}")
        for k in exp["record"]:
            if exp["record"][k] != (got.get("record") or {}).get(k):
                print(f"    record.{k}: python={exp['record'][k]!r} n8n={(got.get('record') or {}).get(k)!r}")
    return same, len(items)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        files = sorted(glob.glob(str(EXTRACTION / "results" / "predictions_v2_dev_*.csv")))
        if not files:
            sys.exit("No predictions_v2_dev file found.")
        path = files[-1]
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    print("=== PARITY ===")
    print(f"Stored predictions: {Path(path).name} ({len(rows)} invoices)")
    a, a_n = compare("Stored v2 predictions", [(r["id"], r["raw"]) for r in rows])
    b, b_n = compare("Edge cases", list(EDGE.items()))
    print(f"Total: {a + b}/{a_n + b_n} identical")