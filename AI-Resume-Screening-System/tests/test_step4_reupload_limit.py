import os
import io
import time
import unittest
import concurrent.futures
from datetime import datetime, timedelta
import docx as python_docx
from werkzeug.datastructures import FileStorage

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.controllers.resume_controller import (
    process_resume_upload,
    check_upload_rate_limit,
    delete_resume_by_id
)
from app.ml.ranking.ranking_engine import compute_candidate_score, rank_candidates


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


def _process_worker_upload_task(args):
    cand_id, i, ts, db_file = args
    from app import create_app
    from app.config.settings import TestingConfig
    from werkzeug.datastructures import FileStorage
    import docx
    import io

    class WorkerConfig(TestingConfig):
        DB_FILE = db_file

    app = create_app(WorkerConfig)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = cand_id
        sess["role"] = "candidate"

    doc = docx.Document()
    doc.add_heading(f"Process Worker {i}", 0)
    doc.add_paragraph(f"Python, MultiProcess{i}")
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)

    fs = FileStorage(stream=bio, filename=f"proc_{i}_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    res = client.post("/api/upload_resume", data={"resume": fs}, content_type="multipart/form-data")
    return res.status_code


class TestStep4ReuploadRateLimit(unittest.TestCase):
    """
    Test Step 4: Re-Upload Rate Limiting & Velocity Decoupling.
    Verifies that:
    1. A candidate can upload up to 3 resumes in a rolling 24-hour period.
    2. A 4th upload attempt within 24 hours is rejected with HTTP 429 Too Many Requests.
    3. Deleting an active resume does NOT reset or bypass the 24-hour rate limit.
    4. Re-uploading is permitted once the 24-hour window has elapsed.
    5. Re-submitting an identical duplicate resume does not consume a rate limit slot.
    6. Candidate ranking algorithms do not reward upload recency or fresh uploads.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_user_can_upload_up_to_3_resumes_in_24h(self):
        """User can upload up to 3 distinct resumes within 24 hours."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_rate3_{ts}@test.com"
        cand_id = register_user("Rate Limit Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        for i in range(1, 4):
            stream = _make_resume_docx(f"Candidate {i}", f"Python, Django, Skill{i}", f"Developer {i}")
            fs = FileStorage(
                stream=stream,
                filename=f"resume_v{i}_{ts}.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            res = self.client.post("/api/upload_resume", data={"resume": fs}, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200, f"Upload {i} failed unexpectedly: {res.get_json()}")
            data = res.get_json()
            self.assertTrue(data.get("success"))

        # Verify exactly 3 upload log entries recorded
        with get_db() as conn:
            log_count = conn.execute("SELECT COUNT(*) FROM resume_upload_logs WHERE user_id=?", (cand_id,)).fetchone()[0]
            self.assertEqual(log_count, 3)

    def test_fourth_upload_in_24h_is_blocked_with_429(self):
        """A 4th resume upload in 24 hours is blocked with HTTP 429 Too Many Requests."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_fourth_{ts}@test.com"
        cand_id = register_user("Fourth Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        # Upload 3 resumes
        for i in range(1, 4):
            stream = _make_resume_docx(f"Candidate {i}", f"Python, Skill{i}", f"Engineer {i}")
            fs = FileStorage(
                stream=stream,
                filename=f"resume_{i}_{ts}.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            res = self.client.post("/api/upload_resume", data={"resume": fs}, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200)

        # 4th upload attempt
        stream4 = _make_resume_docx("Candidate 4", "Python, Skill4", "Engineer 4")
        fs4 = FileStorage(
            stream=stream4,
            filename=f"resume_4_{ts}.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        res4 = self.client.post("/api/upload_resume", data={"resume": fs4}, content_type="multipart/form-data")
        self.assertEqual(res4.status_code, 429, f"Expected 429 Too Many Requests, got {res4.status_code}")
        data4 = res4.get_json()
        self.assertFalse(data4.get("success"))
        self.assertTrue(data4.get("rate_limited"))
        self.assertEqual(data4.get("uploads_in_24h"), 3)
        self.assertEqual(data4.get("max_allowed"), 3)
        self.assertIn("Upload limit reached", data4.get("message"))

        # Verify active resumes in database remain at 3 (the 4th was rejected before DB save)
        with get_db() as conn:
            resume_count = conn.execute("SELECT COUNT(*) FROM resumes WHERE user_id=?", (cand_id,)).fetchone()[0]
            self.assertEqual(resume_count, 3)

    def test_deleting_resumes_does_not_reset_24h_upload_limit(self):
        """Deleting an active resume does NOT bypass the 24-hour rate limit."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_del_evade_{ts}@test.com"
        cand_id = register_user("Delete Evader", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        uploaded_ids = []
        for i in range(1, 4):
            stream = _make_resume_docx(f"Candidate {i}", f"React, JavaScript, Node{i}", f"Frontend {i}")
            fs = FileStorage(
                stream=stream,
                filename=f"resume_del_{i}_{ts}.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            res = self.client.post("/api/upload_resume", data={"resume": fs}, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200)
            uploaded_ids.append(res.get_json()["resume_id"])

        # Candidate deletes one of their active resumes
        del_res = delete_resume_by_id(uploaded_ids[0], current_user_id=cand_id, current_user_role="candidate")
        self.assertTrue(del_res.get("success"))

        # Active resumes count is now 2
        with get_db() as conn:
            active_count = conn.execute("SELECT COUNT(*) FROM resumes WHERE user_id=?", (cand_id,)).fetchone()[0]
            self.assertEqual(active_count, 2)

        # Attempt to upload a 4th resume — MUST STILL BE BLOCKED!
        stream_new = _make_resume_docx("Candidate 4", "React, Node, TypeScript", "Fullstack")
        fs_new = FileStorage(
            stream=stream_new,
            filename=f"resume_attempt4_{ts}.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        res_new = self.client.post("/api/upload_resume", data={"resume": fs_new}, content_type="multipart/form-data")
        self.assertEqual(res_new.status_code, 429, "Security Failure: Deleting a resume allowed bypassing 24h upload limit!")
        data_new = res_new.get_json()
        self.assertTrue(data_new.get("rate_limited"))

    def test_upload_allowed_after_24h_window_elapses(self):
        """Once the 24-hour window has elapsed, the user can upload resumes again."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_after24_{ts}@test.com"
        cand_id = register_user("Reset Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        # Create 3 uploads
        for i in range(1, 4):
            stream = _make_resume_docx(f"Candidate {i}", f"Java, Spring, Skill{i}", f"Java Dev {i}")
            fs = FileStorage(
                stream=stream,
                filename=f"resume_reset_{i}_{ts}.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            self.client.post("/api/upload_resume", data={"resume": fs}, content_type="multipart/form-data")

        # Age the upload logs to 25 hours ago
        past_time = (datetime.now() - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")
        with get_db() as conn:
            conn.execute("UPDATE resume_upload_logs SET uploaded_at=? WHERE user_id=?", (past_time, cand_id))
            conn.execute("UPDATE resumes SET uploaded_at=? WHERE user_id=?", (past_time, cand_id))
            conn.commit()

        # Upload again now that > 24 hours have passed
        stream_fresh = _make_resume_docx("Candidate Fresh", "Java, Kubernetes", "Cloud Java Dev")
        fs_fresh = FileStorage(
            stream=stream_fresh,
            filename=f"resume_fresh_{ts}.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        res_fresh = self.client.post("/api/upload_resume", data={"resume": fs_fresh}, content_type="multipart/form-data")
        self.assertEqual(res_fresh.status_code, 200)
        self.assertTrue(res_fresh.get_json().get("success"))

    def test_duplicate_resume_upload_does_not_consume_rate_limit_slot(self):
        """Re-uploading the exact same resume file syncs profile without consuming a new rate limit slot."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_dup_{ts}@test.com"
        cand_id = register_user("Dup Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        doc_bytes = _make_resume_docx("Duplicate Candidate", "Python, Flask, SQLite", "Backend Engineer").getvalue()

        # Initial upload
        fs1 = FileStorage(stream=io.BytesIO(doc_bytes), filename="master_resume.docx")
        res1 = self.client.post("/api/upload_resume", data={"resume": fs1}, content_type="multipart/form-data")
        self.assertEqual(res1.status_code, 200)

        # Re-upload exact same file
        fs2 = FileStorage(stream=io.BytesIO(doc_bytes), filename="master_resume.docx")
        res2 = self.client.post("/api/upload_resume", data={"resume": fs2}, content_type="multipart/form-data")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2.get("is_duplicate"))

        # Verify only 1 upload slot was logged
        with get_db() as conn:
            log_count = conn.execute("SELECT COUNT(*) FROM resume_upload_logs WHERE user_id=?", (cand_id,)).fetchone()[0]
            self.assertEqual(log_count, 1)

    def test_ranking_velocity_decoupling_no_recency_bias(self):
        """Ensure ranking algorithms do not reward upload recency or penalize older uploads."""
        job_skills = ["Python", "Flask", "PostgreSQL", "Docker"]

        cand_old = {
            "skills": "Python, Flask, PostgreSQL, Docker",
            "ats_score": 85,
            "experience_lines": ["Role 1", "Role 2", "Role 3", "Role 4", "Role 5"],
            "education": "Bachelor of Technology",
            "uploaded_at": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d %H:%M:%S")
        }

        cand_fresh = {
            "skills": "Python, Flask, PostgreSQL, Docker",
            "ats_score": 85,
            "experience_lines": ["Role 1", "Role 2", "Role 3", "Role 4", "Role 5"],
            "education": "Bachelor of Technology",
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        score_old = compute_candidate_score(cand_old, job_skills)
        score_fresh = compute_candidate_score(cand_fresh, job_skills)

        # Both candidates must receive the EXACT same score regardless of upload date
        self.assertEqual(score_old["total_score"], score_fresh["total_score"])
        self.assertEqual(score_old["skills_score"], score_fresh["skills_score"])

        # Candidate rank order does not elevate fresh over old
        ranked = rank_candidates([cand_old, cand_fresh], job_skills)
        self.assertEqual(ranked[0]["rank_score"], ranked[1]["rank_score"])

    def test_multiple_api_routes_enforce_same_limit(self):
        """Test D: Multiple API routes (/api/upload_resume, /api/resume/upload, /api/resumes/upload) share the same quota."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_routes_{ts}@test.com"
        cand_id = register_user("Route Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        routes = ["/api/upload_resume", "/api/resume/upload", "/api/resumes/upload"]
        for idx, route in enumerate(routes, start=1):
            stream = _make_resume_docx(f"Candidate {idx}", f"Skill {idx}", "Engineer")
            fs = FileStorage(stream=stream, filename=f"res_{idx}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            res = self.client.post(route, data={"resume": fs}, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200, f"Route {route} failed: {res.get_json()}")

        # 4th upload via any route must be blocked
        stream4 = _make_resume_docx("Candidate 4", "Skill 4", "Engineer")
        fs4 = FileStorage(stream=stream4, filename="res_4.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res4 = self.client.post("/api/resume/upload", data={"resume": fs4}, content_type="multipart/form-data")
        self.assertEqual(res4.status_code, 429)

    def test_multiple_sessions_same_candidate(self):
        """Test E: Quota applies to candidate account across multiple simultaneous sessions."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_sess_{ts}@test.com"
        cand_id = register_user("Session Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        # Session 1 uploads 2 resumes
        client1 = self.app.test_client()
        with client1.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        for i in (1, 2):
            stream = _make_resume_docx(f"Candidate {i}", f"Skill {i}", "Engineer")
            fs = FileStorage(stream=stream, filename=f"s1_res_{i}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            res = client1.post("/api/upload_resume", data={"resume": fs}, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200)

        # Session 2 uploads 1 resume
        client2 = self.app.test_client()
        with client2.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        stream3 = _make_resume_docx("Candidate 3", "Skill 3", "Engineer")
        fs3 = FileStorage(stream=stream3, filename="s2_res_3.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res3 = client2.post("/api/upload_resume", data={"resume": fs3}, content_type="multipart/form-data")
        self.assertEqual(res3.status_code, 200)

        # 4th upload from Session 2 must be blocked
        stream4 = _make_resume_docx("Candidate 4", "Skill 4", "Engineer")
        fs4 = FileStorage(stream=stream4, filename="s2_res_4.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res4 = client2.post("/api/upload_resume", data={"resume": fs4}, content_type="multipart/form-data")
        self.assertEqual(res4.status_code, 429)

    def test_different_candidates_have_independent_quotas(self):
        """Test F: Candidate A reaching the limit does NOT block Candidate B."""
        ts = int(time.time() * 1000)
        cand_a_id = register_user("User A", f"cand_a_{ts}@test.com", "Password123!", "candidate")["user"]["id"]
        cand_b_id = register_user("User B", f"cand_b_{ts}@test.com", "Password123!", "candidate")["user"]["id"]

        # Candidate A uses all 3 uploads
        client_a = self.app.test_client()
        with client_a.session_transaction() as sess:
            sess["user_id"] = cand_a_id
            sess["role"] = "candidate"

        for i in range(1, 4):
            s = _make_resume_docx(f"A {i}", f"Skill {i}", "Dev")
            f = FileStorage(stream=s, filename=f"a_{i}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            self.assertEqual(client_a.post("/api/upload_resume", data={"resume": f}, content_type="multipart/form-data").status_code, 200)

        # 4th for A is blocked
        s4 = _make_resume_docx("A 4", "Skill 4", "Dev")
        f4 = FileStorage(stream=s4, filename="a_4.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.assertEqual(client_a.post("/api/upload_resume", data={"resume": f4}, content_type="multipart/form-data").status_code, 429)

        # Candidate B must be allowed to upload
        client_b = self.app.test_client()
        with client_b.session_transaction() as sess:
            sess["user_id"] = cand_b_id
            sess["role"] = "candidate"

        s_b = _make_resume_docx("B 1", "Python", "Dev")
        f_b = FileStorage(stream=s_b, filename="b_1.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res_b = client_b.post("/api/upload_resume", data={"resume": f_b}, content_type="multipart/form-data")
        self.assertEqual(res_b.status_code, 200)

    def test_concurrent_upload_requests_race_condition_protection(self):
        """Test G: Concurrent upload requests cannot bypass the 3-upload limit via race conditions."""
        import concurrent.futures
        ts = int(time.time() * 1000)
        cand_id = register_user("Race Cand", f"race_{ts}@test.com", "Password123!", "candidate")["user"]["id"]

        def do_upload(i):
            client = self.app.test_client()
            with client.session_transaction() as sess:
                sess["user_id"] = cand_id
                sess["role"] = "candidate"
            stream = _make_resume_docx(f"Race {i}", f"Python, Skill{i}", f"Role {i}")
            fs = FileStorage(stream=stream, filename=f"race_{i}_{ts}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            res = client.post("/api/upload_resume", data={"resume": fs}, content_type="multipart/form-data")
            return res.status_code

        # Fire 6 concurrent upload attempts simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            status_codes = list(executor.map(do_upload, range(1, 7)))

        success_count = status_codes.count(200)
        blocked_count = status_codes.count(429)

        self.assertEqual(success_count, 3, f"Expected exactly 3 uploads to succeed under concurrency, got {success_count}. Statuses: {status_codes}")
        self.assertEqual(blocked_count, 3, f"Expected 3 uploads to be rejected with 429, got {blocked_count}. Statuses: {status_codes}")

        with get_db() as conn:
            actual_resumes = conn.execute("SELECT COUNT(*) FROM resumes WHERE user_id=?", (cand_id,)).fetchone()[0]
            actual_logs = conn.execute("SELECT COUNT(*) FROM resume_upload_logs WHERE user_id=?", (cand_id,)).fetchone()[0]
            self.assertEqual(actual_resumes, 3)
            self.assertEqual(actual_logs, 3)

    def test_multiprocess_concurrent_uploads(self):
        """Test G2: Concurrent uploads from independent OS worker processes cannot bypass 3-upload limit."""
        ts = int(time.time() * 1000)
        cand_id = register_user("Process Race Cand", f"proc_race_{ts}@test.com", "Password123!", "candidate", is_verified=1)["user"]["id"]
        from flask import current_app
        db_file = current_app.config.get("DB_FILE")

        # Submit 6 concurrent upload attempts across independent OS worker processes
        args = [(cand_id, i, ts, db_file) for i in range(1, 7)]
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            status_codes = list(executor.map(_process_worker_upload_task, args))

        success_count = status_codes.count(200)
        blocked_count = status_codes.count(429)

        self.assertEqual(success_count, 3, f"Expected exactly 3 uploads to succeed across worker processes, got {success_count}. Statuses: {status_codes}")
        self.assertEqual(blocked_count, 3, f"Expected 3 uploads to be rejected with 429 across worker processes, got {blocked_count}. Statuses: {status_codes}")

        with get_db() as conn:
            actual_resumes = conn.execute("SELECT COUNT(*) FROM resumes WHERE user_id=?", (cand_id,)).fetchone()[0]
            actual_logs = conn.execute("SELECT COUNT(*) FROM resume_upload_logs WHERE user_id=?", (cand_id,)).fetchone()[0]
            self.assertEqual(actual_resumes, 3)
            self.assertEqual(actual_logs, 3)

    def test_failed_uploads_do_not_consume_rate_limit_quota(self):
        """Test H: Invalid file types, empty files, or parser failures do not penalize upload quota."""
        ts = int(time.time() * 1000)
        cand_id = register_user("Failed Upload Cand", f"fail_up_{ts}@test.com", "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        # Attempt 1: Invalid file extension (.exe)
        bad_fs = FileStorage(stream=io.BytesIO(b"malicious executable"), filename="resume.exe", content_type="application/x-msdownload")
        res1 = self.client.post("/api/upload_resume", data={"resume": bad_fs}, content_type="multipart/form-data")
        self.assertEqual(res1.status_code, 400)

        # Attempt 2: Empty file
        empty_fs = FileStorage(stream=io.BytesIO(b""), filename="empty.pdf", content_type="application/pdf")
        res2 = self.client.post("/api/upload_resume", data={"resume": empty_fs}, content_type="multipart/form-data")
        self.assertEqual(res2.status_code, 400)

        # Verify 0 quota consumed
        with get_db() as conn:
            logs = conn.execute("SELECT COUNT(*) FROM resume_upload_logs WHERE user_id=?", (cand_id,)).fetchone()[0]
            self.assertEqual(logs, 0)

        # Now upload 3 valid resumes - all 3 must succeed without being penalized
        for i in range(1, 4):
            s = _make_resume_docx(f"Cand {i}", f"Python, Skill{i}", "Engineer")
            f = FileStorage(stream=s, filename=f"valid_{i}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            res = self.client.post("/api/upload_resume", data={"resume": f}, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200)

    def test_database_persistence_across_app_restart(self):
        """Test I: Rate limit persists across Flask application restarts via persistent storage."""
        ts = int(time.time() * 1000)
        cand_id = register_user("Persist Cand", f"persist_{ts}@test.com", "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        # Upload 3 resumes
        for i in range(1, 4):
            s = _make_resume_docx(f"P {i}", f"Skill{i}", "Engineer")
            f = FileStorage(stream=s, filename=f"persist_{i}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            self.assertEqual(self.client.post("/api/upload_resume", data={"resume": f}, content_type="multipart/form-data").status_code, 200)

        # Simulate application restart: tear down context and spin up a fresh client
        self.app_context.pop()
        new_app = create_app(TestingConfig)
        self.app_context = new_app.app_context()
        self.app_context.push()
        fresh_client = new_app.test_client()

        with fresh_client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        # 4th upload after restart must still be rejected with 429
        s4 = _make_resume_docx("P 4", "Skill4", "Engineer")
        f4 = FileStorage(stream=s4, filename="persist_4.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res4 = fresh_client.post("/api/upload_resume", data={"resume": f4}, content_type="multipart/form-data")
        self.assertEqual(res4.status_code, 429)

    def test_audit_log_integrity_and_immutability(self):
        """Test J: Audit log records file hash, timestamp, and survives resume deletion."""
        ts = int(time.time() * 1000)
        cand_id = register_user("Audit Cand", f"audit_{ts}@test.com", "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        s = _make_resume_docx("Audit", "Python, AWS", "DevOps")
        f = FileStorage(stream=s, filename="audit.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res = self.client.post("/api/upload_resume", data={"resume": f}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        resume_id = res.get_json()["resume_id"]

        with get_db() as conn:
            log_row = conn.execute("SELECT * FROM resume_upload_logs WHERE user_id=?", (cand_id,)).fetchone()
            self.assertIsNotNone(log_row)
            self.assertEqual(log_row["user_id"], cand_id)
            self.assertTrue(len(log_row["file_hash"]) >= 16)
            self.assertIsNotNone(log_row["uploaded_at"])

        # Delete resume
        del_res = delete_resume_by_id(resume_id, current_user_id=cand_id, current_user_role="candidate")
        self.assertTrue(del_res["success"])

        # Verify audit log remains completely intact
        with get_db() as conn:
            res_row = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
            self.assertIsNone(res_row, "Resume was not deleted from resumes table!")
            log_count = conn.execute("SELECT COUNT(*) FROM resume_upload_logs WHERE user_id=?", (cand_id,)).fetchone()[0]
            self.assertEqual(log_count, 1, "Audit log was deleted when resume was deleted!")


if __name__ == "__main__":
    unittest.main()

