# Project Charter — Water Supply Reliability Monitoring (Option 06)
DSA 2050 · Group members: ________ / ________ / ________ · Date: ________ · Repo: ________

## 1. Problem and stakeholder
NYCHA manages hundreds of public-housing developments in New York City and pays a monthly water bill for each meter. Leaks, broken meters and supply disruptions waste water and money, and leave residents without service. Crews are limited, so they must go where problems are real and recurring.

**Primary stakeholder:** NYCHA water/utilities management team. **Secondary:** NYC DEP (supply incidents), residents (service quality).

## 2. Decision
Each month, decide which developments get (a) a **meter-repair visit** because readings keep going missing, or (b) a **leak/supply inspection** because consumption is repeatedly abnormal — and which are only monitored.

## 3. Unit of analysis
One **development-month** (a NYCHA development, identified by TDS #, in one bill month). Borough is the higher-level zone for linking 311 complaints.

## 4. Research questions
1. **RQ1 – Abnormal consumption:** Which developments repeatedly use much more or much less water than expected from their own history, season, weather and size, and how much excess water and cost does that represent?
2. **RQ2 – Measurement gaps:** How many development-months are measurement gaps (estimated reads, zero reads, missing bills) rather than real readings, and which developments have recurring gaps?
3. **RQ3 – Corroboration:** Do abnormal months coincide with weather extremes or with spikes in 311 water-system complaints in the same borough?
4. **RQ4 – Method:** Does a development-specific expected-use rule flag abnormal months more usefully than one citywide threshold?

## 5. Data (see source register)
A NYCHA monthly water bills 2013–May 2025 (CSV, 66,432 rows, 25 fields) · B NYCHA Development Data Book (CSV, 346 rows) · C 311 "Water System" complaint counts (JSON API, 11,252 borough-month-type rows) · D Open-Meteo daily weather (JSON API, 4,534 days). Join: A.tds → B.tds (SQL LEFT JOIN, row-count validated); A ↔ C on borough + month; A ↔ D on month.

## 6. Assumptions
- An "Estimated = Y" bill means the meter was not read; its value is not evidence of real use.
- Billing periods of 20–40 days are representative of a month; use is normalised per day.
- 311 complaints are an imperfect, borough-level signal of real disruptions (reporting bias exists).
- Development size (apartments) from the current Data Book is stable enough over the period.
- Weather at Central Park represents the whole city at monthly scale.

## 7. Success measures
- Expected-use method reduces test-period MAE (log scale) by **≥ 10%** vs. the seasonal-naive baseline (same month last year). We also compare against a persistence baseline (last actual month) and report the result honestly.
- The chosen flagging rule keeps the monthly workload within crew capacity (target **≤ 5%** of development-months flagged) and shows lift > 1 against 311 supply-disruption spikes, or we report honestly that it does not.
- A ranked priority list separating "fix metering" from "inspect" developments, with uncertainty stated.

## 8. Scope
**In:** NYCHA developments in the five boroughs, 2013 – May 2025, monthly. **Out:** FHA scattered houses, un-metered accounts, non-NYCHA buildings, real-time/daily detection, causal claims about leaks (we have no inspection records), live experiments.

## 9. Ethical risks and safeguards
| Risk | Safeguard |
|---|---|
| High use blamed on residents of low-income housing | Frame flags as infrastructure/metering issues; no tenant-level data; per-apartment rates only as context |
| 311 reporting bias (some areas report more) | Use 311 only as weak corroboration, never as the target; discuss in limitations |
| Unfair prioritisation between boroughs or sizes | Report flag rates and errors by borough and size group |
| Over-confidence in model flags | Show confidence intervals, sensitivity analysis and failure cases; recommend human review before action |
| Privacy | Only aggregate counts from 311; no addresses or names in the repo |
| Generalising NYC findings to other cities (e.g. Nairobi) | State as a limitation; describe what data a local utility would need |

## 10. Timeline and roles
See `docs/03_work_plan.md`.
