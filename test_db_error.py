from investment_backend.modules.database import get_db_connection
import psycopg2

try:
    with get_db_connection("Investments") as (conn, cursor):
        cursor.execute("DELETE FROM investments WHERE id = 45")
        conn.commit()
except Exception as e:
    print(f"Exception type: {type(e).__name__}")
    print(f"Exception: {e}")
