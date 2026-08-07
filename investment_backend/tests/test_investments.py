"""
Tests for investments.py module.
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock

from modules.investments import (
    add_investment, get_investment_summary, get_investment_summary_display,
    get_currencies_in_portfolio, get_investment_types_in_portfolio,
    get_all_investment_values, get_investment_data, get_portfolio_total_value,
    get_investment_names_list
)


class TestInvestmentOperations:
    """Test investment CRUD operations."""

    @patch('modules.investments.get_db_connection')
    def test_add_investment_success(self, mock_get_db):
        """Test successful investment addition."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock existing investments check (empty result)
        mock_cursor.fetchall.return_value = []

        # Mock the INSERT RETURNING
        mock_cursor.fetchone.return_value = (123,)

        result = add_investment(
            "test_db",
            institution_name="Test Bank",
            initial_investment_date="2023-01-01",
            investment_type="Stocks",
            investment_name="Test Investment",
            investment_ticker="TEST",
            unit_currency="ZAR",
            initial_unit_price=100.0,
            unit_price=110.0,
            number_of_units_held=10.0,
            total_dividends_received=0.0,
            total_tax_paid=0.0,
            total_fees_paid=0.0,
            investment_fee=0.0,
            investment_status="Active"
        )

        # Verify database operations were called
        assert mock_cursor.execute.called
        assert mock_connection.commit.called

    @patch('modules.investments.get_db_connection')
    def test_add_investment_duplicate(self, mock_get_db):
        """Test adding duplicate investment."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock existing investments (duplicate found)
        mock_cursor.fetchall.return_value = [(123, "Test Bank", "Test Investment")]

        result = add_investment(
            "test_db",
            institution_name="Test Bank",
            initial_investment_date="2023-01-01",
            investment_type="Stocks",
            investment_name="Test Investment",
            investment_ticker="TEST",
            unit_currency="ZAR",
            initial_unit_price=100.0,
            unit_price=110.0,
            number_of_units_held=10.0,
            total_dividends_received=0.0,
            total_tax_paid=0.0,
            total_fees_paid=0.0,
            investment_fee=0.0,
            investment_status="Active"
        )

        # Should not proceed with insertion
        assert result is None


class TestInvestmentQueries:
    """Test investment data queries."""

    @patch('modules.investments.get_db_connection')
    def test_get_investment_summary(self, mock_get_db):
        """Test getting investment summary."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock column descriptions and data
        mock_cursor.description = [
            ('id',), ('institution_name',), ('initial_investment_date',),
            ('investment_type',), ('investment_name',), ('investment_ticker',),
            ('unit_currency',), ('initial_unit_price',), ('unit_price',),
            ('number_of_units_held',), ('total_dividends_received',),
            ('total_tax_paid',), ('total_fees_paid',), ('investment_fee',),
            ('investment_status',)
        ]

        mock_cursor.fetchall.return_value = [
            (1, "Test Bank", "2023-01-01", "Stocks", "Test Investment", "TEST",
             "ZAR", 100.0, 110.0, 10.0, 0.0, 0.0, 0.0, 0.0, "Active")
        ]

        result = get_investment_summary("test_db")

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "investment_name" in result.columns

    @patch('modules.investments.get_investment_summary')
    def test_get_currencies_in_portfolio(self, mock_get_summary):
        """Test getting currencies in portfolio."""
        mock_summary = pd.DataFrame({
            'unit_currency': ['ZAR', 'USD', 'EUR', 'ZAR']
        })
        mock_get_summary.return_value = mock_summary

        result = get_currencies_in_portfolio("test_db")

        assert isinstance(result, list)
        assert len(result) == 3
        assert "ZAR" in result
        assert "USD" in result
        assert "EUR" in result

    @patch('modules.investments.get_investment_summary')
    def test_get_investment_types_in_portfolio(self, mock_get_summary):
        """Test getting investment types in portfolio."""
        mock_summary = pd.DataFrame({
            'investment_type': ['Stocks', 'Bonds', 'ETFs', 'Stocks']
        })
        mock_get_summary.return_value = mock_summary

        result = get_investment_types_in_portfolio("test_db")

        assert isinstance(result, list)
        assert len(result) == 3
        assert "Stocks" in result

    @patch('modules.investments.get_db_connection')
    def test_get_investment_names_list(self, mock_get_db):
        """Test getting investment names list."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock investment names
        mock_cursor.fetchall.return_value = [
            ("Test Investment A", "TICKERA"),
            ("Test Investment B", "TICKERB")
        ]

        result = get_investment_names_list("test_db")

        assert isinstance(result, list)
        assert len(result) == 2
        assert "Test Investment A (TICKERA)" in result


class TestPortfolioOperations:
    """Test portfolio-level operations."""

    @patch('modules.investments.get_investment_data')
    def test_get_portfolio_total_value_empty_data(self, mock_get_data):
        """Test portfolio total value with empty data."""
        mock_get_data.return_value = pd.DataFrame()
        result = get_portfolio_total_value("ZAR", "test_db")

        assert isinstance(result, dict)
        assert "total_value" in result
        assert "by_currency" in result
        assert "by_type" in result
        assert result["total_value"] == 0.0

    @patch('modules.investments.get_investment_data')
    def test_get_portfolio_total_value_with_data(self, mock_get_data):
        """Test portfolio total value calculation."""
        # Mock investment data
        mock_df = pd.DataFrame({
            'id': [1, 2],
            'investment_name': ['Inv A', 'Inv B'],
            'unit_currency': ['ZAR', 'USD'],
            'investment_type': ['Stocks', 'Bonds'],
            'investment_value': [1000.0, 2000.0],
            'unit_price_date': ['2023-01-01', '2023-01-01']
        })
        mock_get_data.return_value = mock_df

        result = get_portfolio_total_value("ZAR", "test_db")

        assert isinstance(result, dict)
        assert result["total_value"] > 0
        assert "by_currency" in result
        assert "by_type" in result
