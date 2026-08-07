#!/usr/bin/env python3
"""
Investment Database Functions Module

This module provides database operations, data processing, chart generation,
and reporting functionality for the investment management system.

Refactored to use modular structure.
"""

# Re-export everything from modules
from modules.database import (
    DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DEFAULT_DB, USERS_DB,
    get_db_connection, create_connection, add_user
)

from modules.currency import (
    CURRENCY_SYMBOLS, NATIVE_CURRENCY, SUPPORTED_BASE_CURRENCIES,
    get_exchange_rate, convert_currency_amount, convert_investment_data_for_display
)

from modules.utils import (
    _fetch_and_store_historical_data, _handle_forex_investment
)

from modules.metrics import (
    xirr, is_leap_year, adjust_value, adjust_for_inflation,
    calculate_investment_metrics, update_investment_metrics,
    recalculate_investment_metrics_history, get_investment_metrics_by_name_data,
    get_investment_metrics_data, calculate_portfolio_irr
)

from modules.predictions import (
    PREDICTION_DAYS, CONFIDENCE_LEVEL, TRAIN_RATIO, _LIBRARIES_STATUS,
    store_prediction_data, get_recent_predictions, get_prediction_by_id,
    store_prediction_accuracy, get_prediction_accuracy,
    calculate_model_performance_stats, get_model_improvement_suggestions,
    get_prediction_improvement_data, cleanup_old_predictions, save_prediction,
    generate_historical_data, check_stationarity, make_stationary,
    StockPredictor, get_historical_data_from_db, get_investment_predictions,
    get_available_models_info
)

from modules.investments import (
    add_investment, get_investment_summary, get_investment_summary_display,
    get_currencies_in_portfolio, get_investment_types_in_portfolio,
    get_all_investment_values, get_investment_data, get_portfolio_total_value,
    get_investment_names_list, get_net_worth_timeseries
)

from modules.metrics import (
    get_investment_metrics_data
)

from modules.reporting import generate_investment_pdf_report

from modules.portfolio import (
    ensure_portfolio_exists, update_portfolio, get_portfolio_total_value as get_portfolio_total_value_new
)

from modules.startup_utils import (
    check_database_connection, check_database_exists, create_database_if_not_exists,
    check_system_health, display_startup_summary, initialize_portfolio as initialize_portfolio_util
)

from modules.maintenance_utils import (
    log, update_unit_prices_from_yfinance, calculate_all_investment_metrics,
    update_portfolio_aggregation, cleanup_old_predictions_maintenance, generate_summary_report
)

from modules.api import (
    get_dashboard_data, get_investment_timeseries_data, get_investment_summary_response,
    add_user_api, get_all_investment_values_response, get_investment_values_filtered,
    add_investment_api, import_unit_prices_api, import_investment_data_api,
    invalidate_cache_api, get_investment_names_api, get_investment_predictions_api,
    health_check_api, get_investment_metrics_api, get_investment_metrics_by_name_api,
    generate_pdf_report_api, refresh_data_api, get_dashboard_charts_api,
    get_edit_data_tables, get_edit_data_table, update_edit_data_table,
    add_edit_data_row, delete_edit_data_row
)

# Legacy global variables if needed (try to avoid using them)
investment_database_connection = None
investment_database_cursor = None
