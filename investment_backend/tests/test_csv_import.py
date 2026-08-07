"""
Tests for csv_import.py module.
"""

import pytest
import pandas as pd
import tempfile
import os
from unittest.mock import patch, MagicMock
from io import BytesIO

from modules.csv_import import (
    import_unit_prices_csv, import_csv_data, import_mixed_csv_data, import_inflation_csv_data
)


class TestUnitPricesImport:
    """Test unit prices CSV import functionality."""

    @patch('modules.csv_import.get_db_connection')
    def test_import_unit_prices_csv_success(self, mock_get_db):
        """Test successful unit prices import."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock investment lookup
        mock_cursor.fetchone.return_value = (1,)

        # Create temporary CSV file
        csv_content = "date,unit_price\n2023-01-01,100.50\n2023-01-02,101.25\n"
        csv_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        csv_file.write(csv_content)
        csv_file.close()

        try:
            import_unit_prices_csv(csv_file.name, "Test Investment")

            # Verify database operations
            assert mock_cursor.execute.called
            mock_connection.commit.assert_called_once()

        finally:
            os.unlink(csv_file.name)

    @patch('modules.csv_import.get_db_connection')
    @patch('modules.csv_import.pd.read_csv')
    def test_import_unit_prices_csv_investment_not_found(self, mock_read_csv, mock_get_db):
        """Test import when investment is not found."""
        # Mock CSV reading
        mock_df = pd.DataFrame({
            'date': ['2023-01-01'],
            'unit_price': [100.0]
        })
        mock_read_csv.return_value = mock_df

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock investment lookup failure
        mock_cursor.fetchone.return_value = None

        with pytest.raises(ValueError, match="Investment 'NonExistent' not found"):
            import_unit_prices_csv("dummy.csv", "NonExistent")


class TestCSVDataImport:
    """Test general CSV data import functionality."""

    @patch('modules.csv_import.get_db_connection')
    def test_import_csv_data_transactions(self, mock_get_db):
        """Test importing transaction data."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock investment lookup
        mock_cursor.fetchone.return_value = (1,)

        # Create temporary CSV file
        csv_content = "date,type,amount,number_of_units\n2023-01-01,buy,1000.0,10\n"
        csv_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        csv_file.write(csv_content)
        csv_file.close()

        try:
            import_csv_data(csv_file.name, "transactions", "Test Investment")

            # Verify database operations
            assert mock_cursor.execute.called
            mock_connection.commit.assert_called_once()

        finally:
            os.unlink(csv_file.name)

    @patch('modules.csv_import.get_db_connection')
    def test_import_csv_data_dividends(self, mock_get_db):
        """Test importing dividend data."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock investment lookup
        mock_cursor.fetchone.return_value = (1,)

        # Create temporary CSV file
        csv_content = "date,dividend_amount\n2023-01-01,50.0\n"
        csv_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        csv_file.write(csv_content)
        csv_file.close()

        try:
            import_csv_data(csv_file.name, "dividends", "Test Investment")

            # Verify database operations
            assert mock_cursor.execute.called
            mock_connection.commit.assert_called_once()

        finally:
            os.unlink(csv_file.name)


class TestMixedDataImport:
    """Test mixed data import functionality."""

    @patch('modules.csv_import.get_db_connection')
    def test_import_mixed_csv_data(self, mock_get_db):
        """Test importing mixed data types."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock investment lookup
        mock_cursor.fetchone.return_value = (1,)

        # Create temporary CSV file with mixed data
        csv_content = "date,type,amount\n2023-01-01,buy,1000.0\n2023-02-01,dividend,25.0\n"
        csv_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        csv_file.write(csv_content)
        csv_file.close()

        try:
            import_mixed_csv_data(csv_file.name, "Test Investment")

            # Verify multiple database operations were called
            assert mock_cursor.execute.called
            mock_connection.commit.assert_called_once()

        finally:
            os.unlink(csv_file.name)


class TestInflationImport:
    """Test inflation data import functionality."""

    @patch('modules.csv_import.get_db_connection')
    def test_import_inflation_csv_data(self, mock_get_db):
        """Test importing inflation data."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Create temporary CSV file
        csv_content = "year,inflation_rate,country\n2023,5.2,South Africa\n2024,4.8,South Africa\n"
        csv_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        csv_file.write(csv_content)
        csv_file.close()

        try:
            import_inflation_csv_data(csv_file.name)

            # Verify database operations
            assert mock_cursor.execute.called
            mock_connection.commit.assert_called_once()

        finally:
            os.unlink(csv_file.name)


class TestImportErrorHandling:
    """Test error handling in import functions."""

    def test_import_unit_prices_invalid_csv(self):
        """Test import with invalid CSV format."""
        # Create temporary CSV file with invalid format
        csv_content = "invalid,csv,format\n2023-01-01\n"
        csv_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        csv_file.write(csv_content)
        csv_file.close()

        try:
            with pytest.raises(Exception):  # Should raise some parsing error
                import_unit_prices_csv(csv_file.name, "Test Investment")
        finally:
            os.unlink(csv_file.name)

    @patch('modules.csv_import.get_db_connection')
    def test_import_csv_invalid_data_type(self, mock_get_db):
        """Test import with invalid data type."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_get_db.return_value.__enter__.return_value = (mock_connection, mock_cursor)

        # Mock investment lookup
        mock_cursor.fetchone.return_value = (1,)

        # Create temporary CSV file
        csv_content = "date,invalid_column\n2023-01-01,test\n"
        csv_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        csv_file.write(csv_content)
        csv_file.close()

        try:
            # Should handle gracefully or raise appropriate error
            import_csv_data(csv_file.name, "invalid_type", "Test Investment")
            # If it doesn't raise, that's also acceptable

        finally:
            os.unlink(csv_file.name)
