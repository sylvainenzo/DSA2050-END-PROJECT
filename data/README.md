# Data

Raw and processed data are **not committed** (see `.gitignore`). Anyone can rebuild them with `python src/download_data.py`. Only 15-row previews are committed in `data/sample/`.

| File in data/raw/ | Source | Producer | Access | Licence / terms |
|---|---|---|---|---|
| `water_bills.csv` | Water Consumption And Cost (2013 – May 2025), id 66be-66yr — https://data.cityofnewyork.us/d/66be-66yr | New York City Housing Authority (NYCHA) | Public, no account (SODA API) | NYC Open Data Terms of Use; cite NYCHA |
| `development_data_book.csv` | NYCHA Development Data Book, id evjd-dqpz — https://data.cityofnewyork.us/d/evjd-dqpz | NYCHA | Public, no account | NYC Open Data Terms of Use; cite NYCHA |
| `complaints_311_water_system.json` | 311 Service Requests, ids 76ig-c548 (2010–2019) and erm2-nwe9 (2020–present), filtered to complaint type "Water System", **aggregated to counts by borough, month and descriptor** | NYC 311 / Office of Technology and Innovation | Public SODA API | NYC Open Data Terms of Use |
| `weather_nyc_daily.json` | Open-Meteo Historical Weather API (ERA5 reanalysis), lat 40.7829, lon −73.9654, 2013-01-01 to 2025-05-31 | Open-Meteo | Public API, no key | CC BY 4.0 — "Weather data by Open-Meteo.com" |

Exact request URLs, row counts, sizes, SHA-256 hashes and download times are in `data/raw_manifest.csv` (created by the download script).

**Privacy:** dataset A is at development/meter level with no tenant data. For 311 we download only counts, never addresses or free-text, so no personal identifiers enter this repository.

**Coverage notes:** A ends May 2025 (last updated October 2025). B is a current snapshot, so developments converted to PACT/RAD or demolished earlier may be missing (they appear as unmatched keys in the join check).
