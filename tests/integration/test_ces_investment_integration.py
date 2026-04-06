"""
Integration tests: CES core + Investment model.

Tests that cross the boundary between ces_model.core.ces and
ces_model.core.investment, verifying that the two modules interact
correctly and produce economically coherent results.
"""

from __future__ import annotations

import pytest

from ces_model.core.ces import CESModel, ces_substitution
from ces_model.core.investment import InvestmentResponseModel


class TestCESShareCalculationKnownInputs:
    """Verify share calculations for specific calibrated inputs."""

    def test_share_calculation_parity_alpha_03_sigma_18(self) -> None:
        """At price parity, renew_share equals alpha exactly (sigma=1.8)."""
        result = ces_substitution(65.0, 65.0, sigma=1.8, alpha=0.30)
        assert abs(result.renew_share - 0.30) < 1e-9

    def test_share_calculation_fossil_price_rise_increases_renew_share(self) -> None:
        """Raising fossil price while holding renew price raises renewable share."""
        base = ces_substitution(65.0, 1.0, sigma=1.8, alpha=0.30)
        shocked = ces_substitution(80.0, 1.0, sigma=1.8, alpha=0.30)
        assert shocked.renew_share > base.renew_share

    def test_share_calculation_very_large_oil_price_stable(self) -> None:
        """Very large oil price (e.g. 10,000 USD/bbl) does not produce NaN/inf."""
        result = ces_substitution(10_000.0, 1.0, sigma=1.8, alpha=0.30)
        assert 0.0 <= result.renew_share <= 1.0
        assert result.fossil_share >= 0.0

    def test_share_calculation_very_large_renew_price_stable(self) -> None:
        """Very large renewable price (fossil much cheaper) stays in [0, 1]."""
        result = ces_substitution(65.0, 10_000.0, sigma=1.8, alpha=0.30)
        assert 0.0 <= result.renew_share <= 1.0

    def test_share_calculation_sigma_1_cobb_douglas_ignores_prices(self) -> None:
        """sigma=1 (Cobb-Douglas limit): share equals alpha regardless of prices."""
        r_cheap_fossil = ces_substitution(10.0, 1000.0, sigma=1.0, alpha=0.25)
        r_expensive_fossil = ces_substitution(1000.0, 10.0, sigma=1.0, alpha=0.25)
        assert abs(r_cheap_fossil.renew_share - 0.25) < 1e-9
        assert abs(r_expensive_fossil.renew_share - 0.25) < 1e-9

    def test_share_increases_monotonically_with_oil_price(self) -> None:
        """Renewable share increases monotonically as oil price rises (sigma>1)."""
        oil_prices = [30.0, 50.0, 65.0, 80.0, 100.0, 130.0]
        shares = [
            ces_substitution(p, 1.0, sigma=1.8, alpha=0.30).renew_share
            for p in oil_prices
        ]
        for i in range(len(shares) - 1):
            assert shares[i] < shares[i + 1], (
                f"Share did not increase at oil price index {i}: "
                f"{shares[i]:.6f} >= {shares[i + 1]:.6f}"
            )


class TestMukhtarovElasticityIntegration:
    """
    Verify the Mukhtarov (2024) elasticity anchor through the full CESModel.

    Mukhtarov et al. (2024): 1% oil price rise -> ~0.16% renewable
    consumption rise (China). The CES model is a microeconomic
    approximation; the implied elasticity should be positive and
    in the same order of magnitude.
    """

    def test_validate_mukhtarov_implied_elasticity_positive(self) -> None:
        """A 1% oil price shock produces a positive renewable share increase."""
        model = CESModel(sigma=1.8, alpha=0.30)
        report = model.validate_mukhtarov(base_price=65.0, pct_shock=0.01)
        assert report["implied_elasticity"] > 0.0

    def test_validate_mukhtarov_ratio_same_order_of_magnitude(self) -> None:
        """Implied elasticity vs. Mukhtarov target ratio is within 0.1-10x."""
        model = CESModel(sigma=1.8, alpha=0.30)
        report = model.validate_mukhtarov(base_price=65.0, pct_shock=0.01)
        # Within one order of magnitude of empirical estimate
        assert 0.1 < report["ratio"] < 10.0

    def test_validate_mukhtarov_shocked_share_exceeds_base_share(self) -> None:
        """Shocked share must be strictly greater than base share."""
        model = CESModel(sigma=1.8, alpha=0.30)
        report = model.validate_mukhtarov()
        assert report["shocked_share"] > report["base_share"]

    def test_investment_1pct_oil_rise_increases_terminal_share_and_investment(
        self,
    ) -> None:
        """
        A 1% step-up in oil price from period 1 onward increases both the
        terminal renewable share and the terminal renewable investment.

        The model normalises investment to the base-step share, so the shock
        must occur AFTER step 0 to produce a measurable investment increase.
        """
        model = CESModel(sigma=1.8, alpha=0.30)
        # Flat baseline; shocked path applies +1% from step 1 onward
        base_prices = [65.0] * 6
        shocked_prices = [65.0, 65.65, 65.65, 65.65, 65.65, 65.65]
        base_traj = model.investment_trajectory(base_prices, capex_decline_rate=0.0)
        shocked_traj = model.investment_trajectory(
            shocked_prices, capex_decline_rate=0.0
        )
        assert shocked_traj[-1]["renew_share"] > base_traj[-1]["renew_share"]
        assert (
            shocked_traj[-1]["renew_invest_bn_usd"]
            > base_traj[-1]["renew_invest_bn_usd"]
        )


class TestInvestmentResponseModelIntegration:
    """Integration tests for InvestmentResponseModel wiring into CESModel."""

    def test_policy_multiplier_scales_output_exactly(self) -> None:
        """policy_multiplier=1.3 raises policy_adj_invest by exactly 30%."""
        prices = [65.0, 67.0, 70.0, 72.0, 70.0, 68.0]
        irm_base = InvestmentResponseModel(
            ces=CESModel(), policy_multiplier=1.0, capex_decline_rate=0.0
        )
        irm_policy = InvestmentResponseModel(
            ces=CESModel(), policy_multiplier=1.3, capex_decline_rate=0.0
        )
        base_traj = irm_base.run(prices)
        policy_traj = irm_policy.run(prices)
        for b, p in zip(base_traj, policy_traj):
            assert (
                abs(p["policy_adj_invest_bn_usd"] / b["policy_adj_invest_bn_usd"] - 1.3)
                < 1e-9
            )

    def test_capex_decline_rate_02_raises_terminal_investment(self) -> None:
        """Default 20% CAPEX decline raises terminal-year investment vs. no decline."""
        prices = [65.0] * 6
        irm_no_decline = InvestmentResponseModel(ces=CESModel(), capex_decline_rate=0.0)
        irm_decline = InvestmentResponseModel(ces=CESModel(), capex_decline_rate=0.20)
        no_decline_term = irm_no_decline.run(prices)[-1]["policy_adj_invest_bn_usd"]
        decline_term = irm_decline.run(prices)[-1]["policy_adj_invest_bn_usd"]
        assert decline_term > no_decline_term

    def test_base_year_step_investment_equals_base_when_no_capex_decline(self) -> None:
        """At step 0 with no CAPEX decline, investment equals base_invest_bn_usd."""
        base_invest = 807.0
        prices = [65.0, 70.0, 75.0]
        irm = InvestmentResponseModel(
            ces=CESModel(), base_invest_bn_usd=base_invest, capex_decline_rate=0.0
        )
        traj = irm.run(prices)
        # Step 0: share multiplier == 1.0, so invest == base (no policy uplift)
        assert abs(traj[0]["renew_invest_bn_usd"] - base_invest) < 1e-6

    def test_years_labels_propagate_to_output(self) -> None:
        """Year labels supplied to run() appear in each output row."""
        prices = [65.0, 68.0, 70.0]
        years = [2025, 2026, 2027]
        irm = InvestmentResponseModel(ces=CESModel())
        traj = irm.run(prices, years=years)
        assert [int(r["year"]) for r in traj] == years

    def test_compare_scenarios_returns_all_keys(self) -> None:
        """compare_scenarios returns an entry for every supplied scenario."""
        scenario_paths = {
            "high": [100.0, 110.0, 120.0],
            "low": [50.0, 45.0, 40.0],
        }
        irm = InvestmentResponseModel(ces=CESModel())
        results = irm.compare_scenarios(scenario_paths)
        assert set(results.keys()) == {"high", "low"}
        for traj in results.values():
            assert len(traj) == 3

    def test_high_oil_scenario_higher_terminal_invest_than_low_oil(self) -> None:
        """Higher oil price scenario produces higher terminal renewable investment."""
        high_prices = [100.0, 105.0, 110.0, 115.0, 120.0, 130.0]
        low_prices = [50.0, 48.0, 45.0, 42.0, 38.0, 35.0]
        irm = InvestmentResponseModel(ces=CESModel(sigma=1.8))
        results = irm.compare_scenarios({"high": high_prices, "low": low_prices})
        high_term = results["high"][-1]["policy_adj_invest_bn_usd"]
        low_term = results["low"][-1]["policy_adj_invest_bn_usd"]
        assert high_term > low_term

    def test_mismatched_years_length_raises_value_error(self) -> None:
        """years list of wrong length raises ValueError."""
        irm = InvestmentResponseModel(ces=CESModel())
        with pytest.raises(ValueError, match="same length"):
            irm.run([65.0, 68.0, 70.0], years=[2025, 2026])

    def test_invalid_policy_multiplier_below_1_raises(self) -> None:
        """policy_multiplier < 1.0 raises ValueError on instantiation."""
        with pytest.raises(ValueError, match="policy_multiplier"):
            InvestmentResponseModel(ces=CESModel(), policy_multiplier=0.9)

    def test_cobb_douglas_sigma1_constant_share_through_investment_model(self) -> None:
        """With sigma=1, changing oil prices does not change the renewable share."""
        prices = [30.0, 65.0, 100.0, 150.0]
        model = CESModel(sigma=1.0, alpha=0.35)
        traj = model.investment_trajectory(prices, capex_decline_rate=0.0)
        shares = [row["renew_share"] for row in traj]
        for s in shares:
            assert abs(s - 0.35) < 1e-9, f"Expected share 0.35, got {s}"
