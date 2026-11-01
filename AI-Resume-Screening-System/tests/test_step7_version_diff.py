import os
import io
import time
import json
import unittest
from datetime import datetime, timedelta
import docx as python_docx
from werkzeug.datastructures import FileStorage

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.controllers.resume_controller import process_resume_upload
from app.ml.velocity.learning_timeline_engine import (
    get_skill_learning_time,
    compute_required_learning_time,
    diff_resume_skillsets,
    detect_velocity_anomaly,
    CANONICAL_LEARNING_DAYS
)
from app.services.velocity_service import (
    check_and_record_velocity_anomaly,
    get_user_velocity_anomalies
)
from app.services.candidate_skills_service import declare_blind_skills


def _make_resume_docx(name: str, skills: str, role: str) -> io.BytesIO:
    """Create a minimal docx resume stream with unique content."""
    doc = python_docx.Document()
    doc.add_paragraph(f"Name: {name}")
    doc.add_paragraph(f"Role: {role}")
    doc.add_paragraph(f"Skills: {skills}")
    doc.add_paragraph(f"Experience: 4 years working as a {role} building software systems.")
    doc.add_paragraph("Education: Bachelor of Technology in Computer Science")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


class TestStep7LearningTimelineEngine(unittest.TestCase):
    """
    Test Step 7: Learning Timeline Engine & Velocity Anomaly Detection.
    Verifies that:
    1. Canonical learning times reflect realistic domain complexity tiers (Tier 1 vs 2 vs 3).
    2. Multi-skill learning aggregation formula respects cognitive limits.
    3. Engine triggers severe anomalies when complex skills are added within unrealistic timeframes (<3 days).
    4. Engine produces clean results when learning intervals are realistic (e.g. 45+ days).
    5. First-time resume uploads establish a baseline and never trigger velocity anomalies.
    6. Consecutive uploads with impossible velocities are recorded in `skill_velocity_anomalies` and flag `users.is_outlier`.
    7. Consecutive uploads with same or reduced skills do not trigger anomalies.
    8. Candidate can query their velocity status and disputed skills via `/api/user/velocity`.
    9. HR recruiters can view candidate velocity history via `/api/admin/candidate/<id>/velocity` (protected by 403).
    10. Skills previously declared via blind confirmation do not cause false-positive velocity flags on subsequent resume uploads.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_canonical_learning_durations(self):
        """Tier 1 tools take 3-7 days, Tier 2 languages take 21-45 days, Tier 3 cloud/systems take 45-90 days."""
        self.assertEqual(get_skill_learning_time("Markdown"), 3.0)
        self.assertEqual(get_skill_learning_time("Git"), 7.0)
        self.assertEqual(get_skill_learning_time("Python"), 30.0)
        self.assertEqual(get_skill_learning_time("Java"), 45.0)
        self.assertEqual(get_skill_learning_time("Kubernetes"), 60.0)
        self.assertEqual(get_skill_learning_time("AWS"), 60.0)
        self.assertEqual(get_skill_learning_time("Distributed Systems"), 75.0)

    def test_multi_skill_learning_aggregation(self):
        """Multi-skill aggregation formula: max(T) + 0.5 * sum(remaining)."""
        skills = ["Kubernetes", "Docker"]
        # Kubernetes = 60, Docker = 25 -> 60 + 0.5 * 25 = 72.5
        expected = 60.0 + (0.5 * 25.0)
        self.assertEqual(compute_required_learning_time(skills), expected)

        # Single skill returns its exact time
        self.assertEqual(compute_required_learning_time(["Python"]), 30.0)

    def test_detect_velocity_anomaly_triggers_on_rapid_acquisition(self):
        """Adding Kubernetes and AWS in 24 hours triggers severe velocity anomaly."""
        prev = ["HTML", "CSS"]
        curr = ["HTML", "CSS", "Kubernetes", "AWS"]

        # 1 day elapsed vs ~90 days required
        result = detect_velocity_anomaly(prev, curr, elapsed_days=1.0)
        self.assertTrue(result['is_anomaly'])
        self.assertEqual(result['severity'], 'high')
        self.assertIn('Kubernetes', result['added_skills'])
        self.assertIn('AWS', result['added_skills'])
        self.assertIn('Unrealistic Skill Acquisition Anomaly', result['flag_reason'])
        self.assertLess(result['velocity_ratio'], 0.10)

    def test_detect_velocity_anomaly_clean_when_timeline_is_realistic(self):
        """Adding Python with 45 elapsed days is considered normal and clean."""
        prev = ["HTML", "CSS"]
        curr = ["HTML", "CSS", "Python"]

        # 45 days elapsed vs 30 days required for Python
        result = detect_velocity_anomaly(prev, curr, elapsed_days=45.0)
        self.assertFalse(result['is_anomaly'])
        self.assertEqual(result['severity'], 'none')

    def test_first_resume_upload_never_triggers_anomaly(self):
        """Initial resume upload establishes baseline without anomaly."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_first_{ts}@test.com"
        cand_id = register_user("First Uploader", cand_email, "Password123!", "candidate")["user"]["id"]

        stream = _make_resume_docx("First Uploader", "Python, Docker, Kubernetes, AWS", "DevOps Engineer")
        fs = FileStorage(stream=stream, filename=f"initial_resume_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        res = process_resume_upload(fs, user_id=cand_id)
        self.assertTrue(res['success'])
        self.assertIsNotNone(res.get('resume_id'))

        # Check no anomaly in DB
        anomalies = get_user_velocity_anomalies(cand_id)
        self.assertEqual(len(anomalies), 0)

        with get_db() as conn:
            u_row = conn.execute("SELECT is_outlier FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertEqual(u_row['is_outlier'], 0)

    def test_consecutive_uploads_with_impossible_velocity_flagged_in_db(self):
        """Second upload with sudden complex skills creates an anomaly log and flags is_outlier."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_rapid_{ts}@test.com"
        cand_id = register_user("Rapid Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        # Upload 1: Basic web skills
        s1 = _make_resume_docx("Rapid Candidate", "HTML, CSS, Git", "Junior Web Dev")
        fs1 = FileStorage(stream=s1, filename=f"resume_v1_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res1 = process_resume_upload(fs1, user_id=cand_id)
        self.assertTrue(res1['success'])
        r1_id = res1['resume_id']

        # Ensure timestamp of resume 1 is set to 2 hours ago
        two_hours_ago = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        with get_db() as conn:
            conn.execute("UPDATE resumes SET uploaded_at=? WHERE id=?", (two_hours_ago, r1_id))
            conn.commit()

        # Upload 2: Added Kubernetes, AWS, Distributed Systems in 2 hours
        s2 = _make_resume_docx("Rapid Candidate", "HTML, CSS, Git, Kubernetes, AWS, Distributed Systems", "Principal Cloud Architect")
        fs2 = FileStorage(stream=s2, filename=f"resume_v2_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res2 = process_resume_upload(fs2, user_id=cand_id)
        self.assertTrue(res2['success'])

        # Anomaly must be triggered
        self.assertIsNotNone(res2.get('velocity_anomaly'))
        self.assertTrue(res2['velocity_anomaly']['is_anomaly'])
        self.assertEqual(res2['velocity_anomaly']['severity'], 'high')

        # Check database records
        anomalies = get_user_velocity_anomalies(cand_id)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]['previous_resume_id'], r1_id)
        self.assertEqual(anomalies[0]['status'], 'flagged')

        with get_db() as conn:
            u_row = conn.execute("SELECT is_outlier FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertEqual(u_row['is_outlier'], 1)

    def test_consecutive_uploads_with_same_skills_remain_clean(self):
        """Second upload with unchanged skills does not trigger velocity anomaly."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_same_{ts}@test.com"
        cand_id = register_user("Same Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        # Upload 1
        s1 = _make_resume_docx("Same Candidate", "Python, Flask", "Backend Dev")
        fs1 = FileStorage(stream=s1, filename=f"res_v1_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res1 = process_resume_upload(fs1, user_id=cand_id)
        self.assertTrue(res1['success'])

        # Upload 2: Same skills, different text
        s2 = _make_resume_docx("Same Candidate", "Python, Flask", "Senior Backend Dev")
        fs2 = FileStorage(stream=s2, filename=f"res_v2_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res2 = process_resume_upload(fs2, user_id=cand_id)
        self.assertTrue(res2['success'])
        self.assertFalse(res2['velocity_anomaly']['is_anomaly'])

        anomalies = get_user_velocity_anomalies(cand_id)
        self.assertEqual(len(anomalies), 0)

    def test_candidate_velocity_endpoint(self):
        """Candidate can view their velocity status and flagged skills list."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_vel_route_{ts}@test.com"
        cand_id = register_user("Vel Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        # Initially normal
        res1 = self.client.get('/api/user/velocity')
        self.assertEqual(res1.status_code, 200)
        d1 = res1.get_json()
        self.assertTrue(d1['success'])
        self.assertFalse(d1['has_anomaly'])
        self.assertEqual(d1['disputed_skills'], [])

        # Manually insert flagged anomaly
        with get_db() as conn:
            conn.execute(
                """INSERT INTO skill_velocity_anomalies 
                   (user_id, previous_resume_id, current_resume_id, elapsed_days, estimated_days, new_skills, severity, velocity_ratio, anomaly_reason, status)
                   VALUES (?, 1, 2, 0.5, 75.0, ?, 'high', 0.006, 'Sudden Kubernetes & AWS', 'flagged')""",
                (cand_id, json.dumps(['Kubernetes', 'AWS']))
            )
            conn.commit()

        res2 = self.client.get('/api/user/velocity')
        self.assertEqual(res2.status_code, 200)
        d2 = res2.get_json()
        self.assertTrue(d2['has_anomaly'])
        self.assertIn('Kubernetes', d2['disputed_skills'])
        self.assertIn('AWS', d2['disputed_skills'])

    def test_hr_candidate_velocity_endpoint(self):
        """HR recruiter can inspect candidate velocity history; non-HR users receive HTTP 403."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_target_v_{ts}@test.com"
        cand_id = register_user("Target V", cand_email, "Password123!", "candidate")["user"]["id"]

        hr_email = f"hr_vel_{ts}@test.com"
        hr_id = register_user("HR Inspector", hr_email, "Password123!", "hr", allow_privileged=True, is_verified=1)["user"]["id"]

        # Candidate cannot access HR velocity endpoint
        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        cand_call = self.client.get(f'/api/admin/candidate/{cand_id}/velocity')
        self.assertEqual(cand_call.status_code, 403)

        # HR can access
        with self.client.session_transaction() as sess:
            sess["user_id"] = hr_id
            sess["role"] = "hr"

        hr_call = self.client.get(f'/api/admin/candidate/{cand_id}/velocity')
        self.assertEqual(hr_call.status_code, 200)
        hr_data = hr_call.get_json()
        self.assertTrue(hr_data['success'])
        self.assertEqual(hr_data['user_id'], cand_id)

    def test_prior_blind_confirmed_skills_exempt_from_velocity_anomaly(self):
        """Skills previously confirmed blindly in Step 6 do not trigger false positive velocity flags."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_prior_{ts}@test.com"
        cand_id = register_user("Prior Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        # Candidate previously confirmed Docker blindly
        declare_blind_skills(cand_id, ['Docker'])

        # Upload 1: HTML, CSS
        s1 = _make_resume_docx("Prior Candidate", "HTML, CSS", "Frontend")
        fs1 = FileStorage(stream=s1, filename=f"r1_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        process_resume_upload(fs1, user_id=cand_id)

        # Upload 2 (2 hours later): Added Docker to resume
        s2 = _make_resume_docx("Prior Candidate", "HTML, CSS, Docker", "Fullstack")
        fs2 = FileStorage(stream=s2, filename=f"r2_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res2 = process_resume_upload(fs2, user_id=cand_id)

        # Docker was already known and confirmed -> No anomaly
        self.assertFalse(res2['velocity_anomaly']['is_anomaly'])


if __name__ == "__main__":
    unittest.main()
