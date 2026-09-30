# ============================================================
#  HireAI / TalentSync — Platform Admin Routes
#  Blueprint namespace: /api/platform-admin
#  ALL routes strictly enforce @login_required & @role_required('admin')
# ============================================================

from flask import Blueprint, request, jsonify, session
from app import limiter
from app.utils.security import login_required, role_required
from app.controllers.platform_admin_controller import (
    get_platform_users,
    get_platform_user_detail,
    activate_platform_user,
    deactivate_platform_user,
    change_platform_user_role,
    get_platform_analytics,
    get_platform_login_attempts,
    get_platform_outliers,
    get_platform_audit_logs,
    get_platform_jobs,
    get_platform_job_detail,
    get_platform_applications,
    get_platform_application_detail,
    get_platform_resumes,
    get_platform_resume_detail,
    get_platform_system_health,
    get_platform_integrations
)

platform_admin_bp = Blueprint('platform_admin', __name__, url_prefix='/api/platform-admin')


# ── 1. User & Role Management ────────────────────────────────

@platform_admin_bp.route('/users', methods=['GET'])
@login_required
@role_required('admin')
def list_users():
    """
    GET /api/platform-admin/users
    Query parameters:
      - page: int (default 1)
      - limit: int (default 20, max 100)
      - search: string (matches name or email)
      - role: string ('candidate', 'hr', 'admin')
      - status: string ('active', 'inactive')
      - verification: string ('verified', 'unverified')
    """
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = int(request.args.get('limit', 20))
    except (ValueError, TypeError):
        limit = 20

    search = request.args.get('search', '').strip()
    role = request.args.get('role', '').strip()
    status = request.args.get('status', '').strip()
    verification = request.args.get('verification', '').strip()

    result = get_platform_users(
        page=page, limit=limit, search=search, role=role, status=status, verification=verification
    )
    return jsonify(result), 200


@platform_admin_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
@role_required('admin')
def get_user(user_id: int):
    """
    GET /api/platform-admin/users/<user_id>
    Returns detailed profile without passwords, tokens, or security secrets.
    """
    user = get_platform_user_detail(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
    return jsonify({'success': True, 'user': user, 'data': {'user': user}}), 200


@platform_admin_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@login_required
@role_required('admin')
@limiter.limit("15 per minute")
def activate_user(user_id: int):
    """
    POST /api/platform-admin/users/<user_id>/activate
    Sets is_verified = 1.
    """
    success, message, status_code = activate_platform_user(user_id)
    return jsonify({'success': success, 'message': message}), status_code


@platform_admin_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
@role_required('admin')
@limiter.limit("15 per minute")
def deactivate_user(user_id: int):
    """
    POST /api/platform-admin/users/<user_id>/deactivate
    Sets is_verified = 0. Enforces final-admin and self-deactivation safeguards.
    """
    admin_user_id = session.get('user_id')
    if admin_user_id is None:
        return jsonify({'success': False, 'message': 'Unauthorized session.'}), 401
    success, message, status_code = deactivate_platform_user(user_id, int(admin_user_id))
    return jsonify({'success': success, 'message': message}), status_code


@platform_admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@role_required('admin')
@limiter.limit("15 per minute")
def change_role(user_id: int):
    """
    POST /api/platform-admin/users/<user_id>/role
    JSON Payload: { "role": "candidate" | "hr" | "admin" }
    Enforces final-admin demotion and self-modification safeguards.
    """
    data = request.get_json(silent=True) or {}
    new_role = data.get('role', '')

    if not new_role or not isinstance(new_role, str):
        return jsonify({'success': False, 'message': 'Role is required in JSON payload.'}), 400

    admin_user_id = session.get('user_id')
    if admin_user_id is None:
        return jsonify({'success': False, 'message': 'Unauthorized session.'}), 401
    success, message, status_code = change_platform_user_role(user_id, new_role, int(admin_user_id))
    return jsonify({'success': success, 'message': message}), status_code


# ── 2. System-Wide Analytics ─────────────────────────────────

@platform_admin_bp.route('/analytics', methods=['GET'])
@login_required
@role_required('admin')
def platform_analytics():
    """
    GET /api/platform-admin/analytics
    Real-time platform metrics aggregated strictly from live database data.
    """
    result = get_platform_analytics()
    return jsonify(result), 200


# ── 3. Security & Fraud Oversight ────────────────────────────

@platform_admin_bp.route('/security/login-attempts', methods=['GET'])
@login_required
@role_required('admin')
def login_attempts():
    """
    GET /api/platform-admin/security/login-attempts
    Query parameters:
      - page: int (default 1)
      - limit: int (default 20)
      - status: string ('success', 'failed')
      - search: string (email or IP)
    """
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = int(request.args.get('limit', 20))
    except (ValueError, TypeError):
        limit = 20

    status_filter = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()

    result = get_platform_login_attempts(page=page, limit=limit, status_filter=status_filter, search=search)
    return jsonify(result), 200


@platform_admin_bp.route('/security/outliers', methods=['GET'])
@login_required
@role_required('admin')
def security_outliers():
    """
    GET /api/platform-admin/security/outliers
    Query parameters:
      - page: int (default 1)
      - limit: int (default 20)
    """
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = int(request.args.get('limit', 20))
    except (ValueError, TypeError):
        limit = 20

    result = get_platform_outliers(page=page, limit=limit)
    return jsonify(result), 200


# ── 4. Audit / Activity Viewer ───────────────────────────────

@platform_admin_bp.route('/audit', methods=['GET'])
@login_required
@role_required('admin')
def audit_events():
    """
    GET /api/platform-admin/audit
    Read-only unified timeline from historical database tables.
    Query parameters:
      - page: int (default 1)
      - limit: int (default 20)
      - source: string ('all', 'application_status', 'recommendation_history', 'search_history')
      - search: string
    """
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = int(request.args.get('limit', 20))
    except (ValueError, TypeError):
        limit = 20

    source = request.args.get('source', 'all').strip()
    search = request.args.get('search', '').strip()

    result = get_platform_audit_logs(page=page, limit=limit, source=source, search=search)
    return jsonify(result), 200


# ── 5. Platform Jobs Management ──────────────────────────────

@platform_admin_bp.route('/jobs', methods=['GET'])
@login_required
@role_required('admin')
def list_jobs():
    """
    GET /api/platform-admin/jobs
    Query parameters:
      - page: int (default 1)
      - limit: int (default 20)
      - search: string
      - status: string
    """
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = int(request.args.get('limit', 20))
    except (ValueError, TypeError):
        limit = 20

    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()

    result = get_platform_jobs(page=page, limit=limit, search=search, status=status)
    return jsonify(result), 200


@platform_admin_bp.route('/jobs/<int:job_id>', methods=['GET'])
@login_required
@role_required('admin')
def get_job(job_id: int):
    """
    GET /api/platform-admin/jobs/<job_id>
    """
    result = get_platform_job_detail(job_id)
    if not result:
        return jsonify({'success': False, 'message': 'Job not found.'}), 404
    return jsonify({'success': True, 'job': result, 'data': {'job': result}}), 200


# ── 6. Platform Applications Management ──────────────────────

@platform_admin_bp.route('/applications', methods=['GET'])
@login_required
@role_required('admin')
def list_applications():
    """
    GET /api/platform-admin/applications
    Query parameters:
      - page: int (default 1)
      - limit: int (default 20)
      - search: string
      - status: string
    """
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = int(request.args.get('limit', 20))
    except (ValueError, TypeError):
        limit = 20

    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()

    result = get_platform_applications(page=page, limit=limit, search=search, status=status)
    return jsonify(result), 200


@platform_admin_bp.route('/applications/<int:app_id>', methods=['GET'])
@login_required
@role_required('admin')
def get_application(app_id: int):
    """
    GET /api/platform-admin/applications/<app_id>
    """
    result = get_platform_application_detail(app_id)
    if not result:
        return jsonify({'success': False, 'message': 'Application not found.'}), 404
    return jsonify({'success': True, 'application': result, 'data': {'application': result}}), 200


# ── 7. Platform Resume Operations ────────────────────────────

@platform_admin_bp.route('/resumes', methods=['GET'])
@login_required
@role_required('admin')
def list_resumes():
    """
    GET /api/platform-admin/resumes
    Query parameters:
      - page: int (default 1)
      - limit: int (default 20)
      - search: string
      - status: string
    """
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = int(request.args.get('limit', 20))
    except (ValueError, TypeError):
        limit = 20

    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()

    result = get_platform_resumes(page=page, limit=limit, search=search, status=status)
    return jsonify(result), 200


@platform_admin_bp.route('/resumes/<int:resume_id>', methods=['GET'])
@login_required
@role_required('admin')
def get_resume(resume_id: int):
    """
    GET /api/platform-admin/resumes/<resume_id>
    """
    result = get_platform_resume_detail(resume_id)
    if not result:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
    return jsonify({'success': True, 'resume': result, 'data': {'resume': result}}), 200


# ── 8. System Health & Integrations ──────────────────────────

@platform_admin_bp.route('/system/health', methods=['GET'])
@login_required
@role_required('admin')
def system_health():
    """
    GET /api/platform-admin/system/health
    Probes real underlying infrastructure and services.
    Returns status: Healthy, Degraded, Unavailable, Not Configured.
    """
    result = get_platform_system_health()
    return jsonify(result), 200


@platform_admin_bp.route('/system/integrations', methods=['GET'])
@login_required
@role_required('admin')
def system_integrations():
    """
    GET /api/platform-admin/system/integrations
    Returns operational status of external integrations.
    Zero secrets, API keys, or passwords exposed.
    """
    result = get_platform_integrations()
    return jsonify(result), 200
