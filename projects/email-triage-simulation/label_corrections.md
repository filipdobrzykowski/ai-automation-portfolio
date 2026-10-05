# Label corrections

`dataset/labels.csv` is **not edited**. Corrections are listed here and
applied in a separate step. Each correction cites the rule from
`scenario.md` that the original label violated.

| ID | Field | Original | Corrected | Reason (rule) |
|---|---|---|---|---|
| e002 | priority | low | medium | A question blocking a purchase is `medium` |
| e007 | priority | low | medium | same |
| e028 | priority | low | medium | same |
| e005 | priority | medium | high | Damaged or broken item is `high` |
| e047 | priority | high | medium | Missed delivery without deadline or anger is `medium` |
| e011 | category | return_complaint | invoice_payment | `invoice_payment` covers refunds of money |