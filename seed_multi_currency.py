import os
import sys
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'investment_backend'))
from modules.database import get_db_connection, DEFAULT_DB, USERS_DB
from create_tables import drop_all_tables, create_tables

def seed_database():
    print("=" * 60)
    print("Phase 0: Database Reset & Multi-Currency Seeding")
    print("=" * 60)

    db_name = DEFAULT_DB
    users_db = USERS_DB

    # 1. Reset
    print("Dropping and recreating tables...")
    drop_all_tables(db_name)
    drop_all_tables(users_db)
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

    # 3. Seed Investments (ZAR, USD, GBP, EUR)
    print("Seeding multi-currency investment portfolio...")
    with get_db_connection(db_name) as (conn, cursor):
        investments_data = [
            {"id": 1, "name": "ZAR Equity Fund", "ticker": "ZAR_EQ", "currency": "ZAR", "type": "Unit Trust"},
            {"id": 2, "name": "USD Global Tech", "ticker": "USD_TECH", "currency": "USD", "type": "ETF"},
            {"id": 3, "name": "GBP Income Fund", "ticker": "GBP_INC", "currency": "GBP", "type": "Unit Trust"},
            {"id": 4, "name": "EUR Bond Fund", "ticker": "EUR_BOND", "currency": "EUR", "type": "Bond Fund"}
        ]
        
        for inv in investments_data:
            cursor.execute("""
                INSERT INTO investments (
                    id, institution_name, initial_investment_date, investment_type,
                    investment_name, investment_ticker, unit_currency, initial_unit_price,
                    unit_price, number_of_units_held, total_dividends_received, total_tax_paid,
                    total_fees_paid, investment_fee, investment_status
                ) VALUES (%s, 'Allan Gray', '2021-01-01', %s, %s, %s, %s, 100.0, 150.0, 1000.0, 0.0, 0.0, 0.0, 0.005, 'Active')
                ON CONFLICT (id) DO UPDATE SET unit_price = EXCLUDED.unit_price
            """, (inv["id"], inv["type"], inv["name"], inv["ticker"], inv["currency"]))
        
        # Add a few forex investments for conversions
        fx_data = [
            (10, "USDZAR=X", "USD/ZAR Rate", "ZAR", 18.5),
            (11, "GBPZAR=X", "GBP/ZAR Rate", "ZAR", 23.2),
            (12, "EURZAR=X", "EUR/ZAR Rate", "ZAR", 20.1)
        ]
        for fid, ticker, name, cur, price in fx_data:
            cursor.execute("""
                INSERT INTO investments (
                    id, institution_name, initial_investment_date, investment_type,
                    investment_name, investment_ticker, unit_currency, initial_unit_price,
                    unit_price, number_of_units_held, total_dividends_received, total_tax_paid,
                    total_fees_paid, investment_fee, investment_status
                ) VALUES (%s, 'Forex', '2020-01-01', 'Forex', %s, %s, %s, %s, %s, 1.0, 0.0, 0.0, 0.0, 0.0, 'Active')
                ON CONFLICT (id) DO UPDATE SET unit_price = EXCLUDED.unit_price
            """, (fid, name, ticker, cur, price*0.8, price))

        conn.commit()
    print("✅ Phase 0 Completed: Database reset and multi-currency data seeded.")

if __name__ == "__main__":
    seed_database()
