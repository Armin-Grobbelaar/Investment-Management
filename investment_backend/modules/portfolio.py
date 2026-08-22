from datetime import date
from .database import get_db_connection, DEFAULT_DB
from .currency import get_exchange_rate, CURRENCY_SYMBOLS, NATIVE_CURRENCY, BASE_CURRENCY_CODE, resolve_currency_code

# Portfolio configuration constants
PORTFOLIO_TICKER = "PORTFOLIO"
PORTFOLIO_NAME = "Total Portfolio"
PORTFOLIO_INSTITUTION = "Aggregated"
PORTFOLIO_TYPE = "Portfolio"

def _get_exchange_rate_for_portfolio(cursor, from_currency, to_currency, target_date, database_name):
    """
    Get exchange rate for portfolio aggregation.
    Uses existing get_exchange_rate function.
    """
    from_c = resolve_currency_code(from_currency)
    to_c = resolve_currency_code(to_currency)
    if from_c == to_c:
        return 1.0
    
    try:
        rate, _ = get_exchange_rate(from_c, to_c, target_date, database_name, cursor=cursor)
        return float(rate)
    except Exception as e:
        print(f"Warning: Exception getting exchange rate for {from_c} to {to_c} on {target_date}: {e}")
    
    return 1.0

def ensure_portfolio_exists(database_name=DEFAULT_DB):
    """
    Ensure the Portfolio investment exists. Create it if it doesn't.
    Returns the portfolio investment ID.
    """
    with get_db_connection(database_name) as (conn, cursor):
        # Check if portfolio exists
        cursor.execute("SELECT id FROM investments WHERE investment_ticker = %s", (PORTFOLIO_TICKER,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create portfolio investment
        today = date.today().isoformat()
        
        cursor.execute("""
            INSERT INTO investments (
                institution_name, initial_investment_date, investment_type,
                investment_name, investment_ticker, unit_currency,
                initial_unit_price, unit_price, number_of_units_held,
                total_dividends_received, total_tax_paid, total_fees_paid,
                investment_fee, investment_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            PORTFOLIO_INSTITUTION, today, PORTFOLIO_TYPE, PORTFOLIO_NAME,
            PORTFOLIO_TICKER, NATIVE_CURRENCY,
            100.0, 100.0, 1.0,  # Start at 100 per unit
            0.0, 0.0, 0.0,  # No fees/tax/dividends initially
            0.0, "Active"
        ))
        
        portfolio_id = cursor.fetchone()[0]
        
        # Create initial unit price
        cursor.execute("""
            INSERT INTO unit_prices (
                investment_id, unit_price_date, unit_price,
                unit_price_change, percentage_unit_price_change
            ) VALUES (%s, %s, %s, %s, %s)
        """, (portfolio_id, today, 100.0, 0.0, 0.0))
        
        conn.commit()
        print(f"✓ Created Portfolio investment (ID: {portfolio_id})")
        return portfolio_id

def update_portfolio(database_name=DEFAULT_DB, silent=False):
    """
    Update the Portfolio investment with aggregated data from all investments.
    """
    if not silent:
        print("\n📊 Updating Portfolio...")
    
    try:
        # Ensure portfolio exists
        portfolio_id = ensure_portfolio_exists(database_name)
        
        with get_db_connection(database_name) as (conn, cursor):
            # Get all non-portfolio investments
            cursor.execute("""
                SELECT id, investment_ticker, unit_currency, investment_status, unit_price, number_of_units_held
                FROM investments
                WHERE investment_ticker != %s
                ORDER BY id
            """, (PORTFOLIO_TICKER,))
            
            investments = cursor.fetchall()
            
            if not investments:
                if not silent:
                    print("   No investments to aggregate")
                return portfolio_id
            
            # Clear existing portfolio data
            cursor.execute("DELETE FROM transactions WHERE investment_id = %s", (portfolio_id,))
            cursor.execute("DELETE FROM fees WHERE investment_id = %s", (portfolio_id,))
            cursor.execute("DELETE FROM tax WHERE investment_id = %s", (portfolio_id,))
            cursor.execute("DELETE FROM unit_prices WHERE investment_id = %s", (portfolio_id,))
            
            # === AGGREGATE TRANSACTIONS ===
            aggregated_txns = {}
            for inv_id, ticker, currency, status, _, _ in investments:
                cursor.execute("""
                    SELECT transaction_date, transaction_type, transaction_amount, unit_price, number_of_units
                    FROM transactions
                    WHERE investment_id = %s
                    ORDER BY transaction_date
                """, (inv_id,))
                
                for txn_date, txn_type, txn_amount, unit_price, num_units in cursor.fetchall():
                    # Get exchange rate for this date
                    if currency == "R":
                        currency_code = "ZAR"
                    elif len(currency) == 1:
                        currency_code = CURRENCY_SYMBOLS.get(currency, currency)
                    else:
                        currency_code = currency
                    
                    exchange_rate = _get_exchange_rate_for_portfolio(cursor, currency_code, BASE_CURRENCY_CODE, txn_date, database_name)
                    txn_amount_zar = txn_amount * exchange_rate
                    
                    key = (txn_date, txn_type)
                    if key not in aggregated_txns:
                        aggregated_txns[key] = {'amount': 0.0, 'units': 0.0}
                    
                    aggregated_txns[key]['amount'] += txn_amount_zar
                    aggregated_txns[key]['units'] += num_units
            
            # Insert aggregated transactions
            for (txn_date, txn_type), data in sorted(aggregated_txns.items()):
                avg_unit_price = data['amount'] / data['units'] if data['units'] != 0 else 0
                cursor.execute("""
                    INSERT INTO transactions (
                        investment_id, transaction_date, transaction_type,
                        transaction_amount, unit_price, number_of_units
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (portfolio_id, txn_date, txn_type, data['amount'], avg_unit_price, data['units']))
            
            # === AGGREGATE FEES ===
            aggregated_fees = {}
            total_fees = 0.0
            for inv_id, ticker, currency, status, _, _ in investments:
                cursor.execute("""
                    SELECT fee_date, fee_type, fee_paid, fee_frequency, number_of_units, investment_fee
                    FROM fees
                    WHERE investment_id = %s
                """, (inv_id,))
                
                for fee_date, fee_type, fee_paid, fee_freq, num_units, inv_fee in cursor.fetchall():
                    currency_code = CURRENCY_SYMBOLS.get(currency, currency) if len(currency) == 1 else currency
                    exchange_rate = _get_exchange_rate_for_portfolio(cursor, currency_code, BASE_CURRENCY_CODE, fee_date, database_name)
                    fee_paid_zar = fee_paid * exchange_rate
                    total_fees += fee_paid_zar
                    
                    key = (fee_date, fee_type or "General")
                    if key not in aggregated_fees:
                        aggregated_fees[key] = {'fee_paid': 0.0, 'fee_frequency': fee_freq, 'number_of_units': 0.0, 'investment_fee': 0.0}
                    
                    aggregated_fees[key]['fee_paid'] += fee_paid_zar
                    aggregated_fees[key]['number_of_units'] += num_units
                    aggregated_fees[key]['investment_fee'] += inv_fee
            
            # Insert aggregated fees
            for (fee_date, fee_type), data in aggregated_fees.items():
                cursor.execute("""
                    INSERT INTO fees (
                        investment_id, fee_date, fee_type, fee_paid,
                        fee_frequency, number_of_units, investment_fee
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (portfolio_id, fee_date, fee_type, data['fee_paid'],
                      data['fee_frequency'], data['number_of_units'], data['investment_fee']))
            
            # === AGGREGATE TAX ===
            aggregated_tax = {}
            total_tax = 0.0
            for inv_id, ticker, currency, status, _, _ in investments:
                cursor.execute("""
                    SELECT tax_date, tax_type, tax_paid, tax_percentage
                    FROM tax
                    WHERE investment_id = %s
                """, (inv_id,))
                
                for tax_date, tax_type, tax_paid, tax_pct in cursor.fetchall():
                    currency_code = CURRENCY_SYMBOLS.get(currency, currency) if len(currency) == 1 else currency
                    exchange_rate = _get_exchange_rate_for_portfolio(cursor, currency_code, BASE_CURRENCY_CODE, tax_date, database_name)
                    tax_paid_zar = tax_paid * exchange_rate
                    total_tax += tax_paid_zar
                    
                    key = (tax_date, tax_type or "General")
                    if key not in aggregated_tax:
                        aggregated_tax[key] = {'tax_paid': 0.0, 'tax_percentage': tax_pct}
                    
                    aggregated_tax[key]['tax_paid'] += tax_paid_zar
            
            # Insert aggregated tax
            for (tax_date, tax_type), data in aggregated_tax.items():
                cursor.execute("""
                    INSERT INTO tax (
                        investment_id, tax_date, tax_type, tax_paid, tax_percentage
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (portfolio_id, tax_date, tax_type, data['tax_paid'], data['tax_percentage']))
            
            # === CALCULATE PORTFOLIO VALUE AND UNIT PRICES ===
            # Get all unique dates where we have unit prices
            cursor.execute("""
                SELECT DISTINCT unit_price_date
                FROM v_investment_prices up
                JOIN investments i ON up.investment_id = i.id
                WHERE i.investment_ticker != %s
                ORDER BY unit_price_date
            """, (PORTFOLIO_TICKER,))
            
            all_dates = [row[0] for row in cursor.fetchall()]
            
            if all_dates:
                previous_unit_price = 100.0
                
                for price_date in all_dates:
                    total_value_zar = 0.0
                    
                    # Calculate total portfolio value on this date
                    for inv_id, ticker, currency, status, current_price, current_units in investments:
                        # Get unit price for this date or closest previous
                        cursor.execute("""
                            SELECT unit_price
                            FROM v_investment_prices
                            WHERE investment_id = %s AND unit_price_date <= %s
                            ORDER BY unit_price_date DESC
                            LIMIT 1
                        """, (inv_id, price_date))
                        
                        result = cursor.fetchone()
                        if result:
                            unit_price = result[0]
                            
                            # Get number of units held on this date (from transactions up  to this date)
                            cursor.execute("""
                                SELECT COALESCE(SUM(
                                    CASE 
                                        WHEN LOWER(transaction_type) = 'buy' THEN number_of_units
                                        WHEN LOWER(transaction_type) = 'sell' THEN -number_of_units
                                        ELSE 0
                                    END
                                ), 0)
                                FROM transactions
                                WHERE investment_id = %s AND transaction_date <= %s
                            """, (inv_id, price_date))
                            
                            num_units = cursor.fetchone()[0]
                            value_foreign = unit_price * num_units
                            
                            # Convert to ZAR
                            currency_code = CURRENCY_SYMBOLS.get(currency, currency) if len(currency) == 1 else currency
                            exchange_rate = _get_exchange_rate_for_portfolio(cursor, currency_code, BASE_CURRENCY_CODE, price_date, database_name)
                            value_zar = value_foreign * exchange_rate
                            
                            total_value_zar += value_zar
                    
                    # Portfolio unit price = total value (since we have 1 unit)
                    portfolio_unit_price = total_value_zar if total_value_zar > 0 else 100.0
                    unit_price_change = portfolio_unit_price - previous_unit_price
                    pct_change = (unit_price_change / previous_unit_price * 100) if previous_unit_price != 0 else 0
                    
                    # Insert unit price
                    cursor.execute("""
                        INSERT INTO unit_prices (
                            investment_id, unit_price_date, unit_price,
                            unit_price_change, percentage_unit_price_change
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (portfolio_id, price_date, portfolio_unit_price, unit_price_change, pct_change))
                    
                    previous_unit_price = portfolio_unit_price
                
                # Update portfolio investment record
                cursor.execute("""
                    UPDATE investments
                    SET unit_price = %s,
                        number_of_units_held = 1.0,
                        total_fees_paid = %s,
                        total_tax_paid = %s
                    WHERE id = %s
                """, (previous_unit_price, total_fees, total_tax, portfolio_id))
            
            conn.commit()
            
            if not silent:
                print(f"   ✓ Aggregated {len(investments)} investments")
                print(f"   ✓ Portfolio value: R{previous_unit_price:,.2f}" if all_dates else "   ✓ No price history yet")
        
        return portfolio_id
        
    except Exception as e:
        if not silent:
            print(f"   ✗ Error updating portfolio: {e}")
        raise

def get_portfolio_total_value(database_name=DEFAULT_DB):
    """Get the current total value of the portfolio."""
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            SELECT unit_price FROM investments 
            WHERE investment_ticker = %s
        """, (PORTFOLIO_TICKER,))
        result = cursor.fetchone()
        return result[0] if result else 0.0
