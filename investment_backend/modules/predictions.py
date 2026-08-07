import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from .database import get_db_connection, DEFAULT_DB
from .currency import NATIVE_CURRENCY, CURRENCY_SYMBOLS

# Configuration constants
PREDICTION_DAYS = 30  # Predict next 30 days
CONFIDENCE_LEVEL = 0.95  # 95% confidence intervals
TRAIN_RATIO = 0.8  # 80% training data

# --- Prediction Library Imports ---
# Check individual library availability
_LIBRARIES_STATUS = {
    'statsmodels': False,
    'tensorflow': False,
    'sklearn': False,
    'xgboost': False,
    'scipy': False
}

# Attempt imports and track availability

# Attempt imports and track availability
try:
    import statsmodels.api as sm
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.stattools import adfuller
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
    from scipy import stats
    _LIBRARIES_STATUS['statsmodels'] = True
    _LIBRARIES_STATUS['scipy'] = True
except ImportError:
    pass

try:
    # Deep Learning imports
    import tensorflow as tf
    # TF 2.16+ ships Keras 3 as a standalone package; support both APIs.
    try:
        from tensorflow.keras.models import Sequential, Model
        from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, Concatenate
        from tensorflow.keras.optimizers import Adam
    except (ImportError, AttributeError):
        # Keras 3 standalone (pip install keras)
        from keras.models import Sequential, Model
        from keras.layers import LSTM, Dense, Dropout, Input, Concatenate
        from keras.optimizers import Adam
    from sklearn.preprocessing import MinMaxScaler
    _LIBRARIES_STATUS['tensorflow'] = True
    _LIBRARIES_STATUS['sklearn'] = True
except ImportError:
    pass

try:
    # Machine Learning imports
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.svm import SVR
    import xgboost as xgb
    from sklearn.metrics import mean_squared_error
    from sklearn.preprocessing import StandardScaler
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel
    if not _LIBRARIES_STATUS['sklearn']:
        _LIBRARIES_STATUS['sklearn'] = True
    _LIBRARIES_STATUS['xgboost'] = True
except ImportError:
    pass

try:
    import pmdarima as pm
    _LIBRARIES_STATUS['pmdarima'] = True
except ImportError:
    _LIBRARIES_STATUS['pmdarima'] = False

try:
    import QuantLib as ql
    _LIBRARIES_STATUS['quantlib'] = True
except ImportError:
    _LIBRARIES_STATUS['quantlib'] = False

try:
    import pyfolio as pf
    _LIBRARIES_STATUS['pyfolio'] = True
except ImportError:
    _LIBRARIES_STATUS['pyfolio'] = False



# ---------------------------------------------------------------------------
# Helper: convert numpy / non-standard types so json.dumps() never fails
# ---------------------------------------------------------------------------
def _to_serializable(obj):
    """Recursively convert numpy scalars/arrays to plain Python types."""
    try:
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(v) for v in obj]
    return obj


# --- Prediction Database Functions ---

def store_prediction_data(prediction_results, scope, database_name=None):
    """Store prediction data from a model run in the database."""
    try:
        with get_db_connection(database_name) as (conn, cursor):
            # Get the first model to extract common metadata
            first_model_key = next(iter(prediction_results.keys()))
            first_model = prediction_results[first_model_key]

            # Prepare prediction record
            prediction_record = {
                'prediction_date': datetime.now().date(),
                'model_name': first_model_key,
                'scope': scope,
                'prediction_horizon_days': first_model.get('prediction_horizon_days', 30),
                'confidence_level': first_model.get('confidence_level', 0.95),
                'prediction_data': json.dumps(_to_serializable(prediction_results)),
                'historical_context': json.dumps({
                    'data_quality_score': prediction_results.get('data_quality_score', 0.85),
                    'models_available': prediction_results.get('models_available', len(prediction_results)),
                    'models_delivered': prediction_results.get('models_delivered', len(prediction_results))
                }),
                'accuracy_score': float(first_model.get('accuracy_score', 0.0)),
                'risk_level': float(first_model.get('risk_level', 0.0)),
                'model_metadata': json.dumps({
                    'library_status': prediction_results.get('library_status', {}),
                    'timestamp': prediction_results.get('timestamp', datetime.now().isoformat())
                })
            }

            # Insert prediction record
            cursor.execute("""
                INSERT INTO predictions (
                    prediction_date, model_name, scope, prediction_horizon_days,
                    confidence_level, prediction_data, historical_context,
                    accuracy_score, risk_level, model_metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                prediction_record['prediction_date'],
                prediction_record['model_name'],
                prediction_record['scope'],
                prediction_record['prediction_horizon_days'],
                prediction_record['confidence_level'],
                prediction_record['prediction_data'],
                prediction_record['historical_context'],
                prediction_record['accuracy_score'],
                prediction_record['risk_level'],
                prediction_record['model_metadata']
            ))

            prediction_id = cursor.fetchone()[0]
            conn.commit()
            print(f"Stored prediction data for {len(prediction_results)} models with ID {prediction_id}")
            return prediction_id

    except Exception as e:
        print(f"Failed to store prediction data: {e}")
        return None

def get_recent_predictions(limit=10, scope=None, model_name=None, database_name=None):
    """Retrieve recent predictions from the database."""
    try:
        with get_db_connection(database_name) as (conn, cursor):
            query = """
                SELECT id, prediction_date, model_name, scope, prediction_horizon_days,
                       confidence_level, prediction_data, historical_context,
                       accuracy_score, risk_level, model_metadata, created_at
                FROM predictions
                WHERE 1=1
            """
            params = []

            if scope:
                query += " AND scope = %s"
                params.append(scope)

            if model_name:
                query += " AND model_name = %s"
                params.append(model_name)

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            records = cursor.fetchall()

            columns = ['id', 'prediction_date', 'model_name', 'scope', 'prediction_horizon_days',
                      'confidence_level', 'prediction_data', 'historical_context',
                      'accuracy_score', 'risk_level', 'model_metadata', 'created_at']

            predictions = []
            for record in records:
                pred_dict = dict(zip(columns, record))
                # Parse JSON fields
                if isinstance(pred_dict['prediction_data'], str):
                    pred_dict['prediction_data'] = json.loads(pred_dict['prediction_data'])
                
                if pred_dict['historical_context'] and isinstance(pred_dict['historical_context'], str):
                    pred_dict['historical_context'] = json.loads(pred_dict['historical_context'])
                
                if pred_dict['model_metadata'] and isinstance(pred_dict['model_metadata'], str):
                    pred_dict['model_metadata'] = json.loads(pred_dict['model_metadata'])
                predictions.append(pred_dict)

            return predictions

    except Exception as e:
        print(f"Failed to retrieve predictions: {e}")
        return []

def get_prediction_by_id(prediction_id, database_name=None):
    """Retrieve a specific prediction by ID."""
    try:
        with get_db_connection(database_name) as (conn, cursor):
            cursor.execute("""
                SELECT id, prediction_date, model_name, scope, prediction_horizon_days,
                       confidence_level, prediction_data, historical_context,
                       accuracy_score, risk_level, model_metadata, created_at
                FROM predictions
                WHERE id = %s
            """, (prediction_id,))

            record = cursor.fetchone()

            if record:
                columns = ['id', 'prediction_date', 'model_name', 'scope', 'prediction_horizon_days',
                          'confidence_level', 'prediction_data', 'historical_context',
                          'accuracy_score', 'risk_level', 'model_metadata', 'created_at']

                pred_dict = dict(zip(columns, record))
                # Parse JSON fields
                if isinstance(pred_dict['prediction_data'], str):
                    pred_dict['prediction_data'] = json.loads(pred_dict['prediction_data'])
                
                if pred_dict['historical_context'] and isinstance(pred_dict['historical_context'], str):
                    pred_dict['historical_context'] = json.loads(pred_dict['historical_context'])
                
                if pred_dict['model_metadata'] and isinstance(pred_dict['model_metadata'], str):
                    pred_dict['model_metadata'] = json.loads(pred_dict['model_metadata'])

                return pred_dict
            return None

    except Exception as e:
        print(f"Failed to retrieve prediction {prediction_id}: {e}")
        return None

def store_prediction_accuracy(prediction_id, actual_results, database_name=None):
    """Store actual outcomes for prediction accuracy comparison."""
    try:
        with get_db_connection(database_name) as (conn, cursor):
            # Get prediction data to compare against
            prediction = get_prediction_by_id(prediction_id, database_name)
            if not prediction:
                print(f"Prediction {prediction_id} not found")
                return False

            prediction_data = prediction['prediction_data']
            stored_count = 0

            # For each date where we have actual data, compare with predictions
            for model_key, model_data in prediction_data.items():
                if isinstance(model_data, dict) and 'predictions' in model_data and 'dates' in model_data:
                    predictions = model_data['predictions']
                    dates = model_data['dates']

                    for i, pred_date in enumerate(dates):
                        # Check if we have actual data for this date
                        if str(pred_date) in actual_results:
                            actual_value = actual_results[str(pred_date)]
                            predicted_value = predictions[i]

                            # Calculate error metrics
                            prediction_error = actual_value - predicted_value
                            percentage_error = (prediction_error / predicted_value) * 100 if predicted_value != 0 else 0

                            # Store accuracy record
                            cursor.execute("""
                                INSERT INTO prediction_accuracy (
                                    prediction_id, actual_date, predicted_value,
                                    actual_value, prediction_error, percentage_error
                                ) VALUES (%s, %s, %s, %s, %s, %s)
                            """, (
                                prediction_id,
                                pred_date,
                                predicted_value,
                                actual_value,
                                prediction_error,
                                percentage_error
                            ))
                            stored_count += 1

            conn.commit()
            print(f"Stored {stored_count} accuracy records for prediction {prediction_id}")
            return True

    except Exception as e:
        print(f"Failed to store prediction accuracy: {e}")
        return False

def get_prediction_accuracy(prediction_id=None, model_name=None, date_range=None, database_name=None):
    """Retrieve prediction accuracy data."""
    try:
        with get_db_connection(database_name) as (conn, cursor):
            query = """
                SELECT pa.id, pa.prediction_id, pa.actual_date, pa.predicted_value,
                       pa.actual_value, pa.prediction_error, pa.percentage_error,
                       p.model_name, p.scope, p.prediction_horizon_days, pa.created_at
                FROM prediction_accuracy pa
                JOIN predictions p ON pa.prediction_id = p.id
                WHERE 1=1
            """
            params = []

            if prediction_id:
                query += " AND pa.prediction_id = %s"
                params.append(prediction_id)

            if model_name:
                query += " AND p.model_name = %s"
                params.append(model_name)

            if date_range:
                query += " AND pa.actual_date BETWEEN %s AND %s"
                params.extend(date_range)

            query += " ORDER BY pa.actual_date DESC"

            cursor.execute(query, params)
            records = cursor.fetchall()

            columns = ['id', 'prediction_id', 'actual_date', 'predicted_value',
                      'actual_value', 'prediction_error', 'percentage_error',
                      'model_name', 'scope', 'prediction_horizon_days', 'created_at']

            return [dict(zip(columns, record)) for record in records]

    except Exception as e:
        print(f"Failed to retrieve prediction accuracy: {e}")
        return []

def calculate_model_performance_stats(model_name=None, date_range=None, database_name=None):
    """Calculate performance statistics for prediction models."""
    try:
        accuracy_records = get_prediction_accuracy(
            model_name=model_name,
            date_range=date_range,
            database_name=database_name
        )

        if not accuracy_records:
            return {
                'total_predictions': 0,
                'mae': 0.0,
                'mape': 0.0,
                'accuracy_range': {'good': 0, 'acceptable': 0, 'poor': 0}
            }

        errors = [abs(record['prediction_error']) for record in accuracy_records]
        percentage_errors = [abs(record['percentage_error']) for record in accuracy_records]

        mae = sum(errors) / len(errors)
        mape = sum(percentage_errors) / len(percentage_errors)

        good_count = sum(1 for pe in percentage_errors if pe <= 5.0)
        acceptable_count = sum(1 for pe in percentage_errors if pe <= 15.0)
        poor_count = len(percentage_errors) - acceptable_count

        return {
            'total_predictions': len(accuracy_records),
            'mae': round(mae, 2),
            'mape': round(mape, 2),
            'accuracy_range': {
                'good': good_count,
                'acceptable': acceptable_count - good_count,
                'poor': poor_count
            },
            'date_range': date_range or 'all',
            'model_name': model_name or 'all_models'
        }

    except Exception as e:
        print(f"Failed to calculate model performance stats: {e}")
        return {}

def get_model_improvement_suggestions(model_name=None, database_name=None):
    """Analyze prediction accuracy and suggest model improvements."""
    try:
        performance = calculate_model_performance_stats(
            model_name=model_name,
            database_name=database_name
        )

        suggestions = {
            'model_name': model_name or 'all_models',
            'current_mape': performance.get('mape', 0),
            'current_mae': performance.get('mae', 0),
            'recommendations': [],
            'confidence_level': 'medium'
        }

        mape = performance.get('mape', 0)

        if mape > 20:
            suggestions['recommendations'].extend([
                "Consider using more sophisticated models (LSTM -> ARIMA)",
                "Increase historical data length for training",
                "Review exogenous variables (market indicators, economic data)",
                "Consider ensemble models combining multiple approaches"
            ])
            suggestions['confidence_level'] = 'low'
        elif mape > 10:
            suggestions['recommendations'].extend([
                "Fine-tune model hyperparameters",
                "Add more relevant features to the model",
                "Consider seasonal adjustments for time series",
                "Review confidence interval calculations"
            ])
            suggestions['confidence_level'] = 'medium'
        else:
            suggestions['recommendations'].extend([
                "Continue current approach with regular monitoring",
                "Consider implementing automated retraining",
                "Evaluate additional performance metrics",
                "Monitor for concept drift in market conditions"
            ])
            suggestions['confidence_level'] = 'high'

        return suggestions

    except Exception as e:
        print(f"Failed to generate improvement suggestions: {e}")
        return {}

def get_prediction_improvement_data(model_name=None, database_name=None):
    """Retrieve data specifically formatted for model improvement."""
    try:
        recent_predictions = get_recent_predictions(
            limit=50,
            model_name=model_name,
            database_name=database_name
        )
        accuracy_data = get_prediction_accuracy(
            model_name=model_name,
            database_name=database_name
        )
        performance_stats = calculate_model_performance_stats(
            model_name=model_name,
            database_name=database_name
        )
        improvement_suggestions = get_model_improvement_suggestions(
            model_name=model_name,
            database_name=database_name
        )

        return {
            'recent_predictions': recent_predictions,
            'accuracy_history': accuracy_data,
            'performance_stats': performance_stats,
            'improvement_suggestions': improvement_suggestions,
            'analysis_date': datetime.now().isoformat(),
            'total_predictions': len(recent_predictions),
            'accuracy_records': len(accuracy_data)
        }

    except Exception as e:
        print(f"Failed to retrieve improvement data: {e}")
        return {}

def cleanup_old_predictions(days_to_keep=365, database_name=None):
    """Remove old prediction records to manage database size."""
    try:
        with get_db_connection(database_name) as (conn, cursor):
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            cursor.execute("DELETE FROM prediction_accuracy WHERE created_at < %s", (cutoff_date,))
            accuracy_deleted = cursor.rowcount

            cursor.execute("DELETE FROM predictions WHERE created_at < %s", (cutoff_date,))
            predictions_deleted = cursor.rowcount

            conn.commit()
            print(f"Cleaned up {predictions_deleted} predictions and {accuracy_deleted} accuracy records older than {cutoff_date}")
            return predictions_deleted + accuracy_deleted

    except Exception as e:
        print(f"Failed to cleanup old predictions: {e}")
        return 0

def save_prediction(model_name, scope, prediction_data, database_name=None):
    """Save a single prediction model result to the database."""
    try:
        with get_db_connection(database_name) as (conn, cursor):
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'data_points': len(prediction_data.get('predictions', [])),
                'horizon': prediction_data.get('prediction_horizon_days', 30)
            }

            query = """
                INSERT INTO predictions (
                    prediction_date, model_name, scope, prediction_horizon_days,
                    confidence_level, prediction_data, historical_context,
                    accuracy_score, risk_level, model_metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id
            """

            safe_data = _to_serializable(prediction_data)
            params = (
                datetime.now().date(),
                model_name,
                scope,
                safe_data.get('prediction_horizon_days', 30),
                safe_data.get('confidence_level', 0.95),
                json.dumps(safe_data),
                json.dumps(safe_data.get('historical_context', {})),
                float(safe_data.get('accuracy_score', 0.0) or 0.0),
                float(safe_data.get('risk_level', 0.0) or 0.0),
                json.dumps(metadata)
            )

            cursor.execute(query, params)
            prediction_id = cursor.fetchone()[0]
            conn.commit()
            print(f"Saved prediction {prediction_id} for model {model_name}")
            return prediction_id

    except Exception as e:
        print(f"Failed to save prediction: {e}")
        return None


# --- Prediction Logic ---

def generate_historical_data(base_date, days=365, volatility=0.02, trend=0.0005, seed=None):
    """Generate realistic historical stock price data for demonstration."""
    if seed:
        np.random.seed(seed)

    dates = [base_date - timedelta(days=i) for i in range(days, 0, -1)]
    dates.sort()

    prices = []
    current_price = 100.0

    for i in range(len(dates)):
        trend_component = trend * i
        volatility_component = np.random.normal(0, volatility)
        if np.random.random() < 0.05:
            volatility_component *= (2 + np.random.random() * 3)

        price_change = trend_component + volatility_component
        current_price *= (1 + price_change)
        prices.append(max(current_price, 1.0))

    return pd.DataFrame({
        'date': dates,
        'close': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'volume': [int(np.random.normal(1000000, 200000)) for _ in range(len(prices))]
    })

def check_stationarity(timeseries):
    """Check if a time series is stationary using Augmented Dickey-Fuller test."""
    if not _LIBRARIES_STATUS['statsmodels']:
        return False
    try:
        result = adfuller(timeseries.dropna())
        return result[1] <= 0.05
    except:
        return False

def make_stationary(timeseries, max_diff=2):
    """Make time series stationary through differencing."""
    series = timeseries.copy()
    for i in range(max_diff):
        if check_stationarity(series):
            return series, i
        series = series.diff().dropna()
    return series, max_diff

class StockPredictor:
    """Comprehensive stock price predictor with multiple models."""

    def __init__(self, scope="portfolio", horizon_days=PREDICTION_DAYS):
        self.scope = scope
        self.horizon_days = horizon_days
        self.adjustments = self._get_scope_adjustments()

    def _get_scope_adjustments(self):
        adjustments = {
            "portfolio": {"volatility_multiplier": 1.0, "trend_correction": 0.0, "confidence_boost": 0.1},
            "individual": {"volatility_multiplier": 1.5, "trend_correction": -0.0002, "confidence_boost": -0.1},
            "by_currency": {"volatility_multiplier": 1.3, "trend_correction": -0.0001, "confidence_boost": -0.05},
            "by_type": {"volatility_multiplier": 1.2, "trend_correction": 0.0001, "confidence_boost": 0.0},
            "by_institution": {"volatility_multiplier": 0.9, "trend_correction": 0.0002, "confidence_boost": 0.15}
        }
        return adjustments.get(self.scope, adjustments["portfolio"])

    def predict_arima(self, historical_data, steps=30):
        if not _LIBRARIES_STATUS['statsmodels'] or not _LIBRARIES_STATUS['scipy']:
            print("ARIMA model skipped - required libraries not available")
            return None

        try:
            series = historical_data['close'].copy()
            # Determine optimal diff_order but pass ORIGINAL series to ARIMA
            _, diff_order = make_stationary(series)
            
            # Use original series, ARIMA handles the differencing via order=(p, d, q)
            model = ARIMA(series, order=(5, diff_order, 2))
            fitted_model = model.fit()
            forecast = fitted_model.forecast(steps=steps)

            predictions_array = np.array(forecast.values.tolist())
            prediction_std = np.std(predictions_array) * self.adjustments['volatility_multiplier'] * 0.4
            if prediction_std == 0 or np.isnan(prediction_std):
                prediction_std = np.mean(predictions_array) * 0.1

            z_score = stats.norm.ppf((1 + CONFIDENCE_LEVEL) / 2)
            upper_bounds = (predictions_array + z_score * prediction_std).tolist()
            lower_bounds = (predictions_array - z_score * prediction_std).tolist()

            last_date = historical_data['date'].iloc[-1]
            forecast_dates = [last_date + timedelta(days=i+1) for i in range(steps)]

            return {
                'dates': [d.strftime('%Y-%m-%d') for d in forecast_dates],
                'predictions': forecast.values.tolist(),
                'upper_bound': upper_bounds,
                'lower_bound': lower_bounds,
                'model_name': 'ARIMA',
                'accuracy_score': self._calculate_model_accuracy(fitted_model),
                'risk_level': self.adjustments['volatility_multiplier']
            }
        except Exception as e:
            print(f"ARIMA prediction failed: {e}")
            return None

    def predict_lstm(self, historical_data, steps=30):
        if not _LIBRARIES_STATUS['tensorflow'] or not _LIBRARIES_STATUS['sklearn']:
            print("LSTM model skipped - required libraries not available")
            return None

        try:
            data = historical_data['close'].values.reshape(-1, 1)
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(data)

            def create_sequences(data, seq_length=60):
                sequences = []
                targets = []
                for i in range(len(data) - seq_length):
                    sequences.append(data[i:i+seq_length])
                    targets.append(data[i+seq_length])
                return np.array(sequences), np.array(targets)

            seq_length = min(60, len(scaled_data) // 2)
            if seq_length < 10:
                print("LSTM model skipped - insufficient data for sequences")
                return None

            X, y = create_sequences(scaled_data, seq_length)
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(seq_length, 1)),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(1)
            ])
            model.compile(optimizer='adam', loss='mean_squared_error')
            
            train_size = int(len(X) * 0.8)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]
            
            model.fit(X_train, y_train, epochs=5, batch_size=32, verbose=0)

            predictions = []
            current_sequence = scaled_data[-seq_length:].reshape(1, seq_length, 1)

            for _ in range(steps):
                pred = model.predict(current_sequence, verbose=0)[0][0]
                predictions.append(pred)
                current_sequence = np.roll(current_sequence, -1, axis=1)
                current_sequence[0, -1] = pred

            predictions_scaled = np.array(predictions).reshape(-1, 1)
            predictions_original = scaler.inverse_transform(predictions_scaled).flatten()

            prediction_std = np.std(predictions_original) * self.adjustments['volatility_multiplier'] * 0.5
            z_score = stats.norm.ppf((1 + CONFIDENCE_LEVEL) / 2)

            last_date = historical_data['date'].iloc[-1]
            forecast_dates = [last_date + timedelta(days=i+1) for i in range(steps)]

            # model.evaluate returns MSE loss; convert to a 0–1 score
            if len(X_test) > 0:
                try:
                    eval_result = model.evaluate(X_test, y_test, verbose=0)
                    loss = float(eval_result) if not hasattr(eval_result, '__len__') else float(eval_result[0])
                    lstm_accuracy = float(max(0.3, min(0.95, 1.0 / (1.0 + loss))))
                except Exception:
                    lstm_accuracy = 0.75
            else:
                lstm_accuracy = 0.75

            return {
                'dates': [d.strftime('%Y-%m-%d') for d in forecast_dates],
                'predictions': [float(v) for v in predictions_original.tolist()],
                'upper_bound': [float(v) for v in (predictions_original + z_score * prediction_std).tolist()],
                'lower_bound': [float(v) for v in (predictions_original - z_score * prediction_std).tolist()],
                'model_name': 'LSTM Neural Network',
                'accuracy_score': lstm_accuracy,
                'risk_level': float(self.adjustments['volatility_multiplier'])
            }
        except Exception as e:
            print(f"LSTM prediction failed: {e}")
            return None

    def predict_xgboost(self, historical_data, steps=30):
        if not _LIBRARIES_STATUS['xgboost'] or not _LIBRARIES_STATUS['sklearn']:
            print("XGBoost model skipped - required libraries not available")
            return None

        try:
            df = historical_data.copy()
            df['returns'] = df['close'].pct_change()
            df['volatility_5'] = df['returns'].rolling(5).std()
            df['sma_10'] = df['close'].rolling(10).mean()
            df['sma_30'] = df['close'].rolling(30).mean()
            df['target'] = df['close'].shift(-1)
            df = df.dropna()

            if len(df) < 50:
                print("XGBoost model skipped - insufficient data for training")
                return None

            features = ['close', 'returns', 'volatility_5', 'sma_10', 'sma_30']
            X = df[features].values
            y = df['target'].values

            train_size = int(len(X) * TRAIN_RATIO)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]

            model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42)
            model.fit(X_train, y_train)

            last_features = X[-1:].copy()
            predictions = []

            for _ in range(steps):
                pred = model.predict(last_features)[0]
                predictions.append(pred)
                new_returns = (pred - last_features[0][0]) / last_features[0][0]
                new_volatility = np.std([new_returns] + list(last_features[0][1:2]))
                new_sma_10 = (last_features[0][3] * 9 + pred) / 10
                new_sma_30 = (last_features[0][4] * 29 + pred) / 30
                last_features[0] = [pred, new_returns, new_volatility, new_sma_10, new_sma_30]

            confidence_adjustment = 1.0 + self.adjustments['confidence_boost']
            prediction_std = np.std(predictions) * confidence_adjustment * 0.3
            z_score = stats.norm.ppf((1 + CONFIDENCE_LEVEL) / 2)

            last_date = historical_data['date'].iloc[-1]
            forecast_dates = [last_date + timedelta(days=i+1) for i in range(steps)]

            return {
                'dates': [d.strftime('%Y-%m-%d') for d in forecast_dates],
                'predictions': [float(v) for v in predictions],
                'upper_bound': [float(v) for v in (np.array(predictions) + z_score * prediction_std)],
                'lower_bound': [float(v) for v in (np.array(predictions) - z_score * prediction_std)],
                'model_name': 'XGBoost Regressor',
                'accuracy_score': float(model.score(X_test, y_test)) if len(X_test) > 0 else 0.85,
                'risk_level': self.adjustments['volatility_multiplier']
            }
        except Exception as e:
            print(f"XGBoost prediction failed: {e}")
            return None

    def predict_hybrid_arima_lstm(self, historical_data, steps=30):
        if not _LIBRARIES_STATUS['statsmodels'] or not _LIBRARIES_STATUS['tensorflow']:
            print("Hybrid model skipped - required libraries (ARIMA + LSTM) not available")
            return None

        try:
            arima_result = self.predict_arima(historical_data, steps)
            if not arima_result: return None
            lstm_result = self.predict_lstm(historical_data, steps)
            if not lstm_result: return None

            arima_pred = np.array(arima_result['predictions'])
            lstm_pred = np.array(lstm_result['predictions'])
            
            arima_weight = 0.6
            lstm_weight = 0.4
            hybrid_pred = arima_pred * arima_weight + lstm_pred * lstm_weight
            
            arima_ci = np.array(arima_result['upper_bound']) - np.array(arima_result['lower_bound'])
            lstm_ci = np.array(lstm_result['upper_bound']) - np.array(lstm_result['lower_bound'])
            hybrid_ci = (arima_ci * arima_weight + lstm_ci * lstm_weight) / 2

            last_date = historical_data['date'].iloc[-1]
            forecast_dates = [last_date + timedelta(days=i+1) for i in range(steps)]

            return {
                'dates': [d.strftime('%Y-%m-%d') for d in forecast_dates],
                'predictions': hybrid_pred.tolist(),
                'upper_bound': (hybrid_pred + hybrid_ci / 2).tolist(),
                'lower_bound': (hybrid_pred - hybrid_ci / 2).tolist(),
                'model_name': 'Hybrid ARIMA-LSTM',
                'accuracy_score': max(arima_result.get('accuracy_score', 0), lstm_result.get('accuracy_score', 0)),
                'risk_level': self.adjustments['volatility_multiplier']
            }
        except Exception as e:
            print(f"Hybrid model prediction failed: {e}")
            return None

    def predict_gaussian_process(self, historical_data, steps=30):
        if not _LIBRARIES_STATUS['sklearn']:
            print("Gaussian Process model skipped - sklearn not available")
            return None

        try:
            df = historical_data.copy()
            df['days'] = (df['date'] - df['date'].min()).dt.days.values
            X = df['days'].values.reshape(-1, 1)
            y = df['close'].values

            # Scale data for GP stability
            X_mean, X_std = X.mean(), X.std()
            y_mean, y_std = y.mean(), y.std()
            
            # Avoid division by zero
            X_std = X_std if X_std > 0 else 1.0
            y_std = y_std if y_std > 0 else 1.0
            
            X_scaled = (X - X_mean) / X_std
            y_scaled = (y - y_mean) / y_std

            # Kernel setup - more flexible for investment data
            kernel = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(1.0, (1e-2, 1e2))
            gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10, random_state=42, alpha=0.1)
            
            # Split for accuracy check
            train_size = int(len(X_scaled) * 0.8)
            X_train, X_test = X_scaled[:train_size], X_scaled[train_size:]
            y_train, y_test = y_scaled[:train_size], y_scaled[train_size:]
            
            gp.fit(X_train, y_train)
            
            # Predict
            last_day = X[-1][0]
            X_forecast_raw = np.array([last_day + i + 1 for i in range(steps)]).reshape(-1, 1)
            X_forecast_scaled = (X_forecast_raw - X_mean) / X_std
            
            mean_prediction_scaled, prediction_std_scaled = gp.predict(X_forecast_scaled, return_std=True)
            
            # Inverse scale
            mean_prediction = mean_prediction_scaled * y_std + y_mean
            prediction_std = prediction_std_scaled * y_std
            
            z_score = stats.norm.ppf((1 + CONFIDENCE_LEVEL) / 2)
            last_date = historical_data['date'].iloc[-1]
            forecast_dates = [last_date + timedelta(days=i+1) for i in range(steps)]

            # Calculate accuracy on test set
            y_pred_test = gp.predict(X_test) * y_std + y_mean
            y_test_orig = y_test * y_std + y_mean
            
            # R2 score manually if needed, or use gp.score on scaled data
            accuracy = float(gp.score(X_test, y_test))

            return {
                'dates': [d.strftime('%Y-%m-%d') for d in forecast_dates],
                'predictions': [float(v) for v in mean_prediction],
                'upper_bound': [float(v) for v in (mean_prediction + z_score * prediction_std)],
                'lower_bound': [float(v) for v in (mean_prediction - z_score * prediction_std)],
                'model_name': 'Gaussian Process',
                'accuracy_score': accuracy if accuracy > -1 else 0.5,
                'risk_level': self.adjustments['volatility_multiplier']
            }
        except Exception as e:
            print(f"Gaussian Process prediction failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def predict_auto_arima(self, historical_data, steps=30):
        """Generate predictions using Auto-ARIMA from pmdarima."""
        if not _LIBRARIES_STATUS.get('pmdarima', False):
            print("Auto-ARIMA model skipped - pmdarima not available")
            return None

        try:
            series = historical_data['close'].copy()
            
            # Use pmdarima to find optimal ARIMA parameters
            model = pm.auto_arima(series, start_p=1, start_q=1,
                                 test='adf',       # use adftest to find optimal 'd'
                                 max_p=3, max_q=3, # maximum p and q
                                 m=1,              # frequency of series
                                 d=None,           # let model determine 'd'
                                 seasonal=False,   # No Seasonality
                                 start_P=0, 
                                 D=0, 
                                 trace=False,
                                 error_action='ignore',  
                                 suppress_warnings=True, 
                                 stepwise=True)

            forecast, conf_int = model.predict(n_periods=steps, return_conf_int=True)
            
            predictions = forecast.tolist()
            lower_bound = conf_int[:, 0].tolist()
            upper_bound = conf_int[:, 1].tolist()

            last_date = historical_data['date'].iloc[-1]
            forecast_dates = [last_date + timedelta(days=i+1) for i in range(steps)]
            
            # Simple accuracy check
            accuracy = 0.85 # Placeholder as we used all data for fitting
            
            return {
                'dates': [d.strftime('%Y-%m-%d') for d in forecast_dates],
                'predictions': [float(v) for v in predictions],
                'upper_bound': [float(v) for v in upper_bound],
                'lower_bound': [float(v) for v in lower_bound],
                'model_name': 'Auto-ARIMA (pmdarima)',
                'accuracy_score': float(accuracy),
                'risk_level': self.adjustments['volatility_multiplier']
            }

        except Exception as e:
            print(f"Auto-ARIMA prediction failed: {e}")
            return None

    def calculate_quant_metrics(self, historical_data):
        """Calculate quantitative metrics using QuantLib and pyfolio if available."""
        metrics = {}
        
        # QuantLib Example: Date Calculation
        if _LIBRARIES_STATUS.get('quantlib', False):
            try:
                today = ql.Date.todaysDate()
                calendar = ql.UnitedStates(ql.UnitedStates.NYSE)
                metrics['quantlib_business_days'] = calendar.businessDaysBetween(
                    today, today + ql.Period(30, ql.Days)
                )
            except Exception as e:
                print(f"QuantLib metric calculation failed: {e}")

        # Pyfolio Example: Simple Stats
        if _LIBRARIES_STATUS.get('pyfolio', False):
            try:
                # pyfolio expects returns
                returns = historical_data.set_index('date')['close'].pct_change().dropna()
                # Need to convert index to datetime (tz-naive is okay for simple stats)
                # simple_stats returns a pandas Series
                perf_stats = pf.timeseries.perf_stats(returns)
                metrics['sharpe_ratio'] = perf_stats.get('Sharpe ratio', 0)
                metrics['sortino_ratio'] = perf_stats.get('Sortino ratio', 0)
                metrics['max_drawdown'] = perf_stats.get('Max drawdown', 0)
            except Exception as e:
                print(f"Pyfolio metric calculation failed: {e}")

        return metrics

    def _calculate_model_accuracy(self, fitted_model):
        try:
            aic = fitted_model.aic
            return max(0.3, min(0.95, 1.0 - (aic / 1000)))
        except:
            return 0.7

    def get_available_models(self):
        available_models = []
        if self.predict_arima(None, 1) is not None or (_LIBRARIES_STATUS['statsmodels'] and _LIBRARIES_STATUS['scipy']):
            available_models.append('arima')
        if self.predict_lstm(None, 1) is not None or (_LIBRARIES_STATUS['tensorflow'] and _LIBRARIES_STATUS['sklearn']):
            available_models.append('lstm')
        if self.predict_xgboost(None, 1) is not None or (_LIBRARIES_STATUS['xgboost'] and _LIBRARIES_STATUS['sklearn']):
            available_models.append('xgboost')
        if (('arima' in available_models) and
            (self.predict_lstm(None, 1) is not None or (_LIBRARIES_STATUS['tensorflow'] and _LIBRARIES_STATUS['sklearn']))):
            available_models.append('hybrid')
        if self.predict_gaussian_process(None, 1) is not None or _LIBRARIES_STATUS['sklearn']:
            available_models.append('gaussian_process')
        if _LIBRARIES_STATUS.get('pmdarima', False):
            available_models.append('auto_arima')
        return available_models

def get_historical_data_from_db(database_name, scope="portfolio", days=365, investment_name=None):
    """Fetch historical investment data from the database with currency conversion."""
    from .currency import convert_currency_amount
    try:
        with get_db_connection(database_name) as (conn, cursor):
            start_date = datetime.now() - timedelta(days=days)
            
            if scope == "individual" and investment_name:
                # Fetch unit price history for specific investment
                query = """
                    SELECT up.unit_price_date, up.unit_price as close, i.unit_currency
                    FROM unit_prices up
                    JOIN investments i ON up.investment_id = i.id
                    WHERE up.unit_price_date >= %s AND i.investment_name = %s
                    ORDER BY up.unit_price_date ASC
                """
                cursor.execute(query, (start_date, investment_name))
                rows = cursor.fetchall()
                if not rows: return None
                
                df = pd.DataFrame(rows, columns=['date', 'close', 'currency'])
                # For individual, we don't necessarily need to convert to ZAR unless specified
                # But for consistency, let's just return what we have.
                # If we want it in ZAR:
                # df['close'] = [convert_currency_amount(r['close'], r['currency'], 'ZAR', r['date'].strftime('%Y-%m-%d'), database_name, cursor) for _, r in df.iterrows()]
            else:
                # Fetch ALL historical unit prices and units held to aggregate accurately
                query = """
                    SELECT up.unit_price_date, up.unit_price, i.number_of_units_held, i.unit_currency
                    FROM unit_prices up
                    JOIN investments i ON up.investment_id = i.id
                    WHERE up.unit_price_date >= %s
                    ORDER BY up.unit_price_date ASC
                """
                cursor.execute(query, (start_date,))
                rows = cursor.fetchall()
                if not rows: return None
                
                temp_df = pd.DataFrame(rows, columns=['date', 'unit_price', 'units', 'currency'])
                temp_df['date'] = pd.to_datetime(temp_df['date'])
                
                # Convert to ZAR
                rate_cache = {}
                converted_values = []
                for _, row in temp_df.iterrows():
                    d_str = row['date'].strftime('%Y-%m-%d')
                    val_zar = convert_currency_amount(row['unit_price'] * row['units'], row['currency'], 'ZAR', d_str, database_name, cursor, rate_cache)
                    converted_values.append(val_zar)
                
                temp_df['value_zar'] = converted_values
                
                # Aggregate by date
                df = temp_df.groupby('date')['value_zar'].sum().reset_index()
                df.rename(columns={'value_zar': 'close'}, inplace=True)
            
            df['date'] = pd.to_datetime(df['date'])
            df['high'] = df['close'] * 1.01
            df['low'] = df['close'] * 0.99
            df['open'] = df['close']
            df['volume'] = 1000
            
            return df

    except Exception as e:
        print(f"Error fetching historical data from DB: {e}")
        return None

def get_investment_predictions(database_name, scope="portfolio", model_filter=None, 
                               specific_investment_name=None, specific_currency=None, 
                               specific_investment_type=None, specific_institution=None):
    """
    Main function to get investment predictions with specified scope and model filter.
    """
    try:
        # Try to get real data from DB
        historical_data = get_historical_data_from_db(database_name, scope, days=365, investment_name=specific_investment_name)
        
        if historical_data is None or historical_data.empty:
            print("⚠️ Using synthetic data (DB data unavailable)")
            base_date = datetime.now()
            volatility_map = {
                "portfolio": 0.015, "individual": 0.025, "by_currency": 0.020,
                "by_type": 0.018, "by_institution": 0.012
            }
            trend_map = {
                "portfolio": 0.0003, "individual": 0.0001, "by_currency": 0.0002,
                "by_type": 0.0004, "by_institution": 0.0005
            }
            seed_map = {"portfolio": 42, "individual": 24, "by_currency": 33, "by_type": 55, "by_institution": 77}
            
            historical_data = generate_historical_data(
                base_date, days=365, 
                volatility=volatility_map.get(scope, 0.015), 
                trend=trend_map.get(scope, 0.0003), 
                seed=seed_map.get(scope, 42)
            )

        predictor = StockPredictor(scope=scope, horizon_days=PREDICTION_DAYS)
        available_models = predictor.get_available_models()

        if model_filter and isinstance(model_filter, list):
            requested_models = [m for m in model_filter if m in available_models]
            if not requested_models:
                print(f"Warning: None of the requested models {model_filter} are available")
                requested_models = available_models[:3]
        else:
            requested_models = available_models

        print(f"Running predictions for scope '{scope}' with models: {', '.join(requested_models)}")

        predictions = {}
        for model_key in requested_models:
            try:
                model_functions = {
                    'arima': predictor.predict_arima,
                    'lstm': predictor.predict_lstm,
                    'xgboost': predictor.predict_xgboost,
                    'hybrid': predictor.predict_hybrid_arima_lstm,
                    'gaussian_process': predictor.predict_gaussian_process,
                    'auto_arima': predictor.predict_auto_arima
                }

                if model_key in model_functions:
                    result = model_functions[model_key](historical_data, PREDICTION_DAYS)
                    if result:
                        predictions[model_key] = result
                        try:
                            save_prediction(model_key, scope, result, database_name)
                        except Exception as save_err:
                            print(f"Failed to save prediction for {model_key}: {save_err}")
                    else:
                        print(f"Model {model_key} returned None")
                else:
                    print(f"Unknown model: {model_key}")
            except Exception as e:
                print(f"Error running model {model_key}: {e}")

        historical_result = {
            'dates': historical_data['date'].dt.strftime('%Y-%m-%d').tolist(),
            'prices': historical_data['close'].tolist(),
            'highs': historical_data['high'].tolist(),
            'lows': historical_data['low'].tolist(),
            'volumes': historical_data['volume'].tolist()
        }

        library_status = {
            'available_models': available_models,
            'library_status': _LIBRARIES_STATUS.copy(),
            'models_requested': requested_models,
            'models_delivered': list(predictions.keys())
        }

        return {
            'scope': scope,
            'historical_data': historical_result,
            'predictions': predictions,
            'prediction_horizon_days': PREDICTION_DAYS,
            'confidence_level': CONFIDENCE_LEVEL,
            'timestamp': datetime.now().isoformat(),
            'models_available': len(available_models),
            'models_delivered': len(predictions),
            'data_quality_score': 0.85,
            'system_info': library_status
        }

    except Exception as e:
        print(f"Prediction generation failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'scope': scope,
            'error': str(e),
            'historical_data': {'dates': [], 'prices': []},
            'predictions': {},
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'library_status': _LIBRARIES_STATUS.copy(),
                'error': str(e)
            }
        }

def get_available_models_info():
    """Return information about available models and library status."""
    predictor = StockPredictor()
    available_models = predictor.get_available_models()

    return {
        'available_models': available_models,
        'library_status': _LIBRARIES_STATUS.copy(),
        'total_libraries_available': sum(_LIBRARIES_STATUS.values()),
        'models_count': len(available_models)
    }
