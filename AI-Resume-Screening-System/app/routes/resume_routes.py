import os
import copy
import json
import time
import hashlib
from typing import Dict, Tuple, Any, List, Optional
from flask import Blueprint, request, jsonify, session, send_file
from app.controllers.resume_controller import process_resume_upload, delete_resume_by_id
from app.database.connection import get_db
from app.ml.recommendation.recommend_jobs import recommend_jobs
from app.utils.security import login_required
from app import limiter
from datetime import datetime

import threading

resume_bp = Blueprint('resume', __name__, url_prefix='/api')

# Per-user ranked jobs cache: key -> (timestamp, jobs, status, transparency, source)
_user_ranked_cache: Dict[str, Tuple[float, List[Dict[str, Any]], Dict[str, Any], str, str]] = {}
_user_cache_lock = threading.Lock()


def invalidate_user_ranked_cache(uid: Optional[int]) -> None:
    """Invalidates all cached ranked jobs for a specific user ID in a thread-safe manner."""
    if not uid:
        return
    prefix = f"{uid}:"
    with _user_cache_lock:
        keys_to_remove = [k for k in _user_ranked_cache if k.startswith(prefix)]
        for k in keys_to_remove:
            _user_ranked_cache.pop(k, None)


@resume_bp.route('/upload_resume', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def upload_resume():
    """
    POST /api/upload_resume
    Form data: resume=<file> or file=<file>
    user_id is taken securely from session.
    """
    file = request.files.get('resume') or request.files.get('file')
    user_id = session.get('user_id')

    result = process_resume_upload(file, user_id)
    if result.get('success'):
        invalidate_user_ranked_cache(user_id)
    status = 200 if result.get('success') else 400
    return jsonify(result), status


@resume_bp.route('/resume/download/<int:resume_id>', methods=['GET'])
@login_required
def download_resume(resume_id: int):
    """
    GET /api/resume/download/<resume_id>
    Secure file download endpoint with ownership authorization check.
    Candidate A downloading Candidate B's resume returns HTTP 403 Forbidden.
    HR / Admin roles are granted authorization to view candidate resumes.
    """
    user_id = session.get('user_id')

    with get_db() as conn:
        # Fetch current user role
        user_rec = conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        user_role = user_rec['role'] if user_rec else 'candidate'

        # Fetch target resume metadata
        resume = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()

    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404

    # Ownership Authorization Guard (P0 Security Rule)
    if resume['user_id'] != user_id and user_role not in ('hr', 'admin'):
        return jsonify({'success': False, 'message': 'Unauthorized. You do not have permission to access this resume.'}), 403

    file_path = resume['file_path']
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'message': 'File missing from server storage.'}), 404

    # GAP-04: Support inline preview for PDF files if preview=1 requested
    is_preview = request.args.get('preview', '0') == '1'
    as_attachment = not (is_preview and resume['mime_type'] == 'application/pdf')

    return send_file(
        file_path,
        as_attachment=as_attachment,
        download_name=resume['original_name'],
        mimetype=resume['mime_type']
    )


@resume_bp.route('/resume/my_resumes', methods=['GET'])
@login_required
def get_my_resumes():
    """GET /api/resume/my_resumes — Fetch list of uploaded resumes for logged-in user."""
    user_id = session.get('user_id')

    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, original_name, stored_filename, file_size_bytes, mime_type, ats_score, extracted_skills, structured_json, status, version, uploaded_at 
               FROM resumes WHERE user_id=? ORDER BY id DESC""",
            (user_id,)
        ).fetchall()

    return jsonify({
        'success': True,
        'resumes': [dict(r) for r in rows]
    }), 200


@resume_bp.route('/resume/<int:resume_id>', methods=['DELETE'])
@resume_bp.route('/resumes/<int:resume_id>', methods=['DELETE'])
@resume_bp.route('/resume/delete/<int:resume_id>', methods=['DELETE', 'POST'])
@login_required
def delete_resume_endpoint(resume_id: int):
    """
    DELETE /api/resume/<resume_id>
    POST   /api/resume/delete/<resume_id>
    Secure resume deletion endpoint with ownership authorization, path traversal
    protection, DB transactional deletion, and audit logging.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required. Please log in.'}), 401

    user_role = session.get('role')
    if not user_role and user_id:
        with get_db() as conn:
            u_row = conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
            if u_row:
                user_role = u_row['role']

    user_role_str = str(user_role or 'candidate')
    result = delete_resume_by_id(resume_id, int(user_id), user_role_str)
    status_code = result.get('status_code', 200)
    return jsonify(result), status_code




from app.services.adzuna_service import (
    AdzunaService,
    AdzunaAuthError,
    AdzunaRateLimitError,
    AdzunaTimeoutError,
    AdzunaConfigError,
    AdzunaUpstreamError
)
from app.ai.job_matcher import JobMatcher
from app.utils.logger import get_logger

logger = get_logger(__name__)

@resume_bp.route('/match_jobs', methods=['POST'])
@login_required
def match_jobs():
    """
    POST /api/match_jobs
    JSON: { skills: ['Python', 'SQL', ...] }
    """
    data   = request.get_json(silent=True) or {}
    skills = data.get('skills', [])

    # Validate skills is a list
    if not isinstance(skills, list):
        return jsonify({'success': False, 'message': 'skills must be a list'}), 400

    # 1. NEW CANDIDATE / NO RESUME: Candidate with no parsed skills
    # Do NOT show generic "Software Developer" list as if personalized!
    if not skills:
        with get_db() as conn:
            popular_rows = conn.execute("SELECT * FROM jobs ORDER BY id LIMIT 4").fetchall()
            popular_jobs = [dict(r) for r in popular_rows]
            for pj in popular_jobs:
                pj['is_generic'] = True
                pj['match_percentage'] = 0
                pj['matching_skills'] = []

        return jsonify({
            'success': True,
            'jobs': [],
            'needs_resume': True,
            'popular_jobs': popular_jobs,
            'personalization_summary': '',
            'message': 'Upload your resume to get personalized job matches',
            'source': 'none',
            'source_status': {'adzuna': 'skipped', 'reason': 'no_skills'}
        })

    user_id = session.get('user_id')
    user_exp = data.get('experience')
    user_loc = data.get('location')

    # Resolve candidate experience from latest resume intelligence if not provided in payload
    if not user_exp and user_id:
        try:
            with get_db() as conn:
                r_row = conn.execute(
                    "SELECT structured_json FROM resumes WHERE user_id=? ORDER BY id DESC LIMIT 1",
                    (user_id,)
                ).fetchone()
                if r_row and r_row['structured_json']:
                    s_data = json.loads(r_row['structured_json'])
                    yrs = s_data.get('total_experience_years')
                    if yrs is not None and yrs > 0:
                        user_exp = f"{yrs} years"
                    elif yrs == 0:
                        user_exp = "fresher"
        except Exception:
            pass

    # Resolve candidate location from profile if not provided in payload
    if not user_loc and user_id:
        try:
            with get_db() as conn:
                u_row = conn.execute("SELECT location FROM users WHERE id=?", (user_id,)).fetchone()
                if u_row and u_row['location']:
                    user_loc = u_row['location']
        except Exception:
            pass

    user_prefs = {
        'experience': user_exp or '',
        'location': user_loc or ''
    }

    # 2. PER-USER CACHE: Key includes user_id, sorted skills hash, exp, and loc
    user_id_str = str(user_id or 'anon')
    skills_hash = hashlib.md5(','.join(sorted(set(str(s).lower().strip() for s in skills))).encode('utf-8')).hexdigest()
    exp_str = str(user_prefs.get('experience') or '').lower().strip()
    loc_str = str(user_prefs.get('location') or '').lower().strip()
    user_cache_key = f"{user_id_str}:{skills_hash}:{exp_str}:{loc_str}"

    now = time.time()
    with _user_cache_lock:
        cached_entry = _user_ranked_cache.get(user_cache_key)
    if cached_entry:
        c_ts, c_jobs, c_status, c_transparency, c_source = cached_entry
        if now - c_ts < 300:  # 5 min per-user cache TTL
            logger.info(f"Serving per-user cached ranked jobs for user {user_id_str}")
            return jsonify({
                'success': True,
                'jobs': [copy.deepcopy(j) for j in c_jobs],
                'source': c_source,
                'source_status': c_status,
                'personalization_summary': c_transparency
            })

    # 3. Build transparency summary from the exact inputs used for the queries
    adzuna_service = AdzunaService()
    inferred_role = adzuna_service._infer_role(skills) if skills else ""
    client = adzuna_service.client
    market_ranked_skills = client.rank_skills_by_market_relevance(skills) if hasattr(client, 'rank_skills_by_market_relevance') else skills
    display_role = inferred_role or (market_ranked_skills[0] if market_ranked_skills else "Developer")
    top_2_queried = ", ".join([str(s) for s in market_ranked_skills[:2]])

    trans_parts = [f"Personalized for: {display_role}"]
    if top_2_queried:
        trans_parts.append(top_2_queried)
    if user_prefs.get('location'):
        trans_parts.append(user_prefs['location'])
    transparency_summary = " • ".join(trans_parts)

    matcher = JobMatcher()
    adzuna_status = {"adzuna": "ok"}

    try:
        adzuna = AdzunaService()
        live_jobs = adzuna.fetch_live_jobs(skills=skills, location=user_prefs.get('location', ''))
        if live_jobs:
            for j in live_jobs:
                if 'is_external' not in j:
                    j['is_external'] = True
                if 'external_apply_url' not in j:
                    j['external_apply_url'] = j.get('apply_url') or None
                if 'source_job_id' not in j:
                    j['source_job_id'] = j.get('raw_id') or str(j.get('id', '')).replace('adzuna_', '')
            matched = matcher.rank_jobs(skills, live_jobs, user_prefs=user_prefs)
            with _user_cache_lock:
                _user_ranked_cache[user_cache_key] = (now, [copy.deepcopy(j) for j in matched], {'adzuna': 'ok'}, transparency_summary, 'adzuna')
            return jsonify({
                'success': True,
                'jobs': matched,
                'source': 'adzuna',
                'source_status': {'adzuna': 'ok'},
                'personalization_summary': transparency_summary
            })
        else:
            # Succeeded with 0 matching jobs for the query
            adzuna_status = {'adzuna': 'ok', 'reason': 'empty'}
            
    except AdzunaAuthError as e:
        logger.error(f"Job match Adzuna Auth error: {e}")
        adzuna_status = {'adzuna': 'failed', 'reason': 'auth'}
    except AdzunaRateLimitError as e:
        logger.warning(f"Job match Adzuna Rate Limit error: {e}")
        adzuna_status = {'adzuna': 'failed', 'reason': 'rate_limit'}
    except AdzunaTimeoutError as e:
        logger.warning(f"Job match Adzuna Timeout error: {e}")
        adzuna_status = {'adzuna': 'failed', 'reason': 'timeout'}
    except AdzunaConfigError as e:
        logger.warning(f"Job match Adzuna Config error: {e}")
        adzuna_status = {'adzuna': 'failed', 'reason': 'config'}
    except Exception as e:
        logger.error(f"Job match Adzuna unexpected upstream error: {e}")
        adzuna_status = {'adzuna': 'failed', 'reason': 'upstream'}

    # Fallback to local DB if Adzuna fails or returns 0 jobs
    with get_db() as conn:
        jobs = [dict(j) for j in conn.execute("SELECT * FROM jobs ORDER BY id").fetchall()]

    for j in jobs:
        j['is_external'] = False
        j['external_apply_url'] = None
        j['apply_url'] = ''
        j['source'] = 'local'
        j['source_job_id'] = str(j.get('id', ''))

    matched = matcher.rank_jobs(skills, jobs, user_prefs=user_prefs)
    with _user_cache_lock:
        _user_ranked_cache[user_cache_key] = (now, [copy.deepcopy(j) for j in matched], adzuna_status, transparency_summary, 'local')
    return jsonify({
        'success': True,
        'jobs': matched,
        'source': 'local',
        'source_status': adzuna_status,
        'personalization_summary': transparency_summary
    })


@resume_bp.route('/apply', methods=['POST'])
@login_required
def apply_job():
    """POST /api/apply  →  { job_id, match_score, is_external, external_apply_url, apply_url }
    Distinguishes INTERNAL vs EXTERNAL jobs (GAP-07).
    User ID is strictly taken from the authenticated session.
    """
    from app.utils.validators import validate_external_apply_url

    data    = request.get_json(silent=True) or {}
    user_id = session.get('user_id')
    job_id  = data.get('job_id')
    apply_url = (data.get('external_apply_url') or data.get('apply_url') or '').strip()

    if not job_id and not apply_url:
        return jsonify({'success': False, 'message': 'job_id is required'}), 400

    # Explicitly determine if job is external vs internal
    if 'is_external' in data and data['is_external'] is not None:
        is_external = bool(data['is_external'])
    elif apply_url:
        is_external = True
    elif isinstance(job_id, str) and job_id.startswith('adzuna_'):
        is_external = True
    elif isinstance(job_id, str) and job_id.startswith('internal_'):
        is_external = False
    elif isinstance(job_id, (int, float)) or (isinstance(job_id, str) and job_id.isdigit()):
        is_external = False
    else:
        is_external = False

    # ── EXTERNAL JOB FLOW ────────────────────────────────────
    if is_external:
        if not apply_url:
            return jsonify({'success': False, 'message': 'External job requires a valid external application URL'}), 400

        is_valid_url, url_err = validate_external_apply_url(apply_url)
        if not is_valid_url:
            return jsonify({'success': False, 'message': url_err}), 400

        # Accurately report external redirection — never falsely claim completion
        return jsonify({
            'success': True,
            'type': 'external',
            'status': 'external_redirected',
            'redirect_url': apply_url,
            'external_apply_url': apply_url,
            'message': 'Redirecting to external application site'
        }), 200

    # ── INTERNAL JOB FLOW ────────────────────────────────────
    if job_id is None:
        return jsonify({'success': False, 'message': 'job_id is required for internal job'}), 400

    raw_job_id = str(job_id).replace('internal_', '').strip()
    try:
        internal_job_id = int(raw_job_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid job ID for internal job'}), 400

    with get_db() as conn:
        job = conn.execute("SELECT id FROM jobs WHERE id=?", (internal_job_id,)).fetchone()
        if not job:
            return jsonify({'success': False, 'message': 'Job not found'}), 404

        exists = conn.execute(
            "SELECT id FROM applications WHERE user_id=? AND job_id=?",
            (user_id, internal_job_id)
        ).fetchone()
        if exists:
            return jsonify({'success': False, 'message': 'Already applied!'})

        match_score = int(data.get('match_score', 0))
        conn.execute(
            "INSERT INTO applications (user_id, job_id, match_score, applied_at) VALUES (?, ?, ?, ?)",
            (user_id, internal_job_id, match_score, datetime.now().strftime('%Y-%m-%d %H:%M'))
        )
        conn.commit()

    return jsonify({
        'success': True,
        'type': 'internal',
        'status': 'submitted',
        'message': 'Application submitted successfully'
    }), 200
