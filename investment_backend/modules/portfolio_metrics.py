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

    CAGR: computed as (total_current_value / total_contributions)^(1/max_period) - 1
          for the aggregated group. This is mathematically correct; averaging individual
          CAGRs is NOT valid.

    IRR:  computed via XIRR over the combined dated cash flows for the group up to each
          metrics_date. Contribution-weighted averaging of per-investment IRRs is NOT
          valid — a portfolio's IRR is a property of its aggregate cash-flow stream.
    """
    logger.info("Starting portfolio metrics aggregation...")
    try:
        with get_db_connection(database_name) as (conn, cursor):
            # Fetch all local metrics + investment metadata
            query = """
                SELECT
                    im.investment_id,
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
                    im.local_total_tax,
                    COALESCE(im.local_investment_period, 0.0) as local_investment_period
                FROM investment_metrics im
                JOIN investments i ON im.investment_id = i.id
                WHERE i.investment_status = 'Active'
            """
            df = pd.read_sql(query, conn)

            if df.empty:
                logger.warning("No investment metrics found to aggregate.")
                return 0

            # Add account_type dimension
            df['account_type'] = df.apply(
                lambda row: get_account_type(row['investment_type'], row['investment_name']), axis=1
            )

            # Fill NaNs conservatively
            numeric_cols = [
                'local_total_contributions', 'local_net_growth', 'local_total_return',
                'local_total_fees', 'local_total_dividends', 'local_total_tax',
                'local_investment_period'
            ]
            df[numeric_cols] = df[numeric_cols].fillna(0.0)

            # Compute current_value for each investment×date
            df['local_current_value'] = df['local_total_contributions'] + df['local_net_growth']

            # ----------------------------------------------------------------
            # Load raw dated cash flows from transactions, fees, tax, dividends
            # and unit_prices for XIRR computation per dimension group.
            # We load them once and filter per dimension later.
            # ----------------------------------------------------------------
            # Contributions (negative cash flow)
            cursor.execute("""
                SELECT t.investment_id, t.transaction_date, t.transaction_amount
                FROM transactions t
                JOIN investments i ON t.investment_id = i.id
                WHERE LOWER(t.transaction_type) = 'buy'
                  AND i.investment_status = 'Active'
                ORDER BY t.transaction_date
            """)
            contrib_rows = cursor.fetchall()

            # Fees (negative)
            cursor.execute("""
                SELECT f.investment_id, f.fee_date, f.fee_paid
                FROM fees f
                JOIN investments i ON f.investment_id = i.id
                WHERE i.investment_status = 'Active'
            """)
            fee_rows = cursor.fetchall()

            # Tax (negative)
            cursor.execute("""
                SELECT tx.investment_id, tx.tax_date, tx.tax_paid
                FROM tax tx
                JOIN investments i ON tx.investment_id = i.id
                WHERE i.investment_status = 'Active'
            """)
            tax_rows = cursor.fetchall()

            # Dividends (positive)
            cursor.execute("""
                SELECT d.investment_id, d.dividend_date, d.dividend_recieved
                FROM dividends d
                JOIN investments i ON d.investment_id = i.id
                WHERE i.investment_status = 'Active'
            """)
            div_rows = cursor.fetchall()

            # Build per-investment cash-flow list: (date, signed_amount)
            # Negative = outflow, positive = inflow
            import pandas as _pd
            cf_map: dict[int, list] = {}

            def _add_cf(inv_id, dt, amount):
                if inv_id not in cf_map:
                    cf_map[inv_id] = []
                cf_map[inv_id].append((_pd.to_datetime(dt), float(amount)))

            for inv_id, dt, amt in contrib_rows:
                if dt and amt:
                    _add_cf(inv_id, dt, -float(amt))  # outflow

            for inv_id, dt, amt in fee_rows:
                if dt and amt:
                    _add_cf(inv_id, dt, -float(amt))  # outflow

            for inv_id, dt, amt in tax_rows:
                if dt and amt:
                    _add_cf(inv_id, dt, -float(amt))  # outflow

            for inv_id, dt, amt in div_rows:
                if dt and amt:
                    _add_cf(inv_id, dt, +float(amt))  # inflow

            def _compute_xirr_for_group(investment_ids: list, terminal_date, current_values_by_inv: dict) -> float | None:
                """
                Compute XIRR for a group of investments up to terminal_date.
                - Cash outflows: contributions, fees, taxes on or before terminal_date
                - Cash inflows: dividends on or before terminal_date
                - Terminal inflow: current_value of each investment at terminal_date
                """
                from .metrics import xirr as _xirr
                dates = []
                amounts = []
                for inv_id in investment_ids:
                    for dt, amt in cf_map.get(inv_id, []):
                        if dt <= terminal_date:
                            dates.append(dt)
                            amounts.append(amt)
                    # Terminal value as positive inflow
                    terminal_val = current_values_by_inv.get(inv_id, 0.0)
                    if terminal_val > 0:
                        dates.append(terminal_date)
                        amounts.append(terminal_val)

                if len(dates) < 2:
                    return None
                if not any(a < 0 for a in amounts) or not any(a > 0 for a in amounts):
                    return None
                try:
                    result = _xirr(dates, amounts)
                    return float(result) if result is not None else None
                except Exception:
                    return None

            stored = 0

            def upsert_dimension(group_date, dim_type, dim_value, inv_ids: list,
                                 contrib, current_val, net_growth, fees, divs, tax,
                                 count, max_period, current_values_by_inv: dict):
                nonlocal stored

                # Total return percentage (always recomputed from aggregated values)
                ret_pct = 0.0
                if contrib > 0:
                    ret_pct = ((current_val - contrib) / contrib) * 100

                ret_amt = net_growth

                # CAGR: portfolio-level formula — NOT an average of individual CAGRs
                cagr_val = 0.0
                if contrib > 0 and max_period > 0 and current_val > 0:
                    return_multiple = current_val / contrib
                    if return_multiple > 0:
                        cagr_val = (return_multiple ** (1.0 / max_period)) - 1.0
                elif contrib > 0:
                    cagr_val = (ret_pct / 100.0)

                # IRR: computed via XIRR over combined cash flows
                terminal_dt = _pd.to_datetime(group_date)
                irr_val_raw = _compute_xirr_for_group(inv_ids, terminal_dt, current_values_by_inv)
                irr_val = irr_val_raw if irr_val_raw is not None else cagr_val  # fallback to CAGR

                cursor.execute("""
                    INSERT INTO portfolio_metrics (
                        metrics_date, dimension_type, dimension_value,
                        total_contributions, total_current_value, total_return_amount, total_return_pct,
                        cagr, irr, total_fees, total_dividends, total_tax, investment_count
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (metrics_date, dimension_type, dimension_value)
                    DO UPDATE SET
                        total_contributions = EXCLUDED.total_contributions,
                        total_current_value = EXCLUDED.total_current_value,
                        total_return_amount = EXCLUDED.total_return_amount,
                        total_return_pct = EXCLUDED.total_return_pct,
                        cagr = EXCLUDED.cagr,
                        irr = EXCLUDED.irr,
                        total_fees = EXCLUDED.total_fees,
                        total_dividends = EXCLUDED.total_dividends,
                        total_tax = EXCLUDED.total_tax,
                        investment_count = EXCLUDED.investment_count
                """, (
                    group_date, dim_type, dim_value,
                    contrib, current_val, ret_amt, ret_pct,
                    cagr_val, irr_val, fees, divs, tax, count
                ))
                stored += 1

            # Get all unique metrics_dates to iterate over
            all_dates = sorted(df['metrics_date'].unique())

            # Dimension groupings: name -> (column, dim_type_label)
            dimensions = [
                ('portfolio',      None,                'portfolio'),
                ('investment_type', 'investment_type',  'investment_type'),
                ('institution',    'institution_name',  'institution'),
                ('account_type',   'account_type',      'account_type'),
                ('currency',       'unit_currency',     'currency'),
            ]

            for m_date in all_dates:
                # Slice to only rows on or before this date (cumulative view)
                # Each investment keeps its LATEST row on or before m_date
                date_df = df[df['metrics_date'] <= m_date].copy()

                # Latest metric per investment (most recent on or before m_date)
                date_df = date_df.sort_values('metrics_date').groupby('investment_id').last().reset_index()

                # Build current_values_by_investment for XIRR terminal values
                current_values_by_inv = dict(zip(date_df['investment_id'], date_df['local_current_value']))

                for dim_key, col, dim_type_label in dimensions:
                    if col is None:
                        # Portfolio = all investments
                        groups = [('All', date_df)]
                    else:
                        groups = [(val, grp) for val, grp in date_df.groupby(col)]

                    for dim_val, grp in groups:
                        inv_ids = list(grp['investment_id'])
                        contrib = float(grp['local_total_contributions'].sum())
                        net_growth = float(grp['local_net_growth'].sum())
                        current_val = float(grp['local_current_value'].sum())
                        fees = float(grp['local_total_fees'].sum())
                        divs = float(grp['local_total_dividends'].sum())
                        tax = float(grp['local_total_tax'].sum())
                        count = len(grp)
                        max_period = float(grp['local_investment_period'].max())

                        cv_by_inv = {inv_id: current_values_by_inv.get(inv_id, 0.0) for inv_id in inv_ids}

                        upsert_dimension(
                            m_date, dim_type_label, str(dim_val),
                            inv_ids, contrib, current_val, net_growth,
                            fees, divs, tax, count, max_period, cv_by_inv
                        )

            conn.commit()
            logger.info(f"Successfully aggregated and stored {stored} portfolio metrics rows.")
            return stored

    except Exception as e:
        logger.error(f"Error calculating portfolio metrics: {e}")
        import traceback
        traceback.print_exc()
        return 0

