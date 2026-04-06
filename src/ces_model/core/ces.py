"""
CES (Constant Elasticity of Substitution) substitution model.

Implements the two-input CES production/share function for fossil vs. renewable
energy, calibrated to Papageorgiou et al. (2017) sigma=1.8.

Mathematical framework adapted from Mercure & Salas (FTT:Power) with parameters
from:
  - Papageorgiou, Saam & Schulte (2017): sigma ~ 1.8, electricity sector, 26 countries
  - Mukhtarov et al. (2024): 1% oil price rise -> 0.16% renewable consumption rise
    (China)

CES share function:
    s_r = alpha * p_r^(rho-1) / [alpha * p_r^(rho-1) + (1-alpha) * p_f^(rho-1)]

where rho = 1 - 1/sigma (substitution parameter), p_r = renewable price index,
p_f = fossil price index, alpha = renewable technology weight.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Calibration constants
DEFAULT_SIGMA: float = 1.8  # Papageorgiou et al. 2017
DEFAULT_ALPHA: float = 0.30  # ~30% renewable share of new capacity (2024 baseline)

# Mukhtarov et al. (2024): 1% oil price rise -> 0.16% renewable consumption rise
MUKHTAROV_ELASTICITY: float = 0.16


@dataclass
class CESResult:
    """Output of a CES substitution calculation."""

    renew_share: float
    fossil_share: float
    renew_investment_index: float
    fossil_investment_index: float
    price_ratio: float
    sigma: float
    alpha: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.renew_share <= 1.0):
            raise ValueError(f"renew_share {self.renew_share} outside [0, 1]")


def ces_substitution(
    price_oil: float,
    price_renew: float,
    sigma: float = DEFAULT_SIGMA,
    alpha: float = DEFAULT_ALPHA,
) -> CESResult:
    """
    Compute the CES energy share for renewables given oil and renewable prices.

    The CES share function gives the fraction of total investment or consumption
    that flows to renewable energy, based on relative prices and the elasticity of
    substitution sigma.

    Args:
        price_oil:   Oil/fossil energy price index (USD/bbl or normalised).
        price_renew: Renewable energy price index (same units as price_oil).
        sigma:       Elasticity of substitution. Default 1.8 (Papageorgiou 2017).
                     sigma > 1 => gross substitutes (renewables and fossil are
                     substitutable; higher oil price raises renewable share).
        alpha:       Distribution/weight parameter for renewables in [0, 1].
                     At parity (price_oil == price_renew), renew_share == alpha.

    Returns:
        CESResult with renew_share, fossil_share, and investment indices.

    Raises:
        ValueError: If any price is non-positive or alpha is out of [0, 1].

    Examples:
        >>> r = ces_substitution(100.0, 100.0, sigma=1.8, alpha=0.5)
        >>> abs(r.renew_share - 0.5) < 1e-9
        True
        >>> r2 = ces_substitution(100.0, 50.0, sigma=1.8, alpha=0.5)
        >>> r2.renew_share > 0.5
        True
    """
    if price_oil <= 0.0:
        raise ValueError(f"price_oil must be positive, got {price_oil}")
    if price_renew <= 0.0:
        raise ValueError(f"price_renew must be positive, got {price_renew}")
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")
    if sigma <= 0.0:
        raise ValueError(f"sigma must be positive, got {sigma}")

    if abs(sigma - 1.0) < 1e-12:
        # sigma = 1 => Cobb-Douglas limit: share equals alpha regardless of prices
        renew_share = alpha
    else:
        # Standard CES cost-minimising input share:
        #   s_r = alpha * p_r^(1-sigma) /
        #         [alpha * p_r^(1-sigma) + (1-alpha) * p_f^(1-sigma)]
        #
        # When sigma > 1: (1-sigma) < 0 => lower p_r raises s_r, and
        # higher sigma amplifies substitution (correct economic direction).
        # At parity (p_r == p_f): s_r == alpha (verified analytically).
        exp = 1.0 - sigma
        renew_term = alpha * (price_renew**exp)
        fossil_term = (1.0 - alpha) * (price_oil**exp)
        denom = renew_term + fossil_term
        if denom == 0.0:
            raise ValueError("CES denominator is zero; check input prices.")
        renew_share = renew_term / denom

    fossil_share = 1.0 - renew_share
    price_ratio = price_oil / price_renew

    return CESResult(
        renew_share=float(renew_share),
        fossil_share=float(fossil_share),
        renew_investment_index=float(renew_share),
        fossil_investment_index=float(fossil_share),
        price_ratio=float(price_ratio),
        sigma=sigma,
        alpha=alpha,
    )


@dataclass
class CESModel:
    """
    Stateful CES model with calibrated parameters.

    Holds calibrated sigma and alpha and exposes convenience methods for
    computing shares and investment trajectories over a price path.

    Attributes:
        sigma:   Elasticity of substitution (default 1.8, Papageorgiou 2017).
        alpha:   Renewable distribution parameter (default 0.30).
        oil_elasticity: Empirical oil-price to renewable-consumption elasticity
                        (default 0.16, Mukhtarov et al. 2024). Used for
                        validation / cross-check only; the CES formula drives
                        the model.
    """

    sigma: float = DEFAULT_SIGMA
    alpha: float = DEFAULT_ALPHA
    oil_elasticity: float = MUKHTAROV_ELASTICITY
    _calibrated: bool = field(default=False, init=False, repr=False)

    def compute_share(
        self,
        price_oil: float,
        price_renew: float = 1.0,
    ) -> CESResult:
        """
        Compute renewable share at the given oil and renewable prices.

        Args:
            price_oil:   Oil price (USD/bbl or index).
            price_renew: Renewable price index. Default 1.0 (normalised).

        Returns:
            CESResult.
        """
        return ces_substitution(price_oil, price_renew, self.sigma, self.alpha)

    def investment_trajectory(
        self,
        price_path: list[float] | np.ndarray,
        base_invest_bn_usd: float = 807.0,
        renew_price_path: list[float] | np.ndarray | None = None,
        capex_decline_rate: float = 0.0,
    ) -> list[dict[str, float]]:
        """
        Compute investment trajectory over a sequence of oil prices.

        Investment scales from the base year proportional to the CES share
        and a technology cost-decline multiplier.

        Args:
            price_path:         Sequence of Brent oil prices (USD/bbl).
            base_invest_bn_usd: Base-year renewable power investment (USD bn).
                                Default 807.0 (IEA/IRENA 2024).
            renew_price_path:   Optional sequence of renewable price indices.
                                If None, held constant at 1.0.
            capex_decline_rate: Annual fractional cost decline for renewables
                                (0.0 = no learning curve, 0.20 = 20% decline
                                over the horizon). Applied linearly.

        Returns:
            List of dicts with keys: step, price_oil, price_renew, renew_share,
            renew_invest_bn_usd, fossil_invest_bn_usd.
        """
        prices = np.asarray(price_path, dtype=float)
        n = len(prices)

        if renew_price_path is not None:
            renew_prices = np.asarray(renew_price_path, dtype=float)
            if len(renew_prices) != n:
                raise ValueError(
                    "price_path and renew_price_path must have the same length"
                )
        else:
            renew_prices = np.ones(n, dtype=float)

        # Base-year share at step 0
        base_result = ces_substitution(
            prices[0], renew_prices[0], self.sigma, self.alpha
        )
        base_share = base_result.renew_share

        results: list[dict[str, float]] = []
        for i, (p_oil, p_renew) in enumerate(zip(prices, renew_prices)):
            # Apply capex decline: reduce renew price index linearly over steps
            decline_factor = 1.0 - capex_decline_rate * (i / max(n - 1, 1))
            adj_p_renew = p_renew * max(decline_factor, 0.1)  # floor at 10%

            result = ces_substitution(p_oil, adj_p_renew, self.sigma, self.alpha)

            # Scale investment from base proportional to share change
            if base_share > 0.0:
                share_multiplier = result.renew_share / base_share
            else:
                share_multiplier = 1.0

            renew_invest = base_invest_bn_usd * share_multiplier
            # Fossil investment as residual (using same total pool)
            if base_share > 0:
                total_invest = base_invest_bn_usd / base_share
            else:
                total_invest = base_invest_bn_usd
            fossil_invest = total_invest * result.fossil_share

            results.append(
                {
                    "step": i,
                    "price_oil": p_oil,
                    "price_renew": adj_p_renew,
                    "renew_share": result.renew_share,
                    "renew_invest_bn_usd": renew_invest,
                    "fossil_invest_bn_usd": fossil_invest,
                }
            )

        return results

    def calibrate_alpha(
        self,
        observed_share: float,
        price_oil: float,
        price_renew: float = 1.0,
    ) -> "CESModel":
        """
        Calibrate alpha so the model matches an observed renewable share at
        given prices.

        Uses bisection to find alpha such that
        ces_substitution(price_oil, price_renew, sigma, alpha).renew_share
        == observed_share.

        Args:
            observed_share: Observed renewable share (fraction, e.g. 0.30).
            price_oil:      Corresponding oil price.
            price_renew:    Corresponding renewable price (default 1.0).

        Returns:
            Self with updated alpha (for method chaining).
        """
        from scipy.optimize import brentq

        def _objective(a: float) -> float:
            r = ces_substitution(price_oil, price_renew, self.sigma, a)
            return r.renew_share - observed_share

        # Search alpha in (1e-6, 1 - 1e-6)
        lo, hi = 1e-6, 1.0 - 1e-6
        try:
            alpha_cal = brentq(_objective, lo, hi, xtol=1e-10, maxiter=200)
        except ValueError as exc:
            raise ValueError(
                f"Could not calibrate alpha for observed_share={observed_share}: {exc}"
            )
        self.alpha = float(alpha_cal)
        self._calibrated = True
        return self

    def validate_mukhtarov(
        self,
        base_price: float = 65.0,
        pct_shock: float = 0.01,
    ) -> dict[str, float]:
        """
        Validate that a 1% oil price rise produces ~0.16% renewable share increase.

        Compares the implied elasticity from the CES model against the
        Mukhtarov et al. (2024) empirical estimate of +0.16% per 1% oil rise.

        Args:
            base_price: Base oil price (USD/bbl). Default 65 (STEPS 2030).
            pct_shock:  Oil price shock size (fractional). Default 0.01 (1%).

        Returns:
            Dict with keys: implied_elasticity, mukhtarov_target, ratio.
        """
        base = ces_substitution(base_price, 1.0, self.sigma, self.alpha)
        shocked = ces_substitution(
            base_price * (1.0 + pct_shock), 1.0, self.sigma, self.alpha
        )
        pct_share_change = (shocked.renew_share - base.renew_share) / base.renew_share
        implied_elasticity = pct_share_change / pct_shock

        return {
            "implied_elasticity": implied_elasticity,
            "mukhtarov_target": self.oil_elasticity,
            "ratio": implied_elasticity / self.oil_elasticity,
            "base_share": base.renew_share,
            "shocked_share": shocked.renew_share,
        }
