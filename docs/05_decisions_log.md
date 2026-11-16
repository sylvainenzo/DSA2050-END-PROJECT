# Decisions Log

Row counts from `reports/cleaning_log.csv`, SQL checks q04–q13 and notebook outputs (run of 16 Nov 2026). Add rows as you go; never delete old ones (write "superseded by #n").

| # | Decision | Why | Rows affected | Risk / what could go wrong |
|---|---|---|---|---|
| 1 | Main source = NYCHA water bills (A); unit = development-month | Real, public, 66,432 bills, has an "Estimated" flag that separates unread meters from real reads | – | Public housing only, not the whole city |
| 2 | C2 drop exact duplicate rows | Identical rows double-count water | 4,660 removed | None expected; noted as a publisher data issue |
| 3 | C3 drop rows missing TDS, month or consumption | Cannot place in zone or time | 749 removed (31 no TDS, 725 no consumption) | Small bias if missingness clusters in some developments |
| 4 | C4 keep the five boroughs | "FHA" = scattered repossessed houses; "NON DEVELOPMENT FACILITY" is not housing | 26,258 removed (after C1–C3) | Lose a different housing type (43% of raw rows) |
| 5 | C5 drop accounts with no meter (blank meter number or "UN-METERED") | Flat-rate multifamily/commercial accounts: nothing measured | 2,498 removed | – |
| 6 | C6 drop sewer-only ("-Sewer", rate MWW SWR) and fire-service lines | Sewer lines repeat a water meter with zero use; fire lines are not consumption | 2,611 removed | A real meter mislabelled as sewer would be lost |
| 7 | C7 keep billing periods of 1–62 days | ≤0 days are errors; >62 days are quarterly/catch-up bills spanning 3+ months that cannot be placed in one month | 898 removed | Meters billed quarterly appear as missing months |
| 8 | C8 drop negative consumption | Reversals, not use | 0 removed | – |
| 9 | C9 same meter + same period billed twice → keep actual read | Revised bills | 123 removed | – |
| 10 | KEEP extreme high values, only flag them | They are the signal we look for | 0 removed | Some may be billing errors → checked in failure cases (e.g. UPACA Site 5, Apr–May 2023, >3,000 HCF/day) |
| 11 | Label each development-month actual / estimated / zero_read / missing_bill | Separate measurement gaps from real readings | 9,609 dev-months: 66.6% actual, 22.4% estimated, 8.9% missing, 2.1% zero | Threshold "≥50% of meters estimated" is a judgement call |
| 12 | Estimated months excluded from model target and lags | Estimated months are smoother (median month-to-month change 2.7% vs 6.8%) and lower (12.0 vs 26.4 HCF/day) than actual reads | 2,155 dev-months | Fewer training rows for poorly metered developments |
| 13 | LEFT JOIN bills → Data Book on TDS; keep unmatched | Data Book is a 1 Jan 2025 snapshot | 225 rows / 2 developments unmatched (Williamsburg TDS 1630, 2021; East 4th Street Rehab, 2013–14) | Those have no per-apartment rate |
| 14 | Label developments whole / partial metering (median < 25 gal/apt/day up to 2022 = partial) | 29 developments are metered only at a store or community centre; their per-apartment use is near zero. Clear break in the data: next value above the cut is 26.5 | 70 whole, 29 partial, 5 unknown | Per-apartment analysis covers 70 developments only |
| 15 | 311: use "supply" group (no water, low pressure, main break) for corroboration | Hydrant complaints (392,853 vs 99,273 supply complaints) are mostly summer openings, not supply failures | Descriptor list from q11 | Pattern matching could miss renamed descriptors |
| 16 | Time split: train ≤2021, validation 2022, test 2023-01 to 2025-05 | Mimics real use (predict the future) | train 7,308 / valid 731 / test 1,570 dev-months | COVID-19 period inside training |
| 17 | Expected-use method for Rule B = candidate (GB correction to persistence), chosen on VALIDATION MAE | Lowest validation error (0.127 vs persistence 0.129) | – | Gain over persistence is small (1.5% on test); persistence alone is a valid simpler choice |
| 18 | Operating Rule B threshold k = 4.5, chosen on the VALIDATION year (smallest k with ≤ 5% of 2022 development-months flagged: 4.4%) | Crew capacity; choosing k from test results would be leakage | Test: 6.0% flagged, lift 3.35 | Fewer flags = more missed problems; test rate slightly above target |
| 19 | Crew visit cost assumed at USD 400 | No public NYCHA figure; stated as an assumption | – | Break-even changes with this number |
