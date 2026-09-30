# ============================================================
#  HireAI / TalentSync — Phase 3 Jobs + Talent Pool Regression
#  Covers GAP-07 (External/Adzuna Application) & GAP-10 (Talent Pool)
# ============================================================

import os
import sys
import time
import json
import unittest

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.utils.validators import validate_external_apply_url


class TestPhase3JobsTalentPoolRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestingConfig)

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    # ------------------------------------------------------------
    # GAP-07: URL Validator Unit Tests (Open Redirect Protection)
    # ------------------------------------------------------------
    def test_gap07_validate_external_apply_url_valid_https(self):
        """Valid HTTPS external URLs must pass validation."""
        valid_urls = [
            "https://www.adzuna.in/land/ad/12345678",
            "https://api.adzuna.com/v1/api/jobs/in/redirect/999",
            "https://careers.google.com/jobs/results/12345",
            "https://jobs.lever.co/company/job-id",
            "https://boards.greenhouse.io/company/jobs/456"
        ]
        for url in valid_urls:
            is_valid, msg = validate_external_apply_url(url)
            self.assertTrue(is_valid, f"URL should be valid: {url}, got: {msg}")
            self.assertEqual(msg, "")

    def test_gap07_validate_external_apply_url_rejects_insecure_or_dangerous_schemes(self):
        """Insecure HTTP, javascript, data, file schemes must be rejected."""
        invalid_urls = [
            "http://insecure-adzuna.com/job",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "vbscript:msgbox(1)",
            "ftp://files.example.com/job"
        ]
        for url in invalid_urls:
            is_valid, msg = validate_external_apply_url(url)
            self.assertFalse(is_valid, f"Insecure URL should be rejected: {url}")
            self.assertTrue(len(msg) > 0)

    def test_gap07_validate_external_apply_url_rejects_localhost_and_private_ips(self):
        """Localhost and private IP redirects must be blocked to prevent SSRF."""
        ssrf_urls = [
            "https://localhost/admin",
            "https://127.0.0.1:5000/api",
            "https://192.168.1.1/router",
            "https://10.0.0.1/internal",
            "https://172.16.0.1/secret",
            "https://0.0.0.0/test"
        ]
        for url in ssrf_urls:
            is_valid, msg = validate_external_apply_url(url)
            self.assertFalse(is_valid, f"Private/Local URL should be rejected: {url}")

    def test_gap07_validate_external_apply_url_rejects_crlf_and_whitespace(self):
        """CRLF injection and whitespace must be rejected."""
        crlf_urls = [
            "https://adzuna.com/job\r\nSet-Cookie: evil=1",
            "https://adzuna.com/job\n",
            "https://adzuna .com/job"
        ]
        for url in crlf_urls:
            is_valid, _ = validate_external_apply_url(url)
            self.assertFalse(is_valid)

    # ------------------------------------------------------------
    # GAP-07: Job Application API (Internal vs External)
    # ------------------------------------------------------------
    def test_gap07_internal_job_application_success(self):
        """Authenticated candidate applying to valid local job creates application."""
        cand_email = f"cand_int_{int(time.time()*1000)}@test.com"
        cand_id = register_user("Internal Applicant", cand_email, "ValidPassword10!", "candidate")["user"]["id"]

        with get_db() as conn:
            job = conn.execute("SELECT id FROM jobs WHERE status='Active' LIMIT 1").fetchone()
            if not job:
                conn.execute("INSERT INTO jobs (title, company, status) VALUES ('DevOps Engineer', 'CloudCorp', 'Active')")
                conn.commit()
                job = conn.execute("SELECT id FROM jobs WHERE status='Active' LIMIT 1").fetchone()
            job_id = job["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        res = self.client.post("/api/apply", json={"job_id": job_id, "match_score": 88})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("type"), "internal")

        # Verify application row exists in DB
        with get_db() as conn:
            app_row = conn.execute("SELECT * FROM applications WHERE user_id=? AND job_id=?", (cand_id, job_id)).fetchone()
            self.assertIsNotNone(app_row)
            self.assertEqual(app_row["match_score"], 88)

    def test_gap07_internal_job_duplicate_application_prevented(self):
        """Applying twice to the same internal job returns already applied message."""
        cand_email = f"cand_dup_{int(time.time()*1000)}@test.com"
        cand_id = register_user("Dup Applicant", cand_email, "ValidPassword10!", "candidate")["user"]["id"]

        with get_db() as conn:
            job_id = conn.execute("SELECT id FROM jobs LIMIT 1").fetchone()["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        res1 = self.client.post("/api/apply", json={"job_id": job_id, "match_score": 75})
        self.assertTrue(res1.get_json().get("success"))

        res2 = self.client.post("/api/apply", json={"job_id": job_id, "match_score": 75})
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertFalse(data2.get("success"))
        self.assertIn("Already applied", data2.get("message", ""))

    def test_gap07_internal_job_nonexistent_returns_404(self):
        """Applying to an integer job_id that does not exist returns HTTP 404."""
        cand_email = f"cand_404_{int(time.time()*1000)}@test.com"
        cand_id = register_user("Missing Job Applicant", cand_email, "ValidPassword10!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        res = self.client.post("/api/apply", json={"job_id": 999999999, "is_external": False})
        self.assertEqual(res.status_code, 404)
        self.assertIn("Job not found", res.get_json().get("message", ""))

    def test_gap07_external_job_application_returns_redirect_and_no_404(self):
        """External job application does not query local jobs table and returns external_redirected."""
        cand_email = f"cand_ext_{int(time.time()*1000)}@test.com"
        cand_id = register_user("External Applicant", cand_email, "ValidPassword10!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        adzuna_id = "adzuna_live_4567890123"
        valid_external_url = "https://www.adzuna.in/land/ad/4567890123"

        res = self.client.post("/api/apply", json={
            "job_id": adzuna_id,
            "is_external": True,
            "apply_url": valid_external_url,
            "title": "Senior Python Architect",
            "company": "Adzuna Global Partners"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("type"), "external")
        self.assertEqual(data.get("status"), "external_redirected")
        self.assertEqual(data.get("redirect_url"), valid_external_url)
        self.assertIn("Redirecting", data.get("message", ""))

    def test_gap07_external_job_missing_apply_url_rejected(self):
        """External job missing apply_url fails safely with HTTP 400."""
        cand_email = f"cand_ext_nourl_{int(time.time()*1000)}@test.com"
        cand_id = register_user("No URL Cand", cand_email, "ValidPassword10!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        res = self.client.post("/api/apply", json={
            "job_id": "adzuna_999",
            "is_external": True,
            "apply_url": ""
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("external application url", res.get_json().get("message", "").lower())

    def test_gap07_external_job_invalid_url_rejected(self):
        """External job with unsafe URL (javascript or http) returns HTTP 400."""
        cand_email = f"cand_ext_bad_{int(time.time()*1000)}@test.com"
        cand_id = register_user("Bad URL Cand", cand_email, "ValidPassword10!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        res = self.client.post("/api/apply", json={
            "job_id": "adzuna_malicious",
            "is_external": True,
            "apply_url": "javascript:stealCookies()"
        })
        self.assertEqual(res.status_code, 400)

    def test_gap07_unauthenticated_application_rejected(self):
        """Unauthenticated candidate applying to any job returns HTTP 401."""
        res = self.client.post("/api/apply", json={"job_id": 1})
        self.assertEqual(res.status_code, 401)

    # ------------------------------------------------------------
    # GAP-10: Talent Pool API & Recruiter Discovery
    # ------------------------------------------------------------
    def test_gap10_recruiter_can_retrieve_talent_pool(self):
        """Recruiter (role=hr) successfully accesses /api/admin/talent_pool."""
        hr_email = f"hr_tp_{int(time.time()*1000)}@test.com"
        hr_id = register_user("HR Talent Manager", hr_email, "ValidPassword10!", "hr", allow_privileged=True, is_verified=1)["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = hr_id
            sess["role"] = "hr"

        res = self.client.get("/api/admin/talent_pool")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("candidates", data)
        self.assertIn("total", data)
        self.assertIsInstance(data["candidates"], list)

    def test_gap10_candidate_access_to_talent_pool_denied(self):
        """Candidate (role=candidate) accessing talent pool receives 403 Forbidden."""
        cand_email = f"cand_denied_{int(time.time()*1000)}@test.com"
        cand_id = register_user("Sneaky Cand", cand_email, "ValidPassword10!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        res = self.client.get("/api/admin/talent_pool")
        self.assertEqual(res.status_code, 403)

    def test_gap10_anonymous_access_to_talent_pool_denied(self):
        """Unauthenticated user accessing talent pool receives 401 Unauthorized."""
        res = self.client.get("/api/admin/talent_pool")
        self.assertEqual(res.status_code, 401)

    def test_gap10_candidate_with_zero_applications_appears_in_talent_pool(self):
        """A registered candidate with 0 applications is discoverable in Talent Pool."""
        hr_email = f"hr_test_{int(time.time()*1000)}@test.com"
        hr_id = register_user("HR Tester", hr_email, "ValidPassword10!", "hr", allow_privileged=True, is_verified=1)["user"]["id"]

        zero_app_email = f"zero_app_{int(time.time()*1000)}@test.com"
        zero_app_id = register_user("Zero Applications Candidate", zero_app_email, "ValidPassword10!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = hr_id
            sess["role"] = "hr"

        res = self.client.get(f"/api/admin/talent_pool?q={zero_app_email}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        candidates = data.get("candidates", [])

        found = next((c for c in candidates if c["candidate_id"] == zero_app_id), None)
        self.assertIsNotNone(found, "Candidate with 0 applications must appear in talent pool.")
        self.assertEqual(found["application_count"], 0)
        self.assertEqual(found["email"], zero_app_email)

    def test_gap10_candidate_with_multiple_applications_appears_once(self):
        """A candidate who applied to multiple jobs appears exactly ONCE in talent pool."""
        hr_email = f"hr_once_{int(time.time()*1000)}@test.com"
        hr_id = register_user("HR Inspector", hr_email, "ValidPassword10!", "hr", allow_privileged=True, is_verified=1)["user"]["id"]

        multi_app_email = f"multi_app_{int(time.time()*1000)}@test.com"
        multi_id = register_user("Multi Applicant", multi_app_email, "ValidPassword10!", "candidate")["user"]["id"]

        with get_db() as conn:
            jobs = conn.execute("SELECT id FROM jobs LIMIT 2").fetchall()
            if len(jobs) < 2:
                conn.execute("INSERT INTO jobs (title, company) VALUES ('Job 1', 'Co 1')")
                conn.execute("INSERT INTO jobs (title, company) VALUES ('Job 2', 'Co 2')")
                conn.commit()
                jobs = conn.execute("SELECT id FROM jobs LIMIT 2").fetchall()

            conn.execute("INSERT OR IGNORE INTO applications (user_id, job_id, match_score) VALUES (?, ?, 80)", (multi_id, jobs[0]["id"]))
            conn.execute("INSERT OR IGNORE INTO applications (user_id, job_id, match_score) VALUES (?, ?, 85)", (multi_id, jobs[1]["id"]))
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = hr_id
            sess["role"] = "hr"

        res = self.client.get(f"/api/admin/talent_pool?q={multi_app_email}")
        self.assertEqual(res.status_code, 200)
        candidates = res.get_json().get("candidates", [])
        matches = [c for c in candidates if c["candidate_id"] == multi_id]
        self.assertEqual(len(matches), 1, "Candidate must appear exactly once in talent pool regardless of application count.")
        self.assertGreaterEqual(matches[0]["application_count"], 2)

    def test_gap10_sensitive_fields_not_exposed(self):
        """Talent pool endpoint must NOT expose password hashes or auth tokens."""
        hr_email = f"hr_sec_{int(time.time()*1000)}@test.com"
        hr_id = register_user("HR Security", hr_email, "ValidPassword10!", "hr", allow_privileged=True, is_verified=1)["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = hr_id
            sess["role"] = "hr"

        res = self.client.get("/api/admin/talent_pool?limit=10")
        self.assertEqual(res.status_code, 200)
        candidates = res.get_json().get("candidates", [])
        self.assertGreater(len(candidates), 0)

        for c in candidates:
            self.assertNotIn("password", c)
            self.assertNotIn("password_hash", c)
            self.assertNotIn("token", c)
            self.assertNotIn("reset_token", c)
            self.assertNotIn("verification_token", c)


if __name__ == "__main__":
    unittest.main()
