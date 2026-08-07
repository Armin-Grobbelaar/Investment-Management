"""
Tests for predictions.py module.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date
from unittest.mock import patch, MagicMock

from modules.predictions import (
    _to_serializable,
    store_prediction_data,
    get_recent_predictions
)

class TestPredictions:
    """Test machine learning prediction helpers and storage."""

    def test_to_serializable(self):
        """Test converting numpy/pandas types to standard Python types."""
        # Test numpy types
        assert _to_serializable(np.int64(42)) == 42
        assert _to_serializable(np.float64(3.14)) == 3.14
        assert bool(_to_serializable(np.bool_(True))) is True
        
        # Test arrays
        arr = np.array([1, 2, 3])
        assert _to_serializable(arr) == [1, 2, 3]
        
        # Test fallback
        assert _to_serializable("hello") == "hello"

    @patch('modules.predictions.get_db_connection')
    def test_store_prediction_data(self, mock_get_db):
        """Test storing prediction results in database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        
        mock_cursor.fetchone.return_value = (101,)
        
        test_results = {
            "Prophet": {
                "prediction_horizon_days": 30,
                "confidence_level": 0.95,
                "target": "MSFT",
                "predictions": [{"date": "2023-01-01", "value": 150.0}]
            }
        }
        
        pred_id = store_prediction_data(test_results, "investment_id=1", "test_db")
        
        assert pred_id == 101
        assert mock_cursor.execute.call_count == 1
        
        # Check execute arguments for the insert
        args, kwargs = mock_cursor.execute.call_args_list[0]
        query = args[0]
        params = args[1]
        assert "INSERT INTO predictions" in query
        assert params[1] == "Prophet" # model_name
        assert params[2] == "investment_id=1" # scope
        assert params[3] == 30 # horizon

    @patch('modules.predictions.get_db_connection')
    def test_get_recent_predictions(self, mock_get_db):
        """Test retrieving recent predictions."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.__enter__.return_value = (mock_conn, mock_cursor)
        
        mock_cursor.fetchall.return_value = [
            (
                1, # id
                date(2023, 1, 1), # prediction_date
                "Prophet", # model_name
                "investment_id=1", # scope
                30, # horizon
                0.95, # confidence
                '{"Prophet": {"target": "MSFT"}}', # prediction_data
                '{}', # historical_context
                None, # accuracy_score
                "Medium", # risk_level
                '{}', # model_metadata
                datetime.now() # created_at
            )
        ]
        
        results = get_recent_predictions(limit=5, database_name="test_db")
        
        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["model_name"] == "Prophet"
        assert results[0]["prediction_data"]["Prophet"]["target"] == "MSFT"
