"""
Standalone price backfill script — run on host to populate unit_prices from yfinance.
Targets investments with source='yfinance' that have no (or few) prices.
"""
import os, psycopg2
from datetime import date
import yfinance as yf

POSTGRES_HOST     = os.environ.get("POSTGRES_HOST",     "localhost")
POSTGRES_PORT     = int(os.environ.get("POSTGRES_PORT", 5432))
POSTGRES_USER     = os.environ.get("POSTGRES_USER",     "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "changeme")
INVESTMENTS_DB    = os.environ.get("INVESTMENTS_DB",    "Investments")

conn   = psycopg2.connect(host=POSTGRES_HOST, port=POSTGRES_PORT,
                           user=POSTGRES_USER, password=POSTGRES_PASSWORD,
                           database=INVESTMENTS_DB)
cursor = conn.cursor()

# Get all yfinance investments (not Forex)
cursor.execute("""
    SELECT i.id, i.investment_name, m.source_ticker, i.unit_currency
    FROM investments i
    JOIN investment_source_meta m ON m.investment_id = i.id
    WHERE m.source = 'yfinance'
      AND i.investment_type != 'Forex'
""")
investments = cursor.fetchall()
print(f"Found {len(investments)} yfinance investments to backfill\n")

for inv_id, name, ticker, currency in investments:
    cursor.execute("SELECT COUNT(*) FROM unit_prices WHERE investment_id = %s", (inv_id,))
    existing = cursor.fetchone()[0]
    if existing > 100:
        print(f"  {name}: already has {existing} prices — skipping")
        continue

    print(f"  Fetching {ticker} ({currency}) …")
    try:
        data = yf.download(ticker, period="max", auto_adjust=True, progress=False)
        if data.empty:
            print(f"    No data from yfinance for {ticker}")
            continue

        count = 0
        for idx, row in data.iterrows():
            d = idx.date() if hasattr(idx, 'date') else idx
            try:
                close_val = row['Close']
                price = float(close_val.iloc[0] if hasattr(close_val, 'iloc') else close_val)
            except Exception:
                continue

            cursor.execute("""
                INSERT INTO unit_prices (investment_id, unit_price_date, unit_price, unit_price_change, percentage_unit_price_change)
                VALUES (%s, %s, %s, 0.0, 0.0)
                ON CONFLICT (investment_id, unit_price_date) DO UPDATE SET unit_price = EXCLUDED.unit_price
            """, (inv_id, d, price))
            count += 1

        conn.commit()
        print(f"    → {count} prices inserted")

        # Update investment.unit_price with latest
        cursor.execute("""
            SELECT unit_price FROM unit_prices WHERE investment_id = %s ORDER BY unit_price_date DESC LIMIT 1
        """, (inv_id,))
        row2 = cursor.fetchone()
        if row2:
            cursor.execute("UPDATE investments SET unit_price = %s WHERE id = %s", (float(row2[0]), inv_id))
            conn.commit()

    except Exception as e:
        print(f"    ERROR: {e}")

# Now re-backfill transaction units
print("\n--- Re-backfilling transaction units ---")
cursor.execute("""
    SELECT t.id, t.investment_id, t.transaction_date, t.transaction_amount
    FROM transactions t
    JOIN investments i ON t.investment_id = i.id
    WHERE (t.unit_price = 0 OR t.unit_price IS NULL)
      AND t.transaction_type IN ('buy','Buy','sell','Sell')
      AND i.investment_type != 'Forex'
""")
txs = cursor.fetchall()
print(f"  {len(txs)} transactions to update")

updated = 0
for tx_id, inv_id, tx_date, tx_amount in txs:
    cursor.execute("""
        SELECT unit_price FROM unit_prices
        WHERE investment_id = %s AND unit_price_date <= %s
        ORDER BY unit_price_date DESC LIMIT 1
    """, (inv_id, tx_date))
    row = cursor.fetchone()
    if not row:
        cursor.execute("""
            SELECT unit_price FROM unit_prices WHERE investment_id = %s ORDER BY unit_price_date ASC LIMIT 1
        """, (inv_id,))
        row = cursor.fetchone()
    if row and float(row[0]) > 0:
        price = float(row[0])
        units = float(tx_amount) / price
        cursor.execute("UPDATE transactions SET unit_price=%s, number_of_units=%s WHERE id=%s", (price, units, tx_id))
        updated += 1

# Update total units held per investment
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
        SELECT unit_price FROM unit_prices WHERE investment_id = %s ORDER BY unit_price_date DESC LIMIT 1
    """, (inv_id,))
    pr = cursor.fetchone()
    latest_price = float(pr[0]) if pr else 0.0
    cursor.execute("UPDATE investments SET number_of_units_held=%s, unit_price=%s WHERE id=%s",
                   (total_units, latest_price, inv_id))

conn.commit()
print(f"  Updated {updated} transactions, refreshed holdings")

cursor.close()
conn.close()
print("\n=== Backfill complete ===")
