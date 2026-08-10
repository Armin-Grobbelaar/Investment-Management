"""
Import NPV(Armin).xlsx into the Investments PostgreSQL database.
One-time script for testing/seeding the Docker container.

Usage:
    python import_npv_excel.py [--dry-run]
"""
import os
import sys
import openpyxl
import psycopg2
import psycopg2.extras
from datetime import datetime, date
from decimal import Decimal

# ── Configuration ────────────────────────────────────────────────────────────

POSTGRES_HOST     = os.environ.get("POSTGRES_HOST",     "localhost")
POSTGRES_PORT     = int(os.environ.get("POSTGRES_PORT", 5432))
POSTGRES_USER     = os.environ.get("POSTGRES_USER",     "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "changeme")
INVESTMENTS_DB    = os.environ.get("INVESTMENTS_DB",    "Investments")

EXCEL_PATH            = "/home/armin/finances/NPV(Armin).xlsx"
CORONATION_EXCEL_PATH = "/home/armin/finances/20220201_20260408_CoronationTransactions_MrArminGrobbelaar_2012289.xlsx"
CSV_DIR               = "/home/armin/finances"

DRY_RUN = "--dry-run" in sys.argv

# ── DB helpers ───────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
        database=INVESTMENTS_DB,
    )

# ── XIRR ─────────────────────────────────────────────────────────────────────

def xirr(cashflows):
    """Compute XIRR from [(date, amount)] where amount<0 = outflow."""
    dates = [c[0] for c in cashflows]
    amounts = [c[1] for c in cashflows]
    from modules.metrics import xirr as calc_xirr
    return calc_xirr(dates, amounts)

# ── Investment definitions ────────────────────────────────────────────────────

# cols = (date_col, amount_col) — 1-indexed; data starts at row 4
INVESTMENTS_DEF = [
    # Allan Gray
    dict(sheet="Allan Gray", cols=(1, 2), name="Allan Gray Equity Fund",
         ticker="AGEF",     inst="Allan Gray",  type="Unit Trust", subtype="Voluntary", curr="ZAR", status="Active",  source="profiledata"),
    dict(sheet="Allan Gray", cols=(4, 5), name="Allan Gray Balanced Fund",
         ticker="ZAGBF",    inst="Allan Gray",  type="Unit Trust", subtype="Voluntary", curr="ZAR", status="Active",  source="profiledata"),
    # Coronation (dedicated Excel file)
    dict(sheet="Coronation", cols=None,  name="Coronation Top 20 Fund",
         ticker="ZAGCOR",   inst="Coronation",  type="Unit Trust", subtype="TFSA",      curr="ZAR", status="Active",  source="profiledata",
         excel_override=True),
    # Alexander Forbes (closed RA, switched to PSG)
    dict(sheet="Alexander Forbes", cols=(1, 2), name="AF Flexible Fund of Funds A (ISFAC)",
         ticker="ISFAC",    inst="Alexander Forbes", type="Unit Trust", subtype="RA",  curr="ZAR", status="Closed", source="profiledata"),
    dict(sheet="Alexander Forbes", cols=(4, 5), name="AF Global Equity Feeder Fund A (ISGE)",
         ticker="ISGE",     inst="Alexander Forbes", type="Unit Trust", subtype="RA",  curr="ZAR", status="Closed", source="profiledata"),
    # PSG Wealth
    dict(sheet="PSG Wealth", cols=(1, 2),   name="PSG Global Equity Feeder Fund (E) - Voluntary",
         ticker="PEFE",     inst="PSG Wealth", type="Unit Trust", subtype="Voluntary", curr="ZAR", status="Active", source="profiledata"),
    dict(sheet="PSG Wealth", cols=(4, 5),   name="PSG Global Flexible Feeder Fund (C)",
         ticker="PEFCF",    inst="PSG Wealth", type="Unit Trust", subtype="Voluntary", curr="ZAR", status="Active", source="profiledata"),
    dict(sheet="PSG Wealth", cols=(10, 11), name="PSG Global Equity Feeder Fund (E) - TFSA",
         ticker="PEFE-TFSA",inst="PSG Wealth", type="Unit Trust", subtype="TFSA",      curr="ZAR", status="Active", source="profiledata"),
    dict(sheet="PSG Wealth", cols=(13, 14), name="PSG Balanced Fund (E) - RA",
         ticker="PRBA2",    inst="PSG Wealth", type="Unit Trust", subtype="RA",        curr="ZAR", status="Active", source="profiledata"),
    # Easy Equities – ZAR
    dict(sheet="Easy Equities", cols=(1, 2),  name="Satrix Nasdaq 100 ETF (ZAR)",
         ticker="STXNDQ.JO",inst="Easy Equities", type="ETF", subtype="Voluntary", curr="ZAR", status="Active", source="yfinance"),
    dict(sheet="Easy Equities", cols=(4, 5),  name="Satrix Nasdaq 100 ETF (TFSA)",
         ticker="STXNDQ-TFSA",inst="Easy Equities",type="ETF", subtype="TFSA",    curr="ZAR", status="Active", source="yfinance"),
    dict(sheet="Easy Equities", cols=(7, 8),  name="Satrix MSCI World (TFSA)",
         ticker="STXWDM.JO",inst="Easy Equities", type="ETF", subtype="TFSA",    curr="ZAR", status="Active", source="yfinance"),
    # Easy Equities – Offshore (amounts stored as ZAR in Excel, need forex conversion)
    dict(sheet="Easy Equities", cols=(13, 14), name="iShares MSCI World ETF (USD)",
         ticker="URTH",     inst="Easy Equities", type="ETF", subtype="Voluntary", curr="USD", status="Active", source="yfinance",
         forex_from="ZAR", forex_ticker="USDZAR=X"),
    dict(sheet="Easy Equities", cols=(16, 17), name="iShares CORE MSCI Europe ETF (GBP)",
         ticker="EUE.L",    inst="Easy Equities", type="ETF", subtype="Voluntary", curr="GBP", status="Active", source="yfinance",
         forex_from="ZAR", forex_ticker="GBPZAR=X"),
]

# ── Step 1: Ensure forex pseudo-investments exist and fetch their rates ───────

def ensure_forex(conn, cursor):
    """
    Create/upsert USDZAR=X and GBPZAR=X as placeholder investments and
    populate their unit_prices from yfinance.  Returns a dict:
        {ticker: {date: rate_float}}
    """
    import yfinance as yf

    forex_tickers = ["USDZAR=X", "GBPZAR=X"]
    rate_cache = {}

    for fticker in forex_tickers:
        # Create a pseudo-investment if it doesn't exist
        cursor.execute(
            "SELECT id FROM investments WHERE investment_ticker = %s", (fticker,)
        )
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT INTO investments (
                    institution_name, initial_investment_date, investment_type,
                    investment_name, investment_ticker, unit_currency,
                    initial_unit_price, unit_price, number_of_units_held,
                    total_dividends_received, total_tax_paid, total_fees_paid,
                    investment_fee, investment_status, investment_subtype
                ) VALUES ('Forex','2000-01-01','Forex',%s,%s,'ZAR',0,0,0,0,0,0,0,'Active','Voluntary')
                RETURNING id
            """, (fticker, fticker))
            inv_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO investment_source_meta (investment_id, source, source_ticker, backfill_complete) VALUES (%s,'yfinance',%s,false)",
                (inv_id, fticker)
            )
            print(f"  Created forex investment: {fticker} (id={inv_id})")
        else:
            inv_id = row[0]

        # Fetch historical rates from yfinance (max 10 years)
        print(f"  Fetching {fticker} rates from yfinance …")
        try:
            data = yf.download(fticker, period="max", auto_adjust=True, progress=False)
            rates = {}
            count = 0
            for idx, row_data in data.iterrows():
                d = idx.date() if hasattr(idx, 'date') else idx
                price = float(row_data['Close'].iloc[0] if hasattr(row_data['Close'], 'iloc') else row_data['Close'])
                rates[d] = price
                if not DRY_RUN:
                    cursor.execute("""
                        INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                        VALUES (%s, %s, %s, 0.0, 0.0)
                        ON CONFLICT (investment_id, unit_price_date) DO UPDATE SET unit_price = EXCLUDED.unit_price
                    """, (inv_id, d, price))
                count += 1
            print(f"    Inserted {count} rate entries for {fticker}")
            rate_cache[fticker] = rates
        except Exception as e:
            print(f"    WARNING: Could not fetch {fticker}: {e}")
            rate_cache[fticker] = {}

    if not DRY_RUN:
        conn.commit()
    return rate_cache


def get_rate_for_date(rate_cache, ticker, target_date):
    """Find the closest forex rate on or before target_date."""
    rates = rate_cache.get(ticker, {})
    if not rates:
        return None
    candidates = [d for d in rates if d <= target_date]
    if not candidates:
        # fallback: closest future date
        candidates = sorted(rates.keys())[:1]
    best = max(candidates)
    return rates[best]


# ── Step 2: Read transactions from Excel ─────────────────────────────────────

def read_transactions(idef, wb, rate_cache):
    """Return list of dicts: {date, amount_native, amount_zar, type}"""
    txs = []

    if idef.get("excel_override"):
        # Coronation dedicated file
        cor_wb = openpyxl.load_workbook(CORONATION_EXCEL_PATH, data_only=True)
        cor_ws = cor_wb["Data"]
        for r in range(2, cor_ws.max_row + 1):
            t_date  = cor_ws.cell(row=r, column=1).value
            t_type  = cor_ws.cell(row=r, column=6).value
            price   = cor_ws.cell(row=r, column=8).value  # already in ZAR (not cents)
            t_units = cor_ws.cell(row=r, column=9).value
            t_val   = cor_ws.cell(row=r, column=10).value

            if t_date is None or t_val is None or t_val == 0:
                continue
            if isinstance(t_date, str):
                t_date = datetime.strptime(t_date.split()[0], "%Y-%m-%d")

            t_date = t_date.date() if isinstance(t_date, datetime) else t_date

            # Map transaction type
            t_type_str = str(t_type or "").lower()
            if "interest" in t_type_str:
                tx_kind = "dividend"
            elif "transfer" in t_type_str or "contribution" in t_type_str:
                tx_kind = "buy"
            elif "withdrawal" in t_type_str or "switch out" in t_type_str:
                tx_kind = "sell"
            else:
                tx_kind = "buy"

            txs.append({
                "date": t_date,
                "amount_native": float(t_val),
                "amount_zar":    float(t_val),  # ZAR fund
                "type": tx_kind,
                "unit_price": float(price) if price else 0.0,
                "units": float(t_units) if t_units else 0.0,
            })
        return txs

    # Standard sheet columns
    ws = wb[idef["sheet"]]
    date_col, val_col = idef["cols"]
    forex_ticker = idef.get("forex_ticker")
    forex_from   = idef.get("forex_from")

    for r in range(4, ws.max_row + 1):
        d_val = ws.cell(row=r, column=date_col).value
        v_val = ws.cell(row=r, column=val_col).value

        if d_val is None or v_val is None or v_val == "" or v_val == 0:
            continue
        if isinstance(d_val, str):
            try:
                d_val = datetime.strptime(d_val.split()[0], "%Y-%m-%d")
            except Exception:
                continue
        if not isinstance(d_val, (datetime, date)):
            continue

        t_date  = d_val.date() if isinstance(d_val, datetime) else d_val
        t_amount_zar = float(v_val)
        tx_kind = "sell" if t_amount_zar < 0 else "buy"
        t_amount_zar = abs(t_amount_zar)

        # Convert ZAR→native for offshore investments
        t_amount_native = t_amount_zar
        if forex_ticker and forex_from == "ZAR":
            rate = get_rate_for_date(rate_cache, forex_ticker, t_date)
            if rate and rate > 0:
                t_amount_native = t_amount_zar / rate
            else:
                print(f"    WARNING: No forex rate for {forex_ticker} on {t_date}, using ZAR amount")

        txs.append({
            "date": t_date,
            "amount_native": t_amount_native,
            "amount_zar":    t_amount_zar,
            "type": tx_kind,
            "unit_price": 0.0,
            "units": 0.0,
        })

    return txs


# ── Step 3: Import CSV unit prices ───────────────────────────────────────────

def import_csv_prices(conn, cursor, inv_map):
    """Import historic-prices-*.csv files from finances directory."""
    print("\n--- Importing CSV unit prices ---")
    files = [f for f in os.listdir(CSV_DIR) if f.startswith("historic-prices-") and f.endswith(".csv")]

    for fname in sorted(files):
        parts = fname.split('-')
        if len(parts) < 3:
            continue
        symbol = parts[2]

        # Find matching investment by ticker
        inv_id = None
        for ticker, iid in inv_map.items():
            if ticker == symbol or ticker.startswith(symbol):
                inv_id = iid
                break

        if inv_id is None:
            # Try DB lookup
            cursor.execute(
                "SELECT id FROM investments WHERE investment_ticker = %s OR investment_ticker LIKE %s",
                (symbol, symbol + "%")
            )
            row = cursor.fetchone()
            if row:
                inv_id = row[0]

        if inv_id is None:
            print(f"  No investment matches CSV symbol: {symbol} ({fname})")
            continue

        filepath = os.path.join(CSV_DIR, fname)
        with open(filepath) as fh:
            lines = fh.readlines()

        # Skip "sep=," header if present
        start = 1 if lines[0].startswith("sep=") else 0
        # Skip column header row
        count = 0
        for line in lines[start + 1:]:
            parts2 = line.strip().split(',')
            if len(parts2) != 2:
                continue
            date_str, price_str = parts2
            try:
                price_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                price_cents = float(price_str)
                # ProfileData CSVs are in cents — convert to Rands
                price = price_cents / 100.0
                if not DRY_RUN:
                    cursor.execute("""
                        INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                        VALUES (%s, %s, %s, 0.0, 0.0)
                        ON CONFLICT (investment_id, unit_price_date) DO UPDATE SET unit_price = EXCLUDED.unit_price
                    """, (inv_id, price_date, price))
                count += 1
            except Exception:
                continue

        if not DRY_RUN:
            conn.commit()
        print(f"  {fname}: {count} prices for investment_id={inv_id}")


# ── Step 4: Backfill transaction units from unit_prices ──────────────────────

def backfill_units(conn, cursor):
    """Set unit_price and number_of_units on transactions that have neither."""
    print("\n--- Backfilling transaction units ---")
    cursor.execute("""
        SELECT t.id, t.investment_id, t.transaction_date, t.transaction_amount, t.transaction_type, i.investment_name
        FROM transactions t
        JOIN investments i ON t.investment_id = i.id
        WHERE (t.unit_price = 0 OR t.unit_price IS NULL)
          AND i.investment_type != 'Forex'
    """)
    txs = cursor.fetchall()
    print(f"  {len(txs)} transactions need backfilling")
    updated = 0
    for tx_id, inv_id, tx_date, tx_amount, tx_type, inv_name in txs:
        # Closest price on or before date
        cursor.execute("""
            SELECT unit_price FROM unit_prices
            WHERE investment_id = %s AND unit_price_date <= %s
            ORDER BY unit_price_date DESC LIMIT 1
        """, (inv_id, tx_date))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                SELECT unit_price FROM unit_prices
                WHERE investment_id = %s
                ORDER BY unit_price_date ASC LIMIT 1
            """, (inv_id,))
            row = cursor.fetchone()

        if row:
            price = float(row[0])
            if price > 0:
                units = float(tx_amount) / price
                if not DRY_RUN:
                    cursor.execute("""
                        UPDATE transactions SET unit_price = %s, number_of_units = %s WHERE id = %s
                    """, (price, units, tx_id))
                updated += 1

    # Update investments.number_of_units_held and unit_price
    cursor.execute("SELECT id FROM investments WHERE investment_type != 'Forex'")
    for (inv_id,) in cursor.fetchall():
        cursor.execute("""
            SELECT COALESCE(SUM(CASE WHEN transaction_type IN ('buy','Buy') THEN number_of_units
                                     WHEN transaction_type IN ('sell','Sell') THEN -number_of_units
                                     ELSE 0 END), 0)
            FROM transactions WHERE investment_id = %s
        """, (inv_id,))
        total_units = float(cursor.fetchone()[0] or 0)

        cursor.execute("""
            SELECT unit_price FROM unit_prices
            WHERE investment_id = %s ORDER BY unit_price_date DESC LIMIT 1
        """, (inv_id,))
        price_row = cursor.fetchone()
        latest_price = float(price_row[0]) if price_row else 0.0

        if not DRY_RUN:
            cursor.execute("""
                UPDATE investments SET number_of_units_held = %s, unit_price = %s WHERE id = %s
            """, (total_units, latest_price, inv_id))

    if not DRY_RUN:
        conn.commit()
    print(f"  Updated {updated} transactions, refreshed investment holdings")


# ── Step 5: Verify against Performance sheet ────────────────────────────────

def verify_irr(conn, cursor):
    """Compare DB-computed XIRR against target values from the Performance sheet."""
    print("\n--- IRR verification ---")
    # From Performance sheet row 3-14 col H (Annualized Return)
    TARGETS = {
        "Allan Gray Equity Fund":                   0.17433,
        "Allan Gray Balanced Fund":                 0.15795,
        "PSG Balanced Fund (E) - RA":               0.31993,
        "Coronation Top 20 Fund":                   0.10297,
        "PSG Global Equity Feeder Fund (E) - Voluntary": -0.15201,
        "PSG Global Flexible Feeder Fund (C)":      0.37399,
        "Satrix Nasdaq 100 ETF (ZAR)":              0.18252,
        "iShares MSCI World ETF (USD)":             0.09440,
        "iShares CORE MSCI Europe ETF (GBP)":       0.11480,
    }

    cursor.execute("SELECT id, investment_name, number_of_units_held, unit_price FROM investments WHERE investment_type != 'Forex'")
    investments = cursor.fetchall()

    for inv_id, name, units, price in investments:
        cursor.execute("""
            SELECT transaction_date, transaction_amount, transaction_type
            FROM transactions WHERE investment_id = %s ORDER BY transaction_date
        """, (inv_id,))
        txs = cursor.fetchall()
        if not txs:
            continue

        cashflows = []
        for tx_date, amt, tx_type in txs:
            if tx_type in ('buy', 'Buy'):
                cashflows.append((tx_date, -float(amt)))
            elif tx_type in ('sell', 'Sell'):
                cashflows.append((tx_date, float(amt)))

        current_value = float((units or 0) * (price or 0))
        if current_value > 0:
            cashflows.append((date.today(), current_value))

        if len(cashflows) < 2:
            continue

        irr = xirr(cashflows) * 100
        target = TARGETS.get(name)
        if target is not None:
            diff = abs(irr - target * 100)
            status = "✅ PASS" if diff < 3.0 else "❌ FAIL"
            print(f"  {name:<50} DB={irr:>7.2f}%  Target={target*100:>7.2f}%  diff={diff:.2f}%  {status}")
        else:
            print(f"  {name:<50} DB={irr:>7.2f}%  (no target)")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"=== Investment Excel Import {'(DRY RUN)' if DRY_RUN else ''} ===\n")

    conn   = get_connection()
    cursor = conn.cursor()

    # Clean existing data
    print("--- Cleaning old investment data ---")
    if not DRY_RUN:
        for tbl in [
            "portfolio_metrics", "investment_metrics", "prediction_accuracy",
            "predictions", "returns", "fees", "tax", "dividends",
            "transactions", "unit_prices", "factsheets", "investment_source_meta",
        ]:
            cursor.execute(f"TRUNCATE TABLE {tbl} CASCADE;")
        cursor.execute("DELETE FROM investments;")
        conn.commit()
    else:
        print("  (dry run — skipping truncate)")

    # Ensure forex investments + rates exist first
    print("\n--- Setting up forex rates ---")
    rate_cache = ensure_forex(conn, cursor)

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

    inv_map = {}  # ticker → investment_id

    for idef in INVESTMENTS_DEF:
        print(f"\nProcessing: {idef['name']} …")
        txs = read_transactions(idef, wb, rate_cache)

        if not txs:
            print("  No transactions found — skipping")
            continue

        start_date = min(t["date"] for t in txs)
        print(f"  {len(txs)} transactions from {start_date}")

        if not DRY_RUN:
            cursor.execute("""
                INSERT INTO investments (
                    institution_name, initial_investment_date, investment_type,
                    investment_name, investment_ticker, unit_currency,
                    initial_unit_price, unit_price, number_of_units_held,
                    total_dividends_received, total_tax_paid, total_fees_paid,
                    investment_fee, investment_status, investment_subtype
                ) VALUES (%s,%s,%s,%s,%s,%s, 0.0,0.0,0.0, 0.0,0.0,0.0, 0.0,%s,%s)
                RETURNING id
            """, (idef["inst"], start_date, idef["type"], idef["name"],
                  idef["ticker"], idef["curr"], idef["status"], idef["subtype"]))
            inv_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO investment_source_meta (investment_id, source, source_ticker, backfill_complete)
                VALUES (%s, %s, %s, false)
            """, (inv_id, idef["source"], idef["ticker"]))

            for tx in txs:
                cursor.execute("""
                    INSERT INTO transactions (investment_id, transaction_date, transaction_type,
                                             transaction_amount, unit_price, number_of_units)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (inv_id, tx["date"], tx["type"], tx["amount_native"],
                      tx["unit_price"], tx["units"]))

            conn.commit()
            inv_map[idef["ticker"]] = inv_id
            print(f"  → investment_id={inv_id}")
        else:
            print(f"  → would insert investment + {len(txs)} transactions")

    # Import CSV price files
    import_csv_prices(conn, cursor, inv_map)

    # Backfill units on transactions
    backfill_units(conn, cursor)

    # Verify IRR
    verify_irr(conn, cursor)

    cursor.close()
    conn.close()
    print("\n=== Import complete ===")


if __name__ == "__main__":
    main()
