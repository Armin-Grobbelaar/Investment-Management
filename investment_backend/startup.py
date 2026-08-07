#!/usr/bin/env python3
"""
Investment System Startup Script

Run this script on first startup or when setting up the system.
All logic is in modules/ - this file only orchestrates the startup process.

Usage:
    python3 startup.py              # Normal startup
    python3 startup.py --force      # Force recreation of tables (DANGEROUS!)
"""

import os
import sys
import argparse

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from create_tables import create_tables, INVESTMENTS_DB, USERS_DB
from investment_database_functions import (
    check_database_connection, check_database_exists, create_database_if_not_exists,
    check_system_health, display_startup_summary, initialize_portfolio_util,
    ensure_portfolio_exists, update_portfolio, DEFAULT_DB
)


def initialize_database_tables(force_recreate=False):
    """Initialize database tables."""
    print("\n🏗️  Initializing database tables...")
    
    try:
        if force_recreate:
            print("   ⚠️  FORCE MODE: This will drop and recreate all tables!")
            response = input("   Are you sure? Type 'yes' to continue: ")
            if response.lower() != 'yes':
                print("   Aborted.")
                return False
        
        # Create tables for both databases
        print(f"   Creating tables in '{INVESTMENTS_DB}'...")
        create_tables(INVESTMENTS_DB)
        
        print(f"   Creating tables in '{USERS_DB}'...")
        create_tables(USERS_DB)
        
        print("   ✓ All tables created successfully")
        return True
        
    except Exception as e:
        print(f"   ✗ Failed to create tables: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main startup routine."""
    parser = argparse.ArgumentParser(description='Investment System Startup')
    parser.add_argument('--force', action='store_true', 
                       help='Force recreation of database tables (DANGEROUS!)')
    args = parser.parse_args()
    
    print("=" * 70)
    print("  INVESTMENT SYSTEM STARTUP")
    print("=" * 70)
    print()
    print(f"Environment:")
    print(f"  Host:     {os.getenv('POSTGRES_HOST', 'ThinkTank')}")
    print(f"  Port:     {os.getenv('POSTGRES_PORT', '5432')}")
    print(f"  User:     {os.getenv('POSTGRES_USER', 'postgres')}")
    print(f"  Inv DB:   {INVESTMENTS_DB}")
    print(f"  Users DB: {USERS_DB}")
    print()
    
    # Step 1: Check database connection
    if not check_database_connection():
        print("\n❌ STARTUP FAILED: Cannot connect to database")
        sys.exit(1)
    
    # Step 2: Create databases if they don't exist
    if not create_database_if_not_exists(INVESTMENTS_DB):
        print("\n❌ STARTUP FAILED: Cannot create investments database")
        sys.exit(1)
    
    if not create_database_if_not_exists(USERS_DB):
        print("\n❌ STARTUP FAILED: Cannot create users database")
        sys.exit(1)
    
    # Step 3: Initialize tables
    if not initialize_database_tables(force_recreate=args.force):
        print("\n❌ STARTUP FAILED: Cannot create tables")
        sys.exit(1)
    
    # Step 4: Initialize portfolio
    if not initialize_portfolio_util(DEFAULT_DB):
        print("\n❌ STARTUP FAILED: Cannot initialize portfolio")
        sys.exit(1)
    
    # Step 5: Health check
    if not check_system_health():
        print("\n⚠️  STARTUP COMPLETED WITH WARNINGS")
        print("    Some health checks failed. Review the output above.")
        sys.exit(0)
    
    # Success!
    display_startup_summary()
    sys.exit(0)


if __name__ == "__main__":
    main()
