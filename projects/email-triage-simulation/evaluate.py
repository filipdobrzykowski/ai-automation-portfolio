import csv
import json
import statistics
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

MODEL = "claude-haiku-4-5-20251001"
PROMPT_VERSION = "v1"

# Ceny w USD za 1M tokenów. To założenie, sprawdź aktualny cennik w dokumentacji Anthropic.
PRICE_IN_PER_M = 1.00
PRICE_OUT_PER_M = 5.00

BASE = Path(__file__).parent
EMAILS = BASE / "dataset" / "emails.csv"
LABELS = BASE / "dataset" / "labels.csv"
SCENARIO = BASE / "scenario.md"
RESULTS = BASE / "results"

CATEGORIES = ["return_complaint", "order_status", "product_question",
              "invoice_payment", "partnership_spam", "other"]
PRIORITIES = ["high", "medium", "low"]

SYSTEM = (
    "You are an email triage assistant for a small online shop.\n"
    "Classify each customer email using EXACTLY the definitions and rules below.\n\n"
    + SCENARIO.read_text(encoding="utf-8")
    + "\n\nReturn ONLY valid JSON, with no text before or after it, in this format:\n"
    '{"category": "...", "priority": "...", "order_number": "...", "summary": "..."}\n\n'
    "Constraints:\n"
    f"- category must be one of: {', '.join(CATEGORIES)}\n"
    f"- priority must be one of: {', '.join(PRIORITIES)}\n"
    '- order_number: the order number (format BG-12345) if present, otherwise "none"\n'
    "- summary: one sentence, max 15 words\n"
)


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def classify(text):
    last_error = None
    for attempt in range(3):
        try:
            start = time.perf_counter()
            response = client.messages.create(
                model=MODEL,
                max_tokens=300,
                system=SYSTEM,
                messages=[{"role": "user", "content": "Email:\n\n" + text}],
            )
            latency = time.perf_counter() - start
            return (response.content[0].text,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                    latency)
        except anthropic.APIError as e:
            last_error = e
            time.sleep(2 * (attempt + 1))
    raise last_error


def parse(raw):
    clean = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(clean)
        return data, isinstance(data, dict)
    except json.JSONDecodeError:
        return {}, False


def norm(value, default=""):
    if value is None:
        return default
    value = str(value).strip().lower()
    return value if value else default


def norm_order(value):
    value = norm(value, "none")
    return "none" if value in ("none", "null", "brak", "") else value.upper()


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def main():
    emails = {r["id"]: r["email"] for r in read_csv(EMAILS)}
    labels = read_csv(LABELS)
    missing = [r["id"] for r in labels if r["id"] not in emails]
    if missing:
        raise SystemExit(f"Etykiety bez maila o tym id: {missing}")

    rows = []
    total_in = total_out = 0
    for i, lab in enumerate(labels, start=1):
        raw, tok_in, tok_out, latency = classify(emails[lab["id"]])
        data, parse_ok = parse(raw)
        total_in += tok_in
        total_out += tok_out
        rows.append({
            "id": lab["id"],
            "true_category": norm(lab["category"]),
            "pred_category": norm(data.get("category")),
            "true_priority": norm(lab["priority"]),
            "pred_priority": norm(data.get("priority")),
            "true_order": norm_order(lab.get("order_number")),
            "pred_order": norm_order(data.get("order_number")),
            "hard": norm(lab.get("hard"), "n/a"),
            "summary": str(data.get("summary", "")).strip(),
            "parse_ok": parse_ok,
            "latency_s": round(latency, 2),
        })
        print(f"{i}/{len(labels)} {lab['id']}")

    n = len(rows)
    cat_ok = sum(r["true_category"] == r["pred_category"] for r in rows)
    pri_ok = sum(r["true_priority"] == r["pred_priority"] for r in rows)
    ord_ok = sum(r["true_order"] == r["pred_order"] for r in rows)
    parse_fail = sum(not r["parse_ok"] for r in rows)
    latencies = [r["latency_s"] for r in rows]
    cost = total_in * PRICE_IN_PER_M / 1e6 + total_out * PRICE_OUT_PER_M / 1e6

    print("\n=== RESULTS ===")
    print(f"Model: {MODEL} | prompt: {PROMPT_VERSION} | n = {n}")
    print(f"Category accuracy: {cat_ok}/{n} ({pct(cat_ok, n)})")
    print(f"Priority accuracy: {pri_ok}/{n} ({pct(pri_ok, n)})")
    print(f"Order number accuracy: {ord_ok}/{n} ({pct(ord_ok, n)})")
    print(f"Unparseable responses: {parse_fail}")

    hard_summary = {}
    if any(r["hard"] in ("yes", "no") for r in rows):
        print("\nBy difficulty:")
        for flag in ("no", "yes"):
            subset = [r for r in rows if r["hard"] == flag]
            c = sum(r["true_category"] == r["pred_category"] for r in subset)
            p = sum(r["true_priority"] == r["pred_priority"] for r in subset)
            name = "hard" if flag == "yes" else "easy"
            print(f"  {name} (n={len(subset)}): category {pct(c, len(subset))}, "
                  f"priority {pct(p, len(subset))}")
            hard_summary[name] = {"n": len(subset), "category_correct": c,
                                  "priority_correct": p}

    print("\nCategory confusion matrix (rows = true, columns = predicted):")
    cols = CATEGORIES + ["<invalid>"]
    print(" " * 20 + "".join(c[:9].ljust(11) for c in cols))
    for t in CATEGORIES:
        counts = Counter(r["pred_category"] if r["pred_category"] in CATEGORIES
                         else "<invalid>" for r in rows if r["true_category"] == t)
        print(t.ljust(20) + "".join(str(counts.get(c, 0)).ljust(11) for c in cols))

    print("\nCategory or priority errors:")
    for r in rows:
        if (r["true_category"] != r["pred_category"]
                or r["true_priority"] != r["pred_priority"]):
            print(f"  {r['id']}: category {r['true_category']} -> {r['pred_category']}"
                  f" | priority {r['true_priority']} -> {r['pred_priority']}")

    print("\nCost and time:")
    print(f"  Tokens in/out: {total_in}/{total_out}")
    print(f"  Cost for this run: ${cost:.4f} (prices assumed, verify)")
    print(f"  Cost per 1,000 emails: ${cost / n * 1000:.2f}")
    print(f"  Latency: mean {statistics.mean(latencies):.2f}s, "
          f"median {statistics.median(latencies):.2f}s")

    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pred_path = RESULTS / f"predictions_{PROMPT_VERSION}_{stamp}.csv"
    with open(pred_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    metrics = {
        "model": MODEL, "prompt_version": PROMPT_VERSION, "timestamp": stamp, "n": n,
        "category_correct": cat_ok, "priority_correct": pri_ok,
        "order_number_correct": ord_ok, "unparseable": parse_fail,
        "by_difficulty": hard_summary,
        "tokens_in": total_in, "tokens_out": total_out,
        "cost_usd_assumed_prices": round(cost, 5),
        "latency_mean_s": round(statistics.mean(latencies), 2),
    }
    (RESULTS / f"metrics_{PROMPT_VERSION}_{stamp}.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nZapisano: {pred_path.name}")


if __name__ == "__main__":
    main()