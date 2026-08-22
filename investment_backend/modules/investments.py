from datetime import date
import pandas as pd
from .database import get_db_connection, DEFAULT_DB, create_connection
from .currency import CURRENCY_SYMBOLS, convert_investment_data_for_display, SUPPORTED_BASE_CURRENCIES, DEFAULT_BASE_CURRENCY
from .utils import _fetch_and_store_historical_data, _handle_forex_investment
from .metrics import update_investment_metrics

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
    investment_status: str):
    """
    Add a new investment to the database with comprehensive data insertion,
    transaction creation, unit price tracking, and automatic historical data fetching.
    """

    # Use context manager to ensure proper transaction handling
    with get_db_connection(database_name) as (conn, cursor):
        try:
            # Fetch existing investments to check for duplicates
            cursor.execute("SELECT id, institution_name, investment_name FROM investments")
            investments_rows = cursor.fetchall()
            
            # Check if investment already exists
            for row in investments_rows:
                if row[1] == institution_name and row[2] == investment_name:
                    print(f"Investment '{investment_name}' from '{institution_name}' already exists.")
                    return

            # Insert the investment
            insert_query = """
                INSERT INTO investments (institution_name, initial_investment_date, investment_type,
                investment_name, investment_ticker, unit_currency, initial_unit_price, unit_price,
                number_of_units_held, total_dividends_received, total_tax_paid, total_fees_paid, investment_fee, investment_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """
            params = (institution_name, initial_investment_date, investment_type, investment_name, investment_ticker, unit_currency, initial_unit_price, unit_price, number_of_units_held, total_dividends_received, total_tax_paid, total_fees_paid, investment_fee, investment_status)
            cursor.execute(insert_query, params)
            investment_id = float(cursor.fetchone()[0])

            # Insert initial transaction
            cursor.execute(
                "INSERT INTO transactions (investment_id, transaction_date, transaction_type, transaction_amount, unit_price, number_of_units) VALUES (%s, %s, %s, %s, %s, %s)",
                (investment_id, initial_investment_date, "buy", initial_unit_price * number_of_units_held, unit_price, number_of_units_held)
            )

            # Insert initial unit price
            cursor.execute(
                "INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change) VALUES (%s, %s, %s, %s, %s)",
                (investment_id, initial_investment_date, unit_price, 0.0, 0.0)
            )

            print(f"Added investment '{investment_name}' with ID {investment_id}.")

            # Fetch and store historical data is now handled asynchronously by fetch_prices_now
            # via BackgroundTasks in the FastAPI endpoint

            # Handle Forex
            _handle_forex_investment(cursor, investment_id, unit_currency, initial_investment_date, institution_name, database_name)

            # Commit all changes
            conn.commit()

            # If the same asset is already held in another account, share its
            # price history instead of storing a second copy. This must run
            # AFTER the commit above: the linker opens its own connection, and
            # running it earlier targeted an uncommitted row that connection
            # could not see (the UPDATE/DELETE silently affected 0 rows).
            linked = _link_new_investment_to_price_master(
                database_name, investment_id, investment_name, unit_currency, investment_type
            )
            if linked:
                print(f"Linked '{investment_name}' to shared price master (investment {linked}).")

            # Update investment metrics - after commit so it's visible to other connections
            try:
                update_investment_metrics(investment_id, database_name)
            except Exception as e:
                print(f"Warning: Could not update investment metrics: {e}")

            return investment_id

        except Exception as e:
            print(f"Error adding investment: {e}")
            import traceback
            traceback.print_exc()

def _link_new_investment_to_price_master(database_name: str, investment_id, investment_name: str, unit_currency: str, investment_type: str = ""):
    """
    If the same asset (same name + currency, ignoring account markers) is
    already held by another investment, point the new investment at that
    investment as its price master so its history is only stored once.
    Returns the master investment id, or None if nothing matched.
    """
    if investment_type and investment_type.lower() == 'forex':
        return None
    from .price_scraper import _asset_group_key
    key = _asset_group_key(investment_name)
    if not key:
        return None

    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            SELECT i.id, i.investment_name
            FROM investments i
            WHERE i.id <> %s
              AND i.investment_type <> 'Forex'
              AND i.investment_ticker <> 'PORTFOLIO'
              AND i.price_source_investment_id IS NULL
              AND i.unit_currency = %s
            ORDER BY (SELECT COUNT(*) FROM unit_prices up WHERE up.investment_id = i.id) DESC, i.id ASC
        """, (investment_id, unit_currency))
        for master_id, master_name in cursor.fetchall():
            if _asset_group_key(master_name) != key:
                continue
            cursor.execute(
                "UPDATE investments SET price_source_investment_id = %s WHERE id = %s",
                (master_id, investment_id)
            )
            cursor.execute(
                # If the master has a NULL unit_price, keep the child's own
                # price rather than overwriting it with NULL.
                "UPDATE investments SET unit_price = "
                "COALESCE((SELECT unit_price FROM investments WHERE id = %s), unit_price) "
                "WHERE id = %s",
                (master_id, investment_id)
            )
            cursor.execute("DELETE FROM unit_prices WHERE investment_id = %s", (investment_id,))
            conn.commit()
            return master_id
    return None


def get_investment_summary(database_name: str = DEFAULT_DB):
    """
    Get summary of all investments.
    """
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("SELECT * FROM investments ORDER BY id ASC")
        rows = cursor.fetchall()
        
        # Get column names from cursor description
        if cursor.description:
            colnames = [desc[0] for desc in cursor.description]
            investments = pd.DataFrame(rows, columns=colnames)
        else:
            investments = pd.DataFrame()
        
        if investments.empty:
             return pd.DataFrame(columns=["id", "institution_name", "investment_name", "investment_type", "unit_currency", "investment_value", "unit_price", "total_units_held", "initial_unit_price", "initial_investment_date"])

        investment_id = pd.DataFrame()
        investment_id["id"] = investments["id"]
        investment_id["institution_name"] = investments["institution_name"]
        investment_id["investment_name"] = investments["investment_name"]
        investment_id["investment_type"] = investments["investment_type"]
        investment_id["unit_currency"] = investments["unit_currency"]
        investment_id["investment_value"] = investments["unit_price"] * investments["number_of_units_held"]
        investment_id["unit_price"] = investments["unit_price"]
        investment_id["total_units_held"] = investments["number_of_units_held"]
        investment_id["initial_unit_price"] = investments["initial_unit_price"]
        investment_id["initial_investment_date"] = investments["initial_investment_date"]
        investment_id["total_dividends_received"] = investments["total_dividends_received"]
        investment_id["total_tax_paid"] = investments["total_tax_paid"]
        investment_id["investment_fee"] = investments["investment_fee"]

        return investment_id

def get_investment_summary_display(base_currency: str = "ZAR",
                                  filter_currency: str = None,
                                  database_name: str = DEFAULT_DB) -> pd.DataFrame:
    """
    Get investment summary data with currency conversion for frontend display.
    """
    df = get_investment_summary(database_name)

    # Filter if requested
    if filter_currency:
        symbol_to_code = {v: k for k, v in CURRENCY_SYMBOLS.items()}
        currency_code = symbol_to_code.get(filter_currency, filter_currency)
        df = df[df["unit_currency"].str.upper() == currency_code.upper()]

    # Apply currency conversion for display
    if not df.empty:
        df = convert_investment_data_for_display(df, base_currency, database_name)

    return df

def get_currencies_in_portfolio(database_name: str = DEFAULT_DB) -> list:
    """
    Get list of all currencies currently held in the portfolio.
    """
    df = get_investment_summary(database_name)
    if df.empty:
        return []

    unique_currencies = df["unit_currency"].unique().tolist()
    return sorted(unique_currencies)

def get_investment_types_in_portfolio(database_name: str = DEFAULT_DB) -> list:
    """
    Get list of all investment types currently held in the portfolio.
    """
    df = get_investment_summary(database_name)
    if df.empty:
        return []

    unique_types = df["investment_type"].unique().tolist()
    return sorted(unique_types)

def get_all_investment_values(database_name):
    """
    Get investment time series values calculated using cumulative units held over time.
    """
    conn, cursor = create_connection(database_name)

    try:
        cursor.execute("SELECT * FROM investments ORDER BY id ASC")
        rows = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description] if cursor.description else []
        investments = pd.DataFrame(rows, columns=colnames)

        cursor.execute("""
            SELECT investment_id, transaction_date, transaction_type, number_of_units
            FROM transactions
            ORDER BY investment_id, transaction_date
        """)
        txns = cursor.fetchall()

        import bisect
        inv_txns = {}
        for inv_id, tdate, ttype, units in txns:
            if inv_id not in inv_txns:
                inv_txns[inv_id] = []
            ttype_lower = (ttype or "").lower()
            if ttype_lower in ('buy', 'switch_in'):
                net = float(units)
            elif ttype_lower in ('sell', 'switch_out'):
                net = -abs(float(units))
            else:
                net = 0.0
            inv_txns[inv_id].append((tdate, net))

        inv_cum_units = {}
        for inv_id, events in inv_txns.items():
            events.sort(key=lambda x: x[0])
            timeline = []
            cum = 0.0
            for d, u in events:
                cum += u
                timeline.append((d, cum))
            inv_cum_units[inv_id] = timeline

        def _get_units_on_date(inv_id, target_date, fallback_units, init_date):
            if inv_id in inv_cum_units:
                timeline = inv_cum_units[inv_id]
                idx = bisect.bisect_right(timeline, (target_date, float('inf'))) - 1
                if idx >= 0:
                    return max(0.0, timeline[idx][1])
                return 0.0
            else:
                if init_date and target_date >= init_date:
                    return float(fallback_units or 0.0)
                return 0.0

        cursor.execute("""
            SELECT v.investment_id AS id, i.investment_name, i.unit_currency, i.investment_type,
                   i.institution_name, i.initial_investment_date, i.number_of_units_held,
                   v.unit_price_date, v.unit_price
            FROM v_investment_prices v
            JOIN investments i ON v.investment_id = i.id
            ORDER BY v.investment_id, v.unit_price_date ASC
        """)
        price_rows = cursor.fetchall()
        
        data = []
        for inv_id, inv_name, currency, inv_type, inst_name, init_date, held_units, pdate, price in price_rows:
            units = _get_units_on_date(inv_id, pdate, held_units, init_date)
            value = units * float(price)
            data.append({
                "id": inv_id,
                "investment_name": inv_name,
                "unit_currency": currency,
                "investment_type": inv_type,
                "institution_name": inst_name,
                "unit_price_date": pd.to_datetime(pdate),
                "unit_price": float(price),
                "total_units_held": units,
                "number_of_units": units,
                "investment_value": value
            })

        return pd.DataFrame(data)

    finally:
        conn.close()

def get_investment_data(base_currency: str = None,
                       filter_currency: str = None,
                       filter_investment_type: str = None,
                       database_name: str = DEFAULT_DB) -> pd.DataFrame:
    """
    Get investment data with optional currency conversion and filtering for frontend display.
    """
    if base_currency is None:
        base_currency = DEFAULT_BASE_CURRENCY

    # Accept display symbols ('R') as well as ISO codes ('ZAR') by resolving
    # symbols to their ISO code before validation/conversion.
    if isinstance(base_currency, str):
        base_currency = CURRENCY_SYMBOLS.get(base_currency.strip().upper(), base_currency.strip().upper())

    if base_currency not in SUPPORTED_BASE_CURRENCIES:
        raise ValueError(f"Base currency '{base_currency}' not supported. Available: {SUPPORTED_BASE_CURRENCIES}")

    df = get_all_investment_values(database_name)

    # Filter if requested
    if filter_currency:
        symbol_to_code = {v: k for k, v in CURRENCY_SYMBOLS.items()}
        currency_code = symbol_to_code.get(filter_currency, filter_currency)
        df = df[df["unit_currency"].str.upper() == currency_code.upper()]

    if filter_investment_type:
        df = df[df["investment_type"] == filter_investment_type]

    # Apply currency conversion for display
    if not df.empty:
        df = convert_investment_data_for_display(df, base_currency, database_name)

    return df

def get_portfolio_total_value(base_currency: str = "ZAR", database_name: str = DEFAULT_DB) -> dict:
    """
    Calculate total portfolio value in specified base currency.
    """
    df = get_investment_data(base_currency=base_currency, database_name=database_name)
    if df.empty:
        return {"total_value": 0.0, "by_currency": {}, "by_type": {}, "base_currency": base_currency}

    # We need to take the latest value for each investment
    # Sort by date and take last for each investment id
    latest_df = df.sort_values("unit_price_date").groupby("id").last().reset_index()

    total_value = latest_df["investment_value"].sum()

    by_currency = latest_df.groupby("unit_currency")["investment_value"].sum().to_dict()
    by_type = latest_df.groupby("investment_type")["investment_value"].sum().to_dict()

    return {
        "total_value": round(total_value, 2),
        "by_currency": {k: round(v, 2) for k, v in by_currency.items()},
        "by_type": {k: round(v, 2) for k, v in by_type.items()},
        "base_currency": base_currency,
        "count_investments": len(latest_df)
    }

def get_investment_names_list(database_name: str = DEFAULT_DB) -> list:
    """Get list of investment names with tickers for dropdowns."""
    try:
        with get_db_connection(database_name) as (conn, cursor):
            cursor.execute("SELECT DISTINCT investment_name, investment_ticker FROM investments ORDER BY investment_name")
            rows = cursor.fetchall()
            return [f"{row[0]} ({row[1]})" for row in rows]
    except Exception as e:
        print(f"Failed to fetch investment names: {str(e)}")
        return []


def get_net_worth_timeseries(database_name: str = DEFAULT_DB,
                             base_currency: str = "ZAR") -> list[dict]:
    """
    Build a net-worth time series using ACTUAL historical holdings.

    For each investment on each price date, the value is:
        cumulative_units_purchased_up_to_date * unit_price(on that date)
    where cumulative_units is computed from the transactions table — NOT the
    current number_of_units_held, which would create a misleadingly monotone
    graph (today's holdings valued at historical prices).

    This accurately reflects what the portfolio was worth at each point in time.
    The last point equals the displayed current total net worth.

    Returns a list of {"date": "YYYY-MM-DD", "value": float} sorted ascending.
    """
    from .currency import CURRENCY_SYMBOLS

    with get_db_connection(database_name) as (conn, cursor):
        # Load all buy/sell transactions to reconstruct unit counts over time
        cursor.execute("""
            SELECT t.investment_id, t.transaction_date, t.transaction_type, t.number_of_units
            FROM transactions t
            JOIN investments i ON t.investment_id = i.id
            WHERE i.investment_type <> 'Forex'
              AND i.number_of_units_held > 0
            ORDER BY t.investment_id, t.transaction_date
        """)
        txn_rows = cursor.fetchall()

        import bisect
        # Build (date, cumulative_units) timeline per investment_id
        inv_txns: dict[int, list] = {}
        for inv_id, tdate, ttype, units in txn_rows:
            if inv_id not in inv_txns:
                inv_txns[inv_id] = []
            ttype_lower = (ttype or "").lower()
            if ttype_lower in ('buy', 'switch_in'):
                net = float(units or 0)
            elif ttype_lower in ('sell', 'switch_out'):
                net = -abs(float(units or 0))
            else:
                net = 0.0
            inv_txns[inv_id].append((tdate, net))

        # Build cumulative timeline per investment
        inv_cum_units: dict[int, list] = {}  # {inv_id: [(date, cumulative_units), ...]}
        for inv_id, events in inv_txns.items():
            events.sort(key=lambda x: x[0])
            timeline = []
            cum = 0.0
            for d, u in events:
                cum += u
                timeline.append((d, cum))
            inv_cum_units[inv_id] = timeline

        def _get_units_on_date(inv_id: int, target_date) -> float:
            """Return the cumulative units held for inv_id on target_date."""
            timeline = inv_cum_units.get(inv_id)
            if not timeline:
                return 0.0
            
            # Ensure target_date is a date object for comparison
            t_dt = target_date
            if hasattr(t_dt, 'date'):
                t_dt = t_dt.date()
                
            idx = bisect.bisect_right(timeline, (t_dt, float('inf'))) - 1
            if idx < 0:
                return 0.0
            return max(0.0, timeline[idx][1])

        # Fetch price history via the shared price view (handles price_source_investment_id)
        cursor.execute("""
            SELECT v.investment_id, i.unit_currency, v.unit_price_date, v.unit_price
            FROM v_investment_prices v
            JOIN investments i ON v.investment_id = i.id
            WHERE i.number_of_units_held > 0
              AND i.investment_type <> 'Forex'
              AND v.unit_price > 0
            ORDER BY v.unit_price_date
        """)
        price_rows = cursor.fetchall()

        # Fallback: investments with no price history — use initial date + current value
        cursor.execute("""
            WITH priced_invs AS (
                SELECT DISTINCT investment_id FROM v_investment_prices WHERE unit_price > 0
            )
            SELECT i.id, i.unit_currency, i.initial_investment_date, i.unit_price, i.number_of_units_held
            FROM investments i
            LEFT JOIN priced_invs p ON p.investment_id = i.id
            WHERE i.number_of_units_held > 0
              AND i.investment_type <> 'Forex'
              AND p.investment_id IS NULL
        """)
        unpriced = cursor.fetchall()

        # Load forex rates for currency conversion
        forex_series: dict[tuple, list] = {}
        cursor.execute("""
            SELECT i.investment_ticker, up.unit_price_date, up.unit_price
            FROM investments i
            JOIN v_investment_prices up ON up.investment_id = i.id
            WHERE i.investment_type = 'Forex'
            ORDER BY up.unit_price_date
        """)
        for ticker, fdate, fprice in cursor.fetchall():
            ticker = (ticker or "").upper().replace("=X", "")
            if len(ticker) == 6:
                from_c, to_c = ticker[:3], ticker[3:]
                forex_series.setdefault((from_c, to_c), []).append((fdate, float(fprice)))

    def _lookup_rate(pair: tuple, date_obj) -> float | None:
        series = forex_series.get(pair)
        if not series:
            return None
        idx = bisect.bisect_right(series, (date_obj, float("inf"))) - 1
        if idx < 0:
            return None
        best_date, best_rate = series[idx]
        if (date_obj - best_date).days <= 90:
            return best_rate
        return None

    def _rate(from_c: str, date_obj) -> float:
        if from_c == base_currency:
            return 1.0
        direct = _lookup_rate((from_c, base_currency), date_obj)
        if direct is not None:
            return direct
        rev = _lookup_rate((base_currency, from_c), date_obj)
        if rev is not None and rev != 0:
            return 1.0 / rev
        return 1.0

    # Build monthly totals using HISTORICAL unit counts × historical prices
    # We aggregate to monthly resolution to keep chart performance acceptable
    from collections import defaultdict
    daily_totals: dict = defaultdict(float)

    for inv_id, currency, price_date, price in price_rows:
        currency_code = currency
        if isinstance(currency_code, str) and len(currency_code) == 1:
            currency_code = CURRENCY_SYMBOLS.get(currency_code, currency_code)

        # Use the historically-correct unit count for this date
        units = _get_units_on_date(inv_id, price_date)
        if units <= 0:
            continue  # Investment hadn't been purchased yet on this date

        value_local = units * float(price)
        if currency_code != base_currency:
            value_local *= _rate(currency_code, price_date)
        daily_totals[price_date] += value_local

    # Fallback for investments with no price history
    for inv_id, currency, init_date, price, units_held in unpriced:
        currency_code = currency
        if isinstance(currency_code, str) and len(currency_code) == 1:
            currency_code = CURRENCY_SYMBOLS.get(currency_code, currency_code)
        if init_date is None or price is None or units_held is None:
            continue
        value_local = float(units_held) * float(price)
        if currency_code != base_currency:
            value_local *= _rate(currency_code, init_date)
        init_dt = init_date if isinstance(init_date, date) else init_date.date()
        for d in list(daily_totals.keys()):
            if d >= init_dt:
                daily_totals[d] += value_local
        if not any(d >= init_dt for d in daily_totals):
            daily_totals[init_dt] += value_local

    return [
        {"date": d.isoformat(), "value": round(v, 2)}
        for d, v in sorted(daily_totals.items())
    ]
