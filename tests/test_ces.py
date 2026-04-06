"""Tests for the CES substitution model (core/ces.py)."""

from __future__ import annotations

import pytest

from ces_model.core.ces import (
    DEFAULT_ALPHA,
    DEFAULT_SIGMA,
    CESModel,
    CESResult,
    ces_substitution,
)

# ---------------------------------------------------------------------------
# ces_substitution: unit tests
# ---------------------------------------------------------------------------


class TestCESSubstitution:
    def test_parity_returns_alpha(self) -> None:
        """At parity (oil == renew price), renew_share == alpha."""
        result = ces_substitution(100.0, 100.0, sigma=1.8, alpha=0.5)
        assert abs(result.renew_share - 0.5) < 1e-9

    def test_higher_oil_raises_renew_share(self) -> None:
        """When oil is more expensive than renewables, renew_share > alpha."""
        result = ces_substitution(100.0, 50.0, sigma=1.8, alpha=0.5)
        assert result.renew_share > 0.5

    def test_lower_oil_reduces_renew_share(self) -> None:
        """When oil is cheaper than renewables, renew_share < alpha."""
        result = ces_substitution(50.0, 100.0, sigma=1.8, alpha=0.5)
        assert result.renew_share < 0.5

    def test_shares_sum_to_one(self) -> None:
        """renew_share + fossil_share == 1.0."""
        result = ces_substitution(80.0, 1.0, sigma=1.8, alpha=0.3)
        assert abs(result.renew_share + result.fossil_share - 1.0) < 1e-12

    def test_default_parameters(self) -> None:
        """Default sigma and alpha are applied."""
        result = ces_substitution(100.0, 100.0)
        assert abs(result.renew_share - DEFAULT_ALPHA) < 1e-9
        assert result.sigma == DEFAULT_SIGMA

    def test_cobb_douglas_limit(self) -> None:
        """sigma=1 (Cobb-Douglas limit): share equals alpha regardless of prices."""
        result = ces_substitution(200.0, 1.0, sigma=1.0, alpha=0.4)
        assert abs(result.renew_share - 0.4) < 1e-9

    def test_higher_sigma_amplifies_substitution(self) -> None:
        """Higher sigma -> bigger share shift when oil is more expensive."""
        r_low = ces_substitution(100.0, 50.0, sigma=1.2, alpha=0.5)
        r_high = ces_substitution(100.0, 50.0, sigma=2.5, alpha=0.5)
        assert r_high.renew_share > r_low.renew_share

    def test_negative_oil_price_raises(self) -> None:
        with pytest.raises(ValueError, match="price_oil must be positive"):
            ces_substitution(-10.0, 50.0)

    def test_zero_renew_price_raises(self) -> None:
        with pytest.raises(ValueError, match="price_renew must be positive"):
            ces_substitution(80.0, 0.0)

    def test_alpha_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="alpha must be in"):
            ces_substitution(80.0, 50.0, alpha=1.2)

    def test_zero_sigma_raises(self) -> None:
        with pytest.raises(ValueError, match="sigma must be positive"):
            ces_substitution(80.0, 50.0, sigma=0.0)

    def test_price_ratio_correct(self) -> None:
        result = ces_substitution(80.0, 40.0, sigma=1.8, alpha=0.3)
        assert abs(result.price_ratio - 2.0) < 1e-12

    def test_result_type(self) -> None:
        result = ces_substitution(65.0, 1.0)
        assert isinstance(result, CESResult)

    def test_result_post_init_validation(self) -> None:
        """CESResult raises if renew_share out of [0,1]."""
        with pytest.raises(ValueError, match="outside"):
            CESResult(
                renew_share=1.5,
                fossil_share=-0.5,
                renew_investment_index=1.5,
                fossil_investment_index=-0.5,
                price_ratio=1.0,
                sigma=1.8,
                alpha=0.3,
            )


# ---------------------------------------------------------------------------
# CESModel: calibration and validation
# ---------------------------------------------------------------------------


class TestCESModel:
    def test_default_instantiation(self) -> None:
        model = CESModel()
        assert model.sigma == DEFAULT_SIGMA
        assert model.alpha == DEFAULT_ALPHA

    def test_compute_share(self) -> None:
        model = CESModel(sigma=1.8, alpha=0.3)
        result = model.compute_share(price_oil=65.0, price_renew=1.0)
        assert 0.0 < result.renew_share < 1.0

    def test_calibrate_alpha(self) -> None:
        """calibrate_alpha should match the target share within 1e-6."""
        model = CESModel(sigma=1.8, alpha=0.3)
        model.calibrate_alpha(observed_share=0.40, price_oil=65.0, price_renew=1.0)
        result = model.compute_share(price_oil=65.0, price_renew=1.0)
        assert abs(result.renew_share - 0.40) < 1e-6

    def test_validate_mukhtarov(self) -> None:
        """Implied elasticity in plausible range (not exact match needed)."""
        model = CESModel(sigma=1.8, alpha=0.3)
        report = model.validate_mukhtarov()
        assert "implied_elasticity" in report
        assert report["implied_elasticity"] > 0.0
        # Ratio should not be astronomically off
        assert 0.01 < report["ratio"] < 100.0

    def test_investment_trajectory_length(self) -> None:
        model = CESModel()
        prices = [65.0, 67.0, 69.0, 70.0, 68.0, 65.0]
        traj = model.investment_trajectory(prices)
        assert len(traj) == len(prices)

    def test_investment_trajectory_rising_oil_raises_invest(self) -> None:
        """Rising oil prices from common base should increase renewable investment."""
        model = CESModel(sigma=1.8, alpha=0.3)
        # Both start at 65; high path rises to 100, low path falls to 40.
        common_start = 65.0
        high_prices = [common_start, 75.0, 85.0, 90.0, 95.0, 100.0]
        low_prices = [common_start, 60.0, 55.0, 50.0, 45.0, 40.0]
        high_traj = model.investment_trajectory(high_prices)
        low_traj = model.investment_trajectory(low_prices)
        high_term = high_traj[-1]["renew_invest_bn_usd"]
        low_term = low_traj[-1]["renew_invest_bn_usd"]
        assert high_term > low_term

    def test_investment_trajectory_capex_decline(self) -> None:
        """CAPEX decline should increase renewable investment vs. no decline."""
        model = CESModel()
        prices = [65.0] * 6
        no_decline = model.investment_trajectory(prices, capex_decline_rate=0.0)
        with_decline = model.investment_trajectory(prices, capex_decline_rate=0.30)
        # With cost decline, renewable price falls -> share increases
        no_term = no_decline[-1]["renew_invest_bn_usd"]
        with_term = with_decline[-1]["renew_invest_bn_usd"]
        assert with_term >= no_term
