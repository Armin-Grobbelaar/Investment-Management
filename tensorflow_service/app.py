"""
TensorFlow Prediction API
=========================
Standalone service that trains an LSTM model on historical price data and
returns multi-step forecasts with confidence intervals.

The investment backend calls this service over HTTP (POST /predict/lstm) so
that the investment app image can stay slim while TensorFlow runs in its own
container.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import List

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scipy import stats
from sklearn.preprocessing import MinMaxScaler, StandardScaler

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tensorflow_service")

app = FastAPI(title="TensorFlow Prediction Service")


class HistoricalPoint(BaseModel):
    date: str
    price: float


class LSTMPredictRequest(BaseModel):
    data: List[HistoricalPoint]
    steps: int = 30
    confidence_level: float = 0.95
    volatility_multiplier: float = 1.0


def build_lstm_forecast(prices, dates, steps, confidence_level, volatility_multiplier):
    """Build, train and recursively forecast with an LSTM model.

    The model is trained on the stationary *log-return* series rather than the
    raw price level. Recursive prediction on a non-stationary level series
    compounds small errors and produces divergent / negative forecasts; by
    predicting returns (which stay small and mean-reverting) and reconstructing
    the level from the last observed price, forecasts stay positive and bounded.
    """
    data = np.array(prices, dtype=np.float64).flatten()
    # Zero/negative values (data glitches) are filtered out before the log
    # transform. The forecast is anchored to the last *valid* positive price so
    # the level reconstruction and the flat fallback use the same reference.
    valid = data[data > 0]
    last_observed = float(valid[-1]) if len(valid) else 0.0
    last_date = datetime.fromisoformat(dates[-1]) if dates else datetime.now()
    forecast_dates = [(last_date + timedelta(days=i + 1)).strftime('%Y-%m-%d') for i in range(steps)]

    def anchored_fallback(ret_std=None):
        """Flat forecast anchored at the last observed price."""
        levels = np.full(steps, last_observed)
        band = 0.0
        if ret_std is not None and last_observed > 0:
            band = last_observed * ret_std * volatility_multiplier
        z = stats.norm.ppf((1 + confidence_level) / 2)
        return {
            'dates': forecast_dates,
            'predictions': [float(v) for v in levels.tolist()],
            'upper_bound': [float(v) for v in (levels + z * band).tolist()],
            'lower_bound': [float(v) for v in np.maximum(levels - z * band, 0).tolist()],
            'model_name': 'LSTM Neural Network',
            'accuracy_score': 0.5,
            'risk_level': float(volatility_multiplier),
        }

    # --- Stationary transform: log returns -------------------------------
    if len(valid) < 40:
        return anchored_fallback()
    log_prices = np.log(valid)
    returns = np.diff(log_prices)
    if len(returns) < 20:
        return anchored_fallback(ret_std=float(np.std(returns)) if len(returns) else None)

    scaler = StandardScaler()
    scaled_returns = scaler.fit_transform(returns.reshape(-1, 1))

    def create_sequences(series, seq_length):
        sequences, targets = [], []
        for i in range(len(series) - seq_length):
            sequences.append(series[i:i + seq_length])
            targets.append(series[i + seq_length])
        return np.array(sequences), np.array(targets)

    seq_length = min(40, len(scaled_returns) // 2)
    if seq_length < 8:
        return anchored_fallback(ret_std=float(np.std(returns)))
    X, y = create_sequences(scaled_returns, seq_length)
    if len(X) < 4:
        return anchored_fallback(ret_std=float(np.std(returns)))

    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(seq_length, 1)),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(25),
        Dense(1),
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')

    train_size = max(1, int(len(X) * 0.8))
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]

    model.fit(X_train, y_train, epochs=10, batch_size=16, verbose=0)

    # Recursive multi-step forecast in return space
    predictions_scaled = []
    current_sequence = scaled_returns[-seq_length:].reshape(1, seq_length, 1)
    for _ in range(steps):
        pred = float(model.predict(current_sequence, verbose=0)[0][0])
        predictions_scaled.append(pred)
        current_sequence = np.roll(current_sequence, -1, axis=1)
        current_sequence[0, -1] = pred

    pred_returns = scaler.inverse_transform(
        np.array(predictions_scaled).reshape(-1, 1)
    ).flatten()

    # Cap extreme return predictions so the level forecast cannot explode
    ret_std = float(np.std(returns))
    pred_returns = np.clip(pred_returns, -3 * ret_std, 3 * ret_std)

    # Reconstruct the level series from the last observed price
    cumulative = np.cumsum(pred_returns)
    levels = np.exp(log_prices[-1] + cumulative)

    # Keep forecasts positive and bounded (never collapse below half of last price)
    levels = np.maximum(levels, last_observed * 0.5)

    # Confidence intervals: cumulative uncertainty grows with sqrt(step)
    if len(X_test) > 0:
        try:
            residuals_scaled = model.predict(X_test, verbose=0).flatten() - y_test.flatten()
            residuals = scaler.inverse_transform(residuals_scaled.reshape(-1, 1)).flatten()
            residual_std = float(np.std(residuals))
        except Exception:
            residual_std = ret_std
    else:
        residual_std = ret_std

    z_score = stats.norm.ppf((1 + confidence_level) / 2)
    cumulative_std = residual_std * np.sqrt(np.arange(1, steps + 1)) * volatility_multiplier
    upper = levels * np.exp(z_score * cumulative_std)
    lower = np.maximum(levels * np.exp(-z_score * cumulative_std), 0)

    if len(X_test) > 0:
        try:
            eval_result = model.evaluate(X_test, y_test, verbose=0)
            loss = float(eval_result) if not hasattr(eval_result, '__len__') else float(eval_result[0])
            accuracy = float(max(0.3, min(0.95, 1.0 / (1.0 + loss))))
        except Exception:
            accuracy = 0.75
    else:
        accuracy = 0.75

    return {
        'dates': forecast_dates,
        'predictions': [float(v) for v in levels.tolist()],
        'upper_bound': [float(v) for v in upper.tolist()],
        'lower_bound': [float(v) for v in lower.tolist()],
        'model_name': 'LSTM Neural Network',
        'accuracy_score': accuracy,
        'risk_level': float(volatility_multiplier),
    }


@app.get("/health")
def health():
    return {"status": "healthy", "tensorflow_version": tf.__version__}


@app.get("/")
def root():
    return {"service": "tensorflow-prediction-api", "status": "ok"}


@app.post("/predict/lstm")
def predict_lstm(request: LSTMPredictRequest):
    try:
        if len(request.data) < 30:
            raise HTTPException(status_code=400, detail="Need at least 30 historical data points")
        # Bounds validation — prevents resource exhaustion (recursive predict
        # runs once per step) and garbage confidence bounds.
        if not 1 <= request.steps <= 365:
            raise HTTPException(status_code=400, detail="steps must be between 1 and 365")
        if not 0.5 < request.confidence_level < 1.0:
            raise HTTPException(status_code=400, detail="confidence_level must be between 0.5 and 1.0 (exclusive)")
        if request.volatility_multiplier < 0:
            raise HTTPException(status_code=400, detail="volatility_multiplier must be non-negative")
        prices = [p.price for p in request.data]
        if any(not math.isfinite(p) for p in prices):
            raise HTTPException(status_code=400, detail="prices must be finite numbers (NaN/Infinity not allowed)")
        result = build_lstm_forecast(
            prices=prices,
            dates=[p.date for p in request.data],
            steps=request.steps,
            confidence_level=request.confidence_level,
            volatility_multiplier=request.volatility_multiplier,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")
    except Exception:
        logger.exception("LSTM prediction failed")
        raise HTTPException(status_code=500, detail="Internal prediction error")
