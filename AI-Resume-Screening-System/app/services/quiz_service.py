"""
TalentSync — Technical Quiz Gatekeeper Service (Step 8)
Orchestrates technical assessments for disputed/rapid skills, enforces anti-gaming attempt cooldowns,
authoritatively scores submissions server-side, and elevates verified skills to 1.0 evidence weight.

Anti-Gaming Rules:
1. Pass Threshold: >= 70% score required.
2. Attempt Limit & Cooldown: Max 2 attempts per 24 hours per skill to prevent brute-force guessing.
3. Server-Side Integrity: Correct answers are never sent to the client.
4. Elevation: Passing marks skill as 'quiz_verified' (1.0 weight) in candidate_skills, clears
   velocity anomaly flags, and resets users.is_outlier if all disputes are cleared.
"""

import json
import random
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from app.database.connection import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)

PASSING_THRESHOLD = 70
MAX_ATTEMPTS_PER_WINDOW = 2
COOLDOWN_WINDOW_HOURS = 24
DEFAULT_NUM_QUESTIONS = 5
TIME_LIMIT_SECONDS = 300  # 5 minutes


def check_quiz_eligibility(user_id: int, skill: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Check if a candidate is eligible to take an assessment for a given skill.
    Enforces cooldown after 2 attempts in 24 hours, and detects if already verified.
    """
    if not user_id or not skill:
        return False, "User ID and skill name are required.", {}

    s_clean = skill.strip().lower()

    with get_db() as conn:
        # 1. Check if already verified
        passed_row = conn.execute(
            """SELECT id, score, attempted_at FROM quiz_attempts 
               WHERE user_id=? AND LOWER(skill)=? AND passed=1 
               ORDER BY id DESC LIMIT 1""",
            (user_id, s_clean)
        ).fetchone()

        if passed_row:
            return True, "Skill already verified via assessment.", {
                'already_verified': True,
                'verified_score': passed_row['score'],
                'verified_at': passed_row['attempted_at']
            }

        # 2. Check 24-hour attempt rate limiting
        attempts = conn.execute(
            """SELECT attempted_at, passed FROM quiz_attempts 
               WHERE user_id=? AND LOWER(skill)=? 
               ORDER BY id DESC""",
            (user_id, s_clean)
        ).fetchall()

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        now_loc = datetime.now()
        recent_attempts = 0
        oldest_recent_dt = None

        for att in attempts:
            t_str = att['attempted_at']
            if not t_str:
                continue
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'):
                try:
                    att_dt = datetime.strptime(str(t_str).split('.')[0], fmt)
                    delta_sec = min(
                        abs((now_utc - att_dt).total_seconds()),
                        abs((now_loc - att_dt).total_seconds())
                    )
                    delta_hours = delta_sec / 3600.0
                    if delta_hours <= COOLDOWN_WINDOW_HOURS:
                        recent_attempts += 1
                        oldest_recent_dt = att_dt
                    break
                except ValueError:
                    continue

        if recent_attempts >= MAX_ATTEMPTS_PER_WINDOW:
            hours_left = max(round(COOLDOWN_WINDOW_HOURS - ((now_loc - oldest_recent_dt).total_seconds() / 3600.0), 1), 0.5) if oldest_recent_dt else 24.0
            return False, f"Maximum 2 attempts reached for {skill} within 24 hours. Retake available after cooldown.", {
                'cooldown_active': True,
                'attempts_in_window': recent_attempts,
                'hours_remaining': hours_left
            }

    return True, "Eligible to take assessment.", {'already_verified': False, 'recent_attempts': recent_attempts}


def get_quiz_for_skill(user_id: int, skill: str, num_questions: int = DEFAULT_NUM_QUESTIONS) -> Dict[str, Any]:
    """
    Fetch a randomized set of questions for a skill with correct answers stripped out.
    """
    eligible, msg, meta = check_quiz_eligibility(user_id, skill)
    if not eligible and meta.get('cooldown_active'):
        return {
            'success': False,
            'message': msg,
            'cooldown_active': True,
            'hours_remaining': meta.get('hours_remaining', 24)
        }

    s_clean = skill.strip().lower()

    with get_db() as conn:
        # Query specific questions for this skill
        rows = conn.execute(
            """SELECT id, skill, question, options, difficulty 
               FROM quiz_questions 
               WHERE LOWER(skill)=?""",
            (s_clean,)
        ).fetchall()

        # If question bank has fewer than requested, supplement with general architectural questions
        if len(rows) < num_questions:
            supplement = conn.execute(
                """SELECT id, skill, question, options, difficulty 
                   FROM quiz_questions 
                   WHERE LOWER(skill) != ? 
                   ORDER BY id ASC LIMIT ?""",
                (s_clean, num_questions - len(rows))
            ).fetchall()
            combined_rows = list(rows) + list(supplement)
        else:
            combined_rows = list(rows)

        if not combined_rows:
            return {'success': False, 'message': f"No assessment questions currently available for '{skill}'."}

        # Randomize selection and question order
        random.shuffle(combined_rows)
        selected = combined_rows[:num_questions]

        client_questions = []
        for r in selected:
            raw_opts = r['options']
            try:
                opts_list = json.loads(raw_opts) if isinstance(raw_opts, str) else raw_opts
            except Exception:
                opts_list = ["True", "False"]

            client_questions.append({
                'id': r['id'],
                'skill': r['skill'],
                'question': r['question'],
                'options': opts_list,
                'difficulty': r['difficulty']
            })

    return {
        'success': True,
        'skill': skill,
        'num_questions': len(client_questions),
        'passing_threshold': PASSING_THRESHOLD,
        'time_limit_seconds': TIME_LIMIT_SECONDS,
        'questions': client_questions
    }


def submit_quiz_answers(user_id: int, skill: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Server-side authoritative evaluation of submitted quiz answers.
    Answers format: { "<question_id>": <selected_option_index_int>, ... }
    """
    if not user_id or not skill or not isinstance(answers, dict):
        return {'success': False, 'message': 'Invalid submission payload.'}

    eligible, msg, meta = check_quiz_eligibility(user_id, skill)
    if not eligible and meta.get('cooldown_active'):
        return {
            'success': False,
            'message': msg,
            'cooldown_active': True,
            'hours_remaining': meta.get('hours_remaining', 24)
        }

    s_clean = skill.strip().lower()

    with get_db() as conn:
        correct_count = 0
        total_questions = len(answers)
        if total_questions == 0:
            return {'success': False, 'message': 'No answers submitted.'}

        # Check each answer against DB
        for q_id_str, selected_idx in answers.items():
            try:
                q_id = int(q_id_str)
                row = conn.execute(
                    "SELECT correct_option FROM quiz_questions WHERE id=?",
                    (q_id,)
                ).fetchone()
                if row and int(selected_idx) == row['correct_option']:
                    correct_count += 1
            except Exception:
                pass

        score_pct = round((correct_count / total_questions) * 100)
        passed = 1 if score_pct >= PASSING_THRESHOLD else 0

        # Record attempt
        conn.execute(
            """INSERT INTO quiz_attempts 
               (user_id, skill, score, total_questions, correct_answers, passed, attempted_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
            (user_id, skill, score_pct, total_questions, correct_count, passed)
        )

        if passed == 1:
            # 1. Elevate skill in candidate_skills table to 1.0 confidence
            existing_sk = conn.execute(
                "SELECT id, skill FROM candidate_skills WHERE user_id=? AND LOWER(skill)=?",
                (user_id, s_clean)
            ).fetchone()

            if existing_sk:
                conn.execute(
                    """UPDATE candidate_skills 
                       SET confidence=1.0, source='quiz_verified', confirmed_at=datetime('now')
                       WHERE user_id=? AND LOWER(skill)=?""",
                    (user_id, s_clean)
                )
            else:
                conn.execute(
                    """INSERT INTO candidate_skills (user_id, skill, source, confidence, confirmed_at)
                       VALUES (?, ?, 'quiz_verified', 1.0, datetime('now'))""",
                    (user_id, skill)
                )

            # 2. Clear velocity anomaly for this skill if present
            anomaly_rows = conn.execute(
                "SELECT id, new_skills FROM skill_velocity_anomalies WHERE user_id=? AND status='flagged'",
                (user_id,)
            ).fetchall()

            for a_row in anomaly_rows:
                a_id = a_row['id']
                raw_s = a_row['new_skills']
                try:
                    s_list = json.loads(raw_s) if isinstance(raw_s, str) else raw_s
                    if isinstance(s_list, list) and any(s.strip().lower() == s_clean for s in s_list):
                        conn.execute(
                            "UPDATE skill_velocity_anomalies SET status='verified' WHERE id=?",
                            (a_id,)
                        )
                except Exception:
                    pass

            # 3. If all velocity anomalies for user are cleared, reset users.is_outlier = 0
            remaining_anomalies = conn.execute(
                "SELECT COUNT(*) FROM skill_velocity_anomalies WHERE user_id=? AND status='flagged'",
                (user_id,)
            ).fetchone()[0]

            if remaining_anomalies == 0:
                conn.execute("UPDATE users SET is_outlier=0 WHERE id=?", (user_id,))

            # 4. Sync users.skills
            all_candidate_skills = conn.execute(
                "SELECT skill FROM candidate_skills WHERE user_id=? ORDER BY skill ASC",
                (user_id,)
            ).fetchall()
            merged_str = ", ".join(r['skill'] for r in all_candidate_skills)
            conn.execute("UPDATE users SET skills=? WHERE id=?", (merged_str, user_id))

        conn.commit()

    return {
        'success': True,
        'skill': skill,
        'passed': bool(passed),
        'score': score_pct,
        'passing_threshold': PASSING_THRESHOLD,
        'correct_answers': correct_count,
        'total_questions': total_questions,
        'evidence_weight': 1.0 if passed else 0.2,
        'status': 'Quiz Verified (1.0)' if passed else 'Assessment Not Passed',
        'message': (
            f"Congratulations! You scored {score_pct}%. '{skill}' is now verified with full 1.0 evidence weight."
            if passed else
            f"You scored {score_pct}%. Score did not meet the {PASSING_THRESHOLD}% threshold. You may retake the assessment after cooldown."
        )
    }


def get_user_quiz_history(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve full quiz history for a candidate."""
    if not user_id:
        return []

    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, skill, score, total_questions, correct_answers, passed, attempted_at 
               FROM quiz_attempts 
               WHERE user_id=? 
               ORDER BY id DESC""",
            (user_id,)
        ).fetchall()

        return [dict(r) for r in rows]
