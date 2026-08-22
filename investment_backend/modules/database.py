import os
import psycopg2
import hashlib
import binascii
from psycopg2.extensions import AsIs, ISOLATION_LEVEL_AUTOCOMMIT
from contextlib import contextmanager
from typing import Optional

# Configuration constants
DB_HOST = os.environ.get("POSTGRES_HOST", "ThinkTank")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "changeme")
DB_PORT = int(os.environ.get("POSTGRES_PORT", 5432))
DEFAULT_DB = os.environ.get("POSTGRES_DB", os.environ.get("INVESTMENTS_DB", "investments_app"))
USERS_DB = os.environ.get("USERS_DB", DEFAULT_DB)

def hash_password(password: str) -> str:
    """Hash a password using SHA-512 PBKDF2 with 100,000 iterations and random salt."""
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a stored password against one provided by user."""
    if not stored_password or len(stored_password) < 64:
        return False
    salt = stored_password[:64]
    stored_hash = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha512', provided_password.encode('utf-8'), salt.encode('ascii'), 100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == stored_hash

@contextmanager
def get_db_connection(database_name: str = None, user_id: Optional[int] = None):
    """
    Context manager for database connections.
    Always targets central DEFAULT_DB ('investments_app') and sets session `app.current_user_id` for PostgreSQL RLS policies.
    """
    target_db = "postgres" if database_name == "postgres" else DEFAULT_DB
    conn = psycopg2.connect(
        host=DB_HOST,
        database=target_db,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    try:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT set_config('app.current_user_id', %s, false)", (str(user_id),))
        yield conn, cursor
    finally:
        conn.close()

def create_connection(database_name: str = None, user_id: Optional[int] = None):
    """Legacy connection creator."""
    target_db = "postgres" if database_name == "postgres" else DEFAULT_DB
    conn = psycopg2.connect(
        host=DB_HOST,
        database=target_db,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("SELECT set_config('app.current_user_id', %s, false)", (str(user_id),))
    return conn, cursor

def add_user(username: str, email: str, password: str, full_name: str = None) -> dict:
    """Add a new user to the central database."""
    password_hash = hash_password(password)
    sanitized_name = "".join([c for c in username.lower() if c.isalnum() or c == '_'])[:63]
    database_name = CENTRAL_DB = DEFAULT_DB

    with get_db_connection(DEFAULT_DB) as (conn, cursor):
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, full_name, database_name) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (username, email, password_hash, full_name, database_name)
        )
        new_id = cursor.fetchone()[0]
        conn.commit()

    from .auth import create_jwt_token
    token = create_jwt_token({
        "sub": str(new_id),
        "username": username,
        "email": email,
        "full_name": full_name,
        "database_name": database_name
    })

    return {
        'id': new_id,
        'username': username,
        'email': email,
        'full_name': full_name,
        'database_name': database_name,
        'token': token
    }

def verify_user(username: str, password: str) -> Optional[dict]:
    """Verify user credentials and return user info with JWT token."""
    with get_db_connection(DEFAULT_DB) as (conn, cursor):
        cursor.execute(
            "SELECT id, username, email, password_hash, full_name, database_name FROM users WHERE username = %s OR email = %s",
            (username, username)
        )
        user = cursor.fetchone()
        if user and verify_password(user[3], password):
            u_id = user[0]
            u_name = user[1]
            u_email = user[2]
            u_fullname = user[4]
            u_dbname = user[5] or DEFAULT_DB
            
            from .auth import create_jwt_token
            token = create_jwt_token({
                "sub": str(u_id),
                "username": u_name,
                "email": u_email,
                "full_name": u_fullname,
                "database_name": u_dbname
            })
            
            return {
                'id': u_id,
                'username': u_name,
                'email': u_email,
                'full_name': u_fullname,
                'database_name': u_dbname,
                'token': token
            }
    return None

def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username without password verification."""
    with get_db_connection(DEFAULT_DB) as (conn, cursor):
        cursor.execute(
            "SELECT id, username, email, full_name, database_name FROM users WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'full_name': user[3],
                'database_name': user[4] or DEFAULT_DB
            }
    return None

# ---------------------------------------------------------------------------
# Configuration helpers — read from `configuration` table scoped by user_id
# ---------------------------------------------------------------------------
_config_cache: dict = {}
_config_cache_expiry = None
_CONFIG_CACHE_TTL = 300  # seconds

def get_config_value(key: str, default=None, database_name: str = None, user_id: Optional[int] = None):
    """Read a setting from configuration table scoped by user_id."""
    import time
    global _config_cache, _config_cache_expiry

    db = database_name or DEFAULT_DB
    cache_key = f"{user_id or 0}:{key}"

    now = time.time()
    if _config_cache_expiry and now < _config_cache_expiry and cache_key in _config_cache:
        return _config_cache[cache_key]

    try:
        with get_db_connection(db, user_id=user_id) as (conn, cursor):
            if user_id is not None:
                cursor.execute("SELECT setting_value FROM configuration WHERE user_id = %s AND setting_key = %s", (user_id, key))
            else:
                cursor.execute("SELECT setting_value FROM configuration WHERE setting_key = %s LIMIT 1", (key,))
            row = cursor.fetchone()
            val = row[0] if row else default
            _config_cache[cache_key] = val
            _config_cache_expiry = now + _CONFIG_CACHE_TTL
            return val
    except Exception:
        return default

def get_all_config(database_name: str = None, user_id: Optional[int] = None) -> dict:
    """Return full configuration dict from configuration table scoped by user_id."""
    db = database_name or DEFAULT_DB
    try:
        with get_db_connection(db, user_id=user_id) as (conn, cursor):
            if user_id is not None:
                cursor.execute(
                    "SELECT setting_key, setting_value FROM configuration WHERE user_id = %s ORDER BY setting_category, setting_key",
                    (user_id,)
                )
            else:
                cursor.execute("SELECT setting_key, setting_value FROM configuration ORDER BY setting_category, setting_key")
            return {row[0]: row[1] for row in cursor.fetchall()}
    except Exception:
        return {}

def invalidate_config_cache(database_name: str = None, user_id: Optional[int] = None):
    """Clear the in-memory config cache."""
    global _config_cache, _config_cache_expiry
    _config_cache = {}
    _config_cache_expiry = None

def get_asset_manager_url_patterns(database_name: str = None) -> dict:
    """Load URL patterns for asset managers from database."""
    db = database_name or DEFAULT_DB
    patterns = {}
    try:
        with get_db_connection(db) as (conn, cursor):
            cursor.execute("""
                SELECT manager_name_normalized, factsheet_type, url_pattern, pattern_priority
                FROM asset_manager_url_patterns
                WHERE is_active = true
                ORDER BY manager_name_normalized, factsheet_type, pattern_priority
            """)
            for row in cursor.fetchall():
                manager_norm, ftype, pattern, priority = row
                if manager_norm not in patterns: patterns[manager_norm] = {}
                if ftype not in patterns[manager_norm]: patterns[manager_norm][ftype] = []
                patterns[manager_norm][ftype].append((pattern, priority))
    except Exception as e:
        patterns = {}
    return patterns

def invalidate_asset_manager_patterns_cache(database_name: str = None):
    pass
