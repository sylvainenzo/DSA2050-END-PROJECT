# Interim Findings Memo (Week 3)

**To:** NYCHA water/utilities management and course instructor · **From:** Group __ · **Date:** ____

## 1. Purpose
We are building an evidence base to decide, each month, which NYCHA developments need a meter repair and which need a leak or supply inspection. This memo reports data status and exploratory findings only; no model results yet.

## 2. Data status
- 66,432 raw bills (2013-01 to 2025-05) → **28,635 clean metered bills** after rules C1–C9; 43% of raw rows were "FHA" scattered houses (out of scope).
- **104 developments** have metered water bills; they form 9,609 development-months once missing months are filled in.
- Join to the Development Data Book kept every row (28,635 before and after); 225 rows from 2 developments did not match.
- 29 developments are metered only at a store or community centre ("partial metering"). Per-apartment comparisons use the **70 whole-metered developments**.

## 3. What we observed (observation → uncertainty)
- **Measurement gaps are common and rising (Fig 4).** One in three development-months (33.4%) is a gap: 22.4% estimated, 8.9% missing bill, 2.1% zero read. The estimated share of billed months rose from 18.6% (2018) to 36.9% (2024) and 41.2% (Jan–May 2025). Borough gap rates range from 29.9% (Bronx, 95% CI 15.8–45.2) to 36.7% (Brooklyn, 23.7–51.6); the intervals overlap, so no borough is clearly worse.
- **Recurring gaps are concentrated (Fig 7, q9).** Claremont Rehab (Group 2), Ingersoll and Van Dyke I had 95% of bills estimated; Ocean Bay (Oceanside) 92%; Queensbridge South 91%.
- **Typical use (Figs 1–3).** Median 203 gallons per apartment per day (whole-metered developments, actual reads), with a long right tail. Typical use was higher in 2014 (median 238) than in 2024 (190).
- **Boroughs (Fig 3, Fig 8a).** Mean use per apartment is highest in the Bronx (290 gal/apt/day, 95% CI 232–357) and lowest in Queens (190, 122–271). The Bronx–Queens difference (100) has a 95% CI of −7 to 197, which includes 0: **no clear difference**.
- **Season and weather (Fig 5).** Almost no seasonal pattern and no association with monthly temperature (Pearson r = −0.01). This is an association result only.
- **311 (Fig 6).** Supply complaints (no water, low pressure, main break) total 99,273 in the five boroughs over 2013–May 2025; hydrant complaints (392,853) dominate the raw totals but mostly reflect summer hydrant openings.

## 4. Uncertainty and sampling
- All intervals are cluster-bootstrap 95% CIs (2,000 resamples of whole developments), because months from the same development are correlated.
- A 25% sample of developments (1,000 repeats) estimates the citywide gap rate (33.4%) within roughly ±12 points (simple random 22.0–47.2; stratified by borough 20.5–44.5). Stratification helps only a little. A sample is good enough for a citywide trend, **not** for choosing individual developments.

## 5. Assumption we challenged
"An estimated bill is about as good as a real reading." **Rejected.** Estimated months change far less from month to month (median 2.7% vs 6.8%) and sit lower (12.0 vs 26.4 HCF/day). They are copies of past readings, not measurements, so they are excluded from the model target and from the features that describe past use.

## 6. Refined questions for Week 4
1. RQ1: Which developments repeatedly use more or less water than expected from their own history, and what is the excess worth?
2. RQ2: Which developments have recurring measurement gaps, and how fast is the gap rate rising?
3. RQ3: Do abnormal months coincide with 311 supply-disruption spikes in the same borough? (Weather dropped as an explanation: no association in Fig 5.)
4. RQ4: Does a development-specific rule flag more useful months than a citywide per-apartment threshold?

## 7. Risks and next steps
Risks: 311 is borough-level and subject to reporting bias; partial metering limits per-apartment analysis; no inspection records exist to confirm real leaks. Week 4: fit baselines and the candidate, compare rules A and B on a time split, and cost the errors.
