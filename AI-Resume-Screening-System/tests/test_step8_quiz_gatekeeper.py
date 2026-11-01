import os
import io
import time
import json
import unittest
from datetime import datetime, timedelta

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.services.candidate_skills_service import declare_blind_skills, get_candidate_skills
from app.services.quiz_service import (
    check_quiz_eligibility,
    get_quiz_for_skill,
    submit_quiz_answers,
    get_user_quiz_history,
    PASSING_THRESHOLD
)
from app.ml.ranking.ranking_engine import compute_candidate_score


class TestStep8QuizGatekeeper(unittest.TestCase):
    """
    Test Step 8: Technical Quiz Gatekeeper for Disputed / Sudden Skills.
    Verifies that:
    1. Unauthenticated requests to quiz endpoints are rejected with HTTP 401.
    2. Assessment questions returned to the candidate have correct_option masked.
    3. Passing score (>=70%) elevates skill to 1.0 confidence and source='quiz_verified'.
    4. Failing score (<70%) does not elevate skill and keeps confidence un-elevated (0.2).
    5. Passing a quiz clears active velocity anomaly records matching that skill ('verified').
    6. Clearing all velocity anomalies for a candidate resets users.is_outlier to 0.
    7. Anti-gaming rate limit: 2 attempts within 24 hours triggers cooldown (HTTP 429).
    8. Eligibility check recognizes already-verified skills.
    9. Ranking engine awards full 1.0 evidence weight to quiz-verified skills.
    10. HR recruiters can inspect candidate quiz attempts via /api/admin/candidate/<id>/quizzes (protected by 403).
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def _reg_user(self, name: str, email: str, role: str = "candidate") -> int:
        res = register_user(name, email, "SecurePass123!", role, allow_privileged=(role != "candidate"), is_verified=1)
        return res["user"]["id"]

    def test_unauthenticated_quiz_requests_rejected(self):
        """Quiz endpoints require authentication; return 401/redirect for unauthenticated requests."""
        resp1 = self.client.get('/api/user/quiz/python')
        self.assertIn(resp1.status_code, (401, 302))

        resp2 = self.client.post('/api/user/quiz/python/submit', json={'answers': {}})
        self.assertIn(resp2.status_code, (401, 302))

        resp3 = self.client.get('/api/user/quizzes')
        self.assertIn(resp3.status_code, (401, 302))

    def test_fetch_quiz_questions_masks_correct_options(self):
        """Assessment questions sent to the candidate must never expose correct_option."""
        email = f"quiz_cand_{int(time.time()*1000)}@test.com"
        cand_id = self._reg_user("Quiz Candidate", email, "candidate")

        with self.client.session_transaction() as sess:
            sess['user_id'] = cand_id
            sess['role'] = 'candidate'

        resp = self.client.get('/api/user/quiz/docker')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['num_questions'], 1)
        self.assertEqual(data['passing_threshold'], PASSING_THRESHOLD)

        questions = data['questions']
        self.assertGreater(len(questions), 0)
        for q in questions:
            self.assertIn('id', q)
            self.assertIn('question', q)
            self.assertIn('options', q)
            self.assertIn('difficulty', q)
            # Critical anti-gaming guarantee: correct_option must not be leaked
            self.assertNotIn('correct_option', q)
            self.assertNotIn('correct_answer', q)

    def test_submit_passing_score_elevates_candidate_skill(self):
        """Passing quiz (>=70%) elevates candidate_skills to confidence 1.0 and source='quiz_verified'."""
        email = f"pass_cand_{int(time.time()*1000)}@test.com"
        cand_id = self._reg_user("Pass Candidate", email, "candidate")

        # Pre-declare Docker as bare/self-declared skill (confidence 0.2)
        declare_blind_skills(cand_id, ["Docker"])
        initial_skills = get_candidate_skills(cand_id)
        docker_initial = next(s for s in initial_skills if s['skill'].lower() == 'docker')
        self.assertEqual(docker_initial['confidence'], 0.2)
        self.assertEqual(docker_initial['source'], 'self_declared')

        # Find questions and correct answers for Docker
        with get_db() as conn:
            rows = conn.execute("SELECT id, correct_option FROM quiz_questions WHERE LOWER(skill)='docker'").fetchall()

        answers = {str(r['id']): r['correct_option'] for r in rows}

        with self.client.session_transaction() as sess:
            sess['user_id'] = cand_id
            sess['role'] = 'candidate'

        resp = self.client.post('/api/user/quiz/docker/submit', json={'answers': answers})
        self.assertEqual(resp.status_code, 200)
        res = resp.get_json()
        self.assertTrue(res['success'])
        self.assertTrue(res['passed'])
        self.assertGreaterEqual(res['score'], 70)
        self.assertEqual(res['evidence_weight'], 1.0)
        self.assertIn('Quiz Verified', res['status'])

        # Verify candidate_skills table is elevated
        elevated_skills = get_candidate_skills(cand_id)
        docker_elevated = next(s for s in elevated_skills if s['skill'].lower() == 'docker')
        self.assertEqual(docker_elevated['confidence'], 1.0)
        self.assertEqual(docker_elevated['source'], 'quiz_verified')

    def test_submit_failing_score_does_not_elevate_candidate_skill(self):
        """Failing quiz (<70%) leaves confidence at un-elevated level (0.2)."""
        email = f"fail_cand_{int(time.time()*1000)}@test.com"
        cand_id = self._reg_user("Fail Candidate", email, "candidate")

        declare_blind_skills(cand_id, ["Kubernetes"])

        # Intentionally provide all wrong answers (index 99)
        with get_db() as conn:
            rows = conn.execute("SELECT id FROM quiz_questions WHERE LOWER(skill)='kubernetes'").fetchall()

        wrong_answers = {str(r['id']): 99 for r in rows}

        with self.client.session_transaction() as sess:
            sess['user_id'] = cand_id
            sess['role'] = 'candidate'

        resp = self.client.post('/api/user/quiz/kubernetes/submit', json={'answers': wrong_answers})
        self.assertEqual(resp.status_code, 200)
        res = resp.get_json()
        self.assertTrue(res['success'])
        self.assertFalse(res['passed'])
        self.assertEqual(res['score'], 0)
        self.assertEqual(res['evidence_weight'], 0.2)

        # Verify candidate_skills remains 0.2
        k8s_skill = next(s for s in get_candidate_skills(cand_id) if s['skill'].lower() == 'kubernetes')
        self.assertEqual(k8s_skill['confidence'], 0.2)
        self.assertEqual(k8s_skill['source'], 'self_declared')

    def test_passing_quiz_resolves_velocity_anomaly(self):
        """Passing technical quiz for a disputed skill resolves the anomaly in skill_velocity_anomalies."""
        email = f"anomaly_cand_{int(time.time()*1000)}@test.com"
        cand_id = self._reg_user("Anomaly Candidate", email, "candidate")

        # Inject flagged velocity anomaly for Kubernetes
        with get_db() as conn:
            conn.execute(
                """INSERT INTO skill_velocity_anomalies
                   (user_id, current_resume_id, elapsed_days, estimated_days, new_skills, severity, velocity_ratio, anomaly_reason, status)
                   VALUES (?, 1, 1.0, 90.0, ?, 'critical', 90.0, 'Sudden Kubernetes acquisition', 'flagged')""",
                (cand_id, json.dumps(["Kubernetes"]))
            )
            conn.execute("UPDATE users SET is_outlier=1 WHERE id=?", (cand_id,))
            conn.commit()

        # Submit passing score for Kubernetes
        with get_db() as conn:
            rows = conn.execute("SELECT id, correct_option FROM quiz_questions WHERE LOWER(skill)='kubernetes'").fetchall()
        answers = {str(r['id']): r['correct_option'] for r in rows}

        submit_result = submit_quiz_answers(cand_id, "Kubernetes", answers)
        self.assertTrue(submit_result['passed'])

        # Verify anomaly is marked 'verified'
        with get_db() as conn:
            a_row = conn.execute(
                "SELECT status FROM skill_velocity_anomalies WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (cand_id,)
            ).fetchone()
            self.assertEqual(a_row['status'], 'verified')

    def test_clearing_all_anomalies_clears_user_outlier_status(self):
        """When all velocity anomalies are resolved via quiz, users.is_outlier is reset to 0."""
        email = f"outlier_cand_{int(time.time()*1000)}@test.com"
        cand_id = self._reg_user("Outlier Candidate", email, "candidate")

        # Inject single anomaly for Python
        with get_db() as conn:
            conn.execute(
                """INSERT INTO skill_velocity_anomalies
                   (user_id, current_resume_id, elapsed_days, estimated_days, new_skills, severity, velocity_ratio, anomaly_reason, status)
                   VALUES (?, 1, 0.5, 45.0, ?, 'critical', 90.0, 'Sudden Python acquisition', 'flagged')""",
                (cand_id, json.dumps(["Python"]))
            )
            conn.execute("UPDATE users SET is_outlier=1 WHERE id=?", (cand_id,))
            conn.commit()

        # Check initial outlier status
        with get_db() as conn:
            user_row = conn.execute("SELECT is_outlier FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertEqual(user_row['is_outlier'], 1)

        # Pass Python quiz
        with get_db() as conn:
            rows = conn.execute("SELECT id, correct_option FROM quiz_questions WHERE LOWER(skill)='python'").fetchall()
        answers = {str(r['id']): r['correct_option'] for r in rows}

        submit_quiz_answers(cand_id, "Python", answers)

        # Outlier status must now be reset to 0
        with get_db() as conn:
            user_row = conn.execute("SELECT is_outlier FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertEqual(user_row['is_outlier'], 0)

    def test_quiz_attempt_limit_and_cooldown_enforcement(self):
        """Enforces anti-gaming rate limit: 2 attempts in 24 hours per skill blocks 3rd attempt with 429."""
        email = f"cooldown_cand_{int(time.time()*1000)}@test.com"
        cand_id = self._reg_user("Cooldown Candidate", email, "candidate")

        with self.client.session_transaction() as sess:
            sess['user_id'] = cand_id
            sess['role'] = 'candidate'

        # Attempt 1: fail
        self.client.post('/api/user/quiz/aws/submit', json={'answers': {'1': 99}})
        # Attempt 2: fail
        self.client.post('/api/user/quiz/aws/submit', json={'answers': {'1': 99}})

        # Attempt 3: blocked by 24h cooldown
        resp3 = self.client.get('/api/user/quiz/aws')
        self.assertEqual(resp3.status_code, 429)
        d3 = resp3.get_json()
        self.assertTrue(d3.get('cooldown_active'))
        self.assertIn("Maximum 2 attempts reached", d3.get('message', ''))

        # Direct submit also blocked
        sub_resp = self.client.post('/api/user/quiz/aws/submit', json={'answers': {'1': 99}})
        sub_d = sub_resp.get_json()
        self.assertFalse(sub_d.get('success'))
        self.assertTrue(sub_d.get('cooldown_active'))

    def test_already_verified_skill_check(self):
        """Candidates cannot retake quiz if skill is already verified."""
        email = f"verified_cand_{int(time.time()*1000)}@test.com"
        cand_id = self._reg_user("Verified Candidate", email, "candidate")

        with get_db() as conn:
            rows = conn.execute("SELECT id, correct_option FROM quiz_questions WHERE LOWER(skill)='sql'").fetchall()
        answers = {str(r['id']): r['correct_option'] for r in rows}

        # Pass quiz
        submit_quiz_answers(cand_id, "SQL", answers)

        # Check eligibility
        eligible, msg, meta = check_quiz_eligibility(cand_id, "SQL")
        self.assertTrue(eligible)
        self.assertTrue(meta.get('already_verified'))
        self.assertGreaterEqual(meta.get('verified_score', 0), 70)

    def test_ranking_engine_awards_full_weight_to_quiz_verified_skills(self):
        """Skills verified via technical assessment receive full 1.0 Tier 1 weight in ranking."""
        cand_verified = {
            'candidate_skills': [{'skill': 'Docker', 'source': 'quiz_verified', 'confidence': 1.0}],
            'experience_lines': [],
            'projects': [],
            'ats_score': 70
        }
        cand_unverified = {
            'candidate_skills': [{'skill': 'Docker', 'source': 'self_declared', 'confidence': 0.2}],
            'experience_lines': [],
            'projects': [],
            'ats_score': 70
        }

        job_skills = ['Docker']

        score_v = compute_candidate_score(cand_verified, job_skills)
        score_u = compute_candidate_score(cand_unverified, job_skills)

        # Quiz-verified candidate receives 1.0 weight under 'verified' source
        self.assertEqual(score_v['skill_evidence']['Docker']['weight'], 1.0)
        self.assertEqual(score_v['skill_evidence']['Docker']['source'], 'verified')

        # Unverified candidate receives 0.2 weight under 'self_declared' source
        self.assertEqual(score_u['skill_evidence']['Docker']['weight'], 0.2)
        self.assertEqual(score_u['skill_evidence']['Docker']['source'], 'self_declared')

        # Total skills score is substantially higher for verified candidate
        self.assertGreater(score_v['skills_score'], score_u['skills_score'])

    def test_admin_candidate_quizzes_endpoint(self):
        """HR recruiters can view candidate quiz attempts; unauthorized users are rejected with 403."""
        email_hr = f"hr_{int(time.time()*1000)}@test.com"
        hr_id = self._reg_user("HR Admin", email_hr, "hr")

        email_cand = f"cand_{int(time.time()*1000)}@test.com"
        cand_id = self._reg_user("Quiz Taker", email_cand, "candidate")

        # Candidate submits a quiz
        with get_db() as conn:
            rows = conn.execute("SELECT id, correct_option FROM quiz_questions WHERE LOWER(skill)='python'").fetchall()
        answers = {str(r['id']): r['correct_option'] for r in rows}
        submit_quiz_answers(cand_id, "Python", answers)

        # 1. Candidate attempts to access HR quiz inspection endpoint -> 403 Forbidden
        with self.client.session_transaction() as sess:
            sess['user_id'] = cand_id
            sess['role'] = 'candidate'

        resp_cand = self.client.get(f'/api/admin/candidate/{cand_id}/quizzes')
        self.assertIn(resp_cand.status_code, (403, 302))

        # 2. HR accesses candidate quiz inspection endpoint -> 200 OK
        with self.client.session_transaction() as sess:
            sess['user_id'] = hr_id
            sess['role'] = 'hr'

        resp_hr = self.client.get(f'/api/admin/candidate/{cand_id}/quizzes')
        self.assertEqual(resp_hr.status_code, 200)
        data = resp_hr.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user_id'], cand_id)
        self.assertGreaterEqual(data['total_attempts'], 1)
        self.assertIn('Python', data['verified_skills'])


if __name__ == '__main__':
    unittest.main()
