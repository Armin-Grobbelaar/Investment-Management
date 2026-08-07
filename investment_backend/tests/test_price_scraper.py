"""
Tests for price_scraper.py module.
"""

import pytest
import pandas as pd
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from modules.price_scraper import (
    _determine_source_and_ticker,
    _fetch_yfinance,
    _fetch_fundsdata_current,
    fetch_current_price,
    backfill_historical_prices
)

class TestPriceScraper:
    """Test price scraping functionality."""

    def test_determine_source_and_ticker(self):
        """Test logic for determining price source."""
        # SA unit trust (type + short code) → profiledata
        assert _determine_source_and_ticker(
            {"investment_ticker": "AGBF", "investment_type": "Unit Trust"}
        ) == ("profiledata", "AGBF")
        # SA unit trust detected by CIS manager in the name
        assert _determine_source_and_ticker(
            {"investment_ticker": "AGBF", "investment_name": "Allan Gray Balanced Fund"}
        ) == ("profiledata", "AGBF")
        # JSE ticker → yfinance
        assert _determine_source_and_ticker({"investment_ticker": "STXNDQ.JO"}) == ("yfinance", "STXNDQ.JO")
        # Bare international ticker (no unit-trust hint) → yfinance, NOT profiledata
        assert _determine_source_and_ticker({"investment_ticker": "MSFT"}) == ("yfinance", "MSFT")
        assert _determine_source_and_ticker({"investment_ticker": ""}) == ("none", "")
        # Explicit persisted source wins
        assert _determine_source_and_ticker(
            {"investment_ticker": "AGBF", "source": "yfinance", "source_ticker": "ZNQ.JO"}
        ) == ("yfinance", "ZNQ.JO")

    def test_fetch_yfinance(self):
        """Test fetching data from yfinance."""
        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        
        # Create a mock dataframe like yfinance returns
        mock_df = pd.DataFrame({
            "Date": [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")],
            "Close": [100.0, 105.0]
        })
        mock_df.set_index("Date", inplace=True)
        
        mock_ticker.history.return_value = mock_df
        mock_yf.Ticker.return_value = mock_ticker
        
        with patch.dict('sys.modules', {'yfinance': mock_yf}):
            result = _fetch_yfinance("SPY.US")
            
            assert not result.empty
            assert "Date" in result.columns
            assert "Close" in result.columns
            assert len(result) == 2
            assert result.iloc[1]["Close"] == 105.0

    @patch('modules.price_scraper._session.get')
    def test_fetch_fundsdata_current(self, mock_get):
        """Test scraping fundsdata current price."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # HTML that matches the regex: NAV[^<]{0,100}<td[^>]*>([\d\s,]+\.?\d*)</td>
        mock_resp.text = '<html><body><table><tr><td>NAV <td class="price">1234.56</td></tr></table></body></html>'
        mock_get.return_value = mock_resp
        
        price = _fetch_fundsdata_current("AGBF")
        
        assert price == 1234.56

    @patch('modules.price_scraper._persist_source_meta')
    @patch('modules.price_scraper._update_investment_current_price')
    @patch('modules.price_scraper._upsert_price')
    @patch('modules.price_scraper._fetch_yfinance')
    def test_fetch_current_price_yfinance(self, mock_yf, mock_upsert, mock_update, mock_persist):
        """Test fetching and saving current price."""
        # Mock yfinance return
        mock_df = pd.DataFrame({
            "Date": [date.today()],
            "Close": [150.0]
        })
        mock_yf.return_value = mock_df
        
        inv = {"id": 1, "investment_name": "Test Stocks", "investment_ticker": "SPY.JO"}
        
        price = fetch_current_price(inv, "test_db")
        
        assert price == 150.0
        mock_upsert.assert_called_once_with("test_db", 1, date.today(), 150.0)
        mock_update.assert_called_once_with("test_db", 1, 150.0)

    @patch('modules.price_scraper._persist_source_meta')
    @patch('modules.price_scraper._update_investment_current_price')
    @patch('modules.price_scraper._upsert_price')
    @patch('modules.profiledata_scraper.fetch_profiledata_prices')
    @patch('modules.price_scraper._determine_source_and_ticker')
    def test_fetch_current_price_profiledata(self, mock_det, mock_profiledata,
                                             mock_upsert, mock_update, mock_persist):
        """Test current price via ProfileData (unit trust source)."""
        mock_det.return_value = ("profiledata", "")
        mock_profiledata.return_value = [(date.today(), 805.43), (date.today(), 806.11)]

        inv = {"id": 5, "investment_name": "Allan Gray Equity Fund Class A",
               "investment_ticker": ""}

        price = fetch_current_price(inv, "test_db")

        assert price == 806.11  # last price in the list
        mock_upsert.assert_called_once()
        mock_update.assert_called_once_with("test_db", 5, 806.11)
        mock_persist.assert_called_once()

    @patch('modules.price_scraper._persist_source_meta')
    @patch('modules.price_scraper._update_investment_current_price')
    @patch('modules.price_scraper._upsert_price')
    @patch('modules.price_scraper._fetch_yfinance')
    @patch('modules.profiledata_scraper.fetch_profiledata_prices')
    @patch('modules.price_scraper._determine_source_and_ticker')
    def test_fetch_current_price_profiledata_falls_back_to_yfinance(
            self, mock_det, mock_profiledata, mock_yf, mock_upsert, mock_update, mock_persist):
        """ProfileData fails → yfinance fallback."""
        mock_det.return_value = ("profiledata", "ZNQ.JO")
        mock_profiledata.return_value = []  # ProfileData returned nothing
        mock_df = pd.DataFrame({"Date": [date.today()], "Close": [123.45]})
        mock_yf.return_value = mock_df

        inv = {"id": 6, "investment_name": "Some Fund", "investment_ticker": "ZNQ.JO"}

        price = fetch_current_price(inv, "test_db")

        assert price == 123.45
        mock_yf.assert_called_once_with("ZNQ.JO")

    @patch('modules.price_scraper._persist_source_meta')
    @patch('modules.price_scraper._update_investment_current_price')
    @patch('modules.price_scraper._upsert_price')
    @patch('modules.price_scraper._fetch_stooq')
    @patch('modules.price_scraper._fetch_yfinance')
    @patch('modules.price_scraper._determine_source_and_ticker')
    def test_fetch_current_price_yfinance_falls_back_to_stooq(
            self, mock_det, mock_yf, mock_stooq, mock_upsert, mock_update, mock_persist):
        """yfinance fails → stooq fallback."""
        mock_det.return_value = ("yfinance", "QQQ")
        mock_yf.return_value = pd.DataFrame()  # empty → fail
        mock_stooq.return_value = pd.DataFrame({"Date": [date.today()], "Close": [321.0]})

        inv = {"id": 7, "investment_name": "QQQ", "investment_ticker": "QQQ"}

        price = fetch_current_price(inv, "test_db")

        assert price == 321.0
        mock_stooq.assert_called_once_with("QQQ")

    @patch('modules.price_scraper._persist_source_meta')
    @patch('modules.price_scraper._get_existing_price_dates')
    @patch('modules.price_scraper._get_earliest_investment_date')
    @patch('modules.price_scraper._fetch_yfinance')
    @patch('modules.price_scraper._upsert_price')
    def test_backfill_historical_prices(self, mock_upsert, mock_yf, mock_earliest, mock_existing, mock_persist):
        """Test backfilling missing historical prices."""
        # Mock database states
        start_date = (pd.Timestamp(date.today()) - pd.tseries.offsets.BDay(5)).date()
        mock_earliest.return_value = start_date
        
        # Missing yesterday (guaranteed business day)
        yesterday = (pd.Timestamp(date.today()) - pd.tseries.offsets.BDay(1)).date()
        mock_existing.return_value = {start_date}
        
        # Mock yfinance return
        mock_df = pd.DataFrame({
            "Date": [yesterday],
            "Close": [140.0]
        })
        mock_yf.return_value = mock_df
        
        # Use ticker that defaults to yfinance
        inv = {"id": 1, "investment_name": "Test Stocks", "investment_ticker": "SPY.JO"}
        
        stored = backfill_historical_prices(inv, "test_db", batch_size=1)
        
        # It should have attempted to store the missing date
        assert stored == 1
        mock_upsert.assert_called_once()
