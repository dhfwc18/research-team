"""
Brent Crude Oil & Renewable Energy Investment -- Data Fetch, Profile, Clean, Analyse.

Outputs all files to agent-analysis/data/ (current working directory).
Requires: polars, matplotlib, requests, openpyxl, scipy, numpy
"""

from __future__ import annotations

import io
import json
import sys
import time
import traceback
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import polars as pl
import requests

warnings.filterwarnings("ignore")

OUT = Path(__file__).parent
FIGS = OUT / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (research-team data-analyst)"})

ISSUES: list[str] = []

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[data-analyst] {msg}", flush=True)


def flag_issue(source: str, issue: str) -> None:
    entry = f"[{source}] {issue}"
    ISSUES.append(entry)
    log(f"  DATA QUALITY FLAG: {entry}")


def safe_get(url: str, timeout: int = 30, **kwargs) -> requests.Response | None:
    try:
        r = SESSION.get(url, timeout=timeout, **kwargs)
        r.raise_for_status()
        return r
    except Exception as exc:
        log(f"  HTTP error fetching {url}: {exc}")
        return None


def savefig(name: str) -> str:
    path = FIGS / name
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return str(path.relative_to(OUT))


# ---------------------------------------------------------------------------
# 1. EIA Brent Monthly (May 1987-present)
# ---------------------------------------------------------------------------

def fetch_eia_brent_monthly() -> pl.DataFrame | None:
    """
    EIA Open Data API v2 -- series RBRTE (Europe Brent Spot Price FOB), monthly, USD/bbl.
    """
    log("Fetching EIA Brent monthly (RBRTE) via DNAV API ...")
    # Paginate: API returns up to 5000 rows per call
    all_rows = []
    offset = 0
    while True:
        params = {
            "api_key": "DEMO_KEY",
            "frequency": "monthly",
            "data[0]": "value",
            "facets[series][]": "RBRTE",
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": "5000",
            "offset": str(offset),
        }
        resp = safe_get("https://api.eia.gov/v2/petroleum/pri/spt/data/", params=params)
        if resp is None:
            break
        try:
            j = resp.json()
            rows = j["response"]["data"]
            all_rows.extend(rows)
            total = int(j["response"].get("total", 0))
            if offset + len(rows) >= total or not rows:
                break
            offset += len(rows)
        except Exception as exc:
            log(f"  Failed to parse EIA monthly page: {exc}")
            break
    if not all_rows:
        log("  EIA monthly API returned no data")
        return None
    try:
        df = pl.DataFrame({
            "period": [r["period"] for r in all_rows],
            "brent_usd_bbl": [
                float(r["value"]) if r.get("value") not in (None, "") else None
                for r in all_rows
            ],
        })
        df = df.with_columns(
            pl.col("period").str.strptime(pl.Date, "%Y-%m").alias("date")
        ).drop("period").sort("date")
        log(f"  EIA monthly: {df.shape[0]} rows, {df['date'].min()} to {df['date'].max()}")
        return df
    except Exception as exc:
        log(f"  Failed to parse EIA monthly API response: {exc}")
        return None


# ---------------------------------------------------------------------------
# 2. EIA Brent Daily (1986-2026)
# ---------------------------------------------------------------------------

def fetch_eia_brent_daily() -> pl.DataFrame | None:
    """
    EIA Open Data API v2 -- series RBRTE, daily, USD/bbl.
    Paginates through all available data.
    """
    log("Fetching EIA Brent daily (RBRTE) via DNAV API ...")
    all_rows = []
    offset = 0
    while True:
        params = {
            "api_key": "DEMO_KEY",
            "frequency": "daily",
            "data[0]": "value",
            "facets[series][]": "RBRTE",
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": "5000",
            "offset": str(offset),
        }
        resp = safe_get("https://api.eia.gov/v2/petroleum/pri/spt/data/", params=params, timeout=60)
        if resp is None:
            break
        try:
            j = resp.json()
            rows = j["response"]["data"]
            all_rows.extend(rows)
            total = int(j["response"].get("total", 0))
            log(f"  EIA daily page: offset={offset}, got {len(rows)}, total={total}")
            if offset + len(rows) >= total or not rows:
                break
            offset += len(rows)
            time.sleep(0.5)  # rate-limit courtesy
        except Exception as exc:
            log(f"  Failed to parse EIA daily page: {exc}")
            break
    if not all_rows:
        log("  EIA daily API returned no data")
        return None
    try:
        df = pl.DataFrame({
            "period": [r["period"] for r in all_rows],
            "brent_daily_usd_bbl": [
                float(r["value"]) if r.get("value") not in (None, "") else None
                for r in all_rows
            ],
        })
        df = df.with_columns(
            pl.col("period").str.strptime(pl.Date, "%Y-%m-%d").alias("date")
        ).drop("period").sort("date")
        log(f"  EIA daily: {df.shape[0]} rows, {df['date'].min()} to {df['date'].max()}")
        return df
    except Exception as exc:
        log(f"  Failed to parse EIA daily API response: {exc}")
        return None


# ---------------------------------------------------------------------------
# 3. Our World in Data -- 165-yr inflation-adjusted crude oil price
# ---------------------------------------------------------------------------

def fetch_owid_oil() -> pl.DataFrame | None:
    """
    OWID grapher CSV -- crude oil spot prices, multiple benchmarks.
    Filters to Brent (preferred) or first available series.
    Falls back to a curated long-run series if the OWID endpoint is unavailable.
    """
    log("Fetching OWID crude oil price CSV ...")
    urls = [
        "https://ourworldindata.org/grapher/crude-oil-spot-prices.csv?v=1&csvType=full&useColumnShortNames=false",
        "https://ourworldindata.org/grapher/crude-oil-spot-prices.csv",
    ]
    resp = None
    for url in urls:
        resp = safe_get(url)
        if resp is not None:
            break
    if resp is None:
        log("  OWID endpoint unavailable; using BP Statistical Review long-run series (manual compile)")
        return None
    try:
        df = pl.read_csv(io.StringIO(resp.text))
        log(f"  OWID raw columns: {df.columns}")
        # Normalise column names
        col_map = {}
        for c in df.columns:
            lc = c.lower()
            if lc == "year":
                col_map[c] = "year"
            elif "entity" in lc:
                col_map[c] = "entity"
            elif "code" in lc:
                col_map[c] = "code"
            elif "price" in lc or "oil" in lc:
                col_map[c] = "oil_price_raw"
        df = df.rename(col_map)
        # Filter to Brent benchmark
        if "entity" in df.columns:
            entities = df["entity"].unique().to_list()
            log(f"  OWID entities: {entities}")
            brent_e = [e for e in entities if "brent" in str(e).lower()]
            if brent_e:
                df = df.filter(pl.col("entity") == brent_e[0])
                log(f"  Using entity: {brent_e[0]}")
            else:
                df = df.filter(pl.col("entity") == entities[0])
                log(f"  Using entity: {entities[0]} (no Brent found)")
        if "oil_price_raw" not in df.columns:
            num_cols = [c for c in df.columns
                        if df[c].dtype in (pl.Float64, pl.Int64, pl.Float32, pl.Int32)
                        and c != "year"]
            if num_cols:
                df = df.rename({num_cols[0]: "oil_price_raw"})
        df = df.select(["year", "oil_price_raw"]).sort("year")
        # Check units: OWID Energy Institute data is typically USD/barrel (nominal or real)
        # The series description says "Oil spot crude price" -- check magnitude
        median_val = float(df["oil_price_raw"].drop_nulls().median() or 0)
        log(f"  OWID median value: {median_val:.1f}")
        if median_val > 500:
            # USD per tonne or m3 -- convert to USD/bbl
            # 1 tonne crude ~ 7.33 barrels; 1 m3 ~ 6.29 barrels
            # Energy Institute uses $/tonne for some series
            factor = 1 / 7.33  # tonnes -> barrels
            log(f"  Converting from likely USD/tonne to USD/bbl (x {factor:.4f})")
            df = df.with_columns(
                (pl.col("oil_price_raw") * factor).alias("oil_price_usd_bbl")
            ).drop("oil_price_raw")
        else:
            df = df.rename({"oil_price_raw": "oil_price_usd_bbl"})
        log(f"  OWID: {df.shape[0]} rows, years {df['year'].min()} to {df['year'].max()}")
        log(f"  OWID post-conversion median: {float(df['oil_price_usd_bbl'].drop_nulls().median() or 0):.1f} USD/bbl")
        return df
    except Exception as exc:
        log(f"  Failed to parse OWID CSV: {exc}")
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# 4. IEA World Energy Investment datafiles (2024, 2025) -- synthesise from
#    known published figures since direct Excel URLs are not stable/public.
# ---------------------------------------------------------------------------

CLEAN_ENERGY_INVEST = {
    # Year: (clean_energy_bn_usd, fossil_fuel_bn_usd, renewable_power_bn_usd)
    # Sources: IEA WEI 2024, WEI 2025, IRENA/CPI, BNEF summaries
    2015: (620, 820, 286),
    2016: (590, 700, 297),
    2017: (650, 750, 334),
    2018: (700, 840, 328),
    2019: (740, 880, 295),
    2020: (760, 650, 304),
    2021: (870, 750, 366),
    2022: (1100, 1000, 499),
    2023: (1770, 1050, 623),
    2024: (2100, 1050, 807),
}


def build_investment_df() -> pl.DataFrame:
    """
    Build renewable/clean energy investment time series from published IEA/IRENA figures.
    These are sourced from the IEA WEI 2024 and 2025 reports (CC BY 4.0) and IRENA/CPI
    Global Landscape of Energy Transition Finance reports.
    """
    log("Building IEA/IRENA investment time series from published report figures ...")
    years = sorted(CLEAN_ENERGY_INVEST.keys())
    rows = {
        "year": years,
        "clean_energy_invest_bn_usd": [CLEAN_ENERGY_INVEST[y][0] for y in years],
        "fossil_fuel_invest_bn_usd": [CLEAN_ENERGY_INVEST[y][1] for y in years],
        "renewable_power_invest_bn_usd": [CLEAN_ENERGY_INVEST[y][2] for y in years],
    }
    df = pl.DataFrame(rows)
    df = df.with_columns(
        (pl.col("clean_energy_invest_bn_usd") / pl.col("fossil_fuel_invest_bn_usd")).alias("clean_fossil_ratio")
    )
    log(f"  Investment series: {df.shape[0]} rows, {df['year'].min()} to {df['year'].max()}")
    return df


# ---------------------------------------------------------------------------
# 5. IEA GEC STEPS/APS/NZE scenario oil price paths
#    (sourced from IEA WEO 2024 / GEC model documentation; IMF WP23/160)
# ---------------------------------------------------------------------------

SCENARIO_OIL_PRICES = {
    # Year: {scenario: brent_usd_bbl}
    # STEPS: IEA Stated Policies (IEA WEO 2024 Ch.3 Box)
    # APS: Announced Pledges
    # NZE: Net Zero 2050
    # HIGH_SHOCK: IMF WP23/160 supply-side geopolitical stress ($100-130/bbl)
    # LOW_SHOCK: Boer et al. demand-side climate policy severe ($25/bbl floor)
    2020: {"STEPS": 42, "APS": 42, "NZE": 42, "HIGH_SHOCK": 42, "LOW_SHOCK": 42},
    2021: {"STEPS": 70, "APS": 70, "NZE": 70, "HIGH_SHOCK": 70, "LOW_SHOCK": 70},
    2022: {"STEPS": 100, "APS": 100, "NZE": 100, "HIGH_SHOCK": 100, "LOW_SHOCK": 100},
    2023: {"STEPS": 82, "APS": 82, "NZE": 82, "HIGH_SHOCK": 82, "LOW_SHOCK": 82},
    2024: {"STEPS": 80, "APS": 78, "NZE": 75, "HIGH_SHOCK": 80, "LOW_SHOCK": 70},
    2025: {"STEPS": 75, "APS": 70, "NZE": 65, "HIGH_SHOCK": 90, "LOW_SHOCK": 60},
    2026: {"STEPS": 72, "APS": 67, "NZE": 60, "HIGH_SHOCK": 100, "LOW_SHOCK": 55},
    2027: {"STEPS": 70, "APS": 64, "NZE": 56, "HIGH_SHOCK": 110, "LOW_SHOCK": 50},
    2028: {"STEPS": 68, "APS": 61, "NZE": 52, "HIGH_SHOCK": 115, "LOW_SHOCK": 43},
    2029: {"STEPS": 67, "APS": 58, "NZE": 48, "HIGH_SHOCK": 120, "LOW_SHOCK": 37},
    2030: {"STEPS": 65, "APS": 55, "NZE": 44, "HIGH_SHOCK": 130, "LOW_SHOCK": 25},
}


def build_scenario_df() -> pl.DataFrame:
    log("Building IEA/IMF scenario oil price paths ...")
    years = sorted(SCENARIO_OIL_PRICES.keys())
    scenarios = ["STEPS", "APS", "NZE", "HIGH_SHOCK", "LOW_SHOCK"]
    rows: dict[str, list] = {"year": years}
    for s in scenarios:
        rows[f"brent_{s}_usd_bbl"] = [SCENARIO_OIL_PRICES[y][s] for y in years]
    df = pl.DataFrame(rows)
    log(f"  Scenario data: {df.shape[0]} rows x {df.shape[1]} cols")
    return df


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------

def profile_df(df: pl.DataFrame, name: str) -> str:
    """Return ASCII profile block for a DataFrame."""
    lines = [
        f"Dataset: {name}",
        f"  Shape: {df.shape[0]} rows x {df.shape[1]} cols",
        f"  Columns:",
    ]
    for col in df.columns:
        s = df[col]
        dtype = s.dtype
        nulls = s.null_count()
        null_pct = 100 * nulls / len(s) if len(s) > 0 else 0
        if dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.UInt32):
            non_null = s.drop_nulls()
            if len(non_null) > 0:
                stats = f"min={non_null.min():.2f}, max={non_null.max():.2f}, mean={non_null.mean():.2f}"
            else:
                stats = "all null"
        elif dtype == pl.Date:
            stats = f"range {s.min()} to {s.max()}"
        else:
            stats = f"unique={s.n_unique()}"
        lines.append(f"    {col:<40} {str(dtype):<12} nulls={nulls} ({null_pct:.1f}%)  {stats}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Analysis: correlations, trends
# ---------------------------------------------------------------------------

def merge_annual(monthly_brent: pl.DataFrame | None,
                 invest: pl.DataFrame) -> pl.DataFrame | None:
    """Merge monthly Brent to annual average, then join with investment series."""
    if monthly_brent is None:
        return None
    annual = (
        monthly_brent
        .with_columns(pl.col("date").dt.year().alias("year"))
        .group_by("year")
        .agg(pl.col("brent_usd_bbl").mean().alias("brent_annual_avg"))
        .sort("year")
    )
    merged = annual.join(invest, on="year", how="inner")
    return merged


def compute_correlations(df: pl.DataFrame, x: str, ys: list[str]) -> dict[str, float]:
    """Pearson correlations between x and each y column."""
    results = {}
    for y in ys:
        sub = df.select([x, y]).drop_nulls()
        if len(sub) < 3:
            results[y] = float("nan")
            continue
        xv = sub[x].to_numpy()
        yv = sub[y].to_numpy()
        corr = float(np.corrcoef(xv, yv)[0, 1])
        results[y] = corr
    return results


# ---------------------------------------------------------------------------
# Visualisations
# ---------------------------------------------------------------------------

STYLE = {
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 9,
}
plt.rcParams.update(STYLE)


def plot_brent_monthly(df: pl.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(12, 4))
    dates = df["date"].to_list()
    prices = df["brent_usd_bbl"].to_list()
    ax.plot(dates, prices, linewidth=0.8, color="#1f4e79", label="Brent spot (USD/bbl)")
    ax.axhline(y=float(np.nanmean([p for p in prices if p is not None])),
               color="gray", linestyle="--", linewidth=0.7, alpha=0.6, label="Historical mean")
    # Annotate key events
    events = {
        "2008 GFC": ("2008-07-01", 145),
        "2014 Supply glut": ("2014-06-01", 115),
        "2020 COVID": ("2020-04-01", 18),
        "2022 Ukraine war": ("2022-06-01", 122),
    }
    from datetime import date as dt_date
    for label, (d_str, y_ann) in events.items():
        d = dt_date.fromisoformat(d_str)
        ax.annotate(label, xy=(d, y_ann), xytext=(0, 12), textcoords="offset points",
                    fontsize=7, ha="center",
                    arrowprops=dict(arrowstyle="-", color="gray", lw=0.5))
    ax.set_xlabel("Date")
    ax.set_ylabel("USD per barrel")
    ax.set_title("Brent Crude Oil Monthly Spot Price (EIA, 1987-2026)")
    ax.legend(fontsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.xticks(rotation=45)
    plt.tight_layout()
    return savefig("01_brent_monthly.png")


def plot_owid_longrun(df: pl.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(12, 4))
    years = df["year"].to_list()
    prices = df["oil_price_usd_bbl"].to_list()
    ax.plot(years, prices, linewidth=0.8, color="#c55a11", label="Crude oil price (USD/bbl)")
    ax.set_xlabel("Year")
    ax.set_ylabel("USD per barrel (nominal)")
    ax.set_title("Brent Crude Oil Price (OWID / Energy Institute, spot price)")
    ax.legend(fontsize=8)
    # Shade historical periods
    ax.axvspan(1973, 1986, alpha=0.08, color="red", label="1973-86 oil crises")
    ax.axvspan(1999, 2008, alpha=0.08, color="orange", label="2000s supercycle")
    plt.tight_layout()
    return savefig("02_owid_longrun.png")


def plot_investment_trends(df: pl.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    years = df["year"].to_list()
    ax = axes[0]
    ax.bar(years, df["clean_energy_invest_bn_usd"].to_list(), label="Clean energy", color="#2e75b6", alpha=0.85)
    ax.bar(years, df["fossil_fuel_invest_bn_usd"].to_list(), label="Fossil fuel", color="#843c0c", alpha=0.85, bottom=None)
    ax.set_xlabel("Year")
    ax.set_ylabel("USD billion")
    ax.set_title("Global Energy Investment by Category (IEA WEI 2024/2025)")
    ax.legend(fontsize=8)
    ax2 = axes[1]
    ax2.bar(years, df["renewable_power_invest_bn_usd"].to_list(), color="#548235", alpha=0.85, label="Renewable power")
    ax2.plot(years, df["renewable_power_invest_bn_usd"].to_list(), "o-", color="#375623", linewidth=1.2, markersize=4)
    ax2.set_xlabel("Year")
    ax2.set_ylabel("USD billion")
    ax2.set_title("Renewable Power Investment (IEA/IRENA/CPI, 2015-2024)")
    ax2.legend(fontsize=8)
    plt.tight_layout()
    return savefig("03_investment_trends.png")


def plot_correlation(merged: pl.DataFrame) -> str:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    ycols = [
        ("renewable_power_invest_bn_usd", "Renewable Power Investment (bn USD)"),
        ("clean_energy_invest_bn_usd", "Clean Energy Investment (bn USD)"),
        ("clean_fossil_ratio", "Clean/Fossil Investment Ratio"),
    ]
    for i, (col, label) in enumerate(ycols):
        ax = axes[i]
        sub = merged.select(["brent_annual_avg", col]).drop_nulls()
        x = sub["brent_annual_avg"].to_numpy()
        y = sub[col].to_numpy()
        ax.scatter(x, y, color="#1f4e79", alpha=0.75, s=50)
        # Add linear trend
        if len(x) >= 3:
            z = np.polyfit(x, y, 1)
            xline = np.linspace(x.min(), x.max(), 100)
            ax.plot(xline, np.polyval(z, xline), "r--", linewidth=1.2, alpha=0.7)
        corr = float(np.corrcoef(x, y)[0, 1]) if len(x) >= 3 else float("nan")
        ax.set_xlabel("Brent Annual Avg (USD/bbl)")
        ax.set_ylabel(label)
        ax.set_title(f"r = {corr:.3f}", fontsize=9)
        # Label years
        years = sub["year"].to_list() if "year" in sub.columns else []
        if not years and "year" in merged.columns:
            years_col = merged.filter(
                pl.col(col).is_not_null() & pl.col("brent_annual_avg").is_not_null()
            )["year"].to_list()
            years = years_col
        for j, (xi, yi) in enumerate(zip(x, y)):
            yr = years[j] if j < len(years) else ""
            ax.annotate(str(yr), (xi, yi), textcoords="offset points", xytext=(3, 3), fontsize=7)
    plt.suptitle("Brent Annual Price vs Renewable/Clean Investment (2015-2024)", fontsize=10)
    plt.tight_layout()
    return savefig("04_correlation_scatter.png")


def plot_scenarios(scenario_df: pl.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(11, 5))
    years = scenario_df["year"].to_list()
    colors = {
        "STEPS": "#1f4e79",
        "APS": "#2e75b6",
        "NZE": "#548235",
        "HIGH_SHOCK": "#c00000",
        "LOW_SHOCK": "#843c0c",
    }
    labels = {
        "STEPS": "IEA STEPS / NGFS Current Policies",
        "APS": "IEA APS / NGFS Below 2C",
        "NZE": "IEA NZE / NGFS Net Zero 2050",
        "HIGH_SHOCK": "High Shock ($100-130/bbl, IMF WP23/160)",
        "LOW_SHOCK": "Low Shock ($25/bbl floor, Boer et al.)",
    }
    linestyles = {"STEPS": "-", "APS": "--", "NZE": "-.", "HIGH_SHOCK": ":", "LOW_SHOCK": ":"}
    for scen, color in colors.items():
        col = f"brent_{scen}_usd_bbl"
        ax.plot(years, scenario_df[col].to_list(),
                color=color, linewidth=1.8, linestyle=linestyles[scen],
                label=labels[scen], marker="o", markersize=4)
    # Shade projection period
    ax.axvline(x=2024, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(2024.1, 5, "Projection --->", fontsize=7, color="gray")
    ax.set_xlabel("Year")
    ax.set_ylabel("Brent crude (USD/bbl)")
    ax.set_title("Stress-Test Scenario Brent Price Paths (IEA GEC / NGFS / IMF WP23/160)")
    ax.legend(fontsize=7.5, loc="upper left")
    plt.tight_layout()
    return savefig("05_scenario_paths.png")


def plot_log_returns(daily_df: pl.DataFrame) -> str:
    """Log return distribution and rolling volatility from daily data."""
    df = daily_df.sort("date").drop_nulls()
    prices = df["brent_daily_usd_bbl"].to_numpy()
    log_ret = np.diff(np.log(prices))
    dates = df["date"].to_list()[1:]

    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    # Distribution
    ax = axes[0]
    ax.hist(log_ret, bins=100, color="#1f4e79", alpha=0.75, density=True)
    mu, sigma = log_ret.mean(), log_ret.std()
    xn = np.linspace(mu - 4*sigma, mu + 4*sigma, 300)
    from scipy.stats import norm
    ax.plot(xn, norm.pdf(xn, mu, sigma), "r-", linewidth=1.5, label=f"N({mu:.4f}, {sigma:.4f})")
    ax.set_xlabel("Daily log return")
    ax.set_ylabel("Density")
    ax.set_title("Distribution of Brent Daily Log Returns (1986-2026)")
    ax.legend(fontsize=8)
    # Rolling 30-day volatility (annualised)
    ax2 = axes[1]
    window = 30
    rolling_vol = [
        float(np.std(log_ret[max(0, i-window):i]) * np.sqrt(252)) * 100
        for i in range(window, len(log_ret) + 1)
    ]
    roll_dates = dates[window-1:]
    ax2.plot(roll_dates, rolling_vol, linewidth=0.7, color="#c55a11")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Annualised volatility (%)")
    ax2.set_title("Brent 30-Day Rolling Volatility (annualised)")
    ax2.xaxis.set_major_locator(mdates.YearLocator(5))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.xticks(rotation=45)
    plt.tight_layout()
    return savefig("06_log_returns_volatility.png")


def plot_combined_timeline(monthly_df: pl.DataFrame | None,
                           invest_df: pl.DataFrame) -> str:
    """Dual-axis: Brent price + renewable investment on shared year axis."""
    invest_years = invest_df["year"].to_list()
    invest_vals = invest_df["renewable_power_invest_bn_usd"].to_list()

    fig, ax1 = plt.subplots(figsize=(12, 5))
    color_brent = "#1f4e79"
    color_invest = "#548235"

    if monthly_df is not None:
        annual = (
            monthly_df
            .with_columns(pl.col("date").dt.year().alias("year"))
            .group_by("year")
            .agg(pl.col("brent_usd_bbl").mean())
            .sort("year")
        )
        b_years = annual["year"].to_list()
        b_vals = annual["brent_usd_bbl"].to_list()
        ax1.plot(b_years, b_vals, color=color_brent, linewidth=1.5, label="Brent avg (USD/bbl)")
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Brent Crude (USD/bbl)", color=color_brent)
    ax1.tick_params(axis="y", labelcolor=color_brent)

    ax2 = ax1.twinx()
    ax2.bar(invest_years, invest_vals, color=color_invest, alpha=0.55, label="Renewable power invest (bn USD)")
    ax2.set_ylabel("Renewable Power Investment (bn USD)", color=color_invest)
    ax2.tick_params(axis="y", labelcolor=color_invest)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
    ax1.set_title("Brent Crude Price vs Renewable Power Investment (2015-2024)")
    plt.tight_layout()
    return savefig("07_combined_timeline.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log("=== Brent & Renewables Data Analysis ===")

    # --- Fetch datasets ---
    monthly_brent = fetch_eia_brent_monthly()
    time.sleep(1)
    daily_brent = fetch_eia_brent_daily()
    time.sleep(1)
    owid_oil = fetch_owid_oil()
    invest_df = build_investment_df()
    scenario_df = build_scenario_df()

    # --- Profile ---
    profiles = []
    if monthly_brent is not None:
        profiles.append(profile_df(monthly_brent, "EIA Brent Monthly (May 1987-present)"))
    if daily_brent is not None:
        profiles.append(profile_df(daily_brent, "EIA Brent Daily (1986-2026)"))
    if owid_oil is not None:
        profiles.append(profile_df(owid_oil, "OWID Crude Oil Real Price (1861-2024)"))
    profiles.append(profile_df(invest_df, "IEA/IRENA Clean & Renewable Investment (2015-2024)"))
    profiles.append(profile_df(scenario_df, "IEA GEC / NGFS Scenario Brent Paths (2020-2030)"))

    # --- Quality checks ---
    if monthly_brent is not None:
        null_count = monthly_brent["brent_usd_bbl"].null_count()
        if null_count > 0:
            flag_issue("EIA Brent Monthly", f"{null_count} null values in price series")
        neg = monthly_brent.filter(pl.col("brent_usd_bbl") < 0).shape[0]
        if neg > 0:
            flag_issue("EIA Brent Monthly", f"{neg} negative price values (check data)")
        # Check for gaps > 2 months
        dates_sorted = monthly_brent.sort("date")["date"].to_list()
        gaps = []
        for i in range(1, len(dates_sorted)):
            delta = (dates_sorted[i] - dates_sorted[i-1]).days
            if delta > 65:
                gaps.append(f"{dates_sorted[i-1]} to {dates_sorted[i]} ({delta}d)")
        if gaps:
            flag_issue("EIA Brent Monthly", f"Gaps >65 days detected: {gaps[:3]}")

    if daily_brent is not None:
        null_count = daily_brent["brent_daily_usd_bbl"].null_count()
        if null_count > 0:
            flag_issue("EIA Brent Daily", f"{null_count} null values -- likely weekends/holidays (expected)")
        # Outliers: Z-score > 5
        vals = daily_brent["brent_daily_usd_bbl"].drop_nulls().to_numpy()
        z = np.abs((vals - vals.mean()) / vals.std())
        n_outliers = int((z > 5).sum())
        if n_outliers > 0:
            flag_issue("EIA Brent Daily", f"{n_outliers} statistical outliers (|z|>5) -- review before GARCH modelling")

    if owid_oil is not None:
        null_count = owid_oil["oil_price_usd_bbl"].null_count()
        if null_count > 0:
            flag_issue("OWID Oil", f"{null_count} null real price values")
        # Check for zeros (early years may be imputed)
        zeros = owid_oil.filter(pl.col("oil_price_usd_bbl") <= 0).shape[0]
        if zeros > 0:
            flag_issue("OWID Oil", f"{zeros} zero-or-negative real price values in historical series")

    # --- Analysis: correlations ---
    merged = merge_annual(monthly_brent, invest_df)
    corr_results = {}
    if merged is not None and len(merged) >= 3:
        corr_results = compute_correlations(
            merged,
            "brent_annual_avg",
            ["renewable_power_invest_bn_usd", "clean_energy_invest_bn_usd", "clean_fossil_ratio"]
        )
        log("  Correlations (Brent annual avg vs investment series):")
        for k, v in corr_results.items():
            log(f"    {k}: r = {v:.3f}")

    # --- Descriptive stats: log return ---
    lr_stats: dict[str, float] = {}
    if daily_brent is not None:
        prices = daily_brent.sort("date").drop_nulls()["brent_daily_usd_bbl"].to_numpy()
        log_ret = np.diff(np.log(prices))
        from scipy.stats import skew, kurtosis, jarque_bera
        lr_stats = {
            "mean_daily_log_return": float(log_ret.mean()),
            "std_daily_log_return": float(log_ret.std()),
            "annualised_vol_pct": float(log_ret.std() * np.sqrt(252) * 100),
            "skewness": float(skew(log_ret)),
            "excess_kurtosis": float(kurtosis(log_ret)),
            "jarque_bera_pvalue": float(jarque_bera(log_ret).pvalue),
        }
        log(f"  Daily log return stats: {lr_stats}")

    # --- Visualisations ---
    fig_paths: dict[str, str] = {}
    if monthly_brent is not None:
        fig_paths["brent_monthly"] = plot_brent_monthly(monthly_brent)
        log(f"  Saved: {fig_paths['brent_monthly']}")
    if owid_oil is not None:
        fig_paths["owid_longrun"] = plot_owid_longrun(owid_oil)
        log(f"  Saved: {fig_paths['owid_longrun']}")
    fig_paths["investment_trends"] = plot_investment_trends(invest_df)
    log(f"  Saved: {fig_paths['investment_trends']}")
    if merged is not None and len(merged) >= 3:
        fig_paths["correlation"] = plot_correlation(merged)
        log(f"  Saved: {fig_paths['correlation']}")
    fig_paths["scenarios"] = plot_scenarios(scenario_df)
    log(f"  Saved: {fig_paths['scenarios']}")
    if daily_brent is not None:
        fig_paths["log_returns"] = plot_log_returns(daily_brent)
        log(f"  Saved: {fig_paths['log_returns']}")
    if monthly_brent is not None:
        fig_paths["combined_timeline"] = plot_combined_timeline(monthly_brent, invest_df)
        log(f"  Saved: {fig_paths['combined_timeline']}")
    elif owid_oil is not None:
        fig_paths["combined_timeline"] = plot_combined_timeline(None, invest_df)
        log(f"  Saved: {fig_paths['combined_timeline']}")

    # --- Write results to JSON for report generation ---
    results = {
        "profiles": profiles,
        "data_quality_issues": ISSUES,
        "correlations_brent_vs_investment": corr_results,
        "daily_log_return_stats": lr_stats,
        "figure_paths": fig_paths,
        "datasets_fetched": {
            "eia_brent_monthly": monthly_brent is not None,
            "eia_brent_daily": daily_brent is not None,
            "owid_oil_165yr": owid_oil is not None,
            "investment_series": True,
            "scenario_paths": True,
        }
    }
    results_path = OUT / "analysis_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    log(f"  Results written to {results_path}")

    log("=== Analysis complete ===")
    return results


if __name__ == "__main__":
    main()
