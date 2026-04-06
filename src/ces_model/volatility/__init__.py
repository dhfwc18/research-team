"""GARCH volatility modelling and stress regime classification."""

from ces_model.volatility.evaluate import evaluate_vol_forecast
from ces_model.volatility.features import build_feature_matrix, compute_vol_proxy
from ces_model.volatility.garch import GARCHModel, fit_garch
from ces_model.volatility.regimes import VolRegime, classify_regime

__all__ = [
    "GARCHModel",
    "fit_garch",
    "build_feature_matrix",
    "compute_vol_proxy",
    "evaluate_vol_forecast",
    "classify_regime",
    "VolRegime",
]
