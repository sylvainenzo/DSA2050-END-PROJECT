"""
DSA 2050 - Option 06: Water Supply Reliability Monitoring
Interactive dashboard for the NYCHA water-reliability project.

Run from the project root:
    streamlit run streamlit_app.py

Palette: oat cream (background), coffee blue (structure), tangerine (alerts).
"""
from pathlib import Path
import sys

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# 0. Paths, palette, page setup
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

PANEL = ROOT / "data" / "processed" / "panel_labeled.csv"
REPORTS = ROOT / "reports"

OAT = "#F6EFE2"        # oat cream  - page background
OAT_CARD = "#EFE5D2"   # oat cream  - cards and table headers
OAT_LINE = "#DCCFB4"   # oat cream  - borders
COFFEE = "#27455F"     # coffee blue - headings, primary series
COFFEE_SOFT = "#5B7C97"# coffee blue - secondary series
TANGERINE = "#F28C28"  # tangerine  - highlights, gaps, alerts
TANGERINE_INK = "#B35C00"  # tangerine, darkened for text on cream
INK = "#1C2B3A"        # body text
MUTED = "#6B7B8C"

GAP_COLORS = {"actual": COFFEE, "estimated": TANGERINE,
              "zero_read": "#9E2A2B", "missing_bill": "#B9AFA0"}
ACTION_COLORS = {"Fix metering first (recurring gaps)": TANGERINE,
                 "Inspect for leaks / supply issues (recurring abnormal use)": "#9E2A2B",
                 "Monitor": COFFEE}

st.set_page_config(page_title="Water Supply Reliability - DSA 2050",
                   page_icon="|", layout="wide")

st.markdown(f"""
<style>
  .stApp {{ background: {OAT}; color: {INK}; }}
  section[data-testid="stSidebar"] {{ background: {OAT_CARD};
      border-right: 1px solid {OAT_LINE}; }}
  h1, h2, h3, h4 {{ color: {COFFEE}; font-weight: 700; }}
  .eyebrow {{ color: {TANGERINE_INK}; font-size: 0.78rem; font-weight: 700;
      letter-spacing: .14em; text-transform: uppercase; margin-bottom: .2rem; }}
  div[data-testid="stMetric"] {{ background: {OAT_CARD}; border: 1px solid {OAT_LINE};
      border-left: 5px solid {TANGERINE}; border-radius: 10px; padding: 14px 16px; }}
  div[data-testid="stMetricValue"] {{ color: {COFFEE}; font-size: 1.9rem; }}
  div[data-testid="stMetricLabel"] {{ color: {MUTED}; }}
  .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {OAT_LINE}; }}
  .stTabs [data-baseweb="tab"] {{ background: transparent; color: {MUTED};
      font-weight: 600; padding: 8px 14px; }}
  .stTabs [aria-selected="true"] {{ background: {OAT_CARD}; color: {COFFEE};
      border-radius: 8px 8px 0 0; border-bottom: 3px solid {TANGERINE}; }}
  .note {{ background: {OAT_CARD}; border-left: 4px solid {COFFEE};
      border-radius: 8px; padding: 12px 16px; margin: 8px 0; }}
  .stDataFrame {{ border: 1px solid {OAT_LINE}; border-radius: 8px; }}
  .stButton>button, .stDownloadButton>button {{ background: {COFFEE}; color: {OAT};
      border: none; border-radius: 8px; font-weight: 600; }}
  .stButton>button:hover, .stDownloadButton>button:hover {{ background: {TANGERINE_INK};
      color: {OAT}; }}
  a {{ color: {TANGERINE_INK}; }}
</style>""", unsafe_allow_html=True)


def chart_theme():
    return {"config": {
        "background": OAT,
        "view": {"stroke": "transparent"},
        "font": "Inter, Helvetica, Arial, sans-serif",
        "title": {"color": COFFEE, "fontSize": 14, "anchor": "start", "fontWeight": 600},
        "axis": {"labelColor": INK, "titleColor": MUTED, "gridColor": OAT_LINE,
                 "domainColor": OAT_LINE, "tickColor": OAT_LINE, "labelFontSize": 11,
                 "titleFontSize": 11},
        "legend": {"labelColor": INK, "titleColor": MUTED, "labelFontSize": 11},
        "range": {"category": [COFFEE, TANGERINE, COFFEE_SOFT, "#9E2A2B", "#B9AFA0"]},
    }}


try:                                   # Altair 5.5+ / 6.x
    alt.theme.register("oat", enable=True)(chart_theme)
except AttributeError:                 # older Altair
    alt.themes.register("oat", chart_theme)
    alt.themes.enable("oat")


def eyebrow(text):
    st.markdown(f'<p class="eyebrow">{text}</p>', unsafe_allow_html=True)


def note(text):
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# 1. Load data (cached)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_panel():
    p = pd.read_csv(PANEL)
    p["revenue_month"] = p["revenue_month"].astype(str)
    p["date"] = pd.to_datetime(p["revenue_month"] + "-01")
    p["year"] = p["date"].dt.year
    p["month_of_year"] = p["date"].dt.month
    return p


@st.cache_data(show_spinner=False)
def load_report(name):
    f = REPORTS / f"{name}.csv"
    return pd.read_csv(f) if f.exists() else None


@st.cache_data(show_spinner="Fitting the expected-use model...")
def fit_model():
    """Expected use, residuals and the 311 spike flag, from src/water_utils.py."""
    import water_utils as wu
    p = wu.add_features(wu.load_panel())
    train = p[(p["period"] == "train") & p["y"].notna()]
    model = wu.fit_candidate(train)
    p["pred"] = wu.candidate_predict(model, p)
    p["resid"] = p["y"] - p["pred"]              # actual reads only
    p["resid_raw"] = p["y_raw"] - p["pred"]      # every billed month
    med, scale = wu.robust_scale(p.loc[p["period"] == "valid", "resid"])
    p["spike_311"] = wu.complaint_spikes(p)
    p["expected_hcf_day"] = np.expm1(p["pred"])
    out = p.drop(columns=["month"]).copy()
    out["revenue_month"] = out["revenue_month"].astype(str)
    return out, float(med), float(scale)


try:
    panel = load_panel()
except FileNotFoundError:
    st.error(f"Could not find {PANEL}. Run notebooks/01_acquisition_quality.ipynb first "
             "(Kernel > Restart Kernel and Run All Cells), then reload this page.")
    st.stop()

MODEL_OK = True
try:
    scored, RESID_MED, RESID_SD = fit_model()
except Exception as exc:              # noqa: BLE001
    MODEL_OK = False
    scored, RESID_MED, RESID_SD = None, 0.0, 1.0
    MODEL_ERR = exc

# ----------------------------------------------------------------------------
# 2. Sidebar filters
# ----------------------------------------------------------------------------
st.sidebar.markdown(f"<h3 style='color:{COFFEE};margin-top:0'>Filters</h3>",
                    unsafe_allow_html=True)

boroughs = sorted(panel["borough"].dropna().unique())
sel_boroughs = st.sidebar.multiselect("Borough", boroughs, default=boroughs)

cover_opts = ["whole", "partial", "unknown"]
sel_cover = st.sidebar.multiselect(
    "Metering coverage", cover_opts, default=cover_opts,
    help="'partial' = only a store or community-centre meter, so use per apartment "
         "is not meaningful for that development.")

years = sorted(panel["year"].unique())
yr_from, yr_to = st.sidebar.select_slider(
    "Years", options=years, value=(years[0], years[-1]))

st.sidebar.markdown("---")
st.sidebar.markdown(f"<p class='eyebrow'>Rule B threshold</p>", unsafe_allow_html=True)
K = st.sidebar.slider(
    "Flag when |z| is above", min_value=2.0, max_value=8.0, value=4.5, step=0.5,
    help="z = (actual - expected) / robust SD. The report's operating threshold is 4.5, "
         "chosen on the 2022 validation year to flag at most 5% of development-months.")
GAP_MIN = st.sidebar.slider("'Fix metering' needs this many gap months", 1, 20, 6)
ABN_MIN = st.sidebar.slider("'Inspect' needs this many abnormal months", 1, 12, 3)

st.sidebar.markdown("---")
st.sidebar.caption(
    "DSA 2050 - Option 06\n\n"
    "Sylvain Biket (674139)\n\n"
    "Victor Apamo (673804)\n\n"
    "Whitney Jebor (673308)")

mask = (panel["borough"].isin(sel_boroughs)
        & panel["metering"].isin(sel_cover)
        & panel["year"].between(yr_from, yr_to))
view = panel[mask]

if view.empty:
    st.warning("No development-months match these filters. Widen them in the sidebar.")
    st.stop()

# ----------------------------------------------------------------------------
# 3. Header + KPIs
# ----------------------------------------------------------------------------
eyebrow("DSA 2050 - Option 06 - Applied Data Science Methodology")
st.title("Water Supply Reliability Monitoring")
st.markdown(
    f"<p style='color:{MUTED};font-size:1.03rem;margin-top:-6px'>"
    "Which NYCHA developments show recurring disruption or abnormal consumption - "
    "and which simply are not being read?</p>", unsafe_allow_html=True)

whole = view[(view["gap_type"] == "actual") & (view["metering"] == "whole")]
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Developments", f"{view['tds'].nunique()}")
k2.metric("Development-months", f"{len(view):,}")
k3.metric("Measurement gaps", f"{100 * view['is_gap'].mean():.1f}%",
          help="Share of development-months that are estimated, missing or zero reads.")
k4.metric("Median use", f"{whole['gal_per_apt_day'].median():.0f}" if len(whole) else "-",
          help="Gallons per apartment per day, whole-metered developments, actual reads.")
k5.metric("Estimated bills",
          f"{100 * (view['gap_type'] == 'estimated').mean():.1f}%")

tabs = st.tabs(["Overview", "Measurement gaps", "Consumption", "Model & rules",
                "Priority list", "Development explorer", "Data & SQL"])

# ----------------------------------------------------------------------------
# Tab 1 - Overview
# ----------------------------------------------------------------------------
with tabs[0]:
    st.subheader("The decision this supports")
    c1, c2, c3 = st.columns(3)
    for col, (title, body) in zip(
            (c1, c2, c3),
            [("Fix the meter", "Readings keep going missing or are estimated, so "
                               "consumption cannot be judged at all."),
             ("Inspect for leaks", "Use is repeatedly far from what this development "
                                   "normally uses."),
             ("Monitor", "Nothing recurring: no crew needed this month.")]):
        col.markdown(
            f"<div class='note'><b style='color:{COFFEE}'>{title}</b><br>"
            f"<span style='color:{MUTED}'>{body}</span></div>", unsafe_allow_html=True)

    st.markdown("#### Key findings")
    findings = pd.DataFrame({
        "Finding": [
            "Measurement gaps are the biggest problem, and growing",
            "Estimated bills hide problems",
            "Last month predicts this month",
            "A development-specific rule beats a citywide threshold",
            "Inspection pays",
        ],
        "Evidence": [
            "33.4% of development-months are gaps; estimated bills rose from 18.6% "
            "of billed months (2018) to 41.2% (2025)",
            "Estimated months look normal against expected use (8.8% flagged) while "
            "zero reads raise false alarms (33.3% vs 10.8% of real reads)",
            "Persistence is 36% more accurate than 'same month last year'; the "
            "gradient-boosting candidate adds only 1.5%; weather adds nothing (r = -0.01)",
            "On the same 691 test months Rule B flags 8.3% vs 12.5%, with lift 3.4 vs "
            "2.6 against 311 supply spikes, and 10.5% vs 34.9% of flags on large estates",
            "A median flag is worth about USD 3,200 of excess charges against an "
            "assumed USD 400 crew visit (break-even 2.5% of flags)",
        ]})
    st.dataframe(findings, hide_index=True, width="stretch")

    st.markdown("#### Citywide picture over time")
    monthly = (view.groupby("date")
               .agg(gap_rate=("is_gap", "mean"),
                    developments=("tds", "nunique")).reset_index())
    med_use = (view[(view["gap_type"] == "actual") & (view["metering"] == "whole")]
               .groupby("date")["gal_per_apt_day"].median().reset_index())

    base = alt.Chart(monthly).encode(x=alt.X("date:T", title="Bill month"))
    gap_area = base.mark_area(color=TANGERINE, opacity=0.75).encode(
        y=alt.Y("gap_rate:Q", title="% development-months with a gap",
                axis=alt.Axis(format="%")),
        tooltip=[alt.Tooltip("date:T", title="Month"),
                 alt.Tooltip("gap_rate:Q", format=".1%", title="Gap share"),
                 alt.Tooltip("developments:Q", title="Developments billed")])
    use_line = alt.Chart(med_use).mark_line(color=COFFEE, strokeWidth=2).encode(
        x="date:T",
        y=alt.Y("gal_per_apt_day:Q", title="Median gal / apartment / day"),
        tooltip=[alt.Tooltip("date:T", title="Month"),
                 alt.Tooltip("gal_per_apt_day:Q", format=".0f", title="Median use")])
    st.altair_chart(
        alt.vconcat(
            use_line.properties(height=190, width="container",
                                title="Typical use per apartment (whole-metered, actual reads)"),
            gap_area.properties(height=130, width="container",
                                title="Share of development-months that are a measurement gap"),
        ).resolve_scale(x="shared"), width="stretch")
    note("Read the two panels together: a dip in use that lines up with a spike in "
         "gaps is a <b>measurement artefact</b>, not a real fall in consumption.")

# ----------------------------------------------------------------------------
# Tab 2 - Measurement gaps
# ----------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Measurement gaps: the biggest reliability problem")
    c1, c2 = st.columns([3, 2])

    comp = view.groupby(["year", "gap_type"]).size().reset_index(name="n")
    order = ["actual", "estimated", "zero_read", "missing_bill"]
    c1.altair_chart(
        alt.Chart(comp).mark_bar().encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y("n:Q", title="% of development-months", stack="normalize",
                    axis=alt.Axis(format="%")),
            color=alt.Color("gap_type:N", title="Label", sort=order,
                            scale=alt.Scale(domain=order,
                                            range=[GAP_COLORS[g] for g in order])),
            tooltip=["year:O", "gap_type:N",
                     alt.Tooltip("n:Q", title="Development-months")],
        ).properties(height=330, title="Real reads vs measurement gaps, by year"),
        width="stretch")

    counts = (view["gap_type"].value_counts().rename_axis("gap_type")
              .reset_index(name="development_months"))
    counts["share"] = (100 * counts["development_months"]
                       / counts["development_months"].sum()).round(1)
    c2.markdown("**Labels in the current selection**")
    c2.dataframe(counts, hide_index=True, width="stretch")
    c2.markdown(
        f"<div class='note'><b style='color:{TANGERINE_INK}'>Why this matters</b><br>"
        "<span style='color:" + MUTED + "'>An estimated bill is a carried-forward guess, "
        "not a measurement: estimated months change 2.7% from month to month against "
        "6.8% for real reads. A leak during an estimated month is invisible.</span></div>",
        unsafe_allow_html=True)

    st.markdown("#### Developments with the most gap months")
    worst = (view.groupby(["tds", "development", "borough"], dropna=False)
             .agg(months=("revenue_month", "size"), gap_months=("is_gap", "sum"))
             .reset_index())
    worst["gap_%"] = (100 * worst["gap_months"] / worst["months"]).round(1)
    worst = worst[worst["months"] >= 12].sort_values("gap_%", ascending=False).head(20)
    st.altair_chart(
        alt.Chart(worst).mark_bar(color=TANGERINE).encode(
            x=alt.X("gap_%:Q", title="% of its months that are a measurement gap"),
            y=alt.Y("development:N", sort="-x", title=None),
            tooltip=["development:N", "borough:N", "months:Q", "gap_months:Q",
                     alt.Tooltip("gap_%:Q", format=".1f")],
        ).properties(height=430), width="stretch")

# ----------------------------------------------------------------------------
# Tab 3 - Consumption
# ----------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Consumption, boroughs and uncertainty")
    if whole.empty:
        st.info("No whole-metered actual reads in this selection. Add 'whole' back "
                "under Metering coverage.")
    else:
        c1, c2 = st.columns(2)
        g = whole[whole["gal_per_apt_day"] > 0].copy()
        g["log10"] = np.log10(g["gal_per_apt_day"])
        c1.altair_chart(
            alt.Chart(g).mark_bar(color=COFFEE).encode(
                x=alt.X("log10:Q", bin=alt.Bin(maxbins=50),
                        title="Gallons per apartment per day (log10)"),
                y=alt.Y("count():Q", title="Development-months"),
            ).properties(height=300,
                         title=f"Distribution (median {g['gal_per_apt_day'].median():.0f} gal/apt/day)"),
            width="stretch")
        c2.altair_chart(
            alt.Chart(g).mark_boxplot(color=COFFEE_SOFT, outliers=False).encode(
                x=alt.X("borough:N", title=None),
                y=alt.Y("gal_per_apt_day:Q", title="Gal / apartment / day",
                        scale=alt.Scale(type="log")),
            ).properties(height=300, title="By borough (outliers hidden)"),
            width="stretch")

        ci = load_report("bootstrap_ci_by_borough")
        if ci is not None:
            st.markdown("#### Cluster-bootstrap 95% confidence intervals")
            cic = ci.dropna(subset=["mean_gal_apt_day"])
            pts = alt.Chart(cic).mark_point(filled=True, size=90, color=COFFEE).encode(
                x=alt.X("mean_gal_apt_day:Q", title="Mean gallons per apartment per day"),
                y=alt.Y("borough:N", sort="-x", title=None),
                tooltip=["borough:N", "whole_metered_devs:Q", "mean_gal_apt_day:Q",
                         "ci_low:Q", "ci_high:Q"])
            bars = alt.Chart(cic).mark_rule(color=COFFEE, strokeWidth=2).encode(
                x="ci_low:Q", x2="ci_high:Q", y=alt.Y("borough:N", sort="-x"))
            gpts = alt.Chart(ci).mark_point(filled=True, size=90, color=TANGERINE).encode(
                x=alt.X("pct_gap:Q", title="% development-months with a gap"),
                y=alt.Y("borough:N", sort="-x", title=None),
                tooltip=["borough:N", "pct_gap:Q", "gap_ci_low:Q", "gap_ci_high:Q"])
            gbars = alt.Chart(ci).mark_rule(color=TANGERINE, strokeWidth=2).encode(
                x="gap_ci_low:Q", x2="gap_ci_high:Q", y=alt.Y("borough:N", sort="-x"))
            st.altair_chart(
                ((bars + pts).properties(height=200, title="Use per apartment, 95% CI")
                 | (gbars + gpts).properties(height=200, title="Gap rate, 95% CI")),
                width="stretch")
            note("The intervals overlap, so <b>no borough is clearly different</b>. "
                 "Bronx minus Queens is +100 gal/apt/day with a 95% CI of [-7, 197], "
                 "which includes 0. Months of one development are correlated, so the "
                 "bootstrap resamples whole developments, not rows.")

        st.markdown("#### Season and weather")
        mm = (whole.groupby("revenue_month")
              .agg(gal=("gal_per_apt_day", "median"),
                   temp=("temp_mean", "first")).reset_index())
        mm["month_of_year"] = pd.to_datetime(mm["revenue_month"] + "-01").dt.month
        c3, c4 = st.columns(2)
        c3.altair_chart(
            alt.Chart(mm).mark_boxplot(color=COFFEE_SOFT).encode(
                x=alt.X("month_of_year:O", title="Calendar month"),
                y=alt.Y("gal:Q", title="Median gal/apt/day"),
            ).properties(height=280, title="Seasonal pattern"), width="stretch")
        r = mm[["temp", "gal"]].corr().iloc[0, 1] if len(mm) > 2 else float("nan")
        c4.altair_chart(
            alt.Chart(mm).mark_circle(size=55, color=COFFEE, opacity=.75).encode(
                x=alt.X("temp:Q", title="Monthly mean temperature (deg C)"),
                y=alt.Y("gal:Q", title="Median gal/apt/day"),
                tooltip=["revenue_month:N", "temp:Q", "gal:Q"],
            ).properties(height=280,
                         title=f"Use vs temperature (r = {r:.2f}; association, not causation)"),
            width="stretch")

# ----------------------------------------------------------------------------
# Tab 4 - Model and rules
# ----------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Expected use, then two decision rules")
    note("<b>Layer 1</b> predicts each development's expected use for the month. "
         "<b>Layer 2</b> flags months that are far from expected. "
         "Split by time, never shuffled: train to Dec 2021, validate 2022, "
         "test Jan 2023 - May 2025.")

    mc = load_report("metric_comparison")
    if mc is not None:
        st.markdown("#### Accuracy (MAE on the log scale, lower is better)")
        wide = mc.pivot_table(index="method", columns="split", values="MAE_log")
        wide = wide[[c for c in ["train", "valid", "test"] if c in wide.columns]]
        st.dataframe(wide.round(3), width="stretch")
        st.altair_chart(
            alt.Chart(mc[mc["split"] != "train"]).mark_bar().encode(
                x=alt.X("MAE_log:Q", title="MAE (log scale)"),
                y=alt.Y("method:N", sort="-x", title=None),
                color=alt.Color("split:N", title="Split",
                                scale=alt.Scale(domain=["valid", "test"],
                                                range=[COFFEE_SOFT, COFFEE])),
                tooltip=["method:N", "split:N", alt.Tooltip("MAE_log:Q", format=".3f")],
            ).properties(height=220), width="stretch")
        note("The candidate had the lowest <b>validation</b> error, so it was used for "
             "flagging. On test it is 37% more accurate than seasonal naive (target was "
             "10%), but only <b>1.5% better than persistence</b> - comparing with the "
             "last actual reading is nearly as good and far simpler.")

    rc = load_report("rule_comparison")
    if rc is not None:
        st.markdown("#### Rule A (citywide band) vs Rule B (own history)")
        st.dataframe(rc, hide_index=True, width="stretch")

    sens = load_report("sensitivity_table")
    if sens is not None:
        st.markdown("#### Sensitivity: what the threshold choice costs")
        st.altair_chart(
            alt.Chart(sens).mark_point(filled=True, size=110).encode(
                x=alt.X("flag_rate_%:Q", title="% of development-months flagged (workload)"),
                y=alt.Y("lift:Q", title="Lift against 311 supply spikes"),
                color=alt.Color("rule:N", scale=alt.Scale(domain=["A", "B"],
                                                          range=[COFFEE_SOFT, TANGERINE])),
                tooltip=["rule:N", "threshold:N", "flag_rate_%:Q", "lift:Q"],
            ).properties(height=320), width="stretch")
        st.dataframe(sens, hide_index=True, width="stretch")

    gvf = load_report("gap_vs_flag")
    if gvf is not None:
        st.markdown("#### Why gaps are labelled before flagging")
        st.altair_chart(
            alt.Chart(gvf).mark_bar().encode(
                x=alt.X("gap_type:N", title=None, sort="-y"),
                y=alt.Y("flag_rate_pct:Q", title="% of those months flagged"),
                color=alt.Color("gap_type:N", legend=None,
                                scale=alt.Scale(domain=list(GAP_COLORS),
                                                range=list(GAP_COLORS.values()))),
                tooltip=["gap_type:N", "dev_months:Q", "flag_rate_pct:Q"],
            ).properties(height=260), width="stretch")
        note("Zero reads are flagged about three times as often as real reads: false "
             "alarms unless they are recognised as gaps. Estimated months look "
             "<i>normal</i>, so a real problem during one is invisible.")

# ----------------------------------------------------------------------------
# Tab 5 - Priority list (live, uses the sidebar sliders)
# ----------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Priority list - the answer to the decision question")
    if not MODEL_OK:
        st.warning("The live model could not be fitted here, so this is the saved "
                   f"priority list from the report. ({type(MODEL_ERR).__name__})")
        pl = load_report("priority_list")
        if pl is not None:
            st.dataframe(pl, hide_index=True, width="stretch")
    else:
        test = scored[(scored["period"] == "test")
                      & scored["borough"].isin(sel_boroughs)
                      & scored["metering"].isin(sel_cover)].copy()
        z = (test["resid"] - RESID_MED) / RESID_SD
        test["flag"] = np.where(test["resid"].isna(), np.nan,
                                np.where(z > K, 1, np.where(z < -K, -1, 0)))

        rec = (test.groupby(["tds", "development", "borough", "metering"], dropna=False)
               .agg(months=("revenue_month", "size"),
                    gap_months=("is_gap", "sum"),
                    apartments=("apartments", "first"),
                    high_flags=("flag", lambda s: int((s == 1).sum())),
                    low_flags=("flag", lambda s: int((s == -1).sum())))
               .reset_index())
        rec["abnormal_months"] = rec["high_flags"] + rec["low_flags"]
        rec["action"] = np.select(
            [rec["gap_months"] >= GAP_MIN, rec["abnormal_months"] >= ABN_MIN],
            ["Fix metering first (recurring gaps)",
             "Inspect for leaks / supply issues (recurring abnormal use)"],
            default="Monitor")
        rec = rec.sort_values(["abnormal_months", "gap_months"], ascending=False)

        n_flagged = int((test["flag"].fillna(0) != 0).sum())
        n_scored = int(test["flag"].notna().sum())
        a, b, c, d = st.columns(4)
        a.metric("Fix metering first",
                 int((rec["action"].str.startswith("Fix")).sum()))
        b.metric("Inspect", int((rec["action"].str.startswith("Inspect")).sum()))
        c.metric("Monitor", int((rec["action"] == "Monitor").sum()))
        d.metric("Monthly workload",
                 f"{100 * n_flagged / max(n_scored, 1):.1f}%",
                 help="Share of scored development-months flagged by Rule B at this "
                      "threshold. Crew-capacity target in the report: at most 5%.")

        st.altair_chart(
            alt.Chart(rec).mark_circle(size=130, opacity=.8).encode(
                x=alt.X("gap_months:Q", title="Measurement-gap months in the test period"),
                y=alt.Y("abnormal_months:Q", title=f"Abnormal-use months (|z| > {K})"),
                color=alt.Color("action:N", title="Action",
                                scale=alt.Scale(domain=list(ACTION_COLORS),
                                                range=list(ACTION_COLORS.values())),
                                legend=alt.Legend(orient="bottom", columns=1)),
                size=alt.Size("apartments:Q", title="Apartments",
                              scale=alt.Scale(range=[60, 600])),
                tooltip=["development:N", "borough:N", "metering:N", "apartments:Q",
                         "gap_months:Q", "high_flags:Q", "low_flags:Q", "action:N"],
            ).properties(height=430,
                         title="Two different reliability problems"),
            width="stretch")

        pick = st.selectbox("Show", ["All"] + sorted(rec["action"].unique()))
        shown = rec if pick == "All" else rec[rec["action"] == pick]
        st.dataframe(
            shown[["development", "borough", "metering", "apartments", "months",
                   "gap_months", "high_flags", "low_flags", "abnormal_months", "action"]],
            hide_index=True, width="stretch")
        st.download_button("Download this list (CSV)",
                           shown.to_csv(index=False).encode(),
                           file_name="priority_list_filtered.csv", mime="text/csv")
        note("Move the sliders in the sidebar to see the trade-off: a lower threshold "
             "flags more months (more work, more false alarms), a higher one flags "
             "fewer (more missed problems). The report's operating threshold is 4.5, "
             "chosen on the 2022 validation year, never on the test period.")

# ----------------------------------------------------------------------------
# Tab 6 - Development explorer
# ----------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Look at one development")
    names = (view.dropna(subset=["development"])
             .sort_values("development")["development"].unique())
    if len(names) == 0:
        st.info("No named developments in this selection.")
    else:
        default = int(np.where(names == "RANGEL")[0][0]) if "RANGEL" in names else 0
        dev = st.selectbox("Development", names, index=default)
        d = view[view["development"] == dev].sort_values("date")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Borough", str(d["borough"].iloc[0]).title())
        m2.metric("Apartments", f"{d['apartments'].iloc[0]:,.0f}"
                  if pd.notna(d["apartments"].iloc[0]) else "-")
        m3.metric("Metering", str(d["metering"].iloc[0]))
        m4.metric("Gap months", f"{int(d['is_gap'].sum())} of {len(d)}")

        if MODEL_OK:
            sc = scored[scored["development"] == dev][
                ["revenue_month", "expected_hcf_day", "resid", "resid_raw"]]
            d = d.merge(sc, on="revenue_month", how="left")
            d["z"] = (d["resid_raw"] - RESID_MED) / RESID_SD
            d["flagged"] = d["z"].abs() > K
        else:
            d["expected_hcf_day"], d["flagged"] = np.nan, False

        actual = d[d["gap_type"] == "actual"]
        line = alt.Chart(actual).mark_line(color=COFFEE, strokeWidth=2).encode(
            x=alt.X("date:T", title="Bill month"),
            y=alt.Y("hcf_per_day:Q", title="HCF per day"))
        pts = alt.Chart(d).mark_point(filled=True, size=70).encode(
            x="date:T", y="hcf_per_day:Q",
            color=alt.Color("gap_type:N", title="Month label",
                            scale=alt.Scale(domain=list(GAP_COLORS),
                                            range=list(GAP_COLORS.values()))),
            tooltip=["revenue_month:N", "gap_type:N",
                     alt.Tooltip("hcf_per_day:Q", format=".2f", title="Actual"),
                     alt.Tooltip("expected_hcf_day:Q", format=".2f", title="Expected"),
                     alt.Tooltip("n_meters:Q", title="Meters"),
                     alt.Tooltip("share_estimated:Q", format=".0%", title="Estimated")])
        layers = [line, pts]
        if MODEL_OK and d["expected_hcf_day"].notna().any():
            layers.insert(1, alt.Chart(d).mark_line(
                color=COFFEE_SOFT, strokeDash=[5, 4]).encode(
                x="date:T", y=alt.Y("expected_hcf_day:Q")))
        flags = d[d["flagged"].fillna(False)]
        if len(flags):
            layers.append(alt.Chart(flags).mark_point(
                shape="triangle-up", size=160, color=TANGERINE, filled=True).encode(
                x="date:T", y="hcf_per_day:Q",
                tooltip=["revenue_month:N", alt.Tooltip("z:Q", format=".1f")]))
        st.altair_chart(alt.layer(*layers).properties(
            height=380, title=f"{dev}: actual (solid), expected (dashed), "
                              f"flags (triangles) at |z| > {K}"),
            width="stretch")

        st.dataframe(
            d[["revenue_month", "gap_type", "n_meters", "share_estimated",
               "hcf_per_day", "expected_hcf_day", "gal_per_apt_day", "charges"]]
            .sort_values("revenue_month", ascending=False).round(2),
            hide_index=True, width="stretch", height=280)

# ----------------------------------------------------------------------------
# Tab 7 - Data and SQL
# ----------------------------------------------------------------------------
with tabs[6]:
    st.subheader("Where the data comes from")
    sources = pd.DataFrame({
        "Dataset": ["A. Water Consumption And Cost (2013 - May 2025)",
                    "B. NYCHA Development Data Book",
                    "C. 311 'Water System' complaints (counts only)",
                    "D. Historical daily weather, Central Park"],
        "Producer": ["NYCHA", "NYCHA", "NYC 311 / OTI", "Open-Meteo (ERA5)"],
        "Format": ["CSV", "CSV", "JSON API", "JSON API"],
        "Raw rows": ["66,432", "346", "11,252", "4,534"],
        "Link": ["https://data.cityofnewyork.us/d/66be-66yr",
                 "https://data.cityofnewyork.us/d/evjd-dqpz",
                 "https://data.cityofnewyork.us/d/76ig-c548 + /d/erm2-nwe9",
                 "https://open-meteo.com/en/docs/historical-weather-api"],
        "Licence": ["NYC Open Data Terms of Use", "NYC Open Data Terms of Use",
                    "NYC Open Data Terms of Use", "CC BY 4.0"]})
    st.dataframe(sources, hide_index=True, width="stretch")
    note("Only aggregated 311 counts were downloaded and dataset A holds no tenant "
         "information, so <b>no personal data</b> enters the repository. Raw files are "
         "kept out of GitHub and can be rebuilt with <code>python src/download_data.py</code>.")

    c1, c2 = st.columns(2)
    cl = load_report("cleaning_log")
    if cl is not None:
        c1.markdown("#### Cleaning rules C1-C9")
        c1.dataframe(cl[["rule", "rows_before", "rows_after", "rows_removed"]],
                     hide_index=True, width="stretch")
    dq = load_report("data_quality_table")
    if dq is not None:
        c2.markdown("#### Data-quality audit")
        c2.dataframe(dq, hide_index=True, width="stretch")

    st.markdown("#### The documented SQL join (q07)")
    st.code("""SELECT (SELECT COUNT(*) FROM bills_clean)                 AS rows_before_join,
       COUNT(*)                                           AS rows_after_left_join,
       SUM(CASE WHEN d.tds IS NULL THEN 1 ELSE 0 END)     AS unmatched_rows
FROM   bills_clean AS b
LEFT JOIN developments AS d ON d.tds = b.tds;""", language="sql")
    note("28,635 rows before and after the LEFT JOIN - no fan-out. 225 rows (0.79%) "
         "from 2 developments did not match the 2025 Data Book. All 13 queries and the "
         "two monthly views are in <code>sql/queries.sql</code>.")

st.markdown(
    f"<hr style='border-color:{OAT_LINE}'>"
    f"<p style='color:{MUTED};font-size:.85rem'>DSA 2050 Five-Week Applied Data Science "
    "Methodology Project - Option 06 - USIU-Africa - Sylvain Biket (674139), "
    "Victor Apamo (673804), Whitney Jebor (673308). Built with Streamlit on the "
    "project's own notebook outputs.</p>", unsafe_allow_html=True)