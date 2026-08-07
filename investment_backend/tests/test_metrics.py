"""
Tests for metrics.py module.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date
from unittest.mock import patch, MagicMock

from modules.metrics import (
    xirr, is_leap_year, adjust_value, adjust_for_inflation,
    calculate_investment_metrics, update_investment_metrics,
    recalculate_investment_metrics_history, get_investment_metrics_data,
    get_investment_metrics_by_name_data
)


class TestFinancialCalculations:
    """Test financial calculation functions."""

    def test_xirr_calculation(self):
        """Test XIRR (Internal Rate of Return) calculation."""
        # Simple test case: investment of $1000, returns $1100 after 1 year
        dates = [datetime(2023, 1, 1), datetime(2024, 1, 1)]
        amounts = [-1000.0, 1100.0]  # Negative for investment, positive for return

        irr = xirr(dates, amounts)

        # Should be approximately 10% (0.1)
        assert irr is not None
        assert 0.08 <= irr <= 0.12  # Allow some tolerance

    def test_xirr_empty_data(self):
        """Test XIRR with empty data."""
        result = xirr([], [])
        assert result == 0.0

    def test_is_leap_year(self):
        """Test leap year detection."""
        assert is_leap_year(2024) is True   # 2024 is leap year
        assert is_leap_year(2023) is False  # 2023 is not leap year
        assert is_leap_year(2000) is True   # 2000 is leap year (divisible by 400)
        assert is_leap_year(1900) is False  # 1900 is not leap year (divisible by 100 but not 400)


class TestInflationAdjustment:
    """Test inflation adjustment functions."""

    def test_adjust_value_simple(self):
        """Test simple value adjustment for inflation."""
        # Value of $100 in 2020, adjusted to 2023
        # Assuming 3% annual inflation: $100 * (1.03)^3 ≈ $109.27
        result = adjust_value(100.0, date(2020, 1, 1), date(2023, 1, 1), pd.DataFrame())
        # With empty inflation DataFrame, should return original value
        assert result == 100.0

    def test_adjust_for_inflation_empty_df(self):
        """Test inflation adjustment with empty DataFrame."""
        df = pd.DataFrame()
        result = adjust_for_inflation(df, pd.DataFrame(), date.today())
        assert result.empty


class TestInvestmentMetrics:
    """Test investment metrics calculation."""

    def test_calculate_investment_metrics_empty_data(self):
        """Test metrics calculation with empty data."""
        result = calculate_investment_metrics()
        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    def test_calculate_investment_metrics_basic(self):
        """Test basic metrics calculation."""
        # Create sample data
        contrib_df = pd.DataFrame({
            'date': [datetime(2023, 1, 1), datetime(2023, 6, 1)],
            'contributions': [1000.0, 500.0]
        })

        result = calculate_investment_metrics(
            contributions_local_df=contrib_df,
            current_value_local=1600.0,
            current_value_date=datetime(2024, 1, 1)
        )

        assert isinstance(result, pd.DataFrame)
        assert 'local' in result.index
        assert 'total contributions' in result.columns

    @patch('modules.metrics.pd.read_sql')
    @patch('modules.metrics.get_db_connection')
    def test_update_investment_metrics(self, mock_get_db, mock_read_sql):
        """Test updating investment metrics for specific investment."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock investment details
        mock_cursor.fetchone.side_effect = [
            ('TEST', 'ZAR', 10.0, 100.0), # ticker, currency, units_held, unit_price
            (date(2023, 12, 31),),       # latest price date
            (date(2023, 1, 1), 100.0, 10.0) # initial_investment_date, initial_unit_price, number_of_units_held
        ]

        # Mock read_sql to return empty DataFrames with correct columns
        def mock_read_sql_fn(query, conn, params=None):
            if 'contributions' in query:
                return pd.DataFrame(columns=['date', 'contributions'])
            elif 'fees' in query:
                return pd.DataFrame(columns=['date', 'fees'])
            elif 'tax' in query:
                return pd.DataFrame(columns=['date', 'tax'])
            elif 'dividends' in query:
                return pd.DataFrame(columns=['date', 'dividends'])
            elif 'inflation' in query:
                return pd.DataFrame(columns=['date', 'inflation_rate'])
            return pd.DataFrame()

        mock_read_sql.side_effect = mock_read_sql_fn

        update_investment_metrics(1, 'test_db')

        # Verify database operations were called
        assert mock_cursor.execute.called
        assert mock_connection.commit.called

    @patch('modules.metrics.get_db_connection')
    def test_recalculate_investment_metrics_history(self, mock_get_db):
        """Test recalculating metrics history for all investments."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock investment IDs
        mock_cursor.fetchall.return_value = [(1,), (2,)]

        recalculate_investment_metrics_history('test_db')

        # Verify database operations were called
        assert mock_cursor.execute.called

    @patch('modules.metrics.get_db_connection')
    def test_get_investment_metrics_data_empty(self, mock_get_db):
        """Test getting metrics data when no data exists."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock empty result
        mock_cursor.fetchall.return_value = []

        result = get_investment_metrics_data('test_db')

        assert 'portfolio_performance_return' in result
        assert 'rolling_returns' in result
        assert len(result['portfolio_performance_return']) == 0

    @patch('modules.metrics.get_db_connection')
    def test_get_investment_metrics_by_name_data(self, mock_get_db):
        """Test getting metrics for specific investment by name."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock investment ID lookup
        mock_cursor.fetchone.side_effect = [
            (1,),  # first fetchone: investment ID
        ]
        # Mock the metrics rows returned by SELECT *
        mock_cursor.fetchall.return_value = [
            (1, date(2023, 1, 1), 0.1, 0.2)
        ]

        mock_cursor.description = [('id',), ('metrics_date',), ('local_cagr',), ('local_irr',)]

        result = get_investment_metrics_by_name_data('test_db', 'Test Investment')

        assert isinstance(result, dict)
        assert len(result) > 0
        # Prefixed DB columns (local_cagr / local_irr) are normalised to plain
        # names and returned as percentages in key_metrics and the trends.
        assert result['key_metrics']['cagr'] == 10.0  # 0.1 * 100
        assert result['key_metrics']['irr'] == 20.0   # 0.2 * 100
        assert result['cagr_trend'][0]['value'] == 10.0
        assert result['irr_trend'][0]['value'] == 20.0
