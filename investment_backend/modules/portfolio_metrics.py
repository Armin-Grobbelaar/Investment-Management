"""
Portfolio Metrics Aggregation
=============================
Calculates and stores aggregated portfolio metrics by dimension (institution, type, account type).
"""

import logging
import pandas as pd
from datetime import date
from .database import get_db_connection

logger = logging.getLogger("portfolio_metrics")

def get_account_type(investment_type: str, investment_name: str) -> str:
    """Infer account type from investment type or name."""
    type_str = (investment_type or "").lower()
    name_str = (investment_name or "").lower()
    
    if "tfsa" in type_str or "tax free" in type_str or "tax free" in name_str or "tfsa" in name_str:
        return "Tax Free"
    if "ra" in type_str or "retirement" in type_str or "ra" in name_str:
        return "Retirement Annuity"
    return "Voluntary"

def calculate_and_store_portfolio_metrics(database_name: str) -> int:
    """
    Reads all investment_metrics, groups them by date and various dimensions,
    and upserts into the portfolio_metrics table.
    """
    logger.info("Starting portfolio metrics aggregation...")
    try:
        with get_db_connection(database_name) as (conn, cursor):
            # Fetch all local metrics + investment metadata
            query = """
                SELECT 
                    im.metrics_date,
                    i.investment_name,
                    i.investment_type,
                    i.institution_name,
                    i.unit_currency,
                    im.local_total_contributions,
                    im.local_net_growth,
                    im.local_total_return,
                    im.local_total_fees,
                    im.local_total_dividends,
                    im.local_total_tax
                FROM investment_metrics im
                JOIN investments i ON im.investment_id = i.id
                WHERE i.investment_status = 'Active'
            """
            df = pd.read_sql(query, conn)
            
            if df.empty:
                logger.warning("No investment metrics found to aggregate.")
                return 0
                
            # Add account_type
            df['account_type'] = df.apply(lambda row: get_account_type(row['investment_type'], row['investment_name']), axis=1)
            
            # Fill NaNs
            df = df.fillna(0.0)
            
            # Compute current value
            df['local_current_value'] = df['local_total_contributions'] + df['local_net_growth']
            
            # Prepare aggregations
            agg_funcs = {
                'local_total_contributions': 'sum',
                'local_current_value': 'sum',
                'local_net_growth': 'sum',   # net growth is a dollar amount; sum it
                'local_total_fees': 'sum',
                'local_total_dividends': 'sum',
                'local_total_tax': 'sum',
                'investment_name': 'count' # use for investment_count
            }
            
            stored = 0
            
            # Helper to upsert a group
            def upsert_group(grouped_df, dim_type, dim_value_col=None):
                nonlocal stored
                for name, group in grouped_df:
                    d_val = name if dim_value_col else "All"
                    
                    # We have a time series for this dimension
                    for _, row in group.iterrows():
                        m_date = row['metrics_date']
                        
                        contrib = float(row['local_total_contributions'])
                        current_val = float(row['local_current_value'])
                        net_growth = float(row['local_net_growth'])
                        fees = float(row['local_total_fees'])
                        divs = float(row['local_total_dividends'])
                        tax = float(row['local_total_tax'])
                        count = int(row['investment_name'])
                        
                        # Return percentage = (current_value - contributions) / contributions
                        ret_pct = 0.0
                        if contrib > 0:
                            ret_pct = ((current_val - contrib) / contrib) * 100

                        # Absolute return amount (net growth in currency)
                        ret_amt = net_growth
                            
                        # Simplified CAGR/IRR approximation for aggregates (since we don't have full cashflows here)
                        # The real way to do IRR for aggregates is to sum cashflows per day, which is expensive.
                        # For now, we will store 0 for IRR/CAGR on the portfolio_metrics table, 
                        # or compute it in a separate pass.
                        
                        cursor.execute("""
                            INSERT INTO portfolio_metrics (
                                metrics_date, dimension_type, dimension_value,
                                total_contributions, total_current_value, total_return_amount, total_return_pct,
                                total_fees, total_dividends, total_tax, investment_count
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (metrics_date, dimension_type, dimension_value)
                            DO UPDATE SET
                                total_contributions = EXCLUDED.total_contributions,
                                total_current_value = EXCLUDED.total_current_value,
                                total_return_amount = EXCLUDED.total_return_amount,
                                total_return_pct = EXCLUDED.total_return_pct,
                                total_fees = EXCLUDED.total_fees,
                                total_dividends = EXCLUDED.total_dividends,
                                total_tax = EXCLUDED.total_tax,
                                investment_count = EXCLUDED.investment_count
                        """, (
                            m_date, dim_type, d_val,
                            contrib, current_val, ret_amt, ret_pct,
                            fees, divs, tax, count
                        ))
                        stored += 1
            
            # 1. Dimension: portfolio (all)
            agg_all = df.groupby('metrics_date').agg(agg_funcs).reset_index()
            agg_all['dim_value'] = 'All'
            upsert_group(agg_all.groupby('dim_value'), 'portfolio')
            
            # 2. Dimension: investment_type
            agg_type = df.groupby(['investment_type', 'metrics_date']).agg(agg_funcs).reset_index()
            upsert_group(agg_type.groupby('investment_type'), 'investment_type', True)
            
            # 3. Dimension: institution
            agg_inst = df.groupby(['institution_name', 'metrics_date']).agg(agg_funcs).reset_index()
            upsert_group(agg_inst.groupby('institution_name'), 'institution', True)
            
            # 4. Dimension: account_type
            agg_acc = df.groupby(['account_type', 'metrics_date']).agg(agg_funcs).reset_index()
            upsert_group(agg_acc.groupby('account_type'), 'account_type', True)
            
            # 5. Dimension: currency
            agg_curr = df.groupby(['unit_currency', 'metrics_date']).agg(agg_funcs).reset_index()
            upsert_group(agg_curr.groupby('unit_currency'), 'currency', True)
            
            conn.commit()
            logger.info(f"Successfully aggregated and stored {stored} portfolio metrics rows.")
            return stored
            
    except Exception as e:
        logger.error(f"Error calculating portfolio metrics: {e}")
        return 0
