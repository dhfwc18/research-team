"""
CES model runner for Morris sensitivity analysis.

Evaluates the CES investment model for each row of the Morris sample matrix.
Uses multiprocessing.Pool for parallelism (replaces Snakemake from esom_gsa).

The model output (Y) is the terminal-year renewable investment (USD bn) under
a linear interpolation of the oil price path from oil_price_2025 to oil_price_2030.
"""

from __future__ import annotations

import multiprocessing
from typing import Any

import numpy as np

from ces_model.core.ces import CESModel
from ces_model.core.investment import InvestmentResponseModel
from ces_model.scenarios.paths import interpolate_annual_path

_PROJECTION_YEARS = list(range(2025, 2031))  # 2025-2030 inclusive


def _evaluate_single(params: dict[str, float]) -> float:
    """
    Evaluate the CES investment model for a single parameter combination.

    Args:
        params: Dict with keys from the sensitivity problem:
                sigma, alpha, oil_price_2025, oil_price_2030,
                discount_rate, renew_capex_decline, invest_baseline_bn_usd.
                (oil_price_elasticity is passed through but does not directly
                enter the CES formula; it is used for cross-validation only.)

    Returns:
        Terminal-year (2030) renewable investment in USD bn.
    """
    sigma = float(params.get("sigma", 1.8))
    alpha = float(params.get("alpha", 0.30))
    p2025 = float(params.get("oil_price_2025", 75.0))
    p2030 = float(params.get("oil_price_2030", 65.0))
    capex_decline = float(params.get("renew_capex_decline", 0.20))
    base_invest = float(params.get("invest_baseline_bn_usd", 807.0))

    # Build a linear oil price path from 2025 to 2030
    _, prices = interpolate_annual_path(
        start_year=2025,
        end_year=2030,
        start_price=p2025,
        end_price=p2030,
    )

    ces = CESModel(sigma=sigma, alpha=alpha)
    irm = InvestmentResponseModel(
        ces=ces,
        base_invest_bn_usd=base_invest,
        capex_decline_rate=capex_decline,
    )
    trajectory = irm.run(list(prices), years=_PROJECTION_YEARS)

    # Output: terminal (2030) policy-adjusted investment
    return trajectory[-1]["policy_adj_invest_bn_usd"]


def run_sensitivity(
    sample: np.ndarray,
    problem: dict[str, Any],
    n_workers: int | None = None,
) -> np.ndarray:
    """
    Run the CES model for each row of the Morris sample matrix.

    Args:
        sample:    Morris sample matrix (rows = parameter sets).
        problem:   SALib problem dict (provides parameter names).
        n_workers: Number of worker processes. Default: min(cpu_count, rows).

    Returns:
        1-D numpy array Y of model outputs, one per sample row.
    """
    names = problem["names"]
    param_dicts = [
        {name: float(val) for name, val in zip(names, row)} for row in sample
    ]

    n_rows = len(param_dicts)
    workers = n_workers or min(multiprocessing.cpu_count(), n_rows)

    if workers <= 1 or n_rows < 4:
        # Serial execution for small samples or single-core environments
        y = np.array([_evaluate_single(p) for p in param_dicts])
    else:
        with multiprocessing.Pool(processes=workers) as pool:
            y = np.array(pool.map(_evaluate_single, param_dicts))

    return y
