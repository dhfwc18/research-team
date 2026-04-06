"""
Morris method sampler for CES model sensitivity analysis.

Adapted from Usher et al. (2023) esom_gsa create_sample.py (MIT licence).
Uses SALib >= 1.4 with seed=42 for reproducibility.

Expected run count: (num_groups + 1) * num_trajectories
With 5 groups, 10 trajectories: 60 model runs (each microseconds).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from SALib.sample import morris as morris_sampler

_DEFAULT_NUM_LEVELS = 4
_DEFAULT_NUM_TRAJECTORIES = 10
_DEFAULT_SEED = 42


def sample_morris(
    problem: dict[str, Any],
    num_trajectories: int = _DEFAULT_NUM_TRAJECTORIES,
    num_levels: int = _DEFAULT_NUM_LEVELS,
    seed: int = _DEFAULT_SEED,
) -> np.ndarray:
    """
    Generate a Morris method sample matrix.

    Args:
        problem:          SALib problem dict (from build_problem()).
        num_trajectories: Number of Morris trajectories (replicates). Default 10.
        num_levels:       Number of grid levels for Morris sampling. Default 4.
        seed:             Random seed for reproducibility. Default 42.

    Returns:
        numpy array of shape (num_trajectories * (num_groups + 1), num_vars).
        Each row is a parameter combination to evaluate.

    Raises:
        ValueError: If num_trajectories < 1 or num_levels < 2.
    """
    if num_trajectories < 1:
        raise ValueError(f"num_trajectories must be >= 1, got {num_trajectories}")
    if num_levels < 2:
        raise ValueError(f"num_levels must be >= 2, got {num_levels}")

    sample = morris_sampler.sample(
        problem,
        N=num_trajectories,
        num_levels=num_levels,
        seed=seed,
    )
    return sample


def sample_to_param_dicts(
    sample: np.ndarray,
    problem: dict[str, Any],
) -> list[dict[str, float]]:
    """
    Convert a Morris sample matrix to a list of parameter dicts.

    Args:
        sample:  Sample matrix from sample_morris().
        problem: SALib problem dict (provides parameter names).

    Returns:
        List of dicts, one per sample row, mapping param name -> value.
    """
    names = problem["names"]
    return [{name: float(val) for name, val in zip(names, row)} for row in sample]
