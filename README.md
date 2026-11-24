# Water Supply Reliability Monitoring — NYCHA developments

**DSA 2050 · Data Science Methodology · Five-week group project · Option 06**
USIU-Africa · School of Science and Technology

## Decision problem
**Stakeholder:** NYCHA water/utilities management team (with NYC DEP for supply incidents).
**Decision:** each month, which developments should get a crew visit — a **meter repair** (recurring measurement gaps) or a **leak / supply inspection** (recurring abnormal consumption)?
**Decision question:** *Which zones show recurring disruption or abnormal consumption?*
**Unit of analysis:** development-month (zone = NYCHA development; higher-level zone = borough).

## Results at a glance (run of 16 Nov 2026)
- 66,432 raw bills → 28,635 clean metered bills from 104 developments (9,609 development-months, Jan 2013 – May 2025).
- **One development-month in three is a measurement gap** (22.4% estimated, 8.9% missing, 2.1% zero read). Estimated share of billed months: 18.6% (2018) → 41.2% (Jan–May 2025).
- Persistence (last actual month) beats seasonal naive by 36%; the gradient-boosting candidate adds 1.5% on top (test MAE log 0.133 vs 0.135 vs 0.211).
- Rule B (development-specific) vs Rule A (citywide band), same 691 test months: 8.3% vs 12.5% flagged, lift vs 311 supply spikes 3.4× vs 2.6×.
- Operating threshold |z| > 4.5, chosen on 2022: **28 developments to fix metering, 8 to inspect, 24 to monitor** (`reports/priority_list.csv`).

## Data provenance
| Source | Producer | Format | Link |
|---|---|---|---|
| A. Water Consumption And Cost (2013 – May 2025) | NYCHA via NYC Open Data (66be-66yr) | CSV | https://data.cityofnewyork.us/d/66be-66yr |
| B. NYCHA Development Data Book | NYCHA via NYC Open Data (evjd-dqpz) | CSV | https://data.cityofnewyork.us/d/evjd-dqpz |
| C. 311 Service Requests, "Water System" (counts only) | NYC 311 / OTI via NYC Open Data (76ig-c548 for 2010–2019 + erm2-nwe9 for 2020–present) | JSON API | https://data.cityofnewyork.us/d/76ig-c548 + https://data.cityofnewyork.us/d/erm2-nwe9 |
| D. Historical daily weather, Central Park | Open-Meteo (ERA5), CC BY 4.0 | JSON API | https://open-meteo.com/en/docs/historical-weather-api |

Terms: A–C under the NYC Open Data Terms of Use; D under CC BY 4.0 ("Weather data by Open-Meteo.com"). See `data/README.md`.

## Setup (once)
```bash
git clone <your-repo-url>
cd dsa2050-water-reliability
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Steps to reproduce
1. `python src/download_data.py` — downloads A–D into `data/raw/` and writes `data/raw_manifest.csv` (or let notebook 01 do it).
2. Open Jupyter (`jupyter lab`) and run, in order, with **Restart & Run All**:
   1. `notebooks/01_acquisition_quality.ipynb` → SQLite DB, quality audit, cleaning, joined panel
   2. `notebooks/02_eda_sampling.ipynb` → charts, subgroups, bootstrap CIs, stratified sample
   3. `notebooks/03_baseline_evaluation.ipynb` → baseline vs candidate, rules A vs B, sensitivity, priority list
3. Outputs: tables in `reports/`, figures in `reports/figures/`.

SQL lives in `sql/queries.sql` (named blocks run by the notebooks; also runnable in DB Browser for SQLite).

## Repository structure
```
README.md               this file
data/README.md          sources, licences, how to get the data
data/raw/               downloaded files (git-ignored)
data/processed/         SQLite DB + panel (git-ignored)
data/sample/            15-row previews (committed)
notebooks/              01_acquisition_quality, 02_eda_sampling, 03_baseline_evaluation
sql/queries.sql         all SQL (row counts, GROUP BY, filters, JOIN validation, panel)
src/                    download_data.py, water_utils.py (reusable functions)
docs/                   charter, source register, work plan, data dictionary, decisions log,
                        interim memo, A/B-test protocol, report & slide outlines
reports/                final_report.pdf + result tables + figures/
slides/                 presentation.pdf
requirements.txt, .gitignore, CONTRIBUTIONS.md
```

## Roles
| Member | Role | Main files |
|---|---|---|
| ENZO | Data & SQL lead | `src/download_data.py`, `sql/queries.sql`, notebook 01 |
| Victor | EDA & uncertainty lead | notebook 02, figures, interim memo |
| Whitney| Modelling & evaluation lead | notebook 03, A/B-test protocol |
| All | Report, slides, decisions log, review of each other's notebooks | `docs/`, `reports/`, `slides/` |


