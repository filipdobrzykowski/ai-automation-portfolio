from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

FIELDS = ["invoice_number", "issue_date", "seller_name", "seller_nip",
          "buyer_nip", "net_amount", "vat_rate", "vat_amount", "gross_amount"]
VAT_RATES = {23, 8, 5, 0}
WEIGHTS = [6, 5, 7, 2, 3, 4, 5, 6, 7]
DATE_MIN = date(2025, 1, 1)
DATE_MAX = date(2026, 12, 31)
TOL = Decimal("0.01")


def nip_check_digit(first9):
    return sum(int(c) * w for c, w in zip(first9, WEIGHTS)) % 11


def valid_nip(value):
    s = str(value)
    if len(s) != 10 or not s.isdigit():
        return False
    check = nip_check_digit(s[:9])
    return check != 10 and check == int(s[9])


def to_decimal(value):
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return dec if dec.is_finite() else None


def is_empty(value):
    return value is None or value == ""


def validate(rec):
    """Returns a list of failed checks. An empty list means all checks pass."""
    failures = []

    if any(is_empty(rec.get(f)) for f in FIELDS):
        failures.append("missing_field")

    for f in ("seller_nip", "buyer_nip"):
        if not is_empty(rec.get(f)) and not valid_nip(rec[f]):
            failures.append("nip_checksum")
            break

    if not is_empty(rec.get("issue_date")):
        try:
            parsed = date.fromisoformat(str(rec["issue_date"]))
            if not DATE_MIN <= parsed <= DATE_MAX:
                failures.append("date_range")
        except ValueError:
            failures.append("date_invalid")

    rate = None
    if not is_empty(rec.get("vat_rate")):
        try:
            rate = int(str(rec["vat_rate"]))
        except ValueError:
            failures.append("vat_rate_format")
        else:
            if rate not in VAT_RATES:
                failures.append("vat_rate_value")

    amounts = {}
    for k in ("net_amount", "vat_amount", "gross_amount"):
        v = rec.get(k)
        if is_empty(v):
            amounts[k] = None
            continue
        amounts[k] = to_decimal(v)
        if amounts[k] is None:
            failures.append("amount_format")
    net, vat, gross = (amounts[k] for k in ("net_amount", "vat_amount", "gross_amount"))

    if net is not None and vat is not None and gross is not None:
        if abs(net + vat - gross) > TOL:
            failures.append("sum_mismatch")
    if net is not None and vat is not None and rate in VAT_RATES:
        expected = (net * rate / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
        if abs(vat - expected) > TOL:
            failures.append("vat_mismatch")

    return failures