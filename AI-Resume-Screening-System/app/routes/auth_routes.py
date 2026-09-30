# ============================================================
#  TalentSync — Auth Routes  (Blueprint: /api/auth)
#  v0.2 REST API endpoints for authentication, verification,
#  password reset tokens, and account protection.
# ============================================================

from flask import Blueprint, request, jsonify, session
from app.controllers.auth_controller import (
    login_user, register_user, verify_email_token,
    generate_password_reset_token, reset_password_with_token,
    generate_email_verification_token
)
from app.database.connection import get_db
from app.utils.security import login_required
from app.utils.validators import validate_password
from app import limiter

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """POST /api/auth/login  →  { email, password }"""
    data     = request.get_json(silent=True) or {}
    email    = data.get('email', '').strip()
    password = data.get('password', '')
    ip_addr  = request.remote_addr or '127.0.0.1'

    result = login_user(email, password, ip_address=ip_addr)

    # 1. Handle Account Lockout (HTTP 423 Locked)
    if result.get('is_locked'):
        return jsonify(result), 423

    # 2. Handle Unverified Account (SEC-02: HTTP 403 Forbidden)
    if result.get('not_verified'):
        return jsonify(result), 403

    # 3. Handle Successful Authentication
    if result.get('success'):
        session.clear()  # Regenerate session ID (session fixation prevention)
        session['user_id'] = result['user']['id']
        return jsonify(result), 200

    # 4. Invalid credentials (HTTP 400 Bad Request)
    return jsonify(result), 400


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """POST /api/auth/register  →  { name, email, password, role }"""
    data = request.get_json(silent=True) or {}
    raw_role = data.get('role', 'candidate')
    role = raw_role.strip().lower() if isinstance(raw_role, str) else 'candidate'

    # SEC-01: Public registration permits ONLY 'candidate'
    if role != 'candidate':
        return jsonify({
            'success': False,
            'message': 'Privileged accounts cannot be created through public registration.'
        }), 403

    result = register_user(
        data.get('name', ''),
        data.get('email', ''),
        data.get('password', ''),
        role='candidate'
    )

    if result.get('success'):
        session.clear()
        session['user_id'] = result['user']['id']
        return jsonify(result), 201

    status_code = result.get('status_code', 400)
    return jsonify(result), status_code


@auth_bp.route('/verify_email', methods=['POST'])
def verify_email():
    """POST /api/auth/verify_email  →  { token }"""
    data  = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()

    if not token:
        return jsonify({'success': False, 'message': 'Verification token is required.'}), 400

    result = verify_email_token(token)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@auth_bp.route('/resend_verification', methods=['POST'])
@limiter.limit("2 per minute")
def resend_verification():
    """POST /api/auth/resend_verification  →  { email }"""
    from flask import current_app
    from app.services.email_service import send_verification_email

    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'success': False, 'message': 'Email address is required.'}), 400

    raw_token = None
    with get_db() as conn:
        user = conn.execute("SELECT id, name, is_verified FROM users WHERE email=?", (email,)).fetchone()
        if not user:
            # Anti-enumeration: Return generic success
            return jsonify({'success': True, 'message': 'If your email is registered, a new verification link has been sent.'}), 200

        if user['is_verified'] == 1:
            return jsonify({'success': False, 'message': 'Email is already verified.'}), 400

        # Invalidate prior unused tokens
        conn.execute("UPDATE email_verification_tokens SET is_used=1 WHERE user_id=? AND is_used=0", (user['id'],))
        conn.commit()

        raw_token = generate_email_verification_token(user['id'])
        user_name = user['name'] if 'name' in user.keys() else ""
        send_verification_email(email, raw_token, user_name)

    expose_dev = current_app.config.get("EXPOSE_DEV_TOKENS", False)
    resp = {
        'success': True,
        'message': 'A new verification link has been sent to your email.'
    }
    if expose_dev and raw_token:
        resp['dev_verification_token'] = raw_token

    return jsonify(resp), 200


@auth_bp.route('/forgot_password', methods=['POST'])
@limiter.limit("3 per minute")
def forgot_password():
    """POST /api/auth/forgot_password  →  { email }"""
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'success': False, 'message': 'Email address is required.'}), 400

    result = generate_password_reset_token(email)
    return jsonify(result), 200


@auth_bp.route('/reset_password', methods=['POST'])
@limiter.limit("5 per minute")
def reset_password():
    """POST /api/auth/reset_password  →  { token, new_password }"""
    data         = request.get_json(silent=True) or {}
    token        = data.get('token', '').strip()
    new_password = data.get('new_password', '')

    if not token or not new_password:
        return jsonify({'success': False, 'message': 'Token and new password are required.'}), 400

    result = reset_password_with_token(token, new_password)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """POST /api/auth/logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully.'}), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_me():
    """GET /api/auth/me"""
    user_id = session.get('user_id')
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if user:
            u_dict = dict(user)
            u_dict.pop('password', None)
            return jsonify({'success': True, 'user': u_dict}), 200
    return jsonify({'success': False, 'message': 'User not found'}), 404


@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """POST /api/auth/change_password → { current_password, new_password }"""
    user_id = session.get('user_id')

    data       = request.get_json(silent=True) or {}
    current_pw = data.get('current_password', '')
    new_pw     = data.get('new_password', '')

    if not current_pw or not new_pw:
        return jsonify({'success': False, 'message': 'Both passwords required.'}), 400

    ok, err = validate_password(new_pw)
    if not ok:
        return jsonify({'success': False, 'message': err}), 400

    from werkzeug.security import check_password_hash, generate_password_hash
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        try:
            is_valid = check_password_hash(user['password'], current_pw)
        except Exception:
            is_valid = False

        if not is_valid:
            return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 403

        conn.execute('UPDATE users SET password=? WHERE id=?',
                     (generate_password_hash(new_pw), user_id))
        conn.commit()

    # Invalidate session after password change — force re-login
    session.clear()
    return jsonify({'success': True, 'message': 'Password changed successfully! Please log in again.'}), 200


@auth_bp.route('/landing_stats', methods=['GET'])
def landing_stats():
    """GET /api/auth/landing_stats — public stats for landing page."""
    with get_db() as conn:
        total_candidates = conn.execute("SELECT COUNT(*) FROM users WHERE role='candidate'").fetchone()[0]
        total_jobs       = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        total_apps       = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        avg_row          = conn.execute("SELECT AVG(ats_score) FROM users WHERE role='candidate' AND ats_score>0").fetchone()[0]
        avg_ats          = round(avg_row, 0) if avg_row else 0
    return jsonify({
        'resumes_analyzed': total_candidates,
        'jobs_matched':     total_jobs,
        'applications':     total_apps,
        'avg_ats':          int(avg_ats)
    }), 200

