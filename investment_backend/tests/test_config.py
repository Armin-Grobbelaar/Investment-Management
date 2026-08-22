"""
Tests for the configuration-table helpers in modules/database.py.
"""

import pytest
from unittest.mock import patch, MagicMock

from modules.database import (
    get_config_value,
    get_all_config,
    invalidate_config_cache,
)

@pytest.fixture(autouse=True)
def clear_config_cache():
    """Ensure a clean config cache between tests."""
    invalidate_config_cache()
    yield
    invalidate_config_cache()

class TestGetConfigValue:
    @patch("modules.database.get_db_connection")
    def test_returns_value_from_table(self, mock_get_db):
        """A known key returns its stored value."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        mock_cursor.fetchone.return_value = ("0.40",)

        assert get_config_value("cgt_inclusion_rate") == "0.40"

    @patch("modules.database.get_db_connection")
    def test_missing_key_returns_default(self, mock_get_db):
        """A key not present falls back to the provided default."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        mock_cursor.fetchone.return_value = None

        assert get_config_value("cgt_marginal_tax_rate", "0.45") == "0.45"

    @patch("modules.database.get_db_connection")
    def test_db_error_returns_default(self, mock_get_db):
        """DB errors must not crash config reads."""
        mock_get_db.return_value.__enter__.side_effect = Exception("table missing")

        assert get_config_value("base_currency", "ZAR") == "ZAR"

class TestGetAllConfig:
    @patch("modules.database.get_db_connection")
    def test_returns_full_dict(self, mock_get_db):
        """get_all_config returns a mapping of key -> value."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        mock_cursor.fetchall.return_value = [
            ("base_currency", "ZAR"),
            ("cgt_inclusion_rate", "0.40"),
        ]

        result = get_all_config("test_db")

        assert result["base_currency"] == "ZAR"
        assert result["cgt_inclusion_rate"] == "0.40"

    @patch("modules.database.get_db_connection")
    def test_returns_empty_on_error(self, mock_get_db):
        """DB errors must not raise — return an empty dict."""
        mock_get_db.return_value.__enter__.side_effect = Exception("boom")

        assert get_all_config("test_db") == {}

class TestConfigCaching:
    @patch("modules.database.get_db_connection")
    def test_value_cached_between_calls(self, mock_get_db):
        """Repeated reads use the in-process cache, not new DB calls."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        mock_cursor.fetchone.return_value = ("ZAR",)

        assert get_config_value("base_currency", "USD") == "ZAR"
        assert get_config_value("base_currency", "USD") == "ZAR"
        assert get_config_value("base_currency", "USD") == "ZAR"
        assert mock_get_db.call_count == 1

    @patch("modules.database.get_db_connection")
    def test_invalidate_cache_forces_refresh(self, mock_get_db):
        """invalidate_config_cache clears the cache so the DB is re-read."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        mock_cursor.fetchone.return_value = ("ZAR",)

        assert get_config_value("base_currency") == "ZAR"

        mock_cursor.fetchone.return_value = ("USD",)
        invalidate_config_cache()

        assert get_config_value("base_currency") == "USD"
        assert mock_get_db.call_count == 2
