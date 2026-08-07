"""
Shared pytest fixtures and configuration for investment management tests.
"""

import pytest
import pandas as pd
from datetime import datetime, date
from unittest.mock import MagicMock


@pytest.fixture
def sample_investment_data():
    """Sample investment data for testing."""
    return pd.DataFrame({
        'id': [1, 2, 3],
        'investment_name': ['Investment A', 'Investment B', 'Investment C'],
        'unit_currency': ['ZAR', 'USD', 'EUR'],
        'investment_type': ['Stocks', 'Bonds', 'ETFs'],
        'investment_value': [10000.0, 20000.0, 15000.0],
        'unit_price': [100.0, 200.0, 150.0],
        'total_units_held': [100.0, 100.0, 100.0],
        'initial_unit_price': [90.0, 180.0, 140.0],
        'initial_investment_date': [
            datetime(2022, 1, 1),
            datetime(2022, 6, 1),
            datetime(2023, 1, 1)
        ]
    })


@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing."""
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing."""
    return pd.DataFrame({
        'date': [
            datetime(2023, 1, 1),
            datetime(2023, 2, 1),
            datetime(2023, 3, 1)
        ],
        'transaction_type': ['Buy', 'Buy', 'Sell'],
        'transaction_amount': [1000.0, 500.0, -200.0],
        'number_of_units': [10.0, 5.0, -2.0]
    })


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing imports."""
    return """date,unit_price
2023-01-01,100.50
2023-01-02,101.25
2023-01-03,102.00"""


@pytest.fixture
def temp_csv_file(tmp_path, sample_csv_content):
    """Create a temporary CSV file for testing."""
    file_path = tmp_path / "test_data.csv"
    file_path.write_text(sample_csv_content)
    return str(file_path)


@pytest.fixture
def sample_metrics_data():
    """Sample investment metrics data."""
    return {
        'cagr': 0.12,  # 12%
        'irr': 0.15,   # 15%
        'total_return': 0.25,  # 25%
        'total_contributions': 10000.0,
        'total_fees': 100.0,
        'total_tax': 50.0,
        'number_of_contributions': 10,
        'investment_period': 2.0  # years
    }


@pytest.fixture
def mock_cache():
    """Mock cache for testing API functions."""
    # Import here to avoid circular imports
    from modules.api import _cache_data, _cache_expiry

    # Clear existing cache
    original_cache = _cache_data.copy()
    original_expiry = _cache_expiry.copy()

    _cache_data.clear()
    _cache_expiry.clear()

    yield _cache_data, _cache_expiry

    # Restore original cache
    _cache_data.clear()
    _cache_data.update(original_cache)
    _cache_expiry.clear()
    _cache_expiry.update(original_expiry)
