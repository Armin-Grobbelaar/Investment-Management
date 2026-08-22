"""
Retirement Planning Calculator
==============================
Supports:
- Three projection scenarios: stop contributing / continue / increase contributions
- Living Annuity + Life Annuity split with monthly income
- F.I.R.E., Lean FIRE, Fat FIRE, Coast FIRE metrics
- Inflation-adjusted (real) income
- Year-by-year projection series for charting
- Life annuity purchase rate from DB or online estimate
"""
import math
from typing import Optional


# ---------------------------------------------------------------------------
# Life Annuity Rate helpers
# ---------------------------------------------------------------------------

DEFAULT_LIFE_ANNUITY_RATE = 0.055  # 5.5% p.a.


def _fetch_life_annuity_rate_online() -> Optional[float]:
    """Try to fetch the current life annuity purchase rate from public sources."""
    try:
        import requests
        # Old Mutual publishes annuity rates in a structured way
        # Try a few known sources for SA annuity rates
        sources = [
            "https://www.oldmutual.co.za/annuity-rates",  # best effort
        ]
        for url in sources:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                import re
                # Look for percentage patterns like "5.8%" or "6.2 %"
                matches = re.findall(r'(\d+\.?\d*)\s*%', r.text)
                rates = [float(m) / 100 for m in matches if 3.0 < float(m) < 12.0]
                if rates:
                    # Median of found rates
                    rates.sort()
                    return rates[len(rates) // 2]
    except Exception:
        pass
    return None


def get_life_annuity_rate(database_name: str = None, estimate: bool = False) -> float:
    """Get the life annuity purchase rate.
    Priority: DB stored rate > online fetch (if estimate=True) > default 5.5%
    """
    # Try DB first
    try:
        from .database import get_config_value
        stored = get_config_value("life_annuity_rate", database_name=database_name)
        if stored is not None:
            return float(stored)
    except Exception:
        pass

    if estimate:
        online = _fetch_life_annuity_rate_online()
        if online is not None:
            # Store for future use
            try:
                from .database import get_db_connection
                db = database_name or "Investments"
                with get_db_connection(db) as (conn, cursor):
                    cursor.execute("""
                        INSERT INTO configuration (setting_key, setting_value, setting_description, setting_category)
                        VALUES ('life_annuity_rate', %s, 'Life annuity purchase rate (fetched online)', 'retirement')
                        ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value
                    """, (str(online),))
                    conn.commit()
            except Exception:
                pass
            return online

    return DEFAULT_LIFE_ANNUITY_RATE


# ---------------------------------------------------------------------------
# Core projection engine
# ---------------------------------------------------------------------------

def _future_value_series(
    current_value: float,
    monthly_rate: float,
    monthly_contribution: float,
    contribution_annual_increase: float,
    months: int,
) -> list:
    """
    Compute month-by-month portfolio value.
    Returns list of (month_index, portfolio_value, total_contributed).
    """
    series = []
    value = current_value
    contribution = monthly_contribution
    total_contributed = 0.0
    for m in range(months):
        value = value * (1 + monthly_rate) + contribution
        total_contributed += contribution
        series.append((m + 1, value, total_contributed))
        if (m + 1) % 12 == 0 and contribution_annual_increase > 0:
            contribution *= (1 + contribution_annual_increase)
    return series


def _annualized_growth_to_monthly(annual_rate: float) -> float:
    return (1 + annual_rate) ** (1 / 12) - 1


def _real_value(nominal: float, inflation: float, years: float) -> float:
    """Deflate a nominal value to today's purchasing power."""
    return nominal / ((1 + inflation) ** years)


def _fire_metrics(
    current_value: float,
    monthly_expenses: float,
    inflation: float,
    years_to_retirement: int,
    annual_growth_rate: float,
    monthly_contribution: float,
    contribution_annual_increase: float,
) -> dict:
    """Calculate FIRE-related metrics."""
    # F.I.R.E. number: 25x annual expenses (4% rule) — in today's money
    annual_expenses_today = monthly_expenses * 12
    fire_number_today = annual_expenses_today * 25
    lean_fire_today = annual_expenses_today * 20  # 5% rule
    fat_fire_today = annual_expenses_today * 33   # 3% rule

    # In nominal terms at retirement (inflated)
    fire_number_at_retirement = fire_number_today * ((1 + inflation) ** years_to_retirement)
    lean_fire_at_retirement = lean_fire_today * ((1 + inflation) ** years_to_retirement)
    fat_fire_at_retirement = fat_fire_today * ((1 + inflation) ** years_to_retirement)

    # Coast FIRE: amount needed NOW that grows to FIRE number with zero further contributions
    monthly_rate = _annualized_growth_to_monthly(annual_growth_rate)
    months = years_to_retirement * 12
    growth_factor = (1 + annual_growth_rate) ** years_to_retirement
    coast_fire_today = fire_number_at_retirement / growth_factor if growth_factor > 0 else 0

    # Project the current value + contributions to retirement
    series = _future_value_series(current_value, monthly_rate, monthly_contribution, contribution_annual_increase, months)
    projected_at_retirement = series[-1][1] if series else current_value

    # Shortfall against FIRE number
    shortfall = max(0, fire_number_at_retirement - projected_at_retirement)

    # Extra monthly contribution needed to bridge shortfall
    extra_monthly_needed = 0.0
    if shortfall > 0 and months > 0 and monthly_rate > 0:
        extra_monthly_needed = shortfall * monthly_rate / ((1 + monthly_rate) ** months - 1)

    # Months to reach FIRE number (continuous contributions, starting from today)
    months_to_fire = None
    if monthly_contribution > 0:
        val = current_value
        for m in range(1, 120 * 12):  # max 120 year search
            val = val * (1 + monthly_rate) + monthly_contribution
            if val >= fire_number_at_retirement:
                months_to_fire = m
                break

    is_on_track = projected_at_retirement >= fire_number_at_retirement

    return {
        "fire_number_today": round(fire_number_today, 2),
        "fire_number_at_retirement": round(fire_number_at_retirement, 2),
        "lean_fire_today": round(lean_fire_today, 2),
        "lean_fire_at_retirement": round(lean_fire_at_retirement, 2),
        "fat_fire_today": round(fat_fire_today, 2),
        "fat_fire_at_retirement": round(fat_fire_at_retirement, 2),
        "coast_fire_today": round(coast_fire_today, 2),
        "projected_at_retirement": round(projected_at_retirement, 2),
        "shortfall": round(shortfall, 2),
        "extra_monthly_needed": round(extra_monthly_needed, 2),
        "months_to_fire": months_to_fire,
        "is_on_track": is_on_track,
        "current_value": round(current_value, 2),
        "annual_expenses_today": round(annual_expenses_today, 2),
    }


def _project_scenario(
    label: str,
    current_value: float,
    monthly_rate_pre: float,
    monthly_rate_post: float,
    monthly_contribution: float,
    contribution_annual_increase: float,
    years_to_retirement: int,
    split_living: float,
    split_life: float,
    drawdown_rate: float,
    life_annuity_rate: float,
    inflation: float,
    cpi_escalation: float,
) -> dict:
    """Project a single scenario to retirement and compute monthly income."""
    months = years_to_retirement * 12
    # Pre-retirement accumulation (use historical RA IRR / assumed growth)
    series = _future_value_series(current_value, monthly_rate_pre, monthly_contribution, contribution_annual_increase, months)
    total_at_retirement = series[-1][1] if series else current_value
    total_contributed = series[-1][2] if series else 0.0

    # Annuity split
    living_capital = total_at_retirement * split_living
    life_capital = total_at_retirement * split_life

    # Living annuity income (drawdown of 2.5%-17.5% p.a., FSCA regulated)
    drawdown_rate = max(0.025, min(0.175, drawdown_rate))
    living_income_annual = living_capital * drawdown_rate
    living_income_monthly = living_income_annual / 12

    # Life annuity income (purchase rate proxy)
    life_income_annual = life_capital * life_annuity_rate
    life_income_monthly = life_income_annual / 12

    total_monthly_nominal = living_income_monthly + life_income_monthly

    # Real (inflation-adjusted) income — today's purchasing power
    real_factor = (1 + inflation) ** years_to_retirement
    total_monthly_real = total_monthly_nominal / real_factor
    living_income_monthly_real = living_income_monthly / real_factor
    life_income_monthly_real = life_income_monthly / real_factor

    # Year-by-year series (annual snapshots)
    yearly = []
    for yr in range(years_to_retirement + 1):
        m = yr * 12
        val = series[m - 1][1] if m > 0 and m - 1 < len(series) else current_value
        yearly.append({
            "year": yr,
            "portfolio_value": round(val, 2),
            "portfolio_value_real": round(val / ((1 + inflation) ** yr) if yr > 0 else val, 2),
        })

    return {
        "label": label,
        "monthly_contribution": round(monthly_contribution, 2),
        "total_at_retirement": round(total_at_retirement, 2),
        "total_contributed": round(total_contributed, 2),
        "living_annuity_capital": round(living_capital, 2),
        "life_annuity_capital": round(life_capital, 2),
        "living_income_monthly": round(living_income_monthly, 2),
        "life_income_monthly": round(life_income_monthly, 2),
        "total_monthly_income": round(total_monthly_nominal, 2),
        "living_income_monthly_real": round(living_income_monthly_real, 2),
        "life_income_monthly_real": round(life_income_monthly_real, 2),
        "total_monthly_income_real": round(total_monthly_real, 2),
        "yearly_series": yearly,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_retirement_projection(
    current_ra_value: float,
    split_living_annuity: float,
    split_life_annuity: float,
    assumed_growth: float,           # post-retirement Living Annuity growth
    drawdown_rate: float,
    inflation: float,
    escalation: float,               # CPI linking / escalation for Life Annuity
    monthly_contribution: float,
    years_to_retirement: int,
    ra_irr_historical: float,        # used as pre-retirement growth rate
    life_annuity_rate: float = DEFAULT_LIFE_ANNUITY_RATE,
    monthly_expenses: float = 0.0,   # for FIRE metrics
    contribution_annual_increase: float = 0.0,
    increased_monthly_contribution: float = None,
    database_name: str = None,
):
    """
    Full retirement projection.
    Returns:
    - Three scenarios (stop, continue, increase)
    - FIRE metrics
    - Input summary for calculation transparency
    """
    # Normalise splits to sum to 1.0
    total_split = split_living_annuity + split_life_annuity
    if total_split > 0:
        split_living_annuity = split_living_annuity / total_split
        split_life_annuity = split_life_annuity / total_split
    else:
        split_living_annuity = 0.5
        split_life_annuity = 0.5

    monthly_rate_pre = _annualized_growth_to_monthly(ra_irr_historical)
    monthly_rate_post = _annualized_growth_to_monthly(assumed_growth)
    increased_contribution = increased_monthly_contribution if increased_monthly_contribution is not None else monthly_contribution * 1.5

    # Scenario 1: Stop contributing now
    scenario_stop = _project_scenario(
        label="Stop Contributing",
        current_value=current_ra_value,
        monthly_rate_pre=monthly_rate_pre,
        monthly_rate_post=monthly_rate_post,
        monthly_contribution=0.0,
        contribution_annual_increase=0.0,
        years_to_retirement=years_to_retirement,
        split_living=split_living_annuity,
        split_life=split_life_annuity,
        drawdown_rate=drawdown_rate,
        life_annuity_rate=life_annuity_rate,
        inflation=inflation,
        cpi_escalation=escalation,
    )

    # Scenario 2: Continue current contributions
    scenario_continue = _project_scenario(
        label="Continue Contributions",
        current_value=current_ra_value,
        monthly_rate_pre=monthly_rate_pre,
        monthly_rate_post=monthly_rate_post,
        monthly_contribution=monthly_contribution,
        contribution_annual_increase=contribution_annual_increase,
        years_to_retirement=years_to_retirement,
        split_living=split_living_annuity,
        split_life=split_life_annuity,
        drawdown_rate=drawdown_rate,
        life_annuity_rate=life_annuity_rate,
        inflation=inflation,
        cpi_escalation=escalation,
    )

    # Scenario 3: Increased contributions
    scenario_increase = _project_scenario(
        label="Increased Contributions",
        current_value=current_ra_value,
        monthly_rate_pre=monthly_rate_pre,
        monthly_rate_post=monthly_rate_post,
        monthly_contribution=increased_contribution,
        contribution_annual_increase=contribution_annual_increase,
        years_to_retirement=years_to_retirement,
        split_living=split_living_annuity,
        split_life=split_life_annuity,
        drawdown_rate=drawdown_rate,
        life_annuity_rate=life_annuity_rate,
        inflation=inflation,
        cpi_escalation=escalation,
    )

    # FIRE metrics
    fire = {}
    if monthly_expenses > 0:
        fire = _fire_metrics(
            current_value=current_ra_value,
            monthly_expenses=monthly_expenses,
            inflation=inflation,
            years_to_retirement=years_to_retirement,
            annual_growth_rate=ra_irr_historical,
            monthly_contribution=monthly_contribution,
            contribution_annual_increase=contribution_annual_increase,
        )

    # Calculation transparency inputs
    calculation_inputs = {
        "current_ra_value": current_ra_value,
        "years_to_retirement": years_to_retirement,
        "split_living_annuity_pct": round(split_living_annuity * 100, 1),
        "split_life_annuity_pct": round(split_life_annuity * 100, 1),
        "ra_irr_historical_pct": round(ra_irr_historical * 100, 2),
        "assumed_post_retirement_growth_pct": round(assumed_growth * 100, 2),
        "inflation_pct": round(inflation * 100, 2),
        "drawdown_rate_pct": round(drawdown_rate * 100, 2),
        "life_annuity_rate_pct": round(life_annuity_rate * 100, 2),
        "escalation_pct": round(escalation * 100, 2),
        "monthly_contribution": monthly_contribution,
        "contribution_annual_increase_pct": round(contribution_annual_increase * 100, 2),
        "increased_monthly_contribution": increased_contribution,
        "monthly_expenses": monthly_expenses,
    }

    # Formulas for display
    formulas = {
        "living_annuity_income": "(Capital × Drawdown Rate) ÷ 12",
        "life_annuity_income": "(Capital × Life Annuity Rate) ÷ 12",
        "pre_retirement_growth": "Uses historical RA IRR as growth rate before retirement",
        "post_retirement_living_annuity": "Uses assumed investment growth for Living Annuity post retirement",
        "fire_number": "25 × Annual Expenses (based on 4% safe withdrawal rate)",
        "lean_fire": "20 × Annual Expenses (5% withdrawal rate)",
        "fat_fire": "33 × Annual Expenses (3% withdrawal rate)",
        "coast_fire": "FIRE Number ÷ (1 + growth_rate)^years — amount needed today to coast to FIRE",
        "real_income": "Nominal Income ÷ (1 + inflation)^years — today's purchasing power equivalent",
        "future_value": "FV = PV × (1+r)^n + PMT × [(1+r)^n - 1] / r  (pre-retirement: r = monthly IRR)",
    }

    return {
        "scenarios": [
            scenario_stop,
            scenario_continue,
            scenario_increase,
        ],
        "fire_metrics": fire,
        "calculation_inputs": calculation_inputs,
        "formulas": formulas,
    }
