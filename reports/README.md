Water Supply Reliability Monitoring in NYC Public Housing
DSA 2050 Five-Week Applied Data Science Methodology Project · Option 06 · USIU-Africa · Group members: Sylvain Biket (674139), Victor Apamo (673804), Whitney Jebor (673308)
1. Executive summary
Of the 60 NYCHA developments with metered water bills in 2023–May 2025, 28 need their metering fixed before anything else can be judged, 8 show recurring abnormal consumption and should be inspected, and 24 can simply be monitored.
Decision supported. Each month, NYCHA's water/utilities team decides where to send a limited crew: a meter repair, a leak/supply inspection, or nothing.
Data. 66,432 monthly water bills from NYCHA (2013 – May 2025), joined in SQLite to the NYCHA Development Data Book, 311 "Water System" complaints and daily weather. After cleaning: 28,635 metered bills from 104 developments, 9,609 development-months.
Key findings
1.	Measurement gaps are the biggest reliability problem, and they are growing. One development-month in three (33.4%) is a gap: estimated bill 22.4%, missing bill 8.9%, zero read 2.1%. The estimated share of billed months rose from 18.6% (2018) to 36.9% (2024) and 41.2% (Jan–May 2025).
2.	Estimated bills are not measurements. They change far less month to month than real reads (median 2.7% vs 6.8%). Against an expected-use model, estimated months look normal, so a leak during an estimated month is invisible; zero reads, by contrast, are flagged 3 times as often as real reads (33.3% vs 10.8%).
3.	Last month predicts this month. A persistence forecast (last actual month) is 36% more accurate than "same month last year". Our gradient-boosting candidate improves on persistence by only 1.5% on the 2023–25 test period. Weather and season add almost nothing (r = −0.01 between monthly use and temperature).
4.	A development-specific rule beats a citywide threshold. On the same 691 test development-months, Rule B (abnormal versus the development's own expected use) flagged fewer months (8.3% vs 12.5%), its flags coincided with 311 supply-disruption spikes 3.4× more often than chance (Rule A: 2.6×), and it did not concentrate on large developments (11% vs 35% of flags in the largest third).
5.	Inspection pays. At the operating threshold, a typical (median) high-use flag represents about USD 3,200 of excess water and sewer charges in one month, against an assumed USD 400 crew visit.
Recommendations (Section 11). (1) Restore meter reading at the 28 "fix metering" developments, starting with those estimated 90%+ of the time. (2) Inspect the 8 developments with recurring abnormal use. (3) Adopt Rule B at threshold |z| > 4.5, chosen on the 2022 validation year to flag at most 5% of development-months (6.0% on the test period). (4) Test the effect of proactive inspection with the randomised experiment in Section 10 before scaling up.
2. Context and decision problem
NYCHA pays a monthly water and sewer bill for every meter in its developments. Leaks, broken meters and supply failures waste water and money and leave residents without service, but repair crews are limited. The question is where to send them.
Element	Our framing
Stakeholder	NYCHA water/utilities management (primary); NYC DEP for supply incidents; residents
Decision	Each month: meter repair, leak/supply inspection, or monitor only
Decision question	Which zones show recurring disruption or abnormal consumption?
Unit of analysis	Development-month (zone = development, identified by TDS #; higher-level zone = borough)
Scope	NYCHA developments in the five boroughs, Jan 2013 – May 2025, monthly bills; excludes FHA scattered houses, un-metered accounts and causal claims about leaks
Research questions
1.	RQ1 – Abnormal consumption: which developments repeatedly use more or less water than expected from their own history, and what is the excess worth?
2.	RQ2 – Measurement gaps: how many development-months are measurement gaps rather than real readings, and which developments have recurring gaps?
3.	RQ3 – Corroboration: do abnormal months coincide with 311 supply-disruption spikes in the same borough? (Weather was dropped as an explanation after EDA showed no association.)
4.	RQ4 – Method: does a development-specific rule flag more useful months than one citywide per-apartment threshold?
Success measures (set in Week 1)
•	The expected-use method reduces test-period error (MAE, log scale) by at least 10% versus the seasonal-naive baseline.
•	The chosen flagging rule keeps workload near crew capacity (≤ 5% of development-months) and shows lift above 1 against 311 supply spikes.
•	A ranked priority list separating "fix metering" from "inspect" developments, with uncertainty stated.
3. Data provenance and dictionary
Four public sources were downloaded on 16 November 2026 with src/download_data.py; the raw files are kept out of GitHub (listed in .gitignore) and can be rebuilt by re-running that script; the exact request addresses, row counts, sizes and SHA-256 hashes are in data/raw_manifest.csv.
Dataset	Producer	Format · raw rows	Licence
A. Water Consumption And Cost (66be-66yr), Jan 2013 – May 2025	NYCHA	CSV · 66,432	NYC Open Data Terms of Use
B. NYCHA Development Data Book (evjd-dqpz), 1 Jan 2025	NYCHA	CSV · 346	NYC Open Data Terms of Use
C. 311 "Water System" complaints, 2010–19 + 2020–present
NYC 311 / OTI	JSON · 11,252 counts	NYC Open Data Terms of Use
D. Open-Meteo Historical Weather API, Central Park	Open-Meteo	JSON · 4,534 days	CC BY 4.0
NYC split its 311 dataset in December 2025, so both parts were queried and combined. Only aggregated 311 counts were downloaded, and dataset A holds no tenant information, so no personal data enters the repository. Key fields: tds (development ID; primary key in B, foreign key in A), revenue_month, meter_number and rate_class (to separate real meters from sewer, fire and un-metered lines), days and consumption_hcf (1 HCF = 748 US gallons), estimated (Y = meter not read: the measurement-gap flag), water_sewer_charges (USD), total_number_of_apartments (B), 311 descriptor and count (C), daily temperature and precipitation (D). The full data dictionary is in docs/04_data_dictionary.md.
4. Acquisition and SQL integration
All four sources were loaded into one SQLite database (data/processed/water.db). Every query is a named block in sql/queries.sql (13 queries plus two views), run from the notebooks.
Tables: bills_raw (as downloaded), bills_clean (after rules C1–C9; foreign key tds), developments (primary key tds), complaints_raw and weather_daily, plus two views that make monthly tables: weather_monthly and complaints_monthly (311 counts per borough-month, grouped into supply, leak and hydrant complaints).
The documented join (q07). A LEFT JOIN keeps every bill; if developments had duplicate TDS numbers, the row count would grow (fan-out).
SELECT (SELECT COUNT(*) FROM bills_clean)             AS rows_before_join,
       COUNT(*)                                       AS rows_after_left_join,
       SUM(CASE WHEN d.tds IS NULL THEN 1 ELSE 0 END) AS unmatched_rows
FROM   bills_clean AS b
LEFT JOIN developments AS d ON d.tds = b.tds;
Check	Result
Rows before / after LEFT JOIN (q07)	28,635 / 28,635 — no fan-out
Unmatched bills (q08)	225 rows (0.79%) from 2 developments: Williamsburg (TDS 1630, 2021 only) and East 4th Street Rehab (2013–14); not in the 2025 Data Book
Development-month panel (q12: two GROUP BY levels + three LEFT JOINs)	8,752 development-months before and after joins (q13); 0 without weather, 0 without 311, 23 without a Data Book match
Other required query types: GROUP BY (q02 bills by borough, q10 complaints by borough-year), WHERE filter (q03 largest actual bills in 2024), GROUP BY … HAVING (q05 duplicate meter-months, q09 developments most often estimated).
5. Data quality and preparation
Nine written rules took 66,432 raw bills to 28,635 clean metered bills. Only impossible or unusable rows were removed; extreme but possible values were kept and flagged, because abnormal consumption is what we are looking for.
Rule	What it does	Rows before	Rows removed	Why
C1	Convert types; fill missing days from service dates	66,432	0	Correct types
C2	Drop exact duplicate rows	66,432	4,660	Would double-count water
C3	Drop rows missing TDS (31), month or consumption (725)	61,772	749	Cannot place in zone or time
C4	Keep the five boroughs	61,023	26,258	"FHA" scattered houses and a non-housing facility are not development zones
C5	Drop accounts with no meter	34,765	2,498	Flat-rate multifamily/commercial accounts: nothing measured
C6	Drop sewer-only and fire-service lines	32,267	2,611	Sewer lines repeat a water meter with zero use
C7	Keep billing periods of 1–62 days	29,656	898	≤ 0 days are errors; > 62 days are quarterly bills that span 3+ months
C8	Drop negative consumption	28,758	0	Reversals, not use
C9	Same meter and period billed twice: keep the actual read	28,758	123	Revised bills
	Clean metered bills		28,635	104 developments
Flags kept, not removed: 5,467 estimated bills (19.1%), 1,469 zero-consumption bills (5.1%) and the extreme bills found by q03 (for example Seward Park Extension and Meltzer Tower in 2024).
Measurement-gap labels. Each development was given a complete month grid (missing months added) and every development-month a label:
Label	Rule	Development-months	Share
actual	Real meter reads	6,396	66.6%
estimated	Half or more of its meters estimated	2,155	22.4%
missing_bill	No bill that month	857	8.9%
zero_read	Every meter read zero	201	2.1%
Metering coverage. 29 developments are metered only at a store or community centre, so their use per apartment is near zero (for example Ravenswood, 2,166 apartments, median 0.0 gal/apt/day). We labelled a development "partial" when its median on actual reads up to 2022 was below 25 gallons per apartment per day. The data shows a clear break: the highest "partial" development is at 16.3 and the next is at 26.5. Per-apartment comparisons and Rule A use only the 70 "whole" developments; 5 have no apartment count.
Every decision, with its row count and risk, is in docs/05_decisions_log.md.
6. Sampling, exploratory analysis and uncertainty
The exploration showed that gaps, not consumption, dominate the reliability picture. Each finding below is written as observation, then uncertainty, then what we can and cannot claim. All ten figures are in reports/figures/; the key ones are reproduced at the end of this section.
Observations
•	Gaps are common and rising (Fig 4). The estimated share of billed development-months fell from 29.6% (2013) to 18.6% (2018), then rose to 36.9% (2024) and 41.2% (Jan–May 2025). Missing bills largely disappear after 2023, but estimates replace them.
•	Recurring gaps are concentrated (Fig 7, q09). Claremont Rehab (Group 2) 95.2% of bills estimated, Ingersoll 95.1%, Van Dyke I 95.1%, Nostrand 92.7%, Ocean Bay (Oceanside) 91.7%, Queensbridge South 91.0%.
•	Typical use (Figs 1–3). The median whole-metered development used 203 gallons per apartment per day, with a long right tail (95th percentile 430). Typical use fell from a median of 238 (2014) to 190 (2024). The number of developments with metered bills fell from about 80 a month (2013) to about 48 (2025), so citywide totals would mislead; we report medians.
•	No weather signal (Fig 5). There is almost no seasonal pattern, and monthly use is not associated with temperature (Pearson r = −0.01).
•	311 (Fig 6). Supply complaints (no water, low pressure, main break) total 99,273 in the five boroughs over 2013 – May 2025. Hydrant complaints (392,853) are four times as many but mostly reflect summer hydrant openings, so they were excluded from the disruption signal.
Uncertainty: cluster bootstrap (Fig 8). Months from the same development are correlated, so we resampled whole developments 2,000 times rather than rows.
Borough	Developments (whole-metered)	Mean gal/apt/day [95% CI]	% gap months [95% CI]
Bronx	28 (20)	290 [232, 357]	29.9 [15.8, 45.2]
Manhattan	34 (25)	231 [185, 281]	33.4 [21.5, 44.8]
Brooklyn	30 (18)	219 [161, 273]	36.7 [23.7, 51.6]
Queens	11 (7)	190 [122, 271]	35.2 [16.2, 58.5]
Staten Island	1 (0)	–	1.5
The Bronx minus Queens difference is 100 gal/apt/day with a 95% CI of [−7, 197]. The interval includes 0, so no borough is clearly different in use or in gap rate. With only 7–25 developments per borough, the intervals are wide.
Sampling. If NYCHA could audit only 25% of developments (26 of 104), how accurate would its estimates be? Over 1,000 repeated draws, the citywide gap rate (true value 33.4%) ranged 22.0–47.2% with simple random sampling and 20.5–44.5% with sampling stratified by borough. The median use per apartment (true value 203) ranged 156–276 and 155–270. Stratification narrows the range only slightly: a sample is enough to track a citywide trend, but not to choose individual developments.
Challenged assumption: "an estimated bill is about as good as a real reading." Rejected. Estimated months change much less from month to month (median 2.7% vs 6.8% for actual reads) and sit lower (median 12.0 vs 26.4 HCF/day). They are carried-forward guesses, not measurements, so they were excluded from the model target and from the features describing past use.
What we cannot claim. These are descriptive associations. The data cannot tell us why the Bronx uses more water per apartment or why estimates are rising (meter failure, access problems or staffing are all possible).
 
Fig 4. Real reads vs measurement gaps by year: the estimated share rises sharply in 2024–2025.
 
Fig 8. Use per apartment (left) and gap rate (right) by borough, with 95% cluster-bootstrap intervals. The intervals overlap.
7. Baseline and candidate methods
We have no record of confirmed leaks, so the method has two layers: first predict each development's expected use for the month, then flag months that are far from expected.
Layer 1: expected use (target = log(1 + HCF per day), actual reads only)
Method	Predicts this month as…
Baseline 1: seasonal naive	Same month last year (standard for monthly utility data)
Baseline 2: persistence	Last actual month (added after EDA showed no seasonality)
Candidate: gradient boosting	Persistence plus a correction learned from season, weather, size, borough, recent history and recent gap months (absolute-error loss, so extreme months do not dominate)
The method used for flagging is the one with the lowest error on the validation year (2022), chosen before looking at the test period.
Layer 2: decision rules
Rule	Flags a development-month when…	Learned from
Rule A (citywide threshold)	Gallons per apartment per day is outside the 5th–95th percentile band of all developments (57–426 gal/apt/day)	Training years, whole-metered developments only
Rule B (development-specific)	Actual minus expected use (log scale) is more than k robust standard deviations from zero; robust = median and MAD, so the outliers we hunt do not inflate the spread	Residuals in the validation year (robust SD = 0.085)
Time-based split, no shuffling: train Jan 2013 – Dec 2021 (7,308 development-months), validation 2022 (731), test Jan 2023 – May 2025 (1,570). A random split would let the model see 2024 to predict 2023.
Leakage controls (checked with assert statements in notebook 03): history features use only earlier months (lag1 is verified to equal the previous month); only actual reads feed the target and history, never estimated values; all training months precede all test months; raw consumption and the target are not features; Rule A percentiles, Rule B's spread and the 311 spike thresholds are learned from training or validation data only. Same-month weather is allowed, as an outside input known when the bill arrives.
8. Validation and evaluation
The persistence forecast does almost all the work, and the development-specific rule beats the citywide threshold on every measure we could check.
Expected-use accuracy (all methods scored on the same development-months; MAE on the log scale, lower is better)
Method	Validation 2022 (n = 501)	Test 2023–25 (n = 955)	Test median % error
Baseline 1: seasonal naive	0.231	0.211	15.0%
Baseline 2: persistence	0.129	0.135	7.4%
Candidate: gradient-boosting correction	0.127	0.133	7.3%
The candidate had the lowest validation error, so it was used for flagging. On test it is 37.0% more accurate than seasonal naive (success measure ≥ 10%: met), but only 1.5% better than persistence. Permutation importance (Fig 9) shows the correction relies mostly on recent history and development size; weather features contribute almost nothing. Honest conclusion: "compare with the last actual reading" is nearly as good and far simpler to run.
Subgroup errors (test, MAE log). Accuracy is best in the Bronx (0.087) and worst in Staten Island (0.233, one development) and among the largest third of developments (0.199 vs 0.096–0.111 for small and medium). Large estates have many meters and more volatile totals, so their flags deserve a second look.
Rule A vs Rule B on the same 691 test development-months (Rule B at the pre-specified |z| > 3)
Rule	Months flagged	Developments flagged	Flags in 311 spike months	Lift vs base rate (7.7%)	Flags in largest third of developments
A: citywide 5th–95th percentile	12.5% (86)	13	19.8%	2.6	34.9%
B: development-specific	8.3% (57)	22	26.3%	3.4	10.5%
The rules agree on only 13% of flagged months (Jaccard). Rule B also scores the 29 partially metered developments, which Rule A cannot.
Sensitivity and operating threshold. As the threshold rises, Rule B flags fewer months and its lift generally rises: |z| > 2 flags 18.1% (lift 1.7), |z| > 3 flags 11.1% (2.5), |z| > 5 flags 5.7% (3.5). Rule A's lift peaks at 3.0 for a 2.5–97.5 percentile band (7.6% flagged). Choosing the threshold on the validation year (smallest k flagging at most 5% of 2022 development-months) gave k = 4.5: 4.4% flagged in 2022 and 6.0% in the test period, with lift 3.35.
Measurement gaps vs real incidents. Scoring every billed test month with Rule B (|z| > 3): actual reads are flagged 10.8% of the time (983 development-months), estimated months 8.8% (510) and zero reads 33.3% (42).
Zero reads are flagged three times as often as real reads: false alarms unless they are recognised as gaps. Estimated months look normal, because the utility builds them from earlier readings, so a real problem during an estimated month is invisible. Both are reasons to label gaps before flagging.
Cost of errors (test period, operating threshold k = 4.5; water and sewer charges of USD 9.64 per HCF from the training years). Rule B raised 24 high-use flags worth USD 387,700 of excess water and sewer charges (USD 125,700 without the single largest flag); the median flag is worth about USD 3,200 in one month. Visiting every flag at an assumed USD 400 per crew visit costs USD 9,600, so inspections pay off if just 2.5% of flags are real problems (7.6% without the largest flag).
A missed leak costs far more than a wasted visit, so the rule can tolerate many false alarms. The largest single flag (Samuel (City), June 2023: 1,030 HCF/day against about 136 expected) and the extreme UPACA (Site 5) bills of April–May 2023 (over 3,000 HCF/day) look more like billing or meter errors than leaks and should be checked by hand before any crew is sent.
Failure cases. The ten largest test errors come from three kinds of situations: one-month spikes that reverse the next month (Taft: 2.8 HCF/day in May 2023, 32.6 in June, 5.0 in July, right after a zero read in April; Samuel (City): 1,030 in June 2023, 140 in July), partially metered sites where small absolute changes are large in percentage terms (Melrose, Rangel, Stapleton), and sudden level shifts on a single meter (Baisley Park: about 1 HCF/day in late 2022, 6.5 in January 2023). One-month spikes that reverse are more likely billing corrections than leaks; a real leak tends to persist until it is fixed.
Priority list: the answer to the decision question (test period, 60 developments with metered bills; Fig 10)
Action	Rule	Developments	Examples
Fix metering first	6+ gap months of 29	28	Ingersoll, Claremont Rehab (Group 4), Lower East Side Rehab (Group 5): gaps in all 29 months
Inspect	3+ abnormal months	8	Rehab Program (College Point) 7; Rangel 5; Taft, Marlboro, Melrose 4
Monitor	Neither	24	Shelton House, Baisley Park, Samuel (City)
Seven of the eight "inspect" developments are partially metered (all except Rehab Program (College Point)), so their flags concern a store or community-centre meter rather than the whole estate.
 
Fig 10. Each dot is a development (test period, 29 months). Right of the orange line: fix metering first. Above the red line: inspect.
9. Ethics, bias and limitations
Ethical risks and safeguards
•	Blaming residents of low-income housing for high use: flags are framed as infrastructure and metering problems; no tenant data is used.
•	311 reporting bias (some areas report more): 311 is used only as weak, borough-level corroboration, never as the target.
•	Unfair prioritisation: flag rates and errors are reported by borough and size; Rule B puts fewer flags on large estates than Rule A (10.5% vs 34.9%).
•	Over-confidence in flags: confidence intervals, sensitivity analysis and failure cases are reported, and a person checks every flag before a crew is sent.
•	Privacy: only aggregate 311 counts were downloaded; no addresses or names are in the repository.
•	Excluded residents: "FHA" scattered houses (43% of raw rows) are out of scope, so these findings do not cover them.
Limitations
•	No ground truth: without inspection or repair records we cannot measure how many flags are real (precision) or how many leaks were missed (recall).
•	Coarse corroboration: a 311 spike in a borough says little about one development; weather comes from one point (Central Park).
•	Coverage: 29 of 104 developments are only partly metered, about 50 a month have metered bills by 2025, and 898 quarterly bills were dropped; borough intervals are wide.
•	Snapshot attributes: apartment counts come from the 1 January 2025 Data Book and are assumed constant since 2013.
•	Generalisation: results describe NYCHA in New York; the method transfers to a utility such as Nairobi's only with metered bills that record reading status, zone sizes and incident logs.
10. Proposed randomised experiment (design only)
We propose to test whether proactive inspection of flagged developments reduces excess water use. Among developments flagged "inspect", half would be chosen at random for an inspection within 14 days; the other half would follow the normal complaint-driven process.
Element	Design
Hypothesis	H0: proactive inspection does not change excess use over 6 months; H1: it reduces it
Unit and population	Development (one visit affects the whole estate); whole-metered developments flagged by Rule B with actual reads in the flag month
Treatment / control	Inspection within 14 days / business as usual; control developments still get every repair they request
Randomisation	1:1 within borough × size-third strata, seeded, recorded before outcomes are seen
Outcomes	Primary: mean residual over 6 months (log of actual ÷ expected, actual reads only). Secondary: repeat flags, estimated-read share, 311 supply complaints, cost
Analysis	Intention-to-treat difference in means with a cluster-bootstrap 95% CI, plan registered in advance
Sample size. The 6-month mean residual varies across developments with standard deviation 0.177 (Jan–Jun 2023). With 80% power and α = 0.05 (two-sided), n per arm = 2(z₀.₉₇₅ + z₀.₈₀)²σ²/δ² gives 45 developments per arm (90 in total) to detect a 10% reduction in use, 19 per arm (38) for 15%, and 10 per arm (20) for 20%.
Only 44 developments had metered actual reads in January–June 2023, so a 10% effect is not detectable with today's metered portfolio. Options: target a 20% effect, enrol cohorts over 6–12 months, or extend metering first (Recommendation 1).
Confounders and threats. Seasonality (balanced by randomising within the same calendar months); regression to the mean (a development flagged in an unusually bad month tends to look better next month even without action — exactly why a control group is needed); capital works or conversion to private management during follow-up; meter replacement changing what is measured; spillover between neighbouring developments on shared mains (randomise them together); crews knowing the assignment (keep the analyst blind).
Ethical safeguards. No resident is denied service: emergency and complaint-driven repairs continue in the control group. No tenant data, no penalties for residents, results shared with residents' associations, a stop rule if inspection proves clearly beneficial (then offer it to all), and approval by NYCHA and an ethics committee before starting.
11. Recommendations and monitoring plan
1.	Restore meter reading before judging consumption (NYCHA utilities with the meter vendor, next 6 months). Start with the 12 developments estimated or missing in 27–29 of the last 29 months: Ingersoll, Lower East Side Rehab (Group 5), Claremont Rehab (Groups 2 and 4), Queensbridge South, Van Dyke I, Drew-Hamilton, International Tower, Ocean Bay (Oceanside), Lower East Side I Infill, UPACA (Site 5) and 154 West 84th Street. Success: estimated share of billed months back under 20% (it was 18.6% in 2018 and 36.9% in 2024).
2.	Inspect the 8 developments with recurring abnormal use (maintenance crews, next 3 months): Rehab Program (College Point), Rangel, Taft, Marlboro, Melrose, Stapleton, Smith and Whitman. Check billing records first for one-month spikes that reverse. Success: excess use over the following 6 months, and the share of inspections that find a real problem.
3.	Adopt Rule B with a z-score threshold of 4.5 as the monthly screen, applied after gap labelling (NYCHA data team, monthly). Review the threshold each quarter against crew capacity. Success: 5–6% of development-months flagged, and an inspection hit rate above the 2.5–7.6% break-even.
4.	Meter the whole estate at the 29 developments where only a store or community centre is metered (capital planning), so use can be compared per apartment.
5.	Run the randomised test in Section 10 before scaling proactive inspection citywide, once Recommendation 1 has raised metered coverage.
Monthly monitoring plan
•	Share of estimated, missing and zero bills, citywide and per development (measurement health). Review if it rises 3 months in a row, or a development is estimated 6+ months running.
•	Monthly flag count against crew capacity (workload). Review if it exceeds capacity for 2 months.
•	Share of inspections that find a real problem (precision). Review if it falls below the break-even share.
•	Forecast error on the latest month against the test MAE of 0.133 (model drift). Review if it is 25% worse.
•	Flag rate by borough and size (fairness). Review if one group is flagged far more with no problems found.
12. References and AI-use declaration
Data (all accessed 16 November 2026)
1.	New York City Housing Authority. Water Consumption And Cost (2013 – May 2025). NYC Open Data, dataset 66be-66yr. https://data.cityofnewyork.us/d/66be-66yr. NYC Open Data Terms of Use.
2.	New York City Housing Authority. NYCHA Development Data Book (as of 1 January 2025). NYC Open Data, dataset evjd-dqpz. https://data.cityofnewyork.us/d/evjd-dqpz. NYC Open Data Terms of Use.
3.	NYC 311 / Office of Technology and Innovation. 311 Service Requests from 2010 to 2019 (76ig-c548) and 311 Service Requests from 2020 to Present (erm2-nwe9). https://data.cityofnewyork.us/d/76ig-c548, https://data.cityofnewyork.us/d/erm2-nwe9. NYC Open Data Terms of Use.
4.	Open-Meteo. Historical Weather API (ERA5 reanalysis, ECMWF/Copernicus). https://open-meteo.com/en/docs/historical-weather-api. CC BY 4.0 — weather data by Open-Meteo.com.
5.	NYC Open Data. 311 Service Requests updates (dataset split, December 2025). https://opendata.cityofnewyork.us/311-service-requests-from-2010-to-present-updates/
Software: Python 3, pandas, NumPy, SciPy, scikit-learn (HistGradientBoostingRegressor, permutation importance), matplotlib, seaborn, SQLite, Jupyter.
AI-use declaration. We used an AI assistant (Claude, by Anthropic) to draft the starter code, SQL query structure and document templates, to explain methods, and to help draft this report. Every figure, number and statement in this report comes from our own run of the notebooks on the downloaded data; we verified it by re-running the notebooks from a fresh clone, reading every SQL query, checking row counts against the portal, and matching each number in the report to a notebook output. Interpretations and recommendations are the group's own.
13. Contribution statement
Member (ID)	Role	Main contributions	Report sections
Sylvain Biket (674139)	Data and SQL lead	Download script, SQLite database, SQL queries, cleaning rules, join validation, decisions log	3, 4, 5
Victor Apamo (673804)	EDA and uncertainty lead	Figures 1–8, subgroup tables, cluster bootstrap, sampling check, interim memo	6, 9
Whitney Jebor (673308)	Modelling and evaluation lead	Baselines, candidate, leakage checks, rule comparison, sensitivity, cost, priority list, experiment design	7, 8, 10
All	Shared	Executive summary, recommendations, slides, fresh-clone test, review of each other's notebooks	1, 2, 11, 12
GitHub Link  https://github.com/sylvainenzo/DSA2050-END-PROJECT
<img width="468" height="651" alt="image" src="https://github.com/user-attachments/assets/1028b231-6c3b-444e-a76a-8528b4313f25" />
