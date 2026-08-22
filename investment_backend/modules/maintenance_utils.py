"""
Maintenance Utilities Module

Functions for routine maintenance tasks such as updating prices,
calculating metrics, and generating reports.
"""

from datetime import datetime
import yfinance as yf
from .database import get_db_connection, DEFAULT_DB
from .investments import get_investment_summary
from .metrics import update_investment_metrics
from .portfolio import update_portfolio
from .predictions import cleanup_old_predictions


from .currency import BASE_CURRENCY_CODE, resolve_currency_code, sync_exchange_rates_for_pair


def log(message, level="INFO"):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def sync_all_exchange_rates(database_name=DEFAULT_DB, period="5d"):
    """
    Sync exchange rates for all foreign currencies present in the portfolio.
    Called during routine maintenance.
    """
    log("Syncing FX rates for foreign currencies in portfolio...")
    try:
        with get_db_connection(database_name) as (conn, cursor):
            cursor.execute("""
                SELECT DISTINCT unit_currency FROM investments
                WHERE investment_ticker != 'PORTFOLIO'
                  AND investment_type != 'Forex'
            """)
            currencies = [resolve_currency_code(r[0]) for r in cursor.fetchall() if r[0]]

        synced_count = 0
        for curr in currencies:
            if curr != BASE_CURRENCY_CODE:
                log(f"  Syncing FX rates for {curr}/{BASE_CURRENCY_CODE}...")
                n = sync_exchange_rates_for_pair(curr, BASE_CURRENCY_CODE, database_name, period=period)
                synced_count += n

        log(f"FX rate sync complete: {synced_count} rates updated/inserted")
        return True
    except Exception as e:
        log(f"Failed to sync FX rates: {e}", "ERROR")
        return False


def update_unit_prices_from_yfinance(database_name=DEFAULT_DB):
    """
    Fetch and update unit prices for all investments from Yahoo Finance.
    This updates investments that have tickers compatible with yfinance.
    """
    log("Fetching latest unit prices from Yahoo Finance...")
    
    try:
        conn = get_db_connection(database_name)
        cursor = conn.cursor()
        
        # Get all investments with tickers (exclude Portfolio)
        cursor.execute("""
            SELECT id, investment_name, investment_ticker, unit_currency 
            FROM investments 
            WHERE investment_ticker IS NOT NULL 
            AND investment_ticker != 'PORTFOLIO'
            AND investment_ticker != ''
        """)
        
        investments = cursor.fetchall()
        updated_count = 0
        failed_count = 0
        
        for inv_id, inv_name, ticker, currency in investments:
            try:
                log(f"  Fetching price for {inv_name} ({ticker})...")
                
                # Fetch data from yfinance
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                
                if not hist.empty:
                    latest_price = hist['Close'].iloc[-1]
                    price_date = hist.index[-1].date()
                    
                    # Update the investment's current unit price
                    cursor.execute("""
                        UPDATE investments 
                        SET unit_price = %s
                        WHERE id = %s
                    """, (latest_price, inv_id))
                    
                    # Add to unit_prices table
                    cursor.execute("""
                        INSERT INTO unit_prices (investment_id, unit_price_date, unit_price)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (investment_id, unit_price_date) 
                        DO UPDATE SET unit_price = EXCLUDED.unit_price
                    """, (inv_id, price_date, latest_price))
                    
                    log(f"    ✓ Updated {inv_name}: {currency} {latest_price:.2f}")
                    updated_count += 1
                else:
                    log(f"    ⚠ No data available for {ticker}", "WARN")
                    failed_count += 1
                    
            except Exception as e:
                log(f"    ✗ Failed to update {inv_name}: {e}", "ERROR")
                failed_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        log(f"Unit prices update complete: {updated_count} updated, {failed_count} failed")
        return True
        
    except Exception as e:
        log(f"Failed to update unit prices: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def calculate_all_investment_metrics(database_name=DEFAULT_DB):
    """
    Calculate and store investment metrics for all investments.
    """
    log("Calculating metrics for all investments...")
    
    try:
        # Get all investments
        summary_df = get_investment_summary(database_name)
        
        updated_count = 0
        failed_count = 0
        
        for _, row in summary_df.iterrows():
            inv_id = row['id']
            inv_name = row['investment_name']
            
            try:
                log(f"  Calculating metrics for {inv_name}...")
                update_investment_metrics(inv_id, database_name)
                log(f"    ✓ Metrics calculated for {inv_name}")
                updated_count += 1
            except Exception as e:
                log(f"    ✗ Failed to calculate metrics for {inv_name}: {e}", "ERROR")
                failed_count += 1
        
        log(f"Metrics calculation complete: {updated_count} updated, {failed_count} failed")
        return True
        
    except Exception as e:
        log(f"Failed to calculate investment metrics: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def update_portfolio_aggregation(database_name=DEFAULT_DB):
    """
    Update the Portfolio investment with latest aggregated data.
    """
    log("Updating portfolio aggregation...")
    
    try:
        update_portfolio(database_name, silent=False)
        log("Portfolio aggregation complete")
        return True
        
    except Exception as e:
        log(f"Failed to update portfolio: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def cleanup_old_predictions_maintenance(database_name=DEFAULT_DB, days_to_keep=90):
    """
    Clean up old prediction data to save space.
    Keeps predictions from the last N days.
    """
    log(f"Cleaning up predictions older than {days_to_keep} days...")
    
    try:
        deleted_count = cleanup_old_predictions(database_name, days_to_keep)
        log(f"Cleanup complete: {deleted_count} old predictions removed")
        return True
        
    except Exception as e:
        log(f"Failed to cleanup predictions: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def generate_summary_report(database_name=DEFAULT_DB):
    """
    Generate a summary report of current portfolio status.
    """
    log("Generating portfolio summary report...")
    
    try:
        conn = get_db_connection(database_name)
        cursor = conn.cursor()
        
        # Get portfolio summary
        cursor.execute("""
            SELECT 
                COUNT(*) as total_investments,
                SUM(investment_value) as total_value,
                COUNT(DISTINCT unit_currency) as currencies,
                COUNT(DISTINCT investment_type) as investment_types
            FROM investments
            WHERE investment_ticker != 'PORTFOLIO'
        """)
        
        row = cursor.fetchone()
        total_investments, total_value, currencies, inv_types = row
        
        log("=" * 60)
        log("PORTFOLIO SUMMARY REPORT")
        log("=" * 60)
        log(f"  Total Investments:    {total_investments}")
        log(f"  Total Value:          {total_value:,.2f}" if total_value else "  Total Value:          N/A")
        log(f"  Currencies:           {currencies}")
        log(f"  Investment Types:     {inv_types}")
        log("=" * 60)
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        log(f"Failed to generate summary report: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False
