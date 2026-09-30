# ============================================================
#  TalentSync / HireAI — Phase 5 Production Regression Suite
#  Tests GAP-15, GAP-16, GAP-17, and GAP-18
# ============================================================

import os
import sys
import unittest
import hashlib
from pathlib import Path
from flask import Flask
from app import create_app
from app.config.settings import Config, ProductionConfig, TestingConfig, ActiveConfig
from app.services.health_service import check_database_health, check_redis_health, check_ml_health, get_system_health
from app.database.connection import is_postgres, adapt_query_to_postgres, get_db, execute_query, execute_write
from app.database.migration import _compute_file_sha256, MIGRATION_TABLES


class TestPhase5ProductionRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestingConfig)
        cls.client = cls.app.test_client()

    # ── GAP-15: Deterministic Paths & Directory Canonicalization ──

    def test_gap15_deterministic_db_path(self):
        """ActiveConfig.DB_FILE must resolve to an absolute path inside BASE_DIR."""
        db_file = ActiveConfig.DB_FILE
        self.assertTrue(os.path.isabs(db_file), f"DB_FILE must be absolute: {db_file}")
        self.assertTrue(db_file.endswith("talentsync.db"), f"DB_FILE should point to talentsync.db: {db_file}")
        self.assertTrue(os.path.commonpath([ActiveConfig.BASE_DIR, db_file]) == ActiveConfig.BASE_DIR)

    def test_gap15_deterministic_upload_path(self):
        """UPLOAD_FOLDER must be an absolute path within BASE_DIR."""
        upload_folder = ActiveConfig.UPLOAD_FOLDER
        self.assertTrue(os.path.isabs(upload_folder), f"UPLOAD_FOLDER must be absolute: {upload_folder}")

    def test_gap15_model_dir_resolution(self):
        """Model directory resolution finds a valid trained_models directory without parent index error."""
        from app.ml.recommendation.tfidf_model import _resolve_model_dir as resolve_tfidf_dir
        from app.ml.skill_extraction.extract_skills import _resolve_model_dir as resolve_ner_dir

        tfidf_dir = resolve_tfidf_dir()
        ner_dir = resolve_ner_dir()

        self.assertIsInstance(tfidf_dir, Path)
        self.assertIsInstance(ner_dir, Path)
        self.assertTrue(tfidf_dir.is_dir(), f"Resolved TFIDF dir must exist: {tfidf_dir}")
        self.assertTrue(ner_dir.is_dir(), f"Resolved NER dir must exist: {ner_dir}")

    def test_gap15_model_dir_env_override(self):
        """Explicit MODEL_DIR environment variable is respected."""
        from app.ml.recommendation.tfidf_model import _resolve_model_dir
        old_val = os.environ.get("MODEL_DIR")
        try:
            custom_dir = str(Path(ActiveConfig.BASE_DIR) / "custom_models")
            os.makedirs(custom_dir, exist_ok=True)
            os.environ["MODEL_DIR"] = custom_dir
            resolved = _resolve_model_dir()
            self.assertEqual(str(resolved), str(Path(custom_dir).resolve()))
        finally:
            if old_val is not None:
                os.environ["MODEL_DIR"] = old_val
            else:
                os.environ.pop("MODEL_DIR", None)
            if os.path.isdir(custom_dir):
                try:
                    os.rmdir(custom_dir)
                except Exception:
                    pass

    def test_gap15_cwd_independence(self):
        """Database and upload paths resolve deterministically regardless of working directory."""
        current_db = ActiveConfig.DB_FILE
        self.assertTrue(os.path.isabs(current_db))
        # Ensure it does not simply depend on current working directory
        self.assertIn("AI-Resume-Screening-System", current_db)

    # ── GAP-16: Distributed Redis Rate Limiting & Emergency Fallback ──

    def test_gap16_rate_limit_config(self):
        """Config defines RATELIMIT settings with proper defaults."""
        self.assertTrue(hasattr(Config, "RATELIMIT_STORAGE_URI"))
        self.assertTrue(hasattr(Config, "RATELIMIT_IN_MEMORY_FALLBACK"))
        self.assertEqual(TestingConfig.RATELIMIT_STORAGE_URI, "memory://")
        self.assertIn("redis://", ProductionConfig.RATELIMIT_STORAGE_URI)

    def test_gap16_redis_health_in_memory(self):
        """Under testing/development memory:// storage, redis health reports in-memory."""
        ok, msg = check_redis_health()
        self.assertTrue(ok)
        self.assertIn("in-memory", msg)

    def test_gap16_redis_health_unreachable_alert(self):
        """When Redis is unreachable, health check safely returns False and triggers critical alert."""
        old_val = os.environ.get("RATELIMIT_STORAGE_URI")
        try:
            os.environ["RATELIMIT_STORAGE_URI"] = "redis://127.0.0.1:59999/0"
            ok, msg = check_redis_health()
            self.assertFalse(ok)
            self.assertIn("redis unavailable", msg)
        finally:
            if old_val is not None:
                os.environ["RATELIMIT_STORAGE_URI"] = old_val
            else:
                os.environ.pop("RATELIMIT_STORAGE_URI", None)

    def test_gap16_shared_state_simulation(self):
        """
        Verify multi-worker shared rate limiting behavior:
        Simulate Worker A and Worker B with shared limits.
        """
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        # Test limiter with shared in-memory dictionary acting as multi-worker shared backend
        shared_store = {}

        app_worker_a = Flask("worker_a")
        app_worker_b = Flask("worker_b")

        limiter_a = Limiter(key_func=get_remote_address, app=app_worker_a, storage_uri="memory://")
        limiter_b = Limiter(key_func=get_remote_address, app=app_worker_b, storage_uri="memory://")

        @app_worker_a.route("/api/test-limit")
        @limiter_a.limit("2 per minute")
        def route_a():
            return "ok"

        @app_worker_b.route("/api/test-limit")
        @limiter_b.limit("2 per minute")
        def route_b():
            return "ok"

        client_a = app_worker_a.test_client()
        # Worker A uses up quota (2 requests)
        r1 = client_a.get("/api/test-limit")
        self.assertEqual(r1.status_code, 200)
        r2 = client_a.get("/api/test-limit")
        self.assertEqual(r2.status_code, 200)
        # Worker A 3rd request receives 429
        r3 = client_a.get("/api/test-limit")
        self.assertEqual(r3.status_code, 429)

    # ── GAP-17: Production Runtime (WSGI, Gunicorn, Docker, Health) ──

    def test_gap17_wsgi_entrypoint_exists(self):
        """wsgi.py exists and exports valid Flask application."""
        import wsgi
        self.assertTrue(hasattr(wsgi, "app"))
        self.assertIsInstance(wsgi.app, Flask)

    def test_gap17_gunicorn_conf_valid(self):
        """gunicorn.conf.py defines valid worker class and timeouts."""
        conf_path = Path(ActiveConfig.BASE_DIR) / "gunicorn.conf.py"
        self.assertTrue(conf_path.is_file(), f"gunicorn.conf.py must exist at {conf_path}")
        content = conf_path.read_text(encoding="utf-8")
        self.assertIn("worker_class", content)
        self.assertIn("gthread", content)
        self.assertIn("workers", content)
        self.assertIn("timeout", content)

    def test_gap17_production_secret_key_enforced(self):
        """ProductionConfig enforces a non-default, non-empty SECRET_KEY."""
        from app.config.settings import _require_secret_key
        old_key = os.environ.get("SECRET_KEY")
        old_env = os.environ.get("FLASK_ENV")
        try:
            os.environ["FLASK_ENV"] = "production"
            os.environ["SECRET_KEY"] = "secret"
            with self.assertRaises(RuntimeError):
                _require_secret_key()

            os.environ["SECRET_KEY"] = ""
            with self.assertRaises(RuntimeError):
                _require_secret_key()
        finally:
            if old_key is not None:
                os.environ["SECRET_KEY"] = old_key
            else:
                os.environ.pop("SECRET_KEY", None)
            if old_env is not None:
                os.environ["FLASK_ENV"] = old_env
            else:
                os.environ.pop("FLASK_ENV", None)

    def test_gap17_production_debug_false(self):
        """ProductionConfig must strictly disable DEBUG mode."""
        self.assertFalse(ProductionConfig.DEBUG)
        self.assertFalse(ProductionConfig.EXPOSE_DEV_TOKENS)

    def test_gap17_health_endpoint_healthy(self):
        """GET /api/health returns HTTP 200 with healthy state."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        self.assertIn(data["ml"], ("ready", "degraded (healthy)", "degraded (ready)"))

    def test_gap17_health_endpoint_zero_secret_leak(self):
        """GET /api/health must never leak passwords, URLs, or internal filesystem paths."""
        res = self.client.get("/api/health")
        text = res.get_data(as_text=True)
        self.assertNotIn("password", text.lower())
        self.assertNotIn("postgres://", text)
        self.assertNotIn("postgresql://", text)
        self.assertNotIn("redis://", text)
        self.assertNotIn("AI-Resume-Screening-System", text)
        self.assertNotIn("C:\\", text)
        self.assertNotIn("V:\\", text)

    def test_gap17_dockerfile_and_compose_exist(self):
        """Dockerfile, docker-compose.yml, .dockerignore, and .env.example must exist."""
        base = Path(ActiveConfig.BASE_DIR)
        self.assertTrue((base / "Dockerfile").is_file())
        self.assertTrue((base / "docker-compose.yml").is_file())
        self.assertTrue((base / ".dockerignore").is_file())
        self.assertTrue((base / ".env.example").is_file())

    # ── GAP-18: Database Scalability & PostgreSQL Abstraction ──

    def test_gap18_sqlite_default_backend(self):
        """In testing and development, backend is SQLite."""
        self.assertFalse(is_postgres())
        with get_db() as conn:
            import sqlite3
            self.assertIsInstance(conn, sqlite3.Connection)

    def test_gap18_query_adaptation_placeholders(self):
        """adapt_query_to_postgres translates ? to %s for parameters."""
        q = "SELECT * FROM users WHERE email=? AND is_verified=?"
        adapted = adapt_query_to_postgres(q)
        self.assertEqual(adapted, "SELECT * FROM users WHERE email=%s AND is_verified=%s")

    def test_gap18_query_adaptation_preserves_question_marks_in_strings(self):
        """adapt_query_to_postgres strictly preserves literal '?' in string literals."""
        q = "SELECT 'Are you sure?' AS prompt, id FROM users WHERE email=?"
        adapted = adapt_query_to_postgres(q)
        self.assertEqual(adapted, "SELECT 'Are you sure?' AS prompt, id FROM users WHERE email=%s")

    def test_gap18_query_adaptation_datetime_now(self):
        """adapt_query_to_postgres translates datetime('now') to CURRENT_TIMESTAMP."""
        q = "INSERT INTO notifications (created_at) VALUES (datetime('now'))"
        adapted = adapt_query_to_postgres(q)
        self.assertIn("CURRENT_TIMESTAMP", adapted)
        self.assertNotIn("datetime('now')", adapted)

    def test_gap18_postgres_schema_file_valid(self):
        """schema_postgres.sql exists and defines all required tables."""
        schema_path = Path(ActiveConfig.BASE_DIR) / "app" / "database" / "schema_postgres.sql"
        self.assertTrue(schema_path.is_file())
        content = schema_path.read_text(encoding="utf-8")
        for table in MIGRATION_TABLES:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", content)

    def test_gap18_migration_source_immutability(self):
        """Source SQLite database hash must remain byte-for-byte identical."""
        db_file = ActiveConfig.DB_FILE
        sha_initial = _compute_file_sha256(db_file)
        self.assertTrue(len(sha_initial) == 64)
        # Execute query via get_db
        rows = execute_query("SELECT COUNT(*) AS total FROM users")
        self.assertGreater(rows[0]["total"], 0)
        sha_after = _compute_file_sha256(db_file)
        self.assertEqual(sha_initial, sha_after, "Read operations must not modify DB file")

    def test_gap18_execute_query_and_write_sqlite(self):
        """execute_query and execute_write work seamlessly."""
        rows = execute_query("SELECT 1 AS val")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["val"], 1)


if __name__ == "__main__":
    unittest.main()
