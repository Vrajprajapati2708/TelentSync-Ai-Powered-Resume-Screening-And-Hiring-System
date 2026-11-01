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
        weekday_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        day_labels  = []
        views_daily = []
        apps_daily  = []
        for i in range(6, -1, -1):  # 6 days ago → today
            dt = datetime.datetime.now() - datetime.timedelta(days=i)
            day = dt.strftime('%Y-%m-%d')
            label = 'Today' if i == 0 else weekday_map[dt.weekday()]
            day_labels.append(label)
            cnt = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id=? AND type='profile_view' AND created_at LIKE ?",
                (user_id, day + '%')
            ).fetchone()[0]
            views_daily.append(cnt)

            app_cnt = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE user_id=? AND applied_at LIKE ?",
                (user_id, day + '%')
            ).fetchone()[0]
            apps_daily.append(app_cnt)

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

        resume_count = conn.execute("SELECT COUNT(*) FROM resumes WHERE user_id=?", (user_id,)).fetchone()[0]
        has_resume = bool(resume_count > 0)

        # If user has no resume in database, ensure score and skills are strictly 0 / empty
        if not has_resume:
            skills = []
            base_score = 0
            missing = []
        else:
            skills = [s.strip() for s in (u.get('skills') or '').split(',') if s.strip()]
            base_score = u.get('ats_score') or 0
            candidate_skills_lower = [s.lower() for s in skills]
            missing = [s for s, _ in top_skills if s.lower() not in candidate_skills_lower]

        radar_skills = skills[:6] if skills else []
        if len(radar_skills) < 6:
            radar_skills += ['Communication', 'Teamwork', 'Problem Solving',
                             'Adaptability', 'Leadership', 'Agile'][:6 - len(radar_skills)]

        radar_levels   = [base_score] * len(radar_skills) if has_resume else [0] * len(radar_skills)
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

        # Total candidates with any skills (for % calculation)
        total_candidates_with_skills = len(skills_raw) or 1

        # Real market demand % per skill: what % of candidates on platform have this skill
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

        if has_resume:
            candidate_skills_lower = {s.lower() for s in skills}
            # Detect high-demand market skills absent from candidate profile
            job_rows = conn.execute("SELECT skills FROM jobs WHERE status='Active' AND skills != ''").fetchall()
            market_counts = {}
            for jr in job_rows:
                for sk in (jr[0] or '').split(','):
                    sk = sk.strip()
                    if sk and len(sk) > 1:
                        market_counts[sk] = market_counts.get(sk, 0) + 1
            top_market_skills = [s for s, _ in sorted(market_counts.items(), key=lambda x: x[1], reverse=True)[:25]]
            missing = [s for s in top_market_skills if s.lower() not in candidate_skills_lower]
            if not missing:
                for s, _ in top_skills:
                    if s.lower() not in candidate_skills_lower:
                        missing.append(s)
            if not missing:
                fallback_pool = ['AWS', 'Kubernetes', 'React', 'Redis', 'PostgreSQL', 'TypeScript', 'GraphQL', 'Terraform']
                missing = [s for s in fallback_pool if s.lower() not in candidate_skills_lower]
        else:
            missing = []

    return jsonify({
        'has_resume':           has_resume,
        'ats_score':            base_score,
        'skills_count':         len(skills),
        'skills':               skills,
        'missing_skills':       missing[:4] if has_resume else [],
        'missing_skills_count': len(missing) if has_resume else 0,
        'skill_demand_pct':     skill_demand_pct,
        'profile_views':        profile_views,
        'profile_views_weekly': profile_views_weekly,
        'views_daily':          views_daily,
        'apps_daily':           apps_daily,
        'day_names':            weekday_map,
        'day_labels':           day_labels,
        'applications':         apps,
        'shortlisted':          shortlisted,
        'job_matches':          total_jobs if has_resume else 0,
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


from app.services.candidate_skills_service import (
    get_candidate_skills,
    declare_blind_skills,
    remove_candidate_skill
)


@user_bp.route('/user/skills', methods=['GET'])
@user_bp.route('/candidate/skills', methods=['GET'])
@login_required
def get_user_skills_endpoint():
    """
    GET /api/user/skills
    GET /api/candidate/skills
    Returns confirmed skills for current user with evidence source and confidence weight.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    skills = get_candidate_skills(user_id)
    self_decl = sum(1 for s in skills if s.get('source') == 'self_declared')
    extracted = sum(1 for s in skills if s.get('source') in ('resume_extracted', 'experience', 'project'))
    verified = sum(1 for s in skills if s.get('source') == 'quiz_verified' or s.get('confidence', 0) >= 1.0)

    return jsonify({
        'success': True,
        'user_id': user_id,
        'total_count': len(skills),
        'self_declared_count': self_decl,
        'extracted_count': extracted,
        'verified_count': verified,
        'skills': skills
    }), 200


@user_bp.route('/user/skills/confirm', methods=['POST'])
@user_bp.route('/candidate/skills/declare', methods=['POST'])
@user_bp.route('/candidate/skills/confirm', methods=['POST'])
@login_required
def confirm_user_skills_endpoint():
    """
    POST /api/user/skills/confirm
    POST /api/candidate/skills/declare
    Step 6: Blind Skill Confirmation.
    Candidates confirm/declare skills blindly before viewing job gaps or recommendation feedback.
    Payload:
      { "skills": ["Docker", "Kubernetes", "Redis"] } or { "skill": "Docker" }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    data = request.get_json(silent=True) or {}
    skills_input = data.get('skills')
    if skills_input is None:
        skills_input = data.get('skill')

    if not skills_input:
        return jsonify({
            'success': False,
            'message': 'No skills provided. Provide a "skills" array or "skill" string.'
        }), 400

    result = declare_blind_skills(user_id, skills_input, source='self_declared')
    if not result.get('success'):
        return jsonify(result), 400

    return jsonify(result), 200


@user_bp.route('/user/skills/<path:skill_name>', methods=['DELETE'])
@user_bp.route('/candidate/skills/<path:skill_name>', methods=['DELETE'])
@login_required
def remove_user_skill_endpoint(skill_name: str):
    """
    DELETE /api/user/skills/<skill_name>
    DELETE /api/candidate/skills/<skill_name>
    Remove a skill from the candidate's profile.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    result = remove_candidate_skill(user_id, skill_name)
    status_code = 200 if result.get('success') else 404
    return jsonify(result), status_code


@user_bp.route('/user/velocity', methods=['GET'])
@user_bp.route('/candidate/velocity', methods=['GET'])
@login_required
def get_user_velocity_status():
    """
    GET /api/user/velocity
    GET /api/candidate/velocity
    Returns candidate's velocity status and flagged skills requiring verification.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    from app.services.velocity_service import get_user_velocity_anomalies
    anomalies = get_user_velocity_anomalies(user_id)
    flagged_anomalies = [a for a in anomalies if a.get('status') == 'flagged']

    disputed_skills = []
    for a in flagged_anomalies:
        if isinstance(a.get('new_skills'), list):
            disputed_skills.extend(a['new_skills'])

    return jsonify({
        'success': True,
        'user_id': user_id,
        'has_anomaly': bool(flagged_anomalies),
        'disputed_skills': sorted(list(set(disputed_skills))),
        'message': 'Skills flagged for technical assessment verification' if flagged_anomalies else 'Skill velocity within normal limits'
    }), 200


from app.services.quiz_service import (
    get_quiz_for_skill,
    submit_quiz_answers,
    get_user_quiz_history
)


@user_bp.route('/user/quiz/<path:skill_name>', methods=['GET'])
@user_bp.route('/candidate/quiz/<path:skill_name>', methods=['GET'])
@login_required
def get_skill_quiz_endpoint(skill_name: str):
    """
    GET /api/user/quiz/<skill_name>
    Fetches randomized technical assessment questions for a skill.
    Enforces cooldown and masks out correct options.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    quiz = get_quiz_for_skill(user_id, skill_name)
    status_code = 200 if quiz.get('success') else (429 if quiz.get('cooldown_active') else 400)
    return jsonify(quiz), status_code


@user_bp.route('/user/quiz/<path:skill_name>/submit', methods=['POST'])
@user_bp.route('/candidate/quiz/<path:skill_name>/submit', methods=['POST'])
@login_required
def submit_skill_quiz_endpoint(skill_name: str):
    """
    POST /api/user/quiz/<skill_name>/submit
    Authoritatively grades submitted answers server-side.
    Payload: { "answers": { "1": 1, "2": 2, ... } }
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    data = request.get_json(silent=True) or {}
    answers = data.get('answers')
    if not isinstance(answers, dict):
        return jsonify({'success': False, 'message': 'Invalid format. Provide an "answers" map of question IDs to option indices.'}), 400

    result = submit_quiz_answers(user_id, skill_name, answers)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@user_bp.route('/user/quizzes', methods=['GET'])
@user_bp.route('/candidate/quizzes', methods=['GET'])
@login_required
def get_user_quizzes_endpoint():
    """
    GET /api/user/quizzes
    Returns full assessment history and verified skills for current user.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required.'}), 401

    history = get_user_quiz_history(user_id)
    return jsonify({
        'success': True,
        'user_id': user_id,
        'attempts_count': len(history),
        'attempts': history
    }), 200



