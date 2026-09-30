# HireAI / TalentSync — Security Baseline

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Security Inspection  

---

## 1. Security Controls & Defense-in-Depth Status

| Control Area | Implementation Mechanism | Status | Notes / Findings |
| :--- | :--- | :---: | :--- |
| **Password Hashing** | Werkzeug PBKDF2 with SHA-256 | ✅ STRONG | High iteration salt hashing. Raw passwords never stored. |
| **Password Complexity Policy** | `validators.py:validate_password` | ✅ STRONG | 10–128 chars, requires upper, lower, number, special char. |
| **Brute-Force Account Lockout** | `auth_controller.py:check_account_lockout` | ✅ STRONG | 5 failed attempts locks account for 15 min (HTTP 423). |
| **Timing-Attack Resistance** | `hmac.compare_digest` | ✅ STRONG | Constant-time token verification prevents timing leaks. |
| **Session Fixation Prevention** | `session.clear()` | ✅ STRONG | Clears previous session ID before binding authenticated user. |
| **Cookie Security** | `SESSION_COOKIE_HTTPONLY=True` | ✅ STRONG | Disallows JavaScript access to session cookie (`Lax` SameSite). |
| **SQL Injection Defense** | Parameterized bindings (`?`) | ✅ STRONG | 100% of SQL queries in controllers use parameter substitution. |
| **File Traversal Defense** | UUID storage & `secure_filename` | ✅ STRONG | Original filenames never used directly as disk write targets. |
| **File Spoofing Defense** | Magic-byte signature checking | ✅ STRONG | `%PDF-` and `PK\x03\x04` validated before text parsing. |
| **Rate Limiting** | Flask-Limiter (`limits`) | ✅ PRESENT | Applied to auth and upload routes. Memory storage backend. |

---

## 2. Vulnerabilities, Exposures & Security Debt

1. **Tokens Emitted in JSON Response (Development Mode)**:
   - `resend_verification`: returns `dev_verification_token` in response body.
   - `forgot_password`: returns `dev_reset_token` in response body.
   - *Risk*: In production, tokens must be sent strictly via email, never in JSON responses.
2. **Relative Database Path (GAP-06)**:
   - `DB_FILE = "talentsync.db"` allows different working directories to access or create separate databases, risking authorization bypassing if a secondary DB has missing user records.
3. **Debug Mode Enabled**:
   - `run.py` launches with `debug=True`. In production, debug mode allows arbitrary code execution via the Werkzeug interactive debugger.
4. **Hardcoded Secrets**:
   - `SECRET_KEY` in `settings.py` generates a random key per process in dev, but must be strictly injected via environment variable in production.
   - `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`: Checked; loaded via `os.getenv()`. No live credentials committed in source code.
