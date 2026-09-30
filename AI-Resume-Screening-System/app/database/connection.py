# ============================================================
#  TalentSync / HireAI — Unified Database Connection Manager
#  Supports dual engines:
#    - SQLite: Development & automated testing (deterministic path)
#    - PostgreSQL: Production concurrency with connection pooling (psycopg 3)
# ============================================================

import os
import re
import sqlite3
from typing import Any, List, Optional, Union
from app.config.settings import ActiveConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global connection pool for PostgreSQL (lazy-initialized once)
_pg_pool = None


def is_postgres() -> bool:
    """Return True if the configured database backend is PostgreSQL."""
    db_url = getattr(ActiveConfig, "DATABASE_URL", "") or os.getenv("DATABASE_URL", "")
    return db_url.startswith(("postgresql://", "postgres://"))


def adapt_query_to_postgres(sql: str) -> str:
    """
    Translate SQLite parameter placeholders and function calls to PostgreSQL.
    CRITICAL SECURITY & CORRECTNESS:
    Tokenizes SQL to strictly preserve question marks inside string literals.
    Example:
      SELECT 'Are you sure?' AS q, id FROM users WHERE email=?
    translates to:
      SELECT 'Are you sure?' AS q, id FROM users WHERE email=%s
    """
    # Split query into alternating tokens: [outside_quotes, 'inside_quotes', outside_quotes, ...]
    tokens = re.split(r"('(?:''|[^'])*')", sql)
    for i in range(0, len(tokens), 2):
        tokens[i] = tokens[i].replace("?", "%s")
    adapted = "".join(tokens)

    # Convert SQLite datetime('now') -> PostgreSQL CURRENT_TIMESTAMP
    adapted = re.sub(r"datetime\(\s*'now'\s*\)", "CURRENT_TIMESTAMP", adapted, flags=re.IGNORECASE)
    return adapted


class PostgresCursorWrapper:
    """
    Wraps psycopg cursor to provide sqlite3 compatibility:
    - Provides .lastrowid on INSERT queries (via RETURNING id)
    - Returns dict-accessible and index-accessible rows
    """
    def __init__(self, raw_cursor):
        self._cur = raw_cursor
        self.lastrowid: Optional[int] = None
        self.rowcount: int = 0

    def execute(self, query: str, params: Any = ()):
        adapted_sql = adapt_query_to_postgres(query)
        clean_sql = adapted_sql.strip().rstrip(";")

        # Automatically support lastrowid for INSERT statements targeting tables with an id primary key
        is_insert = clean_sql.upper().startswith("INSERT INTO")
        has_returning = "RETURNING" in clean_sql.upper()

        if is_insert and not has_returning:
            # Conservative check: append RETURNING id to capture lastrowid
            sql_with_ret = f"{clean_sql} RETURNING id"
            try:
                self._cur.execute(sql_with_ret, params)
                row = self._cur.fetchone()
                if row:
                    self.lastrowid = row[0] if isinstance(row, (tuple, list)) else row.get("id", None)
                self.rowcount = self._cur.rowcount
                return self
            except Exception as e:
                # If table does not have 'id' column or RETURNING failed, fallback to original query
                logger.debug(f"RETURNING id fallback on insert: {e}")
                self._cur.connection.rollback()
                self._cur.execute(adapted_sql, params)
                self.rowcount = self._cur.rowcount
                return self

        self._cur.execute(adapted_sql, params)
        self.rowcount = self._cur.rowcount
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size)

    def __iter__(self):
        return iter(self._cur)

    def close(self):
        self._cur.close()


class PostgresConnectionContext:
    """
    Context manager for PostgreSQL connection acquired from psycopg_pool.
    Ensures safe commit on exit, rollback on exception, and connection return to pool.
    """
    def __init__(self, raw_conn, pool=None):
        self._conn = raw_conn
        self._pool = pool
        self._cursor = None

    def execute(self, query: str, params: Any = ()):
        cur = self._conn.cursor()
        wrapper = PostgresCursorWrapper(cur)
        return wrapper.execute(query, params)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._pool:
            self._pool.putconn(self._conn)
        else:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()


def _get_postgres_pool():
    """Lazy initialize PostgreSQL connection pool (min 2, max 5 per worker)."""
    global _pg_pool
    if _pg_pool is None:
        try:
            import psycopg
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            db_url = getattr(ActiveConfig, "DATABASE_URL", "") or os.getenv("DATABASE_URL", "")
            _pg_pool = ConnectionPool(
                conninfo=db_url,
                min_size=2,
                max_size=5,
                timeout=10.0,
                kwargs={"row_factory": dict_row}
            )
            logger.info("Initialized PostgreSQL connection pool (min=2, max=5)")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
            raise
    return _pg_pool


def get_db(db_file=None):
    """
    Open and return a database connection gateway.
    - PostgreSQL: Returns pooled connection with dict_row factory and query adaptation.
    - SQLite: Returns fresh SQLite connection with sqlite3.Row factory.
    Always use as a context manager: `with get_db() as conn:`.
    """
    if is_postgres():
        pool = _get_postgres_pool()
        raw_conn = pool.getconn()
        return PostgresConnectionContext(raw_conn, pool=pool)
    else:
        # SQLite Development / Testing Backend (isolated per configuration)
        if db_file is None:
            from flask import has_app_context, current_app
            if has_app_context() and current_app.config.get("DB_FILE"):
                db_file = current_app.config.get("DB_FILE")
            else:
                from app.config.settings import _detect_testing, TestingConfig
                if _detect_testing():
                    db_file = TestingConfig.DB_FILE
                else:
                    db_file = ActiveConfig.DB_FILE
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        return conn


def execute_query(query: str, params: tuple = ()) -> list[dict]:
    """Utility: run a SELECT query and return list of dicts."""
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def execute_write(query: str, params: tuple = ()) -> int:
    """
    Utility: run an INSERT / UPDATE / DELETE.
    Returns the lastrowid (useful for INSERT).
    """
    with get_db() as conn:
        cur = conn.execute(query, params)
        if hasattr(conn, "commit"):
            conn.commit()
        return getattr(cur, "lastrowid", 0) or 0
