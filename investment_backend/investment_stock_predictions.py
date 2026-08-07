
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

from investment_database_functions import get_investment_data, DEFAULT_DB
from modules.predictions import StockPredictor, store_prediction_data

def get_investment_predictions(database_name, scope="portfolio", models_to_run=None):
    """
    Generate investment predictions using available models.
    
    Args:
        database_name (str): Name of the database to use
        scope (str): Scope of prediction ('portfolio', 'individual', etc.)
        models_to_run (list): List of model names to run. If None, runs all.
    
    Returns:
        dict: formatted prediction results
    """
    if models_to_run is None:
        models_to_run = ['arima', 'lstm', 'xgboost', 'hybrid', 'gaussian_process', 'auto_arima']
        
    # 1. Fetch Historical Data
    # For portfolio scope, we aggregate value. For others, we might need filtering.
    # This is a simplified implementation focusing on Portfolio value for now as per previous context
    
    try:
        df = get_investment_data(base_currency="ZAR", database_name=database_name)
        
        if df.empty:
            return {"error": "No historical data available"}
            
        # Group by date to get portfolio total daily value
        # Assuming 'unit_price_date' and 'investment_value' columns exist based on previous file reads
        daily_data = df.groupby('unit_price_date')['investment_value'].sum().reset_index()
        daily_data.columns = ['date', 'close']
        daily_data['date'] = pd.to_datetime(daily_data['date'])
        daily_data = daily_data.sort_values('date')
        
        # Determine base currency (simplified)
        base_currency = "ZAR" 
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return {"error": str(e)}

    # 2. Initialize Predictor
    predictor = StockPredictor(scope=scope)
    
    # 3. Run Models
    predictions = {}
    
    # helper to format result
    def run_model_safely(model_func, key, name):
        if key in models_to_run:
            print(f"Running {name}...")
            result = model_func(daily_data)
            if result:
                predictions[key] = result
    
    run_model_safely(predictor.predict_arima, 'arima', 'ARIMA')
    run_model_safely(predictor.predict_lstm, 'lstm', 'LSTM')
    run_model_safely(predictor.predict_xgboost, 'xgboost', 'XGBoost')
    run_model_safely(predictor.predict_hybrid_arima_lstm, 'hybrid', 'Hybrid')
    run_model_safely(predictor.predict_gaussian_process, 'gaussian_process', 'Gaussian Process')
    run_model_safely(predictor.predict_auto_arima, 'auto_arima', 'Auto-ARIMA')

    # 4. Calculate Quant Metrics (New Feature)
    quant_metrics = predictor.calculate_quant_metrics(daily_data)
    
    # 5. Construct Response
    historical_response = {
        'dates': [d.strftime('%Y-%m-%d') for d in daily_data['date'].tolist()],
        'prices': daily_data['close'].tolist(),
        # Mocking values for high/low/volume if not available in aggregation
        'highs': daily_data['close'].tolist(), 
        'lows': daily_data['close'].tolist(),
        'volumes': [1000] * len(daily_data) 
    }
    
    response = {
        'scope': scope,
        'base_currency': base_currency,
        'historical_data': historical_response,
        'predictions': predictions,
        'quant_metrics': quant_metrics,
        'prediction_horizon_days': predictor.horizon_days,
        'confidence_level': 0.95,
        'timestamp': datetime.now().isoformat(),
        'models_available': len(predictions),
        'models_requested': len(models_to_run),
        'data_quality_score': 0.95 # Placeholder
    }
    
    # 6. Store in Database
    try:
        # Save each model's prediction individually to match the schema expectations if needed,
        # or simplified as a single record per run if store_prediction_data handles the dict.
        # Based on modules/predictions.py: store_prediction_data takes (prediction_results, scope, database_name)
        # and loops or stores meaningful data.
        
        prediction_id = store_prediction_data(predictions, scope, database_name)
        if prediction_id:
             response['prediction_id'] = prediction_id
             print(f"Successfully stored predictions to DB with ID: {prediction_id}")
    except Exception as e:
        print(f"Failed to store predictions: {e}")
        
    return response
