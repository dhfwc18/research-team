"""
ces_model -- CES substitution model for Brent oil / renewable energy investment
analysis.

Submodules:
    core        -- CES production function and investment response
    data        -- EIA data fetcher and cleaning utilities
    scenarios   -- Scenario price paths and stress testing
    sensitivity -- Morris global sensitivity analysis (SALib-based)
    volatility  -- GARCH volatility modelling and regime mapping
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ces-model")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = ["__version__"]
