# Invoice Extraction (Simulated Scenario)

> Learning project, built with the help of an AI assistant (Claude).

LLM-based extraction of key fields from invoice text for a fictional
accounting office, combined with deterministic validation and routing
(automatic acceptance or manual review).
**Simulated scenario with synthetic data.** See `scenario.md`.

## Status
Complete (v1 and v2 prompts evaluated on a development set of 60 invoices
and a separate test set of 20). Further work is listed under Next steps.

## What it does
For each invoice text the model extracts nine fields into JSON (invoice
number, issue date, seller name, both tax IDs, net, VAT rate, VAT amount,
gross). Deterministic code then validates the result (tax ID checksum,
net + VAT = gross, VAT amount matches the rate, date range, no missing
fields) and routes the invoice: `auto` or `review` (human).

## Results

| Set | Prompt | Invoices fully correct | Silent errors |
|---|---|---|---|
| Development (60) | v1 | 58/60 | 2 |
| Development (60) | v2 | 60/60 (not independent evidence, see below) | 0 |
| Test (20) | v1 | 20/20 | 0 |
| Test (20) | v2 | 20/20 | 0 |

A silent error is an invoice with a wrong extracted field that was routed
`auto`. The test set (20 invoices, 6 with a missing field, 3 with an error
in the document) was generated with a different seed after the prompts were
frozen and committed to git before it was evaluated. Each prompt was run on
it once.

Cost per 1,000 invoices: about $1.35. Mean latency: about 1.44s per invoice.

## Findings
- **The test set does not separate v1 from v2.** Both reach 20/20, so it
  only shows that no failures were found (the lower bound of a 95%
  interval for 20/20 is about 84%). It is a ceiling effect, not proof of
  reliability.
- **The only failure mode observed:** on the development set, v1 filled in
  two fields that were absent from the document (an order number returned
  as invoice number; a VAT amount calculated although the prompt forbade
  it). Prompt v2 was written after seeing these errors, so its 60/60 on the
  development set is not independent evidence. On the test set, v1 handled
  all 6 missing-field cases correctly.
- **Division of labour between model and code.** The checks routed all 13
  injected document errors to review (10 on the development set, 3 on the
  test set), because the model extracted what was printed. They caught none
  of the model's own errors: a calculated VAT amount is consistent with
  net and rate, and an order number looks plausible.

## Method
1. Synthetic invoices from a generator that knows the ground truth, so no
   manual labelling is needed. Ground truth is the value as printed, even
   when the document is wrong.
2. Scenario, metrics and comparison rules written before any code
   (`scenario.md`).
3. Prompt v1 evaluated on the development set; errors analysed
   (`error_analysis.md`); prompt v2 written.
4. Prompts and test design frozen in git, test set generated and committed,
   then evaluated once per prompt.

## Repository
| File | Purpose |
|---|---|
| `scenario.md` | Fields, validation rules, metrics, protocol |
| `generate_invoices.py` | Invoice generator with ground truth |
| `validators.py` | Deterministic checks |
| `prompts/` | Frozen prompt versions |
| `extract.py` | Model call, normalisation, routing |
| `evaluate.py` | Metrics (no API calls) |
| `dataset/`, `results/` | All data and raw outputs (synthetic) |

## How to run
```bash
pip install -r requirements.txt
cp .env.example .env        # add your Anthropic API key
python3 generate_invoices.py
python3 extract.py --prompt v2
python3 evaluate.py --prompt v2
```

## Limitations
- Synthetic plain text from templates; real invoices are messier (scans,
  OCR errors, varied layouts). The test set comes from the same generator,
  so it measures generalisation over new random draws, not over unseen
  layouts.
- Missing-field cases are few: 3 in the development set, 6 in the test set.
  One invoice moves the result by 17 percentage points on the test set.
- The test set was composed after seeing development errors (more
  missing-field cases), so it does not reflect a realistic mix.
- One VAT rate per invoice, Polish and English only, no line items.
- Checks cannot detect a plausible but invented value that is consistent
  with the other fields.
- Cost estimate uses assumed token prices.

## Next steps
- Check that each extracted value occurs in the source text (would catch
  the calculated VAT amount, not the order number).
- Harder test set: unseen layouts, scanned-text noise, several VAT rates.
- Pilot on a few anonymised real invoices with a business partner.