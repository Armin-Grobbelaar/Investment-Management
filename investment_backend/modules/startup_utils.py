"""
Startup Utilities Module

Functions for system startup, database initialization, and health checks.
"""

import re
import psycopg2
from .database import DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DEFAULT_DB
from .portfolio import ensure_portfolio_exists, update_portfolio


def check_database_connection():
    """Check if we can connect to PostgreSQL server."""
    print("🔌 Checking database connection...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database="postgres",  # Connect to default postgres db first
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=5
        )
        conn.close()
        print("   ✓ Database connection successful")
        return True
    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        print("\n   Troubleshooting:")
        print(f"   - Check if PostgreSQL is running")
        print(f"   - Verify host: {DB_HOST}")
        print(f"   - Verify port: {DB_PORT}")
        print(f"   - Verify credentials (user: {DB_USER})")
        return False


def check_database_exists(db_name):
    """Check if a specific database exists."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        return exists
    except Exception as e:
        print(f"   Warning: Could not check if database {db_name} exists: {e}")
        return False


def create_database_if_not_exists(db_name):
    """Create database if it doesn't exist."""
    # Sanitize the database identifier before it is interpolated into SQL.
    # CREATE DATABASE cannot be parameterised, so only allow safe identifier
    # characters (alphanumeric, underscore, dollar) and replace everything else.
    db_name = re.sub(r'[^a-zA-Z0-9_$]', '_', db_name)
    print(f"📊 Checking database '{db_name}'...")
    
    if check_database_exists(db_name):
        print(f"   ✓ Database '{db_name}' exists")
        return True
    
    print(f"   Creating database '{db_name}'...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE {db_name}")
        cursor.close()
        conn.close()
        print(f"   ✓ Database '{db_name}' created")
        return True
    except Exception as e:
        print(f"   ✗ Failed to create database: {e}")
        return False


def check_system_health():
    """Check overall system health."""
    print("\n🏥 System Health Check...")
    
    health_ok = True
    
    # Check if investments table exists and has data
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database="Investments",  # Hardcoded for now
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Count investments
        cursor.execute("SELECT COUNT(*) FROM investments")
        inv_count = cursor.fetchone()[0]
        print(f"   ✓ Investments: {inv_count} total")
        
        # Count portfolios
        cursor.execute("SELECT COUNT(*) FROM investments WHERE investment_ticker = 'PORTFOLIO'")
        portfolio_count = cursor.fetchone()[0]
        
        if portfolio_count == 0:
            print("   ⚠️  No Portfolio investment found")
            health_ok = False
        elif portfolio_count == 1:
            print("   ✓ Portfolio investment exists")
        else:
            print(f"   ⚠️  Multiple Portfolio investments found ({portfolio_count})")
            health_ok = False
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")
        health_ok = False
    
    return health_ok


def display_startup_summary():
    """Display startup summary and next steps."""
    print("\n" + "=" * 70)
    print("  ✅ STARTUP COMPLETE")
    print("=" * 70)
    print()
    print("Your investment tracking system is ready!")
    print()
    print("Next Steps:")
    print("  1. Add your first investment using the API or frontend")
    print("  2. Portfolio will automatically track all investments")
    print("  3. Run maintenance tasks regularly (see maintenance.py)")
    print()
    print("Useful Commands:")
    print("  - Start API:       uvicorn investment_backend_fastapi:investment_api --host 0.0.0.0 --port 3337")
    print("  - Add investment:  # Use API endpoint /add_investment")
    print("  - View portfolio:  # Check investment with ticker 'PORTFOLIO'")
    print("  - Daily tasks:     python3 maintenance.py --daily")
    print("  - Monthly tasks:   python3 maintenance.py --monthly")
    print()


def initialize_portfolio(database_name=DEFAULT_DB):
    """Initialize the Portfolio investment."""
    print("\n💼 Initializing Portfolio investment...")
    
    try:
        # Ensure portfolio exists
        portfolio_id = ensure_portfolio_exists(database_name)
        print(f"   ✓ Portfolio investment ready (ID: {portfolio_id})")
        
        # Perform initial aggregation
        print("   Aggregating existing investments...")
        update_portfolio(database_name, silent=False)
        
        return True
        
    except Exception as e:
        print(f"   ✗ Failed to initialize portfolio: {e}")
        import traceback
        traceback.print_exc()
        return False
