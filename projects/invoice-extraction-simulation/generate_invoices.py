import argparse
import csv
import random
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from validators import FIELDS, nip_check_digit, validate

parser = argparse.ArgumentParser()
parser.add_argument("--test", action="store_true",
                    help="generate the separate test set (20 invoices)")
args = parser.parse_args()

rng = random.Random(2026 if args.test else 42)
SUFFIX = "test" if args.test else "dev"
ID_PREFIX = "t" if args.test else "i"
COMP = (dict(normal=6, hard=11, missing=6, doc_error=3) if args.test
        else dict(normal=35, hard=15, missing=3, doc_error=10))

OUT_DIR = Path(__file__).parent / "dataset"
INVOICES_FILE = OUT_DIR / f"invoices_{SUFFIX}.csv"
TRUTH_FILE = OUT_DIR / f"truth_{SUFFIX}.csv"
for p in (INVOICES_FILE, TRUTH_FILE):
    if p.exists():
        sys.exit(f"{p.name} already exists. Refusing to overwrite it.")

HARD_KINDS = ["amount_dot", "amount_en", "date_long", "nip_prefix",
              "english", "swapped", "email", "noise"]
MISSING_FIELDS = ["buyer_nip", "vat_amount", "invoice_number"]
ERROR_TYPES = ["bad_nip", "sum_mismatch", "vat_mismatch", "bad_date"]

PREFIXES = ["Nova", "Zielony", "Błękitny", "Stalmet", "Orion", "Lipowa", "Biały",
            "Mazurska", "Alfa", "Delta", "Wisła", "Tęcza", "Brzoza", "Kamienny", "Polo"]
SUFFIXES = ["Handel", "Serwis", "Projekt", "Transport", "Meble", "Druk", "Budowa",
            "Technika", "Logistyka", "Pracownia", "Studio", "Hurt"]
FORMS = ["Sp. z o.o.", "S.A.", "Sp. j.", "P.P.H.U."]
STREETS = ["Lipowa", "Krótka", "Polna", "Słoneczna", "Ogrodowa", "Leśna", "Dworcowa"]
CITIES = ["Warszawa", "Kraków", "Gdańsk", "Poznań", "Wrocław", "Łódź", "Lublin"]
NAMES = ["Anna", "Piotr", "Marta", "Tomasz", "Kasia", "Michał", "Ewa", "Jakub"]
MONTHS = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
          "sierpnia", "września", "października", "listopada", "grudnia"]

LABELS = {
    "pl": dict(invoice="Faktura VAT nr", invoice_noid="Faktura VAT",
               number="Numer faktury", issue="Data wystawienia", seller="Sprzedawca",
               buyer="Nabywca", nip="NIP", net="Wartość netto", rate="Stawka VAT",
               vat="Kwota VAT", gross="Wartość brutto", due="Termin płatności",
               order="Zamówienie", customer="Nr klienta"),
    "en": dict(invoice="Invoice No.", invoice_noid="Invoice",
               number="Invoice number", issue="Issue date", seller="Seller",
               buyer="Buyer", nip="VAT ID", net="Net amount", rate="VAT rate",
               vat="VAT amount", gross="Gross amount", due="Due date",
               order="Order", customer="Customer no."),
}


def money(x):
    return f"{x:.2f}"


def make_nip():
    while True:
        first9 = str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(8))
        check = nip_check_digit(first9)
        if check != 10:
            return first9 + str(check)


def break_nip(nip):
    last = int(nip[-1])
    return nip[:-1] + str(rng.choice([x for x in range(10) if x != last]))


def make_company():
    return f"{rng.choice(PREFIXES)} {rng.choice(SUFFIXES)} {rng.choice(FORMS)}"


def make_address():
    return (f"ul. {rng.choice(STREETS)} {rng.randint(1, 120)}, "
            f"{rng.randint(0, 99):02d}-{rng.randint(0, 999):03d} {rng.choice(CITIES)}")


def group(digits, sep):
    parts = []
    while len(digits) > 3:
        parts.insert(0, digits[-3:])
        digits = digits[:-3]
    parts.insert(0, digits)
    return sep.join(parts)


def fmt_amount(value, style):
    whole, frac = value.split(".")
    if style == "space_pl":
        return f"{group(whole, ' ')},{frac} zł"
    if style == "dot_pl":
        return f"{group(whole, '.')},{frac} zł"
    if style == "plain_dot":
        return f"{whole}.{frac} PLN"
    if style == "en":
        return f"PLN {group(whole, ',')}.{frac}"
    return f"{whole},{frac} zł"


def fmt_date(iso, style):
    y, m, d = (int(x) for x in iso.split("-"))
    if style == "dots":
        return f"{d:02d}.{m:02d}.{y}"
    if style == "slash":
        return f"{y}/{m:02d}/{d:02d}"
    if style == "long_pl":
        return f"{d} {MONTHS[m - 1]} {y}"
    return iso


def fmt_nip(nip, style):
    if style == "dashes":
        return f"{nip[:3]}-{nip[3:6]}-{nip[6:8]}-{nip[8:]}"
    if style == "spaces":
        return f"{nip[:3]} {nip[3:6]} {nip[6:8]} {nip[8:]}"
    if style == "prefix":
        return "PL" + nip
    return nip


def make_base(hint):
    start, end = date(2025, 1, 1).toordinal(), date(2026, 12, 31).toordinal()
    issue = date.fromordinal(rng.randint(start, end))
    low_cents = 100000 if hint and hint.startswith("amount") else 5000
    net = (Decimal(rng.randint(low_cents, 2500000)) / 100).quantize(Decimal("0.01"))
    rate = rng.choices([23, 8, 5, 0], weights=[70, 15, 5, 10])[0]
    vat = (net * rate / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    seller_nip = make_nip()
    buyer_nip = make_nip()
    while buyer_nip == seller_nip:
        buyer_nip = make_nip()
    n = rng.randint(1, 999)
    number = rng.choice([
        f"FV/{issue.year}/{issue.month:02d}/{n:04d}",
        f"FV {n}/{issue.year}",
        f"{issue.year}/{issue.month:02d}/FV/{n}",
        f"INV-{issue.year}-{n:04d}",
    ])
    seller_name = make_company()
    buyer_name = make_company()
    while buyer_name == seller_name:
        buyer_name = make_company()
    truth = {
        "invoice_number": number, "issue_date": issue.isoformat(),
        "seller_name": seller_name, "seller_nip": seller_nip, "buyer_nip": buyer_nip,
        "net_amount": money(net), "vat_rate": rate, "vat_amount": money(vat),
        "gross_amount": money(net + vat),
    }
    ctx = {"buyer_name": buyer_name, "seller_addr": make_address(),
           "buyer_addr": make_address()}
    return truth, ctx


def apply_error(truth, error):
    if error == "bad_nip":
        who = rng.choice(["seller_nip", "buyer_nip"])
        truth[who] = break_nip(truth[who])
        return f"bad_nip:{who}"
    if error == "sum_mismatch":
        delta = Decimal(rng.randint(100, 5000)) / 100
        truth["gross_amount"] = money(Decimal(truth["gross_amount"]) + delta)
    elif error == "vat_mismatch":
        delta = Decimal(rng.randint(50, 3000)) / 100
        new_vat = Decimal(truth["vat_amount"]) + delta
        truth["vat_amount"] = money(new_vat)
        truth["gross_amount"] = money(Decimal(truth["net_amount"]) + new_vat)
    elif error == "bad_date":
        year = rng.choice([2025, 2026])
        month, day = rng.choice([(4, 31), (6, 31), (9, 31), (11, 31), (2, 30)])
        truth["issue_date"] = f"{year:04d}-{month:02d}-{day:02d}"
    return error


def make_style(detail):
    s = {"layout": rng.choice(["classic", "keyvalue"]),
         "amount": rng.choice(["space_pl", "plain_pl"]),
         "date": rng.choice(["iso", "dots"]),
         "nip": rng.choice(["plain", "dashes"]),
         "lang": "pl", "swapped": False, "noise": rng.random() < 0.5}
    d = detail or ""
    if d == "amount_dot":
        s["amount"] = "dot_pl"
    elif d == "amount_en":
        s["amount"] = rng.choice(["plain_dot", "en"])
    elif d == "date_long":
        s["date"] = rng.choice(["long_pl", "slash"])
    elif d == "nip_prefix":
        s["nip"] = rng.choice(["prefix", "spaces"])
    elif d == "english":
        s.update(lang="en", amount="en", date=rng.choice(["iso", "slash"]))
    elif d == "swapped":
        s.update(layout="classic", swapped=True)
    elif d == "email":
        s["layout"] = "email"
    elif d == "noise":
        s["noise"] = True
    elif d.startswith("missing:"):
        s["layout"] = rng.choice(["keyvalue", "email"])
    return s


def extras(truth, style, L):
    lines = [f"{L['order']}: ZK/{rng.choice([2025, 2026])}/{rng.randint(1, 999):04d}"]
    try:
        due = date.fromisoformat(truth["issue_date"]) + timedelta(days=rng.choice([7, 14, 30]))
        lines.append(f"{L['due']}: {fmt_date(due.isoformat(), style['date'])}")
    except ValueError:
        pass
    lines.append(f"{L['customer']}: {rng.randint(10**9, 10**10 - 1)}")
    lines.append("IBAN: PL" + f"{rng.randint(10, 99)} "
                 + " ".join(f"{rng.randint(0, 9999):04d}" for _ in range(6)))
    lines.append(f"tel. {rng.randint(500, 799)} {rng.randint(100, 999)} {rng.randint(100, 999)}")
    return lines


def block(L, role, name, address, nip):
    lines = [f"{L[role]}:", name, address]
    if nip:
        lines.append(f"{L['nip']}: {nip}")
    return lines


def render_classic(t, ctx, s):
    L = LABELS[s["lang"]]
    title = f"{L['invoice']} {t['invoice_number']}" if t["invoice_number"] else L["invoice_noid"]
    seller = block(L, "seller", t["seller_name"], ctx["seller_addr"],
                   fmt_nip(t["seller_nip"], s["nip"]))
    buyer = block(L, "buyer", ctx["buyer_name"], ctx["buyer_addr"],
                  fmt_nip(t["buyer_nip"], s["nip"]) if t["buyer_nip"] else None)
    first, second = (buyer, seller) if s["swapped"] else (seller, buyer)
    lines = [title, f"{L['issue']}: {fmt_date(t['issue_date'], s['date'])}", ""]
    lines += first + [""] + second + [""]
    lines.append(f"{L['net']} | {L['rate']} | {L['vat']} | {L['gross']}")
    lines.append(f"{fmt_amount(t['net_amount'], s['amount'])} | {t['vat_rate']}% | "
                 f"{fmt_amount(t['vat_amount'], s['amount'])} | "
                 f"{fmt_amount(t['gross_amount'], s['amount'])}")
    if s["noise"]:
        lines += [""] + extras(t, s, L)
    return "\n".join(lines)


def render_keyvalue(t, ctx, s):
    L = LABELS[s["lang"]]
    lines = []
    if t["invoice_number"]:
        lines.append(f"{L['number']}: {t['invoice_number']}")
    lines.append(f"{L['issue']}: {fmt_date(t['issue_date'], s['date'])}")
    lines.append(f"{L['seller']}: {t['seller_name']}, {ctx['seller_addr']}")
    lines.append(f"{L['nip']} ({L['seller'].lower()}): {fmt_nip(t['seller_nip'], s['nip'])}")
    lines.append(f"{L['buyer']}: {ctx['buyer_name']}, {ctx['buyer_addr']}")
    if t["buyer_nip"]:
        lines.append(f"{L['nip']} ({L['buyer'].lower()}): {fmt_nip(t['buyer_nip'], s['nip'])}")
    lines.append(f"{L['net']}: {fmt_amount(t['net_amount'], s['amount'])}")
    lines.append(f"{L['rate']}: {t['vat_rate']}%")
    if t["vat_amount"]:
        lines.append(f"{L['vat']}: {fmt_amount(t['vat_amount'], s['amount'])}")
    lines.append(f"{L['gross']}: {fmt_amount(t['gross_amount'], s['amount'])}")
    if s["noise"]:
        lines += extras(t, s, L)
    return "\n".join(lines)


def render_email(t, ctx, s):
    L = LABELS["pl"]
    date_txt = fmt_date(t["issue_date"], s["date"])
    if t["invoice_number"]:
        intro = f"w załączeniu przesyłam fakturę {t['invoice_number']} z dnia {date_txt}"
    else:
        intro = f"w załączeniu przesyłam fakturę z dnia {date_txt}"
    intro += (f" wystawioną przez {t['seller_name']} "
              f"(NIP {fmt_nip(t['seller_nip'], s['nip'])}) dla firmy {ctx['buyer_name']}.")
    parts = ["Dzień dobry,", "", intro]
    if t["buyer_nip"]:
        parts.append(f"NIP nabywcy: {fmt_nip(t['buyer_nip'], s['nip'])}.")
    amounts = (f"Wartość netto wynosi {fmt_amount(t['net_amount'], s['amount'])}, "
               f"stawka VAT {t['vat_rate']}%")
    if t["vat_amount"]:
        amounts += f", kwota VAT {fmt_amount(t['vat_amount'], s['amount'])}"
    amounts += f", do zapłaty brutto {fmt_amount(t['gross_amount'], s['amount'])}."
    parts.append(amounts)
    if s["noise"]:
        parts += [""] + extras(t, s, L)
    parts += ["", "Pozdrawiam,", rng.choice(NAMES)]
    return "\n".join(parts)


RENDERERS = {"classic": render_classic, "keyvalue": render_keyvalue, "email": render_email}


def main():
    non_missing = COMP["hard"] - COMP["missing"]
    specs = [("normal", None)] * COMP["normal"]
    specs += [("hard", HARD_KINDS[i % len(HARD_KINDS)]) for i in range(non_missing)]
    specs += [("hard", f"missing:{MISSING_FIELDS[i % len(MISSING_FIELDS)]}")
              for i in range(COMP["missing"])]
    specs += [("doc_error", ERROR_TYPES[i % len(ERROR_TYPES)])
              for i in range(COMP["doc_error"])]
    rng.shuffle(specs)

    invoices, truths = [], []
    for i, (kind, detail) in enumerate(specs, start=1):
        inv_id = f"{ID_PREFIX}{i:03d}"
        truth, ctx = make_base(detail if kind == "hard" else None)
        expected = "auto"
        if kind == "doc_error":
            detail = apply_error(truth, detail)
            expected = "review"
        if kind == "hard" and detail.startswith("missing:"):
            truth[detail.split(":", 1)[1]] = None
            expected = "review"
        style = make_style(detail if kind == "hard" else None)
        text = RENDERERS[style["layout"]](truth, ctx, style)

        fails = validate(truth)
        if (expected == "review") != bool(fails):
            sys.exit(f"Generator bug at {inv_id} ({kind}/{detail}): "
                     f"expected {expected}, checks failed: {fails}\n{truth}")

        invoices.append({"id": inv_id, "text": text})
        row = {"id": inv_id, "kind": kind, "detail": detail or "", "expected_route": expected}
        row.update({f: ("" if truth[f] is None else truth[f]) for f in FIELDS})
        truths.append(row)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(INVOICES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "text"])
        writer.writeheader()
        writer.writerows(invoices)
    with open(TRUTH_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "kind", "detail", "expected_route"] + FIELDS)
        writer.writeheader()
        writer.writerows(truths)

    print(f"Saved {len(invoices)} invoices to {INVOICES_FILE.name} and {TRUTH_FILE.name}")
    print("Kinds:", dict(Counter(r["kind"] for r in truths)))
    print("Details:", dict(Counter(r["detail"].split(":")[0] for r in truths)))
    print("Expected routes:", dict(Counter(r["expected_route"] for r in truths)))


if __name__ == "__main__":
    main()