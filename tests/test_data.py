"""Tests for data loading and cleaning utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ces_model.data.cleaning import (
    ValidationReport,
    annualise_brent,
    clean_brent,
    compute_log_returns,
    validate_brent,
)
from ces_model.data.eia import load_investment_series

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_brent_df(n: int = 12, start: str = "2023-01-01") -> pd.DataFrame:
    """Create a simple synthetic monthly Brent DataFrame for testing."""
    dates = pd.date_range(start, periods=n, freq="MS")
    prices = np.linspace(60.0, 80.0, n)
    return pd.DataFrame({"date": dates, "brent_usd_bbl": prices})


# ---------------------------------------------------------------------------
# clean_brent
# ---------------------------------------------------------------------------


class TestCleanBrent:
    def test_sorts_ascending(self) -> None:
        df = _make_brent_df()
        df = df.iloc[::-1]  # reverse order
        cleaned = clean_brent(df)
        assert cleaned["date"].is_monotonic_increasing

    def test_drops_negative_prices(self) -> None:
        df = _make_brent_df()
        df.loc[0, "brent_usd_bbl"] = -5.0
        cleaned = clean_brent(df)
        assert (cleaned["brent_usd_bbl"] > 0).all()

    def test_drops_zero_prices(self) -> None:
        df = _make_brent_df()
        df.loc[1, "brent_usd_bbl"] = 0.0
        cleaned = clean_brent(df)
        assert (cleaned["brent_usd_bbl"] > 0).all()

    def test_drops_null_prices(self) -> None:
        df = _make_brent_df()
        df.loc[2, "brent_usd_bbl"] = float("nan")
        cleaned = clean_brent(df)
        assert cleaned["brent_usd_bbl"].notna().all()

    def test_extreme_values_retained(self) -> None:
        """COVID crash / GFC spike are genuine events -- should not be dropped."""
        df = _make_brent_df()
        df.loc[0, "brent_usd_bbl"] = 9.1  # COVID 2020 low
        df.loc[1, "brent_usd_bbl"] = 133.9  # 2008 GFC peak
        cleaned = clean_brent(df, fill_gaps=False)
        assert 9.1 in cleaned["brent_usd_bbl"].values
        assert 133.9 in cleaned["brent_usd_bbl"].values

    def test_returns_copy(self) -> None:
        df = _make_brent_df()
        cleaned = clean_brent(df)
        assert df is not cleaned


# ---------------------------------------------------------------------------
# validate_brent
# ---------------------------------------------------------------------------


class TestValidateBrent:
    def test_clean_df_no_issues(self) -> None:
        df = _make_brent_df()
        report = validate_brent(df)
        assert isinstance(report, ValidationReport)
        assert report.is_clean

    def test_reports_nulls(self) -> None:
        df = _make_brent_df()
        df.loc[0, "brent_usd_bbl"] = float("nan")
        report = validate_brent(df)
        assert report.n_nulls == 1
        assert not report.is_clean

    def test_reports_negatives(self) -> None:
        df = _make_brent_df()
        df.loc[0, "brent_usd_bbl"] = -1.0
        report = validate_brent(df)
        assert report.n_negatives == 1

    def test_high_price_triggers_unit_warning(self) -> None:
        df = _make_brent_df()
        df.loc[0, "brent_usd_bbl"] = 500.0  # clearly USD/tonne not USD/bbl
        report = validate_brent(df)
        assert any("plausibility ceiling" in issue for issue in report.issues)

    def test_date_range_populated(self) -> None:
        df = _make_brent_df()
        report = validate_brent(df)
        assert report.date_range[0] != "N/A"
        assert report.date_range[1] != "N/A"

    def test_outlier_count(self) -> None:
        """|z|>5 outliers counted but not flagged as hard issues."""
        df = _make_brent_df(50)
        # Inject a large outlier
        df.loc[0, "brent_usd_bbl"] = 10000.0
        report = validate_brent(df)
        assert report.outlier_count >= 1


# ---------------------------------------------------------------------------
# compute_log_returns
# ---------------------------------------------------------------------------


class TestComputeLogReturns:
    def test_first_element_is_nan(self) -> None:
        df = _make_brent_df()
        returns = compute_log_returns(df)
        assert np.isnan(returns.iloc[0])

    def test_length_matches_input(self) -> None:
        df = _make_brent_df(24)
        returns = compute_log_returns(df)
        assert len(returns) == 24

    def test_constant_series_returns_zero(self) -> None:
        df = _make_brent_df()
        df["brent_usd_bbl"] = 65.0
        returns = compute_log_returns(df)
        assert np.allclose(returns.dropna(), 0.0)


# ---------------------------------------------------------------------------
# annualise_brent
# ---------------------------------------------------------------------------


class TestAnnualiseBrent:
    def test_returns_annual_dataframe(self) -> None:
        df = _make_brent_df(24, "2022-01-01")
        annual = annualise_brent(df)
        assert "year" in annual.columns
        assert "brent_annual_avg_usd_bbl" in annual.columns

    def test_two_years_of_monthly_data(self) -> None:
        df = _make_brent_df(24, "2022-01-01")
        annual = annualise_brent(df)
        assert len(annual) == 2

    def test_values_within_input_range(self) -> None:
        df = _make_brent_df(12, "2023-01-01")
        annual = annualise_brent(df)
        assert annual["brent_annual_avg_usd_bbl"].iloc[0] >= df["brent_usd_bbl"].min()
        assert annual["brent_annual_avg_usd_bbl"].iloc[0] <= df["brent_usd_bbl"].max()


# ---------------------------------------------------------------------------
# load_investment_series
# ---------------------------------------------------------------------------


class TestLoadInvestmentSeries:
    def test_shape(self) -> None:
        df = load_investment_series()
        assert len(df) == 10
        assert "year" in df.columns

    def test_year_range(self) -> None:
        df = load_investment_series()
        assert df["year"].min() == 2015
        assert df["year"].max() == 2024

    def test_clean_fossil_ratio_computed(self) -> None:
        df = load_investment_series()
        assert "clean_fossil_ratio" in df.columns
        assert (df["clean_fossil_ratio"] > 0).all()

    def test_2024_renewable_investment(self) -> None:
        df = load_investment_series()
        row_2024 = df[df["year"] == 2024].iloc[0]
        assert row_2024["renewable_power_invest_bn_usd"] == 807
