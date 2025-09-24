#!/usr/bin/env python3

import os
import psycopg2

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme")
INVESTMENTS_DB = os.getenv("INVESTMENTS_DB", "Investments")
USERS_DB = os.getenv("USERS_DB", "Users")

def create_tables(db_name):
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=db_name,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        port=5432
    )
    cursor = conn.cursor()

    # Investments tables
    if db_name == INVESTMENTS_DB:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            id BIGSERIAL NOT NULL PRIMARY KEY,
            institution_name VARCHAR(200) NOT NULL,
            initial_investment_date DATE NOT NULL,
            investment_type VARCHAR(50) NOT NULL,
            investment_name VARCHAR(200),
            investment_ticker VARCHAR(50) NOT NULL UNIQUE,
            unit_currency VARCHAR(5) NOT NULL,
            initial_unit_price float8 NOT NULL,
            unit_price float8 NOT NULL,
            number_of_units_held float8 NOT NULL,
            total_dividends_received float8 NOT NULL,
            total_tax_paid float8 NOT NULL,
            total_fees_paid float8 NOT NULL,
            investment_fee float8 NOT NULL,
            investment_status VARCHAR(20) NOT NULL
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS unit_prices (
            id BIGINT NOT NULL REFERENCES investments(id),
            unit_price_date DATE NOT NULL,
            unit_price float8 NOT NULL,
            unit_price_change float8 NOT NULL,
            percentage_unit_price_change float8 NOT NULL
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS returns (
            id BIGINT NOT NULL REFERENCES investments(id),
            returns_date DATE NOT NULL,
            monthly_return float8 NOT NULL,
            quarterly_return float8 NOT NULL,
            half_yearly_return float8 NOT NULL,
            yearly_return float8 NOT NULL,
            yearly_3_return float8 NOT NULL,
            yearly_5_return float8 NOT NULL,
            return_since_inception float8 NOT NULL
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id BIGINT NOT NULL REFERENCES investments(id),
            transaction_date DATE NOT NULL,
            transaction_type VARCHAR(20) NOT NULL,
            transaction_amount float8 NOT NULL,
            unit_price float8 NOT NULL,
            number_of_units float8 NOT NULL
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dividends (
            id BIGINT NOT NULL REFERENCES investments(id),
            dividend_date DATE NOT NULL,
            dividend_frequency int NOT NULL,
            dividend_recieved float8 NOT NULL,
            dividend_percentage float8 NOT NULL
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fees (
            id BIGINT NOT NULL REFERENCES investments(id),
            fee_date DATE NOT NULL,
            fee_type VARCHAR(50) NOT NULL,
            fee_paid float8 NOT NULL,
            fee_frequency float8 NOT NULL,
            number_of_units float8 NOT NULL,
            investment_fee float8 NOT NULL
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tax (
            id BIGINT NOT NULL REFERENCES investments(id),
            tax_date DATE NOT NULL,
            tax_type VARCHAR(50) NOT NULL,
            tax_paid float8 NOT NULL,
            tax_percentage float8 NOT NULL
        )""")

    # Users table
    if db_name == USERS_DB:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(200) NOT NULL UNIQUE,
            password_hash VARCHAR(200) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Tables created in {db_name} database")

if __name__ == "__main__":
    create_tables(INVESTMENTS_DB)
    create_tables(USERS_DB)