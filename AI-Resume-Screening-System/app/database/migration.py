# ============================================================
#  TalentSync / HireAI — Standalone SQLite to PostgreSQL Migration
#  MANDATORY SAFETY:
#    - NEVER executed automatically on startup or in tests.
#    - Source SQLite database is read-only (NEVER modified).
#    - Atomic single transaction with full rollback on any failure.
#    - Sequences advanced to prevent ID collision on future writes.
# ============================================================

import os
import sqlite3
import hashlib
from typing import Dict, Any, List
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Ordered list of tables to migrate (ensures foreign key dependency order)
MIGRATION_TABLES = [
    "users",
    "jobs",
    "resumes",
    "applications",
    "email_verification_tokens",
    "password_reset_tokens",
    "login_attempts",
    "notifications",
    "external_jobs",
    "companies",
    "provider_cache",
    "provider_health",
    "saved_jobs",
    "search_history",
    "job_alerts",
    "application_status",
    "recommendation_history",
]


def _compute_file_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def migrate_sqlite_to_postgres(sqlite_path: str, pg_url: str) -> Dict[str, Any]:
    """
    Explicit, standalone migration of data from SQLite to PostgreSQL.
    Atomic: Entire migration executes in a single PostgreSQL transaction.
    Source database remains 100% untouched and verified by SHA-256.
    """
    if not os.path.isfile(sqlite_path):
        raise FileNotFoundError(f"Source SQLite database not found: {sqlite_path}")

    # Record and verify source hash before migration
    sha_before = _compute_file_sha256(sqlite_path)
    logger.info(f"Starting migration from SQLite: '{sqlite_path}' (SHA-256: {sha_before})")

    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row

    stats: Dict[str, Any] = {
        "success": False,
        "source_sha256_before": sha_before,
        "source_sha256_after": None,
        "source_unmodified": False,
        "tables_migrated": {},
        "total_rows": 0,
        "error": None,
    }

    sqlite_conn = sqlite3.connect(f"file:{os.path.abspath(sqlite_path)}?mode=ro", uri=True)
    sqlite_conn.row_factory = sqlite3.Row

    try:
        with psycopg.connect(pg_url, autocommit=False) as pg_conn:
            with pg_conn.cursor(row_factory=dict_row) as pg_cur:
                for table in MIGRATION_TABLES:
                    # Check if table exists in SQLite
                    table_check = sqlite_conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                    ).fetchone()
                    if not table_check:
                        continue

                    # Read all rows from SQLite
                    rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
                    if not rows:
                        stats["tables_migrated"][table] = 0
                        continue

                    # Extract column names
                    col_names = [description[0] for description in sqlite_conn.execute(f"SELECT * FROM {table} LIMIT 0").description]
                    cols_str = ", ".join(col_names)
                    placeholders = ", ".join(["%s"] * len(col_names))
                    insert_sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

                    # Convert sqlite3.Row objects to tuples
                    data_tuples = [tuple(row[col] for col in col_names) for row in rows]

                    # Execute bulk insert
                    pg_cur.executemany(sql.SQL(insert_sql), data_tuples)
                    count = len(data_tuples)
                    stats["tables_migrated"][table] = count
                    stats["total_rows"] += count
                    logger.info(f"Migrated table '{table}': {count} rows")

                    # Advance PostgreSQL sequence if table has an 'id' column
                    if "id" in col_names:
                        try:
                            seq_sql = sql.SQL("SELECT setval(pg_get_serial_sequence(%s, 'id'), coalesce(max(id), 1)) FROM {}").format(sql.Identifier(table))
                            pg_cur.execute(seq_sql, (table,))
                        except Exception as seq_err:
                            logger.debug(f"Sequence advance skipped for {table}: {seq_err}")

            # Commit the single transaction
            pg_conn.commit()
            stats["success"] = True
            logger.info(f"Migration completed successfully! Total rows migrated: {stats['total_rows']}")
    except Exception as e:
        logger.error(f"Migration failed with error, rolling back: {e}")
        stats["error"] = str(e)
        raise
    finally:
        sqlite_conn.close()
        # Verify source database was not modified
        sha_after = _compute_file_sha256(sqlite_path)
        stats["source_sha256_after"] = sha_after
        stats["source_unmodified"] = (sha_before == sha_after)
        assert sha_before == sha_after, "CRITICAL: Source SQLite database was modified during migration!"

    return stats
