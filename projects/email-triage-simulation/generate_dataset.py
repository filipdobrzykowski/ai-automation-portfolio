import csv
import random
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
random.seed(42)

MODEL = "claude-haiku-4-5-20251001"
OUT = Path(__file__).parent / "dataset" / "emails.csv"

COUNTS = {
    "zwrot_reklamacja": 10,
    "status_zamowienia": 10,
    "pytanie_o_produkt": 8,
    "faktura_platnosc": 8,
    "wspolpraca_spam": 6,
    "inne": 8,
}

SITUATIONS = {
    "zwrot_reklamacja": [
        "produkt przyszedł uszkodzony",
        "klient dostał zły rozmiar lub wariant",
        "produkt przestał działać po kilku dniach",
        "klient chce zwrócić produkt w terminie 14 dni",
        "w paczce brakuje części zestawu",
        "klient chce wymienić produkt na inny",
    ],
    "status_zamowienia": [
        "zamówienie nie dotarło mimo upływu terminu",
        "klient pyta, kiedy zamówienie zostanie wysłane",
        "klient chce zmienić adres dostawy przed wysyłką",
        "kurier nie zostawił paczki, klient pyta co dalej",
        "klient pyta o numer do śledzenia paczki",
    ],
    "pytanie_o_produkt": [
        "pytanie o kompatybilność produktu z konkretnym rowerem",
        "pytanie o dostępność produktu w innym kolorze",
        "pytanie o wymiary lub wagę przed zakupem",
        "pytanie, czym różnią się dwa podobne modele",
        "pytanie o gwarancję na produkt przed zakupem",
    ],
    "faktura_platnosc": [
        "klient prosi o fakturę na firmę do zamówienia",
        "płatność została pobrana dwa razy",
        "klient nie dostał potwierdzenia płatności",
        "klient pyta o zwrot pieniędzy po anulowaniu zamówienia",
        "błąd na fakturze (zły NIP lub kwota)",
    ],
    "wspolpraca_spam": [
        "oferta pozycjonowania strony za niską cenę",
        "propozycja współpracy od influencera rowerowego",
        "reklama hurtowni oferującej dropshipping",
        "automatyczna oferta usług księgowych",
        "propozycja wymiany linków",
    ],
    "inne": [
        "podziękowanie za szybką realizację zamówienia",
        "pytanie o godziny pracy lub adres sklepu stacjonarnego",
        "kandydat wysyła zapytanie o pracę w sklepie",
        "ktoś pisze do niewłaściwej firmy",
        "prośba o katalog lub newsletter",
    ],
}

PRODUCTS = [
    "lampka rowerowa LED", "zapięcie U-lock", "sakwa na bagażnik",
    "pompka podłogowa", "zestaw kluczy do roweru", "kask rowerowy",
    "licznik rowerowy", "błotniki", "dzwonek", "uchwyt na telefon",
]

NAMES = [
    "Anna", "Piotr", "Marta", "Tomasz", "Kasia", "Michał", "Ewa",
    "Jakub", "Agnieszka", "Paweł", "Magda", "Krzysztof", "Ola", "Marcin",
]

HARD_STYLES = [
    "z kilkoma literówkami i bez polskich znaków diakrytycznych",
    "napisany po angielsku",
    "zawiera dwa tematy naraz: główny oraz poboczny wątek z innej kategorii",
    "bardzo krótki, jedno zdanie",
    "wściekły, część słów WIELKIMI LITERAMI, ale sprawa jest drobna",
    "bardzo uprzejmy, ale sprawa jest pilna i klient podaje termin",
    "długi i chaotyczny, właściwa sprawa ukryta w środku",
    "niejednoznaczny, nie od razu wiadomo, czego klient chce",
    "z jedną wyraźną groźbą (np. zgłoszenie sprawy do UOKiK)",
    "napisany z telefonu, bez znaków interpunkcyjnych",
]
NORMAL_STYLE = "naturalny, zwykły ton klienta, 3-6 zdań"


def build_specs():
    specs = []
    for category, n in COUNTS.items():
        for _ in range(n):
            specs.append({"category": category, "style": NORMAL_STYLE})
    random.shuffle(specs)
    for spec, style in zip(random.sample(specs, len(HARD_STYLES)), HARD_STYLES):
        spec["style"] = style
    return specs


def generate_email(spec):
    situation = random.choice(SITUATIONS[spec["category"]])
    product = random.choice(PRODUCTS)
    name = random.choice(NAMES)
    if random.random() < 0.6:
        order = f"Zawiera numer zamówienia w formacie BG-{random.randint(10000, 99999)}."
    else:
        order = "Nie podaje numeru zamówienia."

    prompt = f"""Napisz jeden realistyczny e-mail od klienta sklepu internetowego BikeGear.pl (akcesoria rowerowe).

Sytuacja: {situation}
Produkt: {product}
Styl: {spec['style']}
Podpis: {name}
{order}

Zwróć WYŁĄCZNIE treść maila: pierwsza linia "Temat: ...", potem pusta linia, potem treść.
Nie dodawaj komentarzy ani informacji o kategorii maila."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    specs = build_specs()
    rows = []
    for i, spec in enumerate(specs, start=1):
        text = generate_email(spec)
        rows.append({"id": f"e{i:03d}", "email": text})
        print(f"{i}/{len(specs)} ok")

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "email"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Zapisano {len(rows)} maili do {OUT}")


if __name__ == "__main__":
    main()