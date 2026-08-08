import os
import numpy as np
import numpy_financial as npf
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from .database import get_config_value


def _cfg(env_key: str, table_key: str, default: str) -> str:
    """Resolve a default: environment variable first, then the configuration
    table, then the built-in fallback. Values are read once at import time, so
    configuration-table changes take effect on the next restart."""
    env_val = os.environ.get(env_key)
    if env_val is not None:
        return env_val
    return get_config_value(table_key, default)


# SA Transfer Duty brackets (2024/25 tax year) - configurable via environment
TRANSFER_DUTY_BRACKETS = [
    {
        "lower": 0,
        "upper": 1100000,
        "base": 0,
        "rate": 0.0
    },
    {
        "lower": 1100000,
        "upper": 1512500,
        "base": 0,
        "rate": 0.03,
        "excess_from": 1100000
    },
    {
        "lower": 1512500,
        "upper": 2117500,
        "base": 12375,
        "rate": 0.06,
        "excess_from": 1512500
    },
    {
        "lower": 2117500,
        "upper": 2722500,
        "base": 48675,
        "rate": 0.08,
        "excess_from": 2117500
    },
    {
        "lower": 2722500,
        "upper": 12100000,
        "base": 97075,
        "rate": 0.11,
        "excess_from": 2722500
    },
    {
        "lower": 12100000,
        "upper": float('inf'),
        "base": 1128600,
        "rate": 0.13,
        "excess_from": 12100000
    }
]

# Capital Gains Tax defaults — resolved from the configuration table with
# environment-variable override, then a built-in fallback (see _cfg).
DEFAULT_CGT_INCLUSION_RATE = float(_cfg("CGT_INCLUSION_RATE", "cgt_inclusion_rate", "0.40"))
DEFAULT_CGT_MARGINAL_TAX_RATE = float(_cfg("CGT_MARGINAL_TAX_RATE", "cgt_marginal_tax_rate", "0.45"))
DEFAULT_CGT_ANNUAL_EXCLUSION = float(_cfg("CGT_ANNUAL_EXCLUSION", "cgt_annual_exclusion", "40000"))
DEFAULT_CGT_PRIMARY_RESIDENCE_EXCLUSION = float(_cfg("CGT_PRIMARY_RESIDENCE_EXCLUSION", "cgt_primary_residence_exclusion", "2000000"))
DEFAULT_PROJECTION_YEARS = int(_cfg("PROPERTY_PROJECTION_YEARS", "default_projection_years", "20"))
DEFAULT_MONTE_CARLO_SIMULATIONS = int(_cfg("MONTE_CARLO_SIMULATIONS", "monte_carlo_simulations", "1000"))
DEFAULT_BOND_INTEREST_RATE = float(_cfg("DEFAULT_BOND_INTEREST_RATE", "default_bond_interest_rate", "11.75"))
DEFAULT_RENTAL_GROWTH_RATE = float(_cfg("DEFAULT_RENTAL_GROWTH_RATE", "default_rental_growth_rate", "5.0"))
DEFAULT_VACANCY_RATE = float(_cfg("DEFAULT_VACANCY_RATE", "default_vacancy_rate", "5.0"))
DEFAULT_PROPERTY_GROWTH_RATE = float(_cfg("DEFAULT_PROPERTY_GROWTH_RATE", "default_property_growth_rate", "7.0"))
DEFAULT_INFLATION_RATE = float(_cfg("DEFAULT_INFLATION_RATE", "default_inflation_rate", "5.0"))
# Standard deviations are in percentage points (matching the percentage-unit inputs)
DEFAULT_PROPERTY_GROWTH_STD = float(os.environ.get("PROPERTY_GROWTH_STD", "2.5"))
DEFAULT_RENTAL_GROWTH_STD = float(os.environ.get("RENTAL_GROWTH_STD", "2.0"))
DEFAULT_INTEREST_RATE_STD = float(os.environ.get("INTEREST_RATE_STD", "1.5"))
MONTE_CARLO_SEED = int(os.environ.get("MONTE_CARLO_SEED", "42"))

def calculate_pmt(principal: float, annual_rate: float, term_years: int) -> float:
    """Calculate monthly bond repayment using standard PMT formula."""
    if principal <= 0 or term_years <= 0 or annual_rate < 0:
        return 0.0
    r = (annual_rate / 100.0) / 12.0
    n = term_years * 12
    if r == 0:
        return principal / n
    pmt = principal * (r * (1 + r)**n) / ((1 + r)**n - 1)
    return float(pmt)

def calculate_remaining_bond(principal: float, annual_rate: float, term_years: int, months_passed: int) -> float:
    """Calculate remaining bond balance after a number of monthly payments."""
    if principal <= 0 or months_passed <= 0:
        return max(0.0, principal)
    if months_passed >= term_years * 12:
        return 0.0
    r = (annual_rate / 100.0) / 12.0
    n = term_years * 12
    if r == 0:
        return principal - (principal / n) * months_passed
    balance = principal * (((1 + r)**n - (1 + r)**months_passed) / ((1 + r)**n - 1))
    return float(balance)

def calculate_sa_transfer_duty(purchase_price: float) -> float:
    """Calculate SA Transfer Duty using configurable brackets."""
    for bracket in TRANSFER_DUTY_BRACKETS:
        if bracket["lower"] < purchase_price <= bracket["upper"]:
            if bracket["rate"] == 0.0:
                return 0.0
            excess = purchase_price - bracket.get("excess_from", bracket["lower"])
            return bracket["base"] + excess * bracket["rate"]
    # Default fallback to highest bracket
    last_bracket = TRANSFER_DUTY_BRACKETS[-1]
    excess = purchase_price - last_bracket.get("excess_from", last_bracket["lower"])
    return last_bracket["base"] + excess * last_bracket["rate"]

def calculate_cgt(proceeds: float, base_cost: float, inclusion_rate: float = DEFAULT_CGT_INCLUSION_RATE, marginal_tax_rate: float = DEFAULT_CGT_MARGINAL_TAX_RATE, annual_exclusion: float = DEFAULT_CGT_ANNUAL_EXCLUSION, primary_residence_exclusion: float = 0.0) -> dict:
    """Calculate SA Capital Gains Tax on disposal.

    Exclusions are applied in order: the primary-residence exclusion
    (R2m for a person's primary residence, only when the user confirms the
    property is their primary residence) and then the individual's annual
    exclusion. Passing 0.0 for primary_residence_exclusion (the default)
    models a non-primary-residence disposal.
    """
    gain = max(0.0, proceeds - base_cost)
    net_gain = max(0.0, gain - primary_residence_exclusion - annual_exclusion)
    taxable_gain = net_gain * inclusion_rate
    cgt_payable = taxable_gain * marginal_tax_rate
    effective_rate = cgt_payable / gain if gain > 0 else 0
    return {
        "net_gain": float(net_gain),
        "taxable_gain": float(taxable_gain),
        "cgt_payable": float(cgt_payable),
        "effective_rate": float(effective_rate),
        "primary_residence_exclusion": float(primary_residence_exclusion)
    }

def run_property_projection(
    purchase_price: float,
    transfer_costs: float,
    transfer_duty: float,
    bond_registration_costs: float,
    other_acquisition_costs: float,
    deposit_amount: float,
    bond_interest_rate: float,
    bond_term_years: int,
    monthly_levy: float,
    monthly_rates: float,
    monthly_insurance: float,
    monthly_maintenance_reserve: float,
    monthly_management_fee_pct: float,
    monthly_other_costs: float,
    monthly_rental_income: float,
    rental_growth_rate_pa: float,
    vacancy_rate_pct: float,
    property_growth_rate_pa: float,
    inflation_rate: float,
    projection_years: int = DEFAULT_PROJECTION_YEARS,
    cgt_inclusion_rate: float = DEFAULT_CGT_INCLUSION_RATE,
    cgt_marginal_tax_rate: float = DEFAULT_CGT_MARGINAL_TAX_RATE,
    is_primary_residence: bool = False
) -> dict:
    if transfer_duty is None or transfer_duty < 0:
        transfer_duty = calculate_sa_transfer_duty(purchase_price)
    
    # Rates are supplied as percentages (e.g. 10.5, 5, 6) — convert to decimals.
    bond_rate = bond_interest_rate / 100.0
    rental_growth = rental_growth_rate_pa / 100.0
    property_growth = property_growth_rate_pa / 100.0
    inflation = inflation_rate / 100.0
    
    total_acquisition_cost = purchase_price + transfer_costs + transfer_duty + bond_registration_costs + other_acquisition_costs
    initial_cash_outflow = deposit_amount + transfer_costs + transfer_duty + bond_registration_costs + other_acquisition_costs
    bond_amount = max(0.0, purchase_price - deposit_amount)
    
    bond_monthly_repayment = calculate_pmt(bond_amount, bond_interest_rate, bond_term_years)
    
    monthly_projection = []
    annual_cash_flows = [-initial_cash_outflow]
    

    current_property_value = purchase_price
    cumulative_cash_flow = -initial_cash_outflow
    
    monthly_cash_flow_be_year = None
    cumulative_cash_flow_be_year = None
    
    all_monthly_cash_flows = []
    
    for year in range(1, projection_years + 1):
        factor = (1 + inflation)**(year - 1)
        rental_factor = (1 + rental_growth)**(year - 1)
        
        y_rental = monthly_rental_income * rental_factor
        y_levy = monthly_levy * factor
        y_rates = monthly_rates * factor
        y_insurance = monthly_insurance * factor
        y_maintenance = monthly_maintenance_reserve * factor
        y_other = monthly_other_costs * factor
        y_mgmt = y_rental * (monthly_management_fee_pct / 100.0)
        
        gross_monthly_expenses = y_levy + y_rates + y_insurance + y_maintenance + y_mgmt + y_other
        vacancy_allowance = y_rental * (vacancy_rate_pct / 100.0)
        net_monthly_income = y_rental - vacancy_allowance - gross_monthly_expenses
        
        monthly_cash_flow = net_monthly_income - bond_monthly_repayment
        
        if monthly_cash_flow >= 0 and monthly_cash_flow_be_year is None:
            monthly_cash_flow_be_year = year
            
        annual_net_cash_flow = monthly_cash_flow * 12
        cumulative_cash_flow += annual_net_cash_flow
        
        if cumulative_cash_flow >= 0 and cumulative_cash_flow_be_year is None:
            cumulative_cash_flow_be_year = year
            
        annual_cash_flows.append(annual_net_cash_flow)
        for _ in range(12):
            all_monthly_cash_flows.append(monthly_cash_flow)
        
        current_property_value = purchase_price * (1 + property_growth)**year
        remaining_bond = calculate_remaining_bond(bond_amount, bond_interest_rate, bond_term_years, year * 12)
        
        monthly_projection.append({
            "year": year,
            "monthly_rental": round(y_rental, 2),
            "monthly_expenses": round(gross_monthly_expenses, 2),
            "monthly_bond": round(bond_monthly_repayment, 2),
            "monthly_net_cash_flow": round(monthly_cash_flow, 2),
            "annual_net_cash_flow": round(annual_net_cash_flow, 2),
            "cumulative_cash_flow": round(cumulative_cash_flow, 2),
            "property_value": round(current_property_value, 2),
            "remaining_bond": round(remaining_bond, 2),
            "equity": round(current_property_value - remaining_bond, 2)
        })

    # Function to calculate IRR including sale of property
    def get_sale_irr(sell_year: int) -> dict:
        if sell_year > projection_years:
            return {"irr": 0, "real_irr": 0, "cgt": 0}
            
        flows = annual_cash_flows[:sell_year + 1].copy()
        
        sell_value = purchase_price * (1 + property_growth)**sell_year
        remaining = calculate_remaining_bond(bond_amount, bond_interest_rate, bond_term_years, sell_year * 12)
        
        # Calculate CGT
        base_cost = total_acquisition_cost # Simplified
        cgt = calculate_cgt(
            sell_value, base_cost,
            cgt_inclusion_rate, cgt_marginal_tax_rate,
            primary_residence_exclusion=(
                DEFAULT_CGT_PRIMARY_RESIDENCE_EXCLUSION if is_primary_residence else 0.0
            )
        )
        
        net_sale_proceeds = sell_value - remaining - cgt["cgt_payable"]
        flows[-1] += net_sale_proceeds
        
        try:
            nominal_irr = npf.irr(flows) * 100
            real_irr = ((1 + nominal_irr/100) / (1 + inflation) - 1) * 100
        except:
            nominal_irr = 0.0
            real_irr = 0.0
            
        return {
            "irr": nominal_irr, 
            "real_irr": real_irr, 
            "cgt": cgt["cgt_payable"],
            "net_proceeds": net_sale_proceeds
        }

    irr_5yr = get_sale_irr(min(5, projection_years))
    irr_10yr = get_sale_irr(min(10, projection_years))
    irr_15yr = get_sale_irr(min(15, projection_years))
    irr_20yr = get_sale_irr(min(20, projection_years))
    
    first_year_gross_yield = (monthly_rental_income * 12) / purchase_price * 100
    first_year_net_yield = (monthly_projection[0]["annual_net_cash_flow"]) / purchase_price * 100 if monthly_projection else 0
    
    return {
        "initial_outflow": initial_cash_outflow,
        "transfer_duty": transfer_duty,
        "total_acquisition_cost": total_acquisition_cost,
        "bond_amount": bond_amount,
        "bond_monthly_repayment": bond_monthly_repayment,
        "first_year_gross_yield": first_year_gross_yield,
        "first_year_net_yield": first_year_net_yield,
        "monthly_cash_flow_be_year": monthly_cash_flow_be_year,
        "cumulative_cash_flow_be_year": cumulative_cash_flow_be_year,
        "irr_5yr": irr_5yr["irr"],
        "irr_10yr": irr_10yr["irr"],
        "irr_15yr": irr_15yr["irr"],
        "irr_20yr": irr_20yr["irr"],
        "real_irr_5yr": irr_5yr["real_irr"],
        "real_irr_10yr": irr_10yr["real_irr"],
        "real_irr_15yr": irr_15yr["real_irr"],
        "real_irr_20yr": irr_20yr["real_irr"],
        "cgt_10yr": irr_10yr["cgt"],
        "cgt_20yr": irr_20yr["cgt"],
        "projection": monthly_projection,
        "annual_cash_flows": annual_cash_flows,
        "all_monthly_cash_flows": all_monthly_cash_flows
    }

def run_sensitivity_analysis(base_inputs: dict) -> dict:
    """Run sensitivity analysis varying key parameters."""
    results = {
        "interest_rate": [],
        "rental_income": [],
        "property_growth": []
    }
    
    # Interest rate variations (percentage points, e.g. ±1pp, ±2pp)
    base_rate = base_inputs["bond_interest_rate"]
    for diff in [-2.0, -1.0, 0, 1.0, 2.0]:
        inputs = base_inputs.copy()
        inputs["bond_interest_rate"] = max(0, base_rate + diff)
        proj = run_property_projection(**inputs)
        results["interest_rate"].append({
            "variation": f"{diff:+.0f}pp",
            "value": inputs["bond_interest_rate"],
            "irr_10yr": proj["irr_10yr"],
            "monthly_cf_yr1": proj["projection"][0]["monthly_net_cash_flow"]
        })
        
    # Rental income variations 
    base_rent = base_inputs["monthly_rental_income"]
    for pct in [-0.2, -0.1, 0, 0.1, 0.2]:
        inputs = base_inputs.copy()
        inputs["monthly_rental_income"] = base_rent * (1 + pct)
        proj = run_property_projection(**inputs)
        results["rental_income"].append({
            "variation": f"{pct*100:+.0f}%",
            "value": inputs["monthly_rental_income"],
            "irr_10yr": proj["irr_10yr"],
            "monthly_cf_yr1": proj["projection"][0]["monthly_net_cash_flow"]
        })
        
    # Property growth variations (percentage points)
    base_growth = base_inputs["property_growth_rate_pa"]
    for diff in [-2.0, -1.0, 0, 1.0, 2.0]:
        inputs = base_inputs.copy()
        inputs["property_growth_rate_pa"] = base_growth + diff
        proj = run_property_projection(**inputs)
        results["property_growth"].append({
            "variation": f"{diff:+.0f}pp",
            "value": inputs["property_growth_rate_pa"],
            "irr_10yr": proj["irr_10yr"],
            "monthly_cf_yr1": proj["projection"][0]["monthly_net_cash_flow"]
        })
        
    return results

def run_property_monte_carlo(
    base_inputs: dict,
    num_simulations: int = DEFAULT_MONTE_CARLO_SIMULATIONS,
    time_horizon_years: int = DEFAULT_PROJECTION_YEARS,
    property_growth_std: float = DEFAULT_PROPERTY_GROWTH_STD,
    rental_growth_std: float = DEFAULT_RENTAL_GROWTH_STD,
    interest_rate_std: float = DEFAULT_INTEREST_RATE_STD
) -> dict:
    """Run Monte Carlo simulation for property investment."""
    np.random.seed(MONTE_CARLO_SEED)
    
    base_prop_growth = base_inputs["property_growth_rate_pa"]
    base_rent_growth = base_inputs["rental_growth_rate_pa"]
    base_interest = base_inputs["bond_interest_rate"]
    
    # Generate random paths
    prop_growth_paths = np.random.normal(base_prop_growth, property_growth_std, num_simulations)
    rent_growth_paths = np.random.normal(base_rent_growth, rental_growth_std, num_simulations)
    interest_paths = np.random.normal(base_interest, interest_rate_std, num_simulations)
    interest_paths = np.maximum(1.0, interest_paths) # prevent unrealistic (near-zero) rates
    
    irrs = []
    positive_cf_years = []
    
    # Prepare base dict
    inputs = base_inputs.copy()
    inputs["projection_years"] = time_horizon_years
    
    for i in range(num_simulations):
        inputs["property_growth_rate_pa"] = prop_growth_paths[i]
        inputs["rental_growth_rate_pa"] = rent_growth_paths[i]
        inputs["bond_interest_rate"] = interest_paths[i]
        
        res = run_property_projection(**inputs)
        
        irrs.append(res.get(f"irr_{time_horizon_years}yr", res.get("irr_10yr", 0)))
        positive_cf_years.append(res["monthly_cash_flow_be_year"] or 99)
        
    irrs = np.array(irrs)
    positive_cf_years = np.array(positive_cf_years)
    
    # Inflation is supplied as a percentage (e.g. 5.0); fall back to decimal if < 1
    inflation_pct = float(base_inputs.get("inflation_rate", 5.0) or 0.0)
    if inflation_pct < 1.0:
        inflation_pct *= 100.0
    inflation_threshold_pct = inflation_pct
    
    return {
        "num_simulations": num_simulations,
        "percentiles_irr": {
            "p5": float(np.percentile(irrs, 5)),
            "p25": float(np.percentile(irrs, 25)),
            "p50": float(np.percentile(irrs, 50)),
            "p75": float(np.percentile(irrs, 75)),
            "p95": float(np.percentile(irrs, 95))
        },
        "prob_positive_irr": float(np.mean(irrs > 0) * 100),
        "prob_irr_beats_inflation": float(np.mean(irrs > inflation_threshold_pct) * 100),
        "median_cashflow_breakeven_year": float(np.median(positive_cf_years[positive_cf_years < 99])) if any(positive_cf_years < 99) else None
    }