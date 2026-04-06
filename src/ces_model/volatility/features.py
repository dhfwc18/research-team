"""
Feature engineering for Brent volatility modelling.

Implements log-return computation, rolling volatility proxy, and
macro feature pipeline consistent with Chung (2024) GARCH/ML methodology.

Annualised volatility: 40.1% (EIA daily, 1987-2026) with severe fat tails
(skewness -1.68, excess kurtosis 63.4) -- GARCH(1,1) with Student-t errors
is appropriate (Data Analyst, 01-data-analysis.md).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_log_returns(
    prices: pd.Series | np.ndarray,
) -> np.ndarray:
    """
    Compute log returns from a price series.

    Args:
        prices: Price series (sorted ascending, no NaNs).

    Returns:
        Log return array of same length (first element is NaN).
    """
    arr = np.asarray(prices, dtype=float)
    returns = np.empty(len(arr))
    returns[0] = np.nan
    returns[1:] = np.diff(np.log(arr))
    return returns


def compute_vol_proxy(
    log_returns: np.ndarray,
    window: int = 22,
    trading_days: int = 252,
) -> np.ndarray:
    """
    Compute rolling realised volatility as a proxy for the GARCH target.

    Args:
        log_returns:  Daily log returns (NaN for first element).
        window:       Rolling window in trading days. Default 22 (~1 month).
        trading_days: Annual trading days for annualisation. Default 252.

    Returns:
        Array of annualised rolling volatility (NaN for first window-1 rows).
    """
    returns = pd.Series(log_returns).dropna()
    rolling_std = returns.rolling(window=window, min_periods=window).std()
    annualised = rolling_std * np.sqrt(trading_days)
    # Re-align to original index
    result = np.full(len(log_returns), np.nan)
    n_valid = len(returns)
    result[-n_valid:] = annualised.to_numpy()
    return result


def build_feature_matrix(
    df: pd.DataFrame,
    price_col: str = "brent_daily_usd_bbl",
    date_col: str = "date",
    lags: int = 5,
    vol_window: int = 22,
) -> pd.DataFrame:
    """
    Build a feature matrix for volatility modelling from a Brent price DataFrame.

    Features:
      - log_return:       Daily log return.
      - vol_proxy_22d:    22-day rolling annualised volatility.
      - return_lag_{1..n}: Lagged log returns (for ARCH-in-mean / ML inputs).
      - vol_lag_22d:      Lagged 22-day volatility.
      - abs_return:       Absolute log return (leverage proxy).
      - squared_return:   Squared log return (ARCH term).

    Args:
        df:          Brent daily DataFrame (sorted by date ascending).
        price_col:   Name of the price column.
        date_col:    Name of the date column.
        lags:        Number of lagged return features to include.
        vol_window:  Rolling window for vol proxy.

    Returns:
        DataFrame with date index and feature columns; rows with NaN dropped.
    """
    out = df[[date_col, price_col]].copy().sort_values(date_col).reset_index(drop=True)
    prices = out[price_col].to_numpy(dtype=float)

    log_ret = compute_log_returns(prices)
    vol_prx = compute_vol_proxy(log_ret, window=vol_window)

    feat = pd.DataFrame({date_col: out[date_col]})
    feat["log_return"] = log_ret
    feat["vol_proxy_22d"] = vol_prx
    feat["abs_return"] = np.abs(log_ret)
    feat["squared_return"] = log_ret**2

    for lag in range(1, lags + 1):
        feat[f"return_lag_{lag}"] = feat["log_return"].shift(lag)

    feat["vol_lag_22d"] = feat["vol_proxy_22d"].shift(1)
    feat = feat.dropna().reset_index(drop=True)
    return feat
