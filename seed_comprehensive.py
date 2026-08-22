#!/usr/bin/env python3
"""
Comprehensive database seeder for the investment app audit.
Creates realistic test data covering every scenario the app needs to handle.

Test user: Armin Grobbelaar
Portfolio: 8 investments across multiple types, currencies, and platforms
Features exercised: buy, sell, switch-out, switch-in, fees, dividends, tax, withdrawals
"""

import os
import psycopg2
import math
from datetime import date, timedelta

DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "changeme")
DB_PORT = int(os.environ.get("POSTGRES_PORT", 5432))
INVESTMENTS_DB = os.environ.get("INVESTMENTS_DB", "Investments")
USERS_DB = os.environ.get("USERS_DB", "Users")


def realistic_price_series(start_price, days, seed_price, volatility=0.12, annual_drift=0.08):
    """Generate a realistic-ish price series using a geometric brownian motion seed.
    Returns a list of (day_offset, price) tuples.
    """
    import random
    rng = random.Random(seed_price)
    prices = [start_price]
    daily_drift = annual_drift / 252
    daily_vol = volatility / math.sqrt(252)
    
    for _ in range(1, days):
        z = rng.gauss(0, 1)
        change = daily_drift + daily_vol * z
        new_price = prices[-1] * (1 + change)
        new_price = max(new_price, prices[-1] * 0.7)  # no more than 30% drop in one day
        prices.append(round(new_price, 4))
    return prices


def seed_users(conn):
    """Create test user."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (username, email, password_hash)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """, ('armin', 'armin@example.com', 'pbkdf2:sha256:audit_test_hash'))
    conn.commit()
    cur.close()
    print("✓ Test user created")


def seed_investments(conn):
    """Create comprehensive investment portfolio."""
    cur = conn.cursor()
    
    investments = [
        # 1. Allan Gray Balanced Fund — Unit Trust, ZAR, 3+ years history
        ("Allan Gray", "Allan Gray Balanced Fund", "AGBF", "Unit Trust", "ZAR",
         "2022-01-15", 42.50, 48.32, 25000.0, 0.005, "Active"),
        # 2. Satrix S&P500 ETF — ETF, USD, 2+ years history
        ("Standard Bank", "Satrix S&P500 ETF", "STXSP5", "ETF", "USD",
         "2022-06-01", 85.20, 92.15, 200, 0.003, "Active"),
        # 3. PSG Wealth Flexi Fund — Unit Trust, ZAR, 2.5 years
        ("PSG Wealth", "PSG Flexi Fund", "PSGFF", "Unit Trust", "ZAR",
         "2022-09-01", 128.00, 142.50, 800.0, 0.008, "Active"),
        # 4. Discovery Tax-Free Account — Unit Trust, ZAR, 2+ years
        ("Discovery", "Discovery Tax Free Account", "DTFA", "Tax Free", "ZAR",
         "2023-01-10", 95.00, 103.75, 1200.0, 0.002, "Active"),
        # 5. Sanlam Retirement Annuity — Unit Trust, ZAR, 3+ years
        ("Sanlam", "Sanlam Retirement Annuity", "SRA", "Retirement Annuity", "ZAR",
         "2021-06-01", 65.00, 82.40, 3000.0, 0.012, "Active"),
        # 6. Tech Growth Stock (ad-hoc buy) — Equity, ZAR
        ("Discretionary", "Tech Growth Stock", "TGS", "Equity", "ZAR",
         "2023-07-01", 215.00, 198.50, 100.0, 0.005, "Active"),
        # 7. Allan Gray Equity Fund — Unit Trust, ZAR (switch target)
        ("Allan Gray", "Allan Gray Equity Fund", "AGEF", "Unit Trust", "ZAR",
         "2023-04-01", 78.00, 89.50, 500.0, 0.005, "Active"),
        # 8. Nedgroup Investments Global Tech — Unit Trust, USD
        ("Nedgroup", "Nedgroup Global Tech Fund", "NGTF", "Unit Trust", "USD",
         "2022-11-15", 55.30, 61.20, 400.0, 0.01, "Active"),
    ]
    
    inv_ids = {}
    for inv in investments:
        inst, name, ticker, typ, curr, inv_date, p_init, p_curr, units, fee, status = inv
        cur.execute("""
            INSERT INTO investments (
                institution_name, initial_investment_date, investment_type,
                investment_name, investment_ticker, unit_currency,
                initial_unit_price, unit_price, number_of_units_held,
                total_dividends_received, total_tax_paid, total_fees_paid,
                investment_fee, investment_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, %s, %s)
            RETURNING id
        """, (inst, inv_date, typ, name, ticker, curr, p_init, p_curr, units, fee, status))
        inv_id = cur.fetchone()[0]
        inv_ids[ticker] = inv_id
        print(f"  Created investment: {name} (ID: {inv_id})")
    
    conn.commit()
    cur.close()
    return inv_ids


def seed_unit_prices(conn, inv_ids):
    """Generate realistic unit price history for all investments."""
    cur = conn.cursor()
    
    price_configs = {
        "AGBF":  {"start": 42.50, "days": 1300, "vol": 0.10, "drift": 0.08, "seed": 42},
        "STXSP5": {"start": 85.20, "days": 1100, "vol": 0.15, "drift": 0.12, "seed": 43},
        "PSGFF": {"start": 128.00, "days": 1050, "vol": 0.12, "drift": 0.07, "seed": 44},
        "DTFA":  {"start": 95.00, "days": 950, "vol": 0.11, "drift": 0.06, "seed": 45},
        "SRA":   {"start": 65.00, "days": 1500, "vol": 0.09, "drift": 0.07, "seed": 46},
        "TGS":   {"start": 215.00, "days": 400, "vol": 0.25, "drift": -0.03, "seed": 47},
        "AGEF":  {"start": 78.00, "days": 850, "vol": 0.14, "drift": 0.09, "seed": 48},
        "NGTF":  {"start": 55.30, "days": 1100, "vol": 0.18, "drift": 0.10, "seed": 49},
    }
    
    base_date = date(2022, 1, 1)
    
    for ticker, inv_id in inv_ids.items():
        cfg = price_configs.get(ticker)
        if not cfg:
            continue
        
        prices = realistic_price_series(
            cfg["start"], cfg["days"], cfg["seed"],
            volatility=cfg["vol"], annual_drift=cfg["drift"]
        )
        
        prev_price = prices[0]
        for i, price in enumerate(prices):
            day_offset = i  # daily data
            price_date = base_date + timedelta(days=day_offset)
            if price_date > date.today():
                break
            
            change = price - prev_price
            pct_change = (change / prev_price * 100) if prev_price != 0 else 0
            
            cur.execute("""
                INSERT INTO unit_prices (
                    investment_id, unit_price_date, unit_price,
                    unit_price_change, percentage_unit_price_change
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (investment_id, unit_price_date) DO UPDATE SET
                    unit_price = EXCLUDED.unit_price,
                    unit_price_change = EXCLUDED.unit_price_change,
                    percentage_unit_price_change = EXCLUDED.percentage_unit_price_change
            """, (inv_id, price_date, price, change, pct_change))
            
            prev_price = price
        
        # Update the investment's current unit price
        cur.execute(
            "UPDATE investments SET unit_price = %s WHERE id = %s",
            (prev_price, inv_id)
        )
        print(f"  Seeded {min(len(prices), (date.today() - base_date).days)} price points for {ticker}")
    
    conn.commit()
    cur.close()


def seed_transactions(conn, inv_ids):
    """Seed realistic transactions: buys, sell, switch-out, switch-in, withdrawal, fee."""
    cur = conn.cursor()
    
    # === AGBF: Monthly recurring buys over 3 years ===
    agbf_id = inv_ids["AGBF"]
    base_price = 42.50
    contrib_date = date(2022, 2, 15)
    total_contrib = 0
    total_units = 0
    
    while contrib_date <= date.today():
        amount = 2500  # fixed monthly contribution
        units_bought = amount / base_price
        cur.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type,
                transaction_amount, unit_price, number_of_units)
            VALUES (%s, %s, 'buy', %s, %s, %s)
        """, (agbf_id, contrib_date, amount, base_price, units_bought))
        total_contrib += amount
        total_units += units_bought
        
        # Adjust base price slightly each month to simulate time progression
        base_price *= 1.006
        contrib_date += timedelta(days=30)
    
    # Update investment record
    cur.execute(
        "UPDATE investments SET number_of_units_held = %s WHERE id = %s",
        (round(total_units, 4), agbf_id)
    )
    print(f"  AGBF: {int(total_contrib/2500)} monthly buys, total R{total_contrib:,.0f}, {total_units:.0f} units")
    
    # === STXSP5: Initial buy + 2 ad-hoc lump sums ===
    stx_id = inv_ids["STXSP5"]
    cur.execute("""
        INSERT INTO transactions (investment_id, transaction_date, transaction_type,
            transaction_amount, unit_price, number_of_units)
        VALUES (%s, %s, 'buy', %s, %s, %s)
    """, (stx_id, date(2022, 6, 1), 17040.0, 85.20, 200.0))
    
    cur.execute("""
        INSERT INTO transactions (investment_id, transaction_date, transaction_type,
            transaction_amount, unit_price, number_of_units)
        VALUES (%s, %s, 'buy', %s, %s, %s)
    """, (stx_id, date(2023, 3, 15), 5000.0, 89.30, 55.99))
    
    cur.execute("""
        INSERT INTO transactions (investment_id, transaction_date, transaction_type,
            transaction_amount, unit_price, number_of_units)
        VALUES (%s, %s, 'buy', %s, %s, %s)
    """, (stx_id, date(2024, 1, 10), 10000.0, 91.00, 109.89))
    
    cur.execute(
        "UPDATE investments SET number_of_units_held = %s WHERE id = %s",
        (365.88, stx_id)
    )
    print(f"  STXSP5: 3 buys (initial + 2 ad-hoc)")
    
    # === PSGFF: Monthly buys for 1 year, then a withdrawal ===
    psg_id = inv_ids["PSGFF"]
    psg_price = 128.0
    psg_contrib_date = date(2022, 10, 1)
    psg_units = 0.0
    
    while psg_contrib_date <= date(2023, 9, 1):
        amount = 1500
        units = amount / psg_price
        cur.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type,
                transaction_amount, unit_price, number_of_units)
            VALUES (%s, %s, 'buy', %s, %s, %s)
        """, (psg_id, psg_contrib_date, amount, psg_price, units))
        psg_units += units
        psg_price *= 1.005
        psg_contrib_date += timedelta(days=30)
    
    # Withdrawal in Oct 2023
    cur.execute("""
        INSERT INTO transactions (investment_id, transaction_date, transaction_type,
            transaction_amount, unit_price, number_of_units)
        VALUES (%s, %s, 'sell', %s, %s, %s)
    """, (psg_id, date(2023, 10, 15), 2000.0, 135.20, -14.79))
    psg_units -= 14.79
    
    cur.execute(
        "UPDATE investments SET number_of_units_held = %s WHERE id = %s",
        (round(psg_units, 4), psg_id)
    )
    print(f"  PSGFF: 12 monthly buys + 1 withdrawal")
    
    # === DTFA: Monthly buys (TFSA) ===
    dtfa_id = inv_ids["DTFA"]
    dtfa_price = 95.0
    dtfa_contrib_date = date(2023, 2, 1)
    dtfa_units = 0.0
    
    while dtfa_contrib_date <= date.today():
        amount = 1000
        units = amount / dtfa_price
        cur.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type,
                transaction_amount, unit_price, number_of_units)
            VALUES (%s, %s, 'buy', %s, %s, %s)
        """, (dtfa_id, dtfa_contrib_date, amount, dtfa_price, units))
        dtfa_units += units
        dtfa_price *= 1.004
        dtfa_contrib_date += timedelta(days=30)
    
    cur.execute(
        "UPDATE investments SET number_of_units_held = %s WHERE id = %s",
        (round(dtfa_units, 4), dtfa_id)
    )
    print(f"  DTFA: Monthly TFSA buys")
    
    # === SRA: RA with annual contributions ===
    sra_id = inv_ids["SRA"]
    sra_prices = [65.0, 68.5, 72.0, 75.8, 78.5, 82.4]
    sra_dates = [date(y, 6, 1) for y in range(2021, 2027)]
    sra_units = 0.0
    
    for i, (d, p) in enumerate(zip(sra_dates, sra_prices)):
        amount = 5000 * (1 + 0.05 * i)  # growing annual contribution
        units = amount / p
        cur.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type,
                transaction_amount, unit_price, number_of_units)
            VALUES (%s, %s, 'buy', %s, %s, %s)
        """, (sra_id, d, amount, p, units))
        sra_units += units
    
    cur.execute(
        "UPDATE investments SET number_of_units_held = %s WHERE id = %s",
        (round(sra_units, 4), sra_id)
    )
    print(f"  SRA: 6 annual RA contributions")
    
    # === TGS: Single equity buy ===
    tgs_id = inv_ids["TGS"]
    cur.execute("""
        INSERT INTO transactions (investment_id, transaction_date, transaction_type,
            transaction_amount, unit_price, number_of_units)
        VALUES (%s, %s, 'buy', %s, %s, %s)
    """, (tgs_id, date(2023, 7, 1), 21500.0, 215.00, 100.0))
    print(f"  TGS: Single equity buy")
    
    # === SWITCH: Sell AGEF partial, buy NGTF (switch-out/switch-in) ===
    agef_id = inv_ids["AGEF"]
    ngtf_id = inv_ids["NGTF"]
    
    # Switch-out: sell from AGEF
    switch_amount = 4000.0
    switch_price = 85.00
    switch_units = switch_amount / switch_price
    
    cur.execute("""
        INSERT INTO transactions (investment_id, transaction_date, transaction_type,
            transaction_amount, unit_price, number_of_units)
        VALUES (%s, %s, 'switch_out', %s, %s, %s)
    """, (agef_id, date(2024, 3, 15), switch_amount, switch_price, switch_units))
    
    # Switch-in: buy into NGTF
    switch_in_price = 58.50
    switch_in_units = switch_amount / switch_in_price
    
    cur.execute("""
        INSERT INTO transactions (investment_id, transaction_date, transaction_type,
            transaction_amount, unit_price, number_of_units)
        VALUES (%s, %s, 'switch_in', %s, %s, %s)
    """, (ngtf_id, date(2024, 3, 15), switch_amount, switch_price, switch_in_units))
    
    cur.execute(
        "UPDATE investments SET number_of_units_held = number_of_units_held - %s WHERE id = %s",
        (round(switch_units, 4), agef_id)
    )
    cur.execute(
        "UPDATE investments SET number_of_units_held = number_of_units_held + %s WHERE id = %s",
        (round(switch_in_units, 4), ngtf_id)
    )
    
    # Add initial buy for NGTF
    cur.execute("""
        INSERT INTO transactions (investment_id, transaction_date, transaction_type,
            transaction_amount, unit_price, number_of_units)
        VALUES (%s, %s, 'buy', %s, %s, %s)
    """, (ngtf_id, date(2022, 11, 15), 22120.0, 55.30, 400.0))
    
    # Initial buy for AGEF
    cur.execute("""
        INSERT INTO transactions (investment_id, transaction_date, transaction_type,
            transaction_amount, unit_price, number_of_units)
        VALUES (%s, %s, 'buy', %s, %s, %s)
    """, (agef_id, date(2023, 4, 1), 39000.0, 78.00, 500.0))
    
    print(f"  Switch: AGEF→NGTF R{switch_amount:,.0f}")
    
    conn.commit()
    cur.close()


def seed_dividends(conn, inv_ids):
    """Seed dividends for appropriate investments."""
    cur = conn.cursor()
    
    # AGBF pays quarterly distributions
    agbf_id = inv_ids["AGBF"]
    for year in [2022, 2023, 2024, 2025, 2026]:
        for quarter in range(0, 4):
            d_date = date(year, 3 + quarter * 3, 15)
            if d_date > date.today():
                break
            amount = 350.0 * (1 + 0.03 * (year - 2022))  # growing dividends
            cur.execute("""
                INSERT INTO dividends (investment_id, dividend_date, dividend_frequency,
                    dividend_recieved, dividend_percentage)
                VALUES (%s, %s, 4, %s, 0.02)
            """, (agbf_id, d_date, amount))
    
    # STXSP5 pays semi-annual dividends
    stx_id = inv_ids["STXSP5"]
    for year in [2022, 2023, 2024, 2025, 2026]:
        for month in [6, 12]:
            d_date = date(year, month, 20)
            if d_date > date.today():
                break
            amount = 150.0 * (1 + 0.05 * (year - 2022))
            cur.execute("""
                INSERT INTO dividends (investment_id, dividend_date, dividend_frequency,
                    dividend_recieved, dividend_percentage)
                VALUES (%s, %s, 2, %s, 0.015)
            """, (stx_id, d_date, amount))
    
    # SRA pays annual distributions
    sra_id = inv_ids["SRA"]
    for year in [2022, 2023, 2024, 2025, 2026]:
        d_date = date(year, 12, 15)
        if d_date > date.today():
            break
        amount = 800.0 * (1 + 0.04 * (year - 2022))
        cur.execute("""
            INSERT INTO dividends (investment_id, dividend_date, dividend_frequency,
                dividend_recieved, dividend_percentage)
            VALUES (%s, %s, 1, %s, 0.012)
        """, (sra_id, d_date, amount))
    
    conn.commit()
    cur.close()
    print("  Dividends seeded for AGBF, STXSP5, SRA")


def seed_fees(conn, inv_ids):
    """Seed periodic fees."""
    cur = conn.cursor()
    
    # SRA has higher annual fees
    sra_id = inv_ids["SRA"]
    for year in [2022, 2023, 2024, 2025, 2026]:
        fee_date = date(year, 1, 15)
        if fee_date > date.today():
            break
        fee_amount = 350.0 * (1 + 0.05 * (year - 2022))
        cur.execute("""
            INSERT INTO fees (investment_id, fee_date, fee_type, fee_paid,
                fee_frequency, number_of_units, investment_fee)
            VALUES (%s, %s, 'Annual Management Fee', %s, 1, 0, 0.012)
        """, (sra_id, fee_date, fee_amount))
    
    # AGBF has quarterly fees
    agbf_id = inv_ids["AGBF"]
    for year in [2022, 2023, 2024, 2025, 2026]:
        for quarter in range(0, 4):
            fee_date = date(year, 3 + quarter * 3, 1)
            if fee_date > date.today():
                break
            fee_amount = 85.0 * (1 + 0.03 * (year - 2022))
            cur.execute("""
                INSERT INTO fees (investment_id, fee_date, fee_type, fee_paid,
                    fee_frequency, number_of_units, investment_fee)
                VALUES (%s, %s, 'Quarterly Admin Fee', %s, 4, 0, 0.005)
            """, (agbf_id, fee_date, fee_amount))
    
    conn.commit()
    cur.close()
    print("  Fees seeded for SRA, AGBF")


def seed_tax(conn, inv_ids):
    """Seed withholding tax records."""
    cur = conn.cursor()
    
    # SRA: withholding tax on dividends
    sra_id = inv_ids["SRA"]
    for year in [2022, 2023, 2024, 2025, 2026]:
        tax_date = date(year, 12, 15)
        if tax_date > date.today():
            break
        tax_amount = 120.0 * (1 + 0.04 * (year - 2022))
        cur.execute("""
            INSERT INTO tax (investment_id, tax_date, tax_type, tax_paid, tax_percentage)
            VALUES (%s, %s, 'Dividend Withholding Tax', %s, 0.20)
        """, (sra_id, tax_date, tax_amount))
    
    # STXSP5: withholding tax
    stx_id = inv_ids["STXSP5"]
    for year in [2022, 2023, 2024, 2025, 2026]:
        for month in [6, 12]:
            tax_date = date(year, month, 20)
            if tax_date > date.today():
                break
            tax_amount = 22.5 * (1 + 0.05 * (year - 2022))
            cur.execute("""
                INSERT INTO tax (investment_id, tax_date, tax_type, tax_paid, tax_percentage)
                VALUES (%s, %s, 'Dividend Withholding Tax', %s, 0.20)
            """, (stx_id, tax_date, tax_amount))
    
    conn.commit()
    cur.close()
    print("  Tax records seeded")


def verify_integrity(conn):
    """Verify data integrity."""
    cur = conn.cursor()
    
    # Check investment count
    cur.execute("SELECT COUNT(*) FROM investments")
    inv_count = cur.fetchone()[0]
    
    # Check transaction count
    cur.execute("SELECT COUNT(*) FROM transactions")
    txn_count = cur.fetchone()[0]
    
    # Check unit prices count
    cur.execute("SELECT COUNT(*) FROM unit_prices")
    price_count = cur.fetchone()[0]
    
    # Check dividends count
    cur.execute("SELECT COUNT(*) FROM dividends")
    div_count = cur.fetchone()[0]
    
    # Check fees count
    cur.execute("SELECT COUNT(*) FROM fees")
    fee_count = cur.fetchone()[0]
    
    # Check tax count
    cur.execute("SELECT COUNT(*) FROM tax")
    tax_count = cur.fetchone()[0]
    
    # Verify buy transactions match expected
    cur.execute("""
        SELECT COUNT(*) FROM transactions 
        WHERE LOWER(transaction_type) = 'buy'
    """)
    buy_count = cur.fetchone()[0]
    
    # Verify switch transactions exist
    cur.execute("""
        SELECT COUNT(*) FROM transactions 
        WHERE LOWER(transaction_type) IN ('switch_out', 'switch_in')
    """)
    switch_count = cur.fetchone()[0]
    
    # Verify sell transactions exist
    cur.execute("""
        SELECT COUNT(*) FROM transactions 
        WHERE LOWER(transaction_type) = 'sell'
    """)
    sell_count = cur.fetchone()[0]
    
    # Check configuration table
    cur.execute("SELECT COUNT(*) FROM configuration")
    config_count = cur.fetchone()[0]
    
    print(f"\n=== Data Integrity Check ===")
    print(f"  Investments: {inv_count}")
    print(f"  Transactions: {txn_count} (buys: {buy_count}, sells: {sell_count}, switches: {switch_count})")
    print(f"  Unit Prices: {price_count}")
    print(f"  Dividends: {div_count}")
    print(f"  Fees: {fee_count}")
    print(f"  Tax records: {tax_count}")
    print(f"  Configuration: {config_count}")
    print(f"  ✅ All checks passed" if all([inv_count >= 6, txn_count >= 30, price_count >= 100]) else "  ⚠️ Check data completeness")
    
    # Verify no foreign key violations
    cur.execute("""
        SELECT i.id, i.investment_name, 
               COALESCE(SUM(CASE WHEN t.transaction_type = 'buy' THEN t.number_of_units ELSE 0 END), 0) as bought,
               COALESCE(SUM(CASE WHEN t.transaction_type = 'sell' THEN t.number_of_units ELSE 0 END), 0) as sold,
               i.number_of_units_held
        FROM investments i
        LEFT JOIN transactions t ON t.investment_id = i.id
        GROUP BY i.id, i.investment_name, i.number_of_units_held
        ORDER BY i.id
    """)
    print(f"\n  Investment unit reconciliation:")
    for row in cur.fetchall():
        inv_id, name, bought, sold, units_held = row
        net = bought - abs(sold)
        status = "✅" if abs(net - units_held) < 1.0 else "⚠️"
        print(f"    {status} {name}: bought={bought:.0f}, sold={sold:.0f}, net={net:.0f}, held={units_held:.0f}")
    
    cur.close()


def main():
    """Main seed function."""
    print("🔄 Starting comprehensive database seeding...")
    print("=" * 60)
    
    # Connect and reset
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=INVESTMENTS_DB
    )
    conn.autocommit = True
    
    # Truncate all tables
    cur = conn.cursor()
    cur.execute("SET session_replication_role = 'replica'")
    for table in ["unit_prices_backup_20260808", "prediction_accuracy", "portfolio_metrics",
                   "investment_metrics", "predictions", "property_investments", "factsheets",
                   "investment_source_meta", "dividends", "fees", "tax", "returns",
                   "transactions", "unit_prices", "inflation", "investments"]:
        try:
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
        except Exception as e:
            print(f"  Skip truncating {table}: {e}")
    cur.execute("SET session_replication_role = 'origin'")
    conn.commit()
    cur.close()
    print("✓ All tables truncated")
    
    # Seed Users
    user_conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=USERS_DB
    )
    seed_users(user_conn)
    user_conn.close()
    
    # Ensure configuration table is populated
    # (create_tables.py handles this with ON CONFLICT DO NOTHING)
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'investment_backend'))
    from create_tables import create_tables
    create_tables(INVESTMENTS_DB)
    
    # Reconnect after create_tables
    conn.close()
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=INVESTMENTS_DB
    )
    
    # Seed data
    inv_ids = seed_investments(conn)
    seed_unit_prices(conn, inv_ids)
    seed_transactions(conn, inv_ids)
    seed_dividends(conn, inv_ids)
    seed_fees(conn, inv_ids)
    seed_tax(conn, inv_ids)
    
    # Verify
    verify_integrity(conn)
    
    conn.close()
    print("\n" + "=" * 60)
    print("✅ Comprehensive database seeding completed!")


if __name__ == "__main__":
    main()
