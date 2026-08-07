#!/usr/bin/env python3
"""
Investment System Maintenance Script

Run this script daily or monthly to perform routine maintenance tasks.
All logic is in modules/ - this file only orchestrates the maintenance process.

Usage:
    python3 maintenance.py --daily      # Run daily tasks
    python3 maintenance.py --monthly    # Run monthly tasks
    python3 maintenance.py --all        # Run all tasks
    python3 maintenance.py --help       # Show help
"""

import os
import sys
import argparse

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from investment_database_functions import (
    DEFAULT_DB, log, update_unit_prices_from_yfinance, calculate_all_investment_metrics,
    update_portfolio_aggregation, cleanup_old_predictions_maintenance, generate_summary_report
)


def run_daily_tasks(database_name=DEFAULT_DB):
    """Run daily maintenance tasks."""
    log("=" * 70)
    log("STARTING DAILY MAINTENANCE TASKS")
    log("=" * 70)
    
    tasks = [
        ("Update Unit Prices", lambda: update_unit_prices_from_yfinance(database_name)),
        ("Calculate Metrics", lambda: calculate_all_investment_metrics(database_name)),
        ("Update Portfolio", lambda: update_portfolio_aggregation(database_name)),
    ]
    
    results = {}
    for task_name, task_func in tasks:
        log(f"\n--- {task_name} ---")
        try:
            success = task_func()
            results[task_name] = "✓" if success else "✗"
        except Exception as e:
            log(f"Task failed: {e}", "ERROR")
            results[task_name] = "✗"
    
    log("\n" + "=" * 70)
    log("DAILY MAINTENANCE COMPLETE")
    log("=" * 70)
    log("\nResults:")
    for task_name, result in results.items():
        log(f"  {result} {task_name}")
    log("")


def run_monthly_tasks(database_name=DEFAULT_DB):
    """Run monthly maintenance tasks."""
    log("=" * 70)
    log("STARTING MONTHLY MAINTENANCE TASKS")
    log("=" * 70)
    
    tasks = [
        ("Update Unit Prices", lambda: update_unit_prices_from_yfinance(database_name)),
        ("Calculate Metrics", lambda: calculate_all_investment_metrics(database_name)),
        ("Update Portfolio", lambda: update_portfolio_aggregation(database_name)),
        ("Generate Summary Report", lambda: generate_summary_report(database_name)),
        ("Cleanup Old Predictions", lambda: cleanup_old_predictions_maintenance(database_name, days_to_keep=90)),
    ]
    
    results = {}
    for task_name, task_func in tasks:
        log(f"\n--- {task_name} ---")
        try:
            success = task_func()
            results[task_name] = "✓" if success else "✗"
        except Exception as e:
            log(f"Task failed: {e}", "ERROR")
            results[task_name] = "✗"
    
    log("\n" + "=" * 70)
    log("MONTHLY MAINTENANCE COMPLETE")
    log("=" * 70)
    log("\nResults:")
    for task_name, result in results.items():
        log(f"  {result} {task_name}")
    log("")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Investment System Maintenance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 maintenance.py --daily          # Run daily tasks
  python3 maintenance.py --monthly        # Run monthly tasks
  python3 maintenance.py --all            # Run all tasks

Scheduling with cron:
  # Daily at 6 AM
  0 6 * * * cd /path/to/backend && python3 maintenance.py --daily

  # Monthly on 1st at 6 AM
  0 6 1 * * cd /path/to/backend && python3 maintenance.py --monthly
        """
    )
    
    parser.add_argument('--daily', action='store_true', help='Run daily tasks')
    parser.add_argument('--monthly', action='store_true', help='Run monthly tasks')
    parser.add_argument('--all', action='store_true', help='Run all tasks')
    parser.add_argument('--db', default=DEFAULT_DB, help=f'Database name (default: {DEFAULT_DB})')
    
    args = parser.parse_args()
    
    if not (args.daily or args.monthly or args.all):
        parser.print_help()
        sys.exit(1)
    
    database_name = args.db
    
    try:
        if args.daily or args.all:
            run_daily_tasks(database_name)
        
        if args.monthly or args.all:
            run_monthly_tasks(database_name)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        log("\n\nMaintenance interrupted by user", "WARN")
        sys.exit(130)
    except Exception as e:
        log(f"\n\nMaintenance failed with error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
