"""
Reusable functions for the DSA 2050 water-reliability project.

Every notebook imports from here, so one fix updates the whole pipeline.
Sections:
  1. Paths and loading raw files
  2. SQLite helpers (run named queries from sql/queries.sql)
  3. Cleaning rules (with a before/after log)
  4. Development-month panel: gap labels and leakage-safe features
  5. Models: seasonal-naive baseline and gradient-boosting candidate
  6. Anomaly rules, corroboration with 311, cost of errors
  7. Bootstrap confidence intervals
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "reports" / "figures"
DB_PATH = PROCESSED / "water.db"
SQL_FILE = ROOT / "sql" / "queries.sql"

BOROUGHS = ["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"]
GALLONS_PER_HCF = 748  # 1 hundred cubic feet = 748 US gallons

# Evaluation periods (time-based split; never shuffle time-series rows)
TRAIN_END = "2021-12"
VALID_START, VALID_END = "2022-01", "2022-12"
TEST_START = "2023-01"

for _p in (PROCESSED, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Loading raw files
# ---------------------------------------------------------------------------
def snake(name: str) -> str:
    """'TOTAL NUMBER OF APARTMENTS' -> 'total_number_of_apartments'."""
    return re.sub(r"[^0-9a-z]+", "_", str(name).strip().lower()).strip("_")


def load_raw() -> dict[str, pd.DataFrame]:
    """Read the four raw files exactly as downloaded (no cleaning)."""
    bills = pd.read_csv(RAW / "water_bills.csv", low_memory=False, dtype=str)
    bills.columns = [snake(c) for c in bills.columns]

    devbook = pd.read_csv(RAW / "development_data_book.csv", low_memory=False, dtype=str)
    devbook.columns = [snake(c) for c in devbook.columns]

    c311 = pd.DataFrame(json.loads((RAW / "complaints_311_water_system.json").read_text()))
    c311["n"] = pd.to_numeric(c311["n"], errors="coerce")

    w = json.loads((RAW / "weather_nyc_daily.json").read_text())["daily"]
    weather = pd.DataFrame(w).rename(columns={"time": "date"})

    return {"bills_raw": bills, "devbook_raw": devbook,
            "complaints_raw": c311, "weather_daily": weather}


def _find_col(cols, must, avoid=()):
    """First column whose name contains every word in `must` and none in `avoid`."""
    for c in cols:
        if all(m in c for m in must) and not any(a in c for a in avoid):
            return c
    return None


def standardise_devbook(db: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Pick the columns we need from the Development Data Book and give them fixed
    names. Column names in the portal can change between releases, so we search
    for them and REPORT what was matched. Check the printed mapping in Week 2.
    """
    cols = list(db.columns)
    mapping = {
        "tds": next((c for c in cols if c in ("tds", "tds_", "tds_number", "tds_num")), None)
               or _find_col(cols, ["tds"], avoid=["consolidated"]),
        "development": _find_col(cols, ["development"], avoid=["edp", "date", "type"]),
        "borough": _find_col(cols, ["borough"]),
        "apartments": _find_col(cols, ["total", "apartments"]) or _find_col(cols, ["current", "apartments"])
                      or _find_col(cols, ["units"], avoid=["section"]),
        "population": _find_col(cols, ["total", "population"]) or _find_col(cols, ["population"], avoid=["section"]),
        "res_buildings": _find_col(cols, ["residential", "buildings"], avoid=["non"])
                         or _find_col(cols, ["residential", "bldgs"], avoid=["non"]),
    }
    missing = [k for k, v in mapping.items() if v is None and k in ("tds", "apartments")]
    if missing:
        raise KeyError(f"Could not find {missing} in Development Data Book columns: {cols}")

    out = pd.DataFrame({k: db[v] if v else np.nan for k, v in mapping.items()})
    out["tds"] = pd.to_numeric(out["tds"].astype(str).str.strip(), errors="coerce")
    for c in ("apartments", "population", "res_buildings"):
        out[c] = pd.to_numeric(out[c].astype(str).str.replace(",", "").str.strip(), errors="coerce")
    out["borough"] = out["borough"].astype(str).str.strip().str.upper()
    n_before = len(out)
    out = out.dropna(subset=["tds"])
    n_no_key = n_before - len(out)
    n_dup = int(out.duplicated("tds").sum())
    out = out.drop_duplicates("tds", keep="first")
    out["tds"] = out["tds"].astype(int)
    info = {"column_mapping": mapping, "rows_in": n_before,
            "rows_without_tds": n_no_key, "duplicate_tds_dropped": n_dup, "rows_out": len(out)}
    return out, info


# ---------------------------------------------------------------------------
# 2. SQLite helpers
# ---------------------------------------------------------------------------
def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(path)


def write_tables(con: sqlite3.Connection, tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Write DataFrames to SQLite (replacing) and return a table of row counts."""
    rows = []
    for name, df in tables.items():
        df.to_sql(name, con, if_exists="replace", index=False)
        rows.append({"table": name, "rows": len(df), "columns": df.shape[1]})
    return pd.DataFrame(rows)


def load_queries(path: Path = SQL_FILE) -> dict[str, str]:
    """
    Split sql/queries.sql into named blocks. A block starts with a line
    '-- name: <query_name>' and runs until the next such line.
    """
    text = path.read_text()
    parts = re.split(r"^--\s*name:\s*(\S+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def run(con: sqlite3.Connection, name: str, queries: dict[str, str] | None = None):
    """Run one named block. SELECT blocks return a DataFrame; DDL blocks return None."""
    queries = queries or load_queries()
    sql = queries[name]
    if re.match(r"^\s*(CREATE|DROP|INSERT|UPDATE|DELETE)", re.sub(r"--[^\n]*\n", "", sql), flags=re.I):
        con.executescript(sql)
        con.commit()
        return None
    return pd.read_sql_query(sql, con)


# ---------------------------------------------------------------------------
# 3. Cleaning rules (each rule logs rows before/after and the reason)
# ---------------------------------------------------------------------------
class CleaningLog:
    def __init__(self):
        self.rows = []

    def step(self, rule: str, before: int, after: int, reason: str):
        self.rows.append({"rule": rule, "rows_before": before, "rows_after": after,
                          "rows_removed": before - after, "reason": reason})

    def table(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def clean_bills(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply cleaning rules C1-C9 to the raw bills. Returns (clean, log)."""
    log = CleaningLog()
    df = raw.copy()
    n = len(df)

    # C1 - types and standard text (no rows removed)
    num_cols = ["tds", "days", "consumption_hcf", "current_charges",
                "water_sewer_charges", "other_charges"]
    for c in num_cols:
        if c in df:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce")
    for c in ("service_start_date", "service_end_date"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["revenue_month"] = df["revenue_month"].astype(str).str.strip().str[:7]
    df.loc[~df["revenue_month"].str.match(r"^\d{4}-\d{2}$", na=False), "revenue_month"] = np.nan
    for c in ("borough", "estimated", "meter_number", "meter_amr", "rate_class"):
        df[c] = df[c].astype(str).str.strip().str.upper().replace({"NAN": np.nan, "": np.nan})
    # days missing -> recompute from service dates
    calc = (df["service_end_date"] - df["service_start_date"]).dt.days
    df["days_filled_from_dates"] = df["days"].isna() & calc.notna()
    df["days"] = df["days"].fillna(calc)
    log.step("C1 standardise types", n, len(df), "Convert numbers/dates, upper-case text, fill missing days from service dates")

    # C2 - exact duplicate rows
    n = len(df); df = df.drop_duplicates()
    log.step("C2 drop exact duplicates", n, len(df), "Identical rows add no information and double-count water")

    # C3 - rows that cannot be placed in time or zone, or have no measurement
    n = len(df); df = df.dropna(subset=["revenue_month", "tds", "consumption_hcf"])
    log.step("C3 drop missing key fields", n, len(df), "No month, no development ID or no consumption value")

    # C4 - keep the five boroughs (removes 'FHA' scattered houses)
    n = len(df); df = df[df["borough"].isin(BOROUGHS)]
    log.step("C4 keep five boroughs", n, len(df), "'FHA' repossessed houses are scattered homes, not a development zone")

    # C5 - no meter to read: meter number missing or "UN-METERED"
    n = len(df)
    mn = df["meter_number"].fillna("")
    no_meter = (mn == "") | mn.str.contains("UN-METER", na=False)
    df = df[~no_meter]
    log.step("C5 drop accounts with no meter", n, len(df), "Flat-rate / multifamily / commercial accounts with no meter: consumption is not measured")

    # C6 - lines that are charges, not water use: sewer-only lines and fire-service lines
    n = len(df)
    mn = df["meter_number"].fillna("")
    non_use = (mn.str.contains("SEWER", na=False) | mn.str.contains("FIRE", na=False)
               | df["rate_class"].fillna("").str.upper().isin(["MWW SWR", "FIRE", "FRONTAGEWW"]))
    df = df[~non_use]
    log.step("C6 drop sewer-only and fire-service lines", n, len(df), "Sewer charge lines repeat a water meter with zero use; fire lines are not consumption")

    # C7 - impossible billing periods
    n = len(df); df = df[(df["days"] > 0) & (df["days"] <= 62)]
    log.step("C7 drop invalid billing periods", n, len(df), "<=0 days are errors; >62 days are quarterly/catch-up bills spanning 3+ months that cannot be placed in one month")

    # C8 - negative consumption = billing reversal, not water use
    n = len(df); df = df[df["consumption_hcf"] >= 0]
    log.step("C8 drop negative consumption", n, len(df), "Credits/reversals are accounting entries, not water use")

    # C9 - duplicate bill for the same meter and same period: keep the actual read
    n = len(df)
    key = ["tds", "meter_number", "revenue_month", "service_start_date", "service_end_date"]
    df = (df.assign(_est_order=(df["estimated"] == "Y").astype(int))
            .sort_values(key + ["_est_order"])
            .drop_duplicates(key, keep="first")
            .drop(columns="_est_order"))
    log.step("C9 de-duplicate meter-period bills", n, len(df), "Same meter and period billed twice: keep actual read over estimate")

    # Flags only (NO rows removed): we keep extreme values because they are the signal
    df["tds"] = df["tds"].astype(int)
    df["is_estimated"] = (df["estimated"] == "Y").astype(int)
    df["is_zero_read"] = (df["consumption_hcf"] == 0).astype(int)
    df["is_odd_period"] = (~df["days"].between(20, 40)).astype(int)
    df["hcf_per_day"] = df["consumption_hcf"] / df["days"]
    return df.reset_index(drop=True), log.table()


# ---------------------------------------------------------------------------
# 4. Development-month panel: gap labels + leakage-safe features
# ---------------------------------------------------------------------------
def label_gaps(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Add a complete month grid per development and label every development-month:
      missing_bill : no bill at all for that month           -> measurement gap
      estimated    : half or more of its meters were estimated -> measurement gap
      zero_read    : all meters read zero                      -> gap OR shut-off (check 311)
      actual       : real meter reads                          -> usable for modelling
    """
    p = panel.copy()
    p["month"] = pd.PeriodIndex(p["revenue_month"], freq="M")
    grids = []
    for tds, g in p.groupby("tds"):
        idx = pd.period_range(g["month"].min(), g["month"].max(), freq="M")
        grids.append(pd.DataFrame({"tds": tds, "month": idx}))
    grid = pd.concat(grids, ignore_index=True)
    p = grid.merge(p, on=["tds", "month"], how="left")
    p["revenue_month"] = p["month"].astype(str)

    # carry static attributes into the empty (missing-bill) rows
    static = ["borough", "development", "apartments", "population", "res_buildings"]
    p[static] = p.groupby("tds")[static].transform(lambda s: s.ffill().bfill())

    p["share_estimated"] = p["n_est_meters"] / p["n_meters"]
    p["gap_type"] = np.select(
        [p["n_meters"].isna(), p["share_estimated"] >= 0.5, p["hcf_per_day"] == 0],
        ["missing_bill", "estimated", "zero_read"], default="actual")
    p["is_gap"] = (p["gap_type"] != "actual").astype(int)
    p["gal_per_apt_day"] = p["hcf_per_day"] * GALLONS_PER_HCF / p["apartments"]
    return p


def metering_coverage(p: pd.DataFrame, threshold: float = 25.0) -> pd.Series:
    """
    Label each development 'whole' or 'partial' metering.
    Some developments are metered only at a store or community centre, so their
    gallons per apartment per day is near zero. A median below `threshold`
    gal/apt/day on ACTUAL reads (up to the end of validation, 2022, where
    available) is implausible for a whole residential development -> 'partial'.
    Per-apartment comparisons use only 'whole' developments.
    Developments without an apartment count are 'unknown'.
    """
    a = p[(p["gap_type"] == "actual") & p["gal_per_apt_day"].notna()]
    early = a[a["revenue_month"] <= VALID_END]
    med = early.groupby("tds")["gal_per_apt_day"].median()
    rest = a[~a["tds"].isin(med.index)].groupby("tds")["gal_per_apt_day"].median()
    med = pd.concat([med, rest])
    lab = pd.Series(np.where(med >= threshold, "whole", "partial"), index=med.index)
    return p["tds"].map(lab).fillna("unknown")


def load_panel(path: Path = PROCESSED / "panel_labeled.csv") -> pd.DataFrame:
    """Read the labelled panel saved by notebook 01 and restore the month type."""
    p = pd.read_csv(path)
    p["revenue_month"] = p["revenue_month"].astype(str)
    p["month"] = pd.PeriodIndex(p["revenue_month"], freq="M")
    return p


def add_features(p: pd.DataFrame) -> pd.DataFrame:
    """
    Leakage-safe features. Every lag/rolling feature uses ONLY earlier months
    (shift(1) or more) and ONLY actual reads, so estimated values never feed
    the model and the target month never sees itself.
    """
    p = p.sort_values(["tds", "month"]).copy()
    p["y_raw"] = np.log1p(p["hcf_per_day"])                       # all billed months
    p["y"] = p["y_raw"].where(p["gap_type"] == "actual")          # modelling target
    g = p.groupby("tds")["y"]
    for k in (1, 2, 3, 12):
        p[f"lag{k}"] = g.shift(k)
    p["roll3_mean"] = g.transform(lambda s: s.shift(1).rolling(3, min_periods=2).mean())
    p["roll12_median"] = g.transform(lambda s: s.shift(1).rolling(12, min_periods=6).median())
    p["gaps_last12"] = p.groupby("tds")["is_gap"].transform(lambda s: s.shift(1).rolling(12, min_periods=1).sum())
    p["month_of_year"] = p["month"].dt.month
    p["log_apartments"] = np.log1p(p["apartments"])
    for b in BOROUGHS:
        p[f"boro_{b.split()[0].lower()}"] = (p["borough"] == b).astype(int)
    p["period"] = np.where(p["revenue_month"] <= TRAIN_END, "train",
                  np.where(p["revenue_month"] <= VALID_END, "valid", "test"))
    return p


FEATURES = ["lag1", "lag2", "lag3", "lag12", "roll3_mean", "roll12_median", "gaps_last12",
            "month_of_year", "temp_mean", "precip_mm", "freeze_days", "hot_days",
            "log_apartments", "boro_bronx", "boro_brooklyn", "boro_manhattan",
            "boro_queens", "boro_staten"]


# ---------------------------------------------------------------------------
# 5. Baseline and candidate
# ---------------------------------------------------------------------------
def baseline_predict(df: pd.DataFrame) -> pd.Series:
    """Baseline 1 - seasonal naive: same month last year; if missing, mean of last 3 months; then last month."""
    return df["lag12"].fillna(df["roll3_mean"]).fillna(df["lag1"])


def persistence_predict(df: pd.DataFrame) -> pd.Series:
    """Baseline 2 - persistence: last actual month; if missing, mean of last 3 months; then same month last year."""
    return df["lag1"].fillna(df["roll3_mean"]).fillna(df["lag12"])


def fit_candidate(train: pd.DataFrame, random_state: int = 42):
    """
    Candidate - gradient boosting that learns the CORRECTION to persistence
    (target = y - persistence) from season, weather, size, borough and recent
    history. Absolute-error loss so a few extreme months do not dominate.
    """
    from sklearn.ensemble import HistGradientBoostingRegressor
    t = train.assign(_p=persistence_predict(train)).dropna(subset=["_p"])
    model = HistGradientBoostingRegressor(loss="absolute_error", max_iter=300, learning_rate=0.05,
                                          max_leaf_nodes=15, min_samples_leaf=60,
                                          random_state=random_state)
    model.fit(t[FEATURES], t["y"] - t["_p"])
    return model


def candidate_predict(model, df: pd.DataFrame) -> pd.Series:
    """Persistence + learned correction."""
    return persistence_predict(df) + model.predict(df[FEATURES])


def metrics(y_true, y_pred) -> dict:
    """Errors on log scale and in HCF/day (back-transformed)."""
    m = pd.notna(y_true) & pd.notna(y_pred)
    yt, yp = np.asarray(y_true[m]), np.asarray(y_pred[m])
    a, b = np.expm1(yt), np.expm1(yp)
    return {"n": int(m.sum()),
            "MAE_log": float(np.mean(np.abs(yt - yp))),
            "RMSE_log": float(np.sqrt(np.mean((yt - yp) ** 2))),
            "MAE_hcf_day": float(np.mean(np.abs(a - b))),
            "MedAPE_%": float(np.median(np.abs(a - b) / np.where(a == 0, np.nan, a)) * 100)}


# ---------------------------------------------------------------------------
# 6. Anomaly rules, 311 corroboration, cost
# ---------------------------------------------------------------------------
def robust_scale(resid: pd.Series) -> tuple[float, float]:
    """Median and MAD-based standard deviation (robust to the outliers we hunt)."""
    r = resid.dropna()
    med = float(r.median())
    mad = float(np.median(np.abs(r - med))) * 1.4826
    return med, mad


def flag_by_residual(resid: pd.Series, med: float, scale: float, k: float = 3.0) -> pd.Series:
    """+1 = abnormally high, -1 = abnormally low, 0 = normal, NaN = not scored."""
    z = (resid - med) / scale
    out = pd.Series(np.where(z > k, 1, np.where(z < -k, -1, 0)), index=resid.index, dtype=float)
    return out.where(resid.notna())


def flag_by_threshold(gal: pd.Series, low: float, high: float) -> pd.Series:
    """Rule A: one citywide band on gallons per apartment per day."""
    out = pd.Series(np.where(gal > high, 1, np.where(gal < low, -1, 0)), index=gal.index, dtype=float)
    return out.where(gal.notna())


def complaint_spikes(p: pd.DataFrame, k: float = 2.0, col: str = "c_supply") -> pd.Series:
    """
    Borough-month spike in 311 SUPPLY-disruption complaints (no water, low
    pressure, main break): robust z above k, where the centre and spread come
    from the TRAINING years only (no peeking at test).
    """
    bm = p.drop_duplicates(["borough", "revenue_month"])[["borough", "revenue_month", col]]
    tr = bm[bm["revenue_month"] <= TRAIN_END]
    stats = tr.groupby("borough")[col].agg(
        med="median", mad=lambda s: np.median(np.abs(s - s.median())) * 1.4826)
    bm = bm.join(stats, on="borough")
    bm["spike_311"] = ((bm[col] - bm["med"]) / bm["mad"].replace(0, np.nan) > k).astype(int)
    key = p["borough"] + "|" + p["revenue_month"]
    lookup = dict(zip(bm["borough"] + "|" + bm["revenue_month"], bm["spike_311"]))
    return key.map(lookup).fillna(0).astype(int)


def corroboration(flags: pd.Series, spike: pd.Series) -> dict:
    """Share of flagged months that fall in a 311 spike month vs. the base rate (lift)."""
    scored = flags.notna()
    flagged = flags.fillna(0) != 0
    base = spike[scored].mean()
    hit = spike[flagged].mean() if flagged.any() else np.nan
    return {"flag_rate_%": 100 * flagged[scored].mean(), "n_flagged": int(flagged.sum()),
            "in_spike_%": 100 * hit, "base_spike_%": 100 * base,
            "lift": hit / base if base else np.nan}


# ---------------------------------------------------------------------------
# 7. Bootstrap (cluster bootstrap: resample DEVELOPMENTS, not rows)
# ---------------------------------------------------------------------------
def cluster_bootstrap_mean(df: pd.DataFrame, value: str, cluster: str = "tds",
                           B: int = 2000, seed: int = 2050) -> tuple[float, float, float]:
    """
    Months from the same development are not independent, so we resample whole
    developments with replacement. Returns (estimate, CI low, CI high) at 95%.
    """
    rng = np.random.default_rng(seed)
    per = df.groupby(cluster)[value].agg(["sum", "count"])
    s, c = per["sum"].to_numpy(), per["count"].to_numpy()
    k = len(per)
    idx = rng.integers(0, k, size=(B, k))
    boots = s[idx].sum(1) / c[idx].sum(1)
    return float(s.sum() / c.sum()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def cluster_bootstrap_diff(df: pd.DataFrame, value: str, group: str, a: str, b: str,
                           cluster: str = "tds", B: int = 2000, seed: int = 2050):
    """95% CI for mean(value | group==a) - mean(value | group==b), resampling clusters within each group."""
    rng = np.random.default_rng(seed)
    out = []
    for gname in (a, b):
        per = df[df[group] == gname].groupby(cluster)[value].agg(["sum", "count"])
        s, c = per["sum"].to_numpy(), per["count"].to_numpy()
        idx = rng.integers(0, len(per), size=(B, len(per)))
        out.append((s.sum() / c.sum(), s[idx].sum(1) / c[idx].sum(1)))
    est = out[0][0] - out[1][0]
    d = out[0][1] - out[1][1]
    return float(est), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
