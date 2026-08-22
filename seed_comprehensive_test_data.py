#!/usr/bin/env python3
"""
Phase 0 Database Reset and Comprehensive Test Data Seeding Script
"""

import os
import sys
import math
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'investment_backend'))
from modules.database import get_db_connection, DEFAULT_DB, USERS_DB
from create_tables import drop_all_tables, create_tables
from modules.maintenance_utils import calculate_all_investment_metrics, update_portfolio_aggregation

def seed_database():
    print("=" * 60)
    print("Phase 0: Database Reset & Comprehensive Seeding")
    print("=" * 60)

    db_name = DEFAULT_DB
    users_db = USERS_DB

    # 1. Reset tables
    print("Dropping existing tables...")
    drop_all_tables(db_name)
    drop_all_tables(users_db)

    print("Creating schema tables...")
    create_tables(db_name)
    create_tables(users_db)

    # 2. Seed User
    print("Seeding test user...")
    with get_db_connection(users_db) as (conn, cursor):
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, ('armin_investor', 'armin@example.com', 'pbkdf2:sha256:260000$test_secure_hash', datetime(2021, 1, 1)))
        conn.commit()

    # 3. Seed Investments, Transactions, Unit Prices, Fees, Tax, Dividends, Inflation
    print("Seeding realistic multi-year investment portfolio data...")

    with get_db_connection(db_name) as (conn, cursor):
        # A. Seed Inflation rates
        inf_dates = [date(y, 1, 1) for y in range(2020, 2027)]
        for d in inf_dates:
            cursor.execute("""
                INSERT INTO inflation (inflation_date, inflation_rate, country, currency, source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (inflation_date, country) DO UPDATE SET inflation_rate = EXCLUDED.inflation_rate
            """, (d, 0.052, 'South Africa', 'ZAR', 'StatsSA'))
            cursor.execute("""
                INSERT INTO inflation (inflation_date, inflation_rate, country, currency, source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (inflation_date, country) DO UPDATE SET inflation_rate = EXCLUDED.inflation_rate
            """, (d, 0.028, 'United States', 'USD', 'US BLS'))

        # B. Define Investments metadata
        investments_data = [
            {
                "id": 1,
                "institution_name": "Allan Gray",
                "initial_investment_date": date(2021, 1, 15),
                "investment_type": "Unit Trust",
                "investment_name": "AG Equity Fund",
                "investment_ticker": "AGEF",
                "unit_currency": "ZAR",
                "initial_unit_price": 100.0,
                "unit_price": 145.50,
                "investment_status": "Active",
                "investment_subtype": "Equity Fund",
                "source_account": "Tax Free Account"
            },
            {
                "id": 2,
                "institution_name": "PSG Wealth",
                "initial_investment_date": date(2020, 6, 1),
                "investment_type": "Unit Trust",
                "investment_name": "PSG Balanced Fund",
                "investment_ticker": "PSGBF",
                "unit_currency": "ZAR",
                "initial_unit_price": 80.0,
                "unit_price": 112.30,
                "investment_status": "Active",
                "investment_subtype": "Balanced Fund",
                "source_account": "Retirement Annuity"
            },
            {
                "id": 3,
                "institution_name": "Standard Bank",
                "initial_investment_date": date(2021, 3, 10),
                "investment_type": "ETF",
                "investment_name": "Satrix Top 40 ETF",
                "investment_ticker": "STX40",
                "unit_currency": "ZAR",
                "initial_unit_price": 60.0,
                "unit_price": 82.40,
                "investment_status": "Active",
                "investment_subtype": "Index ETF",
                "source_account": "Discretionary Brokerage"
            },
            {
                "id": 4,
                "institution_name": "Alexander Forbes",
                "initial_investment_date": date(2022, 1, 10),
                "investment_type": "Equity",
                "investment_name": "AF Global Equity",
                "investment_ticker": "AFGE",
                "unit_currency": "USD",
                "initial_unit_price": 120.0,
                "unit_price": 158.00,
                "investment_status": "Active",
                "investment_subtype": "Global Offshore",
                "source_account": "Offshore Account"
            },
            {
                "id": 5,
                "institution_name": "Standard Bank",
                "initial_investment_date": date(2024, 1, 15),
                "investment_type": "ETF",
                "investment_name": "Satrix MSCI World ETF",
                "investment_ticker": "STXWDM",
                "unit_currency": "ZAR",
                "initial_unit_price": 75.0,
                "unit_price": 88.60,
                "investment_status": "Active",
                "investment_subtype": "Global ETF",
                "source_account": "Discretionary Brokerage"
            },
            {
                "id": 6,
                "institution_name": "Forex Market",
                "initial_investment_date": date(2020, 1, 1),
                "investment_type": "Forex",
                "investment_name": "USD/ZAR Exchange Rate",
                "investment_ticker": "USDZAR=X",
                "unit_currency": "ZAR",
                "initial_unit_price": 14.50,
                "unit_price": 18.50,
                "investment_status": "Active",
                "investment_subtype": "Currency Pair",
                "source_account": "Treasury"
            }
        ]

        # Insert placeholder rows in investments table to generate IDs
        for inv in investments_data:
            cursor.execute("""
                INSERT INTO investments (
                    id, institution_name, initial_investment_date, investment_type,
                    investment_name, investment_ticker, unit_currency, initial_unit_price,
                    unit_price, number_of_units_held, total_dividends_received, total_tax_paid,
                    total_fees_paid, investment_fee, investment_status, investment_subtype, source_account
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    unit_price = EXCLUDED.unit_price
            """, (
                inv["id"], inv["institution_name"], inv["initial_investment_date"], inv["investment_type"],
                inv["investment_name"], inv["investment_ticker"], inv["unit_currency"], float(inv["initial_unit_price"]),
                float(inv["unit_price"]), 0.0, 0.0, 0.0, 0.0, 0.005, inv["investment_status"],
                inv["investment_subtype"], inv["source_account"]
            ))

        # Reset serial sequence
        cursor.execute("SELECT setval('investments_id_seq', (SELECT MAX(id) FROM investments))")

        # C. Generate Realistic Price History and Transactions
        np.random.seed(42)

        # Helper to generate monthly dates from start_date to today
        today_date = date(2026, 8, 1)

        # Build Forex price history (USDZAR=X)
        fx_dates = pd.date_range(start='2020-01-01', end=today_date, freq='ME').date
        fx_price = 14.50
        for dt in fx_dates:
            fx_price = float(max(13.50, fx_price * (1 + float(np.random.normal(0.003, 0.02)))))
            cursor.execute("""
                INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (investment_id, unit_price_date) DO NOTHING
            """, (6, dt, fx_price, 0.0, 0.0))

        # Investment 1: AG Equity Fund (Initial lump sum + Monthly SIP + Ad-hoc lump sum)
        inv1_start = date(2021, 1, 15)
        inv1_dates = pd.date_range(start='2021-01-15', end=today_date, freq='ME').date
        price = 100.0
        units_held = 0.0
        total_fees = 0.0
        total_tax = 0.0
        total_divs = 0.0

        # Initial lump sum
        lump_amount = 30000.0
        lump_units = lump_amount / price
        units_held += lump_units
        cursor.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
            VALUES (1, %s, 'buy', %s, %s, %s)
        """, (inv1_start, float(lump_amount), float(price), float(lump_units)))

        for dt in inv1_dates:
            drift = 0.008  # ~10% annual drift
            shock = float(np.random.normal(drift, 0.025))
            price = float(max(80.0, price * (1 + shock)))

            cursor.execute("""
                INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (investment_id, unit_price_date) DO UPDATE SET unit_price = EXCLUDED.unit_price
            """, (1, dt, float(price), 0.0, 0.0))

            # Monthly contribution
            monthly_amount = float(2500.0 + float(np.random.choice([0, 500, 1000])))
            m_units = float(monthly_amount / price)
            units_held += m_units
            cursor.execute("""
                INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
                VALUES (1, %s, 'buy', %s, %s, %s)
            """, (dt, float(monthly_amount), float(price), float(m_units)))

            # Quarterly fee
            if dt.month in [3, 6, 9, 12]:
                fee_amt = float(units_held * price * 0.0015)
                total_fees += fee_amt
                cursor.execute("""
                    INSERT INTO fees (investment_id, fee_date, fee_type, fee_paid, fee_frequency, number_of_units, investment_fee)
                    VALUES (%s, %s, 'Management Fee', %s, 4, %s, 0.006)
                """, (1, dt, float(fee_amt), float(units_held)))

            # Annual dividend
            if dt.month == 12:
                div_amt = float(units_held * price * 0.025)
                total_divs += div_amt
                cursor.execute("""
                    INSERT INTO dividends (investment_id, dividend_date, dividend_frequency, dividend_recieved, dividend_percentage)
                    VALUES (%s, %s, 1, %s, 0.025)
                """, (1, dt, float(div_amt)))

        # Ad-hoc lump sum contribution in June 2023
        adhoc_dt = date(2023, 6, 15)
        adhoc_price = float(price * 0.95)
        adhoc_amount = 15000.0
        adhoc_units = float(adhoc_amount / adhoc_price)
        units_held += adhoc_units
        cursor.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
            VALUES (1, %s, 'buy', %s, %s, %s)
        """, (adhoc_dt, float(adhoc_amount), float(adhoc_price), float(adhoc_units)))

        # Update final inv 1
        cursor.execute("""
            UPDATE investments SET unit_price = %s, number_of_units_held = %s, total_fees_paid = %s, total_dividends_received = %s
            WHERE id = 1
        """, (float(price), float(units_held), float(total_fees), float(total_divs)))


        # Investment 2: PSG Balanced Fund (Initial lump sum + Monthly SIP + Partial Withdrawal)
        inv2_start = date(2020, 6, 1)
        inv2_dates = pd.date_range(start='2020-06-01', end=today_date, freq='ME').date
        price2 = 80.0
        units_held2 = 0.0
        total_fees2 = 0.0

        # Initial lump sum
        lump2 = 50000.0
        units2 = lump2 / price2
        units_held2 += units2
        cursor.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
            VALUES (%s, %s, 'buy', %s, %s, %s)
        """, (2, inv2_start, float(lump2), float(price2), float(units2)))

        for dt in inv2_dates:
            shock = float(np.random.normal(0.006, 0.02))
            price2 = float(max(65.0, price2 * (1 + shock)))
            cursor.execute("""
                INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                VALUES (%s, %s, %s, 0.0, 0.0)
                ON CONFLICT (investment_id, unit_price_date) DO UPDATE SET unit_price = EXCLUDED.unit_price
            """, (2, dt, float(price2)))

            m_amt = 3000.0
            m_u = m_amt / price2
            units_held2 += m_u
            cursor.execute("""
                INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
                VALUES (%s, %s, 'buy', %s, %s, %s)
            """, (2, dt, float(m_amt), float(price2), float(m_u)))

        # Partial withdrawal in Nov 2023
        w_dt = date(2023, 11, 20)
        w_amt = 20000.0
        w_units = w_amt / price2
        units_held2 -= w_units
        cursor.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
            VALUES (%s, %s, 'sell', %s, %s, %s)
        """, (2, w_dt, float(w_amt), float(price2), float(w_units)))

        cursor.execute("""
            UPDATE investments SET unit_price = %s, number_of_units_held = %s WHERE id = 2
        """, (float(price2), float(units_held2)))


        # Investment 3 & 5: Satrix Top 40 ETF + Switch into Satrix MSCI World ETF
        inv3_start = date(2021, 3, 10)
        inv3_dates = pd.date_range(start='2021-03-10', end=today_date, freq='ME').date
        price3 = 60.0
        units_held3 = 0.0

        # Initial lump sum
        lump3 = 25000.0
        u3 = lump3 / price3
        units_held3 += u3
        cursor.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
            VALUES (%s, %s, 'buy', %s, %s, %s)
        """, (3, inv3_start, float(lump3), float(price3), float(u3)))

        for dt in inv3_dates:
            shock = float(np.random.normal(0.007, 0.028))
            price3 = float(max(45.0, price3 * (1 + shock)))
            cursor.execute("""
                INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                VALUES (%s, %s, %s, 0.0, 0.0)
                ON CONFLICT (investment_id, unit_price_date) DO UPDATE SET unit_price = EXCLUDED.unit_price
            """, (3, dt, float(price3)))

            m_amt = 1500.0
            m_u = m_amt / price3
            units_held3 += m_u
            cursor.execute("""
                INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
                VALUES (%s, %s, 'buy', %s, %s, %s)
            """, (3, dt, float(m_amt), float(price3), float(m_u)))

        # Perform Investment Switch on 2024-01-15: Switch 300 units out of STX40 into STXWDM
        switch_dt = date(2024, 1, 15)
        switch_units = 300.0
        switch_amt = float(switch_units * price3)
        units_held3 -= switch_units

        # Switch Out transaction on Inv 3
        cursor.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
            VALUES (%s, %s, 'switch_out', %s, %s, %s)
        """, (3, switch_dt, float(switch_amt), float(price3), float(switch_units)))

        # Switch In transaction on Inv 5 (Satrix MSCI World ETF)
        price5 = 75.0
        units_held5 = float(switch_amt / price5)
        cursor.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
            VALUES (%s, %s, 'switch_in', %s, %s, %s)
        """, (5, switch_dt, float(switch_amt), float(price5), float(units_held5)))

        inv5_dates = pd.date_range(start='2024-01-15', end=today_date, freq='ME').date
        for dt in inv5_dates:
            shock = float(np.random.normal(0.009, 0.022))
            price5 = float(max(60.0, price5 * (1 + shock)))
            cursor.execute("""
                INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                VALUES (%s, %s, %s, 0.0, 0.0)
                ON CONFLICT (investment_id, unit_price_date) DO UPDATE SET unit_price = EXCLUDED.unit_price
            """, (5, dt, float(price5)))

        cursor.execute("""
            UPDATE investments SET unit_price = %s, number_of_units_held = %s WHERE id = 3
        """, (float(price3), float(units_held3)))
        cursor.execute("""
            UPDATE investments SET unit_price = %s, number_of_units_held = %s WHERE id = 5
        """, (float(price5), float(units_held5)))


        # Investment 4: AF Global Equity (Offshore USD)
        inv4_start = date(2022, 1, 10)
        inv4_dates = pd.date_range(start='2022-01-10', end=today_date, freq='ME').date
        price4 = 120.0
        units_held4 = 0.0

        lump4 = 10000.0  # USD
        u4 = lump4 / price4
        units_held4 += u4
        cursor.execute("""
            INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
            VALUES (%s, %s, 'buy', %s, %s, %s)
        """, (4, inv4_start, float(lump4), float(price4), float(u4)))

        for dt in inv4_dates:
            shock = float(np.random.normal(0.008, 0.025))
            price4 = float(max(90.0, price4 * (1 + shock)))
            cursor.execute("""
                INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                VALUES (%s, %s, %s, 0.0, 0.0)
                ON CONFLICT (investment_id, unit_price_date) DO UPDATE SET unit_price = EXCLUDED.unit_price
            """, (4, dt, float(price4)))

        cursor.execute("""
            UPDATE investments SET unit_price = %s, number_of_units_held = %s WHERE id = 4
        """, (float(price4), float(units_held4)))

        conn.commit()

    # 4. Data Integrity Verification
    print("Verifying seeded data integrity...")
    with get_db_connection(db_name) as (conn, cursor):
        cursor.execute("SELECT id, investment_name, number_of_units_held FROM investments WHERE investment_type != 'Forex'")
        invs = cursor.fetchall()
        for inv_id, name, held in invs:
            cursor.execute("""
                SELECT COALESCE(SUM(CASE WHEN LOWER(transaction_type) IN ('buy', 'switch_in') THEN number_of_units
                                         WHEN LOWER(transaction_type) IN ('sell', 'switch_out') THEN -number_of_units
                                         ELSE 0 END), 0)
                FROM transactions WHERE investment_id = %s
            """, (inv_id,))
            txn_units = cursor.fetchone()[0]
            diff = abs(held - txn_units)
            if diff > 1e-4:
                raise ValueError(f"Integrity check failed for {name} (ID {inv_id}): held={held}, txn={txn_units}")
            print(f"  ✓ {name} (ID {inv_id}): Reconciled {held:.4f} units successfully.")

    # 5. Run Metrics Calculation & Portfolio Aggregation
    print("Calculating investment metrics and aggregating portfolio...")
    calculate_all_investment_metrics(db_name)
    update_portfolio_aggregation(db_name)

    print("=" * 60)
    print("✅ Phase 0 Completed: Seeded clean, realistic, multi-year test state.")
    print("=" * 60)

if __name__ == "__main__":
    seed_database()
