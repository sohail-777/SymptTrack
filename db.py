"""
db.py — lightweight MySQL connection pool + query helpers.

We deliberately avoid a heavyweight ORM so the whole data layer
is easy to read in one file. All queries use parameterised
placeholders (%s) to prevent SQL injection.
"""
import mysql.connector
from mysql.connector import pooling, Error
from config import Config

_pool = None


def init_pool():
    """Create the MySQL connection pool once at app start-up."""
    global _pool
    if _pool is not None:
        return _pool
    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name="symptrack_pool",
            pool_size=8,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            autocommit=True,
            charset="utf8mb4",
            use_unicode=True,
        )
        print("[db] MySQL connection pool ready.")
    except Error as e:
        print(f"[db] ERROR creating connection pool: {e}")
        _pool = None
    return _pool


def get_connection():
    global _pool
    if _pool is None:
        init_pool()
    if _pool is None:
        raise RuntimeError(
            "Could not connect to MySQL. Check DB_HOST/DB_USER/DB_PASSWORD/DB_NAME "
            "in your .env file and make sure the MySQL server is running and the "
            "'symptrack' database has been created from database/schema.sql."
        )
    return _pool.get_connection()


def query(sql, params=None, fetch="all"):
    """
    Run a SELECT statement.
    fetch: 'all' | 'one'
    Returns list[dict] or dict|None
    """
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        result = cur.fetchall() if fetch == "all" else cur.fetchone()
        cur.close()
        return result
    finally:
        conn.close()


def execute(sql, params=None):
    """Run an INSERT/UPDATE/DELETE. Returns (lastrowid, rowcount)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        last_id, row_count = cur.lastrowid, cur.rowcount
        cur.close()
        return last_id, row_count
    finally:
        conn.close()


def executemany(sql, param_list):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany(sql, param_list)
        conn.commit()
        cur.close()
    finally:
        conn.close()
