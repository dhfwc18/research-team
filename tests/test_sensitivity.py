"""Tests for the Morris sensitivity analysis module."""

from __future__ import annotations

import numpy as np
import pytest

from ces_model.sensitivity.problem import build_problem, get_baselines
from ces_model.sensitivity.runner import run_sensitivity
from ces_model.sensitivity.sampler import sample_morris, sample_to_param_dicts


class TestBuildProblem:
    def test_default_problem(self) -> None:
        prob = build_problem()
        assert prob["num_vars"] >= 2
        assert len(prob["names"]) == prob["num_vars"]
        assert len(prob["bounds"]) == prob["num_vars"]
        assert len(prob["groups"]) == prob["num_vars"]

    def test_bounds_are_valid(self) -> None:
        prob = build_problem()
        for lo, hi in prob["bounds"]:
            assert lo < hi

    def test_at_least_two_groups(self) -> None:
        prob = build_problem()
        assert len(set(prob["groups"])) >= 2

    def test_too_few_params_raises(self) -> None:
        params = [{"name": "x", "group": "a", "min_value": 0.0, "max_value": 1.0}]
        with pytest.raises(ValueError, match="at least 2 parameters"):
            build_problem(params)

    def test_single_group_raises(self) -> None:
        params = [
            {"name": "x", "group": "a", "min_value": 0.0, "max_value": 1.0},
            {"name": "y", "group": "a", "min_value": 0.0, "max_value": 1.0},
        ]
        with pytest.raises(ValueError, match="at least 2 groups"):
            build_problem(params)

    def test_get_baselines(self) -> None:
        baselines = get_baselines()
        assert "sigma" in baselines
        assert abs(baselines["sigma"] - 1.8) < 1e-9
        assert abs(baselines["oil_price_elasticity"] - 0.16) < 1e-9


class TestSampler:
    def test_sample_shape(self) -> None:
        prob = build_problem()
        n_groups = len(set(prob["groups"]))
        n_traj = 5
        sample = sample_morris(prob, num_trajectories=n_traj)
        # Morris: (num_groups + 1) * N rows
        expected_rows = (n_groups + 1) * n_traj
        assert sample.shape == (expected_rows, prob["num_vars"])

    def test_sample_within_bounds(self) -> None:
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=5)
        for col_idx, (lo, hi) in enumerate(prob["bounds"]):
            col = sample[:, col_idx]
            assert col.min() >= lo - 1e-9
            assert col.max() <= hi + 1e-9

    def test_reproducibility(self) -> None:
        prob = build_problem()
        s1 = sample_morris(prob, num_trajectories=5, seed=42)
        s2 = sample_morris(prob, num_trajectories=5, seed=42)
        np.testing.assert_array_equal(s1, s2)

    def test_different_seeds_differ(self) -> None:
        prob = build_problem()
        s1 = sample_morris(prob, num_trajectories=5, seed=42)
        s2 = sample_morris(prob, num_trajectories=5, seed=99)
        assert not np.array_equal(s1, s2)

    def test_sample_to_param_dicts(self) -> None:
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=3)
        dicts = sample_to_param_dicts(sample, prob)
        assert len(dicts) == len(sample)
        assert set(dicts[0].keys()) == set(prob["names"])

    def test_invalid_num_trajectories(self) -> None:
        prob = build_problem()
        with pytest.raises(ValueError, match="num_trajectories"):
            sample_morris(prob, num_trajectories=0)

    def test_invalid_num_levels(self) -> None:
        prob = build_problem()
        with pytest.raises(ValueError, match="num_levels"):
            sample_morris(prob, num_levels=1)


class TestRunner:
    def test_run_sensitivity_output_shape(self) -> None:
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=3, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        assert y.shape == (len(sample),)

    def test_output_is_positive(self) -> None:
        """Investment output should always be positive."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=3, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        assert np.all(y > 0.0)

    def test_output_range_plausible(self) -> None:
        """Investment should be in hundreds of USD bn range."""
        prob = build_problem()
        sample = sample_morris(prob, num_trajectories=3, seed=42)
        y = run_sensitivity(sample, prob, n_workers=1)
        assert y.min() > 50.0
        assert y.max() < 5000.0
