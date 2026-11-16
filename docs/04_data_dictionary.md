# Data Dictionary

Notebook 01 writes a draft to `docs/data_dictionary_generated.csv` (types, % non-null, examples). Copy it here and complete the "Meaning" and "Valid range / rule" columns.

## Source tables
| Table | Column | Type | Meaning | Unit | Valid range / rule | Key |
|---|---|---|---|---|---|---|
| bills_clean | tds | integer | NYCHA development ID | – | > 0 | FK → developments.tds |
| bills_clean | revenue_month | text | Bill month | YYYY-MM | 2013-01 … 2025-05 | join to weather/311 |
| bills_clean | borough | text | Borough | – | 5 boroughs only (C4) | join to 311 |
| bills_clean | meter_number | text | Meter ID | – | not null, not UN-METERED (C5) | |
| bills_clean | days | number | Days in billing period | days | 1–62 (C6) | |
| bills_clean | estimated | text | Meter not read, value estimated | Y/N | Y or N | |
| bills_clean | consumption_hcf | number | Water used | HCF (748 gal) | ≥ 0 (C7) | |
| bills_clean | water_sewer_charges | number | Water + sewer cost | USD | ≥ 0 | |
| developments | tds | integer | Development ID | – | unique | PK |
| developments | apartments | integer | Total apartments | count | > 0 | |
| developments | population | integer | Total residents | people | ≥ 0 | |
| weather_monthly | temp_mean / precip_mm / freeze_days / hot_days | number | Monthly weather | °C / mm / days | | PK month |
| complaints_monthly | complaints_total, c_supply, c_no_water, c_low_pressure, c_main_break, c_leak, c_hydrant | integer | 311 Water System complaints; c_supply = no water + low pressure + main break | count | ≥ 0 | PK borough+month |

## Derived (panel_labeled)
| Column | Meaning | Formula |
|---|---|---|
| hcf_per_day | Development water use per day | Σ over meters of HCF ÷ days |
| gal_per_apt_day | Gallons per apartment per day | hcf_per_day × 748 ÷ apartments |
| share_estimated | Share of meters estimated | n_est_meters ÷ n_meters |
| gap_type | Reading quality label | missing_bill / estimated (≥50% meters) / zero_read / actual |
| y | Model target | log(1 + hcf_per_day), actual months only |
| lag1, lag12, roll3_mean, roll12_median | Past use | from earlier actual months only |
| metering | Meter coverage of the development | whole / partial (median < 25 gal/apt/day on actual reads up to 2022: meter covers only a store or community centre) / unknown (no apartment count) |
| pred_base / pred_pers / pred_cand | Expected use (log scale) | seasonal naive / persistence / gradient-boosting correction to persistence |
| resid | Actual − expected (log scale) | y − pred_best (method chosen on validation) |
| spike_311 | Borough-month 311 supply-complaint spike | robust z of c_supply > 2, centre/spread from training years |
| flag_A / flag_B | Anomaly flag | +1 high, −1 low, 0 normal |
