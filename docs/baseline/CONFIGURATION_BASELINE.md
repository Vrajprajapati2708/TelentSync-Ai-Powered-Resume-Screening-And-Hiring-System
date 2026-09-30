# HireAI / TalentSync — Configuration Baseline

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Audit  

---

## 1. Central Configuration Settings (`app/config/settings.py`)

| Configuration Key | Configured Default Value | Source / Env Override | Evaluation & Risk Assessment |
| :--- | :--- | :--- | :--- |
| **`APP_NAME`** | `"TalentSync"` | `os.getenv("APP_NAME")` | Normal |
| **`APP_VERSION`** | `"2.0"` | `os.getenv("APP_VERSION")` | Normal |
| **`SECRET_KEY`** | Auto-generated per process in dev | `os.getenv("SECRET_KEY")` | **Redacted / Masked**. If unset in prod, raises RuntimeError |
| **`DATABASE_URL`** | `"sqlite:///talentsync.db"` | `os.getenv("DATABASE_URL")` | URL format |
| **`DB_FILE`** | `"talentsync.db"` | Fixed relative string | **RISK (GAP-06)**: Relative path causes DB divergence |
| **`UPLOAD_FOLDER`** | `"app/static/uploads/resumes"` | `os.getenv("UPLOAD_FOLDER")` | **DISCREPANCY**: resume_controller writes to `uploads/resumes` |
| **`TEMP_FOLDER`** | `"app/static/uploads/temp"` | Fixed | Normal |
| **`MAX_CONTENT_LENGTH`**| `5,242,880` (5 MB) | `os.getenv("MAX_CONTENT_LENGTH")` | Enforced at WSGI layer |
| **`ALLOWED_EXTENSIONS`**| `{"pdf", "doc", "docx"}` | Fixed | **RISK (GAP-11)**: Includes binary `.doc` which crashes parser |
| **`PORT`** | `5000` | `os.getenv("PORT")` | Normal |
| **`DEBUG`** | `True` (in development) | `os.getenv("FLASK_ENV")` | Development mode active |
| **`SESSION_COOKIE_HTTPONLY`**| `True` | Fixed | Prevents XSS cookie access |
| **`SESSION_COOKIE_SAMESITE`**| `"Lax"` | Fixed | CSRF mitigation |
| **`SESSION_COOKIE_SECURE`** | `False` (in dev) | `True` if prod | Requires HTTPS in production |
| **`PERMANENT_SESSION_LIFETIME`**| `86400` (24 Hours) | Fixed | Session duration |
| **`ADZUNA_APP_ID`** | `[REDACTED]` | `os.getenv("ADZUNA_APP_ID")` | External job aggregation |
| **`ADZUNA_APP_KEY`**| `[REDACTED]` | `os.getenv("ADZUNA_APP_KEY")` | External job aggregation |
| **`ADZUNA_COUNTRY`**| `"in"` | `os.getenv("ADZUNA_COUNTRY")` | Default to India jobs |
| **`TFIDF_VECTORIZER_PATH`**| `"trained_models/tfidf_vectorizer.pkl"` | Fixed | ML model path |

---

## 2. Rate Limiting Configuration (`app/__init__.py`)

- **Backend**: `limits` via memory storage (`memory://`).
- **Endpoint Limits**:
  - `/api/auth/login`: `10 per minute`
  - `/api/auth/register`: `5 per minute`
  - `/api/auth/forgot_password`: `3 per minute`
  - `/api/auth/reset_password`: `5 per minute`
  - `/api/auth/resend_verification`: `2 per minute`
  - `/api/upload_resume`: `5 per minute`
  - `/api/ml/train`: `2 per hour`

---

## 3. Password Security Policy (`app/utils/validators.py`)

- `MIN_PASSWORD_LENGTH = 10`
- `MAX_PASSWORD_LENGTH = 128`
- Requires at least 1 uppercase letter (`[A-Z]`)
- Requires at least 1 lowercase letter (`[a-z]`)
- Requires at least 1 number (`[0-9]`)
- Requires at least 1 special character (`[!@#$%^&*(),.?":{}|<>]`)
