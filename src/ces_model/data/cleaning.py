"""
Data cleaning and validation utilities for Brent price series.

Key data quality issues from Data Analyst (01-data-analysis.md):
  1. OWID series has unit ambiguity (USD/tonne vs USD/bbl) -- not used here.
  2. EIA daily has two outliers at |z| > 5 (COVID 2020, GFC 2008) -- genuine events,
     retain.
  3. Investment series starts 2015 (annual granularity only).

EIA RBRTE is the authoritative USD/barrel series. Cleaning is conservative:
  - Drop rows with negative or zero prices (instrument errors only).
  - Retain extreme values as genuine price events.
  - Fill short gaps (1-2 months) with linear interpolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class ValidationReport:
    """Summary of validation checks on a Brent price DataFrame."""

    n_rows: int
    n_nulls: int
    n_negatives: int
    n_zeros: int
    min_price: float
    max_price: float
    mean_price: float
    date_range: tuple[str, str]
    gaps_filled: int
    outlier_count: int  # |z| > 5; retained, not dropped
    issues: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0


def clean_brent(
    df: pd.DataFrame,
    price_col: str = "brent_usd_bbl",
    date_col: str = "date",
    fill_gaps: bool = True,
    max_gap_months: int = 2,
) -> pd.DataFrame:
    """
    Clean a Brent price DataFrame.

    Operations (in order):
      1. Sort by date.
      2. Drop rows with null, negative, or zero prices.
      3. Set date as index; resample monthly (for monthly data); fill
         short gaps with linear interpolation if fill_gaps=True.
      4. Reset index.

    Extreme values (COVID crash, GFC peak) are retained as they are genuine
    market observations validated by the Data Analyst.

    Args:
        df:              Input DataFrame with date and price columns.
        price_col:       Name of the price column (float, USD/bbl).
        date_col:        Name of the date column.
        fill_gaps:       If True, linearly interpolate gaps up to max_gap_months.
        max_gap_months:  Maximum consecutive missing months to interpolate.

    Returns:
        Cleaned DataFrame (copy), sorted by date, with reset index.
    """
    out = df[[date_col, price_col]].copy()
    out = out.sort_values(date_col).reset_index(drop=True)

    # Drop invalid prices
    n_before = len(out)
    out = out[out[price_col].notna() & (out[price_col] > 0.0)]
    n_dropped = n_before - len(out)
    if n_dropped > 0:
        pass  # silently dropped; caller can inspect via validate_brent

    if fill_gaps and not out.empty:
        out = _fill_monthly_gaps(out, date_col, price_col, max_gap_months)

    return out.reset_index(drop=True)


def _fill_monthly_gaps(
    df: pd.DataFrame,
    date_col: str,
    price_col: str,
    max_gap_months: int,
) -> pd.DataFrame:
    """Fill short monthly gaps with linear interpolation."""
    df = df.set_index(date_col).sort_index()

    # Only resample if data looks monthly (median gap >= 20 days)
    if len(df) >= 2:
        date_diffs = df.index.to_series().diff().dropna()
        median_gap = date_diffs.median()
        if median_gap.days >= 20:
            monthly = df.resample("MS").mean()
            monthly[price_col] = monthly[price_col].interpolate(
                method="linear", limit=max_gap_months
            )
            df = monthly

    df.index.name = date_col
    return df.reset_index()


def validate_brent(
    df: pd.DataFrame,
    price_col: str = "brent_usd_bbl",
    date_col: str = "date",
) -> ValidationReport:
    """
    Validate a Brent price DataFrame and return a structured report.

    Checks:
      - No null prices.
      - No negative or zero prices.
      - Price range plausibility (1 to 200 USD/bbl for post-1987 Brent).
      - Count of extreme outliers (|z| > 5) for information only.

    Args:
        df:         DataFrame with date and price columns.
        price_col:  Name of the price column.
        date_col:   Name of the date column.

    Returns:
        ValidationReport.
    """
    issues: list[str] = []

    prices = df[price_col]
    n_nulls = int(prices.isna().sum())
    n_negatives = int((prices < 0).sum())
    n_zeros = int((prices == 0).sum())

    if n_nulls > 0:
        issues.append(f"{n_nulls} null values in {price_col}")
    if n_negatives > 0:
        issues.append(f"{n_negatives} negative prices in {price_col}")
    if n_zeros > 0:
        issues.append(f"{n_zeros} zero prices in {price_col}")

    valid = prices.dropna()
    min_p = float(valid.min()) if len(valid) > 0 else float("nan")
    max_p = float(valid.max()) if len(valid) > 0 else float("nan")
    mean_p = float(valid.mean()) if len(valid) > 0 else float("nan")

    # Plausibility check: post-1987 Brent should be between $1 and $200
    if min_p < 1.0:
        issues.append(f"min price {min_p:.2f} below plausibility floor ($1/bbl)")
    if max_p > 200.0:
        issues.append(
            f"max price {max_p:.2f} above plausibility ceiling ($200/bbl) -- "
            "verify units (should be USD/bbl, not USD/tonne)"
        )

    # Outlier count (|z| > 5) -- informational, not a hard failure
    if len(valid) > 2:
        z = (valid - valid.mean()) / valid.std(ddof=1)
        outlier_count = int((np.abs(z) > 5).sum())
    else:
        outlier_count = 0

    dates = df[date_col]
    date_range = (
        str(dates.min().date()) if len(dates) > 0 else "N/A",
        str(dates.max().date()) if len(dates) > 0 else "N/A",
    )

    return ValidationReport(
        n_rows=len(df),
        n_nulls=n_nulls,
        n_negatives=n_negatives,
        n_zeros=n_zeros,
        min_price=min_p,
        max_price=max_p,
        mean_price=mean_p,
        date_range=date_range,
        gaps_filled=0,
        outlier_count=outlier_count,
        issues=issues,
    )


def compute_log_returns(
    df: pd.DataFrame,
    price_col: str = "brent_usd_bbl",
) -> pd.Series:
    """
    Compute daily/monthly log returns from a price series.

    Args:
        df:         DataFrame with price column (sorted by date ascending).
        price_col:  Name of the price column.

    Returns:
        pd.Series of log returns (NaN for the first row).
    """
    prices = df[price_col].to_numpy(dtype=float)
    log_returns = np.empty(len(prices))
    log_returns[0] = np.nan
    log_returns[1:] = np.diff(np.log(prices))
    return pd.Series(log_returns, index=df.index, name="log_return")


def annualise_brent(
    df: pd.DataFrame,
    price_col: str = "brent_usd_bbl",
    date_col: str = "date",
) -> pd.DataFrame:
    """
    Compute annual average Brent price from a monthly or daily series.

    Args:
        df:         Monthly or daily Brent DataFrame.
        price_col:  Name of the price column.
        date_col:   Name of the date column.

    Returns:
        DataFrame with columns: year (int), brent_annual_avg_usd_bbl (float).
    """
    out = df.copy()
    out["year"] = pd.to_datetime(out[date_col]).dt.year
    annual = (
        out.groupby("year")[price_col]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={price_col: "brent_annual_avg_usd_bbl"})
    )
    return annual
