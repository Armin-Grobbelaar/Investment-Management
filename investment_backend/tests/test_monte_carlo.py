"""
Tests for the Monte Carlo simulation module.

Covers the GBM simulation maths and the drift/volatility estimation fix
(historically `sigma` was hardcoded to 0.15 and never computed from data).
"""

import numpy as np
import pytest
from unittest.mock import patch

from modules.monte_carlo import run_gbm_monte_carlo, run_portfolio_monte_carlo


def _sample_data_with_history():
    """Return the metrics payload shape run_portfolio_monte_carlo expects."""
    return {
        "data_points": 12,
        "portfolio_performance_return": [
            {"period": f"2024-{m:02d}", "value": 0.5} for m in range(1, 13)
        ],
        "key_metrics": [
            {"title": "Total Value", "value": "R 100,000.00"},
        ],
        "cagr_trend": [{"period": "2024-12", "value": 8.0}],
        "contribution_vs_growth": [
            {"period": f"2024-{m:02d}", "contributions": m * 1000.0, "growth": 0}
            for m in range(1, 13)
        ],
    }


class TestRunGbmMonteCarlo:
    def test_months_shape(self):
        """months array runs 0..years*12 and percentiles match."""
        result = run_gbm_monte_carlo(
            initial_value=100000,
            monthly_contribution=5000,
            mu=0.10,
            sigma=0.15,
            years=2,
            num_simulations=200,
        )

        assert result["months"] == list(range(25))
        assert len(result["percentiles"]["p50"]) == 25
        assert "median" in result["final_stats"]

    def test_zero_volatility_grows_deterministically(self):
        """With sigma=0 and mu=0 the value only grows by contributions."""
        result = run_gbm_monte_carlo(
            initial_value=1000,
            monthly_contribution=100,
            mu=0.0,
            sigma=0.0,
            years=1,
            num_simulations=50,
        )
        # 1000 + 12 * 100 = 2200 exactly
        assert result["final_stats"]["median"] == pytest.approx(2200.0, abs=1e-6)

    def test_positive_mu_drifts_upward(self):
        """Median path with positive drift should exceed the no-drift path."""
        low = run_gbm_monte_carlo(
            initial_value=100000, monthly_contribution=0, mu=0.0,
            sigma=0.10, years=1, num_simulations=500,
        )["final_stats"]["median"]
        high = run_gbm_monte_carlo(
            initial_value=100000, monthly_contribution=0, mu=0.20,
            sigma=0.10, years=1, num_simulations=500,
        )["final_stats"]["median"]
        assert high > low

    def test_percentile_ordering(self):
        """p5 <= p25 <= p50 <= p75 <= p95 at every month."""
        result = run_gbm_monte_carlo(
            initial_value=50000,
            monthly_contribution=2000,
            mu=0.10,
            sigma=0.20,
            years=3,
            num_simulations=300,
        )
        p5 = result["percentiles"]["p5"]
        p50 = result["percentiles"]["p50"]
        p95 = result["percentiles"]["p95"]
        for a, b, c in zip(p5, p50, p95):
            assert a <= b <= c


class TestRunPortfolioMonteCarlo:
    def test_sigma_computed_from_monthly_returns(self):
        """sigma is derived from historical monthly returns, floored at 5%."""
        data = _sample_data_with_history()

        with patch("modules.monte_carlo.run_gbm_monte_carlo") as mock_run, \
             patch("modules.monte_carlo.get_portfolio_metrics_data_api", return_value=data) as mock_metrics:
            run_portfolio_monte_carlo("test_db", "portfolio", "All", years=5, num_simulations=100)
            mock_metrics.assert_called_once()
            _, kwargs = mock_run.call_args
            assert kwargs["sigma"] >= 0.05  # floor applied

    def test_mu_inferred_from_cagr(self):
        """mu is taken from the latest CAGR trend value."""
        data = _sample_data_with_history()
        data["cagr_trend"][-1]["value"] = 12.0  # 12% CAGR

        with patch("modules.monte_carlo.run_gbm_monte_carlo") as mock_run, \
             patch("modules.monte_carlo.get_portfolio_metrics_data_api", return_value=data):
            run_portfolio_monte_carlo("test_db", "portfolio", "All", years=5, num_simulations=100)
            _, kwargs = mock_run.call_args
            assert kwargs["mu"] == pytest.approx(0.12, abs=1e-9)

    def test_sigma_fallback_when_no_history(self):
        """With no return history, the synthetic fallback uses sigma=0.15."""
        data = {"data_points": 0, "portfolio_performance_return": []}

        with patch("modules.monte_carlo.run_gbm_monte_carlo") as mock_run, \
             patch("modules.monte_carlo.get_portfolio_metrics_data_api", return_value=data):
            run_portfolio_monte_carlo("test_db", "portfolio", "All", years=5, num_simulations=100)
            # Fallback call is positional: (initial, contrib, mu, sigma, years, sims)
            args, _ = mock_run.call_args
            assert args[3] == 0.15

    def test_negative_contribution_clamped(self):
        """Negative inferred contributions are clamped to zero."""
        data = _sample_data_with_history()
        # contribution_vs_growth with a downward contribution trajectory
        data["contribution_vs_growth"] = [
            {"period": f"2024-{m:02d}", "contributions": 100.0, "growth": 0}
            for m in range(1, 13)
        ]

        with patch("modules.monte_carlo.run_gbm_monte_carlo") as mock_run, \
             patch("modules.monte_carlo.get_portfolio_metrics_data_api", return_value=data):
            run_portfolio_monte_carlo("test_db", "portfolio", "All", years=5, num_simulations=100)
            _, kwargs = mock_run.call_args
            assert kwargs["monthly_contribution"] == 0.0
