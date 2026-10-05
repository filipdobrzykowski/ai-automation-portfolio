# Email Triage (Simulated Scenario)

LLM-based triage of customer emails for a fictional online bike shop.
**Simulated scenario with synthetic data.** See `scenario.md`.

## Status
Baseline (v1) measured on 50 hand-labelled emails. Improved rules (v2) are
being tested on a separate, fresh set of 30 emails.

## Results

### Baseline v1: 50 emails, original labels (headline result)

| Metric | Result |
|---|---|
| Category accuracy | 92% (46/50) |
| Priority accuracy | 68% (34/50) |
| Order number extraction | 96% (48/50) |
| Unparseable responses | 0 |
| Cost per 1,000 emails | about $1.02 (assumed prices, to be verified) |
| Mean latency | 1.55 s |

### Same run after 6 documented label corrections

| Metric | Result |
|---|---|
| Category accuracy | 94% (47/50) |
| Priority accuracy | 78% (39/50) |

Each correction fixes a label that contradicted a rule I had written in
`scenario.md`. All six improve the score, so I treat the original result as
the headline and list every change in `label_corrections.md`.

### v2 rules on a fresh test set (30 emails)
To be added after evaluation.

### Notes
- With n = 50, one email is 2 percentage points. Small differences are noise.
- Labels were assigned by one person, so annotation bias is possible.
- Error analysis: `error_analysis.md`.