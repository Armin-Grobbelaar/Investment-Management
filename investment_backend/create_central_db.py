#!/usr/bin/env python3
"""
create_central_db.py
====================
Creates the central multi-tenant database (`investments_app`) with:
- Shared schema
- Foreign keys (`user_id REFERENCES users(id) ON DELETE CASCADE`)
- Proper indexing on `user_id` and query lookups
- PostgreSQL Row-Level Security (RLS) policies on all tenant tables
"""

import os
import psycopg2
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
CENTRAL_DB = os.getenv("POSTGRES_DB", "investments_app")

@contextmanager
def get_db_connection(db_name="postgres"):
    """Context manager for database connections."""
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=db_name,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        port=POSTGRES_PORT
    )
    try:
        yield conn
    finally:
        conn.close()

def create_database():
    """Create the central database if it doesn't exist."""
    with get_db_connection("postgres") as conn:
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (CENTRAL_DB,))
            if not cursor.fetchone():
                cursor.execute(f"CREATE DATABASE {CENTRAL_DB}")
                logger.info(f"✅ Created central database '{CENTRAL_DB}'")
            else:
                logger.info(f"ℹ️ Database '{CENTRAL_DB}' already exists")

def create_tables(target_db=CENTRAL_DB):
    """Create all tables with user_id, indices, and RLS in central database."""
    with get_db_connection(target_db) as conn:
        with conn.cursor() as cursor:
            # 1. Users table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                email VARCHAR(200) NOT NULL UNIQUE,
                password_hash VARCHAR(200) NOT NULL,
                full_name VARCHAR(200),
                database_name VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 2. Investments table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS investments (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                institution_name VARCHAR(200) NOT NULL,
                initial_investment_date DATE NOT NULL,
                investment_type VARCHAR(50) NOT NULL,
                investment_name VARCHAR(200),
                investment_ticker VARCHAR(50) NOT NULL,
                unit_currency VARCHAR(5) NOT NULL,
                initial_unit_price FLOAT8 NOT NULL,
                unit_price FLOAT8 NOT NULL,
                number_of_units_held FLOAT8 NOT NULL,
                total_dividends_received FLOAT8 NOT NULL,
                total_tax_paid FLOAT8 NOT NULL,
                total_fees_paid FLOAT8 NOT NULL,
                investment_fee FLOAT8 NOT NULL,
                investment_status VARCHAR(20) NOT NULL,
                investment_subtype VARCHAR(50),
                source_account VARCHAR(100),
                price_source_investment_id BIGINT REFERENCES investments(id)
            );
            """)

            # 3. Unit prices table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS unit_prices (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
                unit_price_date DATE NOT NULL,
                unit_price FLOAT8 NOT NULL,
                unit_price_change FLOAT8 NOT NULL,
                percentage_unit_price_change FLOAT8 NOT NULL,
                UNIQUE(investment_id, unit_price_date)
            );
            """)

            # 4. Transactions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
                transaction_date DATE NOT NULL,
                transaction_type VARCHAR(20) NOT NULL,
                transaction_amount FLOAT8 NOT NULL,
                unit_price FLOAT8 NOT NULL,
                number_of_units FLOAT8 NOT NULL
            );
            """)

            # 5. Returns table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS returns (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
                returns_date DATE NOT NULL,
                monthly_return FLOAT8 NOT NULL,
                quarterly_return FLOAT8 NOT NULL,
                half_yearly_return FLOAT8 NOT NULL,
                yearly_return FLOAT8 NOT NULL,
                yearly_3_return FLOAT8 NOT NULL,
                yearly_5_return FLOAT8 NOT NULL,
                return_since_inception FLOAT8 NOT NULL,
                UNIQUE(investment_id, returns_date)
            );
            """)

            # 6. Fees table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS fees (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
                fee_date DATE NOT NULL,
                fee_type VARCHAR(50) NOT NULL,
                fee_paid FLOAT8 NOT NULL,
                fee_frequency FLOAT8 NOT NULL,
                number_of_units FLOAT8 NOT NULL,
                investment_fee FLOAT8 NOT NULL
            );
            """)

            # 7. Tax table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tax (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
                tax_date DATE NOT NULL,
                tax_type VARCHAR(50) NOT NULL,
                tax_paid FLOAT8 NOT NULL,
                tax_percentage FLOAT8 NOT NULL
            );
            """)

            # 8. Dividends table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dividends (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
                dividend_date DATE NOT NULL,
                dividend_frequency INTEGER NOT NULL,
                dividend_recieved FLOAT8 NOT NULL,
                dividend_percentage FLOAT8 NOT NULL
            );
            """)

            # 9. Investment metrics table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS investment_metrics (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
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
            );
            """)

            # 10. Portfolio metrics table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_metrics (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                metrics_date DATE NOT NULL,
                dimension_type VARCHAR(50) NOT NULL,
                dimension_value VARCHAR(200) NOT NULL,
                total_contributions FLOAT8,
                total_current_value FLOAT8,
                total_return_amount FLOAT8,
                total_return_pct FLOAT8,
                cagr FLOAT8,
                irr FLOAT8,
                total_fees FLOAT8,
                total_dividends FLOAT8,
                total_tax FLOAT8,
                investment_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 11. Inflation table (Global shared reference)
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
            );
            """)

            # 12. Predictions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
            );
            """)

            # 13. Prediction accuracy table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_accuracy (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                prediction_id BIGINT NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
                actual_date DATE NOT NULL,
                predicted_value FLOAT8 NOT NULL,
                actual_value FLOAT8 NOT NULL,
                prediction_error FLOAT8 NOT NULL,
                percentage_error FLOAT8 NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 14. Property investments table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS property_investments (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
                property_name VARCHAR(300) NOT NULL,
                property_url TEXT,
                property_address TEXT,
                property_type VARCHAR(100),
                purchase_price FLOAT8,
                transfer_costs FLOAT8,
                transfer_duty FLOAT8,
                bond_registration_costs FLOAT8,
                other_acquisition_costs FLOAT8,
                total_acquisition_cost FLOAT8,
                deposit_amount FLOAT8,
                bond_amount FLOAT8,
                bond_interest_rate FLOAT8,
                bond_term_years INTEGER,
                bond_monthly_repayment FLOAT8,
                monthly_levy FLOAT8 DEFAULT 0,
                monthly_rates FLOAT8 DEFAULT 0,
                monthly_insurance FLOAT8 DEFAULT 0,
                monthly_maintenance_reserve FLOAT8 DEFAULT 0,
                monthly_management_fee_pct FLOAT8 DEFAULT 0,
                monthly_other_costs FLOAT8 DEFAULT 0,
                monthly_rental_income FLOAT8 DEFAULT 0,
                rental_growth_rate_pa FLOAT8 DEFAULT 0.05,
                vacancy_rate_pct FLOAT8 DEFAULT 0.05,
                property_growth_rate_pa FLOAT8 DEFAULT 0.07,
                inflation_rate FLOAT8 DEFAULT 0.05,
                gross_rental_yield FLOAT8,
                net_rental_yield FLOAT8,
                monthly_shortfall_surplus FLOAT8,
                irr_10yr FLOAT8,
                irr_20yr FLOAT8,
                break_even_years FLOAT8,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 15. Factsheets table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS factsheets (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
                factsheet_date DATE NOT NULL,
                factsheet_type VARCHAR(50) DEFAULT 'MDD',
                factsheet_year INTEGER NOT NULL,
                factsheet_month INTEGER NOT NULL,
                source_url TEXT,
                file_path TEXT,
                file_name VARCHAR(300),
                file_size_bytes INTEGER,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(investment_id, factsheet_year, factsheet_month, factsheet_type)
            );
            """)

            # 16. Investment source metadata table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS investment_source_meta (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
                source VARCHAR(50) DEFAULT 'yfinance' NOT NULL,
                source_ticker VARCHAR(200),
                profiledata_manager VARCHAR(200),
                profiledata_fund VARCHAR(200),
                profiledata_class VARCHAR(50),
                last_fetched TIMESTAMP,
                backfill_complete BOOLEAN DEFAULT false,
                backfill_cursor DATE
            );
            """)

            # 17. Configuration table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuration (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                setting_key VARCHAR(100) NOT NULL,
                setting_value TEXT,
                setting_description TEXT,
                setting_category VARCHAR(50) DEFAULT 'general',
                is_editable BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, setting_key)
            );
            """)

            # 18. Asset Manager URL Patterns (Global shared reference table)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS asset_manager_url_patterns (
                id BIGSERIAL PRIMARY KEY,
                manager_name VARCHAR(200) NOT NULL,
                manager_name_normalized VARCHAR(200) NOT NULL,
                factsheet_type VARCHAR(50) NOT NULL DEFAULT 'MDD',
                url_pattern TEXT NOT NULL,
                pattern_priority INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(manager_name_normalized, factsheet_type, url_pattern)
            );
            """)

            # 19. Exchange Rates Table (Historical OHLC reference table)
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
            );
            """)

            # ── 20. Indices on user_id for fast tenant query filtering ─────────
            user_tables = [
                "investments", "unit_prices", "transactions", "returns", "fees",
                "tax", "dividends", "investment_metrics", "portfolio_metrics",
                "predictions", "prediction_accuracy", "property_investments",
                "factsheets", "investment_source_meta", "configuration"
            ]
            for tbl in user_tables:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{tbl}_user_id ON {tbl}(user_id);")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exchange_rates_lookup ON exchange_rates (from_currency, to_currency, rate_date);")

            # ── 21. Enable Row-Level Security (RLS) and Create Isolation Policies ────────
            for tbl in user_tables:
                cursor.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
                cursor.execute(f"DROP POLICY IF EXISTS user_isolation_policy ON {tbl};")
                cursor.execute(f"""
                CREATE POLICY user_isolation_policy ON {tbl}
                    USING (user_id = current_setting('app.current_user_id', true)::bigint);
                """)

            # ── 22. Create View v_investment_prices ─────────────────────────────
            cursor.execute("""
            CREATE OR REPLACE VIEW v_investment_prices AS
            SELECT up.user_id, up.investment_id, up.unit_price_date, up.unit_price,
                   up.unit_price_change, up.percentage_unit_price_change
            FROM unit_prices up
            UNION ALL
            SELECT i.user_id, i.id AS investment_id, up.unit_price_date, up.unit_price,
                   up.unit_price_change, up.percentage_unit_price_change
            FROM investments i
            JOIN unit_prices up ON up.investment_id = i.price_source_investment_id
            WHERE i.price_source_investment_id IS NOT NULL;
            """)

            conn.commit()
            logger.info("✅ All multi-tenant tables, indices, RLS policies, and views created/verified.")

if __name__ == "__main__":
    create_database()
    create_tables()
