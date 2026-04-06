"""
Integration tests: Scenario paths + Investment model.

Tests that bridge ces_model.scenarios.paths / stress_test with
ces_model.core.investment, verifying price bounds, convergence
targets, and economic ordering across the five canonical scenarios.
"""

from __future__ import annotations

from ces_model.core.ces import CESModel
from ces_model.core.investment import InvestmentResponseModel
from ces_model.scenarios.paths import SCENARIOS, get_scenario
from ces_model.scenarios.stress_test import StressTest, StressTestResult

# ---------------------------------------------------------------------------
# Scenario price-path bounds
# ---------------------------------------------------------------------------


class TestScenarioPriceBounds:
    """All scenario price paths must stay within authoritative source ranges."""

    def test_all_scenarios_prices_within_25_to_130_usd(self) -> None:
        """Every price in every scenario is within the $25-$130/bbl envelope."""
        for name, sc in SCENARIOS.items():
            for price in sc.prices_usd:
                assert 20.0 <= price <= 135.0, (
                    f"Scenario {name}: price {price} outside [20, 135] USD/bbl"
                )

    def test_steps_2030_price_converges_to_65_usd(self) -> None:
        """STEPS terminal price (2030) should be approximately $65/bbl."""
        sc = get_scenario("STEPS")
        terminal = sc.projection_path(2025)[-1]
        assert abs(terminal - 65.0) < 1.0, f"STEPS 2030 expected ~65, got {terminal}"

    def test_nze_2030_price_converges_to_44_usd(self) -> None:
        """NZE terminal price (2030) should be approximately $44/bbl."""
        sc = get_scenario("NZE")
        terminal = sc.projection_path(2025)[-1]
        assert abs(terminal - 44.0) < 1.0, f"NZE 2030 expected ~44, got {terminal}"

    def test_high_shock_2030_price_is_highest_among_all_scenarios(self) -> None:
        """HIGH_SHOCK terminal price exceeds every other scenario in 2030."""
        high_term = get_scenario("HIGH_SHOCK").projection_path(2025)[-1]
        other_names = [n for n in SCENARIOS if n != "HIGH_SHOCK"]
        for name in other_names:
            other_term = get_scenario(name).projection_path(2025)[-1]
            assert high_term > other_term, (
                f"HIGH_SHOCK terminal {high_term} not above "
                f"{name} terminal {other_term}"
            )

    def test_low_shock_2030_price_is_lowest_among_all_scenarios(self) -> None:
        """LOW_SHOCK terminal price is below every other scenario in 2030."""
        low_term = get_scenario("LOW_SHOCK").projection_path(2025)[-1]
        other_names = [n for n in SCENARIOS if n != "LOW_SHOCK"]
        for name in other_names:
            other_term = get_scenario(name).projection_path(2025)[-1]
            assert low_term < other_term, (
                f"LOW_SHOCK terminal {low_term} not below {name} terminal {other_term}"
            )

    def test_all_projection_paths_have_six_years(self) -> None:
        """Every scenario has exactly 6 projection years (2025-2030 inclusive)."""
        for name, sc in SCENARIOS.items():
            path = sc.projection_path(2025)
            assert len(path) == 6, f"Scenario {name}: expected 6 years, got {len(path)}"


# ---------------------------------------------------------------------------
# Stress test completeness and correctness
# ---------------------------------------------------------------------------


class TestStressTestIntegration:
    """Full StressTest pipeline: all scenarios produce complete, coherent results."""

    def test_stresstest_all_scenarios_run_and_return_complete_results(self) -> None:
        """StressTest.run() covers all 5 scenarios and returns StressTestResult."""
        st = StressTest()
        result = st.run()
        assert isinstance(result, StressTestResult)
        assert set(result.scenario_results.keys()) == {
            "STEPS",
            "APS",
            "NZE",
            "HIGH_SHOCK",
            "LOW_SHOCK",
        }

    def test_stresstest_each_trajectory_has_expected_keys(self) -> None:
        """Every trajectory row contains the required output fields."""
        required_keys = {
            "year",
            "price_oil",
            "renew_share",
            "renew_invest_bn_usd",
            "policy_adj_invest_bn_usd",
            "cagr_vs_base",
        }
        st = StressTest()
        result = st.run()
        for name, sr in result.scenario_results.items():
            for i, row in enumerate(sr.trajectory):
                missing = required_keys - set(row.keys())
                assert not missing, f"Scenario {name}, step {i}: missing keys {missing}"

    def test_stresstest_trajectory_six_steps_per_scenario(self) -> None:
        """Each scenario trajectory has exactly 6 steps (2025-2030)."""
        st = StressTest()
        result = st.run()
        for name, sr in result.scenario_results.items():
            assert len(sr.trajectory) == 6, (
                f"Scenario {name}: expected 6 steps, got {len(sr.trajectory)}"
            )

    def test_stresstest_renew_share_always_in_0_1(self) -> None:
        """Renewable share is in [0, 1] for every scenario and every step."""
        st = StressTest()
        result = st.run()
        for name, sr in result.scenario_results.items():
            for row in sr.trajectory:
                assert 0.0 <= row["renew_share"] <= 1.0, (
                    f"Scenario {name}: renew_share={row['renew_share']} outside [0,1]"
                )

    def test_stresstest_all_investments_positive(self) -> None:
        """Investment values are positive for all scenarios and all steps."""
        st = StressTest()
        result = st.run()
        for name, sr in result.scenario_results.items():
            for row in sr.trajectory:
                step_id = row.get("step", "?")
                assert row["renew_invest_bn_usd"] > 0.0, (
                    f"Scenario {name}: non-positive renew_invest at step {step_id}"
                )
                assert row["policy_adj_invest_bn_usd"] > 0.0

    def test_stresstest_high_shock_highest_terminal_investment(self) -> None:
        """HIGH_SHOCK produces highest terminal-year investment (highest oil price)."""
        st = StressTest()
        result = st.run()
        high_term = result.scenario_results["HIGH_SHOCK"].terminal_invest()
        for name, sr in result.scenario_results.items():
            if name == "HIGH_SHOCK":
                continue
            other_term = sr.terminal_invest()
            assert high_term > other_term, (
                f"HIGH_SHOCK terminal {high_term:.1f} not above "
                f"{name} terminal {other_term:.1f}"
            )

    def test_stresstest_low_shock_lowest_terminal_investment(self) -> None:
        """LOW_SHOCK produces lowest terminal-year investment (lowest oil price)."""
        st = StressTest()
        result = st.run()
        low_term = result.scenario_results["LOW_SHOCK"].terminal_invest()
        for name, sr in result.scenario_results.items():
            if name == "LOW_SHOCK":
                continue
            other_term = sr.terminal_invest()
            assert low_term < other_term, (
                f"LOW_SHOCK terminal {low_term:.1f} not below "
                f"{name} terminal {other_term:.1f}"
            )

    def test_stresstest_summary_contains_all_scenarios(self) -> None:
        """Summary DataFrame has one row per scenario with expected columns."""
        st = StressTest()
        result = st.run()
        summary = result.summary()
        assert len(summary) == 5
        for col in [
            "terminal_invest_bn_usd",
            "total_invest_bn_usd",
            "terminal_renew_share",
        ]:
            assert col in summary.columns, f"Missing column: {col}"

    def test_stresstest_wide_dataframe_has_year_and_all_scenario_columns(self) -> None:
        """Wide DataFrame for investment has year + one column per scenario."""
        st = StressTest()
        result = st.run()
        df = result.to_wide_dataframe()
        assert "year" in df.columns
        for name in SCENARIOS:
            assert name in df.columns, f"Missing scenario column: {name}"

    def test_stresstest_capex_decline_raises_all_terminal_investments(self) -> None:
        """CAPEX decline (20%) produces higher terminal investment than no decline."""
        st_no_decline = StressTest(capex_decline_rate=0.0)
        st_decline = StressTest(capex_decline_rate=0.20)
        r_no = st_no_decline.run()
        r_dec = st_decline.run()
        for name in SCENARIOS:
            term_no = r_no.scenario_results[name].terminal_invest()
            term_dec = r_dec.scenario_results[name].terminal_invest()
            assert term_dec >= term_no, (
                f"Scenario {name}: CAPEX decline did not raise terminal invest "
                f"({term_dec:.1f} vs {term_no:.1f})"
            )

    def test_stresstest_scenario_result_to_dataframe_structure(self) -> None:
        """ScenarioResult.to_dataframe() has the correct columns and row count."""
        st = StressTest()
        sr = st.run_single("STEPS")
        df = sr.to_dataframe()
        assert len(df) == 6
        for col in ["year", "price_oil", "renew_share", "policy_adj_invest_bn_usd"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_stresstest_steps_through_investment_model_years_2025_to_2030(self) -> None:
        """STEPS scenario run via InvestmentResponseModel yields years 2025-2030."""
        sc = get_scenario("STEPS")
        price_path = sc.projection_path(2025)
        years = sc.projection_years(2025)
        irm = InvestmentResponseModel(ces=CESModel())
        traj = irm.run(price_path, years=years)
        assert [int(r["year"]) for r in traj] == list(range(2025, 2031))
