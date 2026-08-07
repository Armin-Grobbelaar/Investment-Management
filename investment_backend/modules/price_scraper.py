"""
Price Scraper Module
====================
Fetches current and historical unit prices from multiple sources:
  1. yfinance  – JSE-listed ETFs, shares and international funds (ticker.JO suffix for JSE)
  2. profiledata.co.za – SA Unit Trust / ASISA funds (scrapes via Playwright)
  3. fundsdata.co.za – SA Unit Trust fallback (scrapes public summary page)
  4. stooq.com  – international fallback

Scheduling
----------
Call `start_scheduler()` once at app startup.  It will:
  - Fetch TODAY's price for every investment at 11:30 SAST daily.
  - Back-fill ALL historical prices for new investments in one go.
  - For profiledata sources, back-fill 10 days per run using backwards cursor.

Install dependencies (if not already present):
    pip install apscheduler yfinance requests-cache pytz
    paru -S python-apscheduler (Arch)
"""

import logging
import random
import re
import time
from datetime import datetime, date, timedelta
from typing import Optional

import pandas as pd
import pytz
import requests

logger = logging.getLogger("price_scraper")
logging.basicConfig(level=logging.INFO)

SAST = pytz.timezone("Africa/Johannesburg")

# How many historical data points to back-fill per investment per scheduler run
DAILY_BACKFILL_BATCH = 10

# Respectful delay between HTTP requests (seconds)
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.5

# Session with User-Agent
_session = requests.Session()
_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-ZA,en;q=0.9",
})


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_investments(database_name: str) -> list[dict]:
    """Return all investments with their ticker and currency."""
    from .database import get_db_connection
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            SELECT i.id, i.investment_name, i.investment_ticker, i.unit_currency, i.investment_type,
                   m.source, m.source_ticker, m.backfill_complete
            FROM investments i
            LEFT JOIN investment_source_meta m ON m.investment_id = i.id
            ORDER BY i.investment_name
        """)
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _get_existing_price_dates(database_name: str, investment_id: int) -> set[date]:
    """Return the set of dates already in unit_prices for an investment."""
    from .database import get_db_connection
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute(
            "SELECT unit_price_date FROM unit_prices WHERE investment_id = %s",
            (investment_id,)
        )
        return {row[0] for row in cursor.fetchall()}


def _upsert_price(database_name: str, investment_id: int,
                   price_date: date, price: float) -> bool:
    """Insert or update a unit price row.  Returns True if a new row was written."""
    from .database import get_db_connection
    with get_db_connection(database_name) as (conn, cursor):
        # Fetch previous price to calculate change
        cursor.execute("""
            SELECT unit_price FROM unit_prices 
            WHERE investment_id = %s AND unit_price_date < %s 
            ORDER BY unit_price_date DESC LIMIT 1
        """, (investment_id, price_date))
        res = cursor.fetchone()
        
        unit_price_change = 0.0
        pct_change = 0.0
        
        if res:
            prev_price = float(res[0])
            unit_price_change = price - prev_price
            if prev_price != 0:
                pct_change = (unit_price_change / prev_price) * 100

        cursor.execute("""
            INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (investment_id, unit_price_date)
            DO UPDATE SET 
                unit_price = EXCLUDED.unit_price,
                unit_price_change = EXCLUDED.unit_price_change,
                percentage_unit_price_change = EXCLUDED.percentage_unit_price_change
        """, (investment_id, price_date, price, unit_price_change, pct_change))
        inserted = cursor.rowcount > 0
        conn.commit()
        return inserted


def _update_investment_current_price(database_name: str, investment_id: int, price: float):
    """Update the live unit_price on the investments row."""
    from .database import get_db_connection
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute(
            "UPDATE investments SET unit_price = %s WHERE id = %s",
            (price, investment_id)
        )
        conn.commit()


def _get_earliest_investment_date(database_name: str, investment_id: int) -> Optional[date]:
    """Return the earliest transaction date or the initial_investment_date."""
    from .database import get_db_connection
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            SELECT LEAST(
                MIN(t.transaction_date),
                i.initial_investment_date
            )
            FROM investments i
            LEFT JOIN transactions t ON t.investment_id = i.id
            WHERE i.id = %s
            GROUP BY i.initial_investment_date
        """, (investment_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None


def _persist_source_meta(database_name: str, investment_id: int,
                         source: str, ticker: str):
    """Record the resolved price source for an investment."""
    from .database import get_db_connection
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            INSERT INTO investment_source_meta (investment_id, source, source_ticker, last_fetched)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (investment_id)
            DO UPDATE SET source = EXCLUDED.source,
                          source_ticker = EXCLUDED.source_ticker,
                          last_fetched = NOW()
        """, (investment_id, source, ticker))
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Price sources
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_yfinance(ticker: str, start: Optional[date] = None,
                    end: Optional[date] = None) -> pd.DataFrame:
    """
    Fetch OHLCV data from yfinance.
    For JSE-listed assets use ticker ending in '.JO' (e.g. 'STXNDQ.JO').
    Returns DataFrame with 'Date' and 'Close' columns (prices in the native currency).
    """
    try:
        import yfinance as yf
        if not ticker:
            return pd.DataFrame()
        t = yf.Ticker(ticker)
        if start and end:
            df = t.history(start=start.isoformat(), end=(end + timedelta(days=1)).isoformat())
        elif start:
            df = t.history(start=start.isoformat())
        else:
            df = t.history(period="1d")
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()[["Date", "Close"]].dropna()
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        return df
    except Exception as e:
        logger.warning(f"yfinance error for {ticker}: {e}")
        return pd.DataFrame()


def _fetch_fundsdata_current(fund_code: str) -> Optional[float]:
    """
    Scrape the current NAV from fundsdata.co.za summary page.
    URL pattern: https://www.fundsdata.co.za/Summary.aspx?c=<FUND_CODE>
    """
    if not fund_code:
        return None
    url = f"https://www.fundsdata.co.za/Summary.aspx?c={fund_code}"
    try:
        resp = _session.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        text = resp.text
        patterns = [
            r'NAV[^<]{0,100}<td[^>]*>([\d\s,]+\.?\d*)</td>',
            r'Unit Price[^<]{0,100}<td[^>]*>([\d\s,]+\.?\d*)</td>',
            r'Price[^<]{0,200}>([\d]+[,.][\d]+)<',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                raw = m.group(1).replace(',', '').replace(' ', '')
                try:
                    return float(raw)
                except ValueError:
                    continue
        return None
    except Exception as e:
        logger.warning(f"fundsdata error for {fund_code}: {e}")
        return None


def _fetch_stooq(ticker: str, start: Optional[date] = None,
                 end: Optional[date] = None) -> pd.DataFrame:
    """
    Fallback: fetch CSV from stooq.com.
    Ticker format for JSE: e.g. 'stxndq.jo' (lowercase).
    """
    if not ticker:
        return pd.DataFrame()
    base = "https://stooq.com/q/d/l/"
    params: dict = {"s": ticker.lower(), "i": "d"}
    if start:
        params["d1"] = start.strftime("%Y%m%d")
    if end:
        params["d2"] = end.strftime("%Y%m%d")
    try:
        resp = _session.get(base, params=params, timeout=15)
        if resp.status_code != 200 or "No data" in resp.text[:200]:
            return pd.DataFrame()
        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))
        df.columns = [c.strip() for c in df.columns]
        df = df[["Date", "Close"]].dropna()
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        df = df[df["Close"] > 0]
        return df
    except Exception as e:
        logger.warning(f"stooq error for {ticker}: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# Core logic
# ─────────────────────────────────────────────────────────────────────────────

def _determine_source_and_ticker(inv: dict) -> tuple[str, str]:
    """
    Decide which source and effective ticker to use.
    Returns (source, ticker_or_code).

    Rules:
      1. Explicit `investment_source_meta` configuration wins.
      2. SA Unit Trusts (investment_type == 'Unit Trust' or a known CIS
         manager detected in the name) go to ProfileData (Playwright) —
         these funds are generally NOT available on Yahoo Finance.
      3. Tickers with a '.JO'/'.ZA' suffix or containing a dot are Yahoo.
      4. Short all-caps codes (e.g. 'AGEF') with no manager hint are treated
         as ProfileData fund codes, since Yahoo has no symbol for them.
      5. Anything else defaults to Yahoo Finance.
    """
    # 1. Use explicit DB configuration if available
    db_source = inv.get("source")
    db_ticker = inv.get("source_ticker")
    if db_source and db_source != 'manual':
        return db_source, db_ticker or inv.get("investment_ticker", "")

    ticker = (inv.get("investment_ticker") or "").strip()
    inv_type = (inv.get("investment_type") or "").lower()

    # Detect SA unit trust by name (CIS manager present)
    from .profiledata_scraper import parse_investment_name
    parsed = parse_investment_name(inv.get("investment_name", ""))
    is_sa_unit_trust = inv_type == 'unit trust' or bool(parsed["manager"])

    if not ticker:
        # Check if it's a known SA unit trust
        if is_sa_unit_trust:
            return "profiledata", ""
        return "none", ""

    # JSE / international exchange suffix → yfinance
    if ticker.upper().endswith(".JO") or ticker.upper().endswith(".ZA"):
        return "yfinance", ticker

    # Short all-caps code without a dot (e.g. 'AGEF', 'PRBA2') → SA fund code,
    # but only when this actually looks like a SA unit trust (manager in the
    # name or investment_type == 'Unit Trust'). Bare codes like 'MSFT' or
    # 'AAPL' must go to Yahoo Finance.
    if is_sa_unit_trust and re.match(r'^[A-Z]{2,8}[0-9]?$', ticker):
        return "profiledata", ticker

    # Has a dot (e.g. "URTH", "MSFT", "BTC-USD", "EUE.L") → yfinance
    return "yfinance", ticker


def fetch_current_price(inv: dict, database_name: str) -> Optional[float]:
    """Fetch today's price for a single investment and persist it."""
    source, effective_ticker = _determine_source_and_ticker(inv)
    price: Optional[float] = None

    if source == "profiledata":
        from .profiledata_scraper import fetch_profiledata_prices
        start_date = date.today() - timedelta(days=5)
        prices = fetch_profiledata_prices(inv["investment_name"], start_date, date.today())
        if prices:
            price = prices[-1][1]
        # Also try yfinance as a quick fallback if profiledata failed
        if price is None and effective_ticker:
            df = _fetch_yfinance(effective_ticker)
            if not df.empty:
                price = float(df["Close"].iloc[-1])

    elif source == "fundsdata":
        price = _fetch_fundsdata_current(effective_ticker)
        if price is None:
            df = _fetch_yfinance(effective_ticker)
            if not df.empty:
                price = float(df["Close"].iloc[-1])

    elif source == "yfinance":
        df = _fetch_yfinance(effective_ticker)
        if not df.empty:
            price = float(df["Close"].iloc[-1])
        else:
            df2 = _fetch_stooq(effective_ticker)
            if not df2.empty:
                price = float(df2["Close"].iloc[-1])

    if price and price > 0:
        today = date.today()
        _upsert_price(database_name, inv["id"], today, price)
        _update_investment_current_price(database_name, inv["id"], price)
        _persist_source_meta(database_name, inv["id"], source, effective_ticker)
        logger.info(f"✅ [{inv['investment_name']}] Today's price: {price:.4f}")
        return price
    else:
        logger.warning(f"⚠️ [{inv['investment_name']}] Could not fetch today's price (ticker: {effective_ticker})")
        return None


def backfill_historical_prices(inv: dict, database_name: str,
                                batch_size: int = DAILY_BACKFILL_BATCH) -> int:
    """
    Fetch missing historical prices for an investment.
    For yfinance, it fetches ALL history in one go (full backfill).
    For profiledata, it fetches 10 days per run using the backwards cursor.
    """
    source, effective_ticker = _determine_source_and_ticker(inv)
    if source == "none":
        return 0

    if source == "profiledata":
        from .profiledata_scraper import backfill_profiledata_prices
        stored = backfill_profiledata_prices(inv["id"], inv["investment_name"], database_name, batch_days=10)
        return stored

    # Determine date range to fill
    start_dt = _get_earliest_investment_date(database_name, inv["id"])
    if start_dt is None:
        start_dt = date.today() - timedelta(days=365 * 3)
    end_dt = date.today()

    existing_dates = _get_existing_price_dates(database_name, inv["id"])

    # Build the set of all business days we'd want
    all_wanted = pd.bdate_range(start=start_dt, end=end_dt).date
    missing = sorted(set(all_wanted) - existing_dates)

    if not missing:
        logger.info(f"  [{inv['investment_name']}] No missing prices — fully backfilled.")
        _mark_backfill_complete(database_name, inv["id"], source)
        return 0

    # For yfinance/fundsdata, fetch the entire range from min(missing) to max(missing)
    batch_start = min(missing)
    batch_end = max(missing)

    logger.info(
        f"  [{inv['investment_name']}] Backfilling {len(missing)} prices for {source} "
        f"({batch_start} – {batch_end})."
    )

    df = pd.DataFrame()
    if source in ("yfinance", "fundsdata"):
        df = _fetch_yfinance(effective_ticker, start=batch_start, end=batch_end)
        if df.empty:
            df = _fetch_stooq(effective_ticker, start=batch_start, end=batch_end)

        # Fallback: yfinance found nothing but this looks like an SA unit
        # trust → switch to ProfileData (Playwright) so we never silently
        # lose an investment just because Yahoo has no symbol for it.
        if df.empty:
            inv_type = (inv.get("investment_type") or "").lower()
            from .profiledata_scraper import parse_investment_name
            parsed = parse_investment_name(inv.get("investment_name", ""))
            if inv_type == 'unit trust' or parsed["manager"]:
                logger.info(
                    f"  [{inv['investment_name']}] Yahoo/Stooq empty — falling back to ProfileData."
                )
                from .profiledata_scraper import backfill_profiledata_prices
                stored = backfill_profiledata_prices(
                    inv["id"], inv["investment_name"], database_name, batch_days=10)
                if stored:
                    _persist_source_meta(database_name, inv["id"], "profiledata", effective_ticker)
                return stored
    else:
        df = _fetch_stooq(effective_ticker, start=batch_start, end=batch_end)

    if df.empty:
        logger.warning(f"  [{inv['investment_name']}] No historical data returned.")
        return 0

    # Store only missing dates
    stored = 0
    for _, row in df.iterrows():
        d = row["Date"]
        p = float(row["Close"])
        if d in missing and p > 0:
            _upsert_price(database_name, inv["id"], d, p)
            stored += 1

    if stored:
        _persist_source_meta(database_name, inv["id"], source, effective_ticker)

    logger.info(f"  [{inv['investment_name']}] Stored {stored} new historical prices.")
    
    # Check if we're now fully backfilled
    new_existing_dates = _get_existing_price_dates(database_name, inv["id"])
    new_missing = set(all_wanted) - new_existing_dates
    if not new_missing:
        _mark_backfill_complete(database_name, inv["id"], source)
        logger.info(f"  [{inv['investment_name']}] Marked backfill as complete.")

    return stored


def _mark_backfill_complete(database_name: str, investment_id: int, source: str):
    """Set backfill_complete = true and update last_fetched for an investment."""
    from .database import get_db_connection
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            INSERT INTO investment_source_meta (investment_id, source, backfill_complete, last_fetched)
            VALUES (%s, %s, true, NOW())
            ON CONFLICT (investment_id)
            DO UPDATE SET source = EXCLUDED.source,
                          backfill_complete = true,
                          last_fetched = NOW()
        """, (investment_id, source))
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Scheduled jobs
# ─────────────────────────────────────────────────────────────────────────────

def run_daily_price_fetch(database_name: str):
    """
    Job: run every day at 11:30 SAST.
    1. Fetch today's price for every investment.
    2. Back-fill a batch of historical prices for every investment.
    """
    logger.info("=" * 60)
    logger.info(f"🕐 Daily price fetch started at {datetime.now(SAST):%Y-%m-%d %H:%M} SAST")
    logger.info("=" * 60)

    try:
        investments = _get_investments(database_name)
    except Exception as e:
        logger.error(f"Failed to load investments: {e}")
        return

    total_current = 0
    total_history = 0

    for inv in investments:
        try:
            # 1. Today's price
            p = fetch_current_price(inv, database_name)
            if p:
                total_current += 1
            time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

            # 2. Historical backfill
            stored = backfill_historical_prices(inv, database_name, DAILY_BACKFILL_BATCH)
            total_history += stored
            if stored > 0:
                time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

        except Exception as e:
            logger.error(f"Error processing [{inv['investment_name']}]: {e}")
            continue

    logger.info(
        f"✅ Price fetch complete: {total_current} current prices, "
        f"{total_history} historical prices stored."
    )


def start_scheduler(database_name: str = "Investments"):
    """
    Start the APScheduler background scheduler.
    Call once at application startup (e.g. from FastAPI lifespan).
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning(
            "APScheduler not installed. Price scheduler disabled. "
            "Run: pip install apscheduler"
        )
        return None

    scheduler = BackgroundScheduler(timezone=SAST)

    # Daily at 11:30 SAST — prices are usually published by 11:00 for SA funds
    scheduler.add_job(
        func=run_daily_price_fetch,
        trigger=CronTrigger(hour=11, minute=30, timezone=SAST),
        args=[database_name],
        id="daily_price_fetch",
        name="Daily Unit Price Fetch",
        replace_existing=True,
    )
    
    # Monthly on the 20th at 09:00 SAST for factsheets
    from .factsheet_downloader import run_monthly_factsheet_downloader
    scheduler.add_job(
        func=run_monthly_factsheet_downloader,
        trigger=CronTrigger(day=20, hour=9, minute=0, timezone=SAST),
        args=[database_name],
        id="monthly_factsheet_fetch",
        name="Monthly Factsheet Fetch",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("📅 Price scheduler started — daily fetch at 11:30 SAST, factsheets on 20th")
    return scheduler


# ─────────────────────────────────────────────────────────────────────────────
# Manual trigger helpers (used by API endpoints)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_prices_now(database_name: str, investment_id: Optional[int] = None) -> dict:
    """
    Manually trigger a price fetch (current + backfill batch).
    If investment_id is None, processes all investments.
    """
    investments = _get_investments(database_name)
    if investment_id is not None:
        investments = [i for i in investments if i["id"] == investment_id]

    results = []
    for inv in investments:
        current_price = fetch_current_price(inv, database_name)
        backfilled = backfill_historical_prices(inv, database_name)
        results.append({
            "investment_name": inv["investment_name"],
            "current_price": current_price,
            "historical_stored": backfilled,
        })
        time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

    return {
        "results": results,
        "timestamp": datetime.now().isoformat(),
        "investments_processed": len(results),
    }


def get_backfill_status(database_name: str) -> list[dict]:
    """
    Return progress for each investment: how many prices exist vs. expected.
    """
    from .database import get_db_connection
    investments = _get_investments(database_name)
    status = []
    
    # Batch fetch all earliest dates in one query
    with get_db_connection(database_name) as (conn, cursor):
        cursor.execute("""
            SELECT i.id, LEAST(
                MIN(t.transaction_date),
                i.initial_investment_date
            ) as earliest_date
            FROM investments i
            LEFT JOIN transactions t ON t.investment_id = i.id
            GROUP BY i.id, i.initial_investment_date
        """)
        earliest_dates = {row[0]: row[1] for row in cursor.fetchall()}
    
    for inv in investments:
        existing = _get_existing_price_dates(database_name, inv["id"])
        start_dt = earliest_dates.get(inv["id"])
        if start_dt is None:
            start_dt = date.today() - timedelta(days=365)
        expected_days = len(pd.bdate_range(start=start_dt, end=date.today()))
        source, ticker = _determine_source_and_ticker(inv)
        status.append({
            "investment_name": inv["investment_name"],
            "ticker": ticker,
            "source": source,
            "prices_stored": len(existing),
            "prices_expected": expected_days,
            "pct_complete": round(len(existing) / expected_days * 100, 1) if expected_days > 0 else 0,
            "fully_backfilled": len(existing) >= expected_days,
        })
    return status