# ============================================================
#  TalentSync — Security Decorators  (app/utils/security.py)
#  Provides:
#    @login_required          — enforces valid session
#    @role_required('hr')     — enforces role after login check
# ============================================================

from functools import wraps
from flask import session, jsonify


def login_required(f):
    """
    Decorator: blocks access if the user is not logged in.
    Returns 401 JSON if the session has no user_id.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({
                'success': False,
                'message': 'Authentication required. Please log in.'
            }), 401
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_roles):
    """
    Decorator factory: blocks access if the user's role is not in allowed_roles.
    Must be applied AFTER @login_required (or it will also check the session).

    Usage:
        @login_required
        @role_required('hr')
        def admin_view(): ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({
                    'success': False,
                    'message': 'Authentication required. Please log in.'
                }), 401

            # Lazy import to avoid circular dependency
            from app.database.connection import get_db
            with get_db() as conn:
                user = conn.execute(
                    "SELECT role, is_verified FROM users WHERE id=?", (user_id,)
                ).fetchone()

            if not user or user['role'] not in allowed_roles:
                return jsonify({
                    'success': False,
                    'message': 'Access denied. Insufficient permissions.'
                }), 403

            is_ver = user['is_verified'] if 'is_verified' in user.keys() else 0
            if not is_ver:
                session.clear()
                return jsonify({
                    'success': False,
                    'message': 'Account is deactivated. Access revoked.'
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
