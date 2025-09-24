import pytest
from fastapi.testclient import TestClient
from investment_backend_fastapi import investment_api

client = TestClient(investment_api)


@pytest.fixture(autouse=True)
def mock_functions(monkeypatch):
    import pandas as pd
    monkeypatch.setattr("investment_database_functions.add_investment", lambda *a, **k: None)
    monkeypatch.setattr("investment_database_functions.create_connection", lambda db: None)
    monkeypatch.setattr("investment_database_functions.add_user", lambda u, s: None)
    monkeypatch.setattr("investment_database_functions.get_investment_summary", lambda db: pd.DataFrame([{"summary": "ok"}]))
    monkeypatch.setattr("investment_database_functions.get_all_investment_values", lambda db: pd.DataFrame([{"investment_name": "Apple", "value": 1200}]))


def test_add_user():
    payload = {"username": "John", "user_surname": "Doe"}
    response = client.post("/add_user", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "User successfully added"}


def test_add_investment():
    payload = {
        "database_name": "testdb",
        "institution_name": "TestBank",
        "initial_investment_date": "2023-01-01",
        "investment_type": "Equity",
        "investment_name": "Apple",
        "investment_ticker": "AAPL",
        "unit_currency": "USD",
        "initial_unit_price": 100.0,
        "unit_price": 120.0,
        "number_of_units_held": 10,
        "total_dividends_received": 0.0,
        "total_tax_paid": 0.0,
        "total_fees_paid": 0.0,
        "investment_fee": 0.0,
        "investment_status": "Active"
    }
    response = client.post("/add_investment/testdb", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "Investment added successfully"}


def test_get_investment_summary():
    response = client.get("/investment_summary/testdb")
    assert response.status_code == 200
    assert "ok" in response.text


def test_get_all_investment_values():
    response = client.get("/all_investment_values/testdb")
    assert response.status_code == 200
    assert "Apple" in response.text