# Error analysis: baseline v1

Baseline run: 50 hand-labelled emails, Claude Haiku 4.5, prompt v1.
Category accuracy 92% (46/50), priority accuracy 68% (34/50).
All 20 emails with an error were reviewed manually.

## Summary

| Code | Meaning | Emails | Count |
|---|---|---|---|
| A | Clear model error | none | 0 |
| B | Rule is ambiguous, both answers defensible | see table B | 14 |
| C | My label contradicts a rule I wrote in scenario.md | see table C | 6 |

## C: labels that contradict my own rules

| ID | Field | My label | Proposed | Rule violated | Your decision |
|---|---|---|---|---|---|
| e002 | priority | low | medium | A question blocking a purchase is `medium` | agree |
| e007 | priority | low | medium | same | agree |
| e028 | priority | low | medium | same | agree |
| e005 | priority | medium | high | Damaged or broken item is `high` | agree |
| e047 | priority | high | medium | Missed delivery, no deadline, no anger is `medium`; also inconsistent with e017 | agree |
| e011 | category | return_complaint | invoice_payment | `invoice_payment` includes refund of money | agree |

## B: gaps in the rules (to be fixed in v2)

| Pattern | Emails | Problem | Proposed v2 rule | Your decision |
|---|---|---|---|---|
| Address change before shipment | e004, e010, e022, e035 | No deadline stated, rules do not cover it | `high`: cost of the error rises after shipment | agree |
| Company invoice, wrong tax ID | e009, e026, e027 | Nothing in the `high` list fits | `medium`, unless a date is given; double charge stays `high` | agree|
| Failed delivery | e017 | Not late, but not delivered | `medium` | agree|
| Fit question | e018 | Unclear if it blocks a purchase | `medium` if about a specific model and bike | agree|
| Wrong size vs defect | e025 | "Does not fit" is not a defect or wrong item | defect, damage, wrong shipment = `high`; correct item that does not suit = `medium` | agree|
| Refund status | e011 (priority) | No rule | `medium`, unless a deadline is given | agree|
| Category for spam | e015, e016, e050 | Customers asking about or replying to spam, not spammers. The phrase "unsolicited mail" misleads the model | `partnership_spam` only for messages sent by a third party advertising its own offer | agree|

## Methodological note

All six corrections in table C improve the model's score. I keep the
original v1 result as the headline number and report the corrected result
separately, with every change documented in `label_corrections.md`.

## Observations for the README

- e050: the customer suggests a possible data leak. In a real shop this
  email would be escalated, but under the current rules it is `other` / `low`.
- e025: one email contains two topics (dropshipping and a complaint).
  The labelling rule says to label the more urgent one.