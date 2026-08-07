"""
Tests for startup.py module.
"""

import pytest
from unittest.mock import patch, MagicMock

from modules.startup_utils import (
    check_database_connection, check_database_exists, create_database_if_not_exists,
    check_system_health, display_startup_summary
)


class TestDatabaseConnectionChecks:
    """Test database connection and existence checks."""

    @patch('modules.startup_utils.psycopg2.connect')
    def test_check_database_connection_success(self, mock_connect):
        """Test successful database connection check."""
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        result = check_database_connection()

        assert result is True
        mock_connection.close.assert_called_once()

    @patch('modules.startup_utils.psycopg2.connect')
    def test_check_database_connection_failure(self, mock_connect):
        """Test database connection failure."""
        mock_connect.side_effect = Exception("Connection failed")

        result = check_database_connection()

        assert result is False

    @patch('modules.startup_utils.psycopg2.connect')
    def test_check_database_exists_true(self, mock_connect):
        """Test checking if database exists (exists)."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)  # Database exists
        mock_connect.return_value = mock_connection

        result = check_database_exists('test_db')

        assert result is True
        mock_connection.close.assert_called_once()

    @patch('modules.startup_utils.psycopg2.connect')
    def test_check_database_exists_false(self, mock_connect):
        """Test checking if database exists (doesn't exist)."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # Database doesn't exist
        mock_connect.return_value = mock_connection

        result = check_database_exists('test_db')

        assert result is False
        mock_connection.close.assert_called_once()

    @patch('modules.startup_utils.check_database_exists')
    @patch('modules.startup_utils.psycopg2.connect')
    def test_create_database_if_not_exists_create(self, mock_connect, mock_exists):
        """Test creating database when it doesn't exist."""
        mock_exists.return_value = False

        mock_connection = MagicMock()
        mock_connection.autocommit = True
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        result = create_database_if_not_exists('test_db')

        assert result is True
        mock_cursor.execute.assert_called_with("CREATE DATABASE test_db")


class TestSystemHealthChecks:
    """Test system health checking functionality."""

    @patch('modules.startup_utils.psycopg2.connect')
    def test_check_system_health_success(self, mock_connect):
        """Test successful system health check."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor

        # Mock investment count
        mock_cursor.fetchone.side_effect = [(5,), (1,)]  # 5 investments, 1 portfolio

        mock_connect.return_value = mock_connection

        result = check_system_health()

        assert result is True
        mock_connection.close.assert_called_once()

    @patch('modules.startup_utils.psycopg2.connect')
    def test_check_system_health_no_portfolio(self, mock_connect):
        """Test system health check when no portfolio exists."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor

        # Mock investment count (no portfolio)
        mock_cursor.fetchone.side_effect = [(5,), (0,)]  # 5 investments, 0 portfolios

        mock_connect.return_value = mock_connection

        result = check_system_health()

        assert result is False  # Should fail because no portfolio

    @patch('modules.startup_utils.psycopg2.connect')
    def test_check_system_health_connection_error(self, mock_connect):
        """Test system health check when database connection fails."""
        mock_connect.side_effect = Exception("Connection failed")

        result = check_system_health()

        assert result is False


class TestStartupSummary:
    """Test startup summary display functionality."""

    @patch('builtins.print')
    def test_display_startup_summary(self, mock_print):
        """Test displaying startup summary."""
        display_startup_summary()

        # Verify that print was called multiple times
        assert mock_print.called
        assert mock_print.call_count > 5  # Should print multiple lines

        # Check that key messages are printed
        call_args_list = [call[0][0] for call in mock_print.call_args_list if call[0] and len(call[0]) > 0]
        summary_text = ' '.join(call_args_list)

        assert "STARTUP COMPLETE" in summary_text
        assert "investment tracking system is ready" in summary_text
        assert "Next Steps:" in summary_text
