# Individual Contributions

DSA 2050 · Five-Week Applied Data Science Methodology Project · Option 06: Water Supply Reliability Monitoring

| Member | Role | What I did | Main files | Weeks |
|---|---|---|---|---|
| Enzo | Data & SQL lead | Downloaded the four datasets, built the SQLite database, wrote and checked the SQL queries (including the join validation), applied the cleaning rules C1–C9, kept the decisions log | `src/download_data.py`, `sql/queries.sql`, `notebooks/01_acquisition_quality.ipynb`, `docs/05_decisions_log.md`, `data/README.md` | 1–2 |
| Victor | EDA & uncertainty lead | Produced and annotated Figures 1–8, the borough comparisons, the cluster bootstrap confidence intervals and the sampling check; wrote the interim memo | `notebooks/02_eda_sampling.ipynb`, `reports/figures/`, `docs/06_interim_memo.md` | 3 |
| Whitney | Modelling & evaluation lead | Built the baselines and the candidate model, ran the leakage checks, compared Rule A and Rule B, ran the sensitivity and cost analysis, built the priority list and designed the A/B test | `notebooks/03_baseline_evaluation.ipynb`, `docs/07_ab_test_protocol.md` | 4 |

## Shared work
- **Charter, source register and work plan (Week 1):** Enzo, Victor, Whitney
- **Final report:** Enzo wrote sections 3–5, Victor sections 6 and 9, Whitney sections 7, 8 and 10; all three wrote sections 1, 2, 11 and 12
- **Slides and presentation:** Enzo presents slides 1–3, Victor slides 4, 5 and 9, Whitney slides 6–8; all three present slide 10
- **Reproducibility check:** each member ran all three notebooks from a fresh copy of the repository and confirmed the numbers match the report


