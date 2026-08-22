"""
Tests for currency.py module.
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from modules.currency import (
    get_exchange_rate, convert_currency_amount,
    convert_investment_data_for_display, get_available_base_currencies,
    SUPPORTED_BASE_CURRENCIES
)

class TestCurrencyOperations:
    """Test currency conversion and exchange rate logic."""

    @patch('modules.currency.get_db_connection')
    def test_get_exchange_rate_same_currency(self, mock_get_db):
        """Test getting exchange rate when currencies are the same."""
        rate, src_date = get_exchange_rate("ZAR", "ZAR")
        assert rate == 1.0
        assert not mock_get_db.called

    @patch('modules.currency.get_db_connection')
    def test_get_exchange_rate_direct_pair(self, mock_get_db):
        """Test getting exchange rate with a direct forex pair."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        
        mock_cursor.fetchone.side_effect = [(15.5, '2023-01-01')]
        
        rate, src_date = get_exchange_rate("USD", "ZAR", "2023-01-01", "test_db")
        
        assert rate == 15.5
        assert src_date == '2023-01-01'

    @patch('modules.currency.get_db_connection')
    def test_get_exchange_rate_inverse_pair(self, mock_get_db):
        """Test getting exchange rate when only reverse pair exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        
        mock_cursor.fetchone.side_effect = [None, (0.05, '2023-01-01')]
        
        rate, src_date = get_exchange_rate("ZAR", "USD", "2023-01-01", "test_db")
        
        assert rate == 1.0 / 0.05
        assert src_date == '2023-01-01'

    @patch('modules.currency.get_db_connection')
    def test_get_exchange_rate_no_pair(self, mock_get_db):
        """Test getting exchange rate when no pair exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        
        mock_cursor.fetchone.side_effect = [None, None, None]
        
        rate, src_date = get_exchange_rate("CAD", "ZAR", "2023-01-01")
        
        assert rate == 1.0

    @patch('modules.currency.get_exchange_rate')
    def test_convert_currency_amount(self, mock_get_rate):
        """Test converting monetary amounts."""
        mock_get_rate.return_value = (15.0, "2023-01-01")
        
        amount1 = convert_currency_amount(100.0, "USD", "ZAR", "2023-01-01")
        assert amount1 == 1500.0
        mock_get_rate.assert_called_once_with("USD", "ZAR", "2023-01-01", "investments_app", None)

    @patch('modules.currency.get_db_connection')
    @patch('modules.currency.convert_currency_amount')
    def test_convert_investment_data_for_display(self, mock_convert, mock_get_db):
        """Test converting entire dataframe for display."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        
        mock_convert.side_effect = lambda amt, *args, **kwargs: amt * 10
        
        df = pd.DataFrame({
            "unit_currency": ["USD", "EUR"],
            "unit_price": [10.0, 20.0],
            "investment_value": [100.0, 200.0],
            "unit_price_date": ["2023-01-01", "2023-01-02"]
        })
        
        result_df = convert_investment_data_for_display(df, "ZAR", "test_db")
        
        assert result_df["unit_price"].tolist() == [100.0, 200.0]
        assert result_df["investment_value"].tolist() == [1000.0, 2000.0]
        assert result_df["unit_currency"].tolist() == ["ZAR", "ZAR"]
        assert result_df["display_currency"].tolist() == ["ZAR", "ZAR"]

    def test_get_available_base_currencies(self):
        """Test getting available base currencies."""
        currencies = get_available_base_currencies()
        assert set(currencies) >= set(SUPPORTED_BASE_CURRENCIES)

    @patch('modules.currency.get_exchange_rate')
    def test_convert_currency_amount_with_cache(self, mock_get_rate):
        """Test convert_currency_amount uses rate_cache when provided."""
        mock_get_rate.return_value = (18.5, "2023-01-01")
        cache = {}
        
        # First call populates cache
        res1 = convert_currency_amount(100.0, "USD", "ZAR", "2023-01-01", rate_cache=cache)
        assert res1 == 1850.0
        assert cache[("USD", "ZAR", "2023-01-01")] == 18.5
        assert mock_get_rate.call_count == 1

        # Second call uses cache without calling get_exchange_rate again
        res2 = convert_currency_amount(50.0, "USD", "ZAR", "2023-01-01", rate_cache=cache)
        assert res2 == 925.0
        assert mock_get_rate.call_count == 1
