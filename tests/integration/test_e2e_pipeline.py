"""
Integration tests: End-to-end pipeline.

Tests the complete workflow from price inputs through CES model to
investment trajectory output, verifying reproducibility, consistency,
and correctness of the full analysis pipeline.
"""

from __future__ import annotations

import numpy as np

from ces_model.core.ces import CESModel
from ces_model.core.investment import InvestmentResponseModel
from ces_model.scenarios.paths import get_scenario, interpolate_annual_path
from ces_model.scenarios.stress_test import StressTest
from ces_model.sensitivity.analyser import analyse_morris
from ces_model.sensitivity.problem import build_problem
from ces_model.sensitivity.runner import run_sensitivity
from ces_model.sensitivity.sampler import sample_morris


class TestEndToEndReproducibility:
    """Full pipeline produces identical results on repeated calls with seed=42."""

    def test_e2e_steps_investment_trajectory_reproducible(self) -> None:
        """STEPS scenario trajectory is identical on two sequential runs."""
        sc = get_scenario("STEPS")
        prices = sc.projection_path(2025)
        years = sc.projection_years(2025)

        irm = InvestmentResponseModel(ces=CESModel())
        traj1 = irm.run(prices, years=years)
        traj2 = irm.run(prices, years=years)

        for r1, r2 in zip(traj1, traj2):
            assert r1 == r2

    def test_e2e_stress_test_reproducible_across_runs(self) -> None:
        """StressTest produces the same terminal investments on two runs."""
        st = StressTest()
        res1 = st.run()
        res2 = st.run()
        for name in res1.scenario_results:
            t1 = res1.scenario_results[name].terminal_invest()
            t2 = res2.scenario_results[name].terminal_invest()
            assert abs(t1 - t2) < 1e-9, f"Scenario {name}: inconsistent terminal invest"

    def test_e2e_sensitivity_pipeline_reproducible_seed_42(self) -> None:
        """Full sensitivity pipeline produces identical Y with seed=42."""
        prob = build_problem()
        s1 = sample_morris(prob, num_trajectories=5, seed=42)
        s2 = sample_morris(prob, num_trajectories=5, seed=42)
        y1 = run_sensitivity(s1, prob, n_workers=1)
        y2 = run_sensitivity(s2, prob, n_workers=1)
        np.testing.assert_array_equal(y1, y2)


class TestEndToEndEconomicConsistency:
    """Full pipeline produces economically consistent results."""

    def test_e2e_higher_sigma_amplifies_investment_response_to_oil_shock(self) -> None:
        """
        Higher sigma (more substitutable) produces a larger investment increase
        when oil prices rise, relative to lower sigma.

        Prices must be near the renewable price index (1.0) so that neither
        model is already at a corner solution.  At very high oil prices, a
        high-sigma model saturates near share=1.0 at the base step, leaving
        almost no room to grow and inverting the comparison.
        """
        # Rising prices near the normalised renewable price (1.0)
        rising_prices = [1.0, 1.2, 1.5, 1.8, 2.0, 2.5]
        low_sigma_irm = InvestmentResponseModel(
            ces=CESModel(sigma=1.2), capex_decline_rate=0.0
        )
        high_sigma_irm = InvestmentResponseModel(
            ces=CESModel(sigma=2.5), capex_decline_rate=0.0
        )

        low_traj = low_sigma_irm.run(rising_prices)
        high_traj = high_sigma_irm.run(rising_prices)

        low_term = low_traj[-1]["policy_adj_invest_bn_usd"]
        high_term = high_traj[-1]["policy_adj_invest_bn_usd"]
        assert high_term > low_term, (
            f"Higher sigma should produce larger investment: "
            f"sigma=2.5 gives {high_term:.1f}, sigma=1.2 gives {low_term:.1f}"
        )

    def test_e2e_calibrated_alpha_matches_observed_share_through_full_pipeline(
        self,
    ) -> None:
        """
        After calibrate_alpha(), running the full InvestmentResponseModel at
        the calibration price produces a base-step share matching the target.
        """
        target_share = 0.45
        cal_price = 65.0
        model = CESModel(sigma=1.8)
        model.calibrate_alpha(observed_share=target_share, price_oil=cal_price)

        irm = InvestmentResponseModel(ces=model, capex_decline_rate=0.0)
        traj = irm.run([cal_price, cal_price, cal_price])
        # Step 0 share should equal the calibrated target
        assert abs(traj[0]["renew_share"] - target_share) < 1e-5

    def test_e2e_interpolated_price_path_through_investment_model(self) -> None:
        """Linear interpolation -> InvestmentResponseModel produces monotonic shares."""
        years, prices = interpolate_annual_path(2025, 2030, 75.0, 100.0)
        irm = InvestmentResponseModel(ces=CESModel(), capex_decline_rate=0.0)
        traj = irm.run(list(prices), years=list(years))

        shares = [row["renew_share"] for row in traj]
        # Monotonically rising oil price should produce monotonically rising shares
        for i in range(len(shares) - 1):
            assert shares[i] <= shares[i + 1], (
                f"Share not monotone at step {i}: {shares[i]:.6f} > {shares[i + 1]:.6f}"
            )

    def test_e2e_stress_test_and_investment_model_steps_agree(self) -> None:
        """
        Running STEPS through StressTest and directly through
        InvestmentResponseModel produce the same terminal investment.
        """
        # StressTest with matching parameters
        st = StressTest(policy_multiplier=1.0, capex_decline_rate=0.20)
        sr = st.run_single("STEPS")
        stress_term = sr.terminal_invest()

        # Direct InvestmentResponseModel run
        sc = get_scenario("STEPS")
        prices = sc.projection_path(2025)
        years = sc.projection_years(2025)
        irm = InvestmentResponseModel(
            ces=CESModel(), policy_multiplier=1.0, capex_decline_rate=0.20
        )
        direct_traj = irm.run(prices, years=years)
        direct_term = direct_traj[-1]["policy_adj_invest_bn_usd"]

        assert abs(stress_term - direct_term) < 1e-6, (
            f"StressTest ({stress_term:.4f}) and direct IRM "
            f"({direct_term:.4f}) disagree"
        )

    def test_e2e_full_pipeline_price_to_sensitivity_analysis(self) -> None:
        """
        Complete pipeline: define problem -> sample -> run model -> analyse.
        Verifies mu_star array length matches number of result names and
        top parameter is identifiable.
        """
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        result = analyse_morris(prob, sample, y)

        assert len(result.mu_star) == len(result.names)
        assert len(result.sigma) == len(result.names)
        top = result.top_parameters(n=1)
        assert len(top) == 1
        assert isinstance(top[0], str)

    def test_e2e_nze_lower_terminal_share_than_high_shock(self) -> None:
        """
        NZE (low oil price 2030) yields lower terminal renewable share than
        HIGH_SHOCK (high oil price 2030), consistent with sigma>1 substitution.
        """
        st = StressTest()
        result = st.run()
        nze_share = result.scenario_results["NZE"].terminal_share()
        high_share = result.scenario_results["HIGH_SHOCK"].terminal_share()
        assert high_share > nze_share, (
            f"HIGH_SHOCK share {high_share:.4f} should exceed NZE share {nze_share:.4f}"
        )

    def test_e2e_invest_baseline_parameter_scales_output_linearly(self) -> None:
        """
        Doubling invest_baseline_bn_usd doubles the terminal investment output.

        This verifies the full pipeline (problem -> sample -> model) correctly
        propagates the baseline investment parameter end-to-end.
        """
        from ces_model.sensitivity.runner import _evaluate_single

        params_base = {
            "sigma": 1.8,
            "alpha": 0.30,
            "oil_price_2025": 75.0,
            "oil_price_2030": 65.0,
            "renew_capex_decline": 0.20,
            "invest_baseline_bn_usd": 807.0,
        }
        params_double = {**params_base, "invest_baseline_bn_usd": 1614.0}

        y_base = _evaluate_single(params_base)
        y_double = _evaluate_single(params_double)

        ratio = y_double / y_base
        assert abs(ratio - 2.0) < 1e-6, (
            f"Doubling baseline should double output: "
            f"{y_double:.2f} / {y_base:.2f} = {ratio:.4f}"
        )
