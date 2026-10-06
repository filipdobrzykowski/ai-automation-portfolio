# Scenario: AccountDesk (fictional accounting office)

**This is a simulated scenario. All data is synthetic.**

AccountDesk is an imaginary small accounting office that receives purchase
invoices from clients as plain text (copied from PDFs or emails). Someone
has to type the key fields into the accounting system and check them.
Typing errors in tax IDs and amounts cause rework.

## Task
For each invoice text, the system:
1. extracts nine fields into JSON (model step),
2. validates the result with deterministic rules (code step),
3. routes the invoice: `auto` (all fields present and all checks pass)
   or `review` (anything else, for a human).

## Fields

| Field | Format | Rules |
|---|---|---|
| invoice_number | string | As printed, trimmed |
| issue_date | YYYY-MM-DD | Convert any printed date format |
| seller_name | string | As printed, trimmed |
| seller_nip | 10 digits | Remove dashes, spaces and the `PL` prefix |
| buyer_nip | 10 digits | Same |
| net_amount | decimal, dot, 2 places | `1 234,56 zł` -> `1234.56` |
| vat_rate | integer: 23, 8, 5 or 0 | Percent, without the % sign |
| vat_amount | decimal, dot, 2 places | As printed |
| gross_amount | decimal, dot, 2 places | As printed |

If a field is missing from the text, the value is `null`. The model never
guesses or calculates a missing field.

Expected model output (example):

    {"invoice_number": "FV/2026/10/0042", "issue_date": "2026-10-05",
     "seller_name": "Example Sp. z o.o.", "seller_nip": "1234563218",
     "buyer_nip": "5260250995", "net_amount": "1000.00", "vat_rate": 23,
     "vat_amount": "230.00", "gross_amount": "1230.00"}

## Ground truth
Fields are extracted **as printed**, even if the document itself is wrong.
The generator knows exactly which values it printed, so no manual labelling
is needed.

## Two kinds of errors (kept separate in the evaluation)
- **Document errors**: the invoice itself is inconsistent (invalid NIP
  checksum, net + VAT != gross, VAT amount not matching the rate, impossible
  date). The correct route is `review`.
- **Extraction errors**: the model returns a value different from the
  printed one. Whether this is caught depends on the checks.

Expected route is `review` if the document has an injected error or a
missing field, otherwise `auto`.

## Validation rules (code, no model)
1. NIP checksum: weights 6,5,7,2,3,4,5,6,7 on the first nine digits; the
   sum modulo 11 must equal the tenth digit (a remainder of 10 is invalid).
2. `net_amount + vat_amount == gross_amount` (tolerance 0.01).
3. `vat_amount == net_amount * vat_rate / 100`, rounded to 2 places
   (tolerance 0.01).
4. `vat_rate` is one of 23, 8, 5, 0.
5. `issue_date` is a valid date between 2025-01-01 and 2026-12-31.
6. `invoice_number`, `seller_name` and all other fields are not null.

## Metrics (fixed before any code is written)

Comparison rule: amounts are compared as decimal numbers (`1234.5` equals
`1234.50`); every other field is compared as an exact string after trimming.
`vat_rate` must be an integer such as `23`, not `23%`. A missing field
(`null`) counts as correct only if the ground truth is also missing.

- **Field accuracy**: exact match with ground truth, per field.
- **Invoice accuracy**: share of invoices where all nine fields match.
- **Route accuracy**: share of invoices routed as expected.
- **Silent errors**: invoices with at least one wrong extracted field that
  were routed `auto`. This is the most important number.
- **Needless reviews**: invoices with all fields correct and a correct
  document that were routed `review`.
- Cost per 1,000 invoices and mean latency (assumed token prices).

## Evaluation protocol
1. Development set: 60 invoices (15 hard, 10 with document errors), used for
   building and for iterating on the prompt.
2. After the prompt is frozen, a separate test set of 20 invoices is
   generated with a different seed and committed to git **before** the
   evaluation is run.
3. The test set is evaluated once.
4. Prompts live in `prompts/` as versioned files (`v1.txt`, `v2.txt`). A
   prompt is frozen by committing it to git before it is run on the test set.
   Every prompt version keeps its own result files.

## Out of scope
Scanned documents and OCR errors, several VAT rates on one invoice,
foreign currencies, exempt or non-taxable sales, correction invoices,
structured e-invoices (XML), line items.

## Data note
Company names are invented. NIP numbers are generated randomly with a valid
checksum, so a match with a real entity is coincidental.