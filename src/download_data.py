"""
Download the four raw sources for the DSA 2050 water-reliability project.

Run from the repository root:
    python src/download_data.py

Files land in data/raw/ (git-ignored) and a manifest with row counts,
file sizes, SHA-256 hashes and download time is written to
data/raw_manifest.csv. That manifest is your Week 2 "raw-data manifest".

Sources
  A  NYCHA Water Consumption And Cost (2013 - May 2025)  NYC Open Data 66be-66yr  (CSV)
  B  NYCHA Development Data Book                          NYC Open Data evjd-dqpz  (CSV)
  C  311 Service Requests, complaint type "Water System"  NYC Open Data 76ig-c548 (2010-19) + erm2-nwe9 (2020-)  (JSON, counts only)
  D  Open-Meteo historical daily weather, New York City   archive-api.open-meteo.com (JSON)
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

START, END = "2013-01-01", "2025-05-31"   # dataset A covers 2013 to May 2025

SOURCES = {
    "water_bills.csv": {
        "label": "A - NYCHA Water Consumption And Cost (66be-66yr)",
        # SODA resource endpoint returns API column names (snake_case)
        "url": "https://data.cityofnewyork.us/resource/66be-66yr.csv",
        "params": {"$limit": 5_000_000},
    },
    "development_data_book.csv": {
        "label": "B - NYCHA Development Data Book (evjd-dqpz)",
        "url": "https://data.cityofnewyork.us/resource/evjd-dqpz.csv",
        "params": {"$limit": 50_000},
    },
    "weather_nyc_daily.json": {
        "label": "D - Open-Meteo historical daily weather, Central Park NYC (CC BY 4.0)",
        "url": "https://archive-api.open-meteo.com/v1/archive",
        "params": {
            "latitude": 40.7829,
            "longitude": -73.9654,
            "start_date": START,
            "end_date": END,
            "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum",
            "timezone": "America/New_York",
        },
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: Path) -> int:
    if path.suffix == ".csv":
        return len(pd.read_csv(path, low_memory=False))
    data = json.loads(path.read_text())
    if isinstance(data, list):              # 311 API returns a list of records
        return len(data)
    return len(data.get("daily", {}).get("time", []))   # Open-Meteo


def download(name: str, spec: dict, force: bool = False) -> dict:
    out = RAW / name
    if out.exists() and not force:
        print(f"[skip] {name} already exists (use force=True to re-download)")
    else:
        print(f"[get ] {spec['label']}")
        r = requests.get(spec["url"], params=spec["params"], timeout=600)
        r.raise_for_status()
        out.write_bytes(r.content)
    return {
        "file": f"data/raw/{name}",
        "source": spec["label"],
        "request_url": requests.Request("GET", spec["url"], params=spec["params"]).prepare().url,
        "rows": count_rows(out),
        "bytes": out.stat().st_size,
        "sha256": sha256(out),
        "downloaded_utc": datetime.fromtimestamp(out.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
    }


# C - 311 "Water System" complaints. NYC split 311 in Dec 2025:
#     76ig-c548 = 2010-2019, erm2-nwe9 = 2020-present. We query both and combine.
#     Aggregated on the server: counts only, no addresses or personal details.
C311_PARTS = [("76ig-c548", START, "2019-12-31"), ("erm2-nwe9", "2020-01-01", END)]


def download_311(force: bool = False) -> dict:
    name = "complaints_311_water_system.json"
    out = RAW / name
    urls = []
    if out.exists() and not force:
        print(f"[skip] {name} already exists")
    else:
        rows = []
        for ds, start, end in C311_PARTS:
            url = f"https://data.cityofnewyork.us/resource/{ds}.json"
            q = {"$select": "borough, date_trunc_ym(created_date) AS ym, descriptor, count(*) AS n",
                 "$where": (f"complaint_type = 'Water System' AND created_date between "
                            f"'{start}T00:00:00' and '{end}T23:59:59'"),
                 "$group": "borough, date_trunc_ym(created_date), descriptor",
                 "$limit": 500_000}
            print(f"[get ] C - 311 Water System counts from {ds}")
            r = requests.get(url, params=q, timeout=1200)
            r.raise_for_status()
            rows += [{"borough": x.get("borough"), "month": x["ym"],
                      "descriptor": x.get("descriptor"), "n": x["n"]} for x in r.json()]
        out.write_text(json.dumps(rows))
    for ds, _, _ in C311_PARTS:
        urls.append(f"https://data.cityofnewyork.us/resource/{ds}.json")
    return {"file": f"data/raw/{name}",
            "source": "C - 311 Water System complaints, counts by borough/month/descriptor (76ig-c548 + erm2-nwe9)",
            "request_url": " + ".join(urls), "rows": count_rows(out), "bytes": out.stat().st_size,
            "sha256": sha256(out),
            "downloaded_utc": datetime.fromtimestamp(out.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")}


def main(force: bool = False) -> pd.DataFrame:
    rows = [download(n, s, force) for n, s in SOURCES.items()]
    rows.insert(2, download_311(force))
    manifest = pd.DataFrame(rows)
    manifest.to_csv(ROOT / "data" / "raw_manifest.csv", index=False)
    print(manifest[["file", "rows", "bytes"]].to_string(index=False))
    return manifest


if __name__ == "__main__":
    main()
