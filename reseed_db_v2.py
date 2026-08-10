import os
import json
import random
import psycopg2
from datetime import date, timedelta
import math

DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "changeme")
DB_PORT = int(os.environ.get("POSTGRES_PORT", 5432))
DB_NAME = os.environ.get("INVESTMENTS_DB", "Investments")

def wipe_and_reseed():
    print("Wiping and reseeding database...")
    try:
        conn = psycopg2.connect(host=DB_HOST, database="postgres", user=DB_USER, password=DB_PASSWORD, port=DB_PORT)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
        cur.execute(f"CREATE DATABASE {DB_NAME}")
        conn.commit()
        cur.close()
        conn.close()
        print("Database wiped and created.")

        # Create tables
        from investment_backend.create_tables import create_tables
        create_tables(DB_NAME)
        print("Tables created.")

        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)
        cur = conn.cursor()
        cur.execute("SET session_replication_role = 'replica'")
        for table in ["unit_prices", "transactions", "dividends", "fees", "tax", "returns",
                       "investment_metrics", "portfolio_metrics", "predictions", "prediction_accuracy",
                       "property_investments", "factsheets", "investment_source_meta"]:
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
        cur.execute("TRUNCATE TABLE investments RESTART IDENTITY CASCADE")
        cur.execute("SET session_replication_role = 'origin'")
        conn.commit()

        # Add test user
        user_conn = psycopg2.connect(host=DB_HOST, database="Users", user=DB_USER, password=DB_PASSWORD, port=DB_PORT)
        user_cur = user_conn.cursor()
        user_cur.execute("INSERT INTO users (username, email, password_hash) VALUES ('admin', 'admin@example.com', 'hashed') ON CONFLICT DO NOTHING")
        user_conn.commit()
        user_conn.close()

        # Seed investments
        investments = [
            ("Allan Gray", "AG Equity Fund", "AGEF", "Unit Trust", "ZAR", "2021-01-15", 150.00, 200.00, 1000, 0.02, "Active"),
            ("PSG Wealth", "PSG Balanced Fund", "PSGBF", "Unit Trust", "ZAR", "2020-06-01", 100.00, 140.00, 500, 0.015, "Active"),
            ("Standard Bank", "Satrix Top 40 ETF", "STX40", "ETF", "ZAR", "2022-03-10", 80.00, 110.00, 1500, 0.002, "Active"),
            ("Alexander Forbes", "AF Global Equity", "AFGE", "Unit Trust", "USD", "2021-08-20", 120.00, 150.00, 300, 0.012, "Active"),
            ("Discretionary", "Tech Growth Stock", "TGS", "Equity", "ZAR", "2023-01-01", 100.00, 95.00, 200, 0.005, "Active"),
            ("Retirement Annuity", "Sanlam Wealth Fund", "SWF", "Unit Trust", "ZAR", "2019-01-01", 50.00, 90.00, 5000, 0.008, "Active")
        ]

        inv_ids = {}
        for inv in investments:
            inst, name, ticker, typ, curr, inv_date, p_init, p_curr, units, fee, status = inv
            cur.execute("""
                INSERT INTO investments (institution_name, initial_investment_date, investment_type, investment_name, investment_ticker, unit_currency, initial_unit_price, unit_price, number_of_units_held, total_dividends_received, total_tax_paid, total_fees_paid, investment_fee, investment_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, %s, %s) RETURNING id
            """, (inst, inv_date, typ, name, ticker, curr, p_init, p_curr, units, fee, status))
            inv_id = cur.fetchone()[0]
            inv_ids[ticker] = inv_id

            # Generate realistic unit prices over 3 years
            start_date = date(2023, 1, 1)
            current_price = p_init
            for i in range(3 * 30): # Sparse data for realism
                day = start_date + timedelta(days=i*3)
                if day > date.today(): break
                change = random.gauss(0.0002, 0.015) * current_price
                current_price += change
                if current_price < 10: current_price = 10
                
                # Update investment current price at the end
                if i == 3 * 30 - 1 or day == date.today():
                    cur.execute("UPDATE investments SET unit_price = %s WHERE id = %s", (current_price, inv_id))
                
                cur.execute("""
                    INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                    VALUES (%s, %s, %s, %s, %s)
                """, (inv_id, day, current_price, change, change/current_price if current_price != 0 else 0))
        
        # Seed transactions
        for ticker, inv_id in inv_ids.items():
            base_amount = random.uniform(5000, 20000)
            total_units_bought = 0.0
            for i in range(10):
                t_date = date(2023, 1, 1) + timedelta(days=i*90)
                if t_date > date.today(): break
                
                # Fetch exact or nearest previous unit price for transaction date
                cur.execute("""
                    SELECT unit_price FROM unit_prices 
                    WHERE investment_id = %s AND unit_price_date <= %s 
                    ORDER BY unit_price_date DESC LIMIT 1
                """, (inv_id, t_date))
                res = cur.fetchone()
                price_on_date = float(res[0]) if res else float(p_init)
                units = base_amount / price_on_date
                total_units_bought += units

                cur.execute("""
                    INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
                    VALUES (%s, %s, 'buy', %s, %s, %s)
                """, (inv_id, t_date, base_amount, price_on_date, units))

            # Update investments table with actual total units held
            cur.execute("""
                UPDATE investments SET number_of_units_held = %s WHERE id = %s
            """, (total_units_bought, inv_id))

            # Seed some dividends
            for i in range(4):
                d_date = date(2023, 3 + i*3, 15)
                if d_date > date.today(): break
                div_amount = random.uniform(50, 500)
                cur.execute("""
                    INSERT INTO dividends (investment_id, dividend_date, dividend_frequency, dividend_recieved, dividend_percentage)
                    VALUES (%s, %s, 4, %s, %s)
                """, (inv_id, d_date, div_amount, 0.02))

        conn.commit()
        cur.close()
        conn.close()
        print("Realistic test data seeded.")

    except Exception as e:
        print(f"Reseed failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    wipe_and_reseed()
