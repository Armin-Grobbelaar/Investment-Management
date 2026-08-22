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
    Ensure exchange rate data exists for a foreign-currency investment.

    When a non-base-currency investment is added, this downloads historical
    exchange rates into the `exchange_rates` table (if not already present).
    No Forex pseudo-investment is created — exchange rates are stored in their
    own dedicated table.
    """
    from .currency import resolve_currency_code, BASE_CURRENCY_CODE, ensure_exchange_rates_exist

    inv_curr = resolve_currency_code(unit_currency)
    if inv_curr == BASE_CURRENCY_CODE:
        return  # Same currency — no FX needed

    print(f"🔄 Ensuring exchange rates exist for {inv_curr}/{BASE_CURRENCY_CODE}...")
    try:
        ensure_exchange_rates_exist(inv_curr, BASE_CURRENCY_CODE, database_name)
    except Exception as e:
        print(f"⚠️ Could not sync exchange rates for {inv_curr}/{BASE_CURRENCY_CODE}: {e}")
        print("   Currency conversion will fall back to rate=1.0 until rates are synced.")
