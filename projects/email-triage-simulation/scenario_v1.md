# Scenario: BikeGear.pl (fictional)

**This is a simulated scenario. All data is synthetic.**

BikeGear.pl is an imaginary small online shop selling bicycle accessories
(lights, locks, bags, tools). One shared inbox receives about 40 customer
emails per day, handled by two people. Emails are in Polish, with a small
share in English.

## Task
For each incoming email, the system returns:
- `category`: one of the categories below
- `priority`: high / medium / low
- `order_number`: order number or null
- `summary`: one sentence, max 15 words

## Categories

| Category | Definition |
|---|---|
| return_complaint | Customer wants to return, exchange or complain about a product |
| order_status | Customer asks where the order is or about delivery time |
| product_question | Question about a product before buying (size, compatibility, availability) |
| invoice_payment | Invoice, payment, refund of money, payment errors |
| partnership_spam | Partnership offers, advertising, unsolicited mail |
| other | Anything that fits none of the above |

## Priority rules

| Priority | When |
|---|---|
| high | Damaged or wrong item, payment taken twice, deadline mentioned (e.g. "need it by Friday"), clearly angry customer, threat of a chargeback |
| medium | Order is late but no deadline, a concrete question blocking a purchase |
| low | General questions, thanks, partnership offers, spam |

## Labeling rules for ambiguous cases
1. If an email contains two topics, label the **more urgent** one.
2. If both are equally urgent, label the one mentioned **first**.
3. Priority is judged by the content of the email, not by its tone alone.
4. When unsure between a category and `other`, choose the category.

## Out of scope
Attachments, images, email threads, automatic replies.