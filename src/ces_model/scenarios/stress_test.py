"""
Stress testing module: run the CES investment model across all scenarios.

For each scenario, computes:
  - Annual renewable investment trajectory (USD bn)
  - Renewable share trajectory (fraction)
  - CAGR vs base year
  - Summary statistics (min, max, terminal value, total 6-year investment)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ces_model.core.ces import CESModel
from ces_model.core.investment import InvestmentResponseModel
from ces_model.scenarios.paths import SCENARIOS, ScenarioPath, get_scenario


@dataclass
class ScenarioResult:
    """Result of running the investment model on a single scenario."""

    scenario: ScenarioPath
    trajectory: list[dict[str, float]]

    @property
    def name(self) -> str:
        return self.scenario.name

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.trajectory)

    def terminal_invest(self) -> float:
        """Investment in the final year (USD bn)."""
        return self.trajectory[-1]["policy_adj_invest_bn_usd"]

    def total_invest(self) -> float:
        """Cumulative investment over the projection period (USD bn)."""
        return sum(r["policy_adj_invest_bn_usd"] for r in self.trajectory)

    def terminal_share(self) -> float:
        """Renewable share in the final year."""
        return self.trajectory[-1]["renew_share"]


@dataclass
class StressTestResult:
    """Aggregated results across all scenarios."""

    scenario_results: dict[str, ScenarioResult] = field(default_factory=dict)

    def to_wide_dataframe(
        self, column: str = "policy_adj_invest_bn_usd"
    ) -> pd.DataFrame:
        """
        Return a wide DataFrame with one column per scenario.

        Args:
            column: Which trajectory column to pivot (default: investment).

        Returns:
            DataFrame indexed by year.
        """
        frames = []
        for name, sr in self.scenario_results.items():
            df = sr.to_dataframe()[["year", column]].copy()
            df = df.rename(columns={column: name})
            frames.append(df.set_index("year"))
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, axis=1).reset_index()

    def summary(self) -> pd.DataFrame:
        """Return a summary table with one row per scenario."""
        rows = []
        for name, sr in self.scenario_results.items():
            traj_df = sr.to_dataframe()
            rows.append(
                {
                    "scenario": name,
                    "label": sr.scenario.label,
                    "vol_regime": sr.scenario.vol_regime,
                    "terminal_invest_bn_usd": round(sr.terminal_invest(), 1),
                    "total_invest_bn_usd": round(sr.total_invest(), 1),
                    "terminal_renew_share": round(sr.terminal_share(), 4),
                    "min_invest_bn_usd": round(
                        traj_df["policy_adj_invest_bn_usd"].min(), 1
                    ),
                    "max_invest_bn_usd": round(
                        traj_df["policy_adj_invest_bn_usd"].max(), 1
                    ),
                }
            )
        return pd.DataFrame(rows).set_index("scenario")


class StressTest:
    """
    Run the CES investment model across all (or selected) scenarios.

    Args:
        ces_model:          Calibrated CES model. Default: CESModel().
        base_invest_bn_usd: Base-year investment (USD bn). Default 807.0.
        policy_multiplier:  Policy uplift factor. Default 1.0.
        capex_decline_rate: CAPEX decline over horizon. Default 0.20.
        projection_start:   First projection year. Default 2025.
    """

    def __init__(
        self,
        ces_model: CESModel | None = None,
        base_invest_bn_usd: float = 807.0,
        policy_multiplier: float = 1.0,
        capex_decline_rate: float = 0.20,
        projection_start: int = 2025,
    ) -> None:
        self._ces = ces_model or CESModel()
        self._irm = InvestmentResponseModel(
            ces=self._ces,
            base_invest_bn_usd=base_invest_bn_usd,
            policy_multiplier=policy_multiplier,
            capex_decline_rate=capex_decline_rate,
        )
        self._projection_start = projection_start

    def run(
        self,
        scenario_names: list[str] | None = None,
    ) -> StressTestResult:
        """
        Run stress test across scenarios.

        Args:
            scenario_names: List of scenario names to run. Default: all five.

        Returns:
            StressTestResult with per-scenario trajectories and summary.
        """
        names = scenario_names or list(SCENARIOS.keys())
        results: dict[str, ScenarioResult] = {}

        for name in names:
            sc = get_scenario(name)
            price_path = sc.projection_path(self._projection_start)
            years = sc.projection_years(self._projection_start)

            trajectory = self._irm.run(price_path, years=years)
            results[name] = ScenarioResult(scenario=sc, trajectory=trajectory)

        return StressTestResult(scenario_results=results)

    def run_single(self, scenario_name: str) -> ScenarioResult:
        """Run a single named scenario and return its result."""
        result = self.run([scenario_name])
        return result.scenario_results[scenario_name.upper()]
