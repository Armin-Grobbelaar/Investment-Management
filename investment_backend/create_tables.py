#!/usr/bin/env python3

import os
import psycopg2
import logging
from contextlib import contextmanager
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "ThinkTank")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
INVESTMENTS_DB = os.getenv("INVESTMENTS_DB", "Investments")
USERS_DB = os.getenv("USERS_DB", "Users")

@contextmanager
def get_db_connection(db_name):
    """Context manager for database connections."""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=db_name,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=POSTGRES_PORT
        )
        yield conn
    except Exception as e:
        logger.error(f"Database connection error for {db_name}: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def create_tables(db_name):
    """Verify or create necessary tables in the given database."""
    with get_db_connection(db_name) as conn:
        with conn.cursor() as cursor:
            try:
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
                        investment_status VARCHAR(20) NOT NULL,
                        investment_subtype VARCHAR(50),
                        source_account VARCHAR(100),
                        price_source_investment_id BIGINT REFERENCES investments(id)
                    )""")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS unit_prices (
                        id BIGSERIAL PRIMARY KEY,
                        investment_id BIGINT NOT NULL REFERENCES investments(id),
                        unit_price_date DATE NOT NULL,
                        unit_price float8 NOT NULL,
                        unit_price_change float8 NOT NULL,
                        percentage_unit_price_change float8 NOT NULL,
                        UNIQUE(investment_id, unit_price_date)
                    )""")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS returns (
                        id BIGSERIAL PRIMARY KEY,
                        investment_id BIGINT NOT NULL REFERENCES investments(id),
                        returns_date DATE NOT NULL,
                        monthly_return float8 NOT NULL,
                        quarterly_return float8 NOT NULL,
                        half_yearly_return float8 NOT NULL,
                        yearly_return float8 NOT NULL,
                        yearly_3_return float8 NOT NULL,
                        yearly_5_return float8 NOT NULL,
                        return_since_inception float8 NOT NULL,
                        UNIQUE(investment_id, returns_date)
                    )""")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id BIGSERIAL PRIMARY KEY,
                        investment_id BIGINT NOT NULL REFERENCES investments(id),
                        transaction_date DATE NOT NULL,
                        transaction_type VARCHAR(20) NOT NULL,
                        transaction_amount float8 NOT NULL,
                        unit_price float8 NOT NULL,
                        number_of_units float8 NOT NULL
                    )""")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS fees (
                        id BIGSERIAL PRIMARY KEY,
                        investment_id BIGINT NOT NULL REFERENCES investments(id),
                        fee_date DATE NOT NULL,
                        fee_type VARCHAR(50) NOT NULL,
                        fee_paid float8 NOT NULL,
                        fee_frequency float8 NOT NULL,
                        number_of_units float8 NOT NULL,
                        investment_fee float8 NOT NULL
                    )""")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tax (
                        id BIGSERIAL PRIMARY KEY,
                        investment_id BIGINT NOT NULL REFERENCES investments(id),
                        tax_date DATE NOT NULL,
                        tax_type VARCHAR(50) NOT NULL,
                        tax_paid float8 NOT NULL,
                        tax_percentage float8 NOT NULL
                    )""")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dividends (
                        id BIGSERIAL PRIMARY KEY,
                        investment_id BIGINT NOT NULL REFERENCES investments(id),
                        dividend_date DATE NOT NULL,
                        dividend_frequency INTEGER NOT NULL,
                        dividend_recieved float8 NOT NULL,
                        dividend_percentage float8 NOT NULL
                    )""")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS investment_metrics (
                        id BIGSERIAL PRIMARY KEY,
                        investment_id BIGINT NOT NULL REFERENCES investments(id),
                        metrics_date DATE NOT NULL,
                        local_net_growth FLOAT8, local_total_return FLOAT8, local_return_multiple FLOAT8,
                        local_cagr FLOAT8, local_irr FLOAT8, local_total_fee_ratio FLOAT8,
                        local_total_tax_ratio FLOAT8, local_total_cost_ratio FLOAT8, local_dividend_yield FLOAT8,
                        local_fee_ratio_annualized FLOAT8, local_tax_ratio_annualized FLOAT8,
                        local_cost_ratio_annualized FLOAT8, local_dividend_yield_annualized FLOAT8,
                        local_total_contributions FLOAT8, local_total_fees FLOAT8, local_total_tax FLOAT8,
                        local_total_dividends FLOAT8, local_number_of_contributions INT,
                        local_average_contributions FLOAT8, local_investment_period FLOAT8,
                        local_real_net_growth FLOAT8, local_real_total_return FLOAT8, local_real_return_multiple FLOAT8,
                        local_real_cagr FLOAT8, local_real_irr FLOAT8, local_real_total_fee_ratio FLOAT8,
                        local_real_total_tax_ratio FLOAT8, local_real_total_cost_ratio FLOAT8,
                        local_real_dividend_yield FLOAT8, local_real_fee_ratio_annualized FLOAT8,
                        local_real_tax_ratio_annualized FLOAT8, local_real_cost_ratio_annualized FLOAT8,
                        local_real_dividend_yield_annualized FLOAT8, local_real_total_contributions FLOAT8,
                        local_real_total_fees FLOAT8, local_real_total_tax FLOAT8, local_real_total_dividends FLOAT8,
                        local_real_number_of_contributions INT, local_real_average_contributions FLOAT8,
                        local_real_investment_period FLOAT8, foreign_net_growth FLOAT8, foreign_total_return FLOAT8,
                        foreign_return_multiple FLOAT8, foreign_cagr FLOAT8, foreign_irr FLOAT8,
                        foreign_total_fee_ratio FLOAT8, foreign_total_tax_ratio FLOAT8, foreign_total_cost_ratio FLOAT8,
                        foreign_dividend_yield FLOAT8, foreign_fee_ratio_annualized FLOAT8,
                        foreign_tax_ratio_annualized FLOAT8, foreign_cost_ratio_annualized FLOAT8,
                        foreign_dividend_yield_annualized FLOAT8, foreign_total_contributions FLOAT8,
                        foreign_total_fees FLOAT8, foreign_total_tax FLOAT8, foreign_total_dividends FLOAT8,
                        foreign_number_of_contributions INT, foreign_average_contributions FLOAT8,
                        foreign_investment_period FLOAT8, foreign_real_net_growth FLOAT8,
                        foreign_real_total_return FLOAT8, foreign_real_return_multiple FLOAT8,
                        foreign_real_cagr FLOAT8, foreign_real_irr FLOAT8, foreign_real_total_fee_ratio FLOAT8,
                        foreign_real_total_tax_ratio FLOAT8, foreign_real_total_cost_ratio FLOAT8,
                        foreign_real_dividend_yield FLOAT8, foreign_real_fee_ratio_annualized FLOAT8,
                        foreign_real_tax_ratio_annualized FLOAT8, foreign_real_cost_ratio_annualized FLOAT8,
                        foreign_real_dividend_yield_annualized FLOAT8, foreign_real_total_contributions FLOAT8,
                        foreign_real_total_fees FLOAT8, foreign_real_total_tax FLOAT8, foreign_real_total_dividends FLOAT8,
                        foreign_real_number_of_contributions INT, foreign_real_average_contributions FLOAT8,
                        foreign_real_investment_period FLOAT8, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(investment_id, metrics_date)
                    )""")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS inflation (
                        id SERIAL PRIMARY KEY,
                        inflation_date DATE NOT NULL,
                        inflation_rate FLOAT8 NOT NULL,
                        country VARCHAR(100) NOT NULL,
                        currency VARCHAR(5) NOT NULL,
                        source VARCHAR(200),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(inflation_date, country)
                    )""")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS predictions (
                        id BIGSERIAL PRIMARY KEY,
                        prediction_date DATE NOT NULL,
                        model_name VARCHAR(100) NOT NULL,
                        scope VARCHAR(50) NOT NULL,
                        prediction_horizon_days INTEGER NOT NULL,
                        confidence_level FLOAT8 NOT NULL,
                        prediction_data JSONB NOT NULL,
                        historical_context JSONB,
                        accuracy_score FLOAT8,
                        risk_level FLOAT8,
                        actual_outcomes JSONB,
                        model_metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )""")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS configuration (
                        id BIGSERIAL PRIMARY KEY,
                        setting_key VARCHAR(100) NOT NULL UNIQUE,
                        setting_value TEXT,
                        setting_description TEXT,
                        setting_category VARCHAR(50) DEFAULT 'general',
                        is_editable BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )""")
                    
                    # Asset Manager URL Patterns - configurable per manager
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS asset_manager_url_patterns (
                        id BIGSERIAL PRIMARY KEY,
                        manager_name VARCHAR(200) NOT NULL,
                        manager_name_normalized VARCHAR(200) NOT NULL,  -- lowercase, stripped for matching
                        factsheet_type VARCHAR(50) NOT NULL DEFAULT 'MDD',  -- MDD, factsheet, annual_report, etc.
                        url_pattern TEXT NOT NULL,  -- supports {ticker}, {fund_slug}, {fund_code}
                        pattern_priority INTEGER DEFAULT 1,  -- lower = higher priority (tried first)
                        is_active BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(manager_name_normalized, factsheet_type, url_pattern)
                    )""")
                    
                    # Index for fast lookups
                    cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_asset_manager_patterns_lookup 
                    ON asset_manager_url_patterns (manager_name_normalized, factsheet_type, pattern_priority)
                    WHERE is_active = true
                    """)

                    # Exchange Rates Table (Historical OHLC reference table)
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS exchange_rates (
                        id BIGSERIAL PRIMARY KEY,
                        from_currency VARCHAR(5) NOT NULL,
                        to_currency VARCHAR(5) NOT NULL,
                        rate_date DATE NOT NULL,
                        open_rate FLOAT8,
                        high_rate FLOAT8,
                        low_rate FLOAT8,
                        close_rate FLOAT8 NOT NULL,
                        source_date DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(from_currency, to_currency, rate_date)
                    )""")
                    cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_exchange_rates_lookup
                    ON exchange_rates (from_currency, to_currency, rate_date)
                    """)
                    
                    # Standard configuration would follow... (kept minimal for space)

                if db_name == USERS_DB:
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGSERIAL PRIMARY KEY,
                        username VARCHAR(100) NOT NULL UNIQUE,
                        email VARCHAR(200) NOT NULL UNIQUE,
                        password_hash VARCHAR(200) NOT NULL,
                        full_name VARCHAR(200),
                        database_name VARCHAR(200) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )""")

                if db_name == INVESTMENTS_DB:
                     cursor.execute("""
                        CREATE OR REPLACE VIEW v_investment_prices AS
                        SELECT up.investment_id AS investment_id,
                               up.unit_price_date, up.unit_price,
                               up.unit_price_change, up.percentage_unit_price_change
                        FROM unit_prices up
                        UNION ALL
                        SELECT i.id AS investment_id,
                               up.unit_price_date, up.unit_price,
                               up.unit_price_change, up.percentage_unit_price_change
                        FROM investments i
                        JOIN unit_prices up ON up.investment_id = i.price_source_investment_id
                        WHERE i.price_source_investment_id IS NOT NULL
                    """)

                conn.commit()
                logger.info(f"✓ Tables created/verified in {db_name}")
            except Exception as e:
                conn.rollback()
                logger.error(f"✗ Failed to create tables in {db_name}: {e}")
                raise

def drop_all_tables(db_name):
    """Drop all tables in the given database (DANGEROUS)."""
    with get_db_connection(db_name) as conn:
        with conn.cursor() as cursor:
            try:
                if db_name == INVESTMENTS_DB:
                    tables = [
                        'prediction_accuracy', 'predictions', 'configuration', 'investment_metrics',
                        'portfolio_metrics', 'factsheets', 'investment_source_meta',
                        'property_investments', 'tax', 'fees', 'dividends', 'returns',
                        'transactions', 'unit_prices', 'investments', 'inflation', 'exchange_rates'
                    ]
                    for t in tables:
                        cursor.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
                elif db_name == USERS_DB:
                    cursor.execute("DROP TABLE IF EXISTS users CASCADE")
                
                conn.commit()
                logger.info(f"🗑️  All tables dropped in {db_name}")
            except Exception as e:
                conn.rollback()
                logger.error(f"✗ Failed to drop tables in {db_name}: {e}")
                raise

def reset_database():
    """Perform a full database reset (DANGEROUS)."""
    logger.warning("Starting full database reset...")
    drop_all_tables(INVESTMENTS_DB)
    drop_all_tables(USERS_DB)
    create_tables(INVESTMENTS_DB)
    create_tables(USERS_DB)
    logger.info("Database reset complete.")

if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_database()
    else:
        create_tables(INVESTMENTS_DB)
        create_tables(USERS_DB)
