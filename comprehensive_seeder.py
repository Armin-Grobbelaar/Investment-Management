import os
import psycopg2
from datetime import date, timedelta
import random

DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "changeme")
DB_PORT = int(os.environ.get("POSTGRES_PORT", 5432))
INV_DB = "Investments"
USERS_DB = "Users"

def run_seed():
    print("Wiping and reseeding...")
    # Wipe DBs
    conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, dbname="postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {INV_DB}")
    cur.execute(f"DROP DATABASE IF EXISTS {USERS_DB}")
    cur.execute(f"CREATE DATABASE {INV_DB}")
    cur.execute(f"CREATE DATABASE {USERS_DB}")
    cur.close()
    conn.close()

    # Recreate tables (import from existing create_tables.py)
    from investment_backend.create_tables import create_tables
    create_tables(INV_DB)
    create_tables(USERS_DB)
    
    # Populate user
    conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, dbname=USERS_DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, email, password_hash) VALUES ('tester', 'test@example.com', 'hashed_pwd')")
    conn.commit()
    cur.close()
    conn.close()

    # Populate investment data
    conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT, dbname=INV_DB)
    cur = conn.cursor()
    
    # Investment 1: Lump sum + monthly + growth
    cur.execute("""INSERT INTO investments (institution_name, initial_investment_date, investment_type, investment_name, investment_ticker, unit_currency, initial_unit_price, unit_price, number_of_units_held, total_dividends_received, total_tax_paid, total_fees_paid, investment_fee, investment_status) 
                   VALUES ('Bank A', '2022-01-01', 'ETF', 'Broad Market ETF', 'ETF1', 'ZAR', 100, 150, 1000, 0, 0, 0, 0.01, 'Active') RETURNING id""")
    inv1_id = cur.fetchone()[0]
    
    # Transactions (1000 units total)
    # Lump sum
    cur.execute("INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units) VALUES (%s, '2022-01-01', 'buy', 100000, 100, 1000)", (inv1_id,))
    # Monthly
    for m in range(24):
        t_date = date(2022, 1, 1) + timedelta(days=m*30)
        cur.execute("INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units) VALUES (%s, %s, 'buy', 5000, 120, 41.66)", (inv1_id, t_date))
    
    # Investment 2: Switch case (Switch out of INV1 to INV2)
    cur.execute("""INSERT INTO investments (institution_name, initial_investment_date, investment_type, investment_name, investment_ticker, unit_currency, initial_unit_price, unit_price, number_of_units_held, total_dividends_received, total_tax_paid, total_fees_paid, investment_fee, investment_status) 
                   VALUES ('Bank B', '2023-06-01', 'Unit Trust', 'Tech Fund', 'TECH', 'ZAR', 10, 15, 2000, 0, 0, 0, 0.02, 'Active') RETURNING id""")
    inv2_id = cur.fetchone()[0]
    # Switch out of INV1
    cur.execute("INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units) VALUES (%s, '2023-06-01', 'sell', 20000, 150, 133.33)", (inv1_id,))
    # Switch into INV2
    cur.execute("INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units) VALUES (%s, '2023-06-01', 'buy', 20000, 10, 2000)", (inv2_id,))

    conn.commit()
    print("Seed complete.")

if __name__ == "__main__":
    run_seed()
