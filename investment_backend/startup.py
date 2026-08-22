#!/usr/bin/env python3

import os
import sys
import argparse
import logging
from time import sleep

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from create_tables import create_tables, INVESTMENTS_DB, USERS_DB
from investment_database_functions import (
    check_database_connection, create_database_if_not_exists,
    check_system_health, display_startup_summary, initialize_portfolio_util,
    DEFAULT_DB
)

def initialize_database_tables(force_recreate=False):
    """Initialize database tables with connection retries."""
    logger.info("Initializing database tables...")
    
    try:
        # Tables creation
        create_tables(INVESTMENTS_DB)
        create_tables(USERS_DB)
        logger.info("✓ All tables verified/created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Investment System Startup')
    parser.add_argument('--force', action='store_true', 
                       help='Force recreation of database tables (DANGEROUS!)')
    args = parser.parse_args()
    
    logger.info("Starting Investment System...")
    
    # 1. Check database connection with retry
    retries = 5
    while retries > 0:
        if check_database_connection():
            logger.info("✓ Database connection established")
            break
        retries -= 1
        logger.warning(f"Waiting for database... Retries left: {retries}")
        sleep(5)
    else:
        logger.error("❌ STARTUP FAILED: Cannot connect to database")
        sys.exit(1)
    
    # 2. Create databases
    if not create_database_if_not_exists(INVESTMENTS_DB) or not create_database_if_not_exists(USERS_DB):
        logger.error("❌ STARTUP FAILED: Cannot create databases")
        sys.exit(1)
    
    # 3. Initialize tables
    if not initialize_database_tables(force_recreate=args.force):
        logger.error("❌ STARTUP FAILED: Cannot initialize tables")
        sys.exit(1)
    
    # 4. Initialize portfolio
    if not initialize_portfolio_util(DEFAULT_DB):
        logger.error("❌ STARTUP FAILED: Cannot initialize portfolio")
        sys.exit(1)
    
    # 5. Health check
    if not check_system_health():
        logger.warning("⚠️  STARTUP COMPLETED WITH WARNINGS: Some health checks failed.")
    else:
        logger.info("✓ Startup completed successfully.")
    
    display_startup_summary()

if __name__ == "__main__":
    main()
