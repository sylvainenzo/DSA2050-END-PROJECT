# Final Report (8–12 pages) and Slides (8–10) — Outline

## Report — required sections (brief §6) with suggested length and evidence
| # | Section | Pages | Evidence to include |
|---|---|---|---|
| 1 | Executive summary | 0.5 | Decision, 3 key findings with numbers + CIs, 3 recommendations |
| 2 | Context and decision problem | 0.5 | Stakeholder, decision, unit, RQ1–RQ4, success measures |
| 3 | Data provenance and dictionary | 1 | Source register table, licences, key fields |
| 4 | Acquisition and SQL integration | 1 | Schema (PK/FK), one JOIN query, row-count validation table (Q7, Q13) |
| 5 | Data quality and preparation | 1 | Data-quality table, cleaning log (before/after) |
| 6 | Sampling, EDA and uncertainty | 2 | 4–6 figures with one-line findings, bootstrap CI table, stratified check, challenged assumption |
| 7 | Baseline and candidate method | 1 | Why seasonal naive; why gradient boosting; features; leakage checks |
| 8 | Validation and evaluation | 1.5 | Metric table, subgroup errors, rule A vs B, sensitivity, gap-vs-flag, cost table, failure cases |
| 9 | Ethics, bias and limitations | 0.5 | Table from charter, updated |
| 10 | Proposed randomised experiment | 0.5 | Protocol table |
| 11 | Recommendations and monitoring plan | 0.5 | 3+ actions, who/when/metric; monthly monitoring KPIs |
| 12 | References | – | Datasets (producer, link, licence, access date), libraries, AI declaration |
| 13 | Contribution statement | – | From CONTRIBUTIONS.md |

## Slides (8–10) for a 5–7 minute talk
1. Title + the decision question (who decides what, monthly)
2. Data: four sources, how they join, row counts
3. Quality: how much is measurement gap (one chart: Fig 4)
4. What we found in EDA (Fig 3 or Fig 5) with CI
5. Method: expected use → residual → flag; baseline vs candidate (metric table)
6. Rule A vs B + sensitivity (one table)
7. Priority list: "fix metering" vs "inspect" (Fig 10)
8. Recommendations (3) with cost
9. A/B test design + limitations
10. (Backup) leakage checks, failure cases

**Speaking split:** each member presents the part they led and must be able to answer questions on all parts.
