import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from .database import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, get_db_connection

def _fetch_and_store_historical_data(cursor, investment_ticker: str, investment_id: int, database_name: str) -> None:
    """Fetch and store historical price data from Yahoo Finance."""
    try:
        ticker = yf.Ticker(investment_ticker)
        ticker_data = ticker.history(period="max")

        if ticker_data.empty:
            print(f"No historical data available for {investment_ticker} from Yahoo Finance.")
            return

        ticker_data.reset_index(inplace=True)
        
        # Prepare dataframe
        investment_unit_prices = pd.DataFrame()
        investment_unit_prices["unit_price_date"] = pd.to_datetime(ticker_data["Date"]).dt.date
        investment_unit_prices["unit_price"] = ticker_data["Close"]
        
        # Reindex to daily frequency
        investment_unit_prices["unit_price_date"] = pd.to_datetime(investment_unit_prices["unit_price_date"])
        investment_unit_prices = (
            investment_unit_prices.set_index("unit_price_date")
            .reindex(pd.date_range(investment_unit_prices.index.min(), investment_unit_prices.index.max(), freq="D"))
            .rename_axis(["unit_price_date"])
            .reset_index()
        )
        investment_unit_prices["unit_price"] = investment_unit_prices["unit_price"].ffill()
        
        # Drop any remaining rows with null unit_price
        investment_unit_prices = investment_unit_prices.dropna(subset=["unit_price"])
        
        if investment_unit_prices.empty:
            print(f"No valid price data available for {investment_ticker} after cleaning")
            return
        
        # Calculate changes
        investment_unit_prices["unit_price_change"] = investment_unit_prices["unit_price"].diff().fillna(0)
        investment_unit_prices["percentage_unit_price_change"] = (
            investment_unit_prices["unit_price_change"] / investment_unit_prices["unit_price"].shift(1) * 100
        ).fillna(0)
        
        investment_unit_prices["investment_id"] = investment_id

        # NOTE: yfinance JSE (.JO) Close prices are already in Rands, even
        # though ticker.info["currency"] may report "ZAc" (a known yfinance
        # metadata quirk for JSE stocks). Do NOT divide by 100 here — that
        # would corrupt Rands-denominated prices into cents and mix scales
        # with manually-entered prices (which are in Rands).

        # Insert historical data
        engine_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{database_name}"
        engine = create_engine(engine_url)
        
        investment_unit_prices.to_sql("unit_prices", engine, index=False, if_exists="append", method="multi", chunksize=1000)
        
        # Update current price
        if not investment_unit_prices.empty:
            latest_price = float(investment_unit_prices.iloc[-1]["unit_price"])
            with engine.connect() as conn:
                 conn.execute(
                     text("UPDATE investments SET unit_price = :price WHERE id = :id"),
                     {"price": latest_price, "id": investment_id}
                 )
                 conn.commit()
            
        print(f"Historical data for {investment_ticker} successfully imported.")

    except Exception as e:
        print(f"Error fetching historical data for {investment_ticker}: {e}")
        import traceback
        traceback.print_exc()

def _handle_forex_investment(cursor, investment_id: int, unit_currency: str, initial_date: str, institution_name: str, database_name: str) -> None:
    """
    Handle automatic creation of Forex investment if needed.
    """
    # If the investment is not in ZAR (native currency), we might need to track the exchange rate
    if unit_currency == "R" or unit_currency == "ZAR":
        return

    # Check if we already have a forex investment for this currency pair (e.g. USDZAR=X)
    forex_ticker = f"{unit_currency}ZAR=X"
    
    cursor.execute("SELECT id FROM investments WHERE investment_ticker = %s", (forex_ticker,))
    if cursor.fetchone():
        return  # Already exists

    print(f"Creating automatic Forex investment for {unit_currency}...")
    
    # We need to call add_investment recursively, but we can't import it here directly due to circular imports.
    # We'll do a direct insert instead.
    
    try:
        # Fetch initial data for forex
        ticker = yf.Ticker(forex_ticker)
        hist = ticker.history(period="1d")
        
        if hist.empty:
            print(f"Could not fetch data for {forex_ticker}")
            return
            
        current_price = float(hist["Close"].iloc[-1])
        
        cursor.execute("""
            INSERT INTO investments (
                institution_name, initial_investment_date, investment_type,
                investment_name, investment_ticker, unit_currency,
                initial_unit_price, unit_price, number_of_units_held,
                total_dividends_received, total_tax_paid, total_fees_paid,
                investment_fee, investment_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            institution_name, initial_date, "Forex",
            f"{unit_currency}/ZAR Exchange Rate", forex_ticker, "ZAR",
            current_price, current_price, 0, # 0 units held as it's just for tracking
            0, 0, 0, 0, "Active"
        ))
        
        forex_id = cursor.fetchone()[0]
        
        # Fetch history for this new forex investment
        _fetch_and_store_historical_data(cursor, forex_ticker, forex_id, database_name)
        
    except Exception as e:
        print(f"Error creating forex investment: {e}")
