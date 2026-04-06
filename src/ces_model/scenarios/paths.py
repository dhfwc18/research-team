"""
Scenario Brent crude oil price paths (2020-2030).

Five scenarios calibrated from authoritative sources:

  STEPS (baseline):      IEA Stated Policies Scenario, WEO 2024.
  APS (pledges):         IEA Announced Pledges Scenario, WEO 2024.
  NZE (net zero):        IEA Net Zero Emissions by 2050 Scenario, WEO 2024.
  HIGH_SHOCK:            IMF WP/23/160 (Boer, Pescatori, Stuermer 2023)
                         geopolitical/supply disruption path.
  LOW_SHOCK:             Boer et al. (2023) demand-side climate policy path;
                         aggressive carbon pricing collapses fossil demand.

Historical actuals 2020-2024 anchor all scenarios.
Projection period: 2025-2030.

Sources:
  IEA WEO 2024, Chapter 3 price tables (CC BY 4.0)
  IMF WP/23/160 Boer, Pescatori & Stuermer (2023)
  IEA GEC Model Key Input Data (CC BY 4.0)
  NGFS Phase V Technical Documentation (Nov 2024)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ScenarioPath:
    """
    A named scenario with annual Brent oil price path.

    Attributes:
        name:         Scenario identifier (e.g. 'STEPS').
        label:        Human-readable label.
        source:       Bibliographic source.
        vol_regime:   Expected volatility regime: 'low', 'medium', or 'high'.
        years:        Tuple of years.
        prices_usd:   Tuple of Brent prices (USD/bbl) matching years.
    """

    name: str
    label: str
    source: str
    vol_regime: str
    years: tuple[int, ...]
    prices_usd: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.years) != len(self.prices_usd):
            raise ValueError("years and prices_usd must have the same length")
        if self.vol_regime not in {"low", "medium", "high"}:
            raise ValueError(
                "vol_regime must be 'low', 'medium', or 'high',"
                f" got {self.vol_regime!r}"
            )

    def to_dataframe(self) -> pd.DataFrame:
        """Return the scenario as a DataFrame with columns: year, price_usd_bbl."""
        return pd.DataFrame(
            {"year": list(self.years), "price_usd_bbl": list(self.prices_usd)}
        )

    def projection_path(self, start_year: int = 2025) -> list[float]:
        """Return only the projection years (>= start_year) as a list of prices."""
        return [p for y, p in zip(self.years, self.prices_usd) if y >= start_year]

    def projection_years(self, start_year: int = 2025) -> list[int]:
        """Return only the projection years (>= start_year)."""
        return [y for y in self.years if y >= start_year]


# ---------------------------------------------------------------------------
# Scenario definitions
# Historical actuals 2020-2024 anchored from EIA RBRTE; projections from sources above.
# ---------------------------------------------------------------------------

_YEARS = tuple(range(2020, 2031))

SCENARIOS: dict[str, ScenarioPath] = {
    "STEPS": ScenarioPath(
        name="STEPS",
        label="IEA Stated Policies (Baseline)",
        source="IEA WEO 2024, Chapter 3; IEA STEO March 2026",
        vol_regime="low",
        years=_YEARS,
        prices_usd=(
            # 2020  2021  2022   2023   2024   2025  2026  2027  2028  2029  2030
            42.0,
            70.0,
            101.0,
            82.0,
            80.0,
            75.0,
            72.0,
            70.0,
            68.0,
            67.0,
            65.0,
        ),
    ),
    "APS": ScenarioPath(
        name="APS",
        label="IEA Announced Pledges",
        source="IEA WEO 2024, Chapter 3",
        vol_regime="medium",
        years=_YEARS,
        prices_usd=(42.0, 70.0, 101.0, 82.0, 80.0, 70.0, 67.0, 63.0, 60.0, 57.0, 55.0),
    ),
    "NZE": ScenarioPath(
        name="NZE",
        label="IEA Net Zero Emissions 2050",
        source="IEA WEO 2024, Chapter 3",
        vol_regime="high",
        years=_YEARS,
        prices_usd=(42.0, 70.0, 101.0, 82.0, 80.0, 65.0, 60.0, 55.0, 50.0, 47.0, 44.0),
    ),
    "HIGH_SHOCK": ScenarioPath(
        name="HIGH_SHOCK",
        label="Geopolitical / Supply Disruption",
        source="IMF WP/23/160 (Boer, Pescatori & Stuermer 2023); IMF WEO upside risk",
        vol_regime="high",
        years=_YEARS,
        prices_usd=(
            42.0,
            70.0,
            101.0,
            82.0,
            80.0,
            90.0,
            100.0,
            110.0,
            120.0,
            125.0,
            130.0,
        ),
    ),
    "LOW_SHOCK": ScenarioPath(
        name="LOW_SHOCK",
        label="Demand Destruction / Climate Policy",
        source="Boer, Pescatori & Stuermer (2023) IMF WP/23/160 demand-side scenario",
        vol_regime="high",
        years=_YEARS,
        prices_usd=(42.0, 70.0, 101.0, 82.0, 80.0, 60.0, 50.0, 40.0, 33.0, 28.0, 25.0),
    ),
}


def get_scenario(name: str) -> ScenarioPath:
    """
    Retrieve a scenario by name.

    Args:
        name: One of 'STEPS', 'APS', 'NZE', 'HIGH_SHOCK', 'LOW_SHOCK'.

    Returns:
        ScenarioPath.

    Raises:
        KeyError: If name is not recognised.
    """
    key = name.upper()
    if key not in SCENARIOS:
        raise KeyError(
            f"Unknown scenario {name!r}. Available: {list(SCENARIOS.keys())}"
        )
    return SCENARIOS[key]


def list_scenarios() -> list[str]:
    """Return the list of available scenario names."""
    return list(SCENARIOS.keys())


def scenarios_to_dataframe() -> pd.DataFrame:
    """
    Return all scenarios as a wide DataFrame indexed by year.

    Columns: year, STEPS, APS, NZE, HIGH_SHOCK, LOW_SHOCK (prices in USD/bbl).
    """
    frames = []
    for name, sc in SCENARIOS.items():
        df = sc.to_dataframe().rename(columns={"price_usd_bbl": name})
        frames.append(df.set_index("year"))
    combined = pd.concat(frames, axis=1).reset_index()
    combined = combined.rename(columns={"index": "year"})
    return combined


def interpolate_annual_path(
    start_year: int,
    end_year: int,
    start_price: float,
    end_price: float,
) -> tuple[tuple[int, ...], tuple[float, ...]]:
    """
    Build a linear annual price path between two anchor points.

    Args:
        start_year:  First year.
        end_year:    Last year (inclusive).
        start_price: Brent price at start_year (USD/bbl).
        end_price:   Brent price at end_year (USD/bbl).

    Returns:
        Tuple of (years, prices).
    """
    years = tuple(range(start_year, end_year + 1))
    prices = tuple(float(p) for p in np.linspace(start_price, end_price, len(years)))
    return years, prices
