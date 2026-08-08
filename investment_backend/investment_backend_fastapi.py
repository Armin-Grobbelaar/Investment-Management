
from investment_database_functions import (
    get_db_connection, get_investment_summary_display, get_portfolio_total_value,
    get_currencies_in_portfolio, get_investment_types_in_portfolio,
    get_all_investment_values, get_investment_data,
    get_investment_summary, import_unit_prices_api, create_connection, add_investment, add_user,
    get_edit_data_tables, get_edit_data_table, update_edit_data_table,
    add_edit_data_row, delete_edit_data_row, get_net_worth_timeseries
)
from modules.csv_import import import_mixed_csv_data, import_csv_data, import_inflation_csv_data
from investment_stock_predictions import get_investment_predictions as generate_predictions
from modules.predictions import (
    store_prediction_data, get_recent_predictions, get_prediction_by_id,
    store_prediction_accuracy, get_prediction_accuracy, calculate_model_performance_stats,
    get_model_improvement_suggestions, get_prediction_improvement_data
)
from modules.property_calculator import (
    run_property_projection, run_sensitivity_analysis, run_property_monte_carlo,
    calculate_pmt, calculate_sa_transfer_duty,
    DEFAULT_BOND_INTEREST_RATE, DEFAULT_RENTAL_GROWTH_RATE, DEFAULT_VACANCY_RATE,
    DEFAULT_PROPERTY_GROWTH_RATE, DEFAULT_INFLATION_RATE
)
from modules.property_scraper import scrape_property_url
from modules.property_reporting import generate_property_pdf_report
from modules.factsheet_downloader import (
    download_factsheet, get_factsheets_for_investment, run_monthly_factsheet_downloader,
    get_factsheet_path
)
from modules.price_scraper import fetch_prices_now, get_backfill_status
from modules.database import get_config_value, get_all_config, invalidate_config_cache
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi import FastAPI, Response, BackgroundTasks, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timedelta, date
import json
import pandas as pd
import os
import tempfile
import logging

# Logger for the backend
logger = logging.getLogger("investment_backend")
logging.basicConfig(level=logging.INFO)

# Process start time — used by the /health endpoint to report real uptime
_APP_START_TIME = datetime.now()

# Default database name from environment
DEFAULT_DB = os.getenv("INVESTMENTS_DB", "Investments")

# Configuration Constants
CACHE_TIMEOUT_SECONDS = int(os.environ.get("CACHE_TIMEOUT_SECONDS", "300"))
DEFAULT_BASE_CURRENCY = os.environ.get("DEFAULT_BASE_CURRENCY", "ZAR")
DASHBOARD_DEFAULT_VALUE = float(os.environ.get("DASHBOARD_DEFAULT_VALUE", "100000"))
SIMULATION_YEARS = int(os.environ.get("SIMULATION_YEARS", "5"))
SIMULATION_MONTHS = SIMULATION_YEARS * 12
ROLLING_YEARS_1Y = 1
ROLLING_YEARS_3Y = 3
ROLLING_YEARS_5Y = 5
PORTFOLIO_RISK_BASELINE = 1.0
INDIVIDUAL_RISK_MULTIPLIER = 1.5
CURRENCY_RISK_MULTIPLIER = 1.2
TYPE_RISK_MULTIPLIER = 1.3
INSTITUTION_RISK_MULTIPLIER = 1.4
PORTFOLIO_DIVIDEND_BASELINE = 0.04
INDIVIDUAL_DIVIDEND_BASE = 0.04
FALLBACK_CONTRIBUTION_DIVISOR = float(os.environ.get("FALLBACK_CONTRIBUTION_DIVISOR", "1.27"))
FALLBACK_INVESTMENT_TIME_YEARS = float(os.environ.get("FALLBACK_INVESTMENT_TIME_YEARS", "1.5"))
FALLBACK_PORTFOLIO_IRR = float(os.environ.get("FALLBACK_PORTFOLIO_IRR", "9.5"))
CORRECTION_PROBABILITY_PORTFOLIO = 0.02
CORRECTION_PROBABILITY_INDIVIDUAL = 0.04
DAILY_GROWTH_BASELINE = 0.001
MARKET_CORRECTION_MIN = 0.05
MARKET_CORRECTION_MAX = 0.15
VOLATILITY_BASELINE_PORTFOLIO = 0.15
VOLATILITY_BASELINE_1Y = 0.15
VOLATILITY_BASELINE_3Y = 0.20
VOLATILITY_BASELINE_5Y = 0.25
STD_DEV_MONTHLY = 0.03
DRAWDOWN_DATA_POINTS = 200
PERFORMANCE_DATA_POINTS = 48
ROLLING_1Y_PERIODS = 12
ROLLING_3Y_PERIODS = 20
ROLLING_5Y_PERIODS = 10
VOLATILITY_PERIODS = 24
SHARPE_PERIODS = 16
CONTRIBUTION_PERIODS = 60
DIVIDEND_PERIODS = 60
AREA_CHART_DAYS = 30
AREA_CHART_TOP_N = 5
EXCELLENT_SHARPE_RATIO = 1.2
GOOD_SHARPE_RATIO = 0.8
EXCELLENT_RETURN_THRESHOLD = 50.0
GOOD_RETURN_THRESHOLD = 20.0
GOOD_VOLATILITY_THRESHOLD = 0.15

from contextlib import asynccontextmanager

_scheduler_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background scheduler (daily price fetch + monthly factsheet download)."""
    global _scheduler_instance
    try:
        from modules.price_scraper import start_scheduler
        _scheduler_instance = start_scheduler("Investments")
        print("✅ Background scheduler started (daily prices at 11:30 SAST, factsheets on 20th)")
    except Exception as e:
        print(f"⚠️ Failed to start background scheduler: {e}")

    # ── Run a price fetch in the background on startup ──────────────────────
    # This ensures prices are fresh when the app is (re-)started.
    # The 15-second delay gives the scheduler a moment to initialise and avoids
    # competing with the first health-check / probe requests.
    def _startup_price_fetch():
        import time
        time.sleep(15)
        try:
            from modules.price_scraper import run_daily_price_fetch
            print("⏰ Running startup price fetch…")
            run_daily_price_fetch("Investments")
            print("✅ Startup price fetch complete")
        except Exception as e:
            print(f"⚠️ Startup price fetch failed: {e}")

    import threading
    threading.Thread(target=_startup_price_fetch, daemon=True,
                     name="startup-price-fetch").start()

    yield
    if _scheduler_instance:
        try:
            _scheduler_instance.shutdown(wait=False)
        except Exception:
            pass


investment_api = FastAPI(lifespan=lifespan)

# Add compression middleware for better performance
investment_api.add_middleware(GZipMiddleware, minimum_size=1000)

# In-memory cache for expensive operations (simple implementation)
_cache_data = {}
_cache_expiry = {}
CACHE_TIMEOUT = CACHE_TIMEOUT_SECONDS  # in seconds

def _get_cache_key(endpoint: str, params: dict = None) -> str:
    """Generate cache key from endpoint and parameters."""
    if params:
        param_str = json.dumps(params, sort_keys=True)
        return f"{endpoint}:{param_str}"
    return endpoint

def _get_cached_data(cache_key: str) -> dict | None:
    """Get cached data if not expired."""
    if cache_key in _cache_data and cache_key in _cache_expiry:
        if datetime.now() < _cache_expiry[cache_key]:
            return _cache_data[cache_key]
        else:
            # Clean up expired cache
            del _cache_data[cache_key]
            del _cache_expiry[cache_key]
    return None

def _set_cache_data(cache_key: str, data: dict) -> None:
    """Cache data with expiry time."""
    _cache_data[cache_key] = data
    _cache_expiry[cache_key] = datetime.now() + timedelta(seconds=CACHE_TIMEOUT)

class AddUserRequest(BaseModel):
    username: str
    user_surname: str


class AddInvestmentRequest(BaseModel):
    database_name: str
    institution_name: str
    initial_investment_date: str
    investment_type: str
    investment_name: str
    investment_ticker: str
    unit_currency: str
    initial_unit_price: float
    unit_price: float
    number_of_units_held: float
    total_dividends_received: float
    total_tax_paid: float
    total_fees_paid: float
    investment_fee: float
    investment_status: str

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3003",
    "http://127.0.0.1:3003",
    "http://192.168.10.100:3003"
]

investment_api.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@investment_api.get("/dashboard_data/{database_name}")
async def fastapi_get_dashboard_data(database_name: str, base_currency: str = "ZAR"):
    """
    Optimized endpoint that provides all dashboard data in a single response.
    Includes caching and pre-computed aggregations for maximum performance.
    """
    cache_key = _get_cache_key("dashboard_data", {
        "database": database_name,
        "base_currency": base_currency
    })

    # Check cache first
    cached_data = _get_cached_data(cache_key)
    if cached_data:
        return Response(
            json.dumps(cached_data),
            media_type="application/json",
            headers={"X-Cache": "HIT"}
        )

    try:
        # Get investment summary with currency conversion
        investment_summary_df = get_investment_summary_display(
            base_currency=base_currency,
            database_name=database_name
        )

        # Get aggregate totals
        portfolio_totals = get_portfolio_total_value(
            base_currency=base_currency,
            database_name=database_name
        )

        # Get currencies and types in portfolio
        currencies_in_portfolio = get_currencies_in_portfolio(database_name)
        types_in_portfolio = get_investment_types_in_portfolio(database_name)

        # Convert DataFrame to dict with proper serialization
        investment_summary = []
        for _, row in investment_summary_df.iterrows():
            # Convert datetime objects and NaN values properly
            row_dict = {}
            for col, value in row.items():
                if pd.isna(value):
                    row_dict[col] = None
                elif hasattr(value, 'isoformat'):  # datetime
                    row_dict[col] = value.isoformat()
                else:
                    row_dict[col] = value
            investment_summary.append(row_dict)

        # Prepare dashboard data structure
        dashboard_data = {
            "investment_summary": investment_summary,
            "portfolio_totals": portfolio_totals,
            "currencies_in_portfolio": currencies_in_portfolio,
            "types_in_portfolio": types_in_portfolio,
            "base_currency": base_currency,
            "timestamp": datetime.now().isoformat(),
            "cache_expires_in": CACHE_TIMEOUT
        }

        # Cache the result
        _set_cache_data(cache_key, dashboard_data)

        return Response(
            json.dumps(dashboard_data),
            media_type="application/json",
            headers={"X-Cache": "MISS"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")

@investment_api.get("/investment_timeseries/{database_name}")
async def fastapi_get_investment_timeseries(database_name: str, base_currency: str = "ZAR",
                                           investment_name: str = None):
    """
    Get optimized time series data for charts with caching.
    """
    cache_key = _get_cache_key("timeseries", {
        "database": database_name,
        "base_currency": base_currency,
        "investment": investment_name or "all"
    })

    # Check cache first
    cached_data = _get_cached_data(cache_key)
    if cached_data:
        return Response(
            json.dumps(cached_data),
            media_type="application/json",
            headers={"X-Cache": "HIT"}
        )

    try:
        # Get investment data with currency conversion
        df = get_investment_data(
            base_currency=base_currency,
            database_name=database_name
        )

        if df.empty:
            return Response(
                json.dumps({"timeseries": [], "date_range": {}}),
                media_type="application/json"
            )

        # Filter by specific investment if requested
        if investment_name:
            df = df[df["investment_name"] == investment_name]

        # Prepare time series data for frontend charts
        timeseries_data = []
        for investment in df["investment_name"].unique():
            inv_data = df[df["investment_name"] == investment].copy()

            # Sort by date
            inv_data = inv_data.sort_values("unit_price_date")

            # Convert dates and prepare points
            points = []
            for _, row in inv_data.iterrows():
                point = {
                    "x": row["unit_price_date"].isoformat() if hasattr(row["unit_price_date"], 'isoformat') else str(row["unit_price_date"]),
                    "y": float(row["investment_value"]) if not pd.isna(row["investment_value"]) else 0.0
                }
                points.append(point)

            timeseries_data.append({
                "label": investment,
                "data": points,
                "borderColour": None  # Frontend will assign colors
            })

        # Get date range
        if not df.empty:
            min_date = df["unit_price_date"].min()
            max_date = df["unit_price_date"].max()

            date_range = {
                "min": min_date.isoformat() if hasattr(min_date, 'isoformat') else str(min_date),
                "max": max_date.isoformat() if hasattr(max_date, 'isoformat') else str(max_date)
            }
        else:
            date_range = {"min": None, "max": None}

        result = {
            "timeseries": timeseries_data,
            "date_range": date_range,
            "base_currency": base_currency,
            "total_investments": len(df["id"].unique()) if not df.empty else 0
        }

        # Cache the result
        _set_cache_data(cache_key, result)

        return Response(
            json.dumps(result),
            media_type="application/json",
            headers={"X-Cache": "MISS"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch timeseries data: {str(e)}")

@investment_api.get("/investment_summary/{database_name}")
def fastapi_get_investment_summary(database_name):
    global investment_summary
    investment_summary = get_investment_summary(database_name)

    return Response(investment_summary.to_json(orient="records"), media_type="application/json")

@investment_api.post("/add_user")
def fastapi_add_user(user_data: AddUserRequest):
    # Call your add_user function with the data from the request
    add_user(user_data.username, user_data.user_surname)
    return {"message": "User successfully added"}

@investment_api.get("/all_investment_values/{database_name}")
def fastapi_get_all_investment_values(database_name: str):
    investment_values = get_all_investment_values(database_name)
    return Response(investment_values.to_json(orient="records"), media_type="application/json")

@investment_api.get("/investment_data/{database_name}/{investment_name}/{column_name}")
async def fastapi_get_investment_values(database_name: str, investment_name: str, column_name: str):
    global investment_values
    investment_values = pd.DataFrame()
    if (investment_values.empty):
        investment_values = get_all_investment_values(database_name)
    investment_values_filttered = investment_values[investment_values["investment_name"] == investment_name][column_name]
    return Response(investment_values_filttered.to_json(orient="records"), media_type="application/json")

@investment_api.post("/add_investment/{database_name}")
async def fastapi_add_investment(database_name: str, investment_data: AddInvestmentRequest, background_tasks: BackgroundTasks = None):
    try:
        # Set up database connection - this function needs it for the legacy add_investment call
        create_connection(database_name)
        add_investment(
            database_name=database_name,
            institution_name=investment_data.institution_name,
            initial_investment_date=investment_data.initial_investment_date,
            investment_type=investment_data.investment_type,
            investment_name=investment_data.investment_name,
            investment_ticker=investment_data.investment_ticker,
            unit_currency=investment_data.unit_currency,
            initial_unit_price=investment_data.initial_unit_price,
            unit_price=investment_data.unit_price,
            number_of_units_held=investment_data.number_of_units_held,
            total_dividends_received=investment_data.total_dividends_received,
            total_tax_paid=investment_data.total_tax_paid,
            total_fees_paid=investment_data.total_fees_paid,
            investment_fee=investment_data.investment_fee,
            investment_status=investment_data.investment_status,
        )

        # Trigger historical unit-price backfill in the background.
        # New investments should have ALL previous prices fetched (Yahoo first,
        # ProfileData Playwright fallback for SA unit trusts not on Yahoo).
        if background_tasks:
            from modules.price_scraper import _get_investments, backfill_historical_prices, _determine_source_and_ticker

            def _backfill_new_investment():
                try:
                    invs = _get_investments(database_name)
                    if invs:
                        # The most recently added investment is the last one
                        inv = invs[-1]
                        logger.info(f"🔄 Backfilling historical prices for new investment '{inv['investment_name']}'")
                        backfill_historical_prices(inv, database_name)
                except Exception as e:
                    logger.error(f"Background backfill failed: {e}")

            background_tasks.add_task(_backfill_new_investment)

        return {"message": "Investment added successfully; historical price backfill queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add investment: {str(e)}")

@investment_api.post("/import_unit_prices/")
async def import_unit_prices(
    file: UploadFile = File(...),
    investment_name: str = Form(...)
):
    try:
        # Save the uploaded file content temporarily in memory
        file_content = await file.read()
        file_name = "temp_unit_prices.csv"

        # Write the file content to a temporary file
        with open(file_name, "wb") as temp_file:
            temp_file.write(file_content)

        # Call the existing function
        import_unit_prices_api(file_name, investment_name)

        return {"message": "Unit prices imported successfully", "investment_name": investment_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@investment_api.post("/import_investment_data/{data_type}/")
async def import_investment_data(
    data_type: str,
    file: UploadFile = File(...),
    investment_name: str = Form(...)
):
    try:
        # Validate data type
        allowed_data_types = ['unit_prices', 'transactions', 'returns', 'dividends', 'fees', 'tax', 'inflation']
        if data_type not in allowed_data_types:
            raise HTTPException(status_code=400, detail=f"Invalid data type. Allowed: {', '.join(allowed_data_types)}")

        # Save the uploaded file content to a temporary file
        file_content = await file.read()
        temp_file_name = f"temp_{data_type}.csv"

        with open(temp_file_name, "wb") as temp_file:
            temp_file.write(file_content)

        # Import the data based on type
        if data_type == 'mixed':
            # Handle mixed data type CSV
            message = import_mixed_csv_data(temp_file_name, investment_name)

        elif data_type == 'unit_prices':
            # Use existing unit prices function
            import_unit_prices_api(temp_file_name, investment_name)
            message = f"Unit prices imported successfully for {investment_name}"

        elif data_type == 'transactions':
            # Call import function for transactions
            import_csv_data(temp_file_name, data_type, investment_name)
            message = f"Transactions imported successfully for {investment_name}"

        elif data_type == 'returns':
            # Call import function for returns
            import_csv_data(temp_file_name, data_type, investment_name)
            message = f"Returns data imported successfully for {investment_name}"

        elif data_type == 'dividends':
            # Call import function for dividends
            import_csv_data(temp_file_name, data_type, investment_name)
            message = f"Dividends data imported successfully for {investment_name}"

        elif data_type == 'fees':
            # Call import function for fees
            import_csv_data(temp_file_name, data_type, investment_name)
            message = f"Fees data imported successfully for {investment_name}"

        elif data_type == 'tax':
            # Call import function for tax
            import_csv_data(temp_file_name, data_type, investment_name)
            message = f"Tax data imported successfully for {investment_name}"

        elif data_type == 'inflation':
            # Inflation data doesn't have investment_id, so we handle it differently
            import_inflation_csv_data(temp_file_name)
            message = "Inflation data imported successfully"

        # Clean up the temporary file
        try:
            import os
            os.remove(temp_file_name)
        except:
            pass  # Ignore cleanup errors

        return {"message": message, "data_type": data_type, "investment_name": investment_name if data_type != 'inflation' else None}

    except Exception as e:
        # Clean up temporary file on error
        try:
            import os
            os.remove(f"temp_{data_type}.csv")
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))



@investment_api.post("/invalidate_cache/{database_name}")
async def invalidate_cache(database_name: str = None):
    """Invalidate all cached data for the given database."""
    global _cache_data, _cache_expiry

    if database_name:
        # Invalidate only cache entries for this database
        keys_to_remove = []
        for key in _cache_data.keys():
            if f"database.{database_name}" in key or f"'database': '{database_name}'" in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            if key in _cache_data:
                del _cache_data[key]
            if key in _cache_expiry:
                del _cache_expiry[key]
    else:
        # Clear all cache
        _cache_data.clear()
        _cache_expiry.clear()

    return {
        "message": f"Cache invalidated for {database_name if database_name else 'all databases'}",
        "timestamp": datetime.now().isoformat()
    }

@investment_api.get("/investment_names")
async def get_investment_names():
    """Get list of investment names for dropdowns."""
    try:
        with get_db_connection(DEFAULT_DB) as (conn, cursor):
            cursor.execute("SELECT DISTINCT investment_name FROM investments ORDER BY investment_name")
            names = [row[0] for row in cursor.fetchall()]
            return {"investment_names": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch investment names: {str(e)}")

@investment_api.get("/edit_data/tables/{database_name}")
async def get_tables_list(database_name: str):
    """Get list of tables available for editing."""
    try:
        tables = get_edit_data_tables(database_name)
        return Response(
            json.dumps({"tables": tables}),
            media_type="application/json"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tables list: {str(e)}")

@investment_api.get("/investment_predictions/{database_name}")
async def get_investment_predictions(database_name: str, scope: str = "portfolio", model_filter: str = None):
    """
    Get comprehensive investment price predictions with confidence intervals.
    Supports multiple prediction models: ARIMA, LSTM, XGBoost, Hybrid, Gaussian Process.
    """
    try:
        # Parse model filter if provided
        models_to_run = None
        if model_filter:
            models_to_run = [m.strip() for m in model_filter.split(',') if m.strip()]

        # Get predictions
        predictions_result = generate_predictions(database_name, scope, models_to_run)

        return Response(
            json.dumps(predictions_result),
            media_type="application/json",
            headers={"X-Cache": "MISS"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate investment predictions: {str(e)}")

@investment_api.get("/health")
async def health_check():
    """Health check endpoint to verify API is responsive."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_entries": len(_cache_data),
        "uptime_seconds": (datetime.now() - _APP_START_TIME).total_seconds()
    }

@investment_api.get("/config/{database_name}")
async def config_get(database_name: str = "Investments"):
    """Return all editable configuration settings from the configuration table."""
    try:
        config = get_all_config(database_name)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch config: {str(e)}")


@investment_api.put("/config/{database_name}")
async def config_update(request: Request, database_name: str = "Investments"):
    """Update one or more configuration settings.

    Body: {"setting_key": "new_value", ...}. Invalidates the in-memory cache.
    """
    try:
        body = await request.json()
        if not isinstance(body, dict) or not body:
            raise HTTPException(status_code=400, detail="Request body must be a non-empty JSON object of {setting_key: value}")

        with get_db_connection(database_name) as (conn, cursor):
            for key, value in body.items():
                cursor.execute(
                    "UPDATE configuration SET setting_value = %s, updated_at = CURRENT_TIMESTAMP WHERE setting_key = %s",
                    (str(value), key)
                )
            conn.commit()

        invalidate_config_cache(database_name)
        return {"message": f"Updated {len(body)} configuration setting(s)", "updated": list(body.keys())}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


@investment_api.get("/edit_data/table/{database_name}/{table_name}")
async def get_table_data(database_name: str, table_name: str, skip: int = 0, limit: int = 100, search: str = None):
    """Get data from a specific table with optional filtering and pagination."""
    try:
        table_data = get_edit_data_table(database_name, table_name, skip, limit, search)
        return Response(json.dumps(table_data), media_type="application/json")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch table data: {str(e)}")

@investment_api.put("/edit_data/table/{database_name}/{table_name}")
async def update_table_data(database_name: str, table_name: str, update_data: dict):
    """Update data in a specific table."""
    try:
        result = update_edit_data_table(database_name, table_name, update_data)
        # Clear cache since data changed
        await invalidate_cache(database_name)
        return {"message": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update table data: {str(e)}")

@investment_api.post("/edit_data/table/{database_name}/{table_name}")
async def add_table_row(database_name: str, table_name: str, row_data: dict):
    """Add a new row to a specific table."""
    try:
        result = add_edit_data_row(database_name, table_name, row_data)
        # Clear cache since data changed
        await invalidate_cache(database_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add row to table data: {str(e)}")

@investment_api.delete("/edit_data/table/{database_name}/{table_name}/{record_id}")
async def delete_table_row(database_name: str, table_name: str, record_id: int, cascade: bool = False):
    """Delete a row from a specific table."""
    try:
        result = delete_edit_data_row(database_name, table_name, record_id, cascade=cascade)
        # Clear cache since data changed
        await invalidate_cache(database_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle foreign key constraint violations
        error_msg = str(e).lower()
        if 'foreign key constraint' in error_msg or 'foreign key' in error_msg:
            raise HTTPException(status_code=400, detail=f"Cannot delete record: it is referenced by other data. Set cascade=true to delete related records as well.")
        elif 'violates' in error_msg and 'constrain' in error_msg:
            raise HTTPException(status_code=400, detail=f"Cannot delete record: it violates database constraints. Record may be required for data integrity.")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete row from table data: {str(e)}")

@investment_api.post("/refresh_data/{database_name}")
async def refresh_data(database_name: str, background_tasks: BackgroundTasks):
    """
    Trigger background refresh of cached data.
    Useful when underlying data has been updated.
    """
    # Clear cache for this database
    await invalidate_cache(database_name)

    # Optionally trigger background data refresh tasks here
    # For now, just return confirmation that cache was invalidated

    return {
        "message": f"Data refresh initiated for {database_name}",
        "cache_invalidated": True,
        "timestamp": datetime.now().isoformat()
    }

@investment_api.get("/dashboard_charts/{database_name}")
async def get_dashboard_charts(database_name: str, base_currency: str = "ZAR",
                              filter_type: str = None, filter_value: str = None):
    """
    Get pre-processed chart data for frontend - all aggregations done server-side.
    Returns ready-to-use pie chart data and aggregated tables.
    """

    # Blue-themed color palettes for charts
    BLUE_COLORS = [
        '#007FFF',  # Main blue
        '#5090D3',  # Medium blue
        '#3399FF',  # Bright blue
        '#1E4976',  # Dark blue
        '#66B2FF',  # Light blue
        '#004C99',  # Deep blue
        '#0F52BA',  # Dodger blue
        '#1E90FF',  # Slate blue
        '#4169E1',  # Royal blue
        '#00BFFF',  # Deep sky blue
    ]

    AREA_CHART_COLORS = [
        '#007FFF',  # Main blue
        '#5090D3',  # Medium blue
        '#3399FF',  # Bright blue
        '#66B2FF',  # Light blue
        '#1E90FF',  # Slate blue
    ]

    def getBlueColor(index: int, opacity: str = "") -> str:
        """Get a blue-themed color, cycling through the palette."""
        color = BLUE_COLORS[index % len(BLUE_COLORS)]
        return color + opacity  # Add opacity if provided

    def getBlueColorForAreaChart(index: int) -> str:
        """Get a blue-themed color for area charts."""
        return AREA_CHART_COLORS[index % len(AREA_CHART_COLORS)]

    cache_key = f"charts:{database_name}:{base_currency}"

    # Check cache first
    cached_data = _get_cached_data(cache_key)
    if cached_data:
        return Response(
            json.dumps(cached_data),
            media_type="application/json",
            headers={"X-Cache": "HIT"}
        )

    try:
        # Get raw investment summary data (for currency pie chart in original currencies)
        raw_summary_df = get_investment_summary(database_name=database_name)

        # Get currency-converted summary data (for most charts/tables)
        summary_df = get_investment_summary_display(
            base_currency=base_currency,
            database_name=database_name
        )

        # Get investment data for line chart timeseries (include in single response)
        timeseries_df = get_investment_data(
            base_currency=base_currency,
            database_name=database_name
        )

        # Apply filtering if filter parameters are provided
        # IMPORTANT: Filter summary data but use same investment names for timeseries
        # even if some investments don't have historical data
        if filter_type and filter_value:
            filtered_investment_names = None

            if filter_type == "investment_type":
                filtered_summary = raw_summary_df[raw_summary_df["investment_type"] == filter_value]
                filtered_investment_names = filtered_summary["investment_name"].tolist()
                raw_summary_df = filtered_summary
                summary_df = summary_df[summary_df["investment_type"] == filter_value]
            elif filter_type == "unit_currency":
                filtered_summary = raw_summary_df[raw_summary_df["unit_currency"] == filter_value]
                filtered_investment_names = filtered_summary["investment_name"].tolist()
                raw_summary_df = filtered_summary
                summary_df = summary_df[summary_df["unit_currency"] == filter_value]
            elif filter_type == "institution_name":
                filtered_summary = raw_summary_df[raw_summary_df["institution_name"] == filter_value]
                filtered_investment_names = filtered_summary["investment_name"].tolist()
                raw_summary_df = filtered_summary
                summary_df = summary_df[summary_df["institution_name"] == filter_value]

            # Filter timeseries data but allow missing investments (they'll just have empty graphs)
            if filtered_investment_names:
                timeseries_df = timeseries_df[timeseries_df["investment_name"].isin(filtered_investment_names)]
                print(f"Filtered data by {filter_type}: {filter_value} - {len(summary_df)} summary records, {len(timeseries_df)} timeseries records for {len(set(filtered_investment_names))} investments")
            else:
                print(f"Filtered data by {filter_type}: {filter_value} - {len(summary_df)} records remaining")

        # Process timeseries data for line charts (pre-process colors server-side)
        processed_timeseries = []
        if not timeseries_df.empty:
            for investment_index, investment in enumerate(timeseries_df["investment_name"].unique()):
                inv_data = timeseries_df[timeseries_df["investment_name"] == investment].copy()
                inv_data = inv_data.sort_values("unit_price_date")

                points = []
                for _, row in inv_data.iterrows():
                    point = {
                        "x": row["unit_price_date"].isoformat() if hasattr(row["unit_price_date"], 'isoformat') else str(row["unit_price_date"]),
                        "y": float(row["investment_value"]) if not pd.isna(row["investment_value"]) else 0.0
                    }
                    points.append(point)

                processed_timeseries.append({
                    "label": investment,
                    "data": points,
                    "borderColour": getBlueColor(investment_index)  # Assign blue colors server-side
                })

            # Set date range
            min_date = timeseries_df["unit_price_date"].min()
            max_date = timeseries_df["unit_price_date"].max()

            timeseries_date_range = {
                "min": min_date.isoformat() if hasattr(min_date, 'isoformat') else str(min_date),
                "max": max_date.isoformat() if hasattr(max_date, 'isoformat') else str(max_date)
            }
        else:
            processed_timeseries = []
            timeseries_date_range = {"min": None, "max": None}



        if summary_df.empty:
            empty_response = {
                "individual_pie": {"labels": [], "datasets": []},
                "type_pie": {"labels": [], "datasets": []},
                "currency_pie": {"labels": [], "datasets": []},
                "institution_pie": {"labels": [], "datasets": []},
                "type_table": [],
                "currency_table": [],
                "institution_table": [],
                "base_currency": base_currency,
                "timestamp": datetime.now().isoformat()
            }
            _set_cache_data(cache_key, empty_response)
            return Response(
                json.dumps(empty_response),
                media_type="application/json",
                headers={"X-Cache": "MISS"}
            )

        # Process data with conditional logic based on filter type
        # Always generate individual investment pie chart (filtered data)
        individual_values = summary_df["investment_value"].fillna(0)
        total_individual = individual_values.sum()

        individual_pie = {
            "labels": summary_df["investment_name"].tolist(),
            "datasets": [{
                "data": [(val / total_individual * 100) if total_individual > 0 else 0 for val in individual_values],
                "backgroundColor": [getBlueColor(i) for i in range(len(summary_df))],
            }]
        }

        # Helper function to safely aggregate dates and handle nulls
        def safe_date_agg(dates):
            valid_dates = pd.to_datetime(dates, errors='coerce')
            if valid_dates.notna().any():
                return valid_dates.min().strftime('%d/%m/%Y')
            else:
                return "N/A"

        # Initialize variables - will be conditionally populated
        type_pie = {"labels": [], "datasets": []}
        type_table = []
        currency_pie = {"labels": [], "datasets": []}
        currency_table = []
        institution_pie = {"labels": [], "datasets": []}
        institution_table = []

        # Generate different charts based on filter type - DO NOT show the same type we're filtering by
        if not filter_type or filter_type != "investment_type":
            # Always show type breakdowns unless we're already filtering by type
            type_groups = summary_df.groupby("investment_type").agg({
                "investment_value": "sum"
            }).reset_index()

            type_dates = []
            for inv_type in type_groups["investment_type"]:
                type_dates.append(safe_date_agg(
                    summary_df[summary_df["investment_type"] == inv_type]["initial_investment_date"]
                ))
            type_groups["initial_investment_date"] = type_dates

            type_values = type_groups["investment_value"]
            total_type = type_values.sum()

            type_pie = {
                "labels": type_groups["investment_type"].tolist(),
                "datasets": [{
                    "data": [(val / total_type * 100) if total_type > 0 else 0 for val in type_values],
                    "backgroundColor": [getBlueColor(i) for i in range(len(type_groups))],
                }]
            }

            type_table = []
            for i, (_, row) in enumerate(type_groups.iterrows()):
                type_table.append({
                    "id": i,
                    "investment_type": row["investment_type"],
                    "investment_value_in_native_currency": round(row["investment_value"], 2),
                    "initial_investment_date": row["initial_investment_date"]
                })

        if not filter_type or filter_type != "unit_currency":
            # Always show currency breakdowns unless we're already filtering by currency
            raw_currency_groups = raw_summary_df.groupby("unit_currency").agg({
                "investment_value": "sum"
            }).reset_index()

            raw_currency_values = raw_currency_groups["investment_value"]
            total_raw_currency = raw_currency_values.sum()

            currency_pie = {
                "labels": raw_currency_groups["unit_currency"].tolist(),
                "datasets": [{
                    "data": [(val / total_raw_currency * 100) if total_raw_currency > 0 else 0 for val in raw_currency_values],
                    "backgroundColor": [getBlueColor(i) for i in range(len(raw_currency_groups))],
                }]
            }

            raw_currency_dates = []
            for currency in raw_currency_groups["unit_currency"]:
                raw_currency_dates.append(safe_date_agg(
                    raw_summary_df[raw_summary_df["unit_currency"] == currency]["initial_investment_date"]
                ))
            raw_currency_groups["initial_investment_date"] = raw_currency_dates

            currency_table = []
            for i, (_, row) in enumerate(raw_currency_groups.iterrows()):
                currency_table.append({
                    "id": i,
                    "unit_currency": row["unit_currency"],
                    "investment_value_in_native_currency": round(row["investment_value"], 2),
                    "initial_investment_date": row["initial_investment_date"]
                })

        if not filter_type or filter_type != "institution_name":
            # Always show institution breakdowns unless we're already filtering by institution
            institution_groups = summary_df.groupby("institution_name").agg({
                "investment_value": "sum"
            }).reset_index()

            institution_dates = []
            for institution in institution_groups["institution_name"]:
                institution_dates.append(safe_date_agg(
                    summary_df[summary_df["institution_name"] == institution]["initial_investment_date"]
                ))
            institution_groups["initial_investment_date"] = institution_dates

            institution_values = institution_groups["investment_value"]
            total_institution = institution_values.sum()

            institution_pie = {
                "labels": institution_groups["institution_name"].tolist(),
                "datasets": [{
                    "data": [(val / total_institution * 100) if total_institution > 0 else 0 for val in institution_values],
                    "backgroundColor": [getBlueColor(i) for i in range(len(institution_groups))],
                    }]
            }

            institution_table = []
            for i, (_, row) in enumerate(institution_groups.iterrows()):
                institution_table.append({
                    "id": i,
                    "institution_name": row["institution_name"],
                    "investment_value_in_native_currency": round(row["investment_value"], 2),
                    "initial_investment_date": row["initial_investment_date"]
                })

        # Format the summary table for frontend (safe date handling)
        summary_table = []
        for _, row in summary_df.iterrows():
            investment_date = row.get("initial_investment_date", "")
            formatted_date = ""
            if pd.notna(investment_date) and investment_date:
                try:
                    parsed_date = pd.to_datetime(investment_date, errors='coerce')
                    if pd.notna(parsed_date):
                        formatted_date = parsed_date.strftime('%d/%m/%Y')
                except Exception:
                    formatted_date = str(investment_date)

            summary_table.append({
                "id": int(row["id"]),
                "investment_name": row["investment_name"],
                "investment_type": row["investment_type"],
                "unit_currency": row.get("unit_currency", base_currency),
                "investment_value_in_native_currency": round(row.get("investment_value", 0), 2),
                "unit_price_in_native_currency": round(row.get("unit_price", 0), 2),
                "total_units_held": float(row["total_units_held"]),
                "initial_unit_price_in_native_currency": round(row.get("initial_unit_price", 0), 2),
                "initial_investment_date": formatted_date
            })

        # Generate key metrics for portfolio dashboard tiles
        # Calculate total contributions from actual buy transaction data in the database
        try:
            with get_db_connection(database_name) as (conn, cursor):
                cursor.execute("SELECT COALESCE(SUM(transaction_amount), 0) FROM transactions WHERE LOWER(transaction_type) = 'buy'")
                total_contributions = float(cursor.fetchone()[0])
                if total_contributions == 0:
                    # Fallback: use fallback estimate
                    total_contributions = float(summary_df["investment_value"].sum()) / FALLBACK_CONTRIBUTION_DIVISOR
        except Exception:
            total_contributions = float(summary_df["investment_value"].sum()) / FALLBACK_CONTRIBUTION_DIVISOR

        # Calculate investment time from earliest real investment (exclude forex entries with 0 units)
        try:
            with get_db_connection(database_name) as (conn, cursor):
                cursor.execute("SELECT MIN(initial_investment_date) FROM investments WHERE number_of_units_held > 0")
                result = cursor.fetchone()
                if result and result[0]:
                    from modules.metrics import fractional_years_between
                    earliest_investment = pd.Timestamp(result[0])
                    total_investment_time = max(fractional_years_between(earliest_investment, pd.Timestamp.now()), 0.1)
                else:
                    total_investment_time = FALLBACK_INVESTMENT_TIME_YEARS
        except Exception:
            total_investment_time = FALLBACK_INVESTMENT_TIME_YEARS

        # Calculate actual IRR from transaction data (cash flows)
        try:
            from modules.metrics import calculate_portfolio_irr
            irr_result = calculate_portfolio_irr(database_name)
            if irr_result and "whole_portfolio" in irr_result and irr_result["whole_portfolio"]["irr"] is not None:
                portfolio_irr = round(irr_result["whole_portfolio"]["irr"] * 100, 2)
            else:
                portfolio_irr = FALLBACK_PORTFOLIO_IRR
        except Exception:
            portfolio_irr = FALLBACK_PORTFOLIO_IRR

        key_metrics = [
            {
                "metric": "IRR",
                "value": portfolio_irr,
                "unit": "%",
                "formatted_value": f"{portfolio_irr:.1f}%"
            },
            {
                "metric": "Total Net Worth",
                "value": round(total_individual, 2),
                "unit": base_currency,
                "formatted_value": f"{base_currency} {round(total_individual, 2):,.2f}"
            },
            {
                "metric": "Total Contributions",
                "value": round(total_contributions, 2),
                "unit": base_currency,
                "formatted_value": f"{base_currency} {round(total_contributions, 2):,.2f}"
            },
            {
                "metric": "Total Investment Time",
                "value": round(total_investment_time, 2),
                "unit": "years",
                "formatted_value": f"{round(total_investment_time, 2)} years"
            }
        ]

        # Generate additional chart types before summary construction
        bar_charts = []
        area_charts = []

        # 1. Bar chart: Portfolio allocation by investment type (horizontal bar)
        if not type_groups.empty:
            type_allocation_data = pd.DataFrame({
                'type': type_groups["investment_type"],
                'value': type_groups["investment_value"],
                'percentage': [(val / total_type * 100) if total_type > 0 else 0 for val in type_groups["investment_value"]]
            })

            bar_charts.append({
                "title": "Portfolio Allocation by Type",
                "type": "horizontalBar",
                "data": {
                    "labels": type_allocation_data["type"].tolist(),
                    "datasets": [{
                        "label": "Investment Value",
                        "data": type_allocation_data["value"].round(2).tolist(),
                        "backgroundColor": [getBlueColor(i) for i in range(len(type_allocation_data))],
                    }]
                }
            })

        # 2. Bar chart: Portfolio allocation by currency
        if not raw_currency_groups.empty:
            currency_allocation_data = pd.DataFrame({
                'currency': raw_currency_groups["unit_currency"],
                'value': raw_currency_groups["investment_value"],
                'percentage': [(val / total_raw_currency * 100) if total_raw_currency > 0 else 0 for val in raw_currency_groups["investment_value"]]
            })

            bar_charts.append({
                "title": "Portfolio Allocation by Currency",
                "type": "verticalBar",
                "data": {
                    "labels": currency_allocation_data["currency"].tolist(),
                    "datasets": [{
                        "label": "Investment Value",
                        "data": currency_allocation_data["value"].round(2).tolist(),
                        "backgroundColor": [getBlueColor(i) for i in range(len(currency_allocation_data))],
                    }]
                }
            })

        # 3. Bar chart: Top 10 investments by value
        top_10_investments = summary_df.nlargest(10, "investment_value")
        if not top_10_investments.empty:
            bar_charts.append({
                "title": "Top 10 Investments by Value",
                "type": "verticalBar",
                "data": {
                    "labels": [inv[:15] + "..." if len(inv) > 15 else inv for inv in top_10_investments["investment_name"].tolist()],
                    "datasets": [{
                        "label": "Investment Value",
                        "data": top_10_investments["investment_value"].round(2).tolist(),
                        "backgroundColor": [getBlueColor(i) for i in range(len(top_10_investments))],
                    }]
                }
            })

        # 4. Area chart: Cumulative portfolio value over time (stacked area)
        try:
            # Get last AREA_CHART_DAYS of data for area chart
            area_timeseries_df = timeseries_df.copy()
            if not area_timeseries_df.empty:
                # Keep only last AREA_CHART_DAYS if there are more
                area_timeseries_df['unit_price_date'] = pd.to_datetime(area_timeseries_df['unit_price_date'])
                last_period_days = area_timeseries_df['unit_price_date'].max() - pd.Timedelta(days=AREA_CHART_DAYS)
                area_timeseries_df = area_timeseries_df[area_timeseries_df['unit_price_date'] >= last_period_days]

                # Group and pivot for stacked area
                area_grouped = area_timeseries_df.groupby(['unit_price_date', 'investment_name'])['investment_value'].sum().reset_index()
                area_pivot = area_grouped.pivot(index='unit_price_date', columns='investment_name', values='investment_value').fillna(0)

                # Take top AREA_CHART_TOP_N for clarity
                top_investments = area_pivot.sum().nlargest(AREA_CHART_TOP_N).index.tolist()
                area_pivot = area_pivot[top_investments]

                # Prepare area chart data
                area_datasets = []
                for i, col in enumerate(area_pivot.columns):
                    color = getBlueColorForAreaChart(i)
                    area_datasets.append({
                        "label": col,
                        "data": [{"x": area_pivot.index[j].strftime('%Y-%m-%d'), "y": float(area_pivot.iloc[j, i])} for j in range(len(area_pivot))],
                        "fill": True,
                        "backgroundColor": color + '40',  # Add transparency
                        "borderColor": color,
                        "pointRadius": 0
                    })

                area_charts.append({
                    "title": f"Portfolio Value Over Time (Top {AREA_CHART_TOP_N} Investments)",
                    "data": {
                        "datasets": area_datasets
                    }
                })
        except Exception as e:
            print(f"Warning: Could not generate area chart: {e}")
            area_charts = []

        # Generate dynamic menu items based on actual portfolio data
        # Only show what's actually in their portfolio
        unique_types = get_investment_types_in_portfolio(database_name) if 'get_investment_types_in_portfolio' in globals() else type_groups["investment_type"].unique().tolist()
        unique_currencies = get_currencies_in_portfolio(database_name) if 'get_currencies_in_portfolio' in globals() else raw_currency_groups["unit_currency"].unique().tolist()
        institution_names = institution_groups["institution_name"].unique().tolist()

        menu_items = [
            {
                "heading": "Investment Type",
                "items": type_groups["investment_type"].tolist(),
                "urls": [f"/Investments/InvestmentsType/{item.replace(' ', '%20')}" for item in type_groups["investment_type"].tolist()]
            },
            {
                "heading": "Investment Currency",
                "items": raw_currency_groups["unit_currency"].tolist(),  # Match the currency table
                "urls": [f"/Investments/InvestmentsCurrency/{item.replace(' ', '%20')}" for item in raw_currency_groups["unit_currency"].tolist()]
            },
            {
                "heading": "Institution",
                "items": institution_groups["institution_name"].head(10).tolist(),  # Show more institutions
                "urls": [f"/Investments/InvestmentsInstitution/{item.replace(' ', '%20')}" for item in institution_groups["institution_name"].head(10).tolist()]
            }
        ]

        result = {
            "individual_pie": individual_pie,
            "type_pie": type_pie,
            "currency_pie": currency_pie,
            "institution_pie": institution_pie,
            "type_table": type_table,
            "currency_table": currency_table,
            "institution_table": institution_table,
            "summary_table": summary_table,
            "timeseries": processed_timeseries,  # Include line chart data in single response
            "timeseries_date_range": timeseries_date_range,  # Include date range
            "bar_charts": bar_charts,  # New bar chart data
            "area_charts": area_charts,  # New area chart data
            "key_metrics": key_metrics,  # Key portfolio metrics tiles
            "menu_items": menu_items,
            "base_currency": base_currency,
            "total_portfolio_value": round(total_individual, 2),
            "timestamp": datetime.now().isoformat(),
            "cache_expires_in": CACHE_TIMEOUT
        }

        # Cache the result
        _set_cache_data(cache_key, result)

        return Response(
            json.dumps(result),
            media_type="application/json",
            headers={"X-Cache": "MISS"}
        )

    except Exception as e:
        # Provide detailed error information for debugging
        error_details = f"Dashboard chart generation failed: {str(e)}"
        print(f"ERROR: {error_details}")  # Log to server console
        raise HTTPException(status_code=500, detail=error_details)


# ─────────────────────────────────────────────────────────────────────────────
# Property Investment Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@investment_api.post("/property/calculate")
async def property_calculate(request: Request, database_name: str = "Investments"):
    """Calculate property investment analysis."""
    try:
        body = await request.json()
        result = run_property_projection(
            purchase_price=float(body.get("purchase_price", 0)),
            transfer_costs=float(body.get("transfer_costs", 0)),
            transfer_duty=float(body.get("transfer_duty", -1)),
            bond_registration_costs=float(body.get("bond_registration_costs", 0)),
            other_acquisition_costs=float(body.get("other_acquisition_costs", 0)),
            deposit_amount=float(body.get("deposit_amount", 0)),
            bond_interest_rate=float(body.get("bond_interest_rate", DEFAULT_BOND_INTEREST_RATE)),
            bond_term_years=int(body.get("bond_term_years", 20)),
            monthly_levy=float(body.get("monthly_levy", 0)),
            monthly_rates=float(body.get("monthly_rates", 0)),
            monthly_insurance=float(body.get("monthly_insurance", 0)),
            monthly_maintenance_reserve=float(body.get("monthly_maintenance_reserve", 0)),
            monthly_management_fee_pct=float(body.get("monthly_management_fee_pct", 0)),
            monthly_other_costs=float(body.get("monthly_other_costs", 0)),
            monthly_rental_income=float(body.get("monthly_rental_income", 0)),
            rental_growth_rate_pa=float(body.get("rental_growth_rate_pa", 0)),
            vacancy_rate_pct=float(body.get("vacancy_rate_pct", 0)),
            property_growth_rate_pa=float(body.get("property_growth_rate_pa", 0)),
            inflation_rate=float(body.get("inflation_rate", 0)),
            projection_years=int(body.get("projection_years", 20)),
            cgt_inclusion_rate=float(body.get("cgt_inclusion_rate", 0.40)),
            cgt_marginal_tax_rate=float(body.get("cgt_marginal_tax_rate", 0.45)),
            is_primary_residence=bool(body.get("is_primary_residence", False))
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Property calculation failed: {str(e)}")


@investment_api.post("/property/monte_carlo")
async def property_monte_carlo(request: Request, database_name: str = "Investments"):
    """Run Monte Carlo simulation for property investment."""
    try:
        body = await request.json()
        base_inputs = {
            "purchase_price": float(body.get("purchase_price", 1500000)),
            "transfer_costs": float(body.get("transfer_costs", 0)),
            "transfer_duty": float(body.get("transfer_duty", -1)),
            "bond_registration_costs": float(body.get("bond_registration_costs", 0)),
            "other_acquisition_costs": float(body.get("other_acquisition_costs", 0)),
            "deposit_amount": float(body.get("deposit_amount", 150000)),
            "bond_interest_rate": float(body.get("bond_interest_rate", DEFAULT_BOND_INTEREST_RATE)),
            "bond_term_years": int(body.get("bond_term_years", 20)),
            "monthly_levy": float(body.get("monthly_levy", 1500)),
            "monthly_rates": float(body.get("monthly_rates", 800)),
            "monthly_insurance": float(body.get("monthly_insurance", 400)),
            "monthly_maintenance_reserve": float(body.get("monthly_maintenance_reserve", 500)),
            "monthly_management_fee_pct": float(body.get("monthly_management_fee_pct", 8)),
            "monthly_other_costs": float(body.get("monthly_other_costs", 0)),
            "monthly_rental_income": float(body.get("monthly_rental_income", 12000)),
            "rental_growth_rate_pa": float(body.get("rental_growth_rate_pa", DEFAULT_RENTAL_GROWTH_RATE)),
            "vacancy_rate_pct": float(body.get("vacancy_rate_pct", DEFAULT_VACANCY_RATE)),
            "property_growth_rate_pa": float(body.get("property_growth_rate_pa", DEFAULT_PROPERTY_GROWTH_RATE)),
            "inflation_rate": float(body.get("inflation_rate", DEFAULT_INFLATION_RATE)),
            "projection_years": int(body.get("projection_years", 20)),
            "cgt_inclusion_rate": float(body.get("cgt_inclusion_rate", 0.40)),
            "cgt_marginal_tax_rate": float(body.get("cgt_marginal_tax_rate", 0.45)),
            "is_primary_residence": bool(body.get("is_primary_residence", False))
        }
        result = run_property_monte_carlo(
            base_inputs=base_inputs,
            num_simulations=int(body.get("num_simulations", 1000)),
            time_horizon_years=int(body.get("time_horizon_years", 20))
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monte Carlo failed: {str(e)}")


@investment_api.post("/property/sensitivity")
async def property_sensitivity(request: Request, database_name: str = "Investments"):
    """Run sensitivity analysis for property investment."""
    try:
        body = await request.json()
        base_inputs = {
            "purchase_price": float(body.get("purchase_price", 1500000)),
            "transfer_costs": float(body.get("transfer_costs", 0)),
            "transfer_duty": float(body.get("transfer_duty", -1)),
            "bond_registration_costs": float(body.get("bond_registration_costs", 0)),
            "other_acquisition_costs": float(body.get("other_acquisition_costs", 0)),
            "deposit_amount": float(body.get("deposit_amount", 150000)),
            "bond_interest_rate": float(body.get("bond_interest_rate", DEFAULT_BOND_INTEREST_RATE)),
            "bond_term_years": int(body.get("bond_term_years", 20)),
            "monthly_levy": float(body.get("monthly_levy", 1500)),
            "monthly_rates": float(body.get("monthly_rates", 800)),
            "monthly_insurance": float(body.get("monthly_insurance", 400)),
            "monthly_maintenance_reserve": float(body.get("monthly_maintenance_reserve", 500)),
            "monthly_management_fee_pct": float(body.get("monthly_management_fee_pct", 8)),
            "monthly_other_costs": float(body.get("monthly_other_costs", 0)),
            "monthly_rental_income": float(body.get("monthly_rental_income", 12000)),
            "rental_growth_rate_pa": float(body.get("rental_growth_rate_pa", DEFAULT_RENTAL_GROWTH_RATE)),
            "vacancy_rate_pct": float(body.get("vacancy_rate_pct", DEFAULT_VACANCY_RATE)),
            "property_growth_rate_pa": float(body.get("property_growth_rate_pa", DEFAULT_PROPERTY_GROWTH_RATE)),
            "inflation_rate": float(body.get("inflation_rate", DEFAULT_INFLATION_RATE)),
            "projection_years": int(body.get("projection_years", 20)),
            "cgt_inclusion_rate": float(body.get("cgt_inclusion_rate", 0.40)),
            "cgt_marginal_tax_rate": float(body.get("cgt_marginal_tax_rate", 0.45)),
            "is_primary_residence": bool(body.get("is_primary_residence", False))
        }
        result = run_sensitivity_analysis(base_inputs)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sensitivity analysis failed: {str(e)}")


@investment_api.post("/property/scrape")
async def property_scrape(request: Request):
    """Scrape a property listing URL to extract details."""
    try:
        body = await request.json()
        url = body.get("url", "")
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        result = scrape_property_url(url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Property scrape failed: {str(e)}")


@investment_api.post("/property/report")
async def property_report(request: Request, database_name: str = "Investments"):
    """Generate a PDF report for property analysis."""
    try:
        body = await request.json()
        output_file = body.get("output_file")
        if not output_file:
            output_file = tempfile.mktemp(suffix=".pdf")
        result_path = generate_property_pdf_report(body, output_file)
        return FileResponse(
            result_path,
            media_type="application/pdf",
            filename=os.path.basename(result_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF report generation failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Factsheet Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@investment_api.get("/factsheets/Investments/list")
async def factsheet_list(database_name: str = "Investments"):
    """Get list of investments with factsheet metadata."""
    try:
        with get_db_connection(database_name) as (conn, cursor):
            cursor.execute("""
                SELECT i.id, i.investment_name, i.institution_name,
                       COUNT(f.id) as factsheet_count,
                       MAX(f.factsheet_date) as latest_factsheet_date
                FROM investments i
                LEFT JOIN factsheets f ON f.investment_id = i.id
                GROUP BY i.id, i.investment_name, i.institution_name
                ORDER BY i.investment_name
            """)
            cols = [d[0] for d in cursor.description]
            results = [dict(zip(cols, row)) for row in cursor.fetchall()]
            for r in results:
                if r['latest_factsheet_date']:
                    r['latest_factsheet_date'] = r['latest_factsheet_date'].isoformat()
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch factsheet list: {str(e)}")


@investment_api.get("/factsheets/Investments/{investment_id}")
async def factsheet_get(database_name: str = "Investments", investment_id: int = None, year: str = None, month: str = None):
    """Get factsheets for a specific investment."""
    try:
        year_int = int(year) if year and year != 'All' else None
        month_int = int(month) if month and month != 'All' else None
        factsheets = get_factsheets_for_investment(investment_id, database_name, year_int, month_int)
        return factsheets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch factsheets: {str(e)}")


@investment_api.get("/factsheets/Investments/{investment_id}/{year}/{month}")
async def factsheet_serve(database_name: str = "Investments", investment_id: int = None, year: int = None, month: int = None):
    """Serve a factsheet PDF file."""
    try:
        file_path = get_factsheet_path(investment_id, year, month, "MDD")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Factsheet not found")
        return FileResponse(file_path, media_type="application/pdf", filename=os.path.basename(file_path))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve factsheet: {str(e)}")


@investment_api.post("/factsheets/Investments/download/{investment_id}")
async def factsheet_download(database_name: str = "Investments", investment_id: int = None):
    """Download the latest factsheet for an investment."""
    try:
        with get_db_connection(database_name) as (conn, cursor):
            cursor.execute("SELECT investment_name, institution_name FROM investments WHERE id = %s", (investment_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Investment not found")
            inv_name, inst_name = row
        res = download_factsheet(investment_id, inv_name, inst_name, database_name)
        return {"details": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download factsheet: {str(e)}")


@investment_api.post("/factsheets/Investments/download_all")
async def factsheet_download_all(database_name: str = "Investments", background_tasks: BackgroundTasks = None):
    """Trigger bulk factsheet download for all investments."""
    try:
        if background_tasks:
            background_tasks.add_task(run_monthly_factsheet_downloader, database_name)
            return {"message": "Bulk factsheet download started in background"}
        else:
            res = run_monthly_factsheet_downloader(database_name)
            return {"message": "Bulk download complete", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger bulk download: {str(e)}")


@investment_api.get("/investment_metrics_by_name/{database_name}/{investment_name}")
async def get_investment_metrics_by_name(database_name: str, investment_name: str):
    """Get metrics for a specific investment by name."""
    try:
        from investment_database_functions import get_investment_metrics_by_name_api
        return get_investment_metrics_by_name_api(database_name, investment_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch investment metrics by name: {str(e)}")


@investment_api.post("/maintenance/recalculate_metrics")
async def maintenance_recalculate_metrics(database_name: str = "Investments"):
    """Trigger recalculation of all investment and portfolio metrics."""
    try:
        from modules.metrics import recalculate_investment_metrics_history
        from modules.portfolio_metrics import calculate_and_store_portfolio_metrics
        recalculate_investment_metrics_history(database_name)
        count = calculate_and_store_portfolio_metrics(database_name)
        return {"message": f"Metrics recalculation completed successfully ({count} portfolio rows stored)", "database": database_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics recalculation failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# IRR Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@investment_api.get("/irr/Investments")
async def get_irr(database_name: str = "Investments", base_currency: str = "ZAR"):
    """Get IRR analysis across all dimensions."""
    try:
        from modules.metrics import calculate_portfolio_irr
        result = calculate_portfolio_irr(database_name, base_currency)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate IRR: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Monte Carlo Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@investment_api.post("/monte_carlo/Investments")
async def run_monte_carlo(request: Request, database_name: str = "Investments"):
    """Run Monte Carlo simulation for portfolio."""
    try:
        body = await request.json()
        dimension_type = body.get("dimension_type", "portfolio")
        dimension_value = body.get("dimension_value", "All")
        years = int(body.get("years", 10))
        num_simulations = int(body.get("num_simulations", 1000))
        
        from modules.monte_carlo import run_portfolio_monte_carlo
        result = run_portfolio_monte_carlo(database_name, dimension_type, dimension_value, years, num_simulations)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monte Carlo failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Bulk Import Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@investment_api.post("/bulk_import/Investments")
async def bulk_import(file: UploadFile = File(...), import_type: str = Form(...)):
    """Bulk import investments from CSV."""
    try:
        file_content = await file.read()
        temp_file = f"temp_bulk_{import_type}.csv"
        with open(temp_file, "wb") as f:
            f.write(file_content)
        
        if import_type == "mixed":
            from modules.csv_import import import_mixed_csv_data
            message = import_mixed_csv_data(temp_file, "Investments")
        elif import_type == "unit_prices":
            from modules.csv_import import import_unit_prices_csv
            message = import_unit_prices_csv(temp_file, "Investments")
        else:
            from modules.csv_import import import_csv_data
            message = import_csv_data(temp_file, import_type, "Investments")
        
        try:
            import os
            os.remove(temp_file)
        except:
            pass
        
        return {
            "message": message or "Import completed",
            "import_type": import_type,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk import failed: {str(e)}")


@investment_api.get("/bulk_import/template/{import_type}")
async def bulk_import_template(import_type: str):
    """Download CSV template for bulk import."""
    templates = {
        "investments": "institution_name,investment_name,investment_ticker,investment_type,unit_currency,initial_investment_date,initial_unit_price,unit_price,number_of_units_held,total_dividends_received,total_tax_paid,total_fees_paid,investment_fee,investment_status\n",
        "transactions": "investment_name,transaction_date,transaction_type,transaction_amount,unit_price,number_of_units\n",
        "unit_prices": "investment_name,unit_price_date,unit_price\n",
    }
    content = templates.get(import_type, "column1,column2\n")
    return Response(content, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=template_{import_type}.csv"})


# ─────────────────────────────────────────────────────────────────────────────
# Net Worth Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@investment_api.get("/net_worth/Investments")
async def get_net_worth(database_name: str = "Investments", base_currency: str = "ZAR"):
    """Get net worth breakdown."""
    try:
        summary_df = get_investment_summary_display(base_currency=base_currency, database_name=database_name)
        portfolio_totals = get_portfolio_total_value(base_currency=base_currency, database_name=database_name)
        
        by_type = []
        by_institution = []
        by_currency = []
        
        if not summary_df.empty:
            type_groups = summary_df.groupby("investment_type").agg({"investment_value": "sum"}).reset_index()
            for _, row in type_groups.iterrows():
                by_type.append({
                    "type": row["investment_type"],
                    "value": round(row["investment_value"], 2),
                    "pct": round(row["investment_value"] / summary_df["investment_value"].sum() * 100, 1) if summary_df["investment_value"].sum() > 0 else 0,
                    "count": len(summary_df[summary_df["investment_type"] == row["investment_type"]])
                })
            
            inst_groups = summary_df.groupby("institution_name").agg({"investment_value": "sum"}).reset_index()
            for _, row in inst_groups.iterrows():
                by_institution.append({
                    "institution": row["institution_name"],
                    "value": round(row["investment_value"], 2),
                    "pct": round(row["investment_value"] / summary_df["investment_value"].sum() * 100, 1) if summary_df["investment_value"].sum() > 0 else 0,
                    "count": len(summary_df[summary_df["institution_name"] == row["institution_name"]])
                })
            
            curr_groups = summary_df.groupby("unit_currency").agg({"investment_value": "sum"}).reset_index()
            for _, row in curr_groups.iterrows():
                by_currency.append({
                    "currency": row["unit_currency"],
                    "value": round(row["investment_value"], 2),
                    "pct": round(row["investment_value"] / summary_df["investment_value"].sum() * 100, 1) if summary_df["investment_value"].sum() > 0 else 0,
                    "count": len(summary_df[summary_df["unit_currency"] == row["unit_currency"]])
                })
        
        timeseries = get_net_worth_timeseries(database_name, base_currency)

        # Use summary_df as the single source of truth for total net worth
        # so that total always equals the sum of by_type / by_institution / by_currency
        total_net_worth = summary_df["investment_value"].sum() if not summary_df.empty else 0

        # Compute real contributions and fees from the transactions table
        total_contributions = 0.0
        total_fees = 0.0
        try:
            with get_db_connection(database_name) as (_conn, _cur):
                _cur.execute("""
                    SELECT COALESCE(SUM(CASE WHEN LOWER(transaction_type) = 'buy' THEN transaction_amount ELSE 0 END), 0),
                           COALESCE(SUM(CASE WHEN LOWER(transaction_type) IN ('fee', 'dividend') THEN transaction_amount ELSE 0 END), 0)
                    FROM transactions
                """)
                _row = _cur.fetchone()
                if _row:
                    total_contributions = float(_row[0])
                    total_fees = float(_row[1])
        except Exception:
            pass

        # Calculate portfolio IRR and CAGR
        portfolio_irr = None
        portfolio_cagr = None
        try:
            from modules.metrics import calculate_portfolio_irr
            irr_data = calculate_portfolio_irr(database_name, base_currency)
            if irr_data and "whole_portfolio" in irr_data:
                portfolio_irr = irr_data["whole_portfolio"].get("irr_pct")
        except Exception:
            pass
        
        return {
            "total_net_worth": round(total_net_worth, 2),
            "total_net_worth_formatted": f"{base_currency} {round(total_net_worth, 2):,.2f}",
            "by_type": by_type,
            "by_institution": by_institution,
            "by_currency": by_currency,
            "timeseries": timeseries,
            "investment_count": len(summary_df) if not summary_df.empty else 0,
            "base_currency": base_currency,
            "timestamp": datetime.now().isoformat(),
            "total_contributions": round(total_contributions, 2),
            "total_fees": round(total_fees, 2),
            "portfolio_cagr": portfolio_cagr,
            "portfolio_irr": portfolio_irr
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch net worth: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Price Fetch Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@investment_api.get("/prices/backfill_status")
async def prices_backfill_status(database_name: str = "Investments"):
    """Get backfill status for all investments."""
    try:
        status = get_backfill_status(database_name)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backfill status: {str(e)}")


@investment_api.post("/prices/fetch/Investments")
async def prices_fetch_all(database_name: str = "Investments"):
    """Trigger price fetch for all investments."""
    try:
        result = fetch_prices_now(database_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch prices: {str(e)}")


@investment_api.post("/prices/fetch_now")
async def prices_fetch_now_endpoint(database_name: str = "Investments", investment_id: int = None):
    """Manually trigger price fetch."""
    try:
        result = fetch_prices_now(database_name, investment_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch prices: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Metrics Endpoints (Real Data)
# ─────────────────────────────────────────────────────────────────────────────

@investment_api.get("/investment_comparison/{database_name}")
async def get_investment_comparison(database_name: str):
    """
    Compare metrics for the same asset held in more than one account
    (e.g. a fund in a brokerage account and in a tax-free account).
    """
    try:
        from modules.comparison import get_investment_comparison
        return get_investment_comparison(database_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@investment_api.get("/investment_metrics/{database_name}")
async def get_investment_metrics(database_name: str, base_currency: str = "ZAR", filter: str = "portfolio"):
    """
    Get comprehensive investment metrics over time from stored portfolio_metrics table.
    """
    try:
        with get_db_connection(database_name) as (conn, cursor):
            # Parse filter into (dimension_type, dimension_value).
            # Frontend sends:
            #   - "portfolio"                    → portfolio / All
            #   - "by_type:ETF"                  → investment_type / ETF
            #   - "by_institution:Standard Bank" → institution / Standard Bank
            #   - "by_currency:ZAR"              → currency / ZAR
            #   - "individual:Investment Name"   → investment / <name>
            dimension_map = {
                "portfolio": "portfolio",
                "individual": "investment",
                "investment": "investment",
                "by_currency": "currency",
                "currency": "currency",
                "by_type": "investment_type",
                "investment_type": "investment_type",
                "by_institution": "institution",
                "institution": "institution",
                "account_type": "account_type"
            }
            dimension_type = "portfolio"
            dimension_value = "All"

            if filter and ":" in filter:
                key, _, value = filter.partition(":")
                key_clean = key.strip()
                dimension_type = dimension_map.get(key_clean, key_clean)
                dimension_value = value.strip()
            else:
                filter_clean = (filter or "").strip()
                dimension_type = dimension_map.get(filter_clean, filter_clean or "portfolio")
                dimension_value = "All"

            cursor.execute("""
                SELECT metrics_date, total_contributions, total_current_value,
                       total_return_amount, total_return_pct, cagr, irr,
                       total_fees, total_dividends, total_tax, investment_count
                FROM portfolio_metrics
                WHERE dimension_type = %s AND dimension_value = %s
                ORDER BY metrics_date ASC
            """, (dimension_type, dimension_value))
            rows = cursor.fetchall()
            
            if not rows:
                return Response(
                    json.dumps({"conclusion": "No metrics data available. Run metric recalculation first.", "filter_type": filter, "data_points": 0}),
                    media_type="application/json"
                )
            
            portfolio_performance_return = []
            rolling_returns_1y = []
            rolling_returns_3y = []
            rolling_returns_5y = []
            risk_metrics = []
            contribution_vs_growth = []
            dividend_yield = []
            
            for idx, row in enumerate(rows):
                date_str = row[0].strftime("%Y-%m") if row[0] else f"Period {idx}"
                contrib = float(row[1] or 0)
                current_val = float(row[2] or 0)
                ret_amt = float(row[3] or 0)
                ret_pct = float(row[4] or 0)
                cagr = float(row[5] or 0)
                irr = float(row[6] or 0)
                fees = float(row[7] or 0)
                divs = float(row[8] or 0)
                tax = float(row[9] or 0)
                count = int(row[10] or 0)
                
                portfolio_performance_return.append({
                    "period": date_str,
                    "value": round(ret_pct * 100, 2),
                    "index": idx
                })
                
                rolling_returns_1y.append({
                    "period": date_str,
                    "value": round(ret_pct * 100, 2),
                    "index": idx
                })
                rolling_returns_3y.append({
                    "period": date_str,
                    "value": round(cagr * 100, 2),
                    "index": idx
                })
                rolling_returns_5y.append({
                    "period": date_str,
                    "value": round(irr * 100, 2),
                    "index": idx
                })
                
                risk_metrics.append({
                    "period": date_str,
                    "value": round(abs(ret_pct) * VOLATILITY_BASELINE_PORTFOLIO, 3),
                    "index": idx
                })
                
                contribution_vs_growth.append({
                    "period": date_str,
                    "contributions": contrib,
                    "growth": current_val - contrib,
                    "index": idx
                })
                
                dividend_yield.append({
                    "period": date_str,
                    "value": round((divs / current_val * 100) if current_val > 0 else 0, 4),
                    "index": idx
                })
            
            latest = rows[-1]
            total_current_value = float(latest[2] or 0)
            total_contributions = float(latest[1] or 0)
            total_return_amount = float(latest[3] or 0)
            total_return_pct = float(latest[4] or 0)
            total_fees = float(latest[7] or 0)
            total_tax = float(latest[9] or 0)
            total_divs = float(latest[8] or 0)
            investment_count = int(latest[10] or 0)
            
            key_metrics = [
                {"metric": "Total Value", "value": round(total_current_value, 2), "unit": base_currency, "formatted_value": f"{base_currency} {round(total_current_value, 2):,.2f}"},
                {"metric": "Total Contributions", "value": round(total_contributions, 2), "unit": base_currency, "formatted_value": f"{base_currency} {round(total_contributions, 2):,.2f}"},
                {"metric": "Total Return %", "value": round(total_return_pct, 2), "unit": "%", "formatted_value": f"{round(total_return_pct, 2):.2f}%"},
                {"metric": "CAGR", "value": round(float(latest[5] or 0) * 100, 2), "unit": "%", "formatted_value": f"{round(float(latest[5] or 0) * 100, 2):.2f}%"},
                {"metric": "IRR", "value": round(float(latest[6] or 0) * 100, 2), "unit": "%", "formatted_value": f"{round(float(latest[6] or 0) * 100, 2):.2f}%"},
                {"metric": "Active Investments", "value": investment_count, "unit": "count", "formatted_value": str(investment_count)}
            ]
            
            conclusion = f"Portfolio performance: Total value {base_currency} {total_current_value:,.2f}, total contributions {base_currency} {total_contributions:,.2f}, net growth {base_currency} {total_return_amount:,.2f}."
            
            fee_analysis = []
            tax_analysis = []
            for idx, row in enumerate(rows):
                date_str = row[0].strftime("%Y-%m") if row[0] else f"Period {idx}"
                fees = float(row[7] or 0)
                tax = float(row[9] or 0)
                divs = float(row[8] or 0)
                curr_val = float(row[2] or 0)
                fee_analysis.append({
                    "period": date_str,
                    "fee_ratio": round((fees / curr_val * 100) if curr_val > 0 else 0, 4),
                    "total_fees": round(fees, 2),
                    "index": idx
                })
                tax_analysis.append({
                    "period": date_str,
                    "tax_ratio": round((tax / curr_val * 100) if curr_val > 0 else 0, 4),
                    "total_tax": round(tax, 2),
                    "index": idx
                })
            
            return Response(
                json.dumps({
                    "portfolio_performance_return": portfolio_performance_return,
                    "rolling_returns": {
                        "one_year": rolling_returns_1y,
                        "three_year": rolling_returns_3y,
                        "five_year": rolling_returns_5y
                    },
                    "risk_metrics": {"volatility": risk_metrics, "sharpe_ratio": [], "max_drawdown": []},
                    "contribution_vs_growth": contribution_vs_growth,
                    "drawdown_analysis": [],
                    "dividend_yield": dividend_yield,
                    "fee_analysis": fee_analysis,
                    "tax_analysis": tax_analysis,
                    "cagr_trend": portfolio_performance_return,
                    "irr_trend": portfolio_performance_return,
                    "benchmarks": {"portfolio": [], "benchmark": []},
                    "key_metrics": key_metrics,
                    "conclusion": conclusion,
                    "filter_type": filter,
                    "generated_at": datetime.now().isoformat(),
                    "base_currency": base_currency,
                    "data_points": len(rows),
                    "data_source": "database",
                    "total_current_value": total_current_value,
                    "total_return_amount": total_return_amount,
                    "total_return_pct": total_return_pct
                }),
                media_type="application/json",
                headers={"X-Cache": "MISS"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate investment metrics: {str(e)}")
