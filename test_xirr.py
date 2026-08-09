from scipy import optimize
from datetime import date, timedelta
import pandas as pd

def is_leap_year(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

def fractional_years_between(start_date, end_date) -> float:
    if start_date is None or end_date is None:
        return 0.0
    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    if hasattr(end_date, 'date'):
        end_date = end_date.date()
    if end_date <= start_date:
        return 0.0

    total = 0.0
    cursor = start_date
    while cursor.year < end_date.year:
        year_end = date(cursor.year, 12, 31)
        days = (year_end - cursor).days + 1
        total += days / (366 if is_leap_year(cursor.year) else 365)
        cursor = date(cursor.year + 1, 1, 1)
    days = (end_date - cursor).days
    total += days / (366 if is_leap_year(cursor.year) else 365)
    return total

def xirr(dates, amounts):
    dates = list(dates)
    amounts = list(amounts)
    
    cashflows = sorted(zip(dates, amounts), key=lambda x: x[0])
    dates = [c[0] for c in cashflows]
    amounts = [c[1] for c in cashflows]
    
    start_date = dates[0]
    
    def npv(rate):
        total = 0.0
        for d, a in zip(dates, amounts):
            if rate <= -1:
                return float('inf')
            total += a / ((1 + rate) ** fractional_years_between(start_date, d))
        return total

    try:
        # Use brentq for robust root finding in a reasonable range
        return optimize.brentq(npv, -0.99, 1.0)
    except Exception as e:
        print("XIRR error:", e)
        return 0.0

# Test data based on user report:
# Total Contributions: 1,748,859.20 (outflow, negative)
# Net Worth: 603,462.23 (inflow/current value, positive)
# Span: let's assume 1.5 years
dates = [pd.to_datetime('2023-01-01'), pd.to_datetime('2024-06-30')]
amounts = [-1748859.20, 603462.23]

# print("Newton XIRR:", optimize.newton(lambda r: -1748859.20 + 603462.23 / ((1 + r) ** 1.5), 0.1))
print("Safe XIRR:", xirr(dates, amounts))
