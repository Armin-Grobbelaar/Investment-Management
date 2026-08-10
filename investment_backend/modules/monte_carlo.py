import numpy as np
import datetime
from .database import get_db_connection, get_config_value
from .metrics import get_investment_metrics_data
from .portfolio_metrics_api import get_portfolio_metrics_data_api

def run_gbm_monte_carlo(
    initial_value: float,
    monthly_contribution: float,
    mu: float,
    sigma: float,
    years: int = 10,
    num_simulations: int = 1000
) -> dict:
    """
    Run Geometric Brownian Motion (GBM) Monte Carlo simulation.
    Returns percentiles (5th, 25th, 50th, 75th, 95th) for each month.
    """
    months = years * 12
    dt = 1 / 12
    
    # Pre-allocate array: [num_simulations, months + 1]
    paths = np.zeros((num_simulations, months + 1))
    paths[:, 0] = initial_value
    
    for t in range(1, months + 1):
        # GBM stochastic term
        z = np.random.standard_normal(num_simulations)
        # S(t) = S(t-1) * exp((mu - sigma^2/2)dt + sigma * sqrt(dt) * Z) + contribution
        growth_factor = np.exp((mu - (sigma ** 2) / 2) * dt + sigma * np.sqrt(dt) * z)
        paths[:, t] = paths[:, t-1] * growth_factor + monthly_contribution

    # Calculate percentiles across all simulations for each month
    percentiles = {
        "p5": np.percentile(paths, 5, axis=0).tolist(),
        "p25": np.percentile(paths, 25, axis=0).tolist(),
        "p50": np.percentile(paths, 50, axis=0).tolist(),
        "p75": np.percentile(paths, 75, axis=0).tolist(),
        "p95": np.percentile(paths, 95, axis=0).tolist(),
    }
    
    # Calculate final value metrics
    final_values = paths[:, -1]
    
    return {
        "months": list(range(months + 1)),
        "percentiles": percentiles,
        "final_stats": {
            "median": float(np.median(final_values)),
            "mean": float(np.mean(final_values)),
            "p5": float(np.percentile(final_values, 5)),
            "p95": float(np.percentile(final_values, 95)),
            "prob_loss": float(np.mean(final_values < initial_value + (monthly_contribution * months)) * 100)
        },
        "inputs": {
            "initial_value": initial_value,
            "monthly_contribution": monthly_contribution,
            "expected_return": mu,
            "volatility": sigma,
            "years": years
        }
    }

def _cfg_float(table_key: str, default: float) -> float:
    val = get_config_value(table_key)
    if val is not None:
        try:
            return float(val)
        except (ValueError, TypeError):
            pass
    return default

def run_portfolio_monte_carlo(database_name: str, dimension_type: str, dimension_value: str, years: int = 10, num_simulations: int = 1000):
    """
    Run Monte Carlo for a portfolio dimension (e.g., 'portfolio', 'account_type:Retirement Annuity', etc.)
    Infers historical return and volatility from existing metrics.
    """
    # 1. Fetch historical data to infer mu and sigma
    data = get_portfolio_metrics_data_api(database_name, dimension_type, dimension_value)
    
    if not data or data.get("data_points", 1) == 0 or not data.get("portfolio_performance_return"):
        # Fallback values if no history
        return run_gbm_monte_carlo(
            _cfg_float("monte_carlo_fallback_value", 100000), 
            _cfg_float("monte_carlo_fallback_contribution", 5000), 
            _cfg_float("monte_carlo_fallback_mu", 0.10), 
            0.15, 
            years, 
            num_simulations
        )
    
    # 2. Extract total current value from key_metrics list
    current_value = 0
    for km in data.get("key_metrics", []):
        if km.get("title") == "Total Value":
            # Parse "R 123,456.78" → 123456.78
            val_str = str(km.get("value", "0")).replace("R", "").replace(",", "").strip()
            try:
                current_value = float(val_str)
            except ValueError as ve:
                import logging
                logging.error(f"Failed to parse total value '{val_str}': {ve}")
                current_value = 0
            break
    
    if current_value <= 0:
        current_value = _cfg_float("monte_carlo_fallback_value", 100000)
        
    # 3. Infer monthly contribution (average over last 6 months)
    recent_contribs = data.get("contribution_vs_growth", [])[-6:]
    if len(recent_contribs) > 1:
        diffs = [recent_contribs[i]["contributions"] - recent_contribs[i-1]["contributions"]
                 for i in range(1, len(recent_contribs))]
        monthly_contrib = sum(diffs) / len(diffs) if diffs else 0
    else:
        monthly_contrib = 0

    # 4. Infer mu from the latest CAGR
    try:
        cagr_val = float(data.get("cagr_trend", [])[-1]["value"])
        mu = cagr_val / 100.0
    except Exception:
        mu = _cfg_float("monte_carlo_fallback_mu", 0.10)
        
    # 5. Infer sigma (annualised volatility) from monthly return variance
    try:
        # Build a list of monthly total returns (ratio, e.g. 0.01 = 1%)
        cagr_series = data.get("portfolio_performance_return", [])
        if len(cagr_series) >= 6:
            returns = [float(d.get("value", 0)) / 100.0 for d in cagr_series[-12:]]
            if returns:
                sigma = float(np.std(returns, ddof=1)) * np.sqrt(12)  # annualise
                sigma = max(sigma, 0.05)  # floor at 5% to avoid unrealistic values
    except Exception:
        sigma = 0.15
    
    # Final fallback if nothing computed
    if 'sigma' not in dir() or sigma is None or sigma <= 0:
        sigma = 0.15
    
    return run_gbm_monte_carlo(
        initial_value=current_value,
        monthly_contribution=max(0, monthly_contrib),
        mu=mu,
        sigma=sigma,
        years=years,
        num_simulations=num_simulations
    )
