# ============================================================
#  TalentSync — Auth Controller (v0.2 P0 Security Core)
#  Business logic for login, register, email verification,
#  password reset tokens, and account lockout tracking.
# ============================================================

import os
import sqlite3
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app.database.connection import get_db
from app.utils.validators import validate_email, validate_password, validate_required_fields
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Allowed roles on registration
ALLOWED_ROLES = {'candidate', 'hr'}
PRIVILEGED_ROLES = {'candidate', 'hr', 'admin'}

# Lockout configuration: 5 failed attempts within 15 minutes
LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW_MINUTES = 15


# ── Account Lockout & Attempt Tracking ────────────────────────

def check_account_lockout(email: str) -> tuple[bool, str]:
    """
    Check if an email account is currently locked out due to
    5+ consecutive failed login attempts in the last 15 minutes.
    Returns (is_locked, message).
    """
    if not email:
        return False, ""

    window_start = (datetime.now() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)).strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:
        # Check attempts in window
        attempts = conn.execute(
            """SELECT success FROM login_attempts 
               WHERE email=? AND attempted_at >= ? 
               ORDER BY id DESC LIMIT ?""",
            (email.strip().lower(), window_start, LOCKOUT_THRESHOLD)
        ).fetchall()

    if len(attempts) >= LOCKOUT_THRESHOLD:
        # If all recent attempts in threshold window were failures
        if all(r['success'] == 0 for r in attempts):
            logger.warning(f"Account locked out due to brute force attempts: {email}")
            return True, f"Account temporarily locked due to multiple failed login attempts. Please try again in {LOCKOUT_WINDOW_MINUTES} minutes."

    return False, ""


def record_login_attempt(email: str, ip_address: str, success: bool):
    """Record a login attempt (success or fail) in the login_attempts table."""
    if not email:
        return
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO login_attempts (email, ip_address, success, attempted_at)
                   VALUES (?, ?, ?, ?)""",
                (email.strip().lower(), ip_address or '127.0.0.1', 1 if success else 0,
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to record login attempt: {e}")


# ── Login & Registration ─────────────────────────────────────

def login_user(email: str, password: str, ip_address: str = '127.0.0.1') -> dict:
    """Authenticate a user with per-account brute-force lockout checking."""
    if not email or not password:
        return {'success': False, 'message': 'Email and password are required.'}

    clean_email = email.strip().lower()

    # 1. Check account lockout status first
    is_locked, lock_msg = check_account_lockout(clean_email)
    if is_locked:
        record_login_attempt(clean_email, ip_address, success=False)
        return {'success': False, 'message': lock_msg, 'is_locked': True}

    # 2. Fetch user from DB
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (clean_email,)
        ).fetchone()

    # Generic error message to prevent account enumeration
    if not user:
        record_login_attempt(clean_email, ip_address, success=False)
        return {'success': False, 'message': 'Invalid email or password.'}

    # 3. Verify password hash
    try:
        is_valid = check_password_hash(user['password'], password)
    except Exception:
        is_valid = False

    if not is_valid:
        record_login_attempt(clean_email, ip_address, success=False)
        return {'success': False, 'message': 'Invalid email or password.'}

    # 4. Check account status / email verification
    # users.is_verified is the universal account status: 1 = active, 0 = inactive/unverified
    # For candidates: is_verified=0 reflects unverified email (SEC-02 contract preserved)
    # For HR/admin: is_verified=0 reflects deactivated account (Platform Admin deactivation)
    user_role = user['role'] if 'role' in user.keys() else 'candidate'
    is_ver = user['is_verified'] if 'is_verified' in user.keys() else 0
    if not is_ver:
        record_login_attempt(clean_email, ip_address, success=False)
        if user_role == 'candidate':
            return {
                'success': False,
                'message': 'Please verify your email address before logging in.',
                'not_verified': True,
                'status_code': 403
            }
        else:
            return {
                'success': False,
                'message': 'Your account has been deactivated. Please contact an administrator.',
                'is_deactivated': True,
                'not_verified': True,
                'status_code': 403
            }

    # 5. Success — record login attempt
    record_login_attempt(clean_email, ip_address, success=True)
    logger.info(f"Login successful: {clean_email}")

    u_dict = dict(user)
    u_dict.pop('password', None)
    return {'success': True, 'user': u_dict}


def _should_expose_dev_tokens() -> bool:
    """Check whether dev diagnostic tokens can be returned in responses."""
    try:
        from flask import current_app
        if current_app:
            return bool(current_app.config.get("EXPOSE_DEV_TOKENS", False))
    except (RuntimeError, ImportError):
        pass

    if os.getenv("FLASK_ENV") == "production":
        return False
    return os.getenv("EXPOSE_DEV_TOKENS", "true").lower() in ("true", "1", "yes")


def register_user(
    name: str,
    email: str,
    password: str,
    role: str = 'candidate',
    allow_privileged: bool = False,
    is_verified: int = 0
) -> dict:
    """Create a new user account with unverified default status and token generation."""
    valid, msg = validate_required_fields(
        {'name': name, 'email': email, 'password': password, 'role': role},
        ['name', 'email', 'password', 'role']
    )
    if not valid:
        return {'success': False, 'message': msg}

    clean_email = email.strip().lower()

    if not validate_email(clean_email):
        return {'success': False, 'message': 'Invalid email address.'}

    ok, err = validate_password(password)
    if not ok:
        return {'success': False, 'message': err}

    # SEC-01: Public self-registration permits only candidate accounts
    if role != 'candidate' and not allow_privileged:
        return {
            'success': False,
            'message': 'Invalid role. Privileged accounts cannot be created through public registration.',
            'status_code': 403
        }

    allowed_roles = PRIVILEGED_ROLES if allow_privileged else ALLOWED_ROLES
    if role not in allowed_roles:
        return {'success': False, 'message': "Invalid role.", 'status_code': 403}

    hashed_password = generate_password_hash(password)

    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, password, role, is_verified) VALUES (?, ?, ?, ?, ?)",
                (name.strip(), clean_email, hashed_password, role, 1 if is_verified else 0)
            )
            user_id = cur.lastrowid
            assert user_id is not None, "INSERT must return a valid lastrowid"

            # Welcome notification
            conn.execute(
                "INSERT INTO notifications (user_id, title, message, type, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, 'Welcome to TalentSync! 🎉',
                 'Account created. Please verify your email address.',
                 'info', datetime.now().strftime('%Y-%m-%d %H:%M'))
            )
            conn.commit()

        # Generate email verification token and send verification email
        raw_token = generate_email_verification_token(user_id)
        from app.services.email_service import send_verification_email
        send_verification_email(clean_email, raw_token, name)

        logger.info(f"New user registered: {clean_email} ({role}), user_id={user_id}")

        expose_dev = _should_expose_dev_tokens()

        resp = {
            'success': True,
            'message': 'Registration successful! Please check your email to verify your account.',
            'user': {'id': user_id, 'name': name, 'email': clean_email, 'role': role, 'ats_score': 0, 'skills': '', 'is_verified': 0},
        }
        if expose_dev:
            resp['dev_verification_token'] = raw_token
        return resp
    except sqlite3.IntegrityError:
        return {'success': False, 'message': 'Email already registered.'}


# ── Email Verification Token Logic ─────────────────────────────

def generate_email_verification_token(user_id: int) -> str:
    """Generate a 32-byte URL-safe token, store SHA-256 hash in DB with 24-hr expiration."""
    raw_token  = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    expires_at = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:
        conn.execute(
            """INSERT INTO email_verification_tokens (user_id, token_hash, expires_at, is_used)
               VALUES (?, ?, ?, 0)""",
            (user_id, token_hash, expires_at)
        )
        conn.commit()

    return raw_token


def verify_email_token(raw_token: str) -> dict:
    """Verify an email verification token using direct hash query and constant-time comparison (SEC-06)."""
    if not raw_token:
        return {'success': False, 'message': 'Verification token is required.'}

    target_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    now_str     = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:
        token_rec = conn.execute(
            """SELECT * FROM email_verification_tokens 
               WHERE token_hash = ? AND is_used = 0 AND expires_at > ?""",
            (target_hash, now_str)
        ).fetchone()

        if not token_rec or not hmac.compare_digest(token_rec['token_hash'], target_hash):
            return {'success': False, 'message': 'Invalid or expired verification token.'}

        user_id = token_rec['user_id']

        # Activate user
        conn.execute("UPDATE users SET is_verified=1 WHERE id=?", (user_id,))
        # Mark token used
        conn.execute("UPDATE email_verification_tokens SET is_used=1 WHERE id=?", (token_rec['id'],))
        conn.commit()

    logger.info(f"Email verified for user_id={user_id}")
    return {'success': True, 'message': 'Email verified successfully! You can now log in.'}


# ── Password Reset Token Logic ───────────────────────────────

def generate_password_reset_token(email: str) -> dict:
    """
    Generate password reset token for an email address.
    Anti-enumeration: Always returns success message even if email is not found.
    Dispatches password reset email securely.
    """
    if not email:
        return {'success': False, 'message': 'Email is required.'}

    clean_email = email.strip().lower()
    raw_token   = None

    with get_db() as conn:
        user = conn.execute("SELECT id, name FROM users WHERE email=?", (clean_email,)).fetchone()

        if user:
            user_id    = user['id']
            user_name  = user['name'] if 'name' in user.keys() else ""
            raw_token  = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
            expires_at = (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')

            # Invalidate prior unused tokens for this user
            conn.execute("UPDATE password_reset_tokens SET is_used=1 WHERE user_id=? AND is_used=0", (user_id,))

            conn.execute(
                """INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, is_used)
                   VALUES (?, ?, ?, 0)""",
                (user_id, token_hash, expires_at)
            )
            conn.commit()

            from app.services.email_service import send_password_reset_email
            send_password_reset_email(clean_email, raw_token, user_name)

            logger.info(f"Password reset token generated and emailed for user_id={user_id}")

    expose_dev = _should_expose_dev_tokens()

    resp = {
        'success': True,
        'message': 'If an account with that email exists, a password reset link has been sent to your email address.'
    }
    if expose_dev and raw_token:
        resp['dev_reset_token'] = raw_token
    return resp


def reset_password_with_token(raw_token: str, new_password: str) -> dict:
    """Reset a user's password using direct hash query and constant-time comparison (SEC-06)."""
    if not raw_token or not new_password:
        return {'success': False, 'message': 'Token and new password are required.'}

    ok, err = validate_password(new_password)
    if not ok:
        return {'success': False, 'message': err}

    target_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    now_str     = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:
        token_rec = conn.execute(
            """SELECT * FROM password_reset_tokens 
               WHERE token_hash = ? AND is_used = 0 AND expires_at > ?""",
            (target_hash, now_str)
        ).fetchone()

        if not token_rec or not hmac.compare_digest(token_rec['token_hash'], target_hash):
            return {'success': False, 'message': 'Invalid or expired password reset token.'}

        user_id         = token_rec['user_id']
        hashed_password = generate_password_hash(new_password)

        # Update password hash
        conn.execute("UPDATE users SET password=? WHERE id=?", (hashed_password, user_id))
        # Mark token as used
        conn.execute("UPDATE password_reset_tokens SET is_used=1 WHERE id=?", (token_rec['id'],))
        conn.commit()

    logger.info(f"Password successfully reset for user_id={user_id}")
    return {'success': True, 'message': 'Password has been reset successfully! Please log in with your new password.'}

