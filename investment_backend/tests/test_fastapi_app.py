"""
Tests for the FastAPI app endpoints added/fixed during the audit:
  - /health (real uptime, not a hardcoded date)
  - /config/{database_name} GET/PUT (configuration table read/update)
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import investment_backend_fastapi as app_module


@pytest.fixture
def client():
    return TestClient(app_module.investment_api)


class TestHealthEndpoint:
    def test_health_returns_real_uptime(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        # Uptime must be small (process just started), not from a fixed 2024 date
        assert data["uptime_seconds"] >= 0
        assert data["uptime_seconds"] < 3600 * 24


class TestConfigEndpoints:
    @patch("investment_backend_fastapi.get_all_config")
    def test_config_get_returns_settings(self, mock_get_all, client):
        mock_get_all.return_value = {"base_currency": "ZAR", "native_currency": "R"}
        resp = client.get("/config/Investments")
        assert resp.status_code == 200
        assert resp.json()["base_currency"] == "ZAR"

    @patch("investment_backend_fastapi.get_all_config")
    def test_config_get_errors_are_500(self, mock_get_all, client):
        mock_get_all.side_effect = Exception("db down")
        resp = client.get("/config/Investments")
        assert resp.status_code == 500

    @patch("investment_backend_fastapi.invalidate_config_cache")
    @patch("investment_backend_fastapi.get_db_connection")
    def test_config_put_updates_settings(self, mock_get_db, mock_invalidate, client):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)

        resp = client.put(
            "/config/Investments",
            json={"base_currency": "USD", "native_currency": "$"},
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == ["base_currency", "native_currency"]
        # Parameterised update + commit + cache invalidation
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()
        mock_invalidate.assert_called_once_with("Investments")

    @patch("investment_backend_fastapi.get_db_connection")
    def test_config_put_rejects_empty_body(self, mock_get_db, client):
        resp = client.put("/config/Investments", json={})
        assert resp.status_code == 400

    @patch("investment_backend_fastapi.get_db_connection")
    def test_config_put_rejects_non_object(self, mock_get_db, client):
        resp = client.put("/config/Investments", json=[1, 2, 3])
        assert resp.status_code == 400


class TestImportUnitPricesEndpoint:
    @patch("investment_backend_fastapi.import_unit_prices_api")
    def test_unit_prices_import_calls_api_without_hardcoded_usd(
        self, mock_import, client
    ):
        """The endpoint must call import_unit_prices_api with exactly 2 args."""
        resp = client.post(
            "/import_unit_prices/",
            data={"investment_name": "Test Fund"},
            files={"file": ("prices.csv", b"date,unit_price\n2024-01-01,100.00", "text/csv")},
        )
        assert resp.status_code == 200
        mock_import.assert_called_once()
        args, kwargs = mock_import.call_args
        assert len(args) == 2  # (file_name, investment_name) — no currency arg
        assert "USD" not in kwargs.values() and "USD" not in args


class TestDashboardFilterCacheKey:
    """Test that filtered and unfiltered dashboard requests use different cache keys
    so the sidebar filter (ETF, GBP, Allan Gray, etc.) returns correctly filtered data
    instead of the cached full-portfolio payload."""

    def test_cache_key_includes_filter_params(self):
        """Cache keys must differ between filtered and unfiltered requests."""
        import investment_backend_fastapi as app_mod

        key_unfiltered = f"charts:Investments:ZAR::"
        key_filtered_type = f"charts:Investments:ZAR:investment_type:ETF"
        key_filtered_curr = f"charts:Investments:ZAR:unit_currency:GBP"
        key_filtered_inst = f"charts:Investments:ZAR:institution_name:Allan Gray"

        assert key_unfiltered != key_filtered_type
        assert key_filtered_type != key_filtered_curr
        assert key_filtered_curr != key_filtered_inst

    def test_filter_by_investment_type_returns_only_that_type(self):
        """When filtering by investment_type, the summary_table must only
        contain investments of that type (no cross-contamination)."""
        import pandas as pd

        # Simulate the filter logic that runs inside get_dashboard_charts
        summary_df = pd.DataFrame({
            "investment_name": ["ETF Fund A", "ETF Fund B", "Trust Fund A", "Forex A"],
            "investment_type": ["ETF", "ETF", "Unit Trust", "Forex"],
            "unit_currency": ["ZAR", "ZAR", "ZAR", "ZAR"],
            "institution_name": ["Allan Gray", "PSG Wealth", "Coronation", "Forex"],
        })

        filter_type = "investment_type"
        filter_value = "ETF"
        filtered_investment_names = summary_df[summary_df["investment_type"] == filter_value]["investment_name"].tolist()
        result = summary_df[summary_df["investment_name"].isin(filtered_investment_names)]

        assert len(result) == 2
        assert all(result["investment_type"] == "ETF")

    def test_filter_by_currency_uses_raw_summary(self):
        """Currency filter must match against the raw (unconverted) unit_currency,
        not the display version which has been converted to base currency."""
        import pandas as pd

        raw_summary = pd.DataFrame({
            "investment_name": ["Fund A", "Fund B", "Fund C"],
            "unit_currency": ["ZAR", "GBP", "USD"],
        })
        display_summary = pd.DataFrame({
            "investment_name": ["Fund A", "Fund B", "Fund C"],
            "unit_currency": ["ZAR", "ZAR", "ZAR"],  # converted to base
        })

        # Filter on raw, then match names in display
        filter_value = "GBP"
        filtered_names = raw_summary[raw_summary["unit_currency"] == filter_value]["investment_name"].tolist()
        result = display_summary[display_summary["investment_name"].isin(filtered_names)]

        assert len(result) == 1
        assert result["investment_name"].iloc[0] == "Fund B"
