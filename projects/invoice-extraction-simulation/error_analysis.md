# Error analysis: prompt v1 on the development set

60 invoices, 58 fully correct. Both errors are silent (routed `auto`).

| ID | Kind | Error | Cause (confirmed by reading the invoice) |
|---|---|---|---|
| i016 | missing invoice_number | model returned the order number (`Zamówienie: ZK/2025/0246`) | spec gap: v1 did not say that order numbers are not invoice numbers |
| i035 | missing vat_amount | model returned `194.83`, which is not printed anywhere | model ignored an explicit rule; the value follows from net and rate, and from gross minus net |

## Observations
- Both errors fill a field that is absent from the document.
- The deterministic checks did not catch either: the calculated VAT amount
  is consistent with net and rate, and an order number looks plausible.
- The checks caught all 10 injected document errors.
- The development set is easy (35 normal invoices: 100%), so the pooled
  accuracy is not a useful headline number.
- A check that an extracted value occurs in the source text would catch
  i035 (the value is not printed) but not i016 (the order number is printed).

## Decision
Prompt v2 adds two explicit rules (see `prompts/v2.txt`). Because v2 was
written after seeing these errors, the development set cannot prove that
it is better; it is used only as a regression check. The test set is
generated with more missing-field cases (6 of 20) so that this failure
mode is actually measured.

## Limitations noted (to be moved to the README)
- The test set comes from the same generator (same templates) as the
  development set, so it measures generalisation over new random draws,
  not over unseen invoice layouts.
- Missing-field cases are few: 3 in the development set, 6 in the test set.
  One invoice moves the result by 17 percentage points.