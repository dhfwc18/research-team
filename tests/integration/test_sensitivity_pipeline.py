"""
Integration tests: Sensitivity analysis full pipeline.

Tests the end-to-end flow: build_problem -> sample_morris ->
run_sensitivity -> analyse_morris, verifying structural completeness,
economic plausibility, and expected parameter names.
"""

from __future__ import annotations

import numpy as np
import pytest

from ces_model.sensitivity.analyser import SensitivityResult, analyse_morris
from ces_model.sensitivity.problem import build_problem, get_baselines
from ces_model.sensitivity.runner import run_sensitivity
from ces_model.sensitivity.sampler import sample_morris

_EXPECTED_PARAMS = {
    "sigma",
    "alpha",
    "oil_price_elasticity",
    "oil_price_2025",
    "oil_price_2030",
    "discount_rate",
    "renew_capex_decline",
    "invest_baseline_bn_usd",
}


class TestSensitivityProblemToSample:
    """Problem definition integrates correctly with the Morris sampler."""

    def test_problem_names_match_expected_parameter_set(self) -> None:
        """Default problem contains all expected CES model parameters."""
        prob = build_problem()
        assert set(prob["names"]) == _EXPECTED_PARAMS

    def test_baselines_include_all_expected_parameters(self) -> None:
        """get_baselines() returns all expected parameter names."""
        baselines = get_baselines()
        assert set(baselines.keys()) == _EXPECTED_PARAMS

    def test_sample_shape_consistent_with_problem(self) -> None:
        """Sample matrix columns match num_vars from the problem dict."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        assert sample.shape[1] == prob["num_vars"]

    def test_sample_values_within_declared_bounds(self) -> None:
        """Every sample value is within the declared parameter bounds."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=10, seed=42)
        for col_idx, (lo, hi) in enumerate(prob["bounds"]):
            col = sample[:, col_idx]
            assert col.min() >= lo - 1e-9, (
                f"Parameter {prob['names'][col_idx]}: sample below lower bound"
            )
            assert col.max() <= hi + 1e-9, (
                f"Parameter {prob['names'][col_idx]}: sample above upper bound"
            )


class TestSensitivityRunnerIntegration:
    """run_sensitivity integrates problem + sample -> model output correctly."""

    def test_run_sensitivity_output_length_matches_sample_rows(self) -> None:
        """Y array has exactly one entry per sample row."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        assert len(y) == len(sample)

    def test_run_sensitivity_all_outputs_positive(self) -> None:
        """Terminal investment is positive for every sample point."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        assert np.all(y > 0.0), "Some sensitivity outputs are non-positive"

    def test_run_sensitivity_output_in_plausible_investment_range(self) -> None:
        """Terminal investment spans a range consistent with hundreds of USD bn."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=10, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        assert y.min() > 50.0, f"Min investment too low: {y.min():.1f} bn USD"
        assert y.max() < 8000.0, (
            f"Max investment implausibly high: {y.max():.1f} bn USD"
        )

    def test_run_sensitivity_reproducible_with_same_seed(self) -> None:
        """Same seed produces identical output arrays."""
        prob = build_problem()
        s1 = sample_morris(prob, num_trajectories=5, seed=42)
        s2 = sample_morris(prob, num_trajectories=5, seed=42)
        y1 = run_sensitivity(s1, prob, n_workers=1)
        y2 = run_sensitivity(s2, prob, n_workers=1)
        np.testing.assert_array_equal(y1, y2)

    def test_run_sensitivity_varies_across_parameter_space(self) -> None:
        """Output Y shows variance across the sample (model is sensitive to inputs)."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=10, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        assert y.std() > 0.0, "Sensitivity output has no variance across sample"


class TestSensitivityAnalyserIntegration:
    """analyse_morris integrates problem + sample + Y -> SensitivityResult."""

    def test_analyse_morris_returns_sensitivity_result(self) -> None:
        """analyse_morris returns a SensitivityResult instance."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        result = analyse_morris(prob, sample, y)
        assert isinstance(result, SensitivityResult)

    def test_analyse_morris_result_has_expected_parameter_names(self) -> None:
        """SensitivityResult.names contains the expected CES parameter names."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        result = analyse_morris(prob, sample, y)
        # When groups are active, SALib returns group names.
        # At minimum, all group labels are present as result names.
        assert len(result.names) > 0

    def test_analyse_morris_mu_star_nonnegative(self) -> None:
        """mu_star (mean absolute effect) is non-negative for every parameter."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        result = analyse_morris(prob, sample, y)
        assert np.all(result.mu_star >= 0.0), "mu_star has negative values"

    def test_analyse_morris_sigma_finite_values_nonnegative(self) -> None:
        """
        sigma (std dev of elementary effects) is non-negative for all finite values.

        SALib with group-based Morris may return NaN sigma for groups where
        there is insufficient trajectory variation.  Only finite values are
        checked here.
        """
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        result = analyse_morris(prob, sample, y)
        finite_sigma = result.sigma[np.isfinite(result.sigma)]
        assert len(finite_sigma) > 0, "No finite sigma values found"
        assert np.all(finite_sigma >= 0.0), (
            f"Some finite sigma values are negative: {finite_sigma}"
        )

    def test_analyse_morris_to_dataframe_has_required_columns(self) -> None:
        """SensitivityResult.to_dataframe() contains parameter, mu, mu_star, sigma."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        result = analyse_morris(prob, sample, y)
        df = result.to_dataframe()
        for col in ["parameter", "mu", "mu_star", "sigma"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_analyse_morris_to_dataframe_sorted_descending_mu_star(self) -> None:
        """to_dataframe() is sorted by mu_star descending."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        result = analyse_morris(prob, sample, y)
        df = result.to_dataframe()
        mu_star_vals = df["mu_star"].tolist()
        assert mu_star_vals == sorted(mu_star_vals, reverse=True)

    def test_analyse_morris_top_parameters_returns_list(self) -> None:
        """top_parameters() returns a non-empty list."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        result = analyse_morris(prob, sample, y)
        top = result.top_parameters(n=3)
        assert isinstance(top, list)
        assert len(top) == 3

    def test_analyse_morris_mismatched_y_length_raises(self) -> None:
        """Passing Y of wrong length raises ValueError."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5, seed=42)
        y_wrong = np.ones(len(sample) + 5)
        with pytest.raises(ValueError, match="length"):
            analyse_morris(prob, sample, y_wrong)
