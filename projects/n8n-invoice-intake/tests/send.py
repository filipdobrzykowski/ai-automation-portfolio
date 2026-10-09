import csv
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
URL = os.environ["N8N_WEBHOOK_URL"]
KEY = os.environ["N8N_WEBHOOK_KEY"]
DEV = ROOT / "projects" / "invoice-extraction-simulation" / "dataset" / "invoices_dev.csv"


def post(payload):
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Api-Key": KEY},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status = r.status
            content_type = r.headers.get("Content-Type")
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode("utf-8")[:500]}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"_status": status, "_content_type": content_type, "_body": body[:500]}


if __name__ == "__main__":
    with open(DEV, encoding="utf-8-sig", newline="") as f:
        texts = {r["id"]: r["text"] for r in csv.DictReader(f)}
    for inv_id in sys.argv[1:]:
        result = post({"id": inv_id, "invoice_text": texts[inv_id]})
        print(inv_id, json.dumps(result, ensure_ascii=False, indent=2))