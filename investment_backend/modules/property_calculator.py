import os
import numpy as np
import numpy_financial as npf
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import json

from .database import get_config_value

def get_property_config():
    """Fetch property settings dynamically from the configuration table."""
    return {
        "bond_interest": float(get_config_value("default_bond_interest_rate", "11.75")),
        "rental_growth": float(get_config_value("default_rental_growth_rate", "5.0")),
        "vacancy_rate": float(get_config_value("default_vacancy_rate", "5.0")),
        "property_growth": float(get_config_value("default_property_growth_rate", "7.0")),
        "inflation_rate": float(get_config_value("default_inflation_rate", "5.0")),
        "projection_years": int(get_config_value("default_projection_years", "20")),
        "cgt_inclusion": float(get_config_value("cgt_inclusion_rate", "0.40")),
        "cgt_marginal": float(get_config_value("cgt_marginal_tax_rate", "0.45")),
        "cgt_annual_exclusion": float(get_config_value("cgt_annual_exclusion", "50000")),
        "cgt_residence_exclusion": float(get_config_value("cgt_primary_residence_exclusion", "3000000")),
        "monte_carlo_sims": int(get_config_value("monte_carlo_simulations", "1000"))
    }

# SA Transfer Duty brackets (static default, overridable)
TRANSFER_DUTY_BRACKETS = [
    {"lower": 0, "upper": 1210000, "base": 0, "rate": 0.0},
    {"lower": 1210000, "upper": 1663800, "base": 0, "rate": 0.03, "excess_from": 1210000},
    {"lower": 1663800, "upper": 2329300, "base": 13614, "rate": 0.06, "excess_from": 1663800},
    {"lower": 2329300, "upper": 2994800, "base": 53544, "rate": 0.08, "excess_from": 2329300},
    {"lower": 2994800, "upper": 13310000, "base": 106784, "rate": 0.11, "excess_from": 2994800},
    {"lower": 13310000, "upper": float('inf'), "base": 1241456, "rate": 0.13, "excess_from": 13310000}
]

def calculate_pmt(principal: float, annual_rate: float, term_years: int) -> float:
    """Calculate monthly bond repayment."""
    if principal <= 0 or term_years <= 0 or annual_rate < 0:
        return 0.0
    r = (annual_rate / 100.0) / 12.0
    n = term_years * 12
    if r == 0:
        return principal / n
    pmt = principal * (r * (1 + r)**n) / ((1 + r)**n - 1)
    return float(pmt)

def calculate_remaining_bond(principal: float, annual_rate: float, term_years: int, months_passed: int) -> float:
    """Calculate remaining bond balance."""
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
    brackets_json = get_config_value("transfer_duty_brackets")
    if brackets_json:
        try:
            brackets = json.loads(brackets_json)
        except Exception:
            brackets = TRANSFER_DUTY_BRACKETS
    else:
        brackets = TRANSFER_DUTY_BRACKETS

    for bracket in brackets:
        lower = bracket.get("lower", 0)
        upper = bracket.get("upper", float('inf'))
        if lower < purchase_price <= upper:
            if bracket.get("rate", 0.0) == 0.0:
                return 0.0
            excess_from = bracket.get("excess_from", lower)
            return bracket.get("base", 0.0) + (purchase_price - excess_from) * bracket["rate"]
    
    if brackets:
        last_bracket = brackets[-1]
        lower = last_bracket.get("lower", 0)
        excess_from = last_bracket.get("excess_from", lower)
        return last_bracket.get("base", 0.0) + (purchase_price - excess_from) * last_bracket.get("rate", 0.0)
    
    return 0.0

def calculate_cgt(proceeds: float, base_cost: float, inclusion_rate: float = 0.40, marginal_tax_rate: float = 0.45, annual_exclusion: float = 40000.0, primary_residence_exclusion: float = 0.0) -> dict:
    """Calculate SA Capital Gains Tax on disposal."""
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
    projection_years: int,
    cgt_inclusion_rate: float,
    cgt_marginal_tax_rate: float,
    is_primary_residence: bool = False
) -> dict:
    
    # Fetch latest configs for defaults if passed values are 0 or negative
    # (assuming 0 means 'use default')
    cfg = get_property_config()
    
    bond_interest_rate = bond_interest_rate if bond_interest_rate > 0 else cfg["bond_interest"]
    rental_growth_rate_pa = rental_growth_rate_pa if rental_growth_rate_pa > 0 else cfg["rental_growth"]
    vacancy_rate_pct = vacancy_rate_pct if vacancy_rate_pct > 0 else cfg["vacancy_rate"]
    property_growth_rate_pa = property_growth_rate_pa if property_growth_rate_pa > 0 else cfg["property_growth"]
    inflation_rate = inflation_rate if inflation_rate > 0 else cfg["inflation_rate"]
    projection_years = projection_years if projection_years > 0 else cfg["projection_years"]
    cgt_inclusion_rate = cgt_inclusion_rate if cgt_inclusion_rate > 0 else cfg["cgt_inclusion"]
    cgt_marginal_tax_rate = cgt_marginal_tax_rate if cgt_marginal_tax_rate > 0 else cfg["cgt_marginal"]

    if transfer_duty is None or transfer_duty < 0:
        transfer_duty = calculate_sa_transfer_duty(purchase_price)
    
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

    def get_sale_irr(sell_year: int) -> dict:
        if sell_year > projection_years:
            return {"irr": 0, "real_irr": 0, "cgt": 0}
            
        flows = annual_cash_flows[:sell_year + 1].copy()
        
        sell_value = purchase_price * (1 + property_growth)**sell_year
        remaining = calculate_remaining_bond(bond_amount, bond_interest_rate, bond_term_years, sell_year * 12)
        
        cgt = calculate_cgt(
            sell_value, total_acquisition_cost,
            cgt_inclusion_rate, cgt_marginal_tax_rate,
            cfg["cgt_annual_exclusion"],
            cfg["cgt_residence_exclusion"] if is_primary_residence else 0.0
        )
        
        net_sale_proceeds = sell_value - remaining - cgt["cgt_payable"]
        flows[-1] += net_sale_proceeds
        
        try:
            nominal_irr = npf.irr(flows) * 100
            real_irr = ((1 + nominal_irr/100) / (1 + inflation) - 1) * 100
        except:
            nominal_irr = 0.0
            real_irr = 0.0
            
        return {"irr": nominal_irr, "real_irr": real_irr, "cgt": cgt["cgt_payable"]}

    irr_5yr = get_sale_irr(min(5, projection_years))
    irr_10yr = get_sale_irr(min(10, projection_years))
    irr_20yr = get_sale_irr(min(20, projection_years))
    
    first_year_gross_yield = (monthly_rental_income * 12 / purchase_price * 100) if purchase_price > 0 else 0.0

    return {
        "transfer_duty": transfer_duty,
        "bond_amount": bond_amount,
        "first_year_gross_yield": first_year_gross_yield,
        "irr_5yr": irr_5yr["irr"],
        "irr_10yr": irr_10yr["irr"],
        "irr_20yr": irr_20yr["irr"],
        "real_irr_20yr": irr_20yr["real_irr"],
        "cgt_20yr": irr_20yr["cgt"],
        "projection": monthly_projection,
        "monthly_cash_flow_be_year": monthly_cash_flow_be_year,
        "cumulative_cash_flow_be_year": cumulative_cash_flow_be_year
    }

def run_property_monte_carlo(base_inputs: dict, num_simulations: int = 0, time_horizon_years: int = 0) -> dict:
    cfg = get_property_config()
    num_simulations = num_simulations if num_simulations > 0 else cfg["monte_carlo_sims"]
    time_horizon_years = time_horizon_years if time_horizon_years > 0 else cfg["projection_years"]
    
    # ... (rest of Monte Carlo implementation using dynamic config)

def run_sensitivity_analysis(base_inputs: dict) -> dict:
    """Run sensitivity analysis for property investment."""
    variations = {
        "bond_interest_rate": [-2.0, -1.0, 0, 1.0, 2.0],
        "property_growth_rate_pa": [-2.0, -1.0, 0, 1.0, 2.0],
        "rental_growth_rate_pa": [-2.0, -1.0, 0, 1.0, 2.0]
    }
    
    results = {}
    for param, offsets in variations.items():
        param_results = []
        for offset in offsets:
            inputs = base_inputs.copy()
            inputs[param] += offset
            # Need to call run_property_projection here
            proj = run_property_projection(**inputs)
            param_results.append({
                "offset": offset,
                "irr_10yr": proj["irr_10yr"],
                "be_year": proj["cumulative_cash_flow_be_year"]
            })
        results[param] = param_results
    return results
