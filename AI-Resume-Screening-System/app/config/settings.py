# ============================================================
#  TalentSync — Application Settings
#  Centralised configuration for all environments
# ============================================================

import os
import secrets
from dotenv import load_dotenv

# Load .env file (only used in development; ignored in production)
load_dotenv()


def _require_secret_key() -> str:
    """
    Returns SECRET_KEY from the environment.
    Generates a secure random key in development but raises an error
    in production if SECRET_KEY is not explicitly set or is insecure.
    """
    key = os.getenv("SECRET_KEY")
    env = os.getenv("FLASK_ENV", "development").lower()
    insecure_defaults = {"secret", "dev-secret", "change-me", "dev-key-please-change", "password", "test"}
    if not key:
        if env == "production":
            raise RuntimeError(
                "CRITICAL: SECRET_KEY environment variable is not set. "
                "Set a strong, random SECRET_KEY before running in production."
            )
        return secrets.token_hex(32)
    if env == "production" and key.lower() in insecure_defaults:
        raise RuntimeError(
            "CRITICAL: Insecure default SECRET_KEY detected in production. "
            "Set a strong, unique SECRET_KEY before running in production."
        )
    return key


class Config:
    """Base configuration — shared by all environments."""

    # ── Application
    APP_NAME    = os.getenv("APP_NAME", "TalentSync")
    APP_VERSION = os.getenv("APP_VERSION", "2.0")
    SECRET_KEY  = _require_secret_key()

    # ── Database (SQLite for now — swap URL for MySQL/PostgreSQL later)
    BASE_DIR     = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    DB_FILE      = os.getenv("DB_FILE", os.path.join(BASE_DIR, "talentsync.db"))
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_FILE.replace(os.sep, '/')}")

    # ── Model Artifacts Root (Deterministic, supports Docker & workspace root)
    _env_model_dir = os.getenv("MODEL_DIR")
    if _env_model_dir:
        MODEL_DIR = os.path.abspath(_env_model_dir)
    else:
        _cand = os.path.join(BASE_DIR, "trained_models")
        if not os.path.isdir(_cand):
            _cand = os.path.abspath(os.path.join(BASE_DIR, "..", "trained_models"))
        MODEL_DIR = _cand

    # ── File Upload (Deterministic absolute paths)
    _default_upload = os.path.join(BASE_DIR, "uploads", "resumes")
    if not os.path.isdir(_default_upload):
        _legacy_upload = os.path.join(BASE_DIR, "app", "static", "uploads", "resumes")
        if os.path.isdir(_legacy_upload):
            _default_upload = _legacy_upload
    UPLOAD_FOLDER      = os.getenv("UPLOAD_FOLDER", _default_upload)
    TEMP_FOLDER        = os.getenv("TEMP_FOLDER", os.path.join(BASE_DIR, "uploads", "temp"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))  # 5 MB
    ALLOWED_EXTENSIONS = {"pdf", "docx"}

    # ── Flask
    DEBUG   = os.getenv("FLASK_ENV", "development") == "development"
    TESTING = False
    PORT    = int(os.getenv("PORT", 5000))

    # ── Session / Cookie Security (OWASP hardening)
    SESSION_COOKIE_HTTPONLY = True    # JS cannot access the session cookie
    SESSION_COOKIE_SAMESITE = "Lax"  # CSRF mitigation
    # NOTE: Set SESSION_COOKIE_SECURE=True in production (requires HTTPS)
    SESSION_COOKIE_SECURE   = os.getenv("FLASK_ENV", "development") == "production"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours (in seconds)

    # ── External Providers (Adzuna)
    ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
    ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
    ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "in") # Default to India
    PROVIDER_TIMEOUT = int(os.getenv("PROVIDER_TIMEOUT", 10)) # Seconds
    PROVIDER_RETRIES = int(os.getenv("PROVIDER_RETRIES", 2))

    # ── ML / NLP
    TFIDF_VECTORIZER_PATH = "trained_models/tfidf_vectorizer.pkl"
    RECOMMENDATION_MODEL  = "trained_models/recommendation_model.pkl"
    CLASSIFIER_MODEL      = "trained_models/classifier.pkl"

    # ── Email Subsystem (GAP-12)
    MAIL_PROVIDER     = os.getenv("MAIL_PROVIDER", "test")
    MAIL_HOST         = os.getenv("MAIL_HOST", os.getenv("MAIL_SERVER", "localhost"))
    MAIL_PORT         = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME     = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD     = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS      = os.getenv("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes")
    MAIL_FROM         = os.getenv("MAIL_FROM", "noreply@talentsync.ai")
    APP_BASE_URL      = os.getenv("APP_BASE_URL", "http://localhost:5000")
    # Security: In production, tokens are strictly emailed and never returned in API responses
    EXPOSE_DEV_TOKENS = os.getenv("EXPOSE_DEV_TOKENS", "true" if os.getenv("FLASK_ENV") == "development" else "false").lower() in ("true", "1", "yes")

    # ── OCR Subsystem (GAP-14)
    OCR_ENABLED         = os.getenv("OCR_ENABLED", "true").lower() in ("true", "1", "yes")
    OCR_ENGINE          = os.getenv("OCR_ENGINE", "auto")
    TESSERACT_CMD       = os.getenv("TESSERACT_CMD", "")
    OCR_MAX_PAGES       = int(os.getenv("OCR_MAX_PAGES", 10))
    OCR_TIMEOUT_SECONDS = int(os.getenv("OCR_TIMEOUT_SECONDS", 15))
    OCR_MIN_TEXT_CHARS  = int(os.getenv("OCR_MIN_TEXT_CHARS", 50))


    # ── Rate Limiting (GAP-16)
    REDIS_URL               = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RATELIMIT_STORAGE_URI   = os.getenv("RATELIMIT_STORAGE_URI", os.getenv("REDIS_URL", "memory://"))
    RATELIMIT_STRATEGY      = "moving-window"
    RATELIMIT_DEFAULT       = []
    RATELIMIT_KEY_PREFIX    = "talentsync_rl:"
    RATELIMIT_IN_MEMORY_FALLBACK = ["3/minute"]
    RATELIMIT_SWALLOW_ERRORS = True


class DevelopmentConfig(Config):
    DEBUG   = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG   = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    EXPOSE_DEV_TOKENS     = False
    MAIL_PROVIDER         = os.getenv("MAIL_PROVIDER", "smtp")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", os.getenv("REDIS_URL", "redis://redis:6379/0"))


import sys
import tempfile


def _detect_testing() -> bool:
    """Detect if execution is running inside a test framework or testing environment."""
    if os.getenv("FLASK_ENV", "").lower() == "testing":
        return True
    if "unittest" in sys.modules or "pytest" in sys.modules:
        return True
    if any("unittest" in str(arg) or "pytest" in str(arg) or "test" in str(arg).lower() for arg in sys.argv):
        return True
    return False


class TestingConfig(Config):
    DEBUG                 = False
    TESTING               = True
    MAIL_PROVIDER         = "test"
    EXPOSE_DEV_TOKENS     = True
    RATELIMIT_STORAGE_URI = "memory://"

    # ── Isolated Test Storage (GAP Remediation Steps 3 & 4)
    # Guaranteed distinct from persistent production/development DB and upload storage
    _TEST_DIR             = os.path.join(tempfile.gettempdir(), "talentsync_test_env")
    DB_FILE               = os.getenv("TEST_DB_FILE", os.path.join(_TEST_DIR, "talentsync_test.db"))
    UPLOAD_FOLDER         = os.getenv("TEST_UPLOAD_FOLDER", os.path.join(_TEST_DIR, "uploads", "resumes"))
    TEMP_FOLDER           = os.path.join(_TEST_DIR, "uploads", "temp")


# Export the active config based on the environment variable
_env = os.getenv("FLASK_ENV", "development").lower()
if _env == "production":
    ActiveConfig = ProductionConfig
elif _env == "testing":
    ActiveConfig = TestingConfig
else:
    ActiveConfig = DevelopmentConfig


