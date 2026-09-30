# ============================================================
#  TalentSync — System Health & Infrastructure Probe Service
#  Provides comprehensive liveness and readiness diagnostics
#  for Database, Redis/Limiter, and Machine Learning subsystems.
#  STRICT SECURITY: Never exposes credentials, URLs, or host paths.
# ============================================================

import os
import time
from app.utils.logger import get_logger

logger = get_logger(__name__)


def check_database_health() -> tuple[bool, str]:
    """Verify primary database connectivity by executing a lightweight probe."""
    try:
        from app.database.connection import get_db
        with get_db() as conn:
            row = conn.execute("SELECT 1 AS probe").fetchone()
            if row and (row["probe"] == 1 or row[0] == 1):
                return True, "connected"
        return False, "query returned unexpected result"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False, f"database unavailable: {type(e).__name__}"


def check_redis_health() -> tuple[bool, str]:
    """
    Verify Redis connectivity for distributed rate limiting.
    If using memory:// in development, returns 'in-memory (dev)'.
    If Redis is unreachable, logs CRITICAL alert indicating emergency fallback.
    """
    try:
        from flask import current_app
        storage_uri = current_app.config.get("RATELIMIT_STORAGE_URI", "memory://") if current_app else os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    except Exception:
        storage_uri = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    if not storage_uri or storage_uri.startswith("memory://"):
        return True, "in-memory (dev)"

    if storage_uri.startswith(("redis://", "rediss://")):
        try:
            import redis
            client = redis.Redis.from_url(storage_uri, socket_timeout=1.5, socket_connect_timeout=1.5)
            if client.ping():
                return True, "connected"
            return False, "ping failed"
        except Exception as e:
            logger.critical(f"CRITICAL: Redis unreachable, emergency rate-limiting active. Details: {e}")
            return False, f"redis unavailable: {type(e).__name__}"

    return True, "custom storage"


def check_ml_health() -> tuple[bool, str]:
    """Verify ML models availability and inference readiness."""
    try:
        from app.ml.ml_pipeline import get_pipeline_status
        status = get_pipeline_status()
        health = status.get("health", "unknown")
        if health in ("healthy", "ready"):
            return True, "ready"
        return True, f"degraded ({health})"
    except Exception as e:
        logger.warning(f"ML health probe encountered error: {e}")
        return False, f"ml degraded: {type(e).__name__}"


def get_system_health() -> tuple[dict, int]:
    """
    Collect aggregated system health status.
    Returns (payload_dict, http_status_code).
    HTTP 200 = healthy or operating with fallback.
    HTTP 503 = critical database failure.
    """
    db_ok, db_msg = check_database_health()
    redis_ok, redis_msg = check_redis_health()
    ml_ok, ml_msg = check_ml_health()

    is_healthy = db_ok
    status_str = "healthy" if is_healthy and redis_ok else "degraded" if db_ok else "unhealthy"
    http_status = 200 if is_healthy else 503

    payload = {
        "status": status_str,
        "database": db_msg,
        "redis": redis_msg,
        "ml": ml_msg,
        "timestamp": int(time.time()),
    }
    return payload, http_status
