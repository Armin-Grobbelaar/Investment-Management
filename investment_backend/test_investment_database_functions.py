import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

# Import your function
from  investment_database_functions import add_investment


@pytest.fixture
def mock_db(monkeypatch):
    # Mock global cursor + connection
    cursor = MagicMock()
    connection = MagicMock()
    monkeypatch.setattr("your_module.investment_database_cursor", cursor)
    monkeypatch.setattr("your_module.investment_database_connection", connection)
    return cursor, connection


@pytest.fixture
def mock_foreign_currency(monkeypatch):
    df = pd.DataFrame({"Symbol": ["USD", "ZAR"], "Currency": ["USD", "ZAR"]})
    monkeypatch.setattr("your_module.foreign_currency", df)
    monkeypatch.setattr("your_module.native_currency", "ZAR")
    return df


def test_investment_already_exists(mock_db, mock_foreign_currency):
    cursor, _ = mock_db
    # Simulate DB returning an existing investment
    cursor.fetchall.return_value = [(1, "TestBank", "Apple", "USD", "Equity")]

    result = add_investment(
        "testdb", "TestBank", "2023-01-01", "Equity", "Apple", "AAPL",
        "USD", 100.0, 120.0, 10, 0, 0, 0, 0, "Active"
    )

    cursor.execute.assert_any_call("SELECT id, institution_name, investment_name, unit_currency, investment_type FROM investments")
    # Function should return early
    assert result is None


@patch("investment_database_functions.yf.Ticker")
@patch("investment_database_functions.create_engine")
def test_add_new_investment(mock_engine, mock_ticker, mock_db, mock_foreign_currency):
    cursor, connection = mock_db
    cursor.fetchall.return_value = []  # No existing investments

    # Mock Ticker history
    mock_ticker.return_value.history.return_value = pd.DataFrame({
        "Date": pd.date_range("2023-01-01", periods=3),
        "Close": [100, 101, 102],
    })

    # Mock insert returning an ID
    cursor.fetchone.return_value = [42]

    add_investment(
        "testdb", "TestBank", "2023-01-01", "Equity", "Apple", "AAPL",
        "USD", 100.0, 120.0, 10, 0, 0, 0, 0, "Active"
    )

    # Check DB insert was called
    assert cursor.execute.call_count > 0
    connection.commit.assert_called()
@pytest.fixture
def mock_db(monkeypatch):
    # Mock global cursor + connection
    cursor = MagicMock()
    connection = MagicMock()
    monkeypatch.setattr("your_module.investment_database_cursor", cursor)
    monkeypatch.setattr("your_module.investment_database_connection", connection)
    return cursor, connection


@pytest.fixture
def mock_foreign_currency(monkeypatch):
    df = pd.DataFrame({"Symbol": ["USD", "ZAR"], "Currency": ["USD", "ZAR"]})
    monkeypatch.setattr("your_module.foreign_currency", df)
    monkeypatch.setattr("your_module.native_currency", "ZAR")
    return df


def test_investment_already_exists(mock_db, mock_foreign_currency):
    cursor, _ = mock_db
    # Simulate DB returning an existing investment
    cursor.fetchall.return_value = [(1, "TestBank", "Apple", "USD", "Equity")]

    result = add_investment(
        "testdb", "TestBank", "2023-01-01", "Equity", "Apple", "AAPL",
        "USD", 100.0, 120.0, 10, 0, 0, 0, 0, "Active"
    )

    cursor.execute.assert_any_call("SELECT id, institution_name, investment_name, unit_currency, investment_type FROM investments")
    # Function should return early
    assert result is None


@patch("investment_database_functions.yf.Ticker")
@patch("investment_database_functions.create_engine")
def test_add_new_investment(mock_engine, mock_ticker, mock_db, mock_foreign_currency):
    cursor, connection = mock_db
    cursor.fetchall.return_value = []  # No existing investments

    # Mock Ticker history
    mock_ticker.return_value.history.return_value = pd.DataFrame({
        "Date": pd.date_range("2023-01-01", periods=3),
        "Close": [100, 101, 102],
    })

    # Mock insert returning an ID
    cursor.fetchone.return_value = [42]

    add_investment(
        "testdb", "TestBank", "2023-01-01", "Equity", "Apple", "AAPL",
        "USD", 100.0, 120.0, 10, 0, 0, 0, 0, "Active"
    )

    # Check DB insert was called
    assert cursor.execute.call_count > 0
    connection.commit.assert_called()

@patch("investment_database_functions.yf.Ticker")
@patch("investment_database_functions.create_engine")
def test_add_investment_with_forex(mock_engine, mock_ticker, mock_db, monkeypatch):
    cursor, connection = mock_db

    # Pretend no investments exist yet
    cursor.fetchall.return_value = []

    # Mock global variables
    monkeypatch.setattr("your_module.native_currency", "ZAR")
    monkeypatch.setattr("your_module.foreign_currency", 
                        pd.DataFrame({"Symbol": ["USD", "ZAR"], "Currency": ["USD", "ZAR"]}))

    # Mock Ticker history
    mock_ticker.return_value.history.return_value = pd.DataFrame({
        "Date": pd.date_range("2023-01-01", periods=3),
        "Close": [100, 101, 102],
    })

    # Mock first insert returning investment ID
    cursor.fetchone.side_effect = [
        [42],  # first investment insert
        [99]   # forex insert
    ]

    add_investment(
        "testdb", "TestBank", "2023-01-01", "Equity", "Apple", "AAPL",
        "USD", 100.0, 120.0, 10, 0, 0, 0, 0, "Active"
    )

    # It should call two inserts (normal + forex)
    executed_queries = [args[0] for args, _ in cursor.execute.call_args_list]
    assert any("INSERT INTO investments" in q for q in executed_queries)
    assert any("INSERT INTO unit_prices" in q for q in executed_queries)

    # Make sure commits were made for both inserts
    assert connection.commit.call_count >= 2

    # Verify forex ticker was passed to yfinance
    forex_ticker_call = mock_ticker.call_args_list[-1][0][0]
    assert forex_ticker_call == "USDZAR=X"


@pytest.fixture
def mock_db(monkeypatch):
    cursor = MagicMock()
    connection = MagicMock()
    monkeypatch.setattr("investment_database_functions.investment_database_cursor", cursor)
    monkeypatch.setattr("investment_database_functions.investment_database_connection", connection)
    return cursor, connection


@pytest.fixture
def mock_foreign_currency(monkeypatch):
    df = pd.DataFrame({"Symbol": ["USD", "ZAR"], "Currency": ["USD", "ZAR"]})
    monkeypatch.setattr("investment_database_functions.foreign_currency", df)
    monkeypatch.setattr("investment_database_functions.native_currency", "ZAR")
    return df


def test_investment_already_exists(mock_db, mock_foreign_currency):
    cursor, _ = mock_db
    cursor.fetchall.return_value = [(1, "TestBank", "Apple", "USD", "Equity")]

    result = add_investment(
        "testdb", "TestBank", "2023-01-01", "Equity", "Apple", "AAPL",
        "USD", 100.0, 120.0, 10, 0, 0, 0, 0, "Active"
    )

    assert result is None
    cursor.execute.assert_any_call("SELECT id, institution_name, investment_name, unit_currency, investment_type FROM investments")