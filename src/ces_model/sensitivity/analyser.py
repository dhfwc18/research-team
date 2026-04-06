"""
Morris sensitivity analysis results analyser.

Adapted from Usher et al. (2023) esom_gsa (MIT licence).
Computes SALib Morris indices (mu, mu_star, sigma) and produces
CSV and PNG outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from SALib.analyze import morris as morris_analyser


@dataclass
class SensitivityResult:
    """
    Morris sensitivity analysis results.

    Attributes:
        problem:   SALib problem dict.
        mu:        Mean elementary effects (signed).
        mu_star:   Mean of absolute elementary effects (key ranking metric).
        sigma:     Standard deviation of elementary effects (interaction proxy).
        names:     Parameter names.
    """

    problem: dict[str, Any]
    mu: np.ndarray
    mu_star: np.ndarray
    sigma: np.ndarray
    names: list[str] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        """Return results as a ranked DataFrame (descending mu_star)."""
        df = pd.DataFrame(
            {
                "parameter": self.names,
                "mu": self.mu,
                "mu_star": self.mu_star,
                "sigma": self.sigma,
                "mu_star_conf": getattr(
                    self, "mu_star_conf", np.zeros(len(self.names))
                ),
            }
        )
        return df.sort_values("mu_star", ascending=False).reset_index(drop=True)

    def top_parameters(self, n: int = 5) -> list[str]:
        """Return the top-n most influential parameters by mu_star."""
        df = self.to_dataframe()
        return df.head(n)["parameter"].tolist()


def analyse_morris(
    problem: dict[str, Any],
    sample: np.ndarray,
    y: np.ndarray,
    num_levels: int = 4,
) -> SensitivityResult:
    """
    Run SALib Morris analysis and return structured results.

    Args:
        problem:    SALib problem dict.
        sample:     Morris sample matrix used to generate y.
        y:          Model output array (one value per sample row).
        num_levels: Number of grid levels used in sampling.

    Returns:
        SensitivityResult with mu, mu_star, sigma per parameter.

    Raises:
        ValueError: If y has wrong length.
    """
    if len(y) != len(sample):
        raise ValueError(
            f"y length ({len(y)}) does not match sample rows ({len(sample)})"
        )

    si = morris_analyser.analyze(
        problem,
        sample,
        y,
        num_levels=num_levels,
        print_to_console=False,
        seed=42,
    )

    return SensitivityResult(
        problem=problem,
        mu=np.asarray(si["mu"]),
        mu_star=np.asarray(si["mu_star"]),
        sigma=np.asarray(si["sigma"]),
        names=list(problem["names"]),
    )


def save_results(
    result: SensitivityResult,
    output_dir: str | Path,
    prefix: str = "morris",
) -> dict[str, Path]:
    """
    Save Morris results to CSV and PNG.

    Args:
        result:     SensitivityResult from analyse_morris().
        output_dir: Directory for output files.
        prefix:     Filename prefix.

    Returns:
        Dict with keys 'csv' and 'png' mapping to output paths.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = result.to_dataframe()

    # CSV
    csv_path = out_dir / f"{prefix}_results.csv"
    df.to_csv(csv_path, index=False)

    # PNG -- mu_star bar chart with sigma error bars
    fig, ax = plt.subplots(figsize=(8, 5))
    y_pos = np.arange(len(df))
    ax.barh(
        y_pos,
        df["mu_star"],
        xerr=df["sigma"],
        align="center",
        color="steelblue",
        ecolor="black",
        capsize=4,
    )
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df["parameter"])
    ax.set_xlabel("Morris mu* (mean absolute elementary effect)")
    ax.set_title("Morris Sensitivity Analysis -- CES Investment Model")
    ax.invert_yaxis()
    plt.tight_layout()

    png_path = out_dir / f"{prefix}_chart.png"
    plt.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close()

    return {"csv": csv_path, "png": png_path}
