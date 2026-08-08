"""
Import Module

Functions for importing data from CSV files.
"""

import os
import pandas as pd
import psycopg2
from .database import get_db_connection, DEFAULT_DB


def import_unit_prices_csv(file_name, investment_name):
    """
    Import unit prices from CSV file for a specific investment.

    Expected CSV format:
    date,unit_price
    2024-01-01,100.50
    2024-01-02,101.25
    ...
    """
    try:
        # Read CSV file
        df = pd.read_csv(file_name)
        df['date'] = pd.to_datetime(df['date'])

        # Get investment ID
        with get_db_connection(DEFAULT_DB) as (conn, cursor):
            cursor.execute("SELECT id FROM investments WHERE investment_name = %s", (investment_name,))
            res = cursor.fetchone()
            if not res:
                raise ValueError(f"Investment '{investment_name}' not found")

            investment_id = res[0]

            # Insert unit prices
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (investment_id, unit_price_date) DO UPDATE SET
                        unit_price = EXCLUDED.unit_price,
                        unit_price_change = EXCLUDED.unit_price_change,
                        percentage_unit_price_change = EXCLUDED.percentage_unit_price_change
                """, (investment_id, row['date'], row['unit_price'], 0.0, 0.0))

            conn.commit()

        print(f"Successfully imported {len(df)} unit prices for {investment_name}")

    except Exception as e:
        print(f"Error importing unit prices: {e}")
        raise


def import_csv_data(file_name, data_type, investment_name):
    """
    Import various types of CSV data (transactions, returns, dividends, fees, tax).

    Expected format depends on data_type:
    - transactions: date,type,amount,number_of_units
    - returns: date,return_amount
    - dividends: date,dividend_amount
    - fees: date,fee_amount
    - tax: date,tax_amount
    """
    try:
        # Read CSV file
        df = pd.read_csv(file_name)
        df['date'] = pd.to_datetime(df['date'])

        # Get investment ID
        with get_db_connection(DEFAULT_DB) as (conn, cursor):
            cursor.execute("SELECT id FROM investments WHERE investment_name = %s", (investment_name,))
            res = cursor.fetchone()
            if not res:
                raise ValueError(f"Investment '{investment_name}' not found")

            investment_id = res[0]

            # Insert based on data type
            if data_type == 'transactions':
                for _, row in df.iterrows():
                    cursor.execute("""
                        INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (investment_id, row['date'], row['type'], row['amount'], 0.0, row['number_of_units']))

            elif data_type == 'returns':
                for _, row in df.iterrows():
                    cursor.execute("""
                        INSERT INTO returns (investment_id, return_date, return_amount)
                        VALUES (%s, %s, %s)
                    """, (investment_id, row['date'], row['return_amount']))

            elif data_type == 'dividends':
                for _, row in df.iterrows():
                    cursor.execute("""
                        INSERT INTO dividends (investment_id, dividend_date, dividend_recieved)
                        VALUES (%s, %s, %s)
                    """, (investment_id, row['date'], row['dividend_amount']))

            elif data_type == 'fees':
                for _, row in df.iterrows():
                    cursor.execute("""
                        INSERT INTO fees (investment_id, fee_date, fee_paid)
                        VALUES (%s, %s, %s)
                    """, (investment_id, row['date'], row['fee_amount']))

            elif data_type == 'tax':
                for _, row in df.iterrows():
                    cursor.execute("""
                        INSERT INTO tax (investment_id, tax_date, tax_paid)
                        VALUES (%s, %s, %s)
                    """, (investment_id, row['date'], row['tax_amount']))

            conn.commit()

        print(f"Successfully imported {len(df)} {data_type} records for {investment_name}")

    except Exception as e:
        print(f"Error importing {data_type}: {e}")
        raise


def import_mixed_csv_data(file_name, investment_name):
    """
    Import mixed CSV data containing multiple data types in one file.
    Expected columns: date,type,amount (type can be 'transaction', 'dividend', 'fee', 'tax')
    """
    try:
        # Read CSV file
        df = pd.read_csv(file_name)
        df['date'] = pd.to_datetime(df['date'])

        # Get investment ID
        with get_db_connection(DEFAULT_DB) as (conn, cursor):
            cursor.execute("SELECT id FROM investments WHERE investment_name = %s", (investment_name,))
            res = cursor.fetchone()
            if not res:
                raise ValueError(f"Investment '{investment_name}' not found")

            investment_id = res[0]

            # Process each row based on type
            for _, row in df.iterrows():
                row_type = row['type'].lower()

                if row_type in ['buy', 'sell', 'transaction']:
                    cursor.execute("""
                        INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (investment_id, row['date'], row['type'], row['amount'], 0.0, 0))

                elif row_type == 'dividend':
                    cursor.execute("""
                        INSERT INTO dividends (investment_id, dividend_date, dividend_recieved)
                        VALUES (%s, %s, %s)
                    """, (investment_id, row['date'], row['amount']))

                elif row_type == 'fee':
                    cursor.execute("""
                        INSERT INTO fees (investment_id, fee_date, fee_paid)
                        VALUES (%s, %s, %s)
                    """, (investment_id, row['date'], row['amount']))

                elif row_type == 'tax':
                    cursor.execute("""
                        INSERT INTO tax (investment_id, tax_date, tax_paid)
                        VALUES (%s, %s, %s)
                    """, (investment_id, row['date'], row['amount']))

            conn.commit()

        print(f"Successfully imported {len(df)} mixed records for {investment_name}")

    except Exception as e:
        print(f"Error importing mixed data: {e}")
        raise


def import_inflation_csv_data(file_name):
    """
    Import inflation data from CSV file.
    Expected format: year,inflation_rate,country
    """
    try:
        # Read CSV file
        df = pd.read_csv(file_name)

        with get_db_connection(DEFAULT_DB) as (conn, cursor):
            # Insert inflation data
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO inflation (inflation_date, inflation_rate, country)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (inflation_date, country) DO UPDATE SET
                        inflation_rate = EXCLUDED.inflation_rate
                """, (f"{row['year']}-01-01", row['inflation_rate'], row.get('country', 'South Africa')))

            conn.commit()

        print(f"Successfully imported {len(df)} inflation records")

    except Exception as e:
        print(f"Error importing inflation data: {e}")
        raise
