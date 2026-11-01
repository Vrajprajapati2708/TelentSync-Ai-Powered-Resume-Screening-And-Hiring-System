"""
TalentSync — Skill Velocity Service (Step 7)
Manages anomaly recording, timeline validation, and candidate velocity tracking.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.database.connection import get_db
from app.ml.velocity.learning_timeline_engine import detect_velocity_anomaly
from app.utils.logger import get_logger

logger = get_logger(__name__)


def check_and_record_velocity_anomaly(
    user_id: int,
    current_resume_id: int,
    current_skills: List[str],
    previous_resume_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Checks if a newly uploaded resume exhibits impossible skill velocity compared to previous version.
    If an anomaly is detected, records it in `skill_velocity_anomalies` and flags user profile.
    """
    if not user_id or not current_resume_id:
        return {'is_anomaly': False, 'reason': 'Missing user_id or current_resume_id.'}

    with get_db() as conn:
        # 1. Fetch previous resume if not provided
        if previous_resume_id:
            prev_row = conn.execute(
                "SELECT id, extracted_skills, uploaded_at, version FROM resumes WHERE id=?",
                (previous_resume_id,)
            ).fetchone()
        else:
            prev_row = conn.execute(
                """SELECT id, extracted_skills, uploaded_at, version 
                   FROM resumes 
                   WHERE user_id=? AND id != ? 
                   ORDER BY id DESC LIMIT 1""",
                (user_id, current_resume_id)
            ).fetchone()

        if not prev_row:
            return {
                'is_anomaly': False,
                'severity': 'none',
                'reason': 'First resume version on platform — velocity baseline established.'
            }

        prev_id = prev_row['id']
        prev_skills_raw = prev_row['extracted_skills'] or ''
        prev_skills = [s.strip() for s in prev_skills_raw.split(',') if s.strip()]
        prev_uploaded_at = prev_row['uploaded_at']

        # 2. Compute elapsed calendar days between uploads
        elapsed_days = 1.0  # default safe fallback
        if prev_uploaded_at:
            try:
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'):
                    try:
                        p_dt = datetime.strptime(str(prev_uploaded_at).split('.')[0], fmt)
                        from datetime import timezone
                        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                        now_loc = datetime.now()
                        delta_sec = min(
                            abs((now_utc - p_dt).total_seconds()),
                            abs((now_loc - p_dt).total_seconds())
                        )
                        elapsed_days = max(delta_sec / 86400.0, 0.001)
                        break
                    except ValueError:
                        continue
            except Exception as e:
                logger.warning(f"Failed to parse prev_uploaded_at '{prev_uploaded_at}': {e}")
                elapsed_days = 1.0

        # 3. Fetch already-known prior skills from candidate_skills to avoid false positives (e.g. blind self-declared skills)
        prior_rows = conn.execute(
            "SELECT skill FROM candidate_skills WHERE user_id=?",
            (user_id,)
        ).fetchall()
        prior_skills_set = {r['skill'] for r in prior_rows}

        # 4. Run velocity anomaly detector
        anomaly = detect_velocity_anomaly(
            prev_skills=prev_skills,
            curr_skills=current_skills,
            elapsed_days=elapsed_days,
            user_prior_skills=prior_skills_set
        )

        if anomaly.get('is_anomaly'):
            logger.warning(
                f"Velocity anomaly detected for user {user_id}: {anomaly['flag_reason']}"
            )

            # Insert anomaly log
            cur = conn.execute(
                """INSERT INTO skill_velocity_anomalies 
                   (user_id, previous_resume_id, current_resume_id, elapsed_days, estimated_days, 
                    new_skills, severity, velocity_ratio, anomaly_reason, status, detected_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'flagged', datetime('now'))""",
                (
                    user_id,
                    prev_id,
                    current_resume_id,
                    anomaly['elapsed_days'],
                    anomaly['estimated_learning_days'],
                    json.dumps(anomaly['added_skills']),
                    anomaly['severity'],
                    anomaly['velocity_ratio'],
                    anomaly['flag_reason']
                )
            )

            # Flag user profile as outlier for HR attention
            conn.execute("UPDATE users SET is_outlier=1 WHERE id=?", (user_id,))
            conn.commit()

            anomaly['anomaly_id'] = cur.lastrowid

    return anomaly


def get_user_velocity_anomalies(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve all velocity anomalies flagged for a candidate."""
    if not user_id:
        return []

    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, user_id, previous_resume_id, current_resume_id, 
                      elapsed_days, estimated_days, new_skills, severity, 
                      velocity_ratio, anomaly_reason, status, detected_at
               FROM skill_velocity_anomalies 
               WHERE user_id=? 
               ORDER BY id DESC""",
            (user_id,)
        ).fetchall()

        results = []
        for r in rows:
            res = dict(r)
            try:
                res['new_skills'] = json.loads(res['new_skills'])
            except Exception:
                pass
            res['flag_reason'] = res.get('anomaly_reason') or ''
            results.append(res)
        return results
