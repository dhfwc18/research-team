"""
EIA Brent crude oil price data fetcher.

Uses the EIA Open Data API v2 (series RBRTE) which is public domain.
API endpoint: https://api.eia.gov/v2/petroleum/pri/spt/data/

Data:
  - Series: RBRTE -- Europe Brent Spot Price FOB, USD/barrel
  - Monthly and daily frequencies available
  - Range: May 1987 to present

Note: The EIA API does not require an API key for the RBRTE series accessed
via the DNAV endpoint. If the API changes, supply EIA_API_KEY as env var.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# EIA API constants
# ---------------------------------------------------------------------------

_EIA_BASE = "https://api.eia.gov/v2/petroleum/pri/spt/data/"
_SERIES_MONTHLY = "RBRTEM"
_SERIES_DAILY = "RBRTED"
_PAGE_SIZE = 5000
_DEFAULT_TIMEOUT = 30

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "ces-model/0.1 (research-team)"})


def _eia_params(
    series_id: str,
    frequency: str,
    offset: int = 0,
    api_key: Optional[str] = None,
) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "data[]": "value",
        "facets[series][]": series_id,
        "frequency": frequency,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": _PAGE_SIZE,
        "offset": offset,
    }
    key = api_key or os.environ.get("EIA_API_KEY")
    if key:
        params["api_key"] = key
    return params


def _fetch_pages(series_id: str, frequency: str) -> list[dict]:
    """Paginate through the EIA API and return all rows."""
    all_rows: list[dict] = []
    offset = 0
    while True:
        params = _eia_params(series_id, frequency, offset)
        try:
            resp = _SESSION.get(_EIA_BASE, params=params, timeout=_DEFAULT_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"EIA API request failed (series={series_id}): {exc}"
            ) from exc

        payload = resp.json()
        rows = payload.get("response", {}).get("data", [])
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
        time.sleep(0.1)  # polite rate limit

    return all_rows


def fetch_brent_monthly(api_key: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch EIA Brent monthly spot prices (RBRTE) from the EIA API.

    Args:
        api_key: Optional EIA API key. Falls back to EIA_API_KEY env var.

    Returns:
        DataFrame with columns: date (datetime64[ns]), brent_usd_bbl (float64).
        Date is the first day of each month (monthly frequency).

    Raises:
        RuntimeError: If the API request fails.
    """
    rows = _fetch_pages(_SERIES_MONTHLY, "monthly")
    if not rows:
        raise RuntimeError("EIA returned no data for RBRTEM (monthly)")

    df = pd.DataFrame(rows)[["period", "value"]].copy()
    df = df.rename(columns={"period": "date", "value": "brent_usd_bbl"})
    df["date"] = pd.to_datetime(df["date"])
    df["brent_usd_bbl"] = pd.to_numeric(df["brent_usd_bbl"], errors="coerce")
    df = df.dropna(subset=["brent_usd_bbl"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def fetch_brent_daily(api_key: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch EIA Brent daily spot prices (RBRTE) from the EIA API.

    Args:
        api_key: Optional EIA API key. Falls back to EIA_API_KEY env var.

    Returns:
        DataFrame with columns: date (datetime64[ns]), brent_daily_usd_bbl (float64).
        Trading days only (weekends and holidays absent -- as expected for spot prices).

    Raises:
        RuntimeError: If the API request fails.
    """
    rows = _fetch_pages(_SERIES_DAILY, "daily")
    if not rows:
        raise RuntimeError("EIA returned no data for RBRTED (daily)")

    df = pd.DataFrame(rows)[["period", "value"]].copy()
    df = df.rename(columns={"period": "date", "value": "brent_daily_usd_bbl"})
    df["date"] = pd.to_datetime(df["date"])
    df["brent_daily_usd_bbl"] = pd.to_numeric(
        df["brent_daily_usd_bbl"], errors="coerce"
    )
    df = df.dropna(subset=["brent_daily_usd_bbl"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def load_brent_monthly(csv_path: str | Path) -> pd.DataFrame:
    """
    Load a locally cached Brent monthly CSV (produced by fetch_brent_monthly).

    Expects columns: date, brent_usd_bbl.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        DataFrame with columns: date (datetime64[ns]), brent_usd_bbl (float64).
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Cached Brent CSV not found: {path}")
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "brent_usd_bbl"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")
    df["brent_usd_bbl"] = pd.to_numeric(df["brent_usd_bbl"], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def load_investment_series() -> pd.DataFrame:
    """
    Return the IEA/IRENA clean and renewable energy investment series (2015-2024).

    Data sourced from:
      - IEA World Energy Investment 2024 (CC BY 4.0)
      - IEA World Energy Investment 2025 (CC BY 4.0)
      - IRENA/CPI Global Landscape of Energy Transition Finance 2025

    Columns:
        year:                         int
        clean_energy_invest_bn_usd:   int  (USD billion)
        fossil_fuel_invest_bn_usd:    int  (USD billion)
        renewable_power_invest_bn_usd: int (USD billion)
        clean_fossil_ratio:           float

    Returns:
        DataFrame with the annual investment series.
    """
    data = {
        "year": list(range(2015, 2025)),
        "clean_energy_invest_bn_usd": [
            590,
            620,
            650,
            680,
            700,
            760,
            960,
            1160,
            1690,
            2100,
        ],
        "fossil_fuel_invest_bn_usd": [
            830,
            760,
            730,
            820,
            870,
            650,
            740,
            900,
            1000,
            1050,
        ],
        "renewable_power_invest_bn_usd": [
            286,
            294,
            305,
            320,
            340,
            380,
            460,
            570,
            620,
            807,
        ],
    }
    df = pd.DataFrame(data)
    df["clean_fossil_ratio"] = (
        df["clean_energy_invest_bn_usd"] / df["fossil_fuel_invest_bn_usd"]
    ).round(2)
    return df
