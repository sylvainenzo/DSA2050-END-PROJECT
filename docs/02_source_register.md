# Dataset / Source Register (Week 1)

Fill "Checked on", "Rows" and "Columns" from your own download (`data/raw_manifest.csv`).

| ID | Dataset | Original producer | Platform / link | Format | Licence / terms | Time coverage | Granularity | Rows | Columns | Fields we use | Permission checked (who, date) | Known issues |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | Water Consumption And Cost (2013 – May 2025) | NYCHA | NYC Open Data 66be-66yr — https://data.cityofnewyork.us/d/66be-66yr | CSV | NYC Open Data Terms of Use | 2013-01 to 2025-05 | Meter × bill | 66,432 | 25 | tds, borough, development_name, meter_number, meter_amr, revenue_month, service dates, days, estimated, consumption_hcf, charges | | "FHA" in borough; un-metered rows; estimated reads; multiple bills per month |
| B | NYCHA Development Data Book | NYCHA | NYC Open Data evjd-dqpz — https://data.cityofnewyork.us/d/evjd-dqpz | CSV | NYC Open Data Terms of Use | Snapshot as of 1 Jan 2025 | Development | 346 (341 with a TDS #) | 52 | TDS #, development, borough, apartments, population, residential buildings | | Snapshot: converted/demolished developments missing |
| C | 311 Service Requests — "Water System" | NYC 311 / OTI (routes to DEP) | NYC Open Data 76ig-c548 (2010–19) + erm2-nwe9 (2020–) (SODA API, aggregated query) | JSON | NYC Open Data Terms of Use | 2013-01 to 2025-05 | Borough × month × descriptor (counts) | 11,252 (6,551 for 2013–19 + 4,701 for 2020–25) | 4 | borough, month, descriptor, n | | Reporting bias; borough-level only; "Unspecified" borough |
| D | Historical daily weather, Central Park | Open-Meteo (ERA5, ECMWF/Copernicus) | archive-api.open-meteo.com | JSON | CC BY 4.0 | 2013-01-01 to 2025-05-31 | Day | 4,534 | 6 | temperature mean/max/min, precipitation, snowfall | | Reanalysis grid, one point for whole city |

**Minimum requirements check:** ≥ 10,000 records (A: 66,432 raw; 28,635 clean bills) ☑ · ≥ 8 meaningful fields (25) ☑ · ≥ 2 sources/formats (2 CSV + 2 JSON) ☑ · ≥ 1 documented SQL join with row-count validation (A→B: 28,635 rows before and after the LEFT JOIN; 225 rows / 2 developments unmatched) ☑

Downloaded 16 Nov 2026. SHA-256 hashes in `data/raw_manifest.csv`. Note: NYC split the 311 dataset in December 2025 into 2010–2019 (76ig-c548) and 2020–present (erm2-nwe9); we query both.
