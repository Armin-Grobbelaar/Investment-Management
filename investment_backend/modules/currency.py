import pandas as pd
from .database import get_db_connection, DEFAULT_DB, get_config_value

# Currency symbols mapping (for storage - original currencies)
CURRENCY_SYMBOLS = {"R": "ZAR", "€": "EUR", "£": "GBP", "$": "USD"}

# Native currency symbol, sourced from the configuration table so it can be
# changed at runtime (e.g. from "R" for South Africa to "$" for a US user)
# without touching code.
NATIVE_CURRENCY = get_config_value("native_currency", "R") or "R"

# Supported base currencies for display conversion (frontend selectable).
# Sourced from the configuration table; the base_currency key defines which
# one is the default display currency.
DEFAULT_BASE_CURRENCY = get_config_value("base_currency", "ZAR") or "ZAR"
SUPPORTED_BASE_CURRENCIES = ["ZAR", "USD", "EUR", "GBP"]


def resolve_currency_code(value: str) -> str:
    """Map a currency symbol or code to its ISO code (e.g. 'R' -> 'ZAR').

    The configuration table stores the base currency as an ISO code ('ZAR'),
    while individual investments may store a symbol ('R'). This helper makes
    comparisons safe regardless of which form is used.
    """
    if not value:
        return DEFAULT_BASE_CURRENCY
    value = value.strip()
    if value in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[value]
    return value.upper()


def currency_display_symbol(code: str) -> str:
    """Return the display symbol for an ISO currency code (e.g. 'ZAR' -> 'R')."""
    code = resolve_currency_code(code).upper()
    for symbol, iso in CURRENCY_SYMBOLS.items():
        if iso == code:
            return symbol
    return code


# ISO code for the configured base currency (used for "local" metrics and
# for converting foreign investment cash flows into the reporting currency).
BASE_CURRENCY_CODE = resolve_currency_code(DEFAULT_BASE_CURRENCY)

def get_exchange_rate(from_currency: str, to_currency: str, date: str = None, database_name: str = DEFAULT_DB, cursor=None) -> float:
    """
    Get exchange rate between two currencies.

    Args:
        from_currency: Source currency code (e.g., "USD")
        to_currency: Target currency code (e.g., "ZAR")
        date: Date for exchange rate (optional, uses latest if not provided)
        database_name: Database name
        cursor: Optional database cursor to reuse existing connection

    Returns:
        Exchange rate (how many to_currency units = 1 from_currency unit)
    """
    if from_currency == to_currency:
        return 1.0

    # Helper function to execute query
    def execute_query(query, params):
        if cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
        else:
            with get_db_connection(database_name) as (conn, temp_cursor):
                temp_cursor.execute(query, params)
                return temp_cursor.fetchone()

    # Find forex investment for this currency pair
    ticker = f"{from_currency}{to_currency}=X"
    
    # Check direct pair
    query = "SELECT id FROM investments WHERE investment_type = 'Forex' AND investment_ticker = %s"
    forex_id = execute_query(query, (ticker,))

    if not forex_id:
        # Try reverse pair
        reverse_ticker = f"{to_currency}{from_currency}=X"
        forex_id = execute_query(query, (reverse_ticker,))
        
        if forex_id:
            # Use inverse rate
            rate_query = """
                SELECT unit_price FROM v_investment_prices
                WHERE investment_id = %s
            """
            if date:
                rate_query += " AND unit_price_date <= %s"
            rate_query += " ORDER BY unit_price_date DESC LIMIT 1"

            result = execute_query(rate_query, (forex_id[0], date) if date else (forex_id[0],))
            return 1.0 / result[0] if result and result[0] != 0 else 1.0
        else:
            return 1.0  # No conversion available

    # Get direct rate
    rate_query = "SELECT unit_price FROM v_investment_prices WHERE investment_id = %s"
    if date:
        rate_query += " AND unit_price_date <= %s"
    rate_query += " ORDER BY unit_price_date DESC LIMIT 1"

    result = execute_query(rate_query, (forex_id[0], date) if date else (forex_id[0],))
    return result[0] if result else 1.0

def convert_currency_amount(amount: float, from_currency: str, to_currency: str, date: str = None, database_name: str = DEFAULT_DB, cursor=None, rate_cache=None) -> float:
    """
    Convert monetary amount from one currency to another.

    Args:
        amount: Amount in from_currency
        from_currency: Source currency code
        to_currency: Target currency code
        date: Date for exchange rate (optional)
        database_name: Database name
        cursor: Optional database cursor
        rate_cache: Optional dictionary for caching rates

    Returns:
        Converted amount in to_currency
    """
    # Check cache first
    cache_key = (from_currency, to_currency, date)
    if rate_cache is not None and cache_key in rate_cache:
        exchange_rate = rate_cache[cache_key]
    else:
        exchange_rate = get_exchange_rate(from_currency, to_currency, date, database_name, cursor)
        if rate_cache is not None:
            rate_cache[cache_key] = exchange_rate
            
    return amount * exchange_rate

def convert_investment_data_for_display(df: pd.DataFrame, base_currency: str = None, database_name: str = DEFAULT_DB) -> pd.DataFrame:
    """
    Convert investment data monetary values to specified base currency for display.
    Optimized to use a single database connection and cache exchange rates.

    Args:
        df: DataFrame with investment data
        base_currency: Target base currency code
        database_name: Database name

    Returns:
        DataFrame with converted monetary values
    """
    if base_currency is None:
        base_currency = DEFAULT_BASE_CURRENCY

    # Accept display symbols ('R') as well as ISO codes ('ZAR') by resolving
    # symbols to their ISO code before validation/conversion.
    if isinstance(base_currency, str):
        base_currency = resolve_currency_code(base_currency)

    if df.empty or base_currency not in SUPPORTED_BASE_CURRENCIES:
        return df

    df_copy = df.copy()

    # Monetary columns to convert (if they exist)
    monetary_columns = [
        "unit_price", "initial_unit_price", "investment_value",
        "total_dividends_received", "total_tax_paid", "total_fees_paid"
    ]

    # Use a single connection for all conversions
    rate_cache = {}
    
    with get_db_connection(database_name) as (conn, cursor):
        for col in monetary_columns:
            if col in df_copy.columns and "unit_currency" in df_copy.columns:
                # Convert each row individually since exchange rates may vary by date
                converted_values = []
                for idx, row in df_copy.iterrows():
                    original_currency = row.get("unit_currency", NATIVE_CURRENCY)
                    if isinstance(original_currency, str) and len(original_currency) == 1:
                        # Map currency symbol to code
                        currency_code = CURRENCY_SYMBOLS.get(original_currency, original_currency)
                    else:
                        currency_code = original_currency

                    # Get date for conversion (use unit_price_date if available, otherwise today)
                    conversion_date = row.get("unit_price_date") if hasattr(row, "unit_price_date") and pd.notna(row.get("unit_price_date")) else None
                    if conversion_date:
                        if isinstance(conversion_date, pd.Timestamp):
                            conversion_date = conversion_date.strftime("%Y-%m-%d")
                        elif hasattr(conversion_date, 'date'):  # datetime object
                            conversion_date = conversion_date.date().isoformat()

                    converted_value = convert_currency_amount(
                        row[col], currency_code, base_currency, conversion_date, database_name, 
                        cursor=cursor, rate_cache=rate_cache
                    )
                    converted_values.append(converted_value)

                df_copy[col] = converted_values

    # Update currency column to reflect base currency
    df_copy["unit_currency"] = base_currency
    df_copy["display_currency"] = base_currency  # Add explicit display currency column

    return df_copy

def get_available_base_currencies() -> list:
    """Return list of available base currencies for frontend selection."""
    return SUPPORTED_BASE_CURRENCIES
