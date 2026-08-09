#!/usr/bin/env python3

import os
import psycopg2

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "ThinkTank")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
INVESTMENTS_DB = os.getenv("INVESTMENTS_DB", "Investments")
USERS_DB = os.getenv("USERS_DB", "Users")

def create_tables(db_name):
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=db_name,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        port=POSTGRES_PORT
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
            
            -- Local (Nominal)
            local_net_growth FLOAT8,
            local_total_return FLOAT8,
            local_return_multiple FLOAT8,
            local_cagr FLOAT8,
            local_irr FLOAT8,
            local_total_fee_ratio FLOAT8,
            local_total_tax_ratio FLOAT8,
            local_total_cost_ratio FLOAT8,
            local_dividend_yield FLOAT8,
            local_fee_ratio_annualized FLOAT8,
            local_tax_ratio_annualized FLOAT8,
            local_cost_ratio_annualized FLOAT8,
            local_dividend_yield_annualized FLOAT8,
            local_total_contributions FLOAT8,
            local_total_fees FLOAT8,
            local_total_tax FLOAT8,
            local_total_dividends FLOAT8,
            local_number_of_contributions INT,
            local_average_contributions FLOAT8,
            local_investment_period FLOAT8,

            -- Local Inflation Adjusted (Real)
            local_real_net_growth FLOAT8,
            local_real_total_return FLOAT8,
            local_real_return_multiple FLOAT8,
            local_real_cagr FLOAT8,
            local_real_irr FLOAT8,
            local_real_total_fee_ratio FLOAT8,
            local_real_total_tax_ratio FLOAT8,
            local_real_total_cost_ratio FLOAT8,
            local_real_dividend_yield FLOAT8,
            local_real_fee_ratio_annualized FLOAT8,
            local_real_tax_ratio_annualized FLOAT8,
            local_real_cost_ratio_annualized FLOAT8,
            local_real_dividend_yield_annualized FLOAT8,
            local_real_total_contributions FLOAT8,
            local_real_total_fees FLOAT8,
            local_real_total_tax FLOAT8,
            local_real_total_dividends FLOAT8,
            local_real_number_of_contributions INT,
            local_real_average_contributions FLOAT8,
            local_real_investment_period FLOAT8,

            -- Foreign (Nominal)
            foreign_net_growth FLOAT8,
            foreign_total_return FLOAT8,
            foreign_return_multiple FLOAT8,
            foreign_cagr FLOAT8,
            foreign_irr FLOAT8,
            foreign_total_fee_ratio FLOAT8,
            foreign_total_tax_ratio FLOAT8,
            foreign_total_cost_ratio FLOAT8,
            foreign_dividend_yield FLOAT8,
            foreign_fee_ratio_annualized FLOAT8,
            foreign_tax_ratio_annualized FLOAT8,
            foreign_cost_ratio_annualized FLOAT8,
            foreign_dividend_yield_annualized FLOAT8,
            foreign_total_contributions FLOAT8,
            foreign_total_fees FLOAT8,
            foreign_total_tax FLOAT8,
            foreign_total_dividends FLOAT8,
            foreign_number_of_contributions INT,
            foreign_average_contributions FLOAT8,
            foreign_investment_period FLOAT8,

            -- Foreign Inflation Adjusted (Real)
            foreign_real_net_growth FLOAT8,
            foreign_real_total_return FLOAT8,
            foreign_real_return_multiple FLOAT8,
            foreign_real_cagr FLOAT8,
            foreign_real_irr FLOAT8,
            foreign_real_total_fee_ratio FLOAT8,
            foreign_real_total_tax_ratio FLOAT8,
            foreign_real_total_cost_ratio FLOAT8,
            foreign_real_dividend_yield FLOAT8,
            foreign_real_fee_ratio_annualized FLOAT8,
            foreign_real_tax_ratio_annualized FLOAT8,
            foreign_real_cost_ratio_annualized FLOAT8,
            foreign_real_dividend_yield_annualized FLOAT8,
            foreign_real_total_contributions FLOAT8,
            foreign_real_total_fees FLOAT8,
            foreign_real_total_tax FLOAT8,
            foreign_real_total_dividends FLOAT8,
            foreign_real_number_of_contributions INT,
            foreign_real_average_contributions FLOAT8,
            foreign_real_investment_period FLOAT8,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            actual_outcomes JSONB, -- To be populated when real results are available
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

        # Insert default configuration settings
        cursor.execute("""
        INSERT INTO configuration (setting_key, setting_value, setting_description, setting_category, is_editable)
        VALUES
            ('native_currency', 'R', 'Default native currency for the application (symbol)', 'currency', true),
            ('pdf_report_frequency', 'monthly', 'How often PDF reports should be generated (daily, weekly, monthly, quarterly, annually)', 'reporting', true),
            ('base_currency', 'ZAR', 'Base currency for portfolio calculations and display', 'currency', true),
            ('risk_tolerance', 'medium', 'Default risk tolerance level for recommendations (low, medium, high)', 'risk', true),
            ('email_notifications', 'true', 'Whether to send email notifications for reports', 'communication', true),
            ('auto_update_prices', 'true', 'Whether to automatically update investment prices from external sources', 'automation', true),
            ('report_timezone', 'Africa/Johannesburg', 'Timezone for report timestamps and scheduling', 'reporting', true),
            ('chart_theme', 'default', 'Color theme for charts (default, dark, colorful)', 'display', true),
            ('performance_calculation_method', 'time_weighted', 'Method for calculating portfolio returns (time_weighted, money_weighted)', 'calculation', true),
            ('max_chart_period_days', '3650', 'Maximum days to show in historical charts (default 10 years)', 'display', true),
            ('cgt_inclusion_rate', '0.40', 'Capital Gains Tax inclusion rate for individuals (fraction)', 'tax', true),
            ('cgt_marginal_tax_rate', '0.45', 'Assumed marginal income tax rate for CGT calc (fraction)', 'tax', true),
            ('cgt_annual_exclusion', '40000', 'Annual CGT exclusion for individuals (in base currency)', 'tax', true),
            ('cgt_primary_residence_exclusion', '2000000', 'CGT exclusion for the sale of a primary residence (in base currency)', 'tax', true),
            ('default_projection_years', '20', 'Default property projection horizon in years', 'property', true),
            ('monte_carlo_simulations', '1000', 'Default number of Monte Carlo simulations', 'property', true),
            ('default_bond_interest_rate', '11.75', 'Default property bond interest rate (percent)', 'property', true),
            ('default_rental_growth_rate', '5.0', 'Default annual rental growth rate (percent)', 'property', true),
            ('default_vacancy_rate', '5.0', 'Default vacancy rate (percent)', 'property', true),
            ('default_property_growth_rate', '7.0', 'Default annual property value growth (percent)', 'property', true),
            ('default_inflation_rate', '5.0', 'Default long-term inflation rate (percent)', 'property', true),
            ('scheduler_daily_hour', '11', 'Hour (SAST) for daily price fetch scheduler', 'automation', true),
            ('scheduler_daily_minute', '30', 'Minute for daily price fetch scheduler', 'automation', true),
            ('scheduler_factsheet_day', '20', 'Day of month for monthly factsheet download', 'automation', true),
            ('prediction_horizon_days', '30', 'Default prediction horizon in days', 'predictions', true)
        ON CONFLICT (setting_key) DO NOTHING
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_accuracy (
            id BIGSERIAL PRIMARY KEY,
            prediction_id BIGINT NOT NULL REFERENCES predictions(id),
            actual_date DATE NOT NULL,
            predicted_value FLOAT8 NOT NULL,
            actual_value FLOAT8 NOT NULL,
            prediction_error FLOAT8 NOT NULL,
            percentage_error FLOAT8 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(prediction_id, actual_date)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS investment_source_meta (
            id BIGSERIAL PRIMARY KEY,
            investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
            source VARCHAR(50) NOT NULL DEFAULT 'yfinance',  -- 'yfinance', 'profiledata', 'manual'
            source_ticker VARCHAR(200),
            profiledata_manager VARCHAR(200),
            profiledata_fund VARCHAR(200),
            profiledata_class VARCHAR(50),
            last_fetched TIMESTAMP,
            backfill_complete BOOLEAN DEFAULT false,
            backfill_cursor DATE,
            UNIQUE(investment_id)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS factsheets (
            id BIGSERIAL PRIMARY KEY,
            investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
            factsheet_date DATE NOT NULL,
            factsheet_type VARCHAR(50) DEFAULT 'MDD',  -- 'MDD', 'factsheet', 'annual_report'
            factsheet_year INTEGER NOT NULL,
            factsheet_month INTEGER NOT NULL,
            source_url TEXT,
            file_path TEXT,
            file_name VARCHAR(300),
            file_size_bytes INTEGER,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(investment_id, factsheet_year, factsheet_month, factsheet_type)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_metrics (
            id BIGSERIAL PRIMARY KEY,
            metrics_date DATE NOT NULL,
            dimension_type VARCHAR(50) NOT NULL,   -- 'investment_type', 'institution', 'account_type', 'portfolio'
            dimension_value VARCHAR(200) NOT NULL, -- e.g. 'ETF', 'Allan Gray', 'Tax Free', 'All'
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(metrics_date, dimension_type, dimension_value)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS property_investments (
            id BIGSERIAL PRIMARY KEY,
            investment_id BIGINT NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
            property_name VARCHAR(300) NOT NULL,
            property_url TEXT,
            property_address TEXT,
            property_type VARCHAR(100),  -- 'apartment', 'house', 'commercial', 'sectional_title'
            -- Purchase
            purchase_price FLOAT8,
            transfer_costs FLOAT8,
            transfer_duty FLOAT8,
            bond_registration_costs FLOAT8,
            other_acquisition_costs FLOAT8,
            total_acquisition_cost FLOAT8,  -- computed: purchase + all costs
            -- Bond / Finance
            deposit_amount FLOAT8,
            bond_amount FLOAT8,
            bond_interest_rate FLOAT8,     -- annual %
            bond_term_years INTEGER,
            bond_monthly_repayment FLOAT8, -- computed via PMT formula
            -- Monthly costs
            monthly_levy FLOAT8 DEFAULT 0,
            monthly_rates FLOAT8 DEFAULT 0,
            monthly_insurance FLOAT8 DEFAULT 0,
            monthly_maintenance_reserve FLOAT8 DEFAULT 0,
            monthly_management_fee_pct FLOAT8 DEFAULT 0,  -- % of rental
            monthly_other_costs FLOAT8 DEFAULT 0,
            -- Rental income
            monthly_rental_income FLOAT8 DEFAULT 0,
            rental_growth_rate_pa FLOAT8 DEFAULT 0.05,  -- 5% default
            vacancy_rate_pct FLOAT8 DEFAULT 0.05,        -- 5% default
            -- Growth assumptions
            property_growth_rate_pa FLOAT8 DEFAULT 0.07,  -- 7% default
            inflation_rate FLOAT8 DEFAULT 0.05,
            -- Calculated results (stored)
            gross_rental_yield FLOAT8,
            net_rental_yield FLOAT8,
            monthly_shortfall_surplus FLOAT8,
            irr_10yr FLOAT8,
            irr_20yr FLOAT8,
            break_even_years FLOAT8,
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(investment_id)
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

    # Shared-price support: investments holding the same asset in different
    # accounts can point at a single "price master" investment via
    # investments.price_source_investment_id.  The view below resolves each
    # investment's effective price series (its own unit_prices rows, or its
    # master's), so calculations only ever see one copy of the price history.
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
    cursor.close()
    conn.close()
    print(f"Tables created in {db_name} database")

def drop_all_tables(db_name):
    """Drop all tables in the database (dangerous - use with caution!)."""
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=db_name,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        port=POSTGRES_PORT
    )
    cursor = conn.cursor()

    if db_name == INVESTMENTS_DB:
        tables_to_drop = [
            'prediction_accuracy', 'predictions', 'configuration', 'investment_metrics',
            'portfolio_metrics', 'factsheets', 'investment_source_meta',
            'property_investments',
            'tax', 'fees', 'dividends', 'returns', 'transactions',
            'unit_prices', 'investments', 'inflation'
        ]

        print(f"🗑️  Dropping all tables in {db_name} database...")
        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"✅ Dropped table: {table}")
            except Exception as e:
                print(f"⚠️  Could not drop {table}: {e}")

    if db_name == USERS_DB:
        try:
            cursor.execute("DROP TABLE IF EXISTS users CASCADE")
            print("✅ Dropped table: users")
        except Exception as e:
            print(f"⚠️  Could not drop users: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"🗑️  Table drop operations completed for {db_name}")

def reset_database_with_new_schema():
    """Complete database reset with new schema and test data."""
    print("🔄 Starting complete database reset with new schema...")
    print("=" * 60)

    # Step 1: Drop all existing tables
    drop_all_tables(INVESTMENTS_DB)
    drop_all_tables(USERS_DB)

    # Step 2: Recreate tables with new schema
    print("\n🏗️  Recreating tables with new schema...")
    create_tables(INVESTMENTS_DB)
    create_tables(USERS_DB)

    # Step 3: Populate default users
    print("\n👤 Populating default users...")
    try:
        user_conn = psycopg2.connect(
            host=POSTGRES_HOST, port=POSTGRES_PORT,
            user=POSTGRES_USER, password=POSTGRES_PASSWORD,
            database=USERS_DB
        )
        u_cursor = user_conn.cursor()
        u_cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            ('armin', 'armin@example.com', 'pbkdf2:sha256:test_hash_armin')
        )
        u_cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            ('demo', 'demo@example.com', 'pbkdf2:sha256:test_hash_demo')
        )
        user_conn.commit()
        u_cursor.close()
        user_conn.close()
        print("✅ Default users inserted into Users database")
    except Exception as e:
        print(f"⚠️ Could not insert default users: {e}")

    # Step 4: Populate with investment test data from Excel/seeder
    print("\n📊 Populating investments with test data...")
    try:
        from import_npv_excel import main as import_main
        import_main()
    except Exception as e:
        print(f"⚠️ Error running import_npv_excel: {e}")

    print("=" * 60)
    print("✅ Database reset with new schema completed!")
    print("\n🔧 Schema Changes:")
    print("   • All child tables now have unique auto-incrementing primary keys")
    print("   • Foreign key field renamed from 'id' to 'investment_id'")
    print("   • Composite unique constraints maintained where needed")
    print("\n🎯 Edit Data operations now work on individual rows!")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_database_with_new_schema()
    else:
        print("Usage: python create_tables.py --reset  # Complete database reset with new schema")
        print("Usage: python create_tables.py          # Normal table creation")
        create_tables(INVESTMENTS_DB)
        create_tables(USERS_DB)
