import os
import psycopg2
from psycopg2.extensions import AsIs, ISOLATION_LEVEL_AUTOCOMMIT
from contextlib import contextmanager

# Configuration constants
DB_HOST = os.environ.get("POSTGRES_HOST", "ThinkTank")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "changeme")
DB_PORT = int(os.environ.get("POSTGRES_PORT", 5432))
DEFAULT_DB = os.environ.get("INVESTMENTS_DB", "Investments")
USERS_DB = os.environ.get("USERS_DB", "Users")

@contextmanager
def get_db_connection(database_name):
    """Context manager for database connections."""
    conn = psycopg2.connect(
        host=DB_HOST,
        database=database_name,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    try:
        yield conn, conn.cursor()
    finally:
        conn.close()

def create_connection(database_name):
    """
    Legacy connection creator. 
    Note: It's better to use get_db_connection context manager.
    """
    global investment_database_connection
    global investment_database_cursor

    investment_database_connection = psycopg2.connect(
        host=DB_HOST, 
        database=database_name, 
        user=DB_USER, 
        password=DB_PASSWORD, 
        port=DB_PORT
    )

    investment_database_cursor = investment_database_connection.cursor()
    return investment_database_connection, investment_database_cursor

def add_user(name, surname):
    """Add a new user and create their database."""
    # Connect to postgres db to create new db
    database_connection = psycopg2.connect(
        host=DB_HOST, 
        database="postgres", 
        user=DB_USER, 
        password=DB_PASSWORD, 
        port=DB_PORT
    )
    database_connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    database_cursor = database_connection.cursor()
    
    import re
    # Sanitize: only allow lowercase alphanumeric + underscores in the identifier
    sanitized_name = re.sub(r'[^a-z0-9_]', '_', name.lower())[:63]
    database_name = sanitized_name + "_investment_database"
    # psycopg2 cannot parameterise identifiers in CREATE DATABASE; use AsIs with the
    # now-sanitised value (only [a-z0-9_] chars are present).
    database_cursor.execute("CREATE database %s", (AsIs(database_name), ))
    database_connection.commit()
    database_cursor.close()
    database_connection.close()

    # Add user to Users db
    user_database_connection = psycopg2.connect(
        host=DB_HOST, 
        database=USERS_DB, 
        user=DB_USER, 
        password=DB_PASSWORD, 
        port=DB_PORT
    )
    user_database_cursor = user_database_connection.cursor()
    user_database_cursor.execute(
        "INSERT INTO users (name, surname, database_name) VALUES (%s, %s, %s)", 
        (name, surname, database_name)
    )
    user_database_connection.commit()
    user_database_cursor.close()
    user_database_connection.close()

    # Initialize the new database
    investment_database_connection = psycopg2.connect(
        host=DB_HOST, 
        database=database_name, 
        user=DB_USER, 
        password=DB_PASSWORD, 
        port=DB_PORT
    )
    investment_database_cursor = investment_database_connection.cursor()
    
    # Create tables
    investment_database_cursor.execute("CREATE TABLE investments (id BIGSERIAL NOT NULL PRIMARY KEY, institution_name VARCHAR(200) NOT NULL, initial_investment_date DATE NOT NULL, investment_type VARCHAR(50) NOT NULL, investment_name VARCHAR(200), investment_ticker VARCHAR(50) NOT NULL UNIQUE, unit_currency VARCHAR(5) NOT NULL, initial_unit_price float8 NOT NULL, unit_price float8 NOT NULL, number_of_units_held float8 NOT NULL, total_dividends_received float8 NOT NULL, total_tax_paid float8 NOT NULL, total_fees_paid float8 NOT NULL, investment_fee float8 NOT NULL, investment_status VARCHAR(20) NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE unit_prices (id BIGINT NOT NULL REFERENCES investments(id), unit_price_date DATE NOT NULL, unit_price float8 NOT NULL, unit_price_change float8 NOT NULL, percentage_unit_price_change float8 NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE returns (id BIGINT NOT NULL REFERENCES investments(id), returns_date DATE NOT NULL, monthly_return float8 NOT NULL, quarterly_return float8 NOT NULL, half_yearly_return float8 NOT NULL, yearly_return float8 NOT NULL, yearly_3_return float8 NOT NULL, yearly_5_return float8 NOT NULL, return_since_inception float8 NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE transactions (id BIGINT NOT NULL REFERENCES investments(id), transaction_date DATE NOT NULL, transaction_type VARCHAR(20) NOT NULL, transaction_amount float8 NOT NULL, unit_price float8 NOT NULL, number_of_units float8 NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE dividends (id BIGINT NOT NULL REFERENCES investments(id), dividend_date DATE NOT NULL, dividend_frequency int NOT NULL, dividend_recieved float8 NOT NULL, dividend_percentage float8 NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE fees (id BIGINT NOT NULL REFERENCES investments(id), fee_date DATE NOT NULL, fee_type VARCHAR(50), fee_paid float8 NOT NULL, fee_frequency float8 NOT  NULL, number_of_units float8 NOT NULL, investment_fee float8 NOT NULL)")
    investment_database_cursor.execute("CREATE TABLE tax (id BIGINT NOT NULL REFERENCES investments(id), tax_date DATE NOT NULL, tax_paid float8 NOT NULL, tax_percentage float8 NOT NULL)")
    
    investment_database_cursor.close()
    investment_database_connection.close()

# ---------------------------------------------------------------------------
# Configuration helpers — read from the `configuration` table
# ---------------------------------------------------------------------------
_config_cache: dict = {}
_config_cache_expiry = None
_CONFIG_CACHE_TTL = 300  # seconds

def get_config_value(key: str, default=None, database_name: str = None):
    """Read a single setting_value from the configuration table.
    
    Results are cached in-process for CONFIG_CACHE_TTL seconds to avoid
    hammering the DB on every request.
    """
    import time
    from datetime import datetime, timedelta

    global _config_cache, _config_cache_expiry

    db = database_name or DEFAULT_DB

    now = time.time()
    if _config_cache_expiry and now < _config_cache_expiry and db in _config_cache:
        return _config_cache[db].get(key, default)

    # Rebuild cache from DB
    try:
        with get_db_connection(db) as (conn, cursor):
            cursor.execute("SELECT setting_key, setting_value FROM configuration")
            cache = {row[0]: row[1] for row in cursor.fetchall()}
        _config_cache[db] = cache
        _config_cache_expiry = now + _CONFIG_CACHE_TTL
    except Exception:
        # If table doesn't exist yet or DB error, return default silently
        return default

    return _config_cache.get(db, {}).get(key, default)


def get_all_config(database_name: str = None) -> dict:
    """Return the full configuration dict from the configuration table."""
    db = database_name or DEFAULT_DB
    import time

    global _config_cache, _config_cache_expiry
    now = time.time()

    if _config_cache_expiry and now < _config_cache_expiry and db in _config_cache:
        return dict(_config_cache[db])

    try:
        with get_db_connection(db) as (conn, cursor):
            cursor.execute(
                "SELECT setting_key, setting_value, setting_description, setting_category "
                "FROM configuration ORDER BY setting_category, setting_key"
            )
            cache = {}
            for row in cursor.fetchall():
                cache[row[0]] = row[1]  # key -> value
            _config_cache[db] = cache
            _config_cache_expiry = now + _CONFIG_CACHE_TTL
            return dict(cache)
    except Exception:
        return {}


def invalidate_config_cache(database_name: str = None):
    """Clear the in-memory config cache (call after config is updated)."""
    global _config_cache, _config_cache_expiry
    _config_cache = {}
    _config_cache_expiry = None
