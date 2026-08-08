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
