"""
SALib problem definition for Morris sensitivity analysis.

Adapted from Usher et al. (2023) esom_gsa (MIT licence).
Snakemake dependency removed; multiprocessing.Pool used for parallelism.

Parameter set covers the key CES model inputs with ranges from:
  - Papageorgiou et al. (2017): sigma in [1.0, 3.0]
  - Mukhtarov et al. (2024): oil_price_elasticity in [0.05, 0.35]
  - IEA WEO 2024 / Boer et al. (2023): price paths
  - WACC estimates: discount_rate in [0.05, 0.15]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Default parameter specification (mirrors parameters.yaml)
_DEFAULT_PARAMETERS: list[dict[str, Any]] = [
    {
        "name": "sigma",
        "group": "substitution",
        "min_value": 1.0,
        "max_value": 3.0,
        "baseline": 1.8,
    },
    {
        "name": "alpha",
        "group": "substitution",
        "min_value": 0.15,
        "max_value": 0.60,
        "baseline": 0.30,
    },
    {
        "name": "oil_price_elasticity",
        "group": "elasticity",
        "min_value": 0.05,
        "max_value": 0.35,
        "baseline": 0.16,
    },
    {
        "name": "oil_price_2025",
        "group": "oil_price",
        "min_value": 30.0,
        "max_value": 110.0,
        "baseline": 75.0,
    },
    {
        "name": "oil_price_2030",
        "group": "oil_price",
        "min_value": 25.0,
        "max_value": 130.0,
        "baseline": 65.0,
    },
    {
        "name": "discount_rate",
        "group": "finance",
        "min_value": 0.05,
        "max_value": 0.15,
        "baseline": 0.08,
    },
    {
        "name": "renew_capex_decline",
        "group": "technology",
        "min_value": 0.0,
        "max_value": 0.50,
        "baseline": 0.20,
    },
    {
        "name": "invest_baseline_bn_usd",
        "group": "investment",
        "min_value": 600.0,
        "max_value": 1200.0,
        "baseline": 807.0,
    },
]


def build_problem(
    parameters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build a SALib problem dict from the parameter specification.

    Args:
        parameters: List of parameter dicts with keys: name, group,
                    min_value, max_value. If None, uses default CES parameters.

    Returns:
        SALib-compatible problem dict with keys:
          num_vars, names, bounds, groups.

    Raises:
        ValueError: If fewer than 2 parameters or 2 groups are provided
                    (SALib Morris requires at least 2 of each).
    """
    params = parameters or _DEFAULT_PARAMETERS

    names = [p["name"] for p in params]
    bounds = [[p["min_value"], p["max_value"]] for p in params]
    groups = [p.get("group", p["name"]) for p in params]

    num_vars = len(names)
    num_groups = len(set(groups))

    if num_vars < 2:
        raise ValueError(f"Morris requires at least 2 parameters; got {num_vars}")
    if num_groups < 2:
        raise ValueError(f"Morris requires at least 2 groups; got {num_groups}")

    return {
        "num_vars": num_vars,
        "names": names,
        "bounds": bounds,
        "groups": groups,
    }


def load_problem_from_yaml(
    yaml_path: str | Path,
) -> dict[str, Any]:
    """
    Load parameter specification from a YAML file and build a SALib problem.

    Expected YAML structure (see parameters.yaml):
        parameters:
          - name: sigma
            group: substitution
            min_value: 1.0
            max_value: 3.0

    Args:
        yaml_path: Path to the YAML file.

    Returns:
        SALib problem dict.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        KeyError: If required fields are missing.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Parameter YAML not found: {path}")

    with path.open("r") as fh:
        config = yaml.safe_load(fh)

    params = config.get("parameters", [])
    if not params:
        raise KeyError(f"No 'parameters' key found in {path}")

    return build_problem(params)


def get_baselines(
    parameters: list[dict[str, Any]] | None = None,
) -> dict[str, float]:
    """
    Return the baseline (central) values for all parameters.

    Args:
        parameters: Parameter list. If None, uses default.

    Returns:
        Dict mapping parameter name -> baseline value.
    """
    params = parameters or _DEFAULT_PARAMETERS
    return {
        p["name"]: float(p.get("baseline", (p["min_value"] + p["max_value"]) / 2))
        for p in params
    }
