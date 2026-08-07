import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, date
from .database import get_db_connection, DEFAULT_DB

# Configuration constants - configurable via environment
DAYS_IN_YEAR = float(os.environ.get("DAYS_IN_YEAR", "365.25"))
CAGR_EXCELLENT_THRESHOLD = float(os.environ.get("CAGR_EXCELLENT_THRESHOLD", "0.15"))
CAGR_GOOD_THRESHOLD = float(os.environ.get("CAGR_GOOD_THRESHOLD", "0.08"))
CAGR_MODERATE_THRESHOLD = float(os.environ.get("CAGR_MODERATE_THRESHOLD", "0.0"))
PREDICTION_ACCURACY_GOOD_THRESHOLD = float(os.environ.get("PREDICTION_ACCURACY_GOOD", "5.0"))
PREDICTION_ACCURACY_ACCEPTABLE_THRESHOLD = float(os.environ.get("PREDICTION_ACCURACY_ACCEPTABLE", "15.0"))
CURRENCY_COUNTRY_MAP = {
    'ZAR': os.environ.get("COUNTRY_ZAR", "South Africa"),
    'USD': os.environ.get("COUNTRY_USD", "United States"),
    'GBP': os.environ.get("COUNTRY_GBP", "United Kingdom"),
    'EUR': os.environ.get("COUNTRY_EUR", "Euro Area")
}

def xirr(dates, amounts):
    """
    Calculate Internal Rate of Return (IRR) for a schedule of cash flows.
    """
    try:
        from scipy import optimize
    except ImportError:
        return 0.0

    dates = list(dates)
    amounts = list(amounts)
    if len(dates) != len(amounts):
        return 0.0
    
    cashflows = sorted(zip(dates, amounts), key=lambda x: x[0])
    dates = [c[0] for c in cashflows]
    amounts = [c[1] for c in cashflows]
    
    if not amounts:
        return 0.0

    start_date = dates[0]
    
    def npv(rate):
        total = 0.0
        for d, a in zip(dates, amounts):
            days = (d - start_date).days
            if rate <= -1:
                return float('inf')
            total += a / ((1 + rate) ** (days / 365.25))
        return total

    try:
        return optimize.newton(npv, 0.1)
    except:
        return 0.0

def is_leap_year(year: int) -> bool:
    """Check whether a given year is a leap year."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

def adjust_value(value: float, date_obj, current_value_date, inflation_df: pd.DataFrame) -> float:
    """
    Adjust a single value for inflation from its date to the target date.
    """
    if inflation_df is None or inflation_df.empty or "year" not in inflation_df.columns:
        return value
    total_factor = 1.0
    current = date_obj
    # Ensure current is datetime
    if not isinstance(current, datetime):
        current = pd.to_datetime(current)
        
    # Ensure current_value_date is datetime
    if not isinstance(current_value_date, datetime):
        current_value_date = pd.to_datetime(current_value_date)

    while current.year <= current_value_date.year:
        # Get inflation for the current year
        inflation_row = inflation_df[inflation_df["year"] == current.year]
        if inflation_row.empty:
            # Skip years not present in inflation data
            current = datetime(current.year + 1, 1, 1)
            continue
        inflation = inflation_row.iloc[0]["inflation_rate"]
        
        # Determine the period to adjust for
        if current.year < current_value_date.year:
            end_date = datetime(current.year + 1, 1, 1)
        else:
            end_date = current_value_date
        
        # Calculate fraction of the year passed
        days_in_year = 366 if is_leap_year(current.year) else 365
        days_between = (end_date - current).days
        proportion = days_between / days_in_year
        
        # Apply inflation proportionally for that period
        total_factor *= (1 + inflation) ** proportion
        
        # Move to next year
        current = end_date
        if current >= current_value_date:
            break
    
    # Return the inflation-adjusted (real) value
    return value / total_factor

def adjust_for_inflation(df: pd.DataFrame, inflation_df: pd.DataFrame, current_value_date) -> pd.DataFrame:
    """
    Adjusts a DataFrame of monetary values for inflation up to a target date.
    """
    if df is None or df.empty or inflation_df is None or inflation_df.empty:
        return df

    df = df.copy()
    value_col = df.columns[1]  # use the second column as value
    adjusted_col = value_col  # keep the same column name

    # Ensure date column is datetime
    df[df.columns[0]] = pd.to_datetime(df[df.columns[0]])

    df[adjusted_col] = df.apply(
        lambda row: adjust_value(row[value_col], row[df.columns[0]], current_value_date, inflation_df),
        axis=1
    )
    return df

def calculate_investment_metrics(
    contributions_local_df=None,
    contributions_foreign_df=None,
    fees_local_df=None,
    fees_foreign_df=None,
    tax_local_df=None,
    tax_foreign_df=None,
    dividends_local_df=None,
    dividends_foreign_df=None,
    current_value_local=0.0,
    current_value_foreign=0.0,
    current_value_date=None,
    local_inflation_df=None,
    foreign_inflation_df=None
):
    """Calculate comprehensive investment metrics."""
    
    # Ensure current_value_date is datetime
    if current_value_date and not isinstance(current_value_date, datetime):
        current_value_date = pd.to_datetime(current_value_date)

    # --- Inflation-adjusted contributions ---
    if contributions_local_df is not None and local_inflation_df is not None:
        contributions_local_inflation_adjusted_df = adjust_for_inflation(
            contributions_local_df, local_inflation_df, current_value_date
        )
    else:
        contributions_local_inflation_adjusted_df = None
    
    if contributions_foreign_df is not None and foreign_inflation_df is not None:
        contributions_foreign_inflation_adjusted_df = adjust_for_inflation(
            contributions_foreign_df, foreign_inflation_df, current_value_date
        )
    else:
        contributions_foreign_inflation_adjusted_df = None
    
    # --- Inflation-adjusted fees ---
    if fees_local_df is not None and local_inflation_df is not None:
        fees_local_inflation_adjusted_df = adjust_for_inflation(fees_local_df, local_inflation_df, current_value_date)
    else:
        fees_local_inflation_adjusted_df = None
    
    if fees_foreign_df is not None and foreign_inflation_df is not None:
        fees_foreign_inflation_adjusted_df = adjust_for_inflation(fees_foreign_df, foreign_inflation_df, current_value_date)
    else:
        fees_foreign_inflation_adjusted_df = None
    
    # --- Inflation-adjusted tax ---
    if tax_local_df is not None and local_inflation_df is not None:
        tax_local_inflation_adjusted_df = adjust_for_inflation(tax_local_df, local_inflation_df, current_value_date)
    else:
        tax_local_inflation_adjusted_df = None
    
    if tax_foreign_df is not None and foreign_inflation_df is not None:
        tax_foreign_inflation_adjusted_df = adjust_for_inflation(tax_foreign_df, foreign_inflation_df, current_value_date)
    else:
        tax_foreign_inflation_adjusted_df = None
    
    # --- Inflation-adjusted dividends ---
    if dividends_local_df is not None and local_inflation_df is not None:
        dividends_local_inflation_adjusted_df = adjust_for_inflation(dividends_local_df, local_inflation_df, current_value_date)
    else:
        dividends_local_inflation_adjusted_df = None
    
    if dividends_foreign_df is not None and foreign_inflation_df is not None:
        dividends_foreign_inflation_adjusted_df = adjust_for_inflation(dividends_foreign_df, foreign_inflation_df, current_value_date)
    else:
        dividends_foreign_inflation_adjusted_df = None
    
    # --- Current values ---
    current_value_local_df = pd.DataFrame([{"date": current_value_date, "value": current_value_local}])
    current_value_foreign_df = pd.DataFrame([{"date": current_value_date, "value": current_value_foreign}])

    if local_inflation_df is not None:
        current_value_local_inflation_adjusted_df = adjust_for_inflation(
            current_value_local_df, local_inflation_df, current_value_date
        )
        current_value_local_real = current_value_local_inflation_adjusted_df["value"].iloc[0]
    else:
        current_value_local_real = current_value_local

    if foreign_inflation_df is not None:
        current_value_foreign_inflation_adjusted_df = adjust_for_inflation(
            current_value_foreign_df, foreign_inflation_df, current_value_date
        )
        current_value_foreign_real = current_value_foreign_inflation_adjusted_df["value"].iloc[0]
    else:
        current_value_foreign_real = current_value_foreign

    # Totals
    total_contributions_local = contributions_local_df["contributions"].sum() if contributions_local_df is not None else 0.0
    total_contributions_foreign = contributions_foreign_df["contributions"].sum() if contributions_foreign_df is not None else 0.0

    total_fees_local = fees_local_df["fees"].sum() if fees_local_df is not None else 0.0
    total_fees_foreign = fees_foreign_df["fees"].sum() if fees_foreign_df is not None else 0.0

    total_tax_local = tax_local_df["tax"].sum() if tax_local_df is not None else 0.0
    total_tax_foreign = tax_foreign_df["tax"].sum() if tax_foreign_df is not None else 0.0

    total_dividends_local = dividends_local_df["dividends"].sum() if dividends_local_df is not None else 0.0
    total_dividends_foreign = dividends_foreign_df["dividends"].sum() if dividends_foreign_df is not None else 0.0

    # Initialize metrics DataFrame
    investment_metrics_rows = ["local", "local_inflation_adjusted", "foreign", "foreign_inflation_adjusted"]
    investment_metrics_columns = [
        "net growth", "total return", "return multiple", "cagr", "irr",
        "total fee ratio", "total tax ratio", "total cost ratio", "dividend yield",
        "fee ratio annualized", "tax ratio annualized", "cost ratio annualized",
        "dividend yield annualized", "total contributions", "total fees",
        "total tax", "total dividends", "number of contrabutions",
        "average contabutions", "investment period",
    ]

    investment_metrics = pd.DataFrame(0.0, index=investment_metrics_rows, columns=investment_metrics_columns)

    # Fill basic totals
    investment_metrics.loc["local", "total contributions"] = total_contributions_local
    investment_metrics.loc["local", "total fees"] = total_fees_local
    investment_metrics.loc["local", "total tax"] = total_tax_local
    investment_metrics.loc["local", "total dividends"] = total_dividends_local
    
    investment_metrics.loc["foreign", "total contributions"] = total_contributions_foreign
    investment_metrics.loc["foreign", "total fees"] = total_fees_foreign
    investment_metrics.loc["foreign", "total tax"] = total_tax_foreign
    investment_metrics.loc["foreign", "total dividends"] = total_dividends_foreign

    if contributions_local_inflation_adjusted_df is not None:
        investment_metrics.loc["local_inflation_adjusted", "total contributions"] = contributions_local_inflation_adjusted_df["contributions"].sum()
    if fees_local_inflation_adjusted_df is not None:
        investment_metrics.loc["local_inflation_adjusted", "total fees"] = fees_local_inflation_adjusted_df["fees"].sum()
    if tax_local_inflation_adjusted_df is not None:
        investment_metrics.loc["local_inflation_adjusted", "total tax"] = tax_local_inflation_adjusted_df["tax"].sum()
    if dividends_local_inflation_adjusted_df is not None:
        investment_metrics.loc["local_inflation_adjusted", "total dividends"] = dividends_local_inflation_adjusted_df["dividends"].sum()

    if contributions_foreign_inflation_adjusted_df is not None:
        investment_metrics.loc["foreign_inflation_adjusted", "total contributions"] = contributions_foreign_inflation_adjusted_df["contributions"].sum()
    if fees_foreign_inflation_adjusted_df is not None:
        investment_metrics.loc["foreign_inflation_adjusted", "total fees"] = fees_foreign_inflation_adjusted_df["fees"].sum()
    if tax_foreign_inflation_adjusted_df is not None:
        investment_metrics.loc["foreign_inflation_adjusted", "total tax"] = tax_foreign_inflation_adjusted_df["tax"].sum()
    if dividends_foreign_inflation_adjusted_df is not None:
        investment_metrics.loc["foreign_inflation_adjusted", "total dividends"] = dividends_foreign_inflation_adjusted_df["dividends"].sum()

    # Helper to calculate metrics for a row
    def calculate_row_metrics(row_name, contrib_df, fees_df, tax_df, div_df, current_val, total_contrib, total_fees, total_tax, total_div):
        if contrib_df is not None and not contrib_df.empty:
            start_date = contrib_df["date"].iloc[0]
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            
            inv_period = (current_value_date - start_date).days / 365.25
            investment_metrics.loc[row_name, "investment period"] = inv_period
            
            net_growth = current_val - total_contrib
            investment_metrics.loc[row_name, "net growth"] = net_growth
            
            if total_contrib != 0:
                investment_metrics.loc[row_name, "total return"] = net_growth / total_contrib
                investment_metrics.loc[row_name, "return multiple"] = current_val / total_contrib
                
                if inv_period > 0 and current_val > 0:
                    investment_metrics.loc[row_name, "cagr"] = (current_val / total_contrib) ** (1 / inv_period) - 1
            
            # IRR Calculation
            try:
                cf_contrib = contrib_df.rename(columns={"contributions": "amount"}).assign(amount=lambda x: -x["amount"])
                cf_fees = fees_df.rename(columns={"fees": "amount"}).assign(amount=lambda x: -x["amount"]) if fees_df is not None else pd.DataFrame(columns=["date", "amount"])
                cf_tax = tax_df.rename(columns={"tax": "amount"}).assign(amount=lambda x: -x["amount"]) if tax_df is not None else pd.DataFrame(columns=["date", "amount"])
                cf_div = div_df.rename(columns={"dividends": "amount"}) if div_df is not None else pd.DataFrame(columns=["date", "amount"])

                cashflows = pd.concat([cf_contrib, cf_fees, cf_tax, cf_div], ignore_index=True)
                cashflows = pd.concat([
                    cashflows,
                    pd.DataFrame({"date": [current_value_date], "amount": [current_val]})
                ], ignore_index=True)

                investment_metrics.loc[row_name, "irr"] = float(xirr(cashflows["date"], cashflows["amount"]))
            except:
                investment_metrics.loc[row_name, "irr"] = 0.0

            # Ratios
            if current_val != 0:
                investment_metrics.loc[row_name, "total fee ratio"] = total_fees / current_val
                investment_metrics.loc[row_name, "total tax ratio"] = total_tax / current_val
                investment_metrics.loc[row_name, "total cost ratio"] = (total_fees + total_tax) / current_val
                investment_metrics.loc[row_name, "dividend yield"] = total_div / current_val

            # Annualized Ratios
            if inv_period > 0:
                investment_metrics.loc[row_name, "fee ratio annualized"] = 1 - (1 - investment_metrics.loc[row_name, "total fee ratio"]) ** (1 / inv_period)
                investment_metrics.loc[row_name, "tax ratio annualized"] = 1 - (1 - investment_metrics.loc[row_name, "total tax ratio"]) ** (1 / inv_period)
                investment_metrics.loc[row_name, "cost ratio annualized"] = 1 - (1 - investment_metrics.loc[row_name, "total cost ratio"]) ** (1 / inv_period)
                investment_metrics.loc[row_name, "dividend yield annualized"] = (1 + investment_metrics.loc[row_name, "dividend yield"]) ** (1 / inv_period) - 1

            # Counts
            count = contrib_df["contributions"].count()
            investment_metrics.loc[row_name, "number of contrabutions"] = count
            if count > 0:
                investment_metrics.loc[row_name, "average contabutions"] = total_contrib / count

    # Calculate for each scenario
    calculate_row_metrics("local", contributions_local_df, fees_local_df, tax_local_df, dividends_local_df, 
                         current_value_local, total_contributions_local, total_fees_local, total_tax_local, total_dividends_local)
    
    calculate_row_metrics("local_inflation_adjusted", contributions_local_inflation_adjusted_df, fees_local_inflation_adjusted_df, 
                         tax_local_inflation_adjusted_df, dividends_local_inflation_adjusted_df, 
                         current_value_local_real, 
                         investment_metrics.loc["local_inflation_adjusted", "total contributions"],
                         investment_metrics.loc["local_inflation_adjusted", "total fees"],
                         investment_metrics.loc["local_inflation_adjusted", "total tax"],
                         investment_metrics.loc["local_inflation_adjusted", "total dividends"])

    calculate_row_metrics("foreign", contributions_foreign_df, fees_foreign_df, tax_foreign_df, dividends_foreign_df, 
                         current_value_foreign, total_contributions_foreign, total_fees_foreign, total_tax_foreign, total_dividends_foreign)

    calculate_row_metrics("foreign_inflation_adjusted", contributions_foreign_inflation_adjusted_df, fees_foreign_inflation_adjusted_df, 
                         tax_foreign_inflation_adjusted_df, dividends_foreign_inflation_adjusted_df, 
                         current_value_foreign_real, 
                         investment_metrics.loc["foreign_inflation_adjusted", "total contributions"],
                         investment_metrics.loc["foreign_inflation_adjusted", "total fees"],
                         investment_metrics.loc["foreign_inflation_adjusted", "total tax"],
                         investment_metrics.loc["foreign_inflation_adjusted", "total dividends"])

    return investment_metrics

def update_investment_metrics(investment_id: int, database_name: str = DEFAULT_DB) -> None:
    """
    Calculate and update investment metrics for a specific investment.
    """
    print(f"Updating metrics for investment {investment_id}...")
    try:
        with get_db_connection(database_name) as (conn, cursor):
            # 1. Get investment details
            cursor.execute("SELECT investment_ticker, unit_currency, number_of_units_held, unit_price FROM investments WHERE id = %s", (investment_id,))
            res = cursor.fetchone()
            if not res:
                print(f"Investment ID {investment_id} not found.")
                return
            ticker, currency, units_held, unit_price = res
            
            current_value = unit_price * units_held
            current_date = date.today()
            
            # Get latest price date
            cursor.execute("SELECT MAX(unit_price_date) FROM unit_prices WHERE investment_id = %s", (investment_id,))
            latest_date_row = cursor.fetchone()
            if latest_date_row and latest_date_row[0]:
                current_date = latest_date_row[0]

            # 2. Get contributions
            query_contrib = "SELECT transaction_date as date, transaction_amount as contributions FROM transactions WHERE investment_id = %s AND LOWER(transaction_type) = 'buy'"
            contributions_df = pd.read_sql(query_contrib, conn, params=(investment_id,))
            
            if contributions_df.empty:
                # Fallback to initial investment if no transactions recorded
                cursor.execute("SELECT initial_investment_date, initial_unit_price, number_of_units_held FROM investments WHERE id = %s", (investment_id,))
                init_res = cursor.fetchone()
                if init_res and init_res[0] and init_res[1] is not None and init_res[2] is not None:
                    init_date, init_price, init_units = init_res
                    contributions_df = pd.DataFrame([{
                        'date': init_date,
                        'contributions': float(init_price) * float(init_units)
                    }])
            
            if not contributions_df.empty:
                contributions_df['date'] = pd.to_datetime(contributions_df['date'])

            # 3. Get fees
            query_fees = "SELECT fee_date as date, fee_paid as fees FROM fees WHERE investment_id = %s"
            fees_df = pd.read_sql(query_fees, conn, params=(investment_id,))
            if not fees_df.empty:
                fees_df['date'] = pd.to_datetime(fees_df['date'])
            
            # 4. Get tax
            query_tax = "SELECT tax_date as date, tax_paid as tax FROM tax WHERE investment_id = %s"
            tax_df = pd.read_sql(query_tax, conn, params=(investment_id,))
            if not tax_df.empty:
                tax_df['date'] = pd.to_datetime(tax_df['date'])
            
            # 5. Get dividends
            query_div = "SELECT dividend_date as date, dividend_recieved as dividends FROM dividends WHERE investment_id = %s"
            dividends_df = pd.read_sql(query_div, conn, params=(investment_id,))
            if not dividends_df.empty:
                dividends_df['date'] = pd.to_datetime(dividends_df['date'])
            
            # 6. Inflation
            currency_country_map = CURRENCY_COUNTRY_MAP
            country = currency_country_map.get(currency, 'South Africa')
            
            query_inf = "SELECT inflation_date as date, inflation_rate FROM inflation WHERE country = %s ORDER BY date"
            inflation_df = pd.read_sql(query_inf, conn, params=(country,))
            if not inflation_df.empty:
                inflation_df['date'] = pd.to_datetime(inflation_df['date'])
                inflation_df['year'] = inflation_df['date'].dt.year
                inflation_df['date'] = inflation_df['date'].dt.date
            
            is_local = (currency == 'ZAR' or currency == 'R')
            from .currency import convert_currency_amount
            
            # Convert current_date to datetime for adjust_for_inflation
            current_date_dt = pd.to_datetime(current_date)
            current_date_str = current_date.strftime('%Y-%m-%d') if hasattr(current_date, 'strftime') else str(current_date)
            
            args = {
                'current_value_date': current_date_dt,
            }
            
            if is_local:
                args['contributions_local_df'] = contributions_df
                args['fees_local_df'] = fees_df
                args['tax_local_df'] = tax_df
                args['dividends_local_df'] = dividends_df
                args['current_value_local'] = current_value
                args['local_inflation_df'] = inflation_df
            else:
                # Foreign investment: populate foreign and local (converted)
                args['contributions_foreign_df'] = contributions_df
                args['fees_foreign_df'] = fees_df
                args['tax_foreign_df'] = tax_df
                args['dividends_foreign_df'] = dividends_df
                args['current_value_foreign'] = current_value
                args['foreign_inflation_df'] = inflation_df
                
                # Convert to local (ZAR) for portfolio-wide aggregation
                rate_cache = {}
                def convert_df(df, val_col):
                    if df is None or df.empty: return None
                    new_df = df.copy()
                    converted_vals = []
                    for _, row in df.iterrows():
                        d_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                        val = convert_currency_amount(row[val_col], currency, 'ZAR', d_str, database_name, cursor, rate_cache)
                        converted_vals.append(val)
                    new_df[val_col] = converted_vals
                    return new_df
                
                args['contributions_local_df'] = convert_df(contributions_df, 'contributions')
                args['fees_local_df'] = convert_df(fees_df, 'fees')
                args['tax_local_df'] = convert_df(tax_df, 'tax')
                args['dividends_local_df'] = convert_df(dividends_df, 'dividends')
                args['current_value_local'] = convert_currency_amount(current_value, currency, 'ZAR', current_date_str, database_name, cursor, rate_cache)
                
                # Also need local inflation for the local part
                query_local_inf = "SELECT inflation_date as date, inflation_rate FROM inflation WHERE country = 'South Africa' ORDER BY date"
                local_inflation_df = pd.read_sql(query_local_inf, conn)
                if not local_inflation_df.empty:
                    local_inflation_df['date'] = pd.to_datetime(local_inflation_df['date'])
                    local_inflation_df['year'] = local_inflation_df['date'].dt.year
                    local_inflation_df['date'] = local_inflation_df['date'].dt.date
                args['local_inflation_df'] = local_inflation_df
                
            metrics = calculate_investment_metrics(**args)
            
            def get_m(row, col):
                try:
                    val = metrics.loc[row, col]
                    return float(val) if not pd.isna(val) else None
                except KeyError:
                    return None

            # Insert or Update
            insert_query = """
                INSERT INTO investment_metrics (
                    investment_id, metrics_date,
                    local_net_growth, local_total_return, local_return_multiple, local_cagr, local_irr,
                    local_total_fee_ratio, local_total_tax_ratio, local_total_cost_ratio, local_dividend_yield,
                    local_fee_ratio_annualized, local_tax_ratio_annualized, local_cost_ratio_annualized, local_dividend_yield_annualized,
                    local_total_contributions, local_total_fees, local_total_tax, local_total_dividends,
                    local_number_of_contributions, local_average_contributions, local_investment_period,

                    local_real_net_growth, local_real_total_return, local_real_return_multiple, local_real_cagr, local_real_irr,
                    local_real_total_fee_ratio, local_real_total_tax_ratio, local_real_total_cost_ratio, local_real_dividend_yield,
                    local_real_fee_ratio_annualized, local_real_tax_ratio_annualized, local_real_cost_ratio_annualized, local_real_dividend_yield_annualized,
                    local_real_total_contributions, local_real_total_fees, local_real_total_tax, local_real_total_dividends,
                    local_real_number_of_contributions, local_real_average_contributions, local_real_investment_period,

                    foreign_net_growth, foreign_total_return, foreign_return_multiple, foreign_cagr, foreign_irr,
                    foreign_total_fee_ratio, foreign_total_tax_ratio, foreign_total_cost_ratio, foreign_dividend_yield,
                    foreign_fee_ratio_annualized, foreign_tax_ratio_annualized, foreign_cost_ratio_annualized, foreign_dividend_yield_annualized,
                    foreign_total_contributions, foreign_total_fees, foreign_total_tax, foreign_total_dividends,
                    foreign_number_of_contributions, foreign_average_contributions, foreign_investment_period,

                    foreign_real_net_growth, foreign_real_total_return, foreign_real_return_multiple, foreign_real_cagr, foreign_real_irr,
                    foreign_real_total_fee_ratio, foreign_real_total_tax_ratio, foreign_real_total_cost_ratio, foreign_real_dividend_yield,
                    foreign_real_fee_ratio_annualized, foreign_real_tax_ratio_annualized, foreign_real_cost_ratio_annualized, foreign_real_dividend_yield_annualized,
                    foreign_real_total_contributions, foreign_real_total_fees, foreign_real_total_tax, foreign_real_total_dividends,
                    foreign_real_number_of_contributions, foreign_real_average_contributions, foreign_real_investment_period
                ) VALUES (
                    %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (investment_id, metrics_date) DO UPDATE SET
                    local_net_growth = EXCLUDED.local_net_growth,
                    local_total_return = EXCLUDED.local_total_return,
                    local_return_multiple = EXCLUDED.local_return_multiple,
                    local_cagr = EXCLUDED.local_cagr,
                    local_irr = EXCLUDED.local_irr,
                    local_total_fee_ratio = EXCLUDED.local_total_fee_ratio,
                    local_total_tax_ratio = EXCLUDED.local_total_tax_ratio,
                    local_total_cost_ratio = EXCLUDED.local_total_cost_ratio,
                    local_dividend_yield = EXCLUDED.local_dividend_yield,
                    local_fee_ratio_annualized = EXCLUDED.local_fee_ratio_annualized,
                    local_tax_ratio_annualized = EXCLUDED.local_tax_ratio_annualized,
                    local_cost_ratio_annualized = EXCLUDED.local_cost_ratio_annualized,
                    local_dividend_yield_annualized = EXCLUDED.local_dividend_yield_annualized,
                    local_total_contributions = EXCLUDED.local_total_contributions,
                    local_total_fees = EXCLUDED.local_total_fees,
                    local_total_tax = EXCLUDED.local_total_tax,
                    local_total_dividends = EXCLUDED.local_total_dividends,
                    local_number_of_contributions = EXCLUDED.local_number_of_contributions,
                    local_average_contributions = EXCLUDED.local_average_contributions,
                    local_investment_period = EXCLUDED.local_investment_period,

                    local_real_net_growth = EXCLUDED.local_real_net_growth,
                    local_real_total_return = EXCLUDED.local_real_total_return,
                    local_real_return_multiple = EXCLUDED.local_real_return_multiple,
                    local_real_cagr = EXCLUDED.local_real_cagr,
                    local_real_irr = EXCLUDED.local_real_irr,
                    local_real_total_fee_ratio = EXCLUDED.local_real_total_fee_ratio,
                    local_real_total_tax_ratio = EXCLUDED.local_real_total_tax_ratio,
                    local_real_total_cost_ratio = EXCLUDED.local_real_total_cost_ratio,
                    local_real_dividend_yield = EXCLUDED.local_real_dividend_yield,
                    local_real_fee_ratio_annualized = EXCLUDED.local_real_fee_ratio_annualized,
                    local_real_tax_ratio_annualized = EXCLUDED.local_real_tax_ratio_annualized,
                    local_real_cost_ratio_annualized = EXCLUDED.local_real_cost_ratio_annualized,
                    local_real_dividend_yield_annualized = EXCLUDED.local_real_dividend_yield_annualized,
                    local_real_total_contributions = EXCLUDED.local_real_total_contributions,
                    local_real_total_fees = EXCLUDED.local_real_total_fees,
                    local_real_total_tax = EXCLUDED.local_real_total_tax,
                    local_real_total_dividends = EXCLUDED.local_real_total_dividends,
                    local_real_number_of_contributions = EXCLUDED.local_real_number_of_contributions,
                    local_real_average_contributions = EXCLUDED.local_real_average_contributions,
                    local_real_investment_period = EXCLUDED.local_real_investment_period,

                    foreign_net_growth = EXCLUDED.foreign_net_growth,
                    foreign_total_return = EXCLUDED.foreign_total_return,
                    foreign_return_multiple = EXCLUDED.foreign_return_multiple,
                    foreign_cagr = EXCLUDED.foreign_cagr,
                    foreign_irr = EXCLUDED.foreign_irr,
                    foreign_total_fee_ratio = EXCLUDED.foreign_total_fee_ratio,
                    foreign_total_tax_ratio = EXCLUDED.foreign_total_tax_ratio,
                    foreign_total_cost_ratio = EXCLUDED.foreign_total_cost_ratio,
                    foreign_dividend_yield = EXCLUDED.foreign_dividend_yield,
                    foreign_fee_ratio_annualized = EXCLUDED.foreign_fee_ratio_annualized,
                    foreign_tax_ratio_annualized = EXCLUDED.foreign_tax_ratio_annualized,
                    foreign_cost_ratio_annualized = EXCLUDED.foreign_cost_ratio_annualized,
                    foreign_dividend_yield_annualized = EXCLUDED.foreign_dividend_yield_annualized,
                    foreign_total_contributions = EXCLUDED.foreign_total_contributions,
                    foreign_total_fees = EXCLUDED.foreign_total_fees,
                    foreign_total_tax = EXCLUDED.foreign_total_tax,
                    foreign_total_dividends = EXCLUDED.foreign_total_dividends,
                    foreign_number_of_contributions = EXCLUDED.foreign_number_of_contributions,
                    foreign_average_contributions = EXCLUDED.foreign_average_contributions,
                    foreign_investment_period = EXCLUDED.foreign_investment_period,

                    foreign_real_net_growth = EXCLUDED.foreign_real_net_growth,
                    foreign_real_total_return = EXCLUDED.foreign_real_total_return,
                    foreign_real_return_multiple = EXCLUDED.foreign_real_return_multiple,
                    foreign_real_cagr = EXCLUDED.foreign_real_cagr,
                    foreign_real_irr = EXCLUDED.foreign_real_irr,
                    foreign_real_total_fee_ratio = EXCLUDED.foreign_real_total_fee_ratio,
                    foreign_real_total_tax_ratio = EXCLUDED.foreign_real_total_tax_ratio,
                    foreign_real_total_cost_ratio = EXCLUDED.foreign_real_total_cost_ratio,
                    foreign_real_dividend_yield = EXCLUDED.foreign_real_dividend_yield,
                    foreign_real_fee_ratio_annualized = EXCLUDED.foreign_real_fee_ratio_annualized,
                    foreign_real_tax_ratio_annualized = EXCLUDED.foreign_real_tax_ratio_annualized,
                    foreign_real_cost_ratio_annualized = EXCLUDED.foreign_real_cost_ratio_annualized,
                    foreign_real_dividend_yield_annualized = EXCLUDED.foreign_real_dividend_yield_annualized,
                    foreign_real_total_contributions = EXCLUDED.foreign_real_total_contributions,
                    foreign_real_total_fees = EXCLUDED.foreign_real_total_fees,
                    foreign_real_total_tax = EXCLUDED.foreign_real_total_tax,
                    foreign_real_total_dividends = EXCLUDED.foreign_real_total_dividends,
                    foreign_real_number_of_contributions = EXCLUDED.foreign_real_number_of_contributions,
                    foreign_real_average_contributions = EXCLUDED.foreign_real_average_contributions,
                    foreign_real_investment_period = EXCLUDED.foreign_real_investment_period
            """
            
            params = (
                investment_id, current_date,
                get_m("local", "net growth"), get_m("local", "total return"), get_m("local", "return multiple"), get_m("local", "cagr"), get_m("local", "irr"),
                get_m("local", "total fee ratio"), get_m("local", "total tax ratio"), get_m("local", "total cost ratio"), get_m("local", "dividend yield"),
                get_m("local", "fee ratio annualized"), get_m("local", "tax ratio annualized"), get_m("local", "cost ratio annualized"), get_m("local", "dividend yield annualized"),
                get_m("local", "total contributions"), get_m("local", "total fees"), get_m("local", "total tax"), get_m("local", "total dividends"),
                get_m("local", "number of contrabutions"), get_m("local", "average contabutions"), get_m("local", "investment period"),

                get_m("local_inflation_adjusted", "net growth"), get_m("local_inflation_adjusted", "total return"), get_m("local_inflation_adjusted", "return multiple"), get_m("local_inflation_adjusted", "cagr"), get_m("local_inflation_adjusted", "irr"),
                get_m("local_inflation_adjusted", "total fee ratio"), get_m("local_inflation_adjusted", "total tax ratio"), get_m("local_inflation_adjusted", "total cost ratio"), get_m("local_inflation_adjusted", "dividend yield"),
                get_m("local_inflation_adjusted", "fee ratio annualized"), get_m("local_inflation_adjusted", "tax ratio annualized"), get_m("local_inflation_adjusted", "cost ratio annualized"), get_m("local_inflation_adjusted", "dividend yield annualized"),
                get_m("local_inflation_adjusted", "total contributions"), get_m("local_inflation_adjusted", "total fees"), get_m("local_inflation_adjusted", "total tax"), get_m("local_inflation_adjusted", "total dividends"),
                get_m("local_inflation_adjusted", "number of contrabutions"), get_m("local_inflation_adjusted", "average contabutions"), get_m("local_inflation_adjusted", "investment period"),

                get_m("foreign", "net growth"), get_m("foreign", "total return"), get_m("foreign", "return multiple"), get_m("foreign", "cagr"), get_m("foreign", "irr"),
                get_m("foreign", "total fee ratio"), get_m("foreign", "total tax ratio"), get_m("foreign", "total cost ratio"), get_m("foreign", "dividend yield"),
                get_m("foreign", "fee ratio annualized"), get_m("foreign", "tax ratio annualized"), get_m("foreign", "cost ratio annualized"), get_m("foreign", "dividend yield annualized"),
                get_m("foreign", "total contributions"), get_m("foreign", "total fees"), get_m("foreign", "total tax"), get_m("foreign", "total dividends"),
                get_m("foreign", "number of contrabutions"), get_m("foreign", "average contabutions"), get_m("foreign", "investment period"),

                get_m("foreign_inflation_adjusted", "net growth"), get_m("foreign_inflation_adjusted", "total return"), get_m("foreign_inflation_adjusted", "return multiple"), get_m("foreign_inflation_adjusted", "cagr"), get_m("foreign_inflation_adjusted", "irr"),
                get_m("foreign_inflation_adjusted", "total fee ratio"), get_m("foreign_inflation_adjusted", "total tax ratio"), get_m("foreign_inflation_adjusted", "total cost ratio"), get_m("foreign_inflation_adjusted", "dividend yield"),
                get_m("foreign_inflation_adjusted", "fee ratio annualized"), get_m("foreign_inflation_adjusted", "tax ratio annualized"), get_m("foreign_inflation_adjusted", "cost ratio annualized"), get_m("foreign_inflation_adjusted", "dividend yield annualized"),
                get_m("foreign_inflation_adjusted", "total contributions"), get_m("foreign_inflation_adjusted", "total fees"), get_m("foreign_inflation_adjusted", "total tax"), get_m("foreign_inflation_adjusted", "total dividends"),
                get_m("foreign_inflation_adjusted", "number of contrabutions"), get_m("foreign_inflation_adjusted", "average contabutions"), get_m("foreign_inflation_adjusted", "investment period")
            )
            
            cursor.execute(insert_query, params)
            conn.commit()
            print(f"Successfully updated metrics for investment {investment_id}")

    except Exception as e:
        print(f"Error updating investment metrics: {e}")
        import traceback
        traceback.print_exc()

def get_investment_metrics_by_name_data(database_name: str, investment_name: str) -> dict:
    """
    Get metrics for a specific investment by name.

    Returns the same rich time-series structure as get_investment_metrics_data
    so the frontend can render charts for an individual investment.
    """
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("SELECT id FROM investments WHERE investment_name = %s", (investment_name,))
        res = cursor.fetchone()
        if not res:
            return {}
        investment_id = res[0]

        cursor.execute("""
            SELECT * FROM investment_metrics
            WHERE investment_id = %s
            ORDER BY metrics_date ASC
        """, (investment_id,))
        rows = cursor.fetchall()
        if not rows:
            return {
                "portfolio_performance_return": [],
                "rolling_returns": {"one_year": [], "three_year": [], "five_year": []},
                "risk_metrics": {"volatility": [], "sharpe_ratio": [], "max_drawdown": []},
                "contribution_vs_growth": [],
                "drawdown_analysis": [],
                "dividend_yield": [],
                "fee_analysis": [],
                "tax_analysis": [],
                "cagr_trend": [],
                "irr_trend": [],
                "conclusion": f"No metrics data available yet for '{investment_name}'.",
                "filter_type": "individual",
                "investment_name": investment_name,
                "data_source": "database",
                "data_points": 0,
                "generated_at": datetime.now().isoformat(),
                "key_metrics": {},
            }

        colnames = [desc[0] for desc in cursor.description]

    # Build time-series structures matching the portfolio metrics endpoint
    cagr_trend = []
    irr_trend = []
    contribution_vs_growth = []
    rolling_returns = {"one_year": [], "three_year": [], "five_year": []}
    fee_analysis = []
    tax_analysis = []
    dividend_yield = []
    volatility = []

    # The DB stores columns with local_/foreign_ (and _real) prefixes, while the
    # metrics DataFrame used unprefixed logical names. Normalise each row so the
    # rest of the code can read plain names like "cagr", "total_contributions".
    def _normalise(record: dict) -> dict:
        out = {}
        for k, v in record.items():
            base = k
            for p in ("local_real_", "foreign_real_", "local_", "foreign_"):
                if k.startswith(p):
                    base = k[len(p):]
                    break
            out.setdefault(base, v)
        # total_current_value is not stored; derive from contributions + net growth
        if ("total_current_value" not in out
                and out.get("total_contributions") is not None
                and out.get("net_growth") is not None):
            out["total_current_value"] = out["total_contributions"] + out["net_growth"]
        return out

    for row in rows:
        record = _normalise(dict(zip(colnames, row)))
        period = record.get("metrics_date")
        if period is None:
            continue
        period_str = period.strftime("%Y-%m") if hasattr(period, "strftime") else str(period)

        cagr = record.get("cagr")
        irr = record.get("irr")
        cagr_trend.append({"period": period_str, "value": round(float(cagr) * 100, 2) if cagr is not None else 0})
        irr_trend.append({"period": period_str, "value": round(float(irr) * 100, 2) if irr is not None else 0})

        total_contributions = record.get("total_contributions") or 0
        total_current_value = record.get("total_current_value") or 0
        total_return = record.get("total_return") or 0
        contribution_vs_growth.append({
            "period": period_str,
            "contributions": round(float(total_contributions), 2),
            "growth": round(float(total_return) * float(total_contributions), 2),
            "value": round(float(total_current_value), 2),
        })

        yield_val = record.get("dividend_yield")
        fee_ratio = record.get("fee_ratio_annualized")
        tax_ratio = record.get("tax_ratio_annualized")
        if fee_ratio is not None:
            fee_analysis.append({"period": period_str, "value": round(float(fee_ratio) * 100, 2)})
        if tax_ratio is not None:
            tax_analysis.append({"period": period_str, "value": round(float(tax_ratio) * 100, 2)})
        if yield_val is not None:
            dividend_yield.append({"period": period_str, "value": round(float(yield_val) * 100, 2)})

    # Latest values for key metrics
    latest = _normalise(dict(zip(colnames, rows[-1])))
    latest_contrib = float(latest.get("total_contributions") or 0)
    latest_value = float(latest.get("total_current_value") or 0)
    latest_return = float(latest.get("total_return") or 0)  # ratio, e.g. 0.36 = 36%
    key_metrics = {
        "total_contributions": round(latest_contrib, 2),
        "total_current_value": round(latest_value, 2),
        "total_return": round(latest_return * latest_contrib, 2),
        "total_return_pct": round(latest_return * 100, 2),
        "cagr": round(float(latest.get("cagr") or 0) * 100, 2),
        "irr": round(float(latest.get("irr") or 0) * 100, 2),
    }

    return {
        "portfolio_performance_return": cagr_trend,
        "rolling_returns": rolling_returns,
        "risk_metrics": {"volatility": volatility, "sharpe_ratio": [], "max_drawdown": []},
        "contribution_vs_growth": contribution_vs_growth,
        "drawdown_analysis": [],
        "dividend_yield": dividend_yield,
        "fee_analysis": fee_analysis,
        "tax_analysis": tax_analysis,
        "cagr_trend": cagr_trend,
        "irr_trend": irr_trend,
        "benchmarks": {"portfolio": [], "benchmark": []},
        "key_metrics": key_metrics,
        "conclusion": f"Metrics for {investment_name}: {len(rows)} data points.",
        "filter_type": "individual",
        "investment_name": investment_name,
        "data_source": "database",
        "data_points": len(rows),
        "generated_at": datetime.now().isoformat(),
        "base_currency": "ZAR",
    }

def recalculate_investment_metrics_history(database_name: str = DEFAULT_DB) -> None:
    """
    Recalculate investment metrics for all investments in the database.
    Update the investment_metrics table with current data.
    """
    print(f"Recalculating investment metrics history for database: {database_name}")

    with get_db_connection(database_name) as (conn, cursor):
        # Get all investment IDs
        cursor.execute("SELECT id FROM investments ORDER BY id")
        investment_ids = [row[0] for row in cursor.fetchall()]

    print(f"Found {len(investment_ids)} investments to process")

    for i, investment_id in enumerate(investment_ids):
        print(f"Processing investment {investment_id} ({i+1}/{len(investment_ids)})")
        update_investment_metrics(investment_id, database_name)

    print("Aggregating portfolio metrics...")
    try:
        from .portfolio_metrics import calculate_and_store_portfolio_metrics
        calculate_and_store_portfolio_metrics(database_name)
    except Exception as e:
        print(f"Error aggregating portfolio metrics: {e}")

    print("Completed recalculating investment metrics history")

def calculate_portfolio_irr(database_name: str, base_currency: str = "ZAR") -> dict:
    """
    Calculate Internal Rate of Return (IRR) across multiple dimensions:
      - per_asset:        IRR for each individual investment
      - by_sector:        IRR aggregated by investment_type (sector)
      - by_institution:   IRR aggregated by institution_name
      - whole_portfolio:  IRR for all investments combined
      - portfolio_ex_ra:  IRR for all investments excluding Retirement Annuities
        (any investment_type containing 'RA', 'retirement', or 'annuity', case-insensitive)

    Returns a dict with the following structure:
    {
        "per_asset": [{"investment_name": ..., "institution": ..., "type": ..., "irr": ..., "irr_pct": ...}, ...],
        "by_sector": [{"sector": ..., "irr": ..., "irr_pct": ...}, ...],
        "by_institution": [{"institution": ..., "irr": ..., "irr_pct": ...}, ...],
        "whole_portfolio": {"irr": ..., "irr_pct": ...},
        "portfolio_ex_ra": {"irr": ..., "irr_pct": ...},
        "base_currency": ...,
        "generated_at": ...,
        "ra_types_excluded": [...],
    }
    """
    import re
    from .currency import get_exchange_rate

    # Helper: detect if an investment_type is a retirement annuity
    RA_PATTERN = re.compile(r'(retirement|annuity|\bRA\b)', re.IGNORECASE)

    def is_ra_type(inv_type: str) -> bool:
        return bool(RA_PATTERN.search(str(inv_type)))

    def _build_cashflows(conn, cursor, investment_ids: list, base_currency: str) -> tuple:
        """
        Gather all dated cash flows (contributions negative, dividends positive,
        current_value positive) for a list of investment_ids.
        Returns (dates_list, amounts_list, current_value_date).
        """
        if not investment_ids:
            return [], [], None

        ids_placeholder = ','.join(['%s'] * len(investment_ids))

        # Contributions (Buy transactions) - negative cash flow
        cursor.execute(
            f"""SELECT t.transaction_date, t.transaction_amount, i.unit_currency
                FROM transactions t
                JOIN investments i ON t.investment_id = i.id
                WHERE t.investment_id IN ({ids_placeholder})
                  AND LOWER(t.transaction_type) = 'buy'
                ORDER BY t.transaction_date""",
            investment_ids
        )
        contributions = cursor.fetchall()

        # Fees - negative cash flow
        cursor.execute(
            f"""SELECT f.fee_date, f.fee_paid, i.unit_currency
                FROM fees f
                JOIN investments i ON f.investment_id = i.id
                WHERE f.investment_id IN ({ids_placeholder})
                ORDER BY f.fee_date""",
            investment_ids
        )
        fees = cursor.fetchall()

        # Tax - negative cash flow
        cursor.execute(
            f"""SELECT tx.tax_date, tx.tax_paid, i.unit_currency
                FROM tax tx
                JOIN investments i ON tx.investment_id = i.id
                WHERE tx.investment_id IN ({ids_placeholder})
                ORDER BY tx.tax_date""",
            investment_ids
        )
        taxes = cursor.fetchall()

        # Dividends - positive cash flow
        cursor.execute(
            f"""SELECT d.dividend_date, d.dividend_recieved, i.unit_currency
                FROM dividends d
                JOIN investments i ON d.investment_id = i.id
                WHERE d.investment_id IN ({ids_placeholder})
                ORDER BY d.dividend_date""",
            investment_ids
        )
        dividends = cursor.fetchall()

        # Current values (latest unit price × units held)
        cursor.execute(
            f"""SELECT i.id, i.unit_price, i.number_of_units_held, i.unit_currency,
                       COALESCE(
                           (SELECT MAX(up.unit_price_date) FROM unit_prices up WHERE up.investment_id = i.id),
                           CURRENT_DATE
                       ) AS value_date
                FROM investments i
                WHERE i.id IN ({ids_placeholder})""",
            investment_ids
        )
        current_values = cursor.fetchall()

        dates = []
        amounts = []

        def _convert(amount, currency):
            if currency and currency.upper() != base_currency.upper():
                rate = get_exchange_rate(currency, base_currency, database_name=database_name)
                return amount * rate
            return float(amount)

        for row in contributions:
            d, amt, curr = row
            if d and amt:
                dates.append(pd.to_datetime(d))
                amounts.append(-_convert(float(amt), curr))

        for row in fees:
            d, amt, curr = row
            if d and amt:
                dates.append(pd.to_datetime(d))
                amounts.append(-_convert(float(amt), curr))

        for row in taxes:
            d, amt, curr = row
            if d and amt:
                dates.append(pd.to_datetime(d))
                amounts.append(-_convert(float(amt), curr))

        for row in dividends:
            d, amt, curr = row
            if d and amt:
                dates.append(pd.to_datetime(d))
                amounts.append(_convert(float(amt), curr))

        # Determine most recent value date across all investments
        value_date = None
        for row in current_values:
            inv_id, price, units, curr, vdate = row
            if vdate:
                vdate_dt = pd.to_datetime(vdate)
                if value_date is None or vdate_dt > value_date:
                    value_date = vdate_dt
            if price and units:
                val = _convert(float(price) * float(units), curr)
                vd = pd.to_datetime(vdate) if vdate else pd.Timestamp.now()
                dates.append(vd)
                amounts.append(val)

        return dates, amounts, value_date

    def _safe_irr(dates, amounts):
        if len(dates) < 2:
            return None
        # Ensure at least one negative and one positive cash flow
        neg = any(a < 0 for a in amounts)
        pos = any(a > 0 for a in amounts)
        if not (neg and pos):
            return None
        try:
            return float(xirr(dates, amounts))
        except Exception:
            return None

    try:
        with get_db_connection(database_name) as (conn, cursor):
            # Fetch all investments
            cursor.execute("""
                SELECT id, investment_name, institution_name, investment_type, unit_currency
                FROM investments ORDER BY investment_name
            """)
            investments = cursor.fetchall()

        if not investments:
            return {
                "per_asset": [],
                "by_sector": [],
                "by_institution": [],
                "whole_portfolio": {"irr": None, "irr_pct": None},
                "portfolio_ex_ra": {"irr": None, "irr_pct": None},
                "base_currency": base_currency,
                "generated_at": datetime.now().isoformat(),
                "ra_types_excluded": [],
            }

        # Identify RA types for reporting
        all_types = list(set(inv[3] for inv in investments))
        ra_types = [t for t in all_types if is_ra_type(t)]

        # ---- Per asset IRR ----
        per_asset = []
        with get_db_connection(database_name) as (conn, cursor):
            for inv in investments:
                inv_id, inv_name, institution, inv_type, currency = inv
                dates, amounts, _ = _build_cashflows(conn, cursor, [inv_id], base_currency)
                irr_val = _safe_irr(dates, amounts)
                per_asset.append({
                    "investment_name": inv_name,
                    "institution": institution,
                    "type": inv_type,
                    "currency": currency,
                    "irr": irr_val,
                    "irr_pct": round(irr_val * 100, 4) if irr_val is not None else None,
                })

        # ---- By sector (investment_type) ----
        sector_map: dict[str, list] = {}
        for inv in investments:
            inv_id, _, _, inv_type, _ = inv
            sector_map.setdefault(inv_type, []).append(inv_id)

        by_sector = []
        with get_db_connection(database_name) as (conn, cursor):
            for sector, ids in sector_map.items():
                dates, amounts, _ = _build_cashflows(conn, cursor, ids, base_currency)
                irr_val = _safe_irr(dates, amounts)
                by_sector.append({
                    "sector": sector,
                    "investment_count": len(ids),
                    "irr": irr_val,
                    "irr_pct": round(irr_val * 100, 4) if irr_val is not None else None,
                })

        # ---- By institution ----
        institution_map: dict[str, list] = {}
        for inv in investments:
            inv_id, _, institution, _, _ = inv
            institution_map.setdefault(institution, []).append(inv_id)

        by_institution = []
        with get_db_connection(database_name) as (conn, cursor):
            for inst, ids in institution_map.items():
                dates, amounts, _ = _build_cashflows(conn, cursor, ids, base_currency)
                irr_val = _safe_irr(dates, amounts)
                by_institution.append({
                    "institution": inst,
                    "investment_count": len(ids),
                    "irr": irr_val,
                    "irr_pct": round(irr_val * 100, 4) if irr_val is not None else None,
                })

        # ---- Whole portfolio ----
        all_ids = [inv[0] for inv in investments]
        with get_db_connection(database_name) as (conn, cursor):
            dates, amounts, _ = _build_cashflows(conn, cursor, all_ids, base_currency)
        whole_irr = _safe_irr(dates, amounts)
        whole_portfolio = {
            "irr": whole_irr,
            "irr_pct": round(whole_irr * 100, 4) if whole_irr is not None else None,
        }

        # ---- Portfolio ex RA ----
        ex_ra_ids = [inv[0] for inv in investments if not is_ra_type(inv[3])]
        if ex_ra_ids:
            with get_db_connection(database_name) as (conn, cursor):
                dates, amounts, _ = _build_cashflows(conn, cursor, ex_ra_ids, base_currency)
            ex_ra_irr = _safe_irr(dates, amounts)
        else:
            ex_ra_irr = None

        portfolio_ex_ra = {
            "irr": ex_ra_irr,
            "irr_pct": round(ex_ra_irr * 100, 4) if ex_ra_irr is not None else None,
            "excluded_count": len(all_ids) - len(ex_ra_ids),
        }

        return {
            "per_asset": per_asset,
            "by_sector": by_sector,
            "by_institution": by_institution,
            "whole_portfolio": whole_portfolio,
            "portfolio_ex_ra": portfolio_ex_ra,
            "base_currency": base_currency,
            "generated_at": datetime.now().isoformat(),
            "ra_types_excluded": ra_types,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "generated_at": datetime.now().isoformat()}


def get_investment_metrics_data(database_name: str, base_currency: str = "ZAR", filter_type: str = "portfolio") -> dict:
    """
    Return real investment metrics from the database.
    
    Supports filters: portfolio, individual, by_currency, by_type, by_institution
    """
    try:
        # Metric type prefix (can be parameterized later)
        prefix = "local_"  # local_ for ZAR nominal, local_real_ for inflation-adjusted
        
        with get_db_connection(database_name) as (conn, cursor):
            # Build query based on filter
            if filter_type == "portfolio":
                # Portfolio-wide aggregation using LATEST metrics per investment
                # This ensures we don't average in historical zero rows
                query = f"""
                    SELECT 
                        im.metrics_date,
                        AVG({prefix}cagr) as cagr,
                        AVG({prefix}irr) as irr,
                        AVG({prefix}total_return) as total_return,
                        SUM({prefix}total_contributions) as total_contributions,
                        SUM({prefix}total_fees) as total_fees,
                        SUM({prefix}total_tax) as total_tax,
                        SUM({prefix}total_dividends) as total_dividends,
                        AVG({prefix}dividend_yield) as dividend_yield,
                        AVG({prefix}fee_ratio_annualized) as fee_ratio,
                        AVG({prefix}tax_ratio_annualized) as tax_ratio,
                        AVG({prefix}cost_ratio_annualized) as cost_ratio
                    FROM investment_metrics im
                    JOIN investments i ON im.investment_id = i.id
                    WHERE im.metrics_date = (
                        SELECT MAX(im2.metrics_date) FROM investment_metrics im2
                        WHERE im2.investment_id = im.investment_id
                    )
                    GROUP BY im.metrics_date
                    ORDER BY im.metrics_date ASC
                """
            else:
                # For other filters, get individual data (latest per investment)
                query = f"""
                    SELECT 
                        im.metrics_date,
                        i.investment_name,
                        i.investment_type,
                        i.unit_currency,
                        i.institution_name,
                        {prefix}cagr as cagr,
                        {prefix}irr as irr,
                        {prefix}total_return as total_return,
                        {prefix}total_contributions as total_contributions,
                        {prefix}total_fees as total_fees,
                        {prefix}total_tax as total_tax,
                        {prefix}total_dividends as total_dividends,
                        {prefix}dividend_yield as dividend_yield,
                        {prefix}fee_ratio_annualized as fee_ratio,
                        {prefix}tax_ratio_annualized as tax_ratio
                    FROM investment_metrics im
                    JOIN investments i ON im.investment_id = i.id
                    WHERE im.metrics_date = (
                        SELECT MAX(im2.metrics_date) FROM investment_metrics im2
                        WHERE im2.investment_id = im.investment_id
                    )
                    ORDER BY im.metrics_date ASC, i.investment_name
                """
            
            df = pd.read_sql(query, conn)
            
            if df.empty:
                # Return empty structure if no data
                return {
                    "portfolio_performance_return": [],
                    "rolling_returns": {"one_year": [], "three_year": [], "five_year": []},
                    "risk_metrics": {"volatility": [], "sharpe_ratio": [], "max_drawdown": []},
                    "contribution_vs_growth": [],
                    "drawdown_analysis": [],
                    "dividend_yield": [],
                    "fee_analysis": [],
                    "tax_analysis": [],
                    "cagr_trend": [],
                    "irr_trend": [],
                    "conclusion": "No metrics data available yet. Please run the metrics calculation.",
                    "filter_type": filter_type,
                    "base_currency": base_currency
                }
            
            # Convert dates
            df['metrics_date'] = pd.to_datetime(df['metrics_date'])
            
            # Portfolio Performance Return (using CAGR)
            portfolio_performance_return = []
            cagr_trend = []
            irr_trend = []
            
            if filter_type == "portfolio":
                for idx, row in df.iterrows():
                    period = row['metrics_date'].strftime("%Y-%m")
                    cagr_pct = round(float(row['cagr']) * 100, 2) if pd.notna(row['cagr']) else 0
                    irr_pct = round(float(row['irr']) * 100, 2) if pd.notna(row['irr']) else 0
                    
                    portfolio_performance_return.append({
                        "period": period,
                        "value": cagr_pct,
                        "index": idx
                    })
                    
                    cagr_trend.append({
                        "period": period,
                        "value": cagr_pct,
                        "index": idx
                    })
                    
                    irr_trend.append({
                        "period": period,
                        "value": irr_pct,
                        "index": idx
                    })
                    
            # Rolling Returns (calculate from existing data)
            rolling_returns = {
                "one_year": [],
                "three_year": [],
                "five_year": []
            }
            
            if filter_type == "portfolio" and len(df) >= 12:
                # Calculate 1-year rolling returns
                for i in range(len(df) - 11):
                    period_df = df.iloc[i:i+12]
                    avg_return = period_df['total_return'].mean() * 100
                    rolling_returns["one_year"].append({
                        "period": period_df.iloc[-1]['metrics_date'].strftime("%Y-%m"),
                        "value": round(float(avg_return), 2) if pd.notna(avg_return) else 0,
                        "index": i
                    })
                
                # Calculate 3-year rolling returns
                if len(df) >= 36:
                    for i in range(0, len(df) - 35, 3):
                        period_df = df.iloc[i:i+36]
                        avg_return = period_df['total_return'].mean() * 100
                        rolling_returns["three_year"].append({
                            "period": period_df.iloc[-1]['metrics_date'].strftime("%Y-Q%q"),
                            "value": round(float(avg_return), 2) if pd.notna(avg_return) else 0,
                            "index": len(rolling_returns["three_year"])
                        })
                
                # Calculate 5-year rolling returns
                if len(df) >= 60:
                    for i in range(0, len(df) - 59, 6):
                        period_df = df.iloc[i:i+60]
                        avg_return = period_df['total_return'].mean() * 100
                        rolling_returns["five_year"].append({
                            "period": period_df.iloc[-1]['metrics_date'].strftime("%Y"),
                            "value": round(float(avg_return), 2) if pd.notna(avg_return) else 0,
                            "index": len(rolling_returns["five_year"])
                        })
            
            # Risk Metrics (volatility calculated from CAGR/IRR variance)
            risk_metrics = {
                "volatility": [],
                "sharpe_ratio": [],
                "max_drawdown": []
            }
            
            if filter_type == "portfolio":
                # Calculate rolling volatility (12-month windows)
                for i in range(len(df) - 11):
                    period_df = df.iloc[i:i+12]
                    volatility = period_df['cagr'].std() * 100 if len(period_df) > 1 else 0
                    risk_metrics["volatility"].append({
                        "period": period_df.iloc[-1]['metrics_date'].strftime("%Y-%m"),
                        "value": round(float(volatility), 2) if pd.notna(volatility) else 0,
                        "index": i
                    })
                
                # Sharpe ratio (simplified: avg_return / volatility)
                for i in range(len(df) - 11):
                    period_df = df.iloc[i:i+12]
                    avg_return = period_df['cagr'].mean()
                    vol = period_df['cagr'].std()
                    sharpe = (avg_return / vol) if vol > 0 else 0
                    risk_metrics["sharpe_ratio"].append({
                        "period": period_df.iloc[-1]['metrics_date'].strftime("%Y-%m"),
                        "value": round(float(sharpe), 2) if pd.notna(sharpe) else 0,
                        "index": i
                    })
            
            # Contribution vs Growth
            contribution_vs_growth = []
            if filter_type == "portfolio":
                for idx, row in df.iterrows():
                    contributions = float(row['total_contributions']) if pd.notna(row['total_contributions']) else 0
                    growth = contributions * float(row['total_return']) if pd.notna(row['total_return']) else 0
                    
                    contribution_vs_growth.append({
                        "period": row['metrics_date'].strftime("%Y-%m"),
                        "contributions": round(contributions, 2),
                        "growth": round(growth, 2),
                        "index": idx
                    })
            
            # Dividend Yield Trend
            dividend_yield = []
            if filter_type == "portfolio":
                for idx, row in df.iterrows():
                    dividend_yield.append({
                        "period": row['metrics_date'].strftime("%Y-%m"),
                        "value": round(float(row['dividend_yield']), 4) if pd.notna(row['dividend_yield']) else 0,
                        "index": idx
                    })
            
            # Fee Analysis (NEW)
            fee_analysis = []
            if filter_type == "portfolio":
                for idx, row in df.iterrows():
                    fee_analysis.append({
                        "period": row['metrics_date'].strftime("%Y-%m"),
                        "fee_ratio": round(float(row['fee_ratio']) * 100, 3) if pd.notna(row['fee_ratio']) else 0,
                        "total_fees": round(float(row['total_fees']), 2) if pd.notna(row['total_fees']) else 0,
                        "index": idx
                    })
            
            # Tax Analysis (NEW)
            tax_analysis = []
            if filter_type == "portfolio":
                for idx, row in df.iterrows():
                    tax_analysis.append({
                        "period": row['metrics_date'].strftime("%Y-%m"),
                        "tax_ratio": round(float(row['tax_ratio']) * 100, 3) if pd.notna(row['tax_ratio']) else 0,
                        "total_tax": round(float(row['total_tax']), 2) if pd.notna(row['total_tax']) else 0,
                        "index": idx
                    })
            
            # Generate conclusion
            latest = df.iloc[-1]
            avg_cagr = float(latest['cagr']) if pd.notna(latest['cagr']) else 0
            avg_return = float(latest['total_return']) if pd.notna(latest['total_return']) else 0
            total_fees = float(latest.get('total_fees', 0)) if pd.notna(latest.get('total_fees')) else 0
            
            if avg_cagr > CAGR_EXCELLENT_THRESHOLD:
                performance = "Excellent"
            elif avg_cagr > CAGR_GOOD_THRESHOLD:
                performance = "Good"
            elif avg_cagr > CAGR_MODERATE_THRESHOLD:
                performance = "Moderate"
            else:
                performance = "Needs Attention"
            
            conclusion = f"{performance} {filter_type} performance with {avg_cagr*100:.2f}% annualized returns. "
            conclusion += f"Total returns: {avg_return*100:.2f}%. "
            if total_fees > 0:
                conclusion += f"Total fees paid: {base_currency} {total_fees:,.2f}."
            
            return {
                "portfolio_performance_return": portfolio_performance_return,
                "rolling_returns": rolling_returns,
                "risk_metrics": risk_metrics,
                "contribution_vs_growth": contribution_vs_growth,
                "drawdown_analysis": [],
                "dividend_yield": dividend_yield,
                "fee_analysis": fee_analysis,
                "tax_analysis": tax_analysis,
                "cagr_trend": cagr_trend,
                "irr_trend": irr_trend,
                "conclusion": conclusion,
                "filter_type": filter_type,
                "generated_at": datetime.now().isoformat(),
                "base_currency": base_currency,
                "data_points": len(df),
                "data_source": "DATABASE"
            }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "conclusion": "Error calculating metrics."
        }
