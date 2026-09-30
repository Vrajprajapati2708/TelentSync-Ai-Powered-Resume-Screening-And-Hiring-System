# ============================================================
#  TalentSync — User Routes  (Blueprint: /api)
#  All endpoints are protected with @login_required.
#  Ownership is enforced: users can only access their own data.
# ============================================================

import datetime
from flask import Blueprint, request, jsonify, session
from app.database.connection import get_db
from app.utils.security import login_required
from app.utils.validators import sanitize_text

user_bp = Blueprint('user', __name__, url_prefix='/api')


def _owns_or_403(requested_user_id: int):
    """
    Returns None if the session user matches requested_user_id,
    otherwise returns a 403 JSON response tuple.
    """
    if session.get('user_id') != requested_user_id:
        return jsonify({'success': False, 'message': 'Access denied.'}), 403
    return None


@user_bp.route('/candidate/stats/<int:user_id>')
@login_required
def candidate_stats(user_id):
    """GET /api/candidate/stats/<user_id> — only accessible by the owner."""
    denied = _owns_or_403(user_id)
    if denied:
        return denied

    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        u = dict(user)

        apps = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE user_id=?", (user_id,)
        ).fetchone()[0]

        shortlisted = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE user_id=? AND status='Shortlisted'", (user_id,)
        ).fetchone()[0]

        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

        profile_views = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND type='profile_view'", (user_id,)
        ).fetchone()[0]

        week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        profile_views_weekly = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND type='profile_view' AND created_at >= ?",
            (user_id, week_ago)
        ).fetchone()[0]

        # Daily profile views for last 7 days (for the chart)
        day_names   = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        views_daily = []
        for i in range(6, -1, -1):  # 6 days ago → today
            day = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            cnt = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id=? AND type='profile_view' AND created_at LIKE ?",
                (user_id, day + '%')
            ).fetchone()[0]
            views_daily.append(cnt)
        # Also collect daily application counts for the same 7 days
        apps_daily = []
        for i in range(6, -1, -1):
            day = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            cnt = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE user_id=? AND applied_at LIKE ?",
                (user_id, day + '%')
            ).fetchone()[0]
            apps_daily.append(cnt)

        skills = [s.strip() for s in (u.get('skills') or '').split(',') if s.strip()]
        base_score = u.get('ats_score') or 0

        radar_skills = skills[:6]
        if len(radar_skills) < 6:
            radar_skills += ['Communication', 'Teamwork', 'Problem Solving',
                             'Adaptability', 'Leadership', 'Agile'][:6 - len(radar_skills)]

        radar_levels   = [base_score] * len(radar_skills)
        radar_required = [75] * len(radar_skills)

        ats_ranges = {'0-20': 0, '21-40': 0, '41-60': 0, '61-70': 0, '71-80': 0, '81-90': 0, '91-100': 0}
        all_ats = conn.execute("SELECT ats_score FROM users WHERE role='candidate'").fetchall()
        for row in all_ats:
            s_val = row[0] or 0
            if s_val <= 20:   ats_ranges['0-20'] += 1
            elif s_val <= 40: ats_ranges['21-40'] += 1
            elif s_val <= 60: ats_ranges['41-60'] += 1
            elif s_val <= 70: ats_ranges['61-70'] += 1
            elif s_val <= 80: ats_ranges['71-80'] += 1
            elif s_val <= 90: ats_ranges['81-90'] += 1
            else:             ats_ranges['91-100'] += 1

        skills_raw = conn.execute(
            "SELECT skills FROM users WHERE role='candidate' AND skills != ''"
        ).fetchall()
        skill_counts = {}
        for row in skills_raw:
            for s_val in row[0].split(','):
                s_val = s_val.strip()
                if s_val:
                    skill_counts[s_val] = skill_counts.get(s_val, 0) + 1
        top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:8]

        # Total candidates with any skills (for % calculation)
        total_candidates_with_skills = len(skills_raw) or 1

        # Real market demand % per skill: what % of candidates on platform have this skill
        # Capped between 5–98 to avoid 0% or 100% extremes
        skill_demand_pct = {
            s: min(98, max(5, round((c / total_candidates_with_skills) * 100)))
            for s, c in skill_counts.items()
        }

        now    = datetime.datetime.now()
        months = [(now.month - i - 1) % 12 + 1 for i in range(5, -1, -1)]
        month_names    = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        app_time_labels      = [month_names[m - 1] for m in months]
        app_time_total       = [0] * 6
        app_time_shortlisted = [0] * 6

        apps_date = conn.execute(
            "SELECT applied_at, status FROM applications WHERE user_id=?", (user_id,)
        ).fetchall()
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

        candidate_skills_lower = [s.lower() for s in skills]
        missing = [s for s, _ in top_skills if s.lower() not in candidate_skills_lower]

    return jsonify({
        'ats_score':            base_score,
        'skills_count':         len(skills),
        'skills':               skills,
        'missing_skills':       missing[:4],
        'skill_demand_pct':     skill_demand_pct,
        'profile_views':        profile_views,
        'profile_views_weekly': profile_views_weekly,
        'views_daily':          views_daily,
        'apps_daily':           apps_daily,
        'day_names':            day_names,
        'applications':         apps,
        'shortlisted':          shortlisted,
        'job_matches':          total_jobs,
        'radar': {
            'labels':   radar_skills,
            'levels':   radar_levels,
            'required': radar_required,
        },
        'market_trends': {
            'ats_distribution': list(ats_ranges.values()),
            'top_skills': [{'skill': s, 'count': c} for s, c in top_skills],
            'app_time': {
                'labels':      app_time_labels,
                'total':       app_time_total,
                'shortlisted': app_time_shortlisted,
            }
        }
    })


@user_bp.route('/users/<int:user_id>/profile', methods=['GET', 'PUT'])
@login_required
def user_profile(user_id):
    """GET/PUT /api/users/<user_id>/profile — owner only."""
    denied = _owns_or_403(user_id)
    if denied:
        return denied

    if request.method == 'GET':
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'Not found'}), 404
        u_dict = dict(user)
        u_dict.pop('password', None)
        return jsonify(u_dict)

    data = request.get_json(silent=True) or {}
    with get_db() as conn:
        conn.execute(
            '''UPDATE users SET name=?, email=?, phone=?, location=?,
               linkedin=?, github=?, summary=?, education=? WHERE id=?''',
            (
                sanitize_text(data.get('name') or '', 100),
                sanitize_text(data.get('email') or '', 254),
                sanitize_text(data.get('phone') or '', 20),
                sanitize_text(data.get('location') or '', 100),
                sanitize_text(data.get('linkedin') or '', 200),
                sanitize_text(data.get('github') or '', 200),
                sanitize_text(data.get('summary') or '', 2000),
                sanitize_text(data.get('education') or '', 1000),
                user_id
            )
        )
        conn.commit()
    return jsonify({'success': True})


@user_bp.route('/notifications/<int:user_id>', methods=['GET'])
@login_required
def get_notifications(user_id):
    """GET /api/notifications/<user_id> — owner only."""
    denied = _owns_or_403(user_id)
    if denied:
        return denied

    with get_db() as conn:
        nots = conn.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()
    return jsonify([dict(n) for n in nots])


@user_bp.route('/notifications/<int:user_id>/read', methods=['POST'])
@login_required
def read_notifications(user_id):
    """POST /api/notifications/<user_id>/read — owner only."""
    denied = _owns_or_403(user_id)
    if denied:
        return denied

    with get_db() as conn:
        conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))
        conn.commit()
    return jsonify({'success': True})
