"""Tests for scenario price paths and stress testing."""

from __future__ import annotations

import pytest

from ces_model.scenarios.paths import (
    SCENARIOS,
    get_scenario,
    interpolate_annual_path,
    list_scenarios,
    scenarios_to_dataframe,
)
from ces_model.scenarios.stress_test import StressTest


class TestScenarioPaths:
    def test_all_five_scenarios_present(self) -> None:
        names = list_scenarios()
        expected = {"STEPS", "APS", "NZE", "HIGH_SHOCK", "LOW_SHOCK"}
        assert set(names) == expected

    def test_get_scenario_by_name(self) -> None:
        sc = get_scenario("STEPS")
        assert sc.name == "STEPS"

    def test_get_scenario_case_insensitive(self) -> None:
        sc = get_scenario("steps")
        assert sc.name == "STEPS"

    def test_get_scenario_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown scenario"):
            get_scenario("UNKNOWN")

    def test_steps_terminal_price(self) -> None:
        sc = get_scenario("STEPS")
        path = sc.projection_path(2025)
        assert path[-1] == pytest.approx(65.0)

    def test_nze_lower_than_steps_2030(self) -> None:
        steps = get_scenario("STEPS").projection_path(2025)[-1]
        nze = get_scenario("NZE").projection_path(2025)[-1]
        assert nze < steps

    def test_high_shock_above_steps_2030(self) -> None:
        steps = get_scenario("STEPS").projection_path(2025)[-1]
        high = get_scenario("HIGH_SHOCK").projection_path(2025)[-1]
        assert high > steps

    def test_low_shock_minimum_is_25(self) -> None:
        low = get_scenario("LOW_SHOCK")
        assert min(low.prices_usd) == pytest.approx(25.0)

    def test_scenario_to_dataframe(self) -> None:
        sc = get_scenario("APS")
        df = sc.to_dataframe()
        assert "year" in df.columns
        assert "price_usd_bbl" in df.columns
        assert len(df) == len(sc.years)

    def test_scenarios_to_wide_dataframe(self) -> None:
        df = scenarios_to_dataframe()
        assert "year" in df.columns
        for name in SCENARIOS:
            assert name in df.columns

    def test_vol_regime_valid(self) -> None:
        for sc in SCENARIOS.values():
            assert sc.vol_regime in {"low", "medium", "high"}

    def test_projection_years(self) -> None:
        sc = get_scenario("STEPS")
        years = sc.projection_years(2025)
        assert years[0] == 2025
        assert years[-1] == 2030

    def test_interpolate_annual_path(self) -> None:
        years, prices = interpolate_annual_path(2025, 2030, 75.0, 65.0)
        assert years[0] == 2025
        assert years[-1] == 2030
        assert prices[0] == pytest.approx(75.0)
        assert prices[-1] == pytest.approx(65.0)
        # Monotonically decreasing
        for i in range(len(prices) - 1):
            assert prices[i] >= prices[i + 1]


class TestStressTest:
    def test_run_all_scenarios(self) -> None:
        st = StressTest()
        result = st.run()
        assert set(result.scenario_results.keys()) == {
            "STEPS",
            "APS",
            "NZE",
            "HIGH_SHOCK",
            "LOW_SHOCK",
        }

    def test_run_single_scenario(self) -> None:
        st = StressTest()
        sr = st.run_single("STEPS")
        assert sr.name == "STEPS"
        assert len(sr.trajectory) == 6  # 2025-2030

    def test_high_shock_terminal_invest_exceeds_nze(self) -> None:
        """Higher oil prices -> more renewable investment (sigma>1 substitution)."""
        st = StressTest()
        result = st.run()
        high = result.scenario_results["HIGH_SHOCK"].terminal_invest()
        nze = result.scenario_results["NZE"].terminal_invest()
        assert high > nze

    def test_summary_dataframe_shape(self) -> None:
        st = StressTest()
        result = st.run()
        summary = result.summary()
        assert len(summary) == 5
        assert "terminal_invest_bn_usd" in summary.columns

    def test_wide_dataframe(self) -> None:
        st = StressTest()
        result = st.run()
        df = result.to_wide_dataframe()
        assert "year" in df.columns
        assert "STEPS" in df.columns

    def test_policy_multiplier_applied(self) -> None:
        st_no_policy = StressTest(policy_multiplier=1.0)
        st_policy = StressTest(policy_multiplier=1.5)
        r_base = st_no_policy.run_single("STEPS").terminal_invest()
        r_policy = st_policy.run_single("STEPS").terminal_invest()
        assert abs(r_policy / r_base - 1.5) < 0.01

    def test_invalid_policy_multiplier(self) -> None:
        with pytest.raises(ValueError, match="policy_multiplier"):
            StressTest(policy_multiplier=0.5)
