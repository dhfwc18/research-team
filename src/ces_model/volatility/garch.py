"""
GARCH(1,1) volatility model wrapper for Brent crude oil returns.

Implements Chung (2024) GARCH/ML specification:
  arch_model(returns * 100, vol='GARCH', p=1, q=1, dist='t').fit()

Student-t errors are appropriate given the extreme fat tails in Brent returns
(excess kurtosis ~63.4, Data Analyst 01-data-analysis.md).

The `arch` library (BSD licence) is used throughout.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

try:
    from arch import arch_model as _arch_model
    from arch.univariate import ARCHModelResult as _ARCHResult

    _ARCH_AVAILABLE = True
except ImportError:
    _ARCH_AVAILABLE = False
    _arch_model = None  # type: ignore[assignment]
    _ARCHResult = Any  # type: ignore[assignment, misc]


def _require_arch() -> None:
    if not _ARCH_AVAILABLE:
        raise ImportError(
            "The 'arch' package is required for GARCH modelling. "
            "Install with: uv add arch"
        )


@dataclass
class GARCHForecast:
    """One-step-ahead conditional volatility forecast from GARCH(1,1)."""

    conditional_vol: np.ndarray
    annualised_vol: np.ndarray
    forecast_horizon: int
    mean_conditional_vol: float
    residuals: np.ndarray


class GARCHModel:
    """
    GARCH(1,1) with Student-t errors for Brent daily log returns.

    Follows Chung (2024): scale returns by 100 before fitting
    (standard practice for daily percentage returns).

    Attributes:
        p:    ARCH lag order (default 1).
        q:    GARCH lag order (default 1).
        dist: Error distribution ('t' for Student-t, 'normal' for Gaussian).
        trading_days: Annual trading days for annualisation.
    """

    def __init__(
        self,
        p: int = 1,
        q: int = 1,
        dist: str = "t",
        trading_days: int = 252,
    ) -> None:
        _require_arch()
        self.p = p
        self.q = q
        self.dist = dist
        self.trading_days = trading_days
        self._result: _ARCHResult | None = None

    def fit(
        self,
        log_returns: np.ndarray | pd.Series,
        disp: str = "off",
    ) -> "GARCHModel":
        """
        Fit the GARCH(1,1) model.

        Args:
            log_returns: Daily log returns (not percentage; will be scaled x100).
            disp:        Optimisation output display ('off' or 'final').

        Returns:
            Self (for method chaining).
        """
        _require_arch()
        returns_pct = np.asarray(log_returns, dtype=float) * 100.0
        # Drop leading NaN
        returns_pct = returns_pct[~np.isnan(returns_pct)]

        model = _arch_model(
            returns_pct,
            vol="GARCH",
            p=self.p,
            q=self.q,
            dist=self.dist,
            rescale=False,
        )
        self._result = model.fit(disp=disp)
        return self

    def forecast(self, horizon: int = 1) -> GARCHForecast:
        """
        Produce conditional volatility forecast.

        Args:
            horizon: Number of steps ahead to forecast.

        Returns:
            GARCHForecast with conditional and annualised volatility.

        Raises:
            RuntimeError: If model has not been fitted.
        """
        if self._result is None:
            raise RuntimeError("Model has not been fitted. Call .fit() first.")

        cond_vol_pct = self._result.conditional_volatility
        # Convert back from % to decimal
        cond_vol = cond_vol_pct / 100.0
        annualised = cond_vol * np.sqrt(self.trading_days)

        return GARCHForecast(
            conditional_vol=cond_vol,
            annualised_vol=annualised,
            forecast_horizon=horizon,
            mean_conditional_vol=float(np.nanmean(annualised)),
            residuals=self._result.resid / 100.0,
        )

    def summary(self) -> str:
        """Return the ARCH model fit summary as a string."""
        if self._result is None:
            return "Model not fitted."
        return str(self._result.summary())


def fit_garch(
    log_returns: np.ndarray | pd.Series,
    p: int = 1,
    q: int = 1,
    dist: str = "t",
    trading_days: int = 252,
) -> GARCHForecast:
    """
    Convenience function: fit GARCH(p,q) and return a forecast.

    Args:
        log_returns:  Daily log returns.
        p:            ARCH lag order.
        q:            GARCH lag order.
        dist:         Error distribution ('t' or 'normal').
        trading_days: Annual trading days.

    Returns:
        GARCHForecast.
    """
    model = GARCHModel(p=p, q=q, dist=dist, trading_days=trading_days)
    model.fit(log_returns)
    return model.forecast()
