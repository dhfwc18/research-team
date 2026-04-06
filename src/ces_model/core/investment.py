"""
Investment response model anchored to CES substitution and Mukhtarov elasticity.

Translates oil price changes into renewable investment flows using:
  1. CES share function (Papageorgiou et al. 2017, sigma=1.8)
  2. Empirical elasticity anchor (Mukhtarov et al. 2024, +0.16% per 1% oil rise)
  3. Technology learning curve (Wright's law CAPEX decline)
  4. Policy multiplier (IRA/REPowerEU-style exogenous investment boost)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ces_model.core.ces import CESModel


@dataclass
class InvestmentResponseModel:
    """
    End-to-end renewable investment response to oil price paths.

    Wraps the CES model and adds:
      - Policy multiplier for exogenous investment shocks (e.g. IRA).
      - Technology learning curve via CAPEX decline.
      - Annualised CAGR tracking for the output trajectory.

    Attributes:
        ces:                     Underlying CES model.
        base_invest_bn_usd:      Base-year renewable investment (USD bn). Default 807.0
                                 (IEA/IRENA renewable power investment 2024).
        policy_multiplier:       Exogenous policy boost factor >= 1.0.
                                 1.0 = no policy effect; 1.2 = 20% policy uplift.
        capex_decline_rate:      Fractional CAPEX decline over the forecast horizon.
    """

    ces: CESModel = field(default_factory=CESModel)
    base_invest_bn_usd: float = 807.0
    policy_multiplier: float = 1.0
    capex_decline_rate: float = 0.20

    def __post_init__(self) -> None:
        if self.policy_multiplier < 1.0:
            raise ValueError(
                f"policy_multiplier must be >= 1.0, got {self.policy_multiplier}"
            )
        if not (0.0 <= self.capex_decline_rate <= 1.0):
            raise ValueError(
                f"capex_decline_rate must be in [0, 1], got {self.capex_decline_rate}"
            )

    def run(
        self,
        price_path: list[float] | np.ndarray,
        years: list[int] | None = None,
    ) -> list[dict[str, float]]:
        """
        Run the investment response over a scenario price path.

        Args:
            price_path: Annual Brent oil prices (USD/bbl) over the horizon.
            years:      Optional list of years corresponding to each price step.
                        If None, steps are labelled 0, 1, 2, ...

        Returns:
            List of dicts per time step:
                year, price_oil, renew_share, renew_invest_bn_usd,
                policy_adj_invest_bn_usd, cagr_vs_base.
        """
        prices = np.asarray(price_path, dtype=float)
        n = len(prices)
        if years is None:
            years_list = list(range(n))
        else:
            if len(years) != n:
                raise ValueError("years and price_path must have the same length")
            years_list = list(years)

        trajectory = self.ces.investment_trajectory(
            price_path=prices,
            base_invest_bn_usd=self.base_invest_bn_usd,
            capex_decline_rate=self.capex_decline_rate,
        )

        results: list[dict[str, float]] = []
        base_invest = self.base_invest_bn_usd
        for i, row in enumerate(trajectory):
            raw_invest = row["renew_invest_bn_usd"]
            adj_invest = raw_invest * self.policy_multiplier

            # CAGR relative to base year
            if i == 0 or base_invest <= 0.0:
                cagr = 0.0
            else:
                cagr = (adj_invest / base_invest) ** (1.0 / i) - 1.0

            results.append(
                {
                    "year": float(years_list[i]),
                    "price_oil": row["price_oil"],
                    "renew_share": row["renew_share"],
                    "renew_invest_bn_usd": raw_invest,
                    "policy_adj_invest_bn_usd": adj_invest,
                    "cagr_vs_base": cagr,
                }
            )

        return results

    def compare_scenarios(
        self,
        scenario_paths: dict[str, list[float] | np.ndarray],
        years: list[int] | None = None,
    ) -> dict[str, list[dict[str, float]]]:
        """
        Run investment response for multiple named scenarios.

        Args:
            scenario_paths: Mapping of scenario name -> oil price path.
            years:          Optional year labels (shared across scenarios).

        Returns:
            Mapping of scenario name -> trajectory (list of row dicts).
        """
        return {
            name: self.run(path, years=years) for name, path in scenario_paths.items()
        }
