"""
Volatility forecast evaluation metrics.

Implements RMSE, MAE, MMEO (mean mixed error -- over), and MMEU (mean mixed
error -- under) from the Chung (2024) GARCH/ML evaluation framework.

MMEO and MMEU distinguish over- vs. under-prediction of volatility, which
matters for risk management: under-predicting vol is more costly.
"""

from __future__ import annotations

import numpy as np


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Root Mean Squared Error.

    Args:
        actual:    Realised volatility values.
        predicted: Forecast volatility values.

    Returns:
        RMSE (same units as inputs).
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = ~(np.isnan(actual) | np.isnan(predicted))
    if mask.sum() == 0:
        return float("nan")
    return float(np.sqrt(np.mean((actual[mask] - predicted[mask]) ** 2)))


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Mean Absolute Error.

    Args:
        actual:    Realised volatility values.
        predicted: Forecast volatility values.

    Returns:
        MAE (same units as inputs).
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = ~(np.isnan(actual) | np.isnan(predicted))
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs(actual[mask] - predicted[mask])))


def mmeo(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Mean Mixed Error -- Over (MMEO).

    Penalises forecast over-predictions more than under-predictions.
    MMEO = mean(max(predicted - actual, 0)).

    Args:
        actual:    Realised volatility values.
        predicted: Forecast volatility values.

    Returns:
        MMEO.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = ~(np.isnan(actual) | np.isnan(predicted))
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.maximum(predicted[mask] - actual[mask], 0.0)))


def mmeu(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Mean Mixed Error -- Under (MMEU).

    Penalises forecast under-predictions more than over-predictions.
    MMEU = mean(max(actual - predicted, 0)).

    Under-prediction of volatility is more costly for risk management
    (scenarios may be under-stressed).

    Args:
        actual:    Realised volatility values.
        predicted: Forecast volatility values.

    Returns:
        MMEU.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = ~(np.isnan(actual) | np.isnan(predicted))
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.maximum(actual[mask] - predicted[mask], 0.0)))


def evaluate_vol_forecast(
    actual: np.ndarray,
    predicted: np.ndarray,
) -> dict[str, float]:
    """
    Compute all four volatility forecast metrics.

    Args:
        actual:    Realised volatility values.
        predicted: Forecast volatility values.

    Returns:
        Dict with keys: rmse, mae, mmeo, mmeu.
    """
    return {
        "rmse": rmse(actual, predicted),
        "mae": mae(actual, predicted),
        "mmeo": mmeo(actual, predicted),
        "mmeu": mmeu(actual, predicted),
    }
