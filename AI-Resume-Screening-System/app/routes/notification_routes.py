# ============================================================
#  TalentSync — Candidate Notification Routes
#  Enterprise-grade notification endpoints with strict RBAC & IDOR protection
# ============================================================

import json
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from app.database.connection import get_db
from app.utils.security import login_required

notification_bp = Blueprint('notification', __name__, url_prefix='/api/notifications')


def _get_authenticated_user_id():
    """Extracts and verifies authenticated user ID from active session."""
    return session.get('user_id')


SENSITIVE_META_KEYS = {'password', 'password_hash', 'token', 'token_hash', 'secret', 'api_key', 'database_url', 'session_cookie'}


@notification_bp.route('', methods=['GET'])
@login_required
def get_user_notifications():
    """
    GET /api/notifications
    Query params:
      - category: 'all'|'application'|'match'|'view'|'system'|'security'|'unread' (default: 'all')
      - search / q: string filter on title / message (max 100 chars)
      - limit: int (default 50, range 1..100)
      - page: int (1-indexed) OR offset: int (0-indexed)
    """
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    category = request.args.get('category', 'all').strip().lower()
    search = (request.args.get('search') or request.args.get('q') or '').strip()[:100]
    
    try:
        limit = max(1, min(int(request.args.get('limit', 50)), 100))
        if 'page' in request.args:
            page = max(1, int(request.args.get('page', 1)))
            offset = (page - 1) * limit
        else:
            offset = max(int(request.args.get('offset', 0)), 0)
    except (ValueError, TypeError):
        limit = 50
        offset = 0

    with get_db() as conn:
        # 1. Base unread count for current user
        unread_row = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)
        ).fetchone()
        unread_count = unread_row[0] if unread_row else 0

        # 2. Build filtered query
        query = "SELECT * FROM notifications WHERE user_id = ?"
        params = [user_id]

        if category == 'unread':
            query += " AND is_read = 0"
        elif category == 'application':
            query += " AND (type = 'application' OR type = 'success' OR type = 'error')"
        elif category == 'match':
            query += " AND (type = 'match' OR type = 'recommendation')"
        elif category == 'view':
            query += " AND (type = 'view' OR type = 'profile_view')"
        elif category == 'system':
            query += " AND (type = 'system' OR type = 'info' OR type = 'security' OR type = 'warning')"

        if search:
            query += " AND (title LIKE ? OR message LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term])

        # Get total matching count for pagination
        count_query = f"SELECT COUNT(*) FROM ({query})"
        total_matching = conn.execute(count_query, params).fetchone()[0]

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()

        notifications = []
        for r in rows:
            item = dict(r)
            # Parse and sanitize metadata if stored as JSON string
            raw_meta = item.get('metadata')
            if isinstance(raw_meta, str) and raw_meta:
                try:
                    parsed = json.loads(raw_meta)
                    if isinstance(parsed, dict):
                        item['metadata'] = {k: v for k, v in parsed.items() if k.lower() not in SENSITIVE_META_KEYS}
                    else:
                        item['metadata'] = {}
                except Exception:
                    item['metadata'] = {}
            elif isinstance(raw_meta, dict):
                item['metadata'] = {k: v for k, v in raw_meta.items() if k.lower() not in SENSITIVE_META_KEYS}
            else:
                item['metadata'] = {}

            # Ensure action fields exist
            item['action_type'] = item.get('action_type') or 'none'
            item['action_target'] = item.get('action_target') or ''
            notifications.append(item)

    return jsonify({
        'success': True,
        'notifications': notifications,
        'total': total_matching,
        'unread_count': unread_count,
        'limit': limit,
        'offset': offset
    }), 200


@notification_bp.route('/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    """GET /api/notifications/unread-count — lightweight counter for navbar badges."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)
        ).fetchone()
        count = row[0] if row else 0

    return jsonify({'success': True, 'unread_count': count}), 200


@notification_bp.route('/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    """
    POST /api/notifications/<notif_id>/read
    Marks a single notification as read.
    Validates ownership to prevent IDOR attacks.
    """
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    with get_db() as conn:
        notif = conn.execute("SELECT id, user_id, is_read FROM notifications WHERE id = ?", (notif_id,)).fetchone()
        if not notif:
            return jsonify({'success': False, 'message': 'Notification not found.'}), 404

        if notif['user_id'] != user_id:
            # IDOR defense: caller is authenticated but does not own this notification
            return jsonify({'success': False, 'message': 'You are not authorized to modify this notification.'}), 403

        conn.execute(
            "UPDATE notifications SET is_read = 1, updated_at = ? WHERE id = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), notif_id)
        )
        conn.commit()

        unread_count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)
        ).fetchone()[0]

    return jsonify({
        'success': True,
        'message': 'Notification marked as read.',
        'notif_id': notif_id,
        'unread_count': unread_count
    }), 200


@notification_bp.route('/<int:notif_id>', methods=['DELETE'])
@login_required
def delete_notification(notif_id):
    """
    DELETE /api/notifications/<notif_id>
    Deletes a single notification.
    Validates ownership to prevent IDOR attacks.
    """
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    with get_db() as conn:
        notif = conn.execute("SELECT id, user_id, is_read FROM notifications WHERE id = ?", (notif_id,)).fetchone()
        if not notif:
            return jsonify({'success': False, 'message': 'Notification not found.'}), 404

        if notif['user_id'] != user_id:
            # IDOR defense: caller is authenticated but does not own this notification
            return jsonify({'success': False, 'message': 'You are not authorized to delete this notification.'}), 403

        conn.execute("DELETE FROM notifications WHERE id = ?", (notif_id,))
        conn.commit()

        unread_count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)
        ).fetchone()[0]

    return jsonify({
        'success': True,
        'message': 'Notification deleted successfully.',
        'notif_id': notif_id,
        'unread_count': unread_count
    }), 200


@notification_bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """
    POST /api/notifications/read-all
    Marks all notifications for the authenticated user as read.
    """
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    with get_db() as conn:
        conn.execute(
            "UPDATE notifications SET is_read = 1, updated_at = ? WHERE user_id = ? AND is_read = 0",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id)
        )
        conn.commit()

    return jsonify({
        'success': True,
        'message': 'All notifications marked as read.',
        'unread_count': 0
    }), 200


@notification_bp.route('/clear', methods=['DELETE'])
@login_required
def clear_read_notifications():
    """
    DELETE /api/notifications/clear
    SEC-14: Clears ONLY read notifications (is_read = 1) for authenticated user.
    Unread notifications (is_read = 0) are strictly PRESERVED.
    """
    user_id = _get_authenticated_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM notifications WHERE user_id = ? AND is_read = 1",
            (user_id,)
        )
        deleted_count = cur.rowcount
        conn.commit()

        unread_count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)
        ).fetchone()[0]

    return jsonify({
        'success': True,
        'message': f'Cleared {deleted_count} read notifications.',
        'deleted_count': deleted_count,
        'unread_count': unread_count
    }), 200


# ── Backward Compatibility Endpoints (Ownership Guaranteed) ──

@notification_bp.route('/<int:user_id>', methods=['GET'])
@login_required
def legacy_get_notifications(user_id):
    """GET /api/notifications/<user_id> — owner only."""
    auth_user_id = _get_authenticated_user_id()
    if auth_user_id != user_id:
        return jsonify({'success': False, 'message': 'Access denied.'}), 403

    with get_db() as conn:
        nots = conn.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()
    return jsonify([dict(n) for n in nots])


@notification_bp.route('/<int:user_id>/read', methods=['POST'])
@login_required
def legacy_read_notifications(user_id):
    """POST /api/notifications/<user_id>/read — owner only."""
    auth_user_id = _get_authenticated_user_id()
    if auth_user_id != user_id:
        return jsonify({'success': False, 'message': 'Access denied.'}), 403

    with get_db() as conn:
        conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))
        conn.commit()
    return jsonify({'success': True})
