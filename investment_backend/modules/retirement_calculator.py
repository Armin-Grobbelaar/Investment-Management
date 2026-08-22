
import numpy as np
import pandas as pd

def project_retirement(
    current_value: float,
    years_to_retirement: int,
    monthly_contribution: float,
    contribution_increase_rate: float,
    investment_growth_rate: float,
    inflation_rate: float,
    split_living_annuity: float, # 0.0 to 1.0
    drawdown_rate: float,
    escalation_rate: float
):
    """
    Project retirement fund and estimated monthly income.
    """
    # 1. Project value until retirement
    # Simple future value of RA projection with monthly contributions
    
    monthly_rate = (1 + investment_growth_rate) ** (1/12) - 1
    
    projected_value = current_value
    contribution = monthly_contribution
    
    for month in range(years_to_retirement * 12):
        projected_value = projected_value * (1 + monthly_rate) + contribution
        
        # Increase contribution yearly
        if (month + 1) % 12 == 0:
            contribution *= (1 + contribution_increase_rate)
            
    # 2. Calculate Annuity Split
    living_annuity_capital = projected_value * split_living_annuity
    life_annuity_capital = projected_value * (1 - split_living_annuity)
    
    # 3. Estimate Income (Simplified)
    
    # Living Annuity: Drawdown
    living_income_monthly = (living_annuity_capital * drawdown_rate) / 12
    
    # Life Annuity: Very rough estimate (e.g., 5-6% p.a. annuity rate)
    # This is highly dependent on market conditions at retirement.
    life_annuity_rate = 0.055 
    life_income_monthly = (life_annuity_capital * life_annuity_rate) / 12
    
    # Adjust for inflation/escalation
    # ... (This needs more refinement based on user requirements)
    
    return {
        "projected_total_value": projected_value,
        "living_annuity_capital": living_annuity_capital,
        "life_annuity_capital": life_annuity_capital,
        "living_income_monthly": living_income_monthly,
        "life_income_monthly": life_income_monthly,
        "total_monthly_income": living_income_monthly + life_income_monthly
    }

def calculate_fire_metrics(
    monthly_expenses: float,
    current_portfolio_value: float,
    annual_return_rate: float,
    years_to_retirement: int
):
    # F.I.R.E number = 25 * annual expenses
    fire_number = monthly_expenses * 12 * 25
    
    # Projected value at retirement
    projected_value = current_portfolio_value * (1 + annual_return_rate) ** years_to_retirement
    
    is_on_track = projected_value >= fire_number
    
    shortfall = fire_number - projected_value
    
    # Amount to add extra each month
    # Formula for future value of an annuity:
    # FV = P * (((1+r)^n - 1) / r)
    # P = FV * r / ((1+r)^n - 1)
    
    r = (1 + annual_return_rate) ** (1/12) - 1
    n = years_to_retirement * 12
    
    if n > 0 and r > 0:
        extra_monthly_needed = shortfall * r / ((1 + r) ** n - 1)
    else:
        extra_monthly_needed = 0 # Or handle edge case
        
    return {
        "fire_number": fire_number,
        "projected_value": projected_value,
        "is_on_track": is_on_track,
        "extra_monthly_needed": max(0, extra_monthly_needed)
    }
