"""
Tests for database.py module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import psycopg2

from modules.database import (
    DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DEFAULT_DB,
    get_db_connection, create_connection, add_user
)

class TestDatabaseConnection:
    """Test database connection functionality."""

    @patch('modules.database.psycopg2.connect')
    def test_get_db_connection(self, mock_connect):
        """Test database connection creation."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        with get_db_connection('test_db') as (conn, cursor):
            assert conn == mock_connection
            assert cursor == mock_cursor

        mock_connection.close.assert_called_once()

    @patch('modules.database.psycopg2.connect')
    def test_create_connection_success(self, mock_connect):
        """Test successful database connection creation."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        from modules.database import create_connection
        conn, cursor = create_connection('test_db')

        assert conn == mock_connection
        assert cursor == mock_cursor

    @patch('modules.database.psycopg2.connect')
    def test_add_user_success(self, mock_connect):
        """Test successful user addition."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        mock_cursor.fetchone.return_value = (42,)

        from modules.database import add_user
        result = add_user('testuser', 'test@example.com', 'password123', 'Test User')

        assert result['id'] == 42
        assert result['username'] == 'testuser'
        assert result['token'] is not None

class TestDatabaseConstants:
    """Test database constants are properly configured."""

    def test_database_constants_exist(self):
        """Test that database constants are defined."""
        assert DEFAULT_DB is not None
        assert isinstance(DEFAULT_DB, str)

    def test_connection_parameters_exist(self):
        """Test connection parameters are defined."""
        assert DB_HOST is not None
        assert DB_USER is not None
        assert DB_PASSWORD is not None
        assert DB_PORT is not None
