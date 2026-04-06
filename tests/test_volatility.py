"""Tests for volatility features, evaluation metrics, and regime classification."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ces_model.volatility.evaluate import evaluate_vol_forecast, mae, mmeo, mmeu, rmse
from ces_model.volatility.features import (
    build_feature_matrix,
    compute_log_returns,
    compute_vol_proxy,
)
from ces_model.volatility.regimes import (
    RegimeThresholds,
    VolRegime,
    classify_regime,
    classify_series,
    regime_to_scenario,
)

# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


class TestFeatures:
    def _brent_df(self, n: int = 100) -> pd.DataFrame:
        np.random.seed(42)
        prices = 65.0 * np.exp(np.cumsum(np.random.normal(0, 0.02, n)))
        dates = pd.date_range("2020-01-01", periods=n, freq="B")
        return pd.DataFrame({"date": dates, "brent_daily_usd_bbl": prices})

    def test_log_returns_length(self) -> None:
        prices = np.array([60.0, 62.0, 61.0, 63.0])
        ret = compute_log_returns(prices)
        assert len(ret) == 4
        assert np.isnan(ret[0])

    def test_log_returns_positive_price_rise(self) -> None:
        prices = np.array([60.0, 66.0])
        ret = compute_log_returns(prices)
        assert ret[1] > 0.0

    def test_vol_proxy_annualised(self) -> None:
        np.random.seed(0)
        ret = np.concatenate([[np.nan], np.random.normal(0, 0.025, 200)])
        vol = compute_vol_proxy(ret, window=22, trading_days=252)
        # After warm-up, vol should be roughly 0.4 annualised (0.025*sqrt(252)~0.397)
        valid = vol[~np.isnan(vol)]
        assert valid.mean() == pytest.approx(0.4, abs=0.15)

    def test_feature_matrix_columns(self) -> None:
        df = self._brent_df(200)
        feat = build_feature_matrix(df)
        assert "log_return" in feat.columns
        assert "vol_proxy_22d" in feat.columns
        assert "return_lag_1" in feat.columns

    def test_feature_matrix_no_nulls(self) -> None:
        df = self._brent_df(200)
        feat = build_feature_matrix(df)
        assert feat.isna().sum().sum() == 0

    def test_feature_matrix_shorter_than_input(self) -> None:
        df = self._brent_df(200)
        feat = build_feature_matrix(df)
        # Dropped for lags and vol warm-up
        assert len(feat) < len(df)


# ---------------------------------------------------------------------------
# Evaluation metrics
# ---------------------------------------------------------------------------


class TestEvaluationMetrics:
    def test_rmse_perfect_forecast(self) -> None:
        y = np.array([0.3, 0.4, 0.5])
        assert rmse(y, y) == pytest.approx(0.0)

    def test_mae_perfect_forecast(self) -> None:
        y = np.array([0.3, 0.4, 0.5])
        assert mae(y, y) == pytest.approx(0.0)

    def test_mmeo_no_overprediction(self) -> None:
        actual = np.array([0.4, 0.5, 0.6])
        predicted = np.array([0.3, 0.4, 0.5])  # all under-predictions
        assert mmeo(actual, predicted) == pytest.approx(0.0)

    def test_mmeu_no_underprediction(self) -> None:
        actual = np.array([0.3, 0.4, 0.5])
        predicted = np.array([0.4, 0.5, 0.6])  # all over-predictions
        assert mmeu(actual, predicted) == pytest.approx(0.0)

    def test_rmse_known_value(self) -> None:
        actual = np.array([0.0, 0.0])
        predicted = np.array([1.0, 1.0])
        assert rmse(actual, predicted) == pytest.approx(1.0)

    def test_evaluate_returns_all_keys(self) -> None:
        actual = np.array([0.3, 0.4, 0.5])
        predicted = np.array([0.32, 0.38, 0.52])
        result = evaluate_vol_forecast(actual, predicted)
        assert set(result.keys()) == {"rmse", "mae", "mmeo", "mmeu"}
        assert all(v >= 0.0 for v in result.values())

    def test_nan_handling(self) -> None:
        actual = np.array([0.3, np.nan, 0.5])
        predicted = np.array([0.32, 0.40, 0.52])
        result = evaluate_vol_forecast(actual, predicted)
        # Should compute on non-nan pairs only
        assert not np.isnan(result["rmse"])


# ---------------------------------------------------------------------------
# Regime classification
# ---------------------------------------------------------------------------


class TestRegimes:
    def test_low_regime(self) -> None:
        assert classify_regime(0.10) == VolRegime.LOW

    def test_medium_regime(self) -> None:
        assert classify_regime(0.35) == VolRegime.MEDIUM

    def test_high_regime(self) -> None:
        assert classify_regime(0.60) == VolRegime.HIGH

    def test_boundary_at_p10(self) -> None:
        thresh = RegimeThresholds(p10=0.20, p75=0.50)
        assert classify_regime(0.20, thresh) == VolRegime.LOW

    def test_classify_series(self) -> None:
        vols = np.array([0.10, 0.35, 0.65])
        regimes = classify_series(vols)
        assert regimes[0] == VolRegime.LOW
        assert regimes[1] == VolRegime.MEDIUM
        assert regimes[2] == VolRegime.HIGH

    def test_classify_series_with_calibration(self) -> None:
        cal = np.linspace(0.1, 0.8, 100)
        vols = np.array([0.1, 0.5, 0.9])
        regimes = classify_series(vols, calibration_series=cal)
        assert len(regimes) == 3

    def test_regime_to_scenario(self) -> None:
        assert regime_to_scenario(VolRegime.LOW) == "STEPS"
        assert regime_to_scenario(VolRegime.MEDIUM) == "APS"
        assert regime_to_scenario(VolRegime.HIGH) in {"NZE", "HIGH_SHOCK", "LOW_SHOCK"}

    def test_vol_regime_enum_values(self) -> None:
        assert VolRegime.LOW.value == "low"
        assert VolRegime.MEDIUM.value == "medium"
        assert VolRegime.HIGH.value == "high"
