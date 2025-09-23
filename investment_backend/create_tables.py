#!/usr/bin/env python3

import psycopg2

investment_database_connection = psycopg2.connect(host="ThinkTank", database="Investments", user="postgres", password="changeme", port=5432)

investment_database_cursor = investment_database_connection.cursor()

investment_database_cursor.execute("CREATE TABLE investments (id BIGSERIAL NOT NULL PRIMARY KEY, institution_name VARCHAR(200) NOT NULL, initial_investment_date DATE NOT NULL, investment_type VARCHAR(50) NOT NULL, investment_name VARCHAR(200), investment_ticker VARCHAR(50) NOT NULL UNIQUE, unit_currency VARCHAR(5) NOT NULL, initial_unit_price float8 NOT NULL, unit_price float8 NOT NULL, number_of_units_held float8 NOT NULL, total_dividends_received float8 NOT NULL, total_tax_paid float8 NOT NULL, total_fees_paid float8 NOT NULL, investment_fee float8 NOT NULL, investment_status VARCHAR(20) NOT NULL)")
investment_database_cursor.execute("CREATE TABLE unit_prices (id BIGINT NOT NULL REFERENCES investments(id), unit_price_date DATE NOT NULL, unit_price float8 NOT NULL, unit_price_change float8 NOT NULL, percentage_unit_price_change float8 NOT NULL)")
investment_database_cursor.execute("CREATE TABLE returns (id BIGINT NOT NULL REFERENCES investments(id), returns_date DATE NOT NULL, monthly_return float8 NOT NULL, quarterly_return float8 NOT NULL, half_yearly_return float8 NOT NULL, yearly_return float8 NOT NULL, yearly_3_return float8 NOT NULL, yearly_5_return float8 NOT NULL, return_since_inception float8 NOT NULL)")
investment_database_cursor.execute("CREATE TABLE transactions (id BIGINT NOT NULL REFERENCES investments(id), transaction_date DATE NOT NULL, transaction_type VARCHAR(20) NOT NULL, transaction_amount float8 NOT NULL, unit_price float8 NOT NULL, number_of_units float8 NOT NULL)")
investment_database_cursor.execute("CREATE TABLE dividends (id BIGINT NOT NULL REFERENCES investments(id), dividend_date DATE NOT NULL, dividend_frequency int NOT NULL, dividend_recieved float8 NOT NULL, dividend_percentage float8 NOT NULL)")
investment_database_cursor.execute("CREATE TABLE fees (id BIGINT NOT NULL REFERENCES investments(id), fee_date DATE NOT NULL, fee_type VARCHAR(50) NOT NULL, fee_paid float8 NOT NULL, fee_frequency float8 NOT  NULL, number_of_units float8 NOT NULL, investment_fee float8 NOT NULL)")
investment_database_cursor.execute("CREATE TABLE tax (id BIGINT NOT NULL REFERENCES investments(id), tax_date DATE NOT NULL, tax_type VARCHAR(50) NOT NULL, tax_paid float8 NOT NULL, tax_percentage float8 NOT NULL)")
investment_database_connection.commit()

investment_database_cursor.close()
investment_database_connection.close()