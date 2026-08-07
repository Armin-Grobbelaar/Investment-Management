"""
Tests for api.py module.
"""

import pytest
import json
import pandas as pd
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from modules.api import (
    get_dashboard_data, get_investment_timeseries_data, get_investment_summary_response,
    add_user_api, get_all_investment_values_response, get_investment_values_filtered,
    add_investment_api, import_unit_prices_api, import_investment_data_api,
    invalidate_cache_api, get_investment_names_api, get_investment_predictions_api,
    health_check_api, get_investment_metrics_api, get_investment_metrics_by_name_api,
    generate_pdf_report_api, refresh_data_api, _get_cache_key, _get_cached_data, _set_cache_data,
    AddInvestmentRequest
)


class TestCacheFunctions:
    """Test caching functionality."""

    def test_get_cache_key(self):
        """Test cache key generation."""
        key1 = _get_cache_key("test_endpoint")
        assert key1 == "test_endpoint"

        key2 = _get_cache_key("test_endpoint", {"param": "value"})
        assert "test_endpoint" in key2
        assert "param" in key2

    def test_cache_operations(self):
        """Test basic cache operations."""
        # Clear any existing cache
        global _cache_data, _cache_expiry
        _cache_data = {}
        _cache_expiry = {}

        # Test setting and getting cache
        test_key = "test_key"
        test_data = {"test": "data"}

        _set_cache_data(test_key, test_data)
        cached_data = _get_cached_data(test_key)

        assert cached_data == test_data


class TestDashboardData:
    """Test dashboard data functionality."""

    @patch('modules.api.get_investment_summary_display')
    @patch('modules.api.get_portfolio_total_value')
    @patch('modules.api.get_currencies_in_portfolio')
    @patch('modules.api.get_investment_types_in_portfolio')
    def test_get_dashboard_data_success(self, mock_types, mock_currencies, mock_totals, mock_summary):
        """Test successful dashboard data retrieval."""
        # Mock the data
        mock_summary.return_value = pd.DataFrame()
        mock_totals.return_value = {"total_value": 1000.0}
        mock_currencies.return_value = ["ZAR", "USD"]
        mock_types.return_value = ["Stocks", "Bonds"]

        result = get_dashboard_data("test_db", "ZAR")


        # Should return a Response object
        assert hasattr(result, 'body')
        assert result.status_code == 200

        # Parse the JSON response
        response_data = json.loads(result.body.decode())
        assert "investment_summary" in response_data
        assert "portfolio_totals" in response_data
        assert "currencies_in_portfolio" in response_data
        assert "types_in_portfolio" in response_data


class TestInvestmentOperations:
    """Test investment-related API operations."""

    @patch('modules.api.get_investment_names_list')
    def test_get_investment_names_api(self, mock_get_names):
        """Test getting investment names."""
        mock_get_names.return_value = ["Investment A (TICKER)", "Investment B (TICKER)"]

        result = get_investment_names_api()

        assert "investment_names" in result
        assert len(result["investment_names"]) == 2

    @patch('modules.api.add_investment')
    @patch('modules.database.create_connection')
    def test_add_investment_api_success(self, mock_create_conn, mock_add_inv):
        """Test successful investment addition."""
        mock_add_inv.return_value = 123

        request_data = {
            "institution_name": "Test Bank",
            "initial_investment_date": "2023-01-01",
            "investment_type": "Stocks",
            "investment_name": "Test Investment",
            "investment_ticker": "TEST",
            "unit_currency": "ZAR",
            "initial_unit_price": 100.0,
            "unit_price": 110.0,
            "number_of_units_held": 10.0,
            "total_dividends_received": 0.0,
            "total_tax_paid": 0.0,
            "total_fees_paid": 0.0,
            "investment_fee": 0.0,
            "investment_status": "Active"
        }

        request_obj = AddInvestmentRequest(**request_data)
        result = add_investment_api("test_db", request_obj)

        assert "message" in result
        assert "investment_id" in result
        assert result["investment_id"] == 123


class TestImportOperations:
    """Test data import operations."""

    @patch('modules.api.import_unit_prices_csv')
    def test_import_unit_prices_api(self, mock_import):
        """Test unit prices import."""
        test_file_content = b"date,unit_price\n2023-01-01,100.50\n"

        result = import_unit_prices_api(test_file_content, "Test Investment")

        assert "message" in result
        assert "investment_name" in result

    @patch('modules.api.import_csv_data')
    def test_import_investment_data_api(self, mock_import):
        """Test investment data import."""
        test_file_content = b"date,type,amount\n2023-01-01,buy,1000.0\n"

        result = import_investment_data_api("transactions", test_file_content, "Test Investment")

        assert "message" in result
        assert "data_type" in result
        assert result["data_type"] == "transactions"


class TestMetricsOperations:
    """Test metrics-related API operations."""

    @patch('modules.api.get_investment_metrics_data')
    def test_get_investment_metrics_api(self, mock_get_metrics):
        """Test getting investment metrics."""
        mock_get_metrics.return_value = {
            "portfolio_performance_return": [],
            "rolling_returns": {"one_year": [], "three_year": [], "five_year": []},
            "conclusion": "Test conclusion"
        }

        result = get_investment_metrics_api("test_db", "ZAR", "portfolio")

        # Should return a Response object
        assert hasattr(result, 'body')
        response_data = json.loads(result.body.decode())
        assert "portfolio_performance_return" in response_data
        assert "conclusion" in response_data

    @patch('modules.api.get_investment_metrics_by_name_data')
    def test_get_investment_metrics_by_name_api(self, mock_get_metrics):
        """Test getting metrics for specific investment."""
        mock_get_metrics.return_value = {"cagr": 0.1, "irr": 0.08}

        result = get_investment_metrics_by_name_api("test_db", "Test Investment")

        # Should return a Response object
        assert hasattr(result, 'body')
        response_data = json.loads(result.body.decode())
        assert "cagr" in response_data


class TestUtilityOperations:
    """Test utility API operations."""

    def test_health_check_api(self):
        """Test health check endpoint."""
        result = health_check_api()

        assert "status" in result
        assert "timestamp" in result
        assert "cache_entries" in result
        assert "uptime_seconds" in result
        assert result["status"] == "healthy"

    def test_invalidate_cache_api(self):
        """Test cache invalidation."""
        result = invalidate_cache_api("test_db")

        assert "message" in result
        assert "timestamp" in result
        assert "Cache invalidated" in result["message"]
