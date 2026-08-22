import os
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Tuple
from .database import get_db_connection, DEFAULT_DB, get_config_value

CURRENCY_SYMBOLS = {"R": "ZAR", "€": "EUR", "£": "GBP", "$": "USD"}
NATIVE_CURRENCY = get_config_value("native_currency", "R") or "R"
DEFAULT_BASE_CURRENCY = get_config_value("base_currency", "ZAR") or "ZAR"

_supported_env = os.environ.get("SUPPORTED_BASE_CURRENCIES")
if _supported_env:
    SUPPORTED_BASE_CURRENCIES = [c.strip().upper() for c in _supported_env.split(",") if c.strip()]
else:
    SUPPORTED_BASE_CURRENCIES = ["ZAR", "USD", "EUR", "GBP"]

def resolve_currency_code(value: str) -> str:
    """Map a currency symbol or code to its ISO code (e.g. 'R' -> 'ZAR')."""
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

BASE_CURRENCY_CODE = resolve_currency_code(DEFAULT_BASE_CURRENCY)

# In-memory FX rate cache: (from_currency, to_currency, target_date_str) -> (rate, source_date_str)
_FX_RATE_CACHE: Dict[Tuple[str, str, str], Tuple[float, str]] = {}

def get_exchange_rate(
    from_currency: str,
    to_currency: str,
    target_date: Optional[str] = None,
    database_name: str = DEFAULT_DB,
    cursor=None
) -> Tuple[float, str]:
    """
    Get the historical exchange rate from stored `exchange_rates` database table.
    
    Uses exact date match if available. If markets were closed (weekend/holiday),
    falls back to the most recent prior trading day's closing rate.
    
    Returns:
        Tuple of (rate, source_date_used_str)
    """
    from_curr = resolve_currency_code(from_currency)
    to_curr = resolve_currency_code(to_currency)

    if from_curr == to_curr:
        dt_str = str(target_date) if target_date else date.today().isoformat()
        return 1.0, dt_str

    target_date_str = str(target_date) if target_date else date.today().isoformat()
    cache_key = (from_curr, to_curr, target_date_str)

    if cache_key in _FX_RATE_CACHE:
        return _FX_RATE_CACHE[cache_key]

    def _query(query_str, params):
        if cursor:
            cursor.execute(query_str, params)
            return cursor.fetchone()
        else:
            with get_db_connection(database_name) as (conn, temp_cursor):
                temp_cursor.execute(query_str, params)
                return temp_cursor.fetchone()

    # 1. Direct query: exact date or closest prior date
    query_direct = """
        SELECT close_rate, rate_date FROM exchange_rates
        WHERE from_currency = %s AND to_currency = %s AND rate_date <= %s
        ORDER BY rate_date DESC LIMIT 1
    """
    res = _query(query_direct, (from_curr, to_curr, target_date_str))

    if res and res[0]:
        rate, src_date = float(res[0]), str(res[1])
        _FX_RATE_CACHE[cache_key] = (rate, src_date)
        return rate, src_date

    # 2. Reverse pair query: (e.g. ZAR -> USD inverse of USD -> ZAR)
    query_reverse = """
        SELECT close_rate, rate_date FROM exchange_rates
        WHERE from_currency = %s AND to_currency = %s AND rate_date <= %s
        ORDER BY rate_date DESC LIMIT 1
    """
    res_rev = _query(query_reverse, (to_curr, from_curr, target_date_str))

    if res_rev and res_rev[0] and float(res_rev[0]) != 0:
        rate, src_date = 1.0 / float(res_rev[0]), str(res_rev[1])
        _FX_RATE_CACHE[cache_key] = (rate, src_date)
        return rate, src_date

    # 3. Fallback: check unit_prices forex pseudo-investments for backward compatibility
    query_legacy = """
        SELECT up.unit_price, up.unit_price_date FROM unit_prices up
        JOIN investments i ON i.id = up.investment_id
        WHERE i.investment_type = 'Forex' AND i.investment_ticker = %s AND up.unit_price_date <= %s
        ORDER BY up.unit_price_date DESC LIMIT 1
    """
    ticker = f"{from_curr}{to_curr}=X"
    res_leg = _query(query_legacy, (ticker, target_date_str))

    if res_leg and res_leg[0]:
        rate, src_date = float(res_leg[0]), str(res_leg[1])
        _FX_RATE_CACHE[cache_key] = (rate, src_date)
        return rate, src_date

    # Final fallback if no rate data exists at all
    _FX_RATE_CACHE[cache_key] = (1.0, target_date_str)
    return 1.0, target_date_str

def convert_currency_amount(
    amount: float,
    from_currency: str,
    to_currency: str,
    target_date: Optional[str] = None,
    database_name: str = DEFAULT_DB,
    cursor=None,
    rate_cache: Optional[Dict] = None
) -> float:
    """Convert monetary amount from one currency to another using historical rate.

    Args:
        rate_cache: Optional dict used as a caller-managed cache to avoid
                    repeated DB lookups during batch conversions (e.g. metrics).
    """
    if amount == 0:
        return 0.0
    from_curr = resolve_currency_code(from_currency)
    to_curr = resolve_currency_code(to_currency)
    if from_curr == to_curr:
        return amount
    target_date_str = str(target_date) if target_date else date.today().isoformat()

    # Check caller-managed cache first
    if rate_cache is not None:
        cache_key = (from_curr, to_curr, target_date_str)
        if cache_key in rate_cache:
            return amount * rate_cache[cache_key]
        rate, _ = get_exchange_rate(from_curr, to_curr, target_date_str, database_name, cursor)
        rate_cache[cache_key] = rate
        return amount * rate

    rate, _ = get_exchange_rate(from_curr, to_curr, target_date_str, database_name, cursor)
    return amount * rate

def sync_historical_exchange_rates(
    pairs: Optional[list] = None,
    database_name: str = DEFAULT_DB,
    period: str = "max"
) -> int:
    """
    Fetch daily historical OHLC FX rates from Yahoo Finance and store in `exchange_rates`.
    
    Pairs default: USDZAR=X, EURZAR=X, GBPZAR=X.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("⚠️ yfinance not installed — skipping FX rate sync.")
        return 0

    if not pairs:
        pairs = [("USD", "ZAR"), ("EUR", "ZAR"), ("GBP", "ZAR")]

    total_inserted = 0

    with get_db_connection(database_name) as (conn, cursor):
        for from_curr, to_curr in pairs:
            ticker = f"{from_curr}{to_curr}=X"
            print(f"🔄 Syncing FX rates for {ticker} (period={period})...")
            try:
                data = yf.download(ticker, period=period, auto_adjust=True, progress=False)
                if data.empty:
                    continue

                for idx, row in data.iterrows():
                    r_date = idx.date() if hasattr(idx, 'date') else idx
                    
                    def _get_val(col_name):
                        if col_name not in row:
                            return None
                        val = row[col_name]
                        return float(val.iloc[0]) if hasattr(val, 'iloc') else float(val)

                    c_rate = _get_val('Close')
                    o_rate = _get_val('Open')
                    h_rate = _get_val('High')
                    l_rate = _get_val('Low')

                    if c_rate is None or c_rate <= 0:
                        continue

                    cursor.execute("""
                        INSERT INTO exchange_rates (
                            from_currency, to_currency, rate_date,
                            open_rate, high_rate, low_rate, close_rate, source_date
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (from_currency, to_currency, rate_date)
                        DO UPDATE SET
                            open_rate = EXCLUDED.open_rate,
                            high_rate = EXCLUDED.high_rate,
                            low_rate = EXCLUDED.low_rate,
                            close_rate = EXCLUDED.close_rate,
                            source_date = EXCLUDED.source_date
                    """, (from_curr, to_curr, r_date, o_rate, h_rate, l_rate, c_rate, r_date))
                    total_inserted += 1

                conn.commit()
                print(f"  ✅ Synced {ticker}")
            except Exception as e:
                print(f"  ⚠️ Error syncing FX ticker {ticker}: {e}")

    return total_inserted

def sync_exchange_rates_for_pair(
    from_currency: str,
    to_currency: str,
    database_name: str = DEFAULT_DB,
    period: str = "max"
) -> int:
    """
    Sync exchange rates for a single currency pair.

    Called on-demand when a new foreign-currency investment is added.
    Downloads full history (period='max') on first call, or a short
    delta ('5d') during daily maintenance.
    """
    from_curr = resolve_currency_code(from_currency)
    to_curr = resolve_currency_code(to_currency)
    if from_curr == to_curr:
        return 0
    return sync_historical_exchange_rates(
        pairs=[(from_curr, to_curr)],
        database_name=database_name,
        period=period
    )

def ensure_exchange_rates_exist(
    investment_currency: str,
    base_currency: str = None,
    database_name: str = DEFAULT_DB
) -> bool:
    """
    Demand-driven trigger: check if exchange rates exist for the pair
    investment_currency <-> base_currency. If not, download full history.

    Returns True if rates were already present or successfully synced.
    """
    if base_currency is None:
        base_currency = BASE_CURRENCY_CODE
    inv_curr = resolve_currency_code(investment_currency)
    base_curr = resolve_currency_code(base_currency)
    if inv_curr == base_curr:
        return True

    # Check if we already have any rates for this pair
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            SELECT 1 FROM exchange_rates
            WHERE (from_currency = %s AND to_currency = %s)
               OR (from_currency = %s AND to_currency = %s)
            LIMIT 1
        """, (inv_curr, base_curr, base_curr, inv_curr))
        if cursor.fetchone():
            return True

    # No rates found — sync full history
    print(f"📥 No exchange rates for {inv_curr}/{base_curr} — downloading history...")
    inserted = sync_exchange_rates_for_pair(inv_curr, base_curr, database_name, period="max")
    if inserted == 0:
        # Try the reverse pair (yfinance may only have one direction)
        inserted = sync_exchange_rates_for_pair(base_curr, inv_curr, database_name, period="max")
    return inserted > 0

def convert_investment_data_for_display(
    df: pd.DataFrame,
    base_currency: str = None,
    database_name: str = DEFAULT_DB,
    user_id: Optional[int] = None
) -> pd.DataFrame:
    """Convert investment data monetary values to specified base currency for display."""
    if base_currency is None:
        base_currency = DEFAULT_BASE_CURRENCY

    base_currency = resolve_currency_code(base_currency)

    if df.empty:
        return df

    df_copy = df.copy()
    monetary_columns = [
        "unit_price", "initial_unit_price", "investment_value",
        "total_dividends_received", "total_tax_paid", "total_fees_paid"
    ]

    with get_db_connection(database_name, user_id=user_id) as (conn, cursor):
        for col in monetary_columns:
            if col in df_copy.columns and "unit_currency" in df_copy.columns:
                converted_values = []
                for idx, row in df_copy.iterrows():
                    orig_currency = resolve_currency_code(row.get("unit_currency", NATIVE_CURRENCY))
                    conv_date = row.get("unit_price_date") if hasattr(row, "unit_price_date") and pd.notna(row.get("unit_price_date")) else None
                    if conv_date:
                        if isinstance(conv_date, pd.Timestamp):
                            conv_date = conv_date.strftime("%Y-%m-%d")
                        elif hasattr(conv_date, 'date'):
                            conv_date = conv_date.date().isoformat()

                    val = convert_currency_amount(
                        float(row[col]) if pd.notna(row[col]) else 0.0,
                        orig_currency,
                        base_currency,
                        conv_date,
                        database_name,
                        cursor=cursor
                    )
                    converted_values.append(val)
                df_copy[col] = converted_values

    df_copy["unit_currency"] = base_currency
    df_copy["display_currency"] = base_currency

    return df_copy

def get_available_base_currencies(database_name: str = DEFAULT_DB) -> list:
    """Return currencies available for portfolio display.

    Combines the user's configured base currency with currencies actually
    present in their portfolio so the frontend dropdown is always relevant.
    """
    available = {BASE_CURRENCY_CODE}
    try:
        with get_db_connection(database_name) as (conn, cursor):
            cursor.execute("""
                SELECT DISTINCT unit_currency FROM investments
                WHERE investment_ticker != 'PORTFOLIO'
                  AND investment_type != 'Forex'
            """)
            for (curr,) in cursor.fetchall():
                available.add(resolve_currency_code(curr))
    except Exception:
        pass
    # Always include the static list as a baseline so the UI is never empty
    for c in SUPPORTED_BASE_CURRENCIES:
        available.add(c)
    return sorted(available)
