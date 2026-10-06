import argparse
import csv
import json
import statistics
import sys
import time
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from validators import FIELDS, to_decimal, validate

MODEL = "claude-haiku-4-5-20251001"
# Assumed prices in USD per 1M tokens. Verify against the current price list.
PRICE_IN_PER_M = 1.00
PRICE_OUT_PER_M = 5.00

BASE = Path(__file__).parent
AMOUNT_FIELDS = ("net_amount", "vat_amount", "gross_amount")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_prompt(version):
    return (BASE / "prompts" / f"{version}.txt").read_text(encoding="utf-8")


def call_model(client, system, text):
    last_error = None
    for attempt in range(3):
        try:
            start = time.perf_counter()
            response = client.messages.create(
                model=MODEL,
                max_tokens=400,
                system=system,
                messages=[{"role": "user", "content": "Invoice text:\n\n" + text}],
            )
            latency = time.perf_counter() - start
            return (response.content[0].text, response.usage.input_tokens,
                    response.usage.output_tokens, latency)
        except anthropic.APIError as e:
            last_error = e
            time.sleep(2 * (attempt + 1))
    raise last_error


def parse_json(raw):
    clean = raw.replace("```json", "").replace("```", "").strip()
    for candidate in (clean, clean[clean.find("{"):clean.rfind("}") + 1]):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data, True
    return {}, False


def clean_value(field, value):
    """Type clean-up only: it never repairs the content of a value."""
    if value is None or isinstance(value, (dict, list)):
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        if field in AMOUNT_FIELDS:
            return str(Decimal(str(value)).quantize(Decimal("0.01")))
        if field == "vat_rate" and float(value).is_integer():
            return int(value)
        return str(value)
    value = str(value).strip()
    return None if value.lower() in ("", "null", "none") else value


def clean_record(data):
    return {f: clean_value(f, data.get(f)) for f in FIELDS}


def route_for(rec):
    failures = validate(rec)
    return ("auto" if not failures else "review"), failures


def field_matches(field, pred, truth):
    """truth comes from the ground-truth CSV, where an empty string means null."""
    t = None if truth in ("", None) else str(truth).strip()
    p = None if pred in ("", None) else str(pred).strip()
    if t is None or p is None:
        return t is None and p is None
    if field in AMOUNT_FIELDS:
        a, b = to_decimal(p), to_decimal(t)
        return a is not None and b is not None and a == b
    return p == t


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=["dev", "test"], default="dev")
    parser.add_argument("--prompt", default="v1")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    results_dir = BASE / "results"
    if args.set == "test":
        if args.limit:
            sys.exit("--limit is not allowed on the test set.")
        if list(results_dir.glob(f"predictions_{args.prompt}_test_*.csv")):
            sys.exit(f"Prompt {args.prompt} was already evaluated on the test set. Refusing to run it again.")

    inv_path = BASE / "dataset" / f"invoices_{args.set}.csv"
    truth_path = BASE / "dataset" / f"truth_{args.set}.csv"
    if not inv_path.exists():
        sys.exit(f"Missing file: {inv_path.name}")
    invoices = read_csv(inv_path)
    if args.limit:
        invoices = invoices[:args.limit]
    truth = {r["id"]: r for r in read_csv(truth_path)} if truth_path.exists() else {}

    load_dotenv()
    client = anthropic.Anthropic()
    system = load_prompt(args.prompt)

    rows = []
    tok_in = tok_out = 0
    for i, inv in enumerate(invoices, start=1):
        raw, t_in, t_out, latency = call_model(client, system, inv["text"])
        data, parse_ok = parse_json(raw)
        rec = clean_record(data)
        route, failures = route_for(rec)
        if not parse_ok:
            failures = ["parse_error"] + failures
        tok_in += t_in
        tok_out += t_out

        row = {"id": inv["id"], "route": route, "failures": ";".join(failures),
               "parse_ok": "yes" if parse_ok else "no", "tokens_in": t_in,
               "tokens_out": t_out, "latency_s": round(latency, 2), "raw": raw}
        row.update({f"pred_{f}": ("" if rec[f] is None else rec[f]) for f in FIELDS})
        rows.append(row)

        line = (f"{i}/{len(invoices)} {inv['id']} route={route} "
                f"checks={','.join(failures) or '-'}")
        t = truth.get(inv["id"])
        if t:
            ok = sum(field_matches(f, rec[f], t[f]) for f in FIELDS)
            line += f" fields={ok}/{len(FIELDS)}"
        print(line)

    n = len(rows)
    cost = tok_in * PRICE_IN_PER_M / 1e6 + tok_out * PRICE_OUT_PER_M / 1e6
    latencies = [r["latency_s"] for r in rows]
    print("\n=== RUN SUMMARY ===")
    print(f"Model: {MODEL} | prompt: {args.prompt} | set: {args.set} | n = {n}")
    print("Routes:", dict(Counter(r["route"] for r in rows)))
    print("Unparseable responses:", sum(r["parse_ok"] == "no" for r in rows))
    print(f"Tokens in/out: {tok_in}/{tok_out}")
    print(f"Cost for this run: ${cost:.4f} (prices assumed, verify)")
    print(f"Cost per 1,000 invoices: ${cost / n * 1000:.2f}")
    print(f"Latency: mean {statistics.mean(latencies):.2f}s, "
          f"median {statistics.median(latencies):.2f}s")

    results_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = results_dir / f"predictions_{args.prompt}_{args.set}_{stamp}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved: {out.name}")


if __name__ == "__main__":
    main()