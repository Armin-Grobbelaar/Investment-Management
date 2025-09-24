#!/usr/bin/env python3

import math
import locale
import random
import smtplib
import psycopg2
import requests
import numpy as np
import pandas as pd
import yfinance as yf
#from fpdf import FPDF
from datetime import date
#import mplfinance as mpf
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine
from email.message import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.platypus.tables import Table
from psycopg2.extensions import AsIs, ISOLATION_LEVEL_AUTOCOMMIT

def add_user(name, surname):
    database_connection = psycopg2.connect(host = "ThinkTank", database = "postgres", user = "postgres", password = "changeme", port=5432)
    database_connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    database_cursor = database_connection.cursor()
    database_name = name.lower() + "_investment_database"
    database_cursor.execute("CREATE database %s", (AsIs(database_name), ))
    database_connection.commit()
    database_cursor.close()
    database_connection.close()

    user_database_connection = psycopg2.connect(host = "ThinkTank", database = "Users", user = "postgres", password = "changeme", port=5432)
    user_database_cursor = user_database_connection.cursor()
    user_database_cursor.execute("INSERT INTO users (name, surname, database_name) VALUES (%s, %s, %s)", (name, surname, database_name))
    user_database_connection.commit()
    user_database_cursor.close()
    user_database_connection.close()

    investment_database_connection = psycopg2.connect(host = "ThinkTank", database = database_name, user = "postgres", password = "changeme", port=5432)
    investment_database_cursor.execute("CREATE TABLE investments (id BIGSERIAL NOT NULL PRIMARY KEY, institution_name VARCHAR(200) NOT NULL, initial_investment_date DATE NOT NULL, investment_type VARCHAR(50) NOT NULL, investment_name VARCHAR(200), investment_ticker VARCHAR(50) NOT NULL UNIQUE, unit_currency VARCHAR(5) NOT NULL, initial_unit_price float8 NOT NULL, unit_price float8 NOT NULL, number_of_units_held float8 NOT NULL, total_dividends_received float8 NOT NULL, total_tax_paid float8 NOT NULL, total_fees_paid float8 NOT NULL, investment_fee float8 NOT NULL, investment_status VARCHAR(20) NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE unit_prices (id BIGINT NOT NULL REFERENCES investments(id), unit_price_date DATE NOT NULL, unit_price float8 NOT NULL, unit_price_change float8 NOT NULL, percentage_unit_price_change float8 NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE returns (id BIGINT NOT NULL REFERENCES investments(id), returns_date DATE NOT NULL, monthly_return float8 NOT NULL, quarterly_return float8 NOT NULL, half_yearly_return float8 NOT NULL, yearly_return float8 NOT NULL, yearly_3_return float8 NOT NULL, yearly_5_return float8 NOT NULL, return_since_inception float8 NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE transactions (id BIGINT NOT NULL REFERENCES investments(id), transaction_date DATE NOT NULL, transaction_type VARCHAR(20) NOT NULL, transaction_amount float8 NOT NULL, unit_price float8 NOT NULL, number_of_units float8 NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE dividends (id BIGINT NOT NULL REFERENCES investments(id), dividend_date DATE NOT NULL, dividend_frequency int NOT NULL, dividend_recieved float8 NOT NULL, dividend_percentage float8 NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE fees (id BIGINT NOT NULL REFERENCES investments(id), fee_date DATE NOT NULL, fee_type VARCHAR(50), fee_paid float8 NOT NULL, fee_frequency float8 NOT  NULL, number_of_units float8 NOT NULL, investment_fee float8 NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE tax (id BIGINT NOT NULL REFERENCES investments(id), tax_date DATE NOT NULL, tax_paid float8 NOT NULL, tax_percentage float8 NOT NULL)")
    investment_database_cursor.close()
    investment_database_connection.close()


def create_connection(database_name):
    global investment_database_connection
    global foreign_currency
    global native_currency
    global investment_database_cursor

    investment_database_connection = psycopg2.connect(host = "ThinkTank", database = database_name, user = "postgres", password = "changeme", port=5432)

    currency_symbols = [("R", "ZAR"), ("€", "EUR"), ("£", "GBP"), ("$", "USD")]
    foreign_currency = pd.DataFrame(currency_symbols, columns= ["Symbol", "Currency"])
    native_currency = "R"
    investment_database_cursor = investment_database_connection.cursor()

def add_investment(
    database_name: str,
    institution_name: str,
    initial_investment_date: str,
    investment_type: str,
    investment_name: str,
    investment_ticker: str,
    unit_currency: str,
    initial_unit_price: float,
    unit_price: float,
    number_of_units_held: float,
    total_dividends_received: float,
    total_tax_paid: float,
    total_fees_paid: float,
    investment_fee: float,
    investment_status: str
):
    # Helper functions
    def get_currency_code():
        return f"{foreign_currency.loc[foreign_currency['Symbol'] == unit_currency, 'Currency'].values[0]}/{foreign_currency.loc[foreign_currency['Symbol'] == native_currency, 'Currency'].values[0]}"

    def get_currency_ticker():
        return f"{foreign_currency.loc[foreign_currency['Symbol'] == unit_currency, 'Currency'].values[0]}{foreign_currency.loc[foreign_currency['Symbol'] == native_currency, 'Currency'].values[0]}=X"

    def execute_insert_investment_query(params):
        query = """
            INSERT INTO investments (institution_name, initial_investment_date, investment_type, 
            investment_name, investment_ticker, unit_currency, initial_unit_price, unit_price, 
            number_of_units_held, total_dividends_received, total_tax_paid, total_fees_paid, investment_fee, investment_status) 
            VALUES (%s, DATE %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """
        investment_database_cursor.execute(query, params)
        return float(investment_database_cursor.fetchone()[0])

    def insert_transaction(investment_id):
        investment_database_cursor.execute(
            "INSERT INTO transactions (id, transaction_date, transaction_type,  transaction_amount, unit_price, number_of_units) VALUES (%s, DATE %s, %s, %s, %s, %s)",
            (investment_id, initial_investment_date, "Buy", initial_unit_price * number_of_units_held, unit_price, number_of_units_held)
        )

    def insert_unit_price(investment_id):
        investment_database_cursor.execute(
            "INSERT INTO unit_prices (id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) VALUES (%s, DATE %s, %s, %s, %s)",
            (investment_id, initial_investment_date, unit_price, 0, 0)
        )

    def fetch_and_store_historical_data(investment_ticker, investment_id):
        try:
            ticker = yf.Ticker(investment_ticker)
            ticker_data = ticker.history(period="max")
            ticker_data.reset_index(inplace=True)

            # Prepare historical data for database
            investment_unit_prices = pd.DataFrame(columns=["unit_price_date", "unit_price"])
            investment_unit_prices[["unit_price_date", "unit_price"]] = ticker_data[["Date", "Close"]]
            investment_unit_prices["unit_price_date"] = pd.to_datetime(investment_unit_prices["unit_price_date"])
            investment_unit_prices.drop_duplicates("unit_price_date", inplace=True)
            investment_unit_prices = (investment_unit_prices.set_index("unit_price_date").reindex(pd.date_range(investment_unit_prices["unit_price_date"].min(), investment_unit_prices["unit_price_date"].max(), freq="D")).rename_axis(["unit_price_date"]).reset_index())
            investment_unit_prices.ffill(inplace=True)
            investment_unit_prices["unit_price_change"] = investment_unit_prices["unit_price"] - investment_unit_prices["unit_price"].shift(1)
            investment_unit_prices.at[0, "unit_price_change"] = 0
            investment_unit_prices["percentage_unit_price_change"] = (investment_unit_prices["unit_price_change"]/investment_unit_prices["unit_price"].shift(1))*100
            investment_unit_prices.at[0, "percentage_unit_price_change"] = 0
            investment_unit_prices.insert(0, "id", investment_id)

            if ticker.info.get("currency") == "ZAc":
                investment_unit_prices["unit_price"] /= 100

            # Save to database
            investment_database_url = "postgresql://postgres:changeme@localhost:5432/" + database_name
            engine = create_engine(investment_database_url)

            # Insert historical data into unit_prices
            investment_unit_prices.to_sql("unit_prices", engine, index=False, if_exists="append", method="multi")

            # Update investment price (if necessary)
            unit_price = float(investment_unit_prices.iloc[-1]["unit_price"])
            investment_database_cursor.execute("UPDATE investments SET unit_price = %s WHERE id = %s", (unit_price, investment_id))
            investment_database_connection.commit()

            print(f"Historical data for {investment_ticker} successfully imported.")
        except Exception as e:
            print("Could not import historical data:", str(e))

    # Main function logic
    currency_ticker = get_currency_ticker()
    currency_name = get_currency_code()
    
    # Fetch existing investments
    investment_database_cursor.execute("SELECT id, institution_name, investment_name, unit_currency, investment_type FROM investments")
    investments = pd.DataFrame(investment_database_cursor.fetchall(), columns=["id", "institution_name", "investment_name", "unit_currency", "investment_type"])

    # Check if investment already exists
    if institution_name in investments["institution_name"].values and investment_name in investments["investment_name"].values:
        print(f"Investment '{investment_name}' from '{institution_name}' already exists.")
        return
    
    # Insert the investment first
    params = (institution_name, initial_investment_date, investment_type, investment_name, investment_ticker, unit_currency, initial_unit_price, unit_price, number_of_units_held, total_dividends_received, total_tax_paid, total_fees_paid, investment_fee, investment_status)
    investment_id = execute_insert_investment_query(params)
    investment_database_connection.commit()
    # Insert transaction and initial unit price
    insert_transaction(investment_id)
    insert_unit_price(investment_id)
    print(f"Added investment '{investment_name}' with ID {investment_id}.")
    
    # Fetch and store historical data
    fetch_and_store_historical_data(investment_ticker, investment_id)

    # Check for existing forex entry before adding new forex data
    forex_exists = (
        investments[(investments["investment_type"] == "Forex") & (investments["unit_currency"] == unit_currency)]
    ).shape[0] > 0

    if unit_currency != native_currency and not forex_exists:
        forex_params = (
            institution_name,
            initial_investment_date,
            "Forex",
            currency_name,
            currency_ticker,
            unit_currency,
            initial_unit_price,
            unit_price,
            0,
            0,
            0,
            0,
            0,
            "Active"
        )
        forex_id = execute_insert_investment_query(forex_params)
        investment_database_connection.commit()
        # Insert forex unit prices
        insert_unit_price(forex_id)
        print(f"Added forex entry for '{currency_name}' with ID {forex_id}.")
        
        # Fetch and store forex historical data
        fetch_and_store_historical_data(currency_ticker, forex_id)
    else:
        print("Forex entry already exists or is not needed.")
    
    investment_database_connection.commit()


def add_transaction(investment_name, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units, include_fees, fees_paid, include_tax, tax_paid):
    if (number_of_units < 0 and include_tax == True):
        investment_database_cursor.execute("SELECT id, total_tax_paid FROM investments WHERE investment_name = %s", (investment_name, ))
        investment_id, previous_tax_paid = investment_database_cursor.fetchone()    
        tax_percentage = (tax_paid/transaction_amount)*100
        total_tax_paid = previous_tax_paid + tax_paid
        investment_database_cursor.execute("INSERT INTO tax (id, tax_date, tax_paid, tax_percentage) VALUES (%s, DATE %s, %s, %s)", (investment_id, transaction_date, tax_paid, tax_percentage))
        investment_database_cursor.execute("INSERT INTO transactions (id, transaction_date, transaction_amount, transaction_type, unit_price, number_of_units) VALUES (%s, DATE %s, %s, %s, %s, %s)", (investment_id, transaction_date, transaction_type, transaction_amount - tax_paid, unit_price, number_of_units))  
        investment_database_cursor.execute("SELECT number_of_units_held FROM investments WHERE investment_name = %s", (investment_name, ))
        new_units_held = float(investment_database_cursor.fetchone()[0]) + number_of_units
        investment_database_cursor.execute("UPDATE investments SET number_of_units_held = %s, total_tax_paid = %s WHERE id = %s", (new_units_held, total_tax_paid, investment_id))  
    else:
        investment_database_cursor.execute("SELECT id FROM investments WHERE investment_name = %s", (investment_name, ))
        investment_id = investment_database_cursor.fetchone()
        investment_database_cursor.execute("INSERT INTO transactions (id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units) VALUES (%s, DATE %s, %s, %s, %s, %s)", (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units)) 
        investment_database_cursor.execute("SELECT number_of_units_held FROM investments WHERE investment_name = %s", (investment_name, ))
        new_units_held = float(investment_database_cursor.fetchone()[0]) + number_of_units
        investment_database_cursor.execute("UPDATE investments SET number_of_units_held = %s WHERE id = %s", (new_units_held, investment_id))

    investment_database_cursor.execute("SELECT unit_price FROM unit_prices WHERE id = %s", (investment_id, ))
    unit_price_last = pd.DataFrame(investment_database_cursor.fetchall()).tail(1)
    unit_price_change = float(unit_price - unit_price_last.values[0][0])
    percentage_unit_price_change = (unit_price_change/unit_price_last.values[0][0])*100
    investment_database_cursor.execute("INSERT INTO unit_prices (id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) VALUES (%s, DATE %s, %s, %s, %s)", (investment_id, transaction_date, float(unit_price), float(unit_price_change), float(percentage_unit_price_change)))   

    investment_database_connection.commit()

  
def add_unit_price(investment_name, unit_price_date, unit_price):
    investment_database_cursor.execute("SELECT id FROM investments WHERE investment_name = %s", (investment_name, ))
    investment_id = investment_database_cursor.fetchone()

    investment_database_cursor.execute("SELECT unit_price FROM unit_prices WHERE id = %s", (investment_id, ))
    unit_price_last = pd.DataFrame(investment_database_cursor.fetchall()).tail(1)
    unit_price_change = float(unit_price - unit_price_last.values[0][0])
    percentage_unit_price_change = (unit_price_change/unit_price_last.values[0][0])*100
    investment_database_cursor.execute("INSERT INTO unit_prices (id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) VALUES (%s, DATE %s, %s, %s, %s)", (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change))

    investment_database_cursor.execute("UPDATE investments SET unit_price = %s WHERE id = %s", (unit_price, investment_id))

    investment_database_connection.commit()


def add_dividend(investment_name, dividend_date, dividend_frequency, dividend_recieved, include_fees, fees_paid, include_tax, tax_paid, dividends_reinvested, number_of_units, unit_price):
    investment_database_cursor.execute("SELECT id, total_tax_paid FROM investments WHERE investment_name = %s", (investment_name, ))
    investment_id, previous_tax_paid = investment_database_cursor.fetchone()
    
    investment_database_cursor.execute("SELECT unit_price, number_of_units_held FROM investments WHERE id = %s", (investment_id, ))
    unit_information = pd.DataFrame(investment_database_cursor.fetchall()).tail(1)
    unit_price_last = float(unit_information.values[0][0])
    number_of_units_held_last = float(unit_information.values[0][1])
    dividend_percentage = (dividend_recieved/(number_of_units_held_last*unit_price_last))*100
    investment_database_cursor.execute("INSERT INTO dividends (id, dividend_date, dividend_frequency, dividend_recieved, dividend_percentage) VALUES (%s, DATE %s, %s, %s, %s)", (investment_id, dividend_date, dividend_frequency, dividend_recieved, dividend_percentage))

    if (include_tax == True and dividends_reinvested == True):
        tax_percentage = (tax_paid/dividend_recieved)*100
        total_tax_paid = previous_tax_paid + tax_paid
        new_units_held = number_of_units_held_last + number_of_units

        investment_database_cursor.execute("INSERT INTO tax (id, tax_date, tax_paid, tax_percentage) VALUES (%s, DATE %s, %s, %s)", (investment_id, dividend_date, tax_paid, tax_percentage))
        investment_database_cursor.execute("UPDATE investments SET number_of_units_held = %s, total_tax_paid = %s WHERE id = %s", (new_units_held, total_tax_paid, investment_id))
        investment_database_cursor.execute("INSERT INTO transactions (id, transaction_date, transaction_amount, unit_price, number_of_units) VALUES (%s, DATE %s, %s, %s, %s)", (investment_id, dividend_date, dividend_recieved - tax_paid, unit_price, number_of_units))

        investment_database_cursor.execute("SELECT unit_price FROM unit_prices WHERE id = %s", (investment_id, ))
        unit_price_last = pd.DataFrame(investment_database_cursor.fetchall()).tail(1)
        unit_price_change = float(unit_price - unit_price_last.values[0][0])
        percentage_unit_price_change = float(unit_price_change/unit_price_last.values[0][0])*100
        investment_database_cursor.execute("INSERT INTO unit_prices (id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) VALUES (%s, DATE %s, %s, %s, %s)", (investment_id, dividend_date, unit_price, unit_price_change, percentage_unit_price_change))
    elif (include_tax == True):
        tax_percentage = (tax_paid/dividend_recieved)*100
        total_tax_paid = previous_tax_paid + tax_paid

        investment_database_cursor.execute("INSERT INTO tax (id, tax_date, tax_paid, tax_percentage) VALUES (%s, DATE %s, %s, %s)", (investment_id, dividend_date, tax_paid, tax_percentage))
        investment_database_cursor.execute("UPDATE investments SET total_tax_paid = %s WHERE id = %s", (total_tax_paid, investment_id))
    elif(dividends_reinvested == True):
        new_units_held = number_of_units_held_last + number_of_units

        investment_database_cursor.execute("UPDATE investments SET number_of_units_held = %s WHERE id = %s", (new_units_held, investment_id))
        investment_database_cursor.execute("INSERT INTO transactions (id, transaction_date, transaction_amount, unit_price, number_of_units) VALUES (%s, DATE %s, %s, %s, %s)", (investment_id, dividend_date, dividend_recieved, unit_price, number_of_units))

        investment_database_cursor.execute("SELECT unit_price FROM unit_prices WHERE id = %s", (investment_id, ))
        unit_price_last = pd.DataFrame(investment_database_cursor.fetchall()).tail(1)
        unit_price_change = float(unit_price - unit_price_last.values[0][0])
        percentage_unit_price_change = (unit_price_change/unit_price_last.values[0][0])*100
        investment_database_cursor.execute("INSERT INTO unit_prices (id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) VALUES (%s, DATE %s, %s, %s, %s)", (investment_id, dividend_date, unit_price, unit_price_change, percentage_unit_price_change))

    investment_database_connection.commit()


def update_returns(investment_name, returns_date, monthly_return, quarterly_return, half_yearly_return, yearly_return, yearly_3_return, yearly_5_return, return_since_inception):
    investment_database_cursor.execute("SELECT id FROM investments WHERE investment_name = %s", (investment_name, ))
    investment_id = investment_database_cursor.fetchone()
    
    investment_database_cursor.execute("INSERT INTO returns (id, returns_date, monthly_return, quarterly_return, half_yearly_return, yearly_return, yearly_3_return, yearly_5_return, return_since_inception) VALUES (%s, DATE %s, %s, %s, %s, %s, %s, %s, %s)", (investment_id, returns_date, monthly_return, quarterly_return, half_yearly_return, yearly_return, yearly_3_return, yearly_5_return, return_since_inception))
    investment_database_connection.commit()
    
#Function does not
def add_tax(investment_name, tax_date, tax_paid, tax_percentage):
    investment_database_cursor.execute("SELECT id, total_tax_paid FROM investments WHERE investment_name = %s", (investment_name, ))
    investment_id, previous_tax_paid = investment_database_cursor.fetchone()
    investment_database_cursor.execute("INSERT INTO tax (id, tax_date, tax_paid, tax_percentage) VALUES (%s, DATE %s, %s, %s)", (investment_id, tax_date, tax_paid, tax_percentage))
    investment_database_cursor.execute("UPDATE investments SET total_tax_paid = %s WHERE id = %s", (total_tax_paid, investment_id)) 
    investment_database_connection.commit()


def daily_update():
    investment_database_cursor.execute("SELECT investment_ticker FROM investments")
    fetch_stocks = investment_database_cursor.fetchall()

    stocks = []
    for i in range(0, len(fetch_stocks)):
        if fetch_stocks[i][0] != "N/A":
            stocks.append(fetch_stocks[i][0])
    
    stocks = list(set(stocks))
    update_unit_prices(stocks)


def update_unit_prices(stocks):
    stocks_string = ""
    for stock in stocks:
        stocks_string = stocks_string + stock + " "
    
    tickers = yf.Tickers(stocks_string)
    current_price = []
    currency = []

    df = yf.download(' '.join(stocks), period='1d', progress=False)
    df = df['Close']
    for stock in stocks:
        #if stock not in df or len(df[stock]) == 0: # this verification is important if trading session is closed
        #continue
        if math.isnan(df[stock][0]):
            current_price.append(df[stock][1])
        else:
            current_price.append(df[stock][0])
    unit_prices = pd.DataFrame(investment_database_cursor.fetchall())
    for stock in stocks:
        stocksinfo = tickers.tickers[stock].info
        for key, value in stocksinfo.items():
            if (key == "currency"):
                currency.append(value)

    for stock in range(0, len(stocks)):
        investment_database_cursor.execute("SELECT id FROM investments WHERE investment_ticker = %s", (stocks[stock], ))
        investment_id = investment_database_cursor.fetchone()

        today = date.today()
        date_format = locale.nl_langinfo(locale.D_FMT)
        unit_price_date = today.strftime(date_format)
        
        if (currency[stock] =="ZAc"):
            unit_price = current_price[stock]/100
        else:
            unit_price = current_price[stock]

        investment_database_cursor.execute("SELECT unit_price FROM unit_prices WHERE id = %s", (investment_id, ))
        unit_price_last = pd.DataFrame(investment_database_cursor.fetchall()).tail(1)
        unit_price_change = float(unit_price - unit_price_last.values[0][0])
        percentage_unit_price_change = (unit_price_change/unit_price_last.values[0][0])*100
        investment_database_cursor.execute("INSERT INTO unit_prices (id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) VALUES (%s, DATE %s, %s, %s, %s)", (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change))
        investment_database_cursor.execute("UPDATE investments SET unit_price = %s WHERE id = %s", (unit_price, investment_id))
        investment_database_connection.commit()


def import_unit_prices_csv(file_name, investment_name, currency):
    # Fetch investment ID
    investment_database_cursor.execute(
        "SELECT id FROM investments WHERE investment_name = %s", (investment_name,)
    )
    investment_id = investment_database_cursor.fetchone()
    if not investment_id:
        raise ValueError(f"Investment '{investment_name}' not found in database.")
    investment_id = investment_id[0]

    # Fetch the last unit price for change calculations
    investment_database_cursor.execute(
        "SELECT unit_price FROM unit_prices WHERE id = %s ORDER BY unit_price_date DESC LIMIT 1",
        (investment_id,),
    )
    last_unit_price = investment_database_cursor.fetchone()
    last_unit_price = float(last_unit_price[0]) if last_unit_price else 0.0

    # Load unit prices CSV into a DataFrame
    investment_unit_prices = pd.read_csv(file_name, names=["unit_price_date", "unit_price"])
    investment_unit_prices["unit_price_date"] = pd.to_datetime(investment_unit_prices["unit_price_date"])
    
    # Remove duplicates and fill missing dates with forward fill
    investment_unit_prices.drop_duplicates("unit_price_date", inplace=True)
    date_range = pd.date_range(
        investment_unit_prices["unit_price_date"].min(),
        investment_unit_prices["unit_price_date"].max(),
        freq="D",
    )
    investment_unit_prices = investment_unit_prices.set_index("unit_price_date").reindex(date_range).ffill()
    investment_unit_prices.reset_index(inplace=True)
    investment_unit_prices.rename(columns={"index": "unit_price_date"}, inplace=True)

    # Calculate changes in unit price
    investment_unit_prices["unit_price_change"] = investment_unit_prices["unit_price"].diff()
    investment_unit_prices.at[0, "unit_price_change"] = investment_unit_prices["unit_price"].iloc[0] - last_unit_price
    investment_unit_prices["percentage_unit_price_change"] = (
        investment_unit_prices["unit_price_change"] / investment_unit_prices["unit_price"].shift(1) * 100
    )
    investment_unit_prices.at[0, "percentage_unit_price_change"] = (
        investment_unit_prices["unit_price_change"].iloc[0] / last_unit_price * 100
        if last_unit_price != 0
        else 0.0
    )

    # Add investment ID and adjust currency if needed
    investment_unit_prices.insert(0, "id", investment_id)
    if currency == "ZAc":
        investment_unit_prices["unit_price"] = investment_unit_prices["unit_price"] / 100

    # Write data to database
    engine = create_engine("postgresql://postgres:changeme@localhost:5432/Investments")
    investment_unit_prices.to_sql("unit_prices", engine, index=False, if_exists="append", method="multi")

    # Update the current unit price in the investments table
    latest_unit_price = float(investment_unit_prices.iloc[-1]["unit_price"])
    investment_database_cursor.execute(
        "UPDATE investments SET unit_price = %s WHERE id = %s", (latest_unit_price, investment_id)
    )
    investment_database_connection.commit()


def create_charts():
    
    investment_values = get_all_investment_values("Investments")

    graph_colours = []
    line_width = 2
    for id in range(len(investment_id)-1):
        hex_colour = hex_code_colors()
        graph_colours.append(hex_colour)
        investment = investment_values[investment_values["id"] == investment_id.loc[id, "id"]]

        plt.plot(investment["unit_price_date"], investment["investment_value"], c=hex_colour, lw=line_width)
        plt.title(investment_id.loc[id, "investment_name"])
        plt.xlabel("Investment Date")
        plt.ylabel("Investment Value (" + investment_id.loc[id, "unit_currency"] + ")")
        plt.savefig("investment_linegraph_" + str(investment_id.at[id, "id"]) + ".png", dpi = 1000, bbox_inches = "tight")
        plt.close()

        plt.boxplot(investment["investment_value"])
        plt.title(investment_id.loc[id, "investment_name"])
        plt.xlabel("Investment Date")
        plt.ylabel("Investment Value (" + investment_id.loc[id, "unit_currency"] + ")")
        plt.savefig("investment_boxplot_" + str(investment_id.at[id, "id"]) + ".png", dpi = 1000, bbox_inches = "tight")
        plt.close()

        if(investment_id.iloc[id]["unit_currency"] != native_currency and investment_id.iloc[id]["investment_name"] != "Exchange"):
            plt.plot(investment["unit_price_date"], investment["exchange_rate"], c=hex_colour, lw=line_width)
            plt.title(investment_id.loc[id, "investment_name"])
            plt.xlabel("Investment Date")
            plt.ylabel("Investment Value (" + native_currency + ")")
            plt.savefig("investment_linegraph_" + str(investment_id.at[id, "id"]) + "_" + native_currency + ".png", dpi = 1000, bbox_inches = "tight")
            plt.close()

            plt.boxplot(investment["exchange_rate"])
            plt.title(investment_id.loc[id, "investment_name"])
            plt.xlabel("Investment Date")
            plt.ylabel("Investment Value (" + investment_id.loc[id, "unit_currency"] + ")")
            plt.savefig("investment_boxplot_" + str(investment_id.at[id, "id"]) + "_" + native_currency + ".png", dpi = 1000, bbox_inches = "tight")
            plt.close()

        

    for currency in investment_id["unit_currency"].unique():
        investment = investment_values[investment_values["unit_currency"] == currency]
        fig, ax = plt.subplots()
        for i, (name, group) in enumerate(investment.groupby('id')):
            ax.plot(group["unit_price_date"], group["investment_value"], c=graph_colours[i], label=investment_id.loc[i, "investment_name"])

        #plt.tight_layout()
        plt.title("All Investments in " + currency)
        plt.xlabel("Investment Date")
        plt.ylabel("Investment Value")
        plt.legend()
        plt.savefig("investments_linegraph_in_" + currency + ".png", dpi = 1000, bbox_inches = "tight")
        plt.close()

        fig, ax = plt.subplots()
        ax.boxplot(investment["investment_value"])

        #plt.tight_layout()
        plt.title("All Investments in " + currency)
        plt.xlabel("Investment Date")
        plt.ylabel("Investment Value")
        plt.savefig("investments_boxplot_in_" + currency + ".png", dpi = 1000, bbox_inches = "tight")
        plt.close()

    for investment_type in investment_id["investment_type"].unique():
        investment = investment_values[investment_values["investment_type"] == investment_type]
        fig, ax = plt.subplots()
        for i, (name, group) in enumerate(investment.groupby('id')):
            ax.plot(group["unit_price_date"], group["investment_value"], c=graph_colours[i], label=investment_id.loc[i, "investment_name"])

        #plt.tight_layout()
        plt.title("All Investments of type " + investment_type)
        plt.xlabel("Investment Date")
        plt.ylabel("Investment Value (R)")
        plt.savefig("investments_linegraph_of_type_" + investment_type + ".png", dpi = 1000, bbox_inches = "tight")
        plt.close()

        fig, ax = plt.subplots()
        ax.boxplot(investment["investment_value"])

        #plt.tight_layout()
        plt.title("All Investments of type " + investment_type)
        plt.xlabel("Investment Date")
        plt.ylabel("Investment Value (R)")
        plt.savefig("investments_boxplot_of_type_" + investment_type + ".png", dpi = 1000, bbox_inches = "tight")
        plt.close()

        

    fig, ax = plt.subplots()
    for i, (name, group) in enumerate(investment.groupby('id')):
        ax.plot(group["unit_price_date"], group['investment_value'], c=graph_colours[i], label=investment_id.loc[i, "investment_name"])

    #plt.tight_layout()
    plt.title("All Investments converted to Rands")
    plt.xlabel("Investment Date")
    plt.ylabel("Investment Value")
    plt.savefig("investments_linegraph_in_rands.png", dpi = 1000, bbox_inches = "tight")
    plt.close()

    fig, ax = plt.subplots()
    ax.boxplot(investment_values["investment_value"])

    #plt.tight_layout()
    plt.title("All Investments converted to Rands")
    plt.xlabel("Investment Date")
    plt.ylabel("Investment Value")
    plt.savefig("investments_boxplot_in_rands.png", dpi = 1000, bbox_inches = "tight")
    plt.close()


def generate_investment_report():
    #daily_update()
    
    font = "Helvetica"
    font_size = 4
    returns_to_show = 5
    transactions_to_show = 5

    investment_database_cursor.execute("SELECT * FROM investments ORDER BY id ASC")
    investments = pd.DataFrame(investment_database_cursor.fetchall(), columns=["id", "institution_name", "initial_investment_date", "investment_type", "investment_name", "investment_ticker", "unit_currency", "initial_unit_price", "unit_price", "number_of_units_held", "total_dividends_received", "total_tax_paid", "total_fees_paid", "investment_fee", "investment_status"])

    today = date.today()
    today = today.strftime("%B %Y")
    date_format = locale.nl_langinfo(locale.D_FMT)

    create_charts()
    investment_pdf_name ="Investment Report-" + today + ".pdf"
    investment_pdf_canvas = canvas.Canvas(investment_pdf_name, pagesize = letter)
    investment_pdf_canvas.setFont(font, font_size)
    #x_position = investment_pdf_canvas._pagesize[0]
    #y_position = investment_pdf_canvas._pagesize[1]
    x_position = letter[0]
    y_position = letter[1]
    text_padding = 20
    y_offset = text_padding
    investment_pdf_canvas.drawCentredString(x_position/2, y_position - y_offset, "Investment Report for " + today)
    y_offset = y_offset + text_padding
    investment_pdf_canvas.drawString(20, y_position - y_offset, "Generated Date: " + date.today().strftime(date_format))
    y_offset = y_offset + text_padding
    investment_pdf_canvas.drawCentredString(x_position/2, y_position - y_offset, "Investment Summary")

    investment_summary = investments
    investment_summary["initial_unit_price"] = investment_summary["unit_currency"].astype(str) + round(investment_summary["initial_unit_price"], 2).astype(str)
    investment_summary["unit_price"] = investment_summary["unit_currency"].astype(str) + round(investment_summary["unit_price"], 2).astype(str)
    investment_summary["number_of_units_held"] = round(investment_summary["number_of_units_held"], 2).astype(str)
    investment_summary["total_dividends_received"] = investment_summary["unit_currency"].astype(str) + round(investment_summary["total_dividends_received"], 2).astype(str)
    investment_summary["total_tax_paid"] = investment_summary["unit_currency"].astype(str) + round(investment_summary["total_tax_paid"], 2).astype(str)
    investment_summary["investment_fee"] = round(investment_summary["investment_fee"], 2).astype(str) + "%"
    investment_summary = investment_summary[["investment_name", "investment_type", "initial_unit_price", "unit_price", "number_of_units_held", "initial_investment_date", "total_dividends_received", "total_tax_paid", "investment_fee"]]
    investment_summary["number_of_units_held"] = pd.to_numeric(investment_summary["number_of_units_held"])
    investment_summary = investment_summary[investment_summary["number_of_units_held"] != 0]
    investment_summary.columns = ["Investment Name", "Investment Type", "Initial Unit Price", "Current Unit Price", "Number of Units Held", "Investment Date", "Dividends Received", "Tax Paid", "Investment Fee"]
    create_connection("Investments")
    investment_database_cursor.execute("SELECT id, transaction_date, unit_price, number_of_units FROM transactions")
    investment_transactions = pd.DataFrame(investment_database_cursor.fetchall(), columns=["id", "transaction_date", "unit_price", "number_of_units"])

    investment_id = pd.DataFrame(columns = ["id", "investment_name", "total_units_held", "unit_currency", "investment_type"])
    all_investment_id = pd.DataFrame(columns = ["id", "investment_name", "total_units_held", "unit_currency", "investment_type"])
    
    all_investment_id["id"] = investments["id"]
    all_investment_id["investment_name"] = investments["investment_name"]
    all_investment_id["total_units_held"] = investments["number_of_units_held"]
    all_investment_id["unit_currency"] = investments["unit_currency"]
    all_investment_id["investment_type"] = investments["investment_type"]

    all_investment_id["total_units_held"] = pd.to_numeric(all_investment_id["total_units_held"])
    investment_id = all_investment_id[~np.isclose(all_investment_id["total_units_held"], 0.0)]

    print(investment_id)
    create_connection("Investments")
    investment_database_cursor.execute("SELECT * FROM returns")
    investment_returns = pd.DataFrame(investment_database_cursor.fetchall(), columns=["id", "returns_date", "monthly_return", "quarterly_return", "half_yearly_return", "yearly_return", "yearly_3_return", "yearly_5_return", "return_since_inception"])
    investment_returns = pd.merge(investment_returns, investment_id, on = "id", how = "left")
    investment_returns.drop(columns = ["total_units_held", "unit_currency", "investment_type"], inplace=True)
    investment_returns = investment_returns[["id", "investment_name", "returns_date", "monthly_return", "quarterly_return", "half_yearly_return", "yearly_return", "yearly_3_return", "yearly_5_return", "return_since_inception"]]
    investment_returns.columns = ["id", "Investment Name", "Returns on date", "Monthly Return", "Quarterly Return", "Half-Yearly Return", "Yearly Return", "Return 3 Year", "Return 5 Year", "Return since Inception"]

    investment_transactions = pd.merge(investment_id, investment_transactions, on="id", how = "right")
    investment_transactions.drop(columns = ["total_units_held", "investment_type"], inplace=True)
    investment_transactions.sort_values(by="transaction_date", inplace=True)
    investment_transactions["total_units_held"] = investment_transactions.groupby("id")["number_of_units"].cumsum()

    investment_table = Table([investment_summary.columns.tolist()] + investment_summary.values.tolist())
    investment_table.setStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('COLWIDTH', (0, 0), (-1, -1), x_position - 20),
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), font_size)
    ])
    investment_table.wrapOn(investment_pdf_canvas, 400, 800)
    y_offset = y_offset + 110
    investment_table.drawOn(investment_pdf_canvas, 10, y_position - y_offset)

    y_offset = y_offset + text_padding*2
    investment_pdf_canvas.drawCentredString(x_position/2, y_position - y_offset, "Individual investment break down")
    investment_pdf_canvas.showPage()

    for id in range(len(investment_id)-1):
        returns = investment_returns[investment_returns["id"] == investment_id.loc[id, "id"]].copy()
        returns.sort_values(by = "Returns on date", inplace=True)
        returns = returns.tail(returns_to_show)
        returns.drop(columns = ["id", "Investment Name"], inplace=True)

        investment_pdf_canvas.setFont(font, font_size)
        y_offset = 20
        investment_pdf_canvas.drawCentredString(x_position/2, y_position - y_offset, investment_id.at[id, "investment_name"])
        investment_table = Table([returns.columns.tolist()] + returns.values.tolist())
        investment_table.setStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('COLWIDTH', (0, 0), (-1, -1), x_position - 20),
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), font_size)
    ])
        investment_table.wrapOn(investment_pdf_canvas, 400, 800)
        y_offset = y_offset + 120
        investment_table.drawOn(investment_pdf_canvas, 10, y_position - y_offset)

        y_offset = y_offset + 402
        investment_pdf_canvas.drawImage("investment_linegraph_" + str(investment_id.at[id, "id"]) + ".png", 10, y_position - y_offset, width=350, height=350)
        investment_pdf_canvas.drawImage("investment_boxplot_" + str(investment_id.at[id, "id"]) + ".png", 350, y_position - y_offset, width=250, height=350)

        if(investment_id.iloc[id]["unit_currency"] != native_currency):
            investment_pdf_canvas.drawImage("investment_linegraph_" + str(investment_id.at[id, "id"]) + "_" + native_currency + ".png", 10, y_position - 2*y_offset, width=200, height=200)
            investment_pdf_canvas.drawImage("investment_boxplot_" + str(investment_id.at[id, "id"]) + "_" + native_currency + ".png", 350, y_position - 2*y_offset, width=100, height=200)
        investment_pdf_canvas.showPage()


    
    investment_pdf_canvas.save()

    sending_email ="armin.investmentmanagement@gmail.com"
    sending_email_passphrase = "aejf xmbx xpsy fvsj"
    receiving_email = "armin.grobbelaar256@gmail.com"
    investment_pdf = []
    investment_pdf.append(investment_pdf_name)
    send_investment_email(sending_email, sending_email_passphrase, receiving_email, investment_pdf)

    investment_database_connection.commit()
    investment_database_cursor.close()
    investment_database_connection.close()


def hex_code_colors():
    a = hex(random.randrange(0,256))
    b = hex(random.randrange(0,256))
    c = hex(random.randrange(0,256))
    a = a[2:]
    b = b[2:]
    c = c[2:]
    if len(a)<2:
        a = "0" + a
    if len(b)<2:
        b = "0" + b
    if len(c)<2:
        c = "0" + c
    z = a + b + c
    return "#" + z.upper()


def send_investment_email(sending_email, sending_email_passphrase, receiving_email, investment_pdfs):
    today = date.today()
    today = today.strftime("%B %Y")

    investment_message = EmailMessage()
    investment_message["Subject"] = "Investment Report for " + today
    investment_message["From"] = sending_email
    investment_message["To"] = receiving_email
    investment_message.set_content("Please see your newest investment report for " + today + " in the pdf document attached.")

    for pdf in investment_pdfs:
        with open(pdf, "rb") as p:
            pdf_data = p.read()
            pdf_name = p.name
        
        investment_message.add_attachment(pdf_data, maintype = "application", subtype = "octet-stream", filename = pdf_name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sending_email, sending_email_passphrase)
        smtp.send_message(investment_message)

def get_all_investment_values(database_name):
    create_connection(database_name)
    global all_investment_id
    global investment_id

    investment_database_cursor.execute("SELECT * FROM investments ORDER BY id ASC")
    investments = pd.DataFrame(investment_database_cursor.fetchall(), columns=["id", "institution_name", "initial_investment_date", "investment_type", "investment_name", "investment_ticker", "unit_currency", "initial_unit_price", "unit_price", "number_of_units_held", "total_dividends_received", "total_tax_paid", "total_fees_paid", "investment_fee", "investment_status"])

    date_format = locale.nl_langinfo(locale.D_FMT)
    
    unit_price_query = """

        WITH cte AS (
        SELECT 
            unit_prices.id,
            unit_prices.unit_price_date,
            unit_prices.unit_price,
            COALESCE(total_units_held, 0) AS total_units_held,
            MAX(CASE WHEN total_units_held > 0 THEN unit_prices.unit_price_date END) OVER (PARTITION BY unit_prices.id ORDER BY unit_prices.unit_price_date) AS last_non_zero_date
        FROM 
            unit_prices
        LEFT JOIN (
            SELECT 
                id,
                transaction_date,
                SUM(number_of_units) AS total_units_held
            FROM 
                transactions
            GROUP BY 
                id, 
                transaction_date
        ) AS transaction_totals ON unit_prices.id = transaction_totals.id 
                                AND unit_prices.unit_price_date = transaction_totals.transaction_date
    )
    SELECT 
        id,
        unit_price_date,
        unit_price,
        COALESCE(total_units_held, 0) AS total_units_held
    FROM 
        cte
    ORDER BY 
        id,
        unit_price_date ASC;

    """
    #investment_database_cursor.execute("SELECT id, unit_price_date, unit_price FROM unit_prices")
    investment_database_cursor.execute(unit_price_query)
    unit_prices = pd.DataFrame(investment_database_cursor.fetchall(), columns=["id", "unit_price_date", "unit_price", "total_units_held"])
    print(unit_prices)
    unit_prices["total_units_held"] = unit_prices.groupby('id')['total_units_held'].cumsum()

    investment_database_cursor.execute("SELECT id, transaction_date, unit_price, number_of_units FROM transactions")
    transactions = pd.DataFrame(investment_database_cursor.fetchall(), columns=["id", "transaction_date", "unit_price", "number_of_units"])

    investment_values = pd.DataFrame(columns = ["id", "investment_name", "unit_price_date", "unit_price", "number_of_units", "investment_value", "unit_currency", "investment_type"])
    investment_values["unit_price_date"] = pd.to_datetime(investment_values["unit_price_date"])
    investment_id = pd.DataFrame(columns = ["id", "investment_name", "total_units_held", "unit_currency", "investment_type"])
    all_investment_id = pd.DataFrame(columns = ["id", "investment_name", "total_units_held", "unit_currency", "investment_type"])

    all_investment_id["id"] = investments["id"]
    all_investment_id["investment_name"] = investments["investment_name"]
    all_investment_id["total_units_held"] = 0
    all_investment_id["unit_currency"] = investments["unit_currency"]
    all_investment_id["investment_type"] = investments["investment_type"]

    investment_id["id"] = investments[investments["number_of_units_held"] != 0]["id"]
    investment_id["investment_name"] = investments[investments["number_of_units_held"] != 0]["investment_name"]
    investment_id["total_units_held"] = 0
    investment_id["unit_currency"] = investments[investments["number_of_units_held"] != 0]["unit_currency"]
    investment_id["investment_type"] = investments[investments["number_of_units_held"] != 0]["investment_type"]

    transactions["used"] = False
    unit_prices.sort_values(by = "unit_price_date", inplace=True)
    unit_prices.reset_index(drop=True, inplace=True)
    transactions.reset_index(drop=True, inplace=True)
    unit_prices = pd.merge(all_investment_id, unit_prices, on = "id", how="left")
    print(unit_prices)
    all_forex_unit_prices = unit_prices[unit_prices["investment_type"] == "Forex"]
    foreign_unit_prices = unit_prices[(unit_prices["unit_currency"] != native_currency) & (unit_prices["investment_type"] != "Forex")]
    print(all_forex_unit_prices)
    print(foreign_unit_prices)
    print("STEP-")
    investment_values = pd.concat([investment_values, unit_prices], ignore_index=True)
    investment_values = pd.merge(investment_values, all_investment_id, on='id', how='left')
    investment_values.drop(columns=["number_of_units", "total_units_held_x", "investment_name_y", "total_units_held", "unit_currency_y", "investment_type_y"], inplace=True)
    print(investment_values.columns)
    investment_values.columns = ["id", "investment_name", "unit_price_date", "unit_price", "investment_value", "unit_currency", "investment_type", "number_of_units"]
    investment_values["investment_value"] = investment_values["unit_price"]*investment_values["number_of_units"]
    print(investment_values.columns)
    print("FUP")
    print(foreign_unit_prices)
    exchange_rates = pd.DataFrame()
    for i in foreign_unit_prices["id"].unique():
        unit_prices_id = foreign_unit_prices[foreign_unit_prices["id"] == i]
        forex_id = all_forex_unit_prices[all_forex_unit_prices["unit_currency"] == foreign_unit_prices[foreign_unit_prices["id"] == i]["unit_currency"].iloc[0]]
        min_date = unit_prices_id["unit_price_date"].min()
        max_date = unit_prices_id["unit_price_date"].max()
        forex_id = forex_id[(forex_id["unit_price_date"] >= min_date) & (forex_id["unit_price_date"] <= max_date)]
        forex_id.rename(columns={"unit_price": "exchange_rate"}, inplace=True)

        unit_prices_id.reset_index(drop=True, inplace=True)
        forex_id.reset_index(drop=True, inplace=True)
        unit_prices_id = pd.merge(unit_prices_id, forex_id, on="unit_price_date", how="left")
        #unit_prices_id.drop(columns=["investment_name_y", "investment_type_y", "id_y", "unit_currency_y"], inplace=True)
        #unit_prices_id.columns = ["id", "unit_price_date", "unit_price", "total_units_held", "investment_name", "unit_currency", "investment_type"]
        column_mapping = {"id_x": "id", "investment_name_x": "investment_name", "unit_currency_x": "unit_currency", "investment_type_x": "investment_type", "unit_price_date": "unit_price_date", "unit_price": "unit_price", "exchange_rate": "exchange_rate"}
        unit_prices_id = unit_prices_id.rename(columns=column_mapping)[["id", "investment_name", "unit_currency", "investment_type", "unit_price_date", "unit_price", "exchange_rate"]]
        #unit_prices_id["exchange_rate"].ffill(inplace=True)
        unit_prices_id["exchange_rate"].ffill(inplace=True)
        print("UP")
        print(unit_prices_id)
        exchange_rates = pd.concat([exchange_rates, unit_prices_id], ignore_index=True)
    print("ER")
    print(exchange_rates)
    investment_exchange = exchange_rates[["id", "unit_price_date", "exchange_rate"]].copy() 
    investment_values = pd.merge(investment_values, investment_exchange, on=["id", "unit_price_date"], how="left")
    investment_values["exchange_rate"].fillna(1)
    investment_values["investment_value_in_native_currency"] = investment_values["investment_value"]*investment_values["exchange_rate"]
    

    investment_values.sort_values(by = ["unit_price_date", "id"], inplace=True)

    investment_values = investment_values[investment_values["investment_value"] != 0]
    investment_values.to_csv('investment_values.csv', index=False)
    #investment_database_connection.commit()
    investment_database_cursor.close()
    #investment_database_connection.close()
    return investment_values

def get_investment_summary(database_name):
    create_connection(database_name)
    global all_investment_id
    global investment_id
    investment_id = pd.DataFrame(columns = ["id", "institution_name", "investment_name", "investment_type", "unit_currency", "investment_value", "unit_price", "total_units_held", "initial_unit_price", "initial_investment_date"])
    all_investment_id = pd.DataFrame(columns = ["id", "investment_name", "total_units_held", "unit_currency", "investment_type"])

    investment_database_cursor.execute("SELECT * FROM investments ORDER BY id ASC")
    investments = pd.DataFrame(investment_database_cursor.fetchall(), columns=["id", "institution_name", "initial_investment_date", "investment_type", "investment_name", "investment_ticker", "unit_currency", "initial_unit_price", "unit_price", "number_of_units_held", "total_dividends_received", "total_tax_paid", "total_fees_paid", "investment_fee", "investment_status"])

    all_investment_id["id"] = investments["id"]
    all_investment_id["investment_name"] = investments["investment_name"]
    all_investment_id["total_units_held"] = investments["number_of_units_held"]
    all_investment_id["unit_currency"] = investments["unit_currency"]
    all_investment_id["investment_type"] = investments["investment_type"]

    investment_id["id"] = investments[investments["number_of_units_held"] != 0]["id"]
    investment_id["institution_name"] = investments[investments["number_of_units_held"] != 0]["institution_name"]
    investment_id["investment_name"] = investments[investments["number_of_units_held"] != 0]["investment_name"]
    investment_id["investment_type"] = investments[investments["number_of_units_held"] != 0]["investment_type"]
    investment_id["unit_currency"] = investments[investments["number_of_units_held"] != 0]["unit_currency"]
    investment_id["investment_value"] = investments[investments["number_of_units_held"] != 0]["unit_price"] * investments[investments["number_of_units_held"] != 0]["number_of_units_held"]
    investment_id["unit_price"] = investments[investments["number_of_units_held"] != 0]["unit_price"]
    investment_id["total_units_held"] = investments[investments["number_of_units_held"] != 0]["number_of_units_held"]
    investment_id["initial_unit_price"] = investments[investments["number_of_units_held"] != 0]["initial_unit_price"]
    investment_id["initial_investment_date"] = investments[investments["number_of_units_held"] != 0]["initial_investment_date"]
    

    investment_database_connection.commit()
    investment_database_cursor.close()
    investment_database_connection.close()

    return investment_id


if __name__ == "__main__":
    #add_user("Armin", "Grobbelaar")
    #print(get_all_investment_values("Investments"))
    create_connection("Investments")
    add_investment("Investments", "Satrix", "2022/02/16", "ETF", "Satrix MSCI World", "STXWDM.JO", "R", 63.66879883, 63.66879883, 20, 0, 0,0, 1.56, "Active")
    #add_transaction("Satrix MSCI World", "2023/02/17", "Buy", 703.0759766, 70.30759766, 10, True, 0, True, 89.56)
    #add_dividend("Satrix MSCI World", "2024/02/19", 4, 600, True, 120, True, 48, 10)
    #add_tax("Satrix MSCI Wo14498.89rld", "2024/02/21", 100, 20)
    #update_returns("Satrix MSCI World", "2024/03/21", 2, 6, 8, 15, 6, 17, 89)
    #investment_database_connection.commit()
    #import_unit_prices_csv("test1.csv", "Satrix MSCI World", "ZAc")
    #investment_database_connection.commit()
    #update_retu
    
    #add_investment("Investments","Satrix", "2023/03/06", "ETF", "Satrix Nasdaq 100", "STXNDQ.JO", "R", 126.9586035, 126.9586035, 50, 0, 0,0, 1.56, "Active")
    #add_transaction("Satrix Nasdaq 100", "2023/11/16", "Buy", 3288.09, 164.4044922, 20, True, 240, True, 89.56)
    #add_dividend("Satrix Nasdaq 100", "2023/11/18", 4, 600, True, 120, True, 48, 10)
    #add_tax("BlackRock EURO STOXX 50", "2023/11/20", 100, 20)
    #update_returns("Satrix Nasdaq 100", "2024/03/21", 2, 9, 8, 15, 6, 17, 89)
    #investment_database_connection.commit()
    #import_unit_prices_csv("test2.csv", "Satrix Nasdaq 100", "ZAc")
    #investment_database_connection.commit()
    
    #add_investment("Sygnia", "2023/03/06", "ETF", "Sygnia Itrix Euro Stoxx 50", "SYGEU.JO", "R", 84.42, 84.42, 10, 0, 0, 1.56)
    #add_transaction("Sygnia Itrix Euro Stoxx 50", "2024/03/01", 10093, 100.93, 100, True, 240)
    #add_dividend("Sygnia Itrix Euro Stoxx 50", "2024/03/03", 4, 600, True, 120, True, 48, 10)
    #add_tax("Sygnia Itrix Euro Stoxx 50", "2024/03/04", 100, 20)
    #update_returns("Sygnia Itrix Euro Stoxx 50", "2024/03/21", 18, 9, 8, 15, 6, 17, 89)
    #investment_database_connection.commit()
    #import_unit_prices_csv("test3.csv", "Sygnia Itrix Euro Stoxx 50", "ZAR")
    #investment_database_connection.commit()
    
    #add_investment("1nvest", "2023/06/06", "ETF", "1nvest S&P500 Feeder", "ETF500.JO", "R", 378.9774219, 378.9774219, 40, 0, 0, 1.56)
    #add_transaction("1nvest S&P500 Feeder", "2023/10/16", 14498.89, 426.4380078, 34, True, 240)
    #add_dividend("1nvest S&P500 Feeder", "2023/10/18", 4, 600, True, 120, True, 48, 10)
    #add_tax("1nvest S&P500 Feeder", "2023/10/20", 100, 20)
    #update_returns("1nvest S&P500 Feeder", "2024/03/21", 18, 20, 8, 15, 6, 17, 89)
    #investment_database_connection.commit()
    #import_unit_prices_csv("test4.csv", "1nvest S&P500 Feeder", "ZAc")
    #investment_database_connection.commit()
    #daily_update()
    #add_investment("Europe", "2023/03/06", "Forex", "Foreign Currency", "GBP/ZAR=X", "£", 15.7, 15.7, 100, 0, 0, 0)
    #add_investment("UK", "2023/03/06", "Forex", "Foreign Currency", "EUR/ZAR=X", "€", 15.7, 15.7, 100, 0, 0, 0)
    #investment_database_connection.commit()
    
    #sending_email ="armin.investmentmanagement@gmail.com"
    #sending_email_passphrase = "aejf xmbx xpsy fvsj"
    #receiving_email = "armin.grobbelaar256@gmail.com"
    #investment_pdf = []
    #investment_pdf.append("test.pdf")
    #send_investment_email(sending_email, sending_email_passphrase, receiving_email, investment_pdf)
    add_investment("Investments","Sygnia", "2023/03/06", "ETF", "Sygnia Itrix MSCI USA Index ETF", "SYGUS.JO", "$", 84.42, 84.42, 10, 0, 0,0, 1.56, "Active")
    #investment_database_connection.commit()
    generate_investment_report()
    #import_unit_prices_csv("test.csv", "Sygnia Itrix MSCI USA Index ETF", "$")
    #Read unit prices from csv
    #unit_prices = pd.read_csv("all_unit_prices.csv")
    
    #for i in range(len(unit_prices)):
    #    investment_database_cursor.execute("INSERT INTO unit_prices (id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) VALUES (%s, DATE %s, %s, %s, %s)", (int(unit_prices.loc[i, "id"]), unit_prices.loc[i, "unit_price_date"], float(unit_prices.loc[i, "unit_price"]), float(unit_prices.loc[i, "unit_price_change"]), float(unit_prices.loc[i, "percentage_unit_price_change"]))
    
    
    #investment_database_cursor.execute("\copy unit_prices(id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) FROM '/home/armin/.config/scripts/investments/SYGEU.JO_clean.csv' DELIMITER ',' CSV HEADER;")




