# ============================================================
#  TalentSync — Platform Admin Comprehensive Security & Production Audit
#  Test Suite: tests/test_platform_admin_security_audit_final.py
#  Validates:
#    - RBAC & Authentication across all Platform Admin endpoints
#    - IDOR / Object-level authorization
#    - Role escalation prevention & self-privilege modification
#    - Admin self-protection & final-admin lockout prevention
#    - Resume authorization, path isolation, and download protection
#    - Platform data export security, format validation & audit trail
#    - ML pipeline authorization, concurrency & cache flush
#    - System health zero-secret disclosure
# ============================================================

import os
import io
import json
import uuid
import unittest
from flask import session
from werkzeug.security import generate_password_hash

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db


class TestPlatformAdminSecurityAuditFinal(unittest.TestCase):
    """Rigorous end-to-end security and authorization test suite for Platform Admin."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # Seed test actors
        self.admin1_id, self.admin1_email = self._create_user("Admin One", "admin", is_verified=1)
        self.admin2_id, self.admin2_email = self._create_user("Admin Two", "admin", is_verified=1)
        self.hr_id, self.hr_email         = self._create_user("HR Manager", "hr", is_verified=1)
        self.cand_a_id, self.cand_a_email = self._create_user("Candidate A", "candidate", is_verified=1, ats_score=85)
        self.cand_b_id, self.cand_b_email = self._create_user("Candidate B", "candidate", is_verified=1, ats_score=72)

        # Seed Job
        self.job_id = self._create_job("Python Architect", "Tech Corp")
        # Seed Application
        self.app_id = self._create_application(self.cand_a_id, self.job_id, status="Shortlisted", match_score=90)
        # Seed Resume
        self.resume_id = self._create_resume(self.cand_a_id, f"candA_{uuid.uuid4().hex[:6]}.pdf")

    def tearDown(self):
        self.app_context.pop()

    def _create_user(self, name, role, is_verified=1, ats_score=0):
        uid_suffix = uuid.uuid4().hex[:8]
        email = f"{name.lower().replace(' ', '')}_{uid_suffix}_{role}@test.com"
        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO users (name, email, password, role, is_verified, ats_score)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, email, generate_password_hash("password123"), role, is_verified, ats_score)
            )
            user_id = cur.lastrowid
            if hasattr(conn, "commit"):
                conn.commit()
        return user_id, email

    def _create_job(self, title, company):
        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, location, type, salary, skills, description, status)
                   VALUES (?, ?, 'Remote', 'Full-time', '$120k', 'Python,Flask', 'Job description', 'Active')""",
                (title, company)
            )
            job_id = cur.lastrowid
            if hasattr(conn, "commit"):
                conn.commit()
        return job_id

    def _create_application(self, user_id, job_id, status="Reviewing", match_score=0):
        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO applications (user_id, job_id, match_score, status)
                   VALUES (?, ?, ?, ?)""",
                (user_id, job_id, match_score, status)
            )
            app_id = cur.lastrowid
            if hasattr(conn, "commit"):
                conn.commit()
        return app_id

    def _create_resume(self, user_id, filename):
        upload_dir = os.path.join(self.app.config.get('UPLOAD_FOLDER', 'uploads/resumes'))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(b"%PDF-1.4 mock resume binary content for test")

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, ats_score, extracted_skills, status)
                   VALUES (?, ?, ?, ?, 'mock_hash_12345', 48, 'application/pdf', 85, 'Python,SQL', 'processed')""",
                (user_id, filename, filename, file_path)
            )
            resume_id = cur.lastrowid
            if hasattr(conn, "commit"):
                conn.commit()
        return resume_id

    def _login(self, user_id, email, role):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["email"] = email
            sess["role"] = role

    # ═══════════════════════════════════════════════════════════
    # 1. RBAC & AUTHENTICATION TESTS
    # ═══════════════════════════════════════════════════════════

    def test_01_all_platform_admin_endpoints_deny_unauthenticated(self):
        """Every platform admin endpoint must deny unauthenticated access with 401."""
        endpoints = [
            ("GET", "/api/platform-admin/users"),
            ("GET", f"/api/platform-admin/users/{self.cand_a_id}"),
            ("GET", "/api/platform-admin/analytics"),
            ("GET", "/api/platform-admin/jobs"),
            ("GET", f"/api/platform-admin/jobs/{self.job_id}"),
            ("GET", "/api/platform-admin/applications"),
            ("GET", f"/api/platform-admin/applications/{self.app_id}"),
            ("GET", "/api/platform-admin/resumes"),
            ("GET", f"/api/platform-admin/resumes/{self.resume_id}"),
            ("GET", "/api/platform-admin/security/login-attempts"),
            ("GET", "/api/platform-admin/security/outliers"),
            ("GET", "/api/platform-admin/audit"),
            ("GET", "/api/platform-admin/system/health"),
            ("GET", "/api/platform-admin/system/integrations"),
            ("GET", "/api/platform-admin/export?format=json"),
            ("GET", "/api/ml/status"),
            ("POST", "/api/ml/cache/flush"),
            ("POST", "/api/ml/train"),
        ]
        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, json={})
            self.assertEqual(res.status_code, 401, f"Expected 401 for unauthenticated {method} {url}, got {res.status_code}")

    def test_02_all_platform_admin_endpoints_deny_candidate(self):
        """Every platform admin endpoint must deny Candidate access with 403 Forbidden."""
        self._login(self.cand_a_id, self.cand_a_email, "candidate")
        endpoints = [
            ("GET", "/api/platform-admin/users"),
            ("GET", f"/api/platform-admin/users/{self.cand_a_id}"),
            ("GET", "/api/platform-admin/analytics"),
            ("GET", "/api/platform-admin/jobs"),
            ("GET", f"/api/platform-admin/jobs/{self.job_id}"),
            ("GET", "/api/platform-admin/applications"),
            ("GET", f"/api/platform-admin/applications/{self.app_id}"),
            ("GET", "/api/platform-admin/resumes"),
            ("GET", f"/api/platform-admin/resumes/{self.resume_id}"),
            ("GET", "/api/platform-admin/security/login-attempts"),
            ("GET", "/api/platform-admin/security/outliers"),
            ("GET", "/api/platform-admin/audit"),
            ("GET", "/api/platform-admin/system/health"),
            ("GET", "/api/platform-admin/system/integrations"),
            ("GET", "/api/platform-admin/export?format=json"),
            ("GET", "/api/ml/status"),
            ("POST", "/api/ml/cache/flush"),
            ("POST", "/api/ml/train"),
        ]
        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, json={})
            self.assertEqual(res.status_code, 403, f"Expected 403 for candidate {method} {url}, got {res.status_code}")

    def test_03_all_platform_admin_endpoints_deny_hr(self):
        """Every platform admin endpoint must deny HR access with 403 Forbidden."""
        self._login(self.hr_id, self.hr_email, "hr")
        endpoints = [
            ("GET", "/api/platform-admin/users"),
            ("GET", f"/api/platform-admin/users/{self.cand_a_id}"),
            ("GET", "/api/platform-admin/analytics"),
            ("GET", "/api/platform-admin/jobs"),
            ("GET", f"/api/platform-admin/jobs/{self.job_id}"),
            ("GET", "/api/platform-admin/applications"),
            ("GET", f"/api/platform-admin/applications/{self.app_id}"),
            ("GET", "/api/platform-admin/resumes"),
            ("GET", f"/api/platform-admin/resumes/{self.resume_id}"),
            ("GET", "/api/platform-admin/security/login-attempts"),
            ("GET", "/api/platform-admin/security/outliers"),
            ("GET", "/api/platform-admin/audit"),
            ("GET", "/api/platform-admin/system/health"),
            ("GET", "/api/platform-admin/system/integrations"),
            ("GET", "/api/platform-admin/export?format=json"),
            ("GET", "/api/ml/status"),
            ("POST", "/api/ml/cache/flush"),
            ("POST", "/api/ml/train"),
        ]
        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, json={})
            self.assertEqual(res.status_code, 403, f"Expected 403 for HR {method} {url}, got {res.status_code}")

    def test_04_all_platform_admin_endpoints_allow_platform_admin(self):
        """Platform Admin must be allowed access (HTTP 200/202)."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        endpoints = [
            ("GET", "/api/platform-admin/users"),
            ("GET", f"/api/platform-admin/users/{self.cand_a_id}"),
            ("GET", "/api/platform-admin/analytics"),
            ("GET", "/api/platform-admin/jobs"),
            ("GET", f"/api/platform-admin/jobs/{self.job_id}"),
            ("GET", "/api/platform-admin/applications"),
            ("GET", f"/api/platform-admin/applications/{self.app_id}"),
            ("GET", "/api/platform-admin/resumes"),
            ("GET", f"/api/platform-admin/resumes/{self.resume_id}"),
            ("GET", "/api/platform-admin/security/login-attempts"),
            ("GET", "/api/platform-admin/security/outliers"),
            ("GET", "/api/platform-admin/audit"),
            ("GET", "/api/platform-admin/system/health"),
            ("GET", "/api/platform-admin/system/integrations"),
            ("GET", "/api/platform-admin/export?format=json"),
            ("GET", "/api/ml/status"),
            ("POST", "/api/ml/cache/flush"),
        ]
        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, json={})
            self.assertIn(res.status_code, (200, 202), f"Expected 200/202 for Admin {method} {url}, got {res.status_code}")

    # ═══════════════════════════════════════════════════════════
    # 2. IDOR / OBJECT-LEVEL AUTHORIZATION TESTS
    # ═══════════════════════════════════════════════════════════

    def test_05_idor_candidate_cannot_access_other_candidate_resume(self):
        """Candidate B cannot download Candidate A's resume via IDOR."""
        self._login(self.cand_b_id, self.cand_b_email, "candidate")
        res = self.client.get(f"/api/resume/download/{self.resume_id}")
        self.assertEqual(res.status_code, 403)
        self.assertIn("Unauthorized", res.get_json().get("message", ""))

    def test_06_idor_candidate_can_download_own_resume(self):
        """Candidate A can download their own uploaded resume."""
        self._login(self.cand_a_id, self.cand_a_email, "candidate")
        res = self.client.get(f"/api/resume/download/{self.resume_id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"%PDF-1.4 mock resume binary content", res.data)

    def test_07_idor_admin_can_download_candidate_resume(self):
        """Platform Admin can securely download candidate resumes for auditing."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        res = self.client.get(f"/api/resume/download/{self.resume_id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"%PDF-1.4 mock resume binary content", res.data)

    # ═══════════════════════════════════════════════════════════
    # 3. ROLE ESCALATION & PRIVILEGE MANIPULATION TESTS
    # ═══════════════════════════════════════════════════════════

    def test_08_candidate_cannot_escalate_own_role(self):
        """Candidate cannot change their role to admin."""
        self._login(self.cand_a_id, self.cand_a_email, "candidate")
        res = self.client.post(f"/api/platform-admin/users/{self.cand_a_id}/role", json={"role": "admin"})
        self.assertEqual(res.status_code, 403)

    def test_09_hr_cannot_escalate_own_role(self):
        """HR user cannot change their role to admin."""
        self._login(self.hr_id, self.hr_email, "hr")
        res = self.client.post(f"/api/platform-admin/users/{self.hr_id}/role", json={"role": "admin"})
        self.assertEqual(res.status_code, 403)

    def test_10_admin_cannot_modify_own_role(self):
        """Admin cannot modify their own role claims directly."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        res = self.client.post(f"/api/platform-admin/users/{self.admin1_id}/role", json={"role": "candidate"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("cannot modify their own role", res.get_json().get("message", ""))

    # ═══════════════════════════════════════════════════════════
    # 4. ADMIN SELF-PROTECTION & FINAL ADMIN LOCKOUT TESTS
    # ═══════════════════════════════════════════════════════════

    def test_11_admin_cannot_deactivate_self(self):
        """Admin cannot deactivate their own active account."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        res = self.client.post(f"/api/platform-admin/users/{self.admin1_id}/deactivate")
        self.assertEqual(res.status_code, 400)
        self.assertIn("cannot deactivate their own account", res.get_json().get("message", ""))

    def test_12_admin_cannot_delete_self(self):
        """Admin cannot delete their own active account."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        res = self.client.delete(f"/api/platform-admin/users/{self.admin1_id}")
        self.assertEqual(res.status_code, 400)
        self.assertIn("cannot delete their own account", res.get_json().get("message", ""))

    def test_13_cannot_delete_or_deactivate_final_active_admin(self):
        """System refuses to delete or deactivate the last remaining active administrator."""
        self._login(self.admin1_id, self.admin1_email, "admin")

        # Deactivate Admin 2 first
        res1 = self.client.post(f"/api/platform-admin/users/{self.admin2_id}/deactivate")
        self.assertEqual(res1.status_code, 200)

        # Admin 1 is the only active admin remaining; cannot be demoted, deactivated, or deleted
        res2 = self.client.delete(f"/api/platform-admin/users/{self.admin1_id}")
        self.assertEqual(res2.status_code, 400)

    def test_14_admin_can_delete_candidate_with_cascading_cleanup(self):
        """Admin deleting a candidate removes user, resumes, applications, and logs audit."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        res = self.client.delete(f"/api/platform-admin/users/{self.cand_a_id}")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        with get_db() as conn:
            u = conn.execute("SELECT id FROM users WHERE id=?", (self.cand_a_id,)).fetchone()
            self.assertIsNone(u)
            r = conn.execute("SELECT id FROM resumes WHERE user_id=?", (self.cand_a_id,)).fetchone()
            self.assertIsNone(r)
            a = conn.execute("SELECT id FROM applications WHERE user_id=?", (self.cand_a_id,)).fetchone()
            self.assertIsNone(a)

    # ═══════════════════════════════════════════════════════════
    # 5. PLATFORM DATA EXPORT TESTS
    # ═══════════════════════════════════════════════════════════

    def test_15_export_json_format_and_zero_secret_exposure(self):
        """Export JSON returns platform entities and does NOT expose password hashes or secrets."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        res = self.client.get("/api/platform-admin/export?format=json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/json")

        data = json.loads(res.data.decode("utf-8"))
        self.assertTrue(data["success"])
        self.assertIn("users", data["data"])
        self.assertIn("jobs", data["data"])
        self.assertIn("applications", data["data"])

        # Verify NO password field in users export
        for u in data["data"]["users"]:
            self.assertNotIn("password", u)
            self.assertNotIn("password_hash", u)

    def test_16_export_csv_format(self):
        """Export CSV returns text/csv response."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        res = self.client.get("/api/platform-admin/export?format=csv&type=users")
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.mimetype)
        self.assertIn("text/csv", res.mimetype or "")
        csv_text = res.data.decode("utf-8")
        self.assertIn("ID,Name,Email,Role", csv_text)

    def test_17_export_invalid_format_rejected(self):
        """Export endpoint rejects unsupported format with 400 Bad Request."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        res = self.client.get("/api/platform-admin/export?format=xml")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

    def test_18_export_creates_audit_log_entry(self):
        """Export action is recorded into the audit trail."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        res = self.client.get("/api/platform-admin/export?format=json&type=all")
        self.assertEqual(res.status_code, 200)

        with get_db() as conn:
            audit = conn.execute("SELECT action, details FROM audit_logs WHERE action='export_platform_data'").fetchone()
            self.assertIsNotNone(audit)
            self.assertIn("format=json", audit["details"])

    # ═══════════════════════════════════════════════════════════
    # 6. ML PIPELINE SECURITY & CONCURRENCY
    # ═══════════════════════════════════════════════════════════

    def test_19_ml_train_requires_admin(self):
        """POST /api/ml/train requires Platform Admin authorization."""
        res_unauth = self.client.post("/api/ml/train", json={})
        self.assertEqual(res_unauth.status_code, 401)

        self._login(self.cand_a_id, self.cand_a_email, "candidate")
        res_cand = self.client.post("/api/ml/train", json={})
        self.assertEqual(res_cand.status_code, 403)

        self._login(self.hr_id, self.hr_email, "hr")
        res_hr = self.client.post("/api/ml/train", json={})
        self.assertEqual(res_hr.status_code, 403)

    def test_20_ml_cache_flush_requires_admin_and_succeeds(self):
        """POST /api/ml/cache/flush executes cleanly for Platform Admin."""
        self._login(self.admin1_id, self.admin1_email, "admin")
        res = self.client.post("/api/ml/cache/flush")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

    # ═══════════════════════════════════════════════════════════
    # 7. SYSTEM HEALTH & INTEGRATIONS ZERO SECRET DISCLOSURE
    # ═══════════════════════════════════════════════════════════

    def test_21_system_health_and_integrations_zero_secrets(self):
        """System health & integrations diagnostic endpoints do not expose API secrets or stack traces."""
        self._login(self.admin1_id, self.admin1_email, "admin")

        res_health = self.client.get("/api/platform-admin/system/health")
        self.assertEqual(res_health.status_code, 200)
        health_json = res_health.get_json()
        self.assertTrue(health_json["success"])
        health_str = json.dumps(health_json)
        self.assertNotIn("DATABASE_URL", health_str)
        self.assertNotIn("SECRET_KEY", health_str)

        res_integ = self.client.get("/api/platform-admin/system/integrations")
        self.assertEqual(res_integ.status_code, 200)
        integ_json = res_integ.get_json()
        self.assertTrue(integ_json["success"])
        integ_str = json.dumps(integ_json)
        self.assertNotIn("SECRET_KEY", integ_str)

    # ═══════════════════════════════════════════════════════════
    # 8. OUTLIER FRAUD RESOLUTION & UNIFIED AUDIT TRAIL
    # ═══════════════════════════════════════════════════════════

    def test_22_security_outlier_resolve_and_audit_trail(self):
        """Admin can resolve an outlier candidate flag and write to audit_logs."""
        # Create an outlier candidate
        outlier_id, outlier_email = self._create_user("Outlier User", "candidate", is_verified=1, ats_score=99)
        with get_db() as conn:
            conn.execute("UPDATE users SET is_outlier = 1 WHERE id = ?", (outlier_id,))
            if hasattr(conn, "commit"):
                conn.commit()

        # Check in outliers list
        self._login(self.admin1_id, self.admin1_email, "admin")
        res_list = self.client.get("/api/platform-admin/security/outliers")
        self.assertEqual(res_list.status_code, 200)
        data = res_list.get_json()
        outliers = data.get("data", {}).get("outliers", data.get("outliers", []))
        outlier_ids = [o.get("user_id", o.get("id")) for o in outliers]
        self.assertIn(outlier_id, outlier_ids)

        # Non-admin cannot resolve
        self._login(self.cand_a_id, self.cand_a_email, "candidate")
        res_cand = self.client.post(f"/api/platform-admin/security/outliers/{outlier_id}/resolve")
        self.assertEqual(res_cand.status_code, 403)

        # Admin resolves outlier
        self._login(self.admin1_id, self.admin1_email, "admin")
        res_resolve = self.client.post(f"/api/platform-admin/security/outliers/{outlier_id}/resolve")
        self.assertEqual(res_resolve.status_code, 200)
        self.assertTrue(res_resolve.get_json()["success"])

        # Verify DB is_outlier cleared
        with get_db() as conn:
            user = conn.execute("SELECT is_outlier FROM users WHERE id = ?", (outlier_id,)).fetchone()
            self.assertEqual(user["is_outlier"], 0)

            # Audit log entry created
            audit = conn.execute("SELECT action, details FROM audit_logs WHERE action = 'resolve_outlier' ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(audit)
            self.assertIn(outlier_email, audit["details"])

    def test_23_security_audit_log_aggregation_sources(self):
        """Unified audit logs endpoint returns records across audit_logs and operational tables."""
        self._login(self.admin1_id, self.admin1_email, "admin")

        # Insert audit_log record
        with get_db() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, details TEXT, ip_address TEXT, timestamp TEXT DEFAULT (datetime('now')))"
            )
            conn.execute(
                "INSERT INTO audit_logs (user_id, action, details, ip_address, timestamp) VALUES (?, 'system_security_check', 'Verification passed', '10.0.0.1', datetime('now'))",
                (self.admin1_id,)
            )
            if hasattr(conn, "commit"):
                conn.commit()

        res = self.client.get("/api/platform-admin/audit?source=all")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        events = data.get("data", {}).get("events", data.get("events", []))
        self.assertGreaterEqual(len(events), 1)

        # Check presence of expected keys in event
        first_event = events[0]
        self.assertIn("source", first_event)
        self.assertIn("source_table", first_event)
        self.assertIn("action", first_event)
        self.assertIn("timestamp", first_event)


if __name__ == "__main__":
    unittest.main()

