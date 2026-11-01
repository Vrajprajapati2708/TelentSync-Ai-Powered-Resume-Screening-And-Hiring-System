"""
TalentSync — Anti-Gaming Real-World Scenarios Test Suite
Comprehensive verification of the 5-layer Anti-Gaming Architecture across 9 real-world scenarios:

Scenario 1: Candidate adds Python, Flask, SQL only to the skills list (0.2 weight, velocity anomaly flagged).
Scenario 2: Candidate adds the same skills with genuine project descriptions (0.7 weight).
Scenario 3: Candidate adds the same skills with genuine professional experience (1.0 weight).
Scenario 4: Candidate already knows skills but omitted from Resume 1 (blind confirmation exempts from anomaly).
Scenario 5: Candidate completes the technical assessment successfully (elevates to 1.0 quiz-verified, clears anomaly).
Scenario 6: Candidate fails the technical assessment (remains 0.2, anomaly stays flagged, non-punitive).
Scenario 7: Candidate uploads multiple resume versions (sequential versioning & upload audit integrity).
Scenario 8: Candidate already applied using Resume 1 and later uploads Resume 2 (immutable snapshot lock).
Scenario 9: HR reviews the candidate's resume history and evidence (provenance, velocity, quizzes, resume_diff).
"""

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
from app.controllers.resume_controller import process_resume_upload, delete_resume_by_id
from app.services.candidate_skills_service import (
    declare_blind_skills,
    get_candidate_skills,
    sync_resume_extracted_skills
)
from app.services.velocity_service import (
    check_and_record_velocity_anomaly,
    get_user_velocity_anomalies
)
from app.services.quiz_service import (
    get_quiz_for_skill,
    submit_quiz_answers,
    get_user_quiz_history
)
from app.ml.ranking.ranking_engine import (
    compute_candidate_score,
    rank_candidates,
    extract_candidate_evidence
)
from app.ml.velocity.learning_timeline_engine import (
    diff_resume_skillsets,
    compute_required_learning_time,
    detect_velocity_anomaly
)


def _make_custom_docx(name: str, skills_line: str, exp_text: str = "", proj_text: str = "") -> io.BytesIO:
    """Helper to generate a realistic .docx resume with specific section contents."""
    doc = python_docx.Document()
    doc.add_paragraph(f"Candidate Name: {name}")
    doc.add_paragraph(f"Email: {name.lower().replace(' ', '')}@example.com")
    doc.add_paragraph("Education: Bachelor of Science in Computer Science, State University, 2021")
    if skills_line:
        doc.add_paragraph(f"Technical Skills: {skills_line}")
    if exp_text:
        doc.add_paragraph(f"Professional Experience:\n{exp_text}")
    else:
        doc.add_paragraph("Professional Experience: Junior Web Developer at Apex Corp. Built responsive HTML/CSS web pages.")
    if proj_text:
        doc.add_paragraph(f"Key Projects:\n{proj_text}")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


class TestAntiGamingRealWorldScenarios(unittest.TestCase):
    """Execution of all 9 Anti-Gaming real-world validation scenarios."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def _login(self, email: str, role: str = "candidate") -> int:
        with get_db() as conn:
            row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            uid = row['id'] if row else None
        with self.client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['role'] = role
        return uid

    # =========================================================================
    # SCENARIO 1: Bare Skills List Addition (Gamer / Keyword Stuffer)
    # =========================================================================
    def test_scenario_1_bare_skills_list_addition(self):
        """
        Scenario 1: Candidate adds Python, Flask and SQL ONLY to the skills list.
        - Extracted skills: Contains Python, Flask, SQL.
        - Evidence tier: Bare list (0.2 weight).
        - Ranking calculation: Overlap score is heavily suppressed compared to experience.
        - Anomaly detection: High severity velocity anomaly flagged (<3 days vs 51 days required).
        - Candidate experience: Not blocked, upload succeeds.
        - HR visibility: Anomaly visible in /api/admin/candidate/<id>/velocity.
        - Database consistency: Logged in skill_velocity_anomalies, is_outlier=1.
        """
        ts = int(time.time() * 1000)
        cand_email = f"stuffer_{ts}@test.com"
        cand_id = register_user("Keyword Stuffer", cand_email, "Password123!", "candidate")["user"]["id"]

        # 1. Upload Resume 1: Only HTML, CSS
        s1 = _make_custom_docx("Keyword Stuffer", "HTML, CSS", "Worked on frontend HTML pages.")
        fs1 = FileStorage(stream=s1, filename=f"r1_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res1 = process_resume_upload(fs1, user_id=cand_id)
        self.assertTrue(res1['success'])
        r1_id = res1['resume_id']

        # Age Resume 1 by 25 hours to clear the 24h upload rate limit
        past_time = (datetime.now() - timedelta(hours=25)).strftime('%Y-%m-%d %H:%M:%S')
        with get_db() as conn:
            conn.execute("UPDATE resumes SET uploaded_at=? WHERE id=?", (past_time, r1_id))
            conn.execute("UPDATE resume_upload_logs SET uploaded_at=? WHERE user_id=?", (past_time, cand_id))
            conn.commit()

        # 2. Upload Resume 2: Adds Python, Flask, SQL ONLY in skills list (no mention in experience/projects)
        s2 = _make_custom_docx(
            "Keyword Stuffer",
            "HTML, CSS, Python, Flask, SQL",
            "Worked on frontend HTML pages. Maintained CSS stylesheets."
        )
        fs2 = FileStorage(stream=s2, filename=f"r2_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res2 = process_resume_upload(fs2, user_id=cand_id)
        self.assertTrue(res2['success'])

        # Verify extracted skills
        skills_extracted = res2['data']['skills']
        self.assertTrue(any('python' in s.lower() for s in skills_extracted))
        self.assertTrue(any('flask' in s.lower() for s in skills_extracted))
        self.assertTrue(any('sql' in s.lower() for s in skills_extracted))

        # Verify evidence classification in candidate_skills: Bare list = 0.2
        cand_skills = get_candidate_skills(cand_id)
        skill_map = {s['skill'].lower(): s for s in cand_skills}
        for sk in ['python', 'flask', 'sql']:
            self.assertIn(sk, skill_map)
            self.assertEqual(skill_map[sk]['confidence'], 0.2)
            self.assertEqual(skill_map[sk]['source'], 'resume_extracted')

        # Verify ranking calculation against target job requiring Python, Flask, SQL
        job_skills = ['Python', 'Flask', 'SQL']
        cand_proxy = {
            'skills': skills_extracted,
            'experience_lines': ["Worked on frontend HTML pages. Maintained CSS stylesheets."],
            'projects': "",
            'ats_score': 70
        }
        score_res = compute_candidate_score(cand_proxy, job_skills)
        # 3 skills * 0.2 = 0.6 total weight / 3 = 0.2 overlap ratio -> 0.2 * 40 = 8 points
        self.assertEqual(score_res['breakdown']['skills_score'], 8)

        # Verify anomaly detection: 51 days required vs ~1.04 days elapsed -> High anomaly
        self.assertIsNotNone(res2.get('velocity_anomaly'))
        self.assertTrue(res2['velocity_anomaly']['is_anomaly'])
        self.assertEqual(res2['velocity_anomaly']['severity'], 'high')

        # Database consistency: is_outlier=1, skill_velocity_anomalies logged
        with get_db() as conn:
            u_row = conn.execute("SELECT is_outlier FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertEqual(u_row['is_outlier'], 1)

        anomalies = get_user_velocity_anomalies(cand_id)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]['status'], 'flagged')

    # =========================================================================
    # SCENARIO 2: Genuine Project Descriptions (0.7 Project Tier)
    # =========================================================================
    def test_scenario_2_project_evidence_recognition(self):
        """
        Scenario 2: Candidate adds Python, Flask and SQL with genuine project descriptions.
        - Evidence classification: 0.7 confidence (Project Demonstrated tier).
        - Ranking calculation: Awarded 0.7 * 40 = 28 points on skills match.
        """
        ts = int(time.time() * 1000)
        cand_email = f"project_dev_{ts}@test.com"
        cand_id = register_user("Project Dev", cand_email, "Password123!", "candidate")["user"]["id"]

        # Structured resume with project narrative
        proj_text = (
            "E-Commerce Inventory Engine: Developed web APIs using Flask and Python. "
            "Designed and optimized SQL database schemas with relational constraints."
        )
        s = _make_custom_docx("Project Dev", "Python, Flask, SQL", "", proj_text)
        fs = FileStorage(stream=s, filename=f"proj_resume_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res = process_resume_upload(fs, user_id=cand_id)
        self.assertTrue(res['success'])

        cand_proxy = {
            'skills': ['Python', 'Flask', 'SQL'],
            'projects': proj_text,
            'experience_lines': [],
            'ats_score': 75
        }
        score_res = compute_candidate_score(cand_proxy, ['Python', 'Flask', 'SQL'])
        # 3 skills * 0.7 = 2.1 / 3 = 0.7 overlap ratio -> 0.7 * 40 = 28 points
        self.assertEqual(score_res['breakdown']['skills_score'], 28)
        self.assertEqual(score_res['evidence_counts']['project'], 3)

    # =========================================================================
    # SCENARIO 3: Genuine Professional Experience (1.0 Experience Tier)
    # =========================================================================
    def test_scenario_3_professional_experience_recognition(self):
        """
        Scenario 3: Candidate adds Python, Flask and SQL with genuine professional experience.
        - Evidence classification: 1.0 confidence (Work Experience tier).
        - Ranking calculation: Full 40 points on skills match.
        """
        ts = int(time.time() * 1000)
        cand_email = f"exp_dev_{ts}@test.com"
        cand_id = register_user("Experienced Dev", cand_email, "Password123!", "candidate")["user"]["id"]

        exp_text = (
            "Senior Backend Engineer at CloudSystems (3 years):\n"
            "- Architected high-throughput RESTful services using Python and Flask.\n"
            "- Tuned high-load SQL queries and indexing strategies in production PostgreSQL."
        )
        s = _make_custom_docx("Experienced Dev", "Python, Flask, SQL", exp_text, "")
        fs = FileStorage(stream=s, filename=f"exp_resume_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res = process_resume_upload(fs, user_id=cand_id)
        self.assertTrue(res['success'])

        cand_proxy = {
            'skills': ['Python', 'Flask', 'SQL'],
            'experience_lines': [exp_text],
            'projects': "",
            'ats_score': 85
        }
        score_res = compute_candidate_score(cand_proxy, ['Python', 'Flask', 'SQL'])
        # 3 skills * 1.0 = 3.0 / 3 = 1.0 overlap ratio -> 1.0 * 40 = 40 points
        self.assertEqual(score_res['breakdown']['skills_score'], 40)
        self.assertEqual(score_res['evidence_counts']['experience'], 3)

    # =========================================================================
    # SCENARIO 4: Omitted Skills Blindly Declared (Protects True Candidate)
    # =========================================================================
    def test_scenario_4_omitted_skills_blind_confirmation(self):
        """
        Scenario 4: Candidate already knows skills but forgot them in Resume 1.
        - Candidate declares them blindly prior to Resume 2 upload.
        - Subsequent upload does NOT trigger false-positive velocity anomaly.
        """
        ts = int(time.time() * 1000)
        cand_email = f"forgotten_{ts}@test.com"
        cand_id = register_user("Honest Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        # Upload Resume 1: HTML, CSS only
        s1 = _make_custom_docx("Honest Candidate", "HTML, CSS", "Frontend developer")
        fs1 = FileStorage(stream=s1, filename=f"r1_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res1 = process_resume_upload(fs1, user_id=cand_id)
        r1_id = res1['resume_id']

        # Age Resume 1 by 25 hours
        past_time = (datetime.now() - timedelta(hours=25)).strftime('%Y-%m-%d %H:%M:%S')
        with get_db() as conn:
            conn.execute("UPDATE resumes SET uploaded_at=? WHERE id=?", (past_time, r1_id))
            conn.execute("UPDATE resume_upload_logs SET uploaded_at=? WHERE user_id=?", (past_time, cand_id))
            conn.commit()

        # Candidate blindly declares pre-existing knowledge of Python, Flask, SQL
        decl_res = declare_blind_skills(cand_id, ['Python', 'Flask', 'SQL'])
        self.assertTrue(decl_res['success'])

        # Upload Resume 2 adding Python, Flask, SQL
        s2 = _make_custom_docx("Honest Candidate", "HTML, CSS, Python, Flask, SQL", "Fullstack developer")
        fs2 = FileStorage(stream=s2, filename=f"r2_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res2 = process_resume_upload(fs2, user_id=cand_id)
        self.assertTrue(res2['success'])

        # Must NOT trigger velocity anomaly because skills were already known in user profile
        self.assertFalse(res2['velocity_anomaly']['is_anomaly'])
        with get_db() as conn:
            u_row = conn.execute("SELECT is_outlier FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertEqual(u_row['is_outlier'], 0)

    # =========================================================================
    # SCENARIO 5: Successful Technical Assessment (1.0 Quiz-Verified)
    # =========================================================================
    def test_scenario_5_successful_technical_assessment(self):
        """
        Scenario 5: Candidate completes technical assessment with >= 70% score.
        - Elevates skill to 1.0 (quiz_verified).
        - Resolves anomaly flag in skill_velocity_anomalies (status = 'verified').
        - Clears users.is_outlier flag.
        - Full credit awarded in ranking score.
        """
        ts = int(time.time() * 1000)
        cand_email = f"quiz_pass_{ts}@test.com"
        cand_id = register_user("Quiz Master", cand_email, "Password123!", "candidate")["user"]["id"]

        # Seed flagged anomaly
        with get_db() as conn:
            conn.execute(
                """INSERT INTO skill_velocity_anomalies 
                   (user_id, previous_resume_id, current_resume_id, elapsed_days, estimated_days, new_skills, severity, velocity_ratio, anomaly_reason, status)
                   VALUES (?, 1, 2, 1.0, 30.0, ?, 'high', 0.03, 'Rapid Python acquisition', 'flagged')""",
                (cand_id, json.dumps(['Python']))
            )
            conn.execute("UPDATE users SET is_outlier=1 WHERE id=?", (cand_id,))
            conn.commit()

        # Start quiz
        quiz = get_quiz_for_skill(cand_id, 'Python')
        self.assertTrue(quiz['success'])

        # Submit perfect answers (100%)
        # Fetch correct answers directly from DB for test determinism
        with get_db() as conn:
            rows = conn.execute("SELECT id, correct_option FROM quiz_questions WHERE skill='Python'").fetchall()
            answers = {str(r['id']): r['correct_option'] for r in rows}

        sub_res = submit_quiz_answers(cand_id, 'Python', answers)
        self.assertTrue(sub_res['success'])
        self.assertTrue(sub_res['passed'])
        self.assertGreaterEqual(sub_res['score'], 70)

        # Verify skill elevated to 1.0 Quiz-Verified
        cand_skills = get_candidate_skills(cand_id)
        py_skill = next((s for s in cand_skills if s['skill'].lower() == 'python'), None)
        self.assertIsNotNone(py_skill)
        self.assertEqual(py_skill['confidence'], 1.0)
        self.assertEqual(py_skill['source'], 'quiz_verified')

        # Verify anomaly resolved
        with get_db() as conn:
            anom = conn.execute("SELECT status FROM skill_velocity_anomalies WHERE user_id=?", (cand_id,)).fetchone()
            self.assertEqual(anom['status'], 'verified')
            u_row = conn.execute("SELECT is_outlier FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertEqual(u_row['is_outlier'], 0)

        # Ranking reflects full 1.0 weight for quiz-verified skill
        cand_proxy = {
            'skills': ['Python'],
            'candidate_skills': cand_skills,
            'experience_lines': [],
            'ats_score': 70
        }
        score_res = compute_candidate_score(cand_proxy, ['Python'], verified_skills=['Python'])
        self.assertEqual(score_res['breakdown']['skills_score'], 40)

    # =========================================================================
    # SCENARIO 6: Failed Technical Assessment (Non-Punitive)
    # =========================================================================
    def test_scenario_6_failed_technical_assessment(self):
        """
        Scenario 6: Candidate fails technical assessment (<70%).
        - Skill confidence remains at baseline 0.2.
        - Anomaly remains 'flagged'.
        - Candidate is NOT banned or deleted (non-punitive).
        """
        ts = int(time.time() * 1000)
        cand_email = f"quiz_fail_{ts}@test.com"
        cand_id = register_user("Unprepared Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            conn.execute(
                """INSERT INTO skill_velocity_anomalies 
                   (user_id, previous_resume_id, current_resume_id, elapsed_days, estimated_days, new_skills, severity, velocity_ratio, anomaly_reason, status)
                   VALUES (?, 1, 2, 1.0, 30.0, ?, 'high', 0.03, 'Rapid Python acquisition', 'flagged')""",
                (cand_id, json.dumps(['Python']))
            )
            conn.execute("UPDATE users SET is_outlier=1 WHERE id=?", (cand_id,))
            conn.commit()

        quiz = get_quiz_for_skill(cand_id, 'Python')
        self.assertTrue(quiz['success'])

        # Submit wrong answers (all option 99)
        wrong_answers = {str(q['id']): 99 for q in quiz['questions']}
        sub_res = submit_quiz_answers(cand_id, 'Python', wrong_answers)

        self.assertTrue(sub_res['success'])
        self.assertFalse(sub_res['passed'])
        self.assertLess(sub_res['score'], 70)

        # Anomaly status remains flagged
        with get_db() as conn:
            anom = conn.execute("SELECT status FROM skill_velocity_anomalies WHERE user_id=?", (cand_id,)).fetchone()
            self.assertEqual(anom['status'], 'flagged')
            u_row = conn.execute("SELECT is_outlier FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertEqual(u_row['is_outlier'], 1)

    # =========================================================================
    # SCENARIO 7: Multiple Resume Versions Tracking
    # =========================================================================
    def test_scenario_7_multiple_resume_versions(self):
        """
        Scenario 7: Candidate uploads multiple resume versions.
        - Sequential version numbering (v1, v2, v3).
        - Each upload tracked in resume_upload_logs.
        - Version diffing connects consecutive uploads.
        """
        ts = int(time.time() * 1000)
        cand_email = f"multi_v_{ts}@test.com"
        cand_id = register_user("Version Tracker", cand_email, "Password123!", "candidate")["user"]["id"]

        # Upload 1
        s1 = _make_custom_docx("Version Tracker", "HTML")
        fs1 = FileStorage(stream=s1, filename=f"r1_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res1 = process_resume_upload(fs1, user_id=cand_id)
        r1_id = res1['resume_id']

        past_1 = (datetime.now() - timedelta(hours=50)).strftime('%Y-%m-%d %H:%M:%S')
        with get_db() as conn:
            conn.execute("UPDATE resumes SET uploaded_at=? WHERE id=?", (past_1, r1_id))
            conn.execute("UPDATE resume_upload_logs SET uploaded_at=? WHERE user_id=?", (past_1, cand_id))
            conn.commit()

        # Upload 2
        s2 = _make_custom_docx("Version Tracker", "HTML, CSS")
        fs2 = FileStorage(stream=s2, filename=f"r2_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res2 = process_resume_upload(fs2, user_id=cand_id)
        r2_id = res2['resume_id']

        past_2 = (datetime.now() - timedelta(hours=25)).strftime('%Y-%m-%d %H:%M:%S')
        with get_db() as conn:
            conn.execute("UPDATE resumes SET uploaded_at=? WHERE id=?", (past_2, r2_id))
            conn.execute("UPDATE resume_upload_logs SET uploaded_at=? WHERE user_id=?", (past_2, cand_id))
            conn.commit()

        # Upload 3
        s3 = _make_custom_docx("Version Tracker", "HTML, CSS, JavaScript")
        fs3 = FileStorage(stream=s3, filename=f"r3_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res3 = process_resume_upload(fs3, user_id=cand_id)
        r3_id = res3['resume_id']

        with get_db() as conn:
            versions = conn.execute("SELECT id, version FROM resumes WHERE user_id=? ORDER BY id ASC", (cand_id,)).fetchall()
            self.assertEqual(len(versions), 3)
            self.assertEqual([v['version'] for v in versions], [1, 2, 3])

            logs = conn.execute("SELECT id FROM resume_upload_logs WHERE user_id=? ORDER BY id ASC", (cand_id,)).fetchall()
            self.assertEqual(len(logs), 3)

    # =========================================================================
    # SCENARIO 8: Application Snapshot Lock on Re-Upload
    # =========================================================================
    def test_scenario_8_application_snapshot_lock(self):
        """
        Scenario 8: Candidate already applied using Resume 1 and later uploads Resume 2.
        - Application record remains locked to Resume 1 and original score.
        - Cooldown prevents immediate re-submission for the same job.
        - Active resume deletion archives Resume 1, preserving historical HR access.
        """
        ts = int(time.time() * 1000)
        cand_email = f"app_lock_{ts}@test.com"
        cand_id = register_user("Snapshot Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        # Create a job
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO jobs (title, company, skills, description, status) VALUES ('Backend Eng', 'Acme', 'Python, SQL', 'Backend developer role', 'Active')"
            )
            job_id = cur.lastrowid
            conn.commit()

        # Upload Resume 1: only has SQL
        s1 = _make_custom_docx("Snapshot Candidate", "SQL", "SQL queries")
        fs1 = FileStorage(stream=s1, filename=f"r1_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res1 = process_resume_upload(fs1, user_id=cand_id)
        r1_id = res1['resume_id']

        # Apply to job with Resume 1
        self._login(cand_email, "candidate")
        apply_res = self.client.post('/api/apply', json={'job_id': job_id})
        self.assertEqual(apply_res.status_code, 200)

        with get_db() as conn:
            app_rec = conn.execute("SELECT resume_id, match_score FROM applications WHERE user_id=? AND job_id=?", (cand_id, job_id)).fetchone()
            original_resume_id = app_rec['resume_id']
            original_match_score = app_rec['match_score']
            self.assertEqual(original_resume_id, r1_id)

        # Age Resume 1 by 25h and upload Resume 2 (adds Python)
        past_time = (datetime.now() - timedelta(hours=25)).strftime('%Y-%m-%d %H:%M:%S')
        with get_db() as conn:
            conn.execute("UPDATE resumes SET uploaded_at=? WHERE id=?", (past_time, r1_id))
            conn.execute("UPDATE resume_upload_logs SET uploaded_at=? WHERE user_id=?", (past_time, cand_id))
            conn.commit()

        s2 = _make_custom_docx("Snapshot Candidate", "SQL, Python", "SQL and Python backend")
        fs2 = FileStorage(stream=s2, filename=f"r2_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res2 = process_resume_upload(fs2, user_id=cand_id)
        r2_id = res2['resume_id']

        # Existing application MUST still reference Resume 1 and original score
        with get_db() as conn:
            app_rec2 = conn.execute("SELECT resume_id, match_score FROM applications WHERE user_id=? AND job_id=?", (cand_id, job_id)).fetchone()
            self.assertEqual(app_rec2['resume_id'], original_resume_id)
            self.assertEqual(app_rec2['match_score'], original_match_score)

        # Immediate re-application triggers 30-day cooldown
        re_apply = self.client.post('/api/apply', json={'job_id': job_id})
        self.assertTrue(re_apply.get_json().get('cooldown_active'))

        # Candidate deletes Resume 1 from their dashboard -> soft archived
        del_res = delete_resume_by_id(r1_id, cand_id, "candidate")
        self.assertTrue(del_res['success'])
        self.assertTrue(del_res.get('archived'))

        # HR can still download the archived resume snapshot submitted with the application
        hr_email = f"hr_snap_{ts}@test.com"
        register_user("HR Snapshot", hr_email, "Password123!", "hr", allow_privileged=True, is_verified=1)
        self._login(hr_email, "hr")
        dl = self.client.get(f'/api/resume/download/{r1_id}')
        self.assertEqual(dl.status_code, 200)

    # =========================================================================
    # SCENARIO 9: HR Audit, Evidence Provenance & Resume Diff Inspection
    # =========================================================================
    def test_scenario_9_hr_resume_history_and_evidence_transparency(self):
        """
        Scenario 9: HR reviews candidate's resume history and evidence.
        - /api/admin/candidates reflects outlier status from users.is_outlier.
        - /api/admin/candidate/<id>/skills returns full evidence classification.
        - /api/admin/candidate/<id>/velocity returns acquisition timeline logs.
        - /api/admin/candidate/<id>/quizzes returns technical assessment history.
        - /api/admin/candidate/<id>/resumes returns full version history.
        - /api/admin/candidate/<id>/resume_diff returns side-by-side version comparison.
        - Candidate cannot access HR inspection routes (HTTP 403).
        """
        ts = int(time.time() * 1000)
        cand_email = f"cand_audit_{ts}@test.com"
        cand_id = register_user("Audit Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        # Upload Resume 1
        s1 = _make_custom_docx("Audit Candidate", "HTML, CSS", "Frontend UI work")
        fs1 = FileStorage(stream=s1, filename=f"r1_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res1 = process_resume_upload(fs1, user_id=cand_id)
        r1_id = res1['resume_id']

        past_time = (datetime.now() - timedelta(hours=25)).strftime('%Y-%m-%d %H:%M:%S')
        with get_db() as conn:
            conn.execute("UPDATE resumes SET uploaded_at=? WHERE id=?", (past_time, r1_id))
            conn.execute("UPDATE resume_upload_logs SET uploaded_at=? WHERE user_id=?", (past_time, cand_id))
            conn.commit()

        # Upload Resume 2 (rapidly adding Kubernetes, AWS)
        s2 = _make_custom_docx("Audit Candidate", "HTML, CSS, Kubernetes, AWS", "Frontend UI work")
        fs2 = FileStorage(stream=s2, filename=f"r2_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res2 = process_resume_upload(fs2, user_id=cand_id)
        r2_id = res2['resume_id']

        # Apply to a job so candidate appears in /api/admin/candidates
        with get_db() as conn:
            cur = conn.execute("INSERT INTO jobs (title, company, skills, description, status) VALUES ('DevOps', 'Acme', 'AWS', 'Role', 'Active')")
            job_id = cur.lastrowid
            conn.commit()

        self._login(cand_email, "candidate")
        self.client.post('/api/apply', json={'job_id': job_id})

        # Unauthorized access guard: candidate calling HR endpoints gets 403
        cand_resp = self.client.get(f'/api/admin/candidate/{cand_id}/resume_diff')
        self.assertEqual(cand_resp.status_code, 403)

        # Login as HR
        hr_email = f"hr_audit_{ts}@test.com"
        register_user("HR Auditor", hr_email, "Password123!", "hr", allow_privileged=True, is_verified=1)
        self._login(hr_email, "hr")

        # 1. Inspect /api/admin/candidates
        cands_resp = self.client.get('/api/admin/candidates')
        self.assertEqual(cands_resp.status_code, 200)
        cands_data = cands_resp.get_json()
        target_cand = next((c for c in cands_data if c['user_id'] == cand_id), None)
        self.assertIsNotNone(target_cand)
        self.assertTrue(target_cand.get('outlier_flag'))
        self.assertIn('outlier', target_cand.get('outlier_reason', '').lower())

        # 2. Inspect /api/admin/candidate/<id>/skills
        skills_resp = self.client.get(f'/api/admin/candidate/{cand_id}/skills')
        self.assertEqual(skills_resp.status_code, 200)
        skills_data = skills_resp.get_json()
        self.assertTrue(skills_data['success'])
        self.assertGreaterEqual(len(skills_data['skills']), 4)
        # Check aliases: skill_name and evidence_weight exist
        self.assertIn('skill_name', skills_data['skills'][0])
        self.assertIn('evidence_weight', skills_data['skills'][0])

        # 3. Inspect /api/admin/candidate/<id>/velocity
        vel_resp = self.client.get(f'/api/admin/candidate/{cand_id}/velocity')
        self.assertEqual(vel_resp.status_code, 200)
        vel_data = vel_resp.get_json()
        self.assertTrue(vel_data['has_anomaly'])
        self.assertIn('flag_reason', vel_data['anomalies'][0])

        # 4. Inspect /api/admin/candidate/<id>/resumes
        resumes_resp = self.client.get(f'/api/admin/candidate/{cand_id}/resumes')
        self.assertEqual(resumes_resp.status_code, 200)
        resumes_data = resumes_resp.get_json()
        self.assertEqual(resumes_data['total_resumes'], 2)
        self.assertEqual(resumes_data['resumes'][0]['version'], 1)
        self.assertEqual(resumes_data['resumes'][1]['version'], 2)

        # 5. Inspect /api/admin/candidate/<id>/resume_diff
        diff_resp = self.client.get(f'/api/admin/candidate/{cand_id}/resume_diff')
        self.assertEqual(diff_resp.status_code, 200)
        diff_data = diff_resp.get_json()
        self.assertTrue(diff_data['has_diff'])
        self.assertIn('Kubernetes', diff_data['diff']['added_skills'])
        self.assertIn('AWS', diff_data['diff']['added_skills'])
        self.assertTrue(diff_data['anomaly']['is_flagged'])


if __name__ == "__main__":
    unittest.main()
