import os
from flask import Blueprint, request, jsonify, session, send_file
from app import limiter
from app.utils.security import login_required, role_required
from app.controllers.platform_admin_controller import (
    get_platform_users,
    get_platform_user_detail,
    create_platform_user,
    activate_platform_user,
    deactivate_platform_user,
    change_platform_user_role,
    delete_platform_user,
    get_platform_analytics,
    get_platform_login_attempts,
    get_platform_outliers,
    resolve_platform_outlier,
    get_platform_audit_logs,
    get_platform_jobs,
    get_platform_job_detail,
    update_platform_job_status,
    delete_platform_job,
    get_platform_applications,
    get_platform_application_detail,
    update_platform_application_status,
    get_platform_jobs_apps_summary,
    get_platform_resumes,
    get_platform_resume_detail,
    delete_platform_resume,
    get_platform_resume_file_path,
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


@platform_admin_bp.route('/users', methods=['POST'])
@login_required
@role_required('admin')
@limiter.limit("15 per minute")
def create_user():
    """
    POST /api/platform-admin/users
    Provisions a new user account with specified role and credentials.
    """
    admin_user_id = session.get('user_id')
    if admin_user_id is None:
        return jsonify({'success': False, 'message': 'Unauthorized session.'}), 401
    data = request.get_json(silent=True) or {}
    success, message, status_code, user_id = create_platform_user(data, int(admin_user_id))
    return jsonify({'success': success, 'message': message, 'user_id': user_id}), status_code


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


@platform_admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
@role_required('admin')
@limiter.limit("15 per minute")
def delete_user(user_id: int):
    """
    DELETE /api/platform-admin/users/<user_id>
    Permanently deletes a user account with cascading cleanup and audit logging.
    Enforces final-admin and self-deletion safeguards.
    """
    admin_user_id = session.get('user_id')
    if admin_user_id is None:
        return jsonify({'success': False, 'message': 'Unauthorized session.'}), 401
    success, message, status_code = delete_platform_user(user_id, int(admin_user_id))
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


@platform_admin_bp.route('/security/outliers/<int:user_id>/resolve', methods=['POST'])
@login_required
@role_required('admin')
def resolve_outlier(user_id):
    """
    POST /api/platform-admin/security/outliers/<user_id>/resolve
    Clears the outlier flag for a candidate profile with audit logging.
    """
    admin_user_id = int(session.get('user_id') or 0)
    success, message, status_code = resolve_platform_outlier(user_id, admin_user_id)
    return jsonify({"success": success, "message": message}), status_code


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
      - company: string
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
    company = request.args.get('company', '').strip()

    result = get_platform_jobs(page=page, limit=limit, search=search, status=status, company=company)
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


@platform_admin_bp.route('/jobs/<int:job_id>/status', methods=['POST'])
@login_required
@role_required('admin')
@limiter.limit("20 per minute")
def change_job_status(job_id: int):
    """
    POST /api/platform-admin/jobs/<job_id>/status
    JSON Payload: { "status": "Active" | "Closed" | "Draft" }
    """
    admin_user_id = session.get('user_id', 0)
    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '').strip()
    if not new_status:
        return jsonify({'success': False, 'message': 'Status parameter is required.'}), 400

    success, message, status_code = update_platform_job_status(job_id, new_status, int(admin_user_id))
    return jsonify({'success': success, 'message': message}), status_code


@platform_admin_bp.route('/jobs/<int:job_id>', methods=['DELETE'])
@login_required
@role_required('admin')
@limiter.limit("15 per minute")
def remove_job(job_id: int):
    """
    DELETE /api/platform-admin/jobs/<job_id>
    """
    admin_user_id = session.get('user_id', 0)
    success, message, status_code = delete_platform_job(job_id, int(admin_user_id))
    return jsonify({'success': success, 'message': message}), status_code


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
      - job_id: int
      - min_match: int
      - max_match: int
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

    job_id_param = request.args.get('job_id', '').strip()
    job_id = int(job_id_param) if job_id_param.isdigit() else None

    min_match_param = request.args.get('min_match', '').strip()
    min_match = int(min_match_param) if min_match_param.isdigit() else None

    max_match_param = request.args.get('max_match', '').strip()
    max_match = int(max_match_param) if max_match_param.isdigit() else None

    result = get_platform_applications(
        page=page, limit=limit, search=search, status=status,
        job_id=job_id, min_match=min_match, max_match=max_match
    )
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


@platform_admin_bp.route('/applications/<int:app_id>/status', methods=['POST'])
@login_required
@role_required('admin')
@limiter.limit("30 per minute")
def change_application_status(app_id: int):
    """
    POST /api/platform-admin/applications/<app_id>/status
    JSON Payload: { "status": "Pending" | "Reviewing" | "Shortlisted" | "Rejected" | "Hired", "notes": string }
    """
    admin_user_id = session.get('user_id', 0)
    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '').strip()
    notes = data.get('notes', '').strip()
    if not new_status:
        return jsonify({'success': False, 'message': 'Status parameter is required.'}), 400

    success, message, status_code = update_platform_application_status(app_id, new_status, notes, int(admin_user_id))
    return jsonify({'success': success, 'message': message}), status_code


@platform_admin_bp.route('/jobs-apps/summary', methods=['GET'])
@login_required
@role_required('admin')
def jobs_apps_summary():
    """
    GET /api/platform-admin/jobs-apps/summary
    Returns summary KPIs and company filter choices.
    """
    result = get_platform_jobs_apps_summary()
    return jsonify(result), 200


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
      - integrity: string ('available', 'missing')
      - min_ats: int
      - max_ats: int
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
    integrity = request.args.get('integrity', '').strip().lower()

    min_ats_param = request.args.get('min_ats', '').strip()
    min_ats = int(min_ats_param) if min_ats_param.isdigit() else None

    max_ats_param = request.args.get('max_ats', '').strip()
    max_ats = int(max_ats_param) if max_ats_param.isdigit() else None

    result = get_platform_resumes(
        page=page, limit=limit, search=search, status=status,
        integrity=integrity, min_ats=min_ats, max_ats=max_ats
    )
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


@platform_admin_bp.route('/resumes/<int:resume_id>', methods=['DELETE'])
@login_required
@role_required('admin')
@limiter.limit("20 per minute")
def delete_resume(resume_id: int):
    """
    DELETE /api/platform-admin/resumes/<resume_id>
    Permanently deletes resume record, storage file, and records audit trail.
    """
    admin_user_id = session.get('user_id', 0)
    success, message, status_code = delete_platform_resume(resume_id, int(admin_user_id))
    return jsonify({'success': success, 'message': message}), status_code


@platform_admin_bp.route('/resumes/<int:resume_id>/download', methods=['GET'])
@login_required
@role_required('admin')
def download_resume(resume_id: int):
    """
    GET /api/platform-admin/resumes/<resume_id>/download
    Safely streams the physical resume file for platform admin review.
    """
    fpath, orig_name, mime_type = get_platform_resume_file_path(resume_id)
    if not fpath or not os.path.isfile(fpath):
        return jsonify({'success': False, 'message': 'Resume file does not exist on storage.'}), 404
    return send_file(
        fpath,
        as_attachment=True,
        download_name=orig_name or 'resume.pdf',
        mimetype=mime_type or 'application/pdf'
    )


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


# ── 9. Platform Data Export (JSON / CSV) ─────────────────────

@platform_admin_bp.route('/export', methods=['GET'])
@login_required
@role_required('admin')
@limiter.limit("5 per minute")
def export_platform_data():
    """
    GET /api/platform-admin/export?format=json|csv&type=all|users|jobs|applications|audit
    Secured platform data export for authorized backup and compliance.
    """
    import csv
    import io
    import json
    from flask import Response
    from app.database.connection import get_db

    export_format = request.args.get('format', 'json').strip().lower()
    export_type = request.args.get('type', 'all').strip().lower()

    if export_format not in ('json', 'csv'):
        return jsonify({'success': False, 'message': 'Unsupported export format. Allowed formats: json, csv.'}), 400

    if export_type not in ('all', 'users', 'jobs', 'applications', 'audit'):
        return jsonify({'success': False, 'message': 'Unsupported export type. Allowed types: all, users, jobs, applications, audit.'}), 400

    # Record export action to audit log
    admin_id = session.get('user_id')
    ip_addr = request.remote_addr or '127.0.0.1'

    with get_db() as conn:
        users = [dict(row) for row in conn.execute("SELECT id, name, email, role, phone, location, ats_score, is_verified, created_at FROM users").fetchall()]
        jobs = [dict(row) for row in conn.execute("SELECT id, title, company, location, type, salary, status, created_at FROM jobs").fetchall()]
        applications = [dict(row) for row in conn.execute("SELECT id, user_id, job_id, match_score, status, applied_at FROM applications").fetchall()]
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, details TEXT, ip_address TEXT, timestamp TEXT DEFAULT (datetime('now')))"
            )
            conn.execute(
                "INSERT INTO audit_logs (user_id, action, details, ip_address, timestamp) VALUES (?, 'export_platform_data', ?, ?, datetime('now'))",
                (admin_id, f"format={export_format}, type={export_type}", ip_addr)
            )
            if hasattr(conn, 'commit'):
                conn.commit()
        except Exception:
            pass

        try:
            audit = [dict(row) for row in conn.execute("SELECT id, user_id, action, details, ip_address, timestamp FROM audit_logs ORDER BY id DESC LIMIT 500").fetchall()]
        except Exception:
            audit = []

    if export_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        if export_type == 'users':
            writer.writerow(['ID', 'Name', 'Email', 'Role', 'Phone', 'Location', 'ATS Score', 'Verified', 'Created At'])
            for u in users:
                writer.writerow([u.get('id'), u.get('name'), u.get('email'), u.get('role'), u.get('phone'), u.get('location'), u.get('ats_score'), u.get('is_verified'), u.get('created_at')])
        elif export_type == 'jobs':
            writer.writerow(['ID', 'Title', 'Company', 'Location', 'Type', 'Salary', 'Status', 'Created At'])
            for j in jobs:
                writer.writerow([j.get('id'), j.get('title'), j.get('company'), j.get('location'), j.get('type'), j.get('salary'), j.get('status'), j.get('created_at')])
        elif export_type == 'applications':
            writer.writerow(['ID', 'User ID', 'Job ID', 'Match Score', 'Status', 'Applied At'])
            for a in applications:
                writer.writerow([a.get('id'), a.get('user_id'), a.get('job_id'), a.get('match_score'), a.get('status'), a.get('applied_at')])
        else:
            writer.writerow(['Audit ID', 'User ID', 'Action', 'Details', 'IP Address', 'Timestamp'])
            for l in audit:
                writer.writerow([l.get('id'), l.get('user_id'), l.get('action'), l.get('details'), l.get('ip_address'), l.get('timestamp')])

        csv_data = output.getvalue()
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=talentsync_platform_export_{export_type}.csv'}
        )

    export_payload = {
        'success': True,
        'export_timestamp': request.date or 'now',
        'data': {
            'users': users,
            'jobs': jobs,
            'applications': applications,
            'audit_logs': audit
        }
    }
    return Response(
        json.dumps(export_payload, indent=2, default=str),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=talentsync_platform_backup.json'}
    )
