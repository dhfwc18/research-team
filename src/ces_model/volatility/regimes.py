"""
Volatility regime classifier: map GARCH conditional vol forecasts to stress regimes.

Regime mapping (from Code Analyst synthesis-backend-recommendations.md):
  Low vol  (<= P10):   NGFS Current Policies / STEPS baseline (~$65/bbl)
  Med vol  (P10-P75):  NGFS Delayed Transition / APS (~$55/bbl)
  High vol (> P75):    NGFS Net Zero 2050 / geopolitical shock ($25-$130/bbl)

The percentile thresholds are computed from the calibration vol series
(EIA daily, 1987-2026; annualised vol ~40.1%).
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

import numpy as np


class VolRegime(str, Enum):
    """Volatility stress regime."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RegimeThresholds(NamedTuple):
    """Percentile thresholds for regime classification."""

    p10: float  # boundary between LOW and MEDIUM
    p75: float  # boundary between MEDIUM and HIGH


# Default thresholds calibrated from EIA daily 1987-2026 (annualised vol ~40.1%)
# P10 ~ 20%, P75 ~ 50% annualised vol (approximate from historical distribution)
_DEFAULT_THRESHOLDS = RegimeThresholds(p10=0.20, p75=0.50)


def classify_regime(
    annualised_vol: float,
    thresholds: RegimeThresholds = _DEFAULT_THRESHOLDS,
) -> VolRegime:
    """
    Classify a single annualised volatility value into a stress regime.

    Args:
        annualised_vol: Annualised volatility (decimal, e.g. 0.40 = 40%).
        thresholds:     RegimeThresholds(p10, p75).

    Returns:
        VolRegime.LOW, .MEDIUM, or .HIGH.
    """
    if annualised_vol <= thresholds.p10:
        return VolRegime.LOW
    elif annualised_vol <= thresholds.p75:
        return VolRegime.MEDIUM
    else:
        return VolRegime.HIGH


def classify_series(
    annualised_vols: np.ndarray,
    calibration_series: np.ndarray | None = None,
) -> list[VolRegime]:
    """
    Classify an array of annualised volatility values.

    If calibration_series is provided, thresholds are computed as the P10 and
    P75 percentiles of that series (fitted on training data only -- do not
    re-fit on test/scenario data to avoid data leakage).

    Args:
        annualised_vols:   Array of annualised volatility values to classify.
        calibration_series: Optional in-sample vol series for threshold fitting.

    Returns:
        List of VolRegime values.
    """
    if calibration_series is not None:
        cal = np.asarray(calibration_series, dtype=float)
        cal = cal[~np.isnan(cal)]
        thresholds = RegimeThresholds(
            p10=float(np.percentile(cal, 10)),
            p75=float(np.percentile(cal, 75)),
        )
    else:
        thresholds = _DEFAULT_THRESHOLDS

    vols = np.asarray(annualised_vols, dtype=float)
    return [classify_regime(float(v), thresholds) for v in vols]


def regime_to_scenario(regime: VolRegime) -> str:
    """
    Map a volatility regime to the corresponding scenario name.

    Args:
        regime: VolRegime value.

    Returns:
        Scenario name string ('STEPS', 'APS', or a high-stress scenario).
    """
    mapping = {
        VolRegime.LOW: "STEPS",
        VolRegime.MEDIUM: "APS",
        VolRegime.HIGH: "NZE",  # default; HIGH_SHOCK or LOW_SHOCK also apply
    }
    return mapping[regime]
