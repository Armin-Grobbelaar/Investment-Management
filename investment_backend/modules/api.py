"""
API Module

Functions for FastAPI endpoints and API-related operations.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import pandas as pd
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

# Import from existing modules
from .database import DEFAULT_DB
from .investments import (
    get_investment_summary_display, get_portfolio_total_value,
    get_currencies_in_portfolio, get_investment_types_in_portfolio,
    get_all_investment_values, get_investment_data, get_investment_summary,
    add_investment, get_investment_names_list
)
from .csv_import import (
    import_unit_prices_csv, import_mixed_csv_data, import_csv_data, import_inflation_csv_data
)
from .predictions import get_investment_predictions
from .reporting import generate_investment_pdf_report
from .metrics import get_investment_metrics_data, get_investment_metrics_by_name_data
from .currency import currency_display_symbol
from .database import add_user as add_user_db


# Default database name from environment
DEFAULT_DB_ENV = os.getenv("INVESTMENTS_DB", "Investments")

# In-memory cache for expensive operations (simple implementation)
_cache_data = {}
_cache_expiry = {}
CACHE_TIMEOUT = 300  # 5 minutes in seconds

def _get_cache_key(endpoint: str, params: dict = None) -> str:
    """Generate cache key from endpoint and parameters."""
    if params:
        param_str = json.dumps(params, sort_keys=True)
        return f"{endpoint}:{param_str}"
    return endpoint

def _get_cached_data(cache_key: str):
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
    email: str
    password: str
    full_name: str = None

class AddInvestmentRequest(BaseModel):
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

def get_dashboard_data(database_name: str, base_currency: str = "ZAR"):
    """
    Get optimized dashboard data with caching.
    """
    # Normalize display symbols ('R') to ISO codes ('ZAR').
    from .currency import resolve_currency_code
    base_currency = resolve_currency_code(base_currency or "")
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

def get_investment_timeseries_data(database_name: str, base_currency: str = "ZAR", investment_name: str = None):
    """
    Get investment timeseries data for line charts.
    """
    # Normalize display symbols ('R') to ISO codes ('ZAR').
    from .currency import resolve_currency_code
    base_currency = resolve_currency_code(base_currency or "")

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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Dashboard chart generation failed: {str(e)}")

def get_investment_summary_response(database_name):
    """Get investment summary as JSON response."""
    investment_summary = get_investment_summary(database_name)
    return Response(investment_summary.to_json(orient="records"), media_type="application/json")

def add_user_api(user_data: AddUserRequest):
    """Add a user via API."""
    from .database import add_user
    add_user(user_data.username, user_data.email, user_data.password, user_data.full_name)
    return {"message": "User successfully added"}

def get_all_investment_values_response(database_name: str):
    """Get all investment values as JSON response."""
    investment_values = get_all_investment_values(database_name)
    return Response(investment_values.to_json(orient="records"), media_type="application/json")

def get_investment_values_filtered(database_name: str, investment_name: str, column_name: str):
    """Get filtered investment values."""
    global investment_values
    investment_values = pd.DataFrame()
    if (investment_values.empty):
        investment_values = get_all_investment_values(database_name)
    investment_values_filttered = investment_values[investment_values["investment_name"] == investment_name][column_name]
    return Response(investment_values_filttered.to_json(orient="records"), media_type="application/json")

def add_investment_api(database_name: str, investment_data: AddInvestmentRequest):
    """Add an investment via API."""
    try:
        from .database import create_connection
        # Set up database connection - this function needs it for the legacy add_investment call
        create_connection(database_name)
        result = add_investment(
            database_name,
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

        if result is None:
            # Investment already exists
            return {"message": "Investment already exists. Skipped adding duplicate investment."}
        else:
            # Investment was successfully added, result contains the ID
            return {"message": "Investment added successfully!", "investment_id": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add investment: {str(e)}")

def import_unit_prices_api(file_content, investment_name):
    """Import unit prices from uploaded file."""
    try:
        # Save the uploaded file content temporarily in memory
        file_name = "temp_unit_prices.csv"

        # Write the file content to a temporary file
        with open(file_name, "wb") as temp_file:
            temp_file.write(file_content)

        # Call the existing function (currency is stored on the investment
        # record itself, so no currency argument is needed)
        import_unit_prices_csv(file_name, investment_name)

        return {"message": "Unit prices imported successfully", "investment_name": investment_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def import_investment_data_api(data_type: str, file_content, investment_name: str = None):
    """Import investment data from uploaded file."""
    try:
        # Validate data type
        allowed_data_types = ['unit_prices', 'transactions', 'returns', 'dividends', 'fees', 'tax', 'inflation', 'mixed']
        if data_type not in allowed_data_types:
            raise HTTPException(status_code=400, detail=f"Invalid data type. Allowed: {', '.join(allowed_data_types)}")

        # Save the uploaded file content to a temporary file
        temp_file_name = f"temp_{data_type}.csv"

        with open(temp_file_name, "wb") as temp_file:
            temp_file.write(file_content)

        # Import the data based on type
        if data_type == 'mixed':
            # Handle mixed data type CSV
            message = import_mixed_csv_data(temp_file_name, investment_name)

        elif data_type == 'unit_prices':
            # Use existing unit prices function (currency is stored on the
            # investment record itself, so no currency argument is needed)
            import_unit_prices_csv(temp_file_name, investment_name)
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
        except Exception as e:
            import logging
            logging.warning(f"Failed to clean up temp file: {e}")

        return {"message": message, "data_type": data_type, "investment_name": investment_name if data_type != 'inflation' else None}

    except Exception as e:
        # Clean up temporary file on error
        try:
            import os
            os.remove(f"temp_{data_type}.csv")
        except Exception as e:
            import logging
            logging.warning(f"Failed to clean up temp file on error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def invalidate_cache_api(database_name: str = None):
    """Invalidate cached data."""
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

def get_investment_names_api():
    """Get list of investment names for dropdowns."""
    try:
        names = get_investment_names_list(DEFAULT_DB_ENV)
        return {"investment_names": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch investment names: {str(e)}")

def get_investment_predictions_api(database_name: str, scope: str = "portfolio", model_filter: str = None,
                                   specific_investment_name: str = None, specific_currency: str = None,
                                   specific_investment_type: str = None, specific_institution: str = None):
    """
    Get comprehensive investment price predictions with confidence intervals.
    """
    try:
        # Parse model filter if provided
        models_to_run = None
        if model_filter:
            models_to_run = [m.strip() for m in model_filter.split(',') if m.strip()]

        # Get predictions with all selection parameters
        predictions_result = get_investment_predictions(
            database_name=database_name,
            scope=scope,
            model_filter=models_to_run,
            specific_investment_name=specific_investment_name,
            specific_currency=specific_currency,
            specific_investment_type=specific_investment_type,
            specific_institution=specific_institution
        )

        return Response(
            json.dumps(predictions_result),
            media_type="application/json",
            headers={"X-Cache": "MISS"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate investment predictions: {str(e)}")

def health_check_api():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_entries": len(_cache_data),
        "uptime_seconds": (datetime.now() - datetime.strptime("2024-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")).total_seconds()
    }

def get_investment_metrics_api(database_name: str, base_currency: str = "ZAR", filter: str = "portfolio"):
    """
    Get comprehensive investment metrics data.
    """
    # Normalize display symbols ('R') to ISO codes ('ZAR').
    from .currency import resolve_currency_code
    base_currency = resolve_currency_code(base_currency or "")

    try:
        metrics_data = get_investment_metrics_data(database_name, base_currency, filter)

        return Response(
            json.dumps(metrics_data),
            media_type="application/json",
            headers={"X-Data-Source": "REAL_DATABASE"}
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch investment metrics: {str(e)}")

def get_investment_metrics_by_name_api(database_name: str, investment_name: str):
    """Get metrics for a specific investment by name."""
    try:
        data = get_investment_metrics_by_name_data(database_name, investment_name)

        return Response(
            json.dumps(data),
            media_type="application/json"
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"ERROR in get_investment_metrics_by_name: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")

def generate_pdf_report_api(database_name: str, output_filename: str = None):
    """Generate PDF report."""
    try:
        # Generate the PDF report
        pdf_path = generate_investment_pdf_report(database_name, output_filename)

        # Return as downloadable file
        return FileResponse(
            path=pdf_path,
            media_type='application/pdf',
            filename=os.path.basename(pdf_path),
            headers={
                "Content-Disposition": f"attachment; filename={os.path.basename(pdf_path)}"
            }
        )

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate PDF report: {str(e)}"
        }

def refresh_data_api(database_name: str):
    """Trigger background refresh of cached data."""
    # Clear cache for this database
    invalidate_cache_api(database_name)

    # Optionally trigger background data refresh tasks here
    # For now, just return confirmation that cache was invalidated

    return {
        "message": f"Data refresh initiated for {database_name}",
        "cache_invalidated": True,
        "timestamp": datetime.now().isoformat()
    }


# Color palettes for charts
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

def _get_blue_color(index: int, opacity: str = "") -> str:
    """Get a blue-themed color, cycling through the palette."""
    color = BLUE_COLORS[index % len(BLUE_COLORS)]
    return color + opacity  # Add opacity if provided

def _get_blue_color_for_area_chart(index: int) -> str:
    """Get a blue-themed color for area charts."""
    return AREA_CHART_COLORS[index % len(AREA_CHART_COLORS)]


def get_dashboard_charts_api(database_name: str, base_currency: str = "ZAR",
                             filter_type: str = None, filter_value: str = None):
    """
    Get pre-processed chart data for frontend - all aggregations done server-side.
    Returns ready-to-use pie chart data and aggregated tables.
    """
    # Normalize display symbols ('R') to ISO codes ('ZAR').
    from .currency import resolve_currency_code
    base_currency = resolve_currency_code(base_currency or "")
   
    cache_key = f"charts:{database_name}:{base_currency}:{filter_type or ''}:{filter_value or ''}"

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
        
        # Ensure unit_price_date is datetime and investment_value is numeric float to avoid type comparison errors
        if not timeseries_df.empty:
            if "unit_price_date" in timeseries_df.columns:
                timeseries_df["unit_price_date"] = pd.to_datetime(timeseries_df["unit_price_date"], errors='coerce')
                timeseries_df = timeseries_df.dropna(subset=["unit_price_date"])
            if "investment_value" in timeseries_df.columns:
                timeseries_df["investment_value"] = pd.to_numeric(timeseries_df["investment_value"], errors='coerce').fillna(0.0)

        # Apply filtering if filter parameters are provided
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

            # Filter timeseries data
            if filtered_investment_names:
                timeseries_df = timeseries_df[timeseries_df["investment_name"].isin(filtered_investment_names)]

        # Process timeseries data for line charts
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
                    "borderColour": _get_blue_color(investment_index)
                })

            # Trim date range to the first non-zero investment value date
            nonzero_df = timeseries_df[timeseries_df["investment_value"] > 0.01]
            if not nonzero_df.empty:
                min_date = nonzero_df["unit_price_date"].min()
            else:
                min_date = timeseries_df["unit_price_date"].min()
            max_date = timeseries_df["unit_price_date"].max()

            timeseries_date_range = {
                "min": min_date.isoformat() if hasattr(min_date, 'isoformat') else str(min_date),
                "max": max_date.isoformat() if hasattr(max_date, 'isoformat') else str(max_date)
            }
        else:
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
                "summary_table": [],
                "timeseries": [],
                "timeseries_date_range": {"min": None, "max": None},
                "bar_charts": [],
                "area_charts": [],
                "key_metrics": [],
                "menu_items": [],
                "base_currency": base_currency,
                "total_portfolio_value": 0.0,
                "timestamp": datetime.now().isoformat(),
                "cache_expires_in": CACHE_TIMEOUT
            }
            _set_cache_data(cache_key, empty_response)
            return Response(
                json.dumps(empty_response),
                media_type="application/json",
                headers={"X-Cache": "MISS"}
            )

        # Individual investment pie chart
        individual_values = summary_df["investment_value"].fillna(0)
        total_individual = individual_values.sum()

        individual_pie = {
            "labels": summary_df["investment_name"].tolist(),
            "datasets": [{
                "data": [(val / total_individual * 100) if total_individual > 0 else 0 for val in individual_values],
                "backgroundColor": [_get_blue_color(i) for i in range(len(summary_df))],
            }]
        }

        # Helper function to safely aggregate dates
        def safe_date_agg(dates):
            valid_dates = pd.to_datetime(dates, errors='coerce')
            if valid_dates.notna().any():
                return valid_dates.min().strftime('%d/%m/%Y')
            else:
                return "N/A"

        # Initialize variables  
        type_pie = {"labels": [], "datasets": []}
        type_table = []
        currency_pie = {"labels": [], "datasets": []}
        currency_table = []
        institution_pie = {"labels": [], "datasets": []}
        institution_table = []
        type_groups = pd.DataFrame()
        raw_currency_groups = pd.DataFrame()
        institution_groups = pd.DataFrame()

        # Generate charts based on filter type
        if not filter_type or filter_type != "investment_type":
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
                    "backgroundColor": [_get_blue_color(i) for i in range(len(type_groups))],
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
            raw_currency_groups = raw_summary_df.groupby("unit_currency").agg({
                "investment_value": "sum"
            }).reset_index()

            raw_currency_values = raw_currency_groups["investment_value"]
            total_raw_currency = raw_currency_values.sum()

            currency_pie = {
                "labels": raw_currency_groups["unit_currency"].tolist(),
                "datasets": [{
                    "data": [(val / total_raw_currency * 100) if total_raw_currency > 0 else 0 for val in raw_currency_values],
                    "backgroundColor": [_get_blue_color(i) for i in range(len(raw_currency_groups))],
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
                    "backgroundColor": [_get_blue_color(i) for i in range(len(institution_groups))],
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

        # Format summary table
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

                    formatted_date = str(investment_date)

            try:
                summary_table.append({
                    "id": int(row["id"]),
                    "institution_name": row["institution_name"],
                    "investment_name": row["investment_name"],
                    "investment_type": row["investment_type"],
                    "unit_currency": row.get("unit_currency", base_currency),
                    "investment_value_in_native_currency": round(row.get("investment_value", 0), 2),
                    "unit_price_in_native_currency": round(row.get("unit_price", 0), 2),
                    "total_units_held": float(row.get("total_units_held", row.get("number_of_units_held", 0))),
                    "initial_unit_price_in_native_currency": round(row.get("initial_unit_price", 0), 2),
                    "initial_investment_date": formatted_date
                })
            except Exception as e:
                print(f"ERROR processing row for {row.get('investment_name', 'UNKNOWN')}: {e}")
                print(f"Row keys: {row.keys()}")
                raise e

        # Key metrics for dashboard tiles
        # Actual IRR from the portfolio metric data is calculated in the metrics
        # module; this legacy endpoint is superseded by /dashboard_charts in
        # investment_backend_fastapi.py. IRR/contributions fall back to 0 here.
        key_metrics = [
            {
                "metric": "IRR",
                "value": round(0.0, 2),
                "unit": "%",
                "formatted_value": "0.0%"
            },
            {
                "metric": "Total Net Worth",
                "value": round(total_individual, 2),
                "unit": base_currency,
                "formatted_value": f"{currency_display_symbol(base_currency)} {round(total_individual, 2):,.2f}"
            },
            {
                "metric": "Total Contributions",
                "value": round(0.0, 2),
                "unit": base_currency,
                "formatted_value": f"{currency_display_symbol(base_currency)} {round(0.0, 2):,.2f}"
            },
            {
                "metric": "Total Investment Time",
                "value": round(0.0, 2),
                "unit": "years",
                "formatted_value": "0.0 years"
            }
        ]

        # Generate bar charts
        bar_charts = []

        if not type_groups.empty:
            total_type = type_groups["investment_value"].sum()
            bar_charts.append({
                "title": "Portfolio Allocation by Type",
                "type": "horizontalBar",
                "data": {
                    "labels": type_groups["investment_type"].tolist(),
                    "datasets": [{
                        "label": "Investment Value",
                        "data": type_groups["investment_value"].round(2).tolist(),
                        "backgroundColor": [_get_blue_color(i) for i in range(len(type_groups))],
                    }]
                }
            })

        if not raw_currency_groups.empty:
            bar_charts.append({
                "title": "Portfolio Allocation by Currency",
                "type": "verticalBar",
                "data": {
                    "labels": raw_currency_groups["unit_currency"].tolist(),
                    "datasets": [{
                        "label": "Investment Value",
                        "data": raw_currency_groups["investment_value"].round(2).tolist(),
                        "backgroundColor": [_get_blue_color(i) for i in range(len(raw_currency_groups))],
                    }]
                }
            })

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
                        "backgroundColor": [_get_blue_color(i) for i in range(len(top_10_investments))],
                    }]
                }
            })

        # Area charts
        area_charts = []
        try:
            area_timeseries_df = timeseries_df.copy()
            if not area_timeseries_df.empty:
                area_timeseries_df['unit_price_date'] = pd.to_datetime(area_timeseries_df['unit_price_date'])
                last_30_days = area_timeseries_df['unit_price_date'].max() - pd.Timedelta(days=30)
                area_timeseries_df = area_timeseries_df[area_timeseries_df['unit_price_date'] >= last_30_days]

                area_grouped = area_timeseries_df.groupby(['unit_price_date', 'investment_name'])['investment_value'].sum().reset_index()
                area_pivot = area_grouped.pivot(index='unit_price_date', columns='investment_name', values='investment_value').fillna(0)

                top_investments = area_pivot.sum().nlargest(5).index.tolist()
                area_pivot = area_pivot[top_investments]

                area_datasets = []
                for i, col in enumerate(area_pivot.columns):
                    color = _get_blue_color_for_area_chart(i)
                    area_datasets.append({
                        "label": col,
                        "data": [{"x": area_pivot.index[j].strftime('%Y-%m-%d'), "y": float(area_pivot.iloc[j, i])} for j in range(len(area_pivot))],
                        "fill": True,
                        "backgroundColor": color + '40',
                        "borderColor": color,
                        "pointRadius": 0
                    })

                area_charts.append({
                    "title": "Portfolio Value Over Time (Top 5 Investments)",
                    "data": {
                        "datasets": area_datasets
                    }
                })
        except Exception as e:
            print(f"Warning: Could not generate area chart: {e}")
            area_charts = []

        # Menu items
        menu_items = []
        if not type_groups.empty:
            menu_items.append({
                "heading": "Investment Type",
                "items": type_groups["investment_type"].tolist(),
                "urls": [f"/Investments/InvestmentsType/{item.replace(' ', '%20')}" for item in type_groups["investment_type"].tolist()]
            })
        
        if not raw_currency_groups.empty:
            menu_items.append({
                "heading": "Investment Currency",
                "items": raw_currency_groups["unit_currency"].tolist(),
                "urls": [f"/Investments/InvestmentsCurrency/{item.replace(' ', '%20')}" for item in raw_currency_groups["unit_currency"].tolist()]
            })
        
        if not institution_groups.empty:
            menu_items.append({
                "heading": "Institution",
                "items": institution_groups["institution_name"].head(10).tolist(),
                "urls": [f"/Investments/InvestmentsInstitution/{item.replace(' ', '%20')}" for item in institution_groups["institution_name"].head(10).tolist()]
            })

        menu_items.append({
            "heading": "Tools & Analysis",
            "items": ["Edit Data", "Factsheets", "Property Analysis", "View Metrics", "Monte Carlo Simulations"],
            "urls": ["/EditInvestmentData", "/Factsheets", "/PropertyAnalysis", "/ViewInvestmentMetrics", "/ViewInvestmentPredictions"]
        })

        result = {
            "individual_pie": individual_pie,
            "type_pie": type_pie,
            "currency_pie": currency_pie,
            "institution_pie": institution_pie,
            "type_table": type_table,
            "currency_table": currency_table,
            "institution_table": institution_table,
            "summary_table": summary_table,
            "timeseries": processed_timeseries,
            "timeseries_date_range": timeseries_date_range,
            "bar_charts": bar_charts,
            "area_charts": area_charts,
            "key_metrics": key_metrics,
            "menu_items": menu_items,
            "base_currency": base_currency,
            "total_portfolio_value": round(total_individual, 2),
            "timestamp": datetime.now().isoformat(),
            "cache_expires_in": CACHE_TIMEOUT
        }

        _set_cache_data(cache_key, result)

        return Response(
            json.dumps(result),
            media_type="application/json",
            headers={"X-Cache": "MISS"}
        )

    except Exception as e:
        error_details = f"Dashboard chart generation failed: {str(e)}"
        print(f"ERROR: {error_details}")
        raise HTTPException(status_code=500, detail=error_details)


# Edit Data Functions
def get_edit_data_tables(database_name: str):
    """Get list of tables available for editing."""
    # Return the whitelist of editable tables
    return [
        "investments",
        "transactions",
        "unit_prices",
        "dividends",
        "returns",
        "fees",
        "tax",
        "investment_metrics",
        "inflation",
        "predictions",
        "configuration",
        "prediction_accuracy",
        "investment_source_meta",
        "factsheets",
        "portfolio_metrics",
        "property_investments"
    ]


def get_edit_data_table(database_name: str, table_name: str, skip: int = 0, limit: int = 100, search: str = None):
    """Get data from a specific table with optional filtering and pagination."""
    from decimal import Decimal
    from .database import get_db_connection

    # Validate table name (security)
    allowed_tables = get_edit_data_tables(database_name)
    if table_name not in allowed_tables:
        raise ValueError(f"Table '{table_name}' is not allowed for editing")

    # Map PostgreSQL data_type strings to simple type tokens the frontend understands
    _PG_TYPE_MAP = {
        'integer': 'integer', 'bigint': 'integer', 'smallint': 'integer',
        'real': 'float', 'double precision': 'float',
        'numeric': 'numeric', 'decimal': 'numeric',
        'date': 'date',
        'timestamp without time zone': 'timestamp', 'timestamp with time zone': 'timestamp',
        'boolean': 'boolean',
        'character varying': 'text', 'varchar': 'text', 'text': 'text', 'char': 'text',
    }

    try:
        with get_db_connection(database_name) as (conn, cursor):
            # ------------------------------------------------------------------
            # Fetch column metadata (name + type) from information_schema so the
            # frontend can render the correct input type for each column.
            # ------------------------------------------------------------------
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name   = %s
                ORDER BY ordinal_position
            """, (table_name,))
            raw_cols = cursor.fetchall()  # [(col_name, data_type), ...]

            # Build [{name, type}] list expected by the frontend
            columns_meta = [
                {'name': col_name, 'type': _PG_TYPE_MAP.get(data_type, 'text')}
                for col_name, data_type in raw_cols
            ]
            column_names = [c['name'] for c in columns_meta]

            # Determine ORDER BY column — prefer 'id' if it exists, else first column
            order_col = "id" if "id" in column_names else (column_names[0] if column_names else "1")

            # Build query with optional search
            if search:
                search_conditions = [f"CAST({col} AS TEXT) ILIKE %s" for col in column_names]
                search_clause = " OR ".join(search_conditions)
                search_param = f"%{search}%"
                query = f"SELECT * FROM {table_name} WHERE {search_clause} ORDER BY {order_col} LIMIT %s OFFSET %s"
                cursor.execute(query, [search_param] * len(column_names) + [limit, skip])
            else:
                query = f"SELECT * FROM {table_name} ORDER BY {order_col} LIMIT %s OFFSET %s"
                cursor.execute(query, (limit, skip))

            rows = cursor.fetchall()

            # Total row count
            if search:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {search_clause}",
                               [search_param] * len(column_names))
            else:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_count = cursor.fetchone()[0]

            # Serialize rows to dicts — handle Decimal, datetime, bytes, etc.
            data = []
            for row in rows:
                row_dict = {}
                for i, col_meta in enumerate(columns_meta):
                    value = row[i]
                    # Convert non-JSON-serializable PostgreSQL types
                    if isinstance(value, Decimal):
                        value = float(value)
                    elif hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    elif isinstance(value, bytes):
                        value = value.decode('utf-8', errors='replace')
                    row_dict[col_meta['name']] = value
                data.append(row_dict)

            return {
                "table_name": table_name,
                "columns": columns_meta,  # [{name, type}, ...] — matches frontend interface
                "data": data,
                "total": total_count,       # alias expected by frontend
                "total_count": total_count,
                "skip": skip,
                "limit": limit,
            }

    except Exception as e:
        print(f"ERROR in get_edit_data_table: {e}")
        raise e



def _get_column_types(cursor, table_name: str) -> dict:
    """Return {column_name: (pg_data_type, is_nullable, has_default)} for a table."""
    cursor.execute("""
        SELECT column_name, data_type, is_nullable,
               (column_default IS NOT NULL) AS has_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    return {row[0]: (row[1], row[2] == 'YES', row[3]) for row in cursor.fetchall()}


def _sanitize_value(value, pg_type: str, nullable: bool):
    """
    Convert frontend-supplied values to Python types safe for psycopg2.
    Empty-string inputs are converted to None (if nullable) or a zero-default.
    """
    _INT_TYPES  = {'integer', 'bigint', 'smallint', 'int', 'int2', 'int4', 'int8', 'serial', 'bigserial'}
    _FLOAT_TYPES = {'real', 'double precision', 'float4', 'float8', 'numeric', 'decimal'}
    _DATE_TYPES  = {'date'}
    _TS_TYPES    = {'timestamp without time zone', 'timestamp with time zone', 'timestamp'}
    _BOOL_TYPES  = {'boolean', 'bool'}

    # Treat empty strings as NULL (only when the column allows it)
    if value == '' or value is None:
        if nullable:
            return None
        # Non-nullable: supply a safe default
        if pg_type in _INT_TYPES:   return 0
        if pg_type in _FLOAT_TYPES: return 0.0
        if pg_type in _BOOL_TYPES:  return False
        if pg_type in _DATE_TYPES:
            from datetime import date as _date
            return _date.today()
        if pg_type in _TS_TYPES:
            from datetime import datetime as _dt
            return _dt.now()
        return ''  # keep empty string for non-nullable text columns (never NULL)

    # Integer coercion (frontend may send numeric strings or floats)
    if pg_type in _INT_TYPES:
        try:   return int(float(str(value)))
        except Exception as e: return None if nullable else 0

    # Float coercion
    if pg_type in _FLOAT_TYPES:
        try:   return float(str(value))
        except Exception as e: return None if nullable else 0.0

    # Date coercion — accept ISO strings or datetime objects
    if pg_type in _DATE_TYPES:
        if hasattr(value, 'date'): return value.date()
        try:
            from datetime import date as _date
            return _date.fromisoformat(str(value)[:10])
        except Exception as e: return None if nullable else None

    # Timestamp coercion
    if pg_type in _TS_TYPES:
        if hasattr(value, 'isoformat'): return value
        try:
            from datetime import datetime as _dt
            return _dt.fromisoformat(str(value).replace('Z', '+00:00'))
        except: return None if nullable else None

    # Boolean coercion
    if pg_type in _BOOL_TYPES:
        if isinstance(value, bool): return value
        return str(value).lower() in ('true', '1', 'yes')

    # Default: return as-is (text, json, etc.)
    return value


def update_edit_data_table(database_name: str, table_name: str, update_data: dict):
    """Update data in a specific table with full input sanitization."""
    from .database import get_db_connection
    
    # Validate table name
    allowed_tables = get_edit_data_tables(database_name)
    if table_name not in allowed_tables:
        raise ValueError(f"Table '{table_name}' is not allowed for editing")
    
    with get_db_connection(database_name) as (conn, cursor):
        col_types = _get_column_types(cursor, table_name)
        
        # Determine the primary-key / lookup column. Prefer 'id', else first column.
        pk_col = 'id' if 'id' in col_types else (list(col_types.keys())[0] if col_types else None)
        if pk_col is None:
            raise ValueError(f"Table '{table_name}' has no columns")
        
        if pk_col not in update_data or update_data[pk_col] is None:
            raise ValueError(f"Record identifier '{pk_col}' is required for update")
        
        record_id = update_data.pop(pk_col)
        
        # Sanitize every value and strip unknown columns
        sanitized = {}
        for col, val in update_data.items():
            if col not in col_types:
                continue  # ignore extra keys not in the DB schema
            pg_type, nullable, _ = col_types[col]
            sanitized[col] = _sanitize_value(val, pg_type, nullable)
        
        if not sanitized:
            raise ValueError("No valid columns to update")
        
        set_clauses = [f"{col} = %s" for col in sanitized]
        query = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {pk_col} = %s"
        cursor.execute(query, list(sanitized.values()) + [record_id])
        conn.commit()
        
        if cursor.rowcount == 0:
            return f"No record with {pk_col}={record_id} found in {table_name}"
        
        return f"Record {record_id} updated successfully in {table_name}"


def add_edit_data_row(database_name: str, table_name: str, row_data: dict):
    """Add a new row to a specific table with full input sanitization."""
    from .database import get_db_connection
    
    # Validate table name
    allowed_tables = get_edit_data_tables(database_name)
    if table_name not in allowed_tables:
        raise ValueError(f"Table '{table_name}' is not allowed for editing")
    
    with get_db_connection(database_name) as (conn, cursor):
        col_types = _get_column_types(cursor, table_name)
        
        # Strip 'id' (auto-generated), strip unknown columns, sanitize values
        sanitized = {}
        for col, val in row_data.items():
            if col.lower() == 'id':
                continue
            if col not in col_types:
                continue
            pg_type, nullable, _ = col_types[col]
            sanitized[col] = _sanitize_value(val, pg_type, nullable)
        
        # Supply safe defaults for missing NOT NULL columns that have no
        # database-level default (e.g. total_fees_paid on investments), so
        # inserts never fail on the NOT NULL constraint.
        for col, (pg_type, nullable, has_default) in col_types.items():
            if col.lower() == 'id':
                continue
            if nullable or has_default:
                continue
            if col not in sanitized:
                sanitized[col] = _sanitize_value('', pg_type, nullable=False)
        
        if not sanitized:
            raise ValueError("No valid columns to insert")
        
        cols_sql = ', '.join(sanitized.keys())
        placeholders = ', '.join(['%s'] * len(sanitized))
        query = f"INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders}) RETURNING id"
        cursor.execute(query, list(sanitized.values()))
        new_id = cursor.fetchone()[0]
        conn.commit()
        
        return {"message": f"Record added successfully to {table_name}", "id": new_id}


def delete_edit_data_row(database_name: str, table_name: str, record_id: int, cascade: bool = False):
    """Delete a row from a specific table."""
    from .database import get_db_connection
    
    # Validate table name
    allowed_tables = get_edit_data_tables(database_name)
    if table_name not in allowed_tables:
        raise ValueError(f"Table '{table_name}' is not allowed for editing")
    
    with get_db_connection(database_name) as (conn, cursor):
        if table_name.lower() == 'investments' and cascade:
            # Clean up child tables to prevent foreign key violations
            cursor.execute("DELETE FROM unit_prices WHERE investment_id = %s", (record_id,))
            cursor.execute("DELETE FROM transactions WHERE investment_id = %s", (record_id,))
            cursor.execute("DELETE FROM investment_source_meta WHERE investment_id = %s", (record_id,))
            cursor.execute("DELETE FROM factsheets WHERE investment_id = %s", (record_id,))
            cursor.execute("DELETE FROM prediction_accuracy WHERE investment_id = %s", (record_id,))
            cursor.execute("""
                DELETE FROM investment_predictions 
                WHERE investment_name = (SELECT investment_name FROM investments WHERE id = %s)
            """, (record_id,))
        
        query = f"DELETE FROM {table_name} WHERE id = %s"
        cursor.execute(query, (record_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise ValueError(f"No record found with ID {record_id} in {table_name}")
        
        return {"message": f"Record {record_id} deleted successfully from {table_name}"}
