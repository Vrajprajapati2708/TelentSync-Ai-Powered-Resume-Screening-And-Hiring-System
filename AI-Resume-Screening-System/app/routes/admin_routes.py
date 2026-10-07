# ============================================================
#  TalentSync — Admin Routes  (Blueprint: /api/admin)
#  ALL routes require an authenticated HR session.
# ============================================================

import csv
import io
import json
from typing import Any, List, Optional, Tuple, Dict
from datetime import datetime
from flask import Blueprint, request, jsonify, Response
from app.database.connection import get_db
from app.utils.security import login_required, role_required
from app.utils.validators import validate_status, sanitize_text

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/stats')
@login_required
@role_required('hr')
def admin_stats():
    """GET /api/admin/stats — Dashboard KPIs and chart data. HR only."""
    with get_db() as conn:
        total       = conn.execute("""
            SELECT COUNT(*) FROM applications a
            INNER JOIN users u ON a.user_id = u.id
            WHERE u.role = 'candidate'
        """).fetchone()[0]
        shortlisted = conn.execute("""
            SELECT COUNT(*) FROM applications a
            INNER JOIN users u ON a.user_id = u.id
            WHERE u.role = 'candidate' AND a.status='Shortlisted'
        """).fetchone()[0]
        reviewing   = conn.execute("""
            SELECT COUNT(*) FROM applications a
            INNER JOIN users u ON a.user_id = u.id
            WHERE u.role = 'candidate' AND a.status='Reviewing'
        """).fetchone()[0]
        pending     = conn.execute("""
            SELECT COUNT(*) FROM applications a
            INNER JOIN users u ON a.user_id = u.id
            WHERE u.role = 'candidate' AND a.status='Pending'
        """).fetchone()[0]
        rejected    = conn.execute("""
            SELECT COUNT(*) FROM applications a
            INNER JOIN users u ON a.user_id = u.id
            WHERE u.role = 'candidate' AND a.status='Rejected'
        """).fetchone()[0]
        active_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='Active'").fetchone()[0]
        total_jobs  = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        total_cands = conn.execute("SELECT COUNT(*) FROM users WHERE role='candidate'").fetchone()[0]
        avg_row     = conn.execute("SELECT AVG(ats_score) FROM users WHERE role='candidate' AND ats_score>0").fetchone()[0]
        avg_ats     = round(avg_row, 1) if avg_row else 0
        analyzed    = conn.execute("SELECT COUNT(*) FROM users WHERE role='candidate' AND ats_score>0").fetchone()[0]

        skills_raw   = conn.execute("SELECT skills FROM users WHERE role='candidate' AND skills != ''").fetchall()
        skill_counts: dict = {}
        for row in skills_raw:
            for s in row[0].split(','):
                s = s.strip()
                if s:
                    skill_counts[s] = skill_counts.get(s, 0) + 1
        top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:8]

        role_data = conn.execute('''
            SELECT j.title, COUNT(*) as cnt FROM applications a
            INNER JOIN users u ON a.user_id = u.id
            JOIN jobs j ON a.job_id = j.id
            WHERE u.role = 'candidate'
            GROUP BY j.title ORDER BY cnt DESC LIMIT 6
        ''').fetchall()

        ats_ranges = {'0-20':0, '21-40':0, '41-60':0, '61-70':0, '71-80':0, '81-90':0, '91-100':0}
        all_ats = conn.execute("SELECT ats_score FROM users WHERE role='candidate'").fetchall()
        for row in all_ats:
            s = row[0] or 0
            if s <= 20: ats_ranges['0-20'] += 1
            elif s <= 40: ats_ranges['21-40'] += 1
            elif s <= 60: ats_ranges['41-60'] += 1
            elif s <= 70: ats_ranges['61-70'] += 1
            elif s <= 80: ats_ranges['71-80'] += 1
            elif s <= 90: ats_ranges['81-90'] += 1
            else: ats_ranges['91-100'] += 1

        import datetime as dt
        now = dt.datetime.now()
        months = [(now.month - i - 1) % 12 + 1 for i in range(5, -1, -1)]
        month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        app_time_labels      = [month_names[m-1] for m in months]
        app_time_total       = [0] * 6
        app_time_shortlisted = [0] * 6

        apps_date = conn.execute("""
            SELECT a.applied_at, a.status FROM applications a
            INNER JOIN users u ON a.user_id = u.id
            WHERE u.role = 'candidate'
        """).fetchall()
        for row in apps_date:
            date_str, status = row
            try:
                m = int(date_str.split('-')[1])
                if m in months:
                    idx = months.index(m)
                    app_time_total[idx] += 1
                    if status == 'Shortlisted':
                        app_time_shortlisted[idx] += 1
            except Exception:
                pass

    return jsonify({
        'total_applicants':   total,
        'shortlisted':        shortlisted,
        'reviewing':          reviewing,
        'pending':            pending,
        'rejected':           rejected,
        'active_jobs':        active_jobs,
        'total_jobs':         total_jobs,
        'total_candidates':   total_cands,
        'avg_ats_score':      avg_ats,
        'time_to_shortlist':  '2.4h',
        'resumes_analyzed':   analyzed,
        'top_skills':         [{'skill': s, 'count': c} for s, c in top_skills],
        'top_skill_demanded': top_skills[0][0] if top_skills else 'Python',
        'acceptance_rate':    round((shortlisted / total * 100), 1) if total > 0 else 0,
        'status_breakdown':   {'Shortlisted': shortlisted, 'Reviewing': reviewing, 'Pending': pending, 'Rejected': rejected},
        'apps_by_role':       [{'role': r[0], 'count': r[1]} for r in role_data],
        'ats_distribution':   list(ats_ranges.values()),
        'app_time': {
            'labels':      app_time_labels,
            'total':       app_time_total,
            'shortlisted': app_time_shortlisted
        }
    })


@admin_bp.route('/candidates')
@login_required
@role_required('hr')
def get_candidates():
    """GET /api/admin/candidates — All applicants with outlier flags, cluster labels, and real Resume Intelligence. HR only."""
    import json
    from app.ml.outlier.outlier_detector import detect_outliers
    from app.ml.clustering.candidate_clusterer import cluster_candidates

    with get_db() as conn:
        rows = conn.execute('''
            SELECT a.id as app_id, u.id as user_id, u.name, u.email, u.phone, u.location,
                   u.linkedin, u.github, u.summary, u.education as user_education, u.skills, u.ats_score,
                   j.title as job, a.match_score, a.status, a.applied_at,
                   r.id as resume_id, r.original_name as resume_name, r.mime_type as resume_mime,
                   r.structured_json
            FROM applications a
            JOIN users u ON a.user_id = u.id
            JOIN jobs j  ON a.job_id  = j.id
            LEFT JOIN (
                SELECT id, user_id, original_name, mime_type, structured_json,
                       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY id DESC) as rn
                FROM resumes
            ) r ON r.user_id = u.id AND r.rn = 1
            ORDER BY a.match_score DESC
        ''').fetchall()

    candidates = []
    for r in rows:
        c = dict(r)
        degree = c.get('user_education') or None
        exp_years = None
        exp_summary = None
        s_json = c.pop('structured_json', None)
        if s_json:
            try:
                intel = json.loads(s_json) if isinstance(s_json, str) else s_json
                if isinstance(intel, dict):
                    contact = intel.get('contact') or {}
                    if not c.get('phone') and contact.get('phone'):
                        c['phone'] = contact['phone']
                    if not c.get('linkedin') and contact.get('linkedin'):
                        c['linkedin'] = contact['linkedin']
                    if not c.get('github') and contact.get('github'):
                        c['github'] = contact['github']

                    edu_list = intel.get('education') or []
                    if edu_list and isinstance(edu_list, list):
                        first_edu = edu_list[0]
                        if isinstance(first_edu, dict):
                            deg_name = first_edu.get('degree') or ''
                            inst = first_edu.get('institution') or ''
                            degree = f"{deg_name} · {inst}".strip(' ·') or deg_name or inst

                    total_yrs = intel.get('total_experience_years')
                    if total_yrs is not None and total_yrs > 0:
                        exp_years = round(total_yrs, 1)
                        exp_summary = f"{exp_years} yrs"
                    elif intel.get('experience') and len(intel['experience']) > 0:
                        exp_summary = f"{len(intel['experience'])} roles"
            except Exception:
                pass

        c['degree'] = degree or 'Not detected'
        c['exp'] = exp_summary or ('Not detected' if exp_years is None else '0 yrs')
        c['exp_years'] = exp_years
        candidates.append(c)

    # ── Run Outlier Detection ───────────────────────────────
    candidates = detect_outliers(candidates)

    # ── Run Clustering Analysis ─────────────────────────────
    candidates = cluster_candidates(candidates, n_clusters=5)

    return jsonify(candidates)


def query_talent_pool(
    q: Optional[str] = None,
    skills: Optional[str] = None,
    location: Optional[str] = None,
    min_ats: Optional[float] = None,
    limit: Optional[int] = 100,
    offset: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Shared candidate retrieval and filtering function used by both Talent Pool API and CSV Export.
    Guarantees 100% deterministic query consistency across JSON UI responses and CSV downloads.
    """
    with get_db() as conn:
        base_query = '''
            SELECT 
                u.id as candidate_id,
                u.name,
                u.email,
                u.phone,
                u.location,
                u.linkedin,
                u.github,
                u.summary,
                u.education as user_education,
                u.skills,
                u.ats_score,
                u.created_at,
                r.id as resume_id,
                r.original_name as resume_name,
                r.mime_type as resume_mime,
                r.structured_json,
                COUNT(a.id) as application_count
            FROM users u
            LEFT JOIN (
                SELECT id, user_id, original_name, mime_type, structured_json,
                       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY id DESC) as rn
                FROM resumes
            ) r ON r.user_id = u.id AND r.rn = 1
            LEFT JOIN applications a ON a.user_id = u.id
            WHERE u.role = 'candidate'
        '''
        params: List[Any] = []
        where_clauses: List[str] = []

        if q:
            wildcard = f"%{q}%"
            where_clauses.append('(u.name LIKE ? OR u.email LIKE ? OR u.skills LIKE ? OR u.location LIKE ?)')
            params.extend([wildcard, wildcard, wildcard, wildcard])

        if skills:
            where_clauses.append('u.skills LIKE ?')
            params.append(f"%{skills}%")

        if location:
            where_clauses.append('u.location LIKE ?')
            params.append(f"%{location}%")

        if min_ats is not None:
            where_clauses.append('u.ats_score >= ?')
            params.append(float(min_ats))

        if where_clauses:
            base_query += ' AND ' + ' AND '.join(where_clauses)

        base_query += ' GROUP BY u.id ORDER BY u.id DESC'

        if limit is not None:
            base_query += ' LIMIT ? OFFSET ?'
            params.extend([limit, offset])

        rows = conn.execute(base_query, params).fetchall()

        # Count total candidates matching criteria
        count_query = "SELECT COUNT(*) FROM users u WHERE u.role = 'candidate'"
        count_params: List[Any] = []
        if where_clauses:
            count_query += ' AND ' + ' AND '.join(where_clauses)
            count_params = list(params[:len(params) - (2 if limit is not None else 0)])
        total_count = conn.execute(count_query, count_params).fetchone()[0]

    candidates = []
    for r in rows:
        c = dict(r)
        degree = c.get('user_education') or None
        exp_years = None
        exp_summary = None
        quality_score = None
        s_json = c.pop('structured_json', None)

        if s_json:
            try:
                intel = json.loads(s_json) if isinstance(s_json, str) else s_json
                if isinstance(intel, dict):
                    contact = intel.get('contact') or {}
                    if not c.get('phone') and contact.get('phone'):
                        c['phone'] = contact['phone']
                    if not c.get('linkedin') and contact.get('linkedin'):
                        c['linkedin'] = contact['linkedin']
                    if not c.get('github') and contact.get('github'):
                        c['github'] = contact['github']

                    edu_list = intel.get('education') or []
                    if edu_list and isinstance(edu_list, list):
                        first_edu = edu_list[0]
                        if isinstance(first_edu, dict):
                            deg_name = first_edu.get('degree') or ''
                            inst = first_edu.get('institution') or ''
                            degree = f"{deg_name} · {inst}".strip(' ·') or deg_name or inst

                    total_yrs = intel.get('total_experience_years')
                    if total_yrs is not None and total_yrs > 0:
                        exp_years = round(total_yrs, 1)
                        exp_summary = f"{exp_years} yrs"
                    elif intel.get('experience') and len(intel['experience']) > 0:
                        exp_summary = f"{len(intel['experience'])} roles"

                    quality = intel.get('quality') or {}
                    quality_score = quality.get('quality_score')
            except Exception:
                pass

        c['degree'] = degree or 'Not detected'
        c['exp'] = exp_summary or ('Not detected' if exp_years is None else '0 yrs')
        c['exp_years'] = exp_years
        c['quality_score'] = quality_score if quality_score is not None else (c.get('ats_score') or 0)
        c['skills'] = [s.strip() for s in (c.get('skills') or '').split(',') if s.strip()]
        candidates.append(c)

    return candidates, total_count


def sanitize_csv_cell(value: Any) -> str:
    """
    Guards against CSV formula injection (OWASP / CWE-1236).
    If a field starts with '=', '+', '-', '@', '\t', '\r', prefix with single quote "'".
    """
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + val_str
    return val_str


@admin_bp.route('/talent_pool', methods=['GET'])
@admin_bp.route('/talent-pool', methods=['GET'])
@login_required
@role_required('hr', 'admin')
def get_talent_pool():
    """
    GET /api/admin/talent_pool — Discover registered candidates independently of applications (GAP-10).
    Includes latest uploaded resume intelligence and application count.
    Supports search and filtering: ?q=keyword, ?skills=python, ?location=city, ?min_ats=70, ?limit=100, ?offset=0.
    HR and Admin authorized.
    """
    q = (request.args.get('q') or '').strip()
    skills = (request.args.get('skills') or '').strip() or None
    location = (request.args.get('location') or '').strip() or None
    min_ats_raw = request.args.get('min_ats') or request.args.get('ats')
    min_ats = None
    if min_ats_raw is not None and min_ats_raw != '':
        try:
            min_ats = float(min_ats_raw)
        except (ValueError, TypeError):
            pass

    try:
        limit = max(1, min(int(request.args.get('limit', 100)), 500))
    except (ValueError, TypeError):
        limit = 100

    try:
        offset = max(0, int(request.args.get('offset', 0)))
    except (ValueError, TypeError):
        offset = 0

    candidates, total_count = query_talent_pool(
        q=q or None,
        skills=skills,
        location=location,
        min_ats=min_ats,
        limit=limit,
        offset=offset
    )

    return jsonify({
        'success': True,
        'total': total_count,
        'limit': limit,
        'offset': offset,
        'candidates': candidates
    }), 200


@admin_bp.route('/talent_pool/export', methods=['GET'])
@admin_bp.route('/talent_pool/export_csv', methods=['GET'])
@admin_bp.route('/talent-pool/export', methods=['GET'])
@admin_bp.route('/talent-pool/export_csv', methods=['GET'])
@login_required
@role_required('hr', 'admin')
def export_talent_pool_csv():
    """
    GET /api/admin/talent_pool/export
    Exports candidate talent pool records to RFC-4180 compliant CSV.
    Reuses the exact same underlying candidate query and filter logic.
    Protects against CSV formula injection (CWE-1236).
    Excludes all sensitive fields (passwords, hashes, tokens, session IDs).
    """
    q = (request.args.get('q') or '').strip()
    skills = (request.args.get('skills') or '').strip() or None
    location = (request.args.get('location') or '').strip() or None
    min_ats_raw = request.args.get('min_ats') or request.args.get('ats')
    min_ats = None
    if min_ats_raw is not None and min_ats_raw != '':
        try:
            min_ats = float(min_ats_raw)
        except (ValueError, TypeError):
            pass

    # For export, retrieve the full matching set (limit=None)
    candidates, _ = query_talent_pool(
        q=q or None,
        skills=skills,
        location=location,
        min_ats=min_ats,
        limit=None,
        offset=0
    )

    headers = [
        'Candidate ID',
        'Name',
        'Email',
        'Phone',
        'Location',
        'Degree / Education',
        'Experience',
        'ATS Score',
        'Applications Count',
        'Skills',
        'Registered Date'
    ]

    si = io.StringIO()
    writer = csv.writer(si, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)

    for c in candidates:
        skills_str = ', '.join(c.get('skills', [])) if isinstance(c.get('skills'), list) else str(c.get('skills') or '')
        row = [
            sanitize_csv_cell(c.get('candidate_id', '')),
            sanitize_csv_cell(c.get('name', '')),
            sanitize_csv_cell(c.get('email', '')),
            sanitize_csv_cell(c.get('phone', '')),
            sanitize_csv_cell(c.get('location', '')),
            sanitize_csv_cell(c.get('degree', '')),
            sanitize_csv_cell(c.get('exp', '')),
            sanitize_csv_cell(c.get('ats_score', 0)),
            sanitize_csv_cell(c.get('application_count', 0)),
            sanitize_csv_cell(skills_str),
            sanitize_csv_cell(c.get('created_at', ''))
        ]
        writer.writerow(row)

    csv_data = si.getvalue().encode('utf-8-sig')
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"TalentSync_Talent_Pool_{timestamp_str}.csv"

    return Response(
        csv_data,
        mimetype='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )



@admin_bp.route('/clusters')
@login_required
@role_required('hr')
def get_clusters():
    """GET /api/admin/clusters — Candidates grouped by skill cluster. HR only."""
    from app.ml.outlier.outlier_detector import detect_outliers
    from app.ml.clustering.candidate_clusterer import cluster_candidates, get_cluster_groups

    with get_db() as conn:
        rows = conn.execute('''
            SELECT a.id as app_id, u.name, u.email, u.skills, u.ats_score,
                   j.title as job, a.match_score, a.status, a.applied_at
            FROM applications a
            JOIN users u ON a.user_id = u.id
            JOIN jobs j  ON a.job_id  = j.id
            ORDER BY a.match_score DESC
        ''').fetchall()

    candidates = [dict(r) for r in rows]
    candidates = detect_outliers(candidates)
    candidates = cluster_candidates(candidates, n_clusters=5)
    groups     = get_cluster_groups(candidates)

    return jsonify({
        'groups': [
            {'label': label, 'count': len(members), 'candidates': members}
            for label, members in groups.items()
        ]
    })


@admin_bp.route('/outliers')
@login_required
@role_required('hr')
def get_outliers():
    """GET /api/admin/outliers — Only flagged/suspicious candidates. HR only."""
    from app.ml.outlier.outlier_detector import detect_outliers

    with get_db() as conn:
        rows = conn.execute('''
            SELECT a.id as app_id, u.name, u.email, u.skills, u.ats_score,
                   j.title as job, a.match_score, a.status, a.applied_at
            FROM applications a
            JOIN users u ON a.user_id = u.id
            JOIN jobs j  ON a.job_id  = j.id
            ORDER BY u.ats_score ASC
        ''').fetchall()

    candidates = [dict(r) for r in rows]
    candidates = detect_outliers(candidates)
    flagged    = [c for c in candidates if c.get('outlier_flag')]

    return jsonify({'count': len(flagged), 'flagged': flagged})


@admin_bp.route('/update_status', methods=['POST'])
@login_required
@role_required('hr')
def update_status():
    """POST /api/admin/update_status  →  { app_id, status }. HR only."""
    data   = request.get_json(silent=True) or {}
    app_id = data.get('app_id')
    status = data.get('status')

    if not app_id or not status:
        return jsonify({'success': False, 'message': 'app_id and status required'}), 400

    # Whitelist check — prevent arbitrary strings being stored
    if not validate_status(status):
        return jsonify({'success': False, 'message': 'Invalid status value.'}), 400

    with get_db() as conn:
        app_row = conn.execute(
            """SELECT a.user_id, a.status, a.job_id, j.title as job_title, j.company as job_company
               FROM applications a
               LEFT JOIN jobs j ON a.job_id = j.id
               WHERE a.id = ?""",
            (app_id,)
        ).fetchone()
        if not app_row:
            return jsonify({'success': False, 'message': 'Application not found'}), 404

        user_id = app_row['user_id']
        old_status = app_row['status']

        # Idempotency check: if status hasn't changed, don't create duplicate notifications
        if old_status == status:
            return jsonify({'success': True, 'message': 'Application status already up to date.'})

        conn.execute('UPDATE applications SET status=? WHERE id=?', (status, app_id))
        
        job_title = app_row['job_title'] or 'Job'
        job_company = app_row['job_company'] or ''
        company_str = f" at {job_company}" if job_company else ""
        msg = f"Your application for {job_title}{company_str} has been updated to: {status}."
        ntype = 'application'
        
        conn.execute(
            """INSERT INTO notifications 
               (user_id, title, message, type, action_type, action_target, metadata, created_at)
               VALUES (?, ?, ?, ?, 'view_application', '#cand-applications', ?, ?)""",
            (
                user_id,
                f'Application {status} 📄',
                msg,
                ntype,
                json.dumps({
                    'application_id': app_id,
                    'job_id': app_row['job_id'],
                    'old_status': old_status,
                    'new_status': status
                }),
                datetime.now().strftime('%Y-%m-%d %H:%M')
            )
        )
        conn.commit()
    return jsonify({'success': True})


@admin_bp.route('/delete_job/<int:job_id>', methods=['DELETE'])
@login_required
@role_required('hr')
def delete_job(job_id):
    """DELETE /api/admin/delete_job/<job_id>. HR only."""
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()
    return jsonify({'success': True})


# ── Jobs CRUD ─────────────────────────────────────────────
@admin_bp.route('/jobs', methods=['GET', 'POST'])
@login_required
@role_required('hr')
def jobs_api():
    """GET/POST /api/admin/jobs. HR only."""
    if request.method == 'GET':
        with get_db() as conn:
            jobs = conn.execute('SELECT * FROM jobs ORDER BY id DESC').fetchall()
        return jsonify([dict(j) for j in jobs])

    data = request.get_json(silent=True) or {}
    with get_db() as conn:
        conn.execute(
            'INSERT INTO jobs (title, company, location, type, salary, skills, description, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
            (
                sanitize_text(data.get('title') or '', 200),
                sanitize_text(data.get('company') or '', 200),
                sanitize_text(data.get('location') or '', 200),
                sanitize_text(data.get('type') or 'Full-time', 50),
                sanitize_text(data.get('salary') or '', 100),
                sanitize_text(data.get('skills') or '', 500),
                sanitize_text(data.get('description') or '', 5000),
                'Active',
                datetime.now().strftime('%Y-%m-%d')
            )
        )
        conn.commit()
    return jsonify({'success': True})


@admin_bp.route('/jobs/<int:job_id>', methods=['PUT', 'GET'])
@login_required
@role_required('hr')
def job_detail(job_id):
    """GET/PUT /api/admin/jobs/<job_id>. HR only."""
    if request.method == 'GET':
        with get_db() as conn:
            job = conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        return jsonify(dict(job)) if job else (jsonify({'error': 'Not found'}), 404)

    data = request.get_json(silent=True) or {}
    with get_db() as conn:
        conn.execute(
            'UPDATE jobs SET title=?, company=?, location=?, type=?, salary=?, skills=?, description=? WHERE id=?',
            (
                sanitize_text(data.get('title') or '', 200),
                sanitize_text(data.get('company') or '', 200),
                sanitize_text(data.get('location') or '', 200),
                sanitize_text(data.get('type') or '', 50),
                sanitize_text(data.get('salary') or '', 100),
                sanitize_text(data.get('skills') or '', 500),
                sanitize_text(data.get('description') or '', 5000),
                job_id
            )
        )
        conn.commit()
    return jsonify({'success': True})


@admin_bp.route('/adzuna-health', methods=['GET'])
def adzuna_health():
    """
    GET /api/admin/adzuna-health
    Diagnostic endpoint (admin, HR, or debug-mode only) testing real Adzuna API connectivity.
    Makes one real Adzuna call: what=python, where=Ahmedabad, results_per_page=3.
    Returns: { keys_loaded, status_code, latency_ms, results_count, error_type, error_message }
    """
    from flask import current_app, session
    from app.services.adzuna_client import adzuna_client

    # Allow if logged in as admin/hr, or if app is in debug/testing mode
    is_authorized = (
        session.get('role') in ('admin', 'hr') or
        current_app.config.get('DEBUG', False) or
        current_app.config.get('TESTING', False)
    )
    if not is_authorized:
        return jsonify({'error': 'Unauthorized', 'message': 'Admin or debug mode required.'}), 403

    diag = adzuna_client.check_health(what="python", where="Ahmedabad", limit=3)
    return jsonify({
        "keys_loaded": diag["keys_loaded"],
        "status_code": diag["status_code"],
        "latency_ms": diag["latency_ms"],
        "results_count": diag["results_count"],
        "error_type": diag["error_type"],
        "error_message": diag["error_message"]
    })
