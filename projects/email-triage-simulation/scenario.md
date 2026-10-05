# Scenario: BikeGear.pl (fictional)

**This is a simulated scenario. All data is synthetic.**

BikeGear.pl is an imaginary small online shop selling bicycle accessories
(lights, locks, bags, tools). One shared inbox receives about 40 customer
emails per day, handled by two people. Emails are in Polish, with a small
share in English.

## Task
For each incoming email, the system returns:
- `kategoria`: one of the categories below
- `priorytet`: wysoki / sredni / niski
- `numer_zamowienia`: order number or null
- `streszczenie`: one sentence, max 15 words

## Categories

| Category | Definition |
|---|---|
| zwrot_reklamacja | Customer wants to return, exchange or complain about a product |
| status_zamowienia | Customer asks where the order is or about delivery time |
| pytanie_o_produkt | Question about a product before buying (size, compatibility, availability) |
| faktura_platnosc | Invoice, payment, refund of money, payment errors |
| wspolpraca_spam | Partnership offers, advertising, unsolicited mail |
| inne | Anything that fits none of the above |

## Priority rules

| Priority | When |
|---|---|
| wysoki | Damaged or wrong item, payment taken twice, deadline mentioned (e.g. "need it by Friday"), clearly angry customer, threat of a chargeback |
| sredni | Order is late but no deadline, a concrete question blocking a purchase |
| niski | General questions, thanks, partnership offers, spam |

## Labeling rules for ambiguous cases
1. If an email contains two topics, label the **more urgent** one.
2. If both are equally urgent, label the one mentioned **first**.
3. Priority is judged by the content of the email, not by its tone alone.
4. When unsure between a category and `inne`, choose the category.

## Out of scope
Attachments, images, email threads, automatic replies.