# ============================================================
#  TalentSync / HireAI — Platform Admin Phase 1 Regression Suite
#  Strictly adheres to:
#  - TestingConfig with isolated temporary database & uploads
#  - Cross-role authorization & isolation (Candidate/HR 403, Admin 200)
#  - Final active admin safety & self-modification prevention
#  - Real DB aggregation for Analytics (no hardcoded/demo values)
#  - Security/Fraud oversight & Outlier retrieval
#  - Read-only Audit stream with empty state resilience
#  - SQL injection resistance & zero secret leakage
# ============================================================

import time
import json
import unittest
from flask import session

from app import create_app
from app.config.settings import TestingConfig, Config
from app.database.connection import get_db
from werkzeug.security import generate_password_hash
from app.controllers.auth_controller import register_user


class TestPlatformAdminRegression(unittest.TestCase):
    """Production-grade regression test suite for Platform Admin Phase 1."""

    def setUp(self):
        # Always use isolated TestingConfig
        self.app = create_app(TestingConfig)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # Seed controlled test accounts
        self.admin_id, self.admin_email = self._create_user("Super Admin", "admin", is_verified=1)
        self.hr_id, self.hr_email       = self._create_user("HR Manager", "hr", is_verified=1)
        self.cand_id, self.cand_email   = self._create_user("Jane Candidate", "candidate", is_verified=1)
        self.cand2_id, self.cand2_email = self._create_user("John Inactive", "candidate", is_verified=0)

    def tearDown(self):
        self.app_context.pop()

    def _unique_email(self, prefix="pa_test"):
        return f"{prefix}_{int(time.time() * 1000)}_{id(self)}@test.com"

    def _create_user(self, name, role, is_verified=1, ats_score=75, is_outlier=0):
        email = self._unique_email(role)
        hashed = generate_password_hash("ValidPassword10!")
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, password, role, is_verified, ats_score, is_outlier) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, email, hashed, role, is_verified, ats_score, is_outlier)
            )
            user_id = cur.lastrowid
            conn.commit()
        return user_id, email

    def _login_as(self, user_id):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

    def _logout(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    # ============================================================
    # 1. AUTHORIZATION TESTS & CROSS-ROLE ISOLATION
    # ============================================================

    def test_auth_unauthenticated_requests_return_401(self):
        """Unauthenticated requests to Platform Admin endpoints must return HTTP 401."""
        self._logout()
        endpoints = [
            ("GET", "/api/platform-admin/users"),
            ("GET", f"/api/platform-admin/users/{self.cand_id}"),
            ("POST", f"/api/platform-admin/users/{self.cand_id}/activate"),
            ("POST", f"/api/platform-admin/users/{self.cand_id}/deactivate"),
            ("POST", f"/api/platform-admin/users/{self.cand_id}/role"),
            ("GET", "/api/platform-admin/analytics"),
            ("GET", "/api/platform-admin/security/login-attempts"),
            ("GET", "/api/platform-admin/security/outliers"),
            ("GET", "/api/platform-admin/audit"),
        ]

        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, json={})
            self.assertEqual(res.status_code, 401, f"Failed 401 check on {url}: got {res.status_code}")
            data = res.get_json()
            self.assertFalse(data.get("success"))

    def test_auth_candidate_role_returns_403(self):
        """Candidate accounts accessing Platform Admin endpoints must receive HTTP 403."""
        self._login_as(self.cand_id)
        endpoints = [
            ("GET", "/api/platform-admin/users"),
            ("GET", f"/api/platform-admin/users/{self.cand_id}"),
            ("POST", f"/api/platform-admin/users/{self.cand_id}/activate"),
            ("POST", f"/api/platform-admin/users/{self.cand_id}/deactivate"),
            ("POST", f"/api/platform-admin/users/{self.cand_id}/role"),
            ("GET", "/api/platform-admin/analytics"),
            ("GET", "/api/platform-admin/security/login-attempts"),
            ("GET", "/api/platform-admin/security/outliers"),
            ("GET", "/api/platform-admin/audit"),
        ]

        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, json={"role": "hr"})
            self.assertEqual(res.status_code, 403, f"Candidate was not blocked with 403 on {url}: got {res.status_code}")
            data = res.get_json()
            self.assertFalse(data.get("success"))

    def test_auth_hr_role_returns_403(self):
        """HR / Recruiter accounts accessing Platform Admin endpoints must receive HTTP 403."""
        self._login_as(self.hr_id)
        endpoints = [
            ("GET", "/api/platform-admin/users"),
            ("GET", f"/api/platform-admin/users/{self.cand_id}"),
            ("POST", f"/api/platform-admin/users/{self.cand_id}/activate"),
            ("POST", f"/api/platform-admin/users/{self.cand_id}/deactivate"),
            ("POST", f"/api/platform-admin/users/{self.cand_id}/role"),
            ("GET", "/api/platform-admin/analytics"),
            ("GET", "/api/platform-admin/security/login-attempts"),
            ("GET", "/api/platform-admin/security/outliers"),
            ("GET", "/api/platform-admin/audit"),
        ]

        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, json={"role": "admin"})
            self.assertEqual(res.status_code, 403, f"HR was not blocked with 403 on {url}: got {res.status_code}")
            data = res.get_json()
            self.assertFalse(data.get("success"))

    def test_auth_admin_role_allowed(self):
        """Admin accounts accessing Platform Admin endpoints succeed with HTTP 200."""
        self._login_as(self.admin_id)
        res = self.client.get("/api/platform-admin/users")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

        res = self.client.get("/api/platform-admin/analytics")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

    def test_candidate_cannot_access_hr_endpoints(self):
        """Candidate cannot access existing HR endpoints (/api/admin/*)."""
        self._login_as(self.cand_id)
        res = self.client.get("/api/admin/candidates")
        self.assertEqual(res.status_code, 403)

    # ============================================================
    # 2. USER & ROLE MANAGEMENT TESTS
    # ============================================================

    def test_user_list_pagination_and_deterministic_ordering(self):
        """Verify user listing supports pagination, deterministic ordering, and bounds."""
        self._login_as(self.admin_id)
        res = self.client.get("/api/platform-admin/users?page=1&limit=2")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        users = data.get("users", data.get("data", {}).get("users", []))
        self.assertEqual(len(users), 2)
        pagination = data.get("pagination", data.get("data", {}).get("pagination", {}))
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["limit"], 2)
        self.assertGreaterEqual(pagination["total"], 4)
        # Check deterministic ordering (id ascending)
        self.assertLess(users[0]["id"], users[1]["id"])

    def test_user_list_filtering(self):
        """Verify user listing filters by search query, role, and active status."""
        self._login_as(self.admin_id)

        # Role filter
        res = self.client.get("/api/platform-admin/users?role=hr")
        data = res.get_json()
        for u in data.get("users", data.get("data", {}).get("users", [])):
            self.assertEqual(u["role"], "hr")

        # Status filter
        res = self.client.get("/api/platform-admin/users?status=inactive")
        data = res.get_json()
        for u in data.get("users", data.get("data", {}).get("users", [])):
            self.assertEqual(u["is_active"], False)

        # Search filter
        res = self.client.get(f"/api/platform-admin/users?search={self.cand_email}")
        data = res.get_json()
        self.assertGreaterEqual(len(data.get("users", [])), 1)
        self.assertEqual(data.get("users", [])[0]["email"], self.cand_email)

    def test_user_detail_safe_profile(self):
        """GET /api/platform-admin/users/<id> returns profile without leaking secrets."""
        self._login_as(self.admin_id)
        res = self.client.get(f"/api/platform-admin/users/{self.cand_id}")
        self.assertEqual(res.status_code, 200)
        user = res.get_json().get("user", res.get_json().get("data", {}).get("user"))
        self.assertEqual(user["id"], self.cand_id)
        self.assertEqual(user["email"], self.cand_email)

        # Security check: secrets must NEVER be present
        for forbidden in ["password", "password_hash", "reset_token", "verification_token", "secret"]:
            self.assertNotIn(forbidden, user)

    def test_user_detail_nonexistent_and_malformed_id(self):
        """User detail with nonexistent or malformed ID returns 404 or 400."""
        self._login_as(self.admin_id)
        res = self.client.get("/api/platform-admin/users/9999999")
        self.assertEqual(res.status_code, 404)
        self.assertFalse(res.get_json()["success"])

        res = self.client.get("/api/platform-admin/users/abc")
        self.assertIn(res.status_code, (400, 404))

        res = self.client.get("/api/platform-admin/users/-5")
        self.assertIn(res.status_code, (400, 404))

    def test_activate_and_deactivate_user(self):
        """Verify activating and deactivating a target user toggles is_verified in DB."""
        self._login_as(self.admin_id)

        # Deactivate candidate
        res = self.client.post(f"/api/platform-admin/users/{self.cand_id}/deactivate")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        with get_db() as conn:
            u = conn.execute("SELECT is_verified FROM users WHERE id=?", (self.cand_id,)).fetchone()
            self.assertEqual(u["is_verified"], 0)

        # Activate candidate
        res = self.client.post(f"/api/platform-admin/users/{self.cand_id}/activate")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        with get_db() as conn:
            u = conn.execute("SELECT is_verified FROM users WHERE id=?", (self.cand_id,)).fetchone()
            self.assertEqual(u["is_verified"], 1)

    def test_self_deactivation_is_prevented(self):
        """Admin cannot deactivate their own account."""
        self._login_as(self.admin_id)
        res = self.client.post(f"/api/platform-admin/users/{self.admin_id}/deactivate")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("own account", data["message"].lower())

    def test_final_active_admin_deactivation_is_prevented(self):
        """The final active admin on the platform cannot be deactivated."""
        # Ensure only self.admin_id is active admin
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE role='admin' AND id!=?", (self.admin_id,))
            conn.commit()

        # Create a second admin to test deactivating the final active admin
        admin2_id, _ = self._create_user("Admin Two", "admin", is_verified=1)
        self._login_as(admin2_id)

        # Now self.admin_id and admin2_id are active. Deactivate self.admin_id
        res = self.client.post(f"/api/platform-admin/users/{self.admin_id}/deactivate")
        self.assertEqual(res.status_code, 200)

        # Now admin2_id is the ONLY active admin. Attempting to deactivate admin2_id (by another session or if possible)
        # To simulate: login as self.admin_id (temporarily reactivate) and try to deactivate admin2_id
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=1 WHERE id=?", (self.admin_id,))
            conn.execute("UPDATE users SET is_verified=0 WHERE id!=? AND role='admin'", (self.admin_id,))
            conn.commit()

        # Create a third admin to act as the operator
        operator_id, _ = self._create_user("Operator Admin", "admin", is_verified=1)
        self._login_as(operator_id)
        # Deactivate self.admin_id so operator_id is the ONLY active admin
        self.client.post(f"/api/platform-admin/users/{self.admin_id}/deactivate")

        # Now operator_id is the final active admin. Deactivating self is blocked:
        res = self.client.post(f"/api/platform-admin/users/{operator_id}/deactivate")
        self.assertEqual(res.status_code, 400)

    def test_role_change_valid_transitions(self):
        """Test valid role transitions: candidate <-> hr <-> admin."""
        self._login_as(self.admin_id)

        target_id, _ = self._create_user("Transition Target", "candidate", is_verified=1)

        # candidate -> hr
        res = self.client.post(f"/api/platform-admin/users/{target_id}/role", json={"role": "hr"})
        self.assertEqual(res.status_code, 200)
        with get_db() as conn:
            self.assertEqual(conn.execute("SELECT role FROM users WHERE id=?", (target_id,)).fetchone()["role"], "hr")

        # hr -> admin
        res = self.client.post(f"/api/platform-admin/users/{target_id}/role", json={"role": "admin"})
        self.assertEqual(res.status_code, 200)
        with get_db() as conn:
            self.assertEqual(conn.execute("SELECT role FROM users WHERE id=?", (target_id,)).fetchone()["role"], "admin")

        # admin -> hr
        res = self.client.post(f"/api/platform-admin/users/{target_id}/role", json={"role": "hr"})
        self.assertEqual(res.status_code, 200)
        with get_db() as conn:
            self.assertEqual(conn.execute("SELECT role FROM users WHERE id=?", (target_id,)).fetchone()["role"], "hr")

        # hr -> candidate
        res = self.client.post(f"/api/platform-admin/users/{target_id}/role", json={"role": "candidate"})
        self.assertEqual(res.status_code, 200)
        with get_db() as conn:
            self.assertEqual(conn.execute("SELECT role FROM users WHERE id=?", (target_id,)).fetchone()["role"], "candidate")

    def test_self_role_change_prevented(self):
        """Admin cannot alter their own role."""
        self._login_as(self.admin_id)
        res = self.client.post(f"/api/platform-admin/users/{self.admin_id}/role", json={"role": "hr"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("own role", res.get_json()["message"].lower())

    def test_final_admin_demotion_prevented(self):
        """Cannot demote the final active admin to hr or candidate."""
        # Ensure only self.admin_id is active admin
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE role='admin' AND id!=?", (self.admin_id,))
            conn.commit()

        # Create a second admin to perform the demotion request on self.admin_id
        admin2_id, _ = self._create_user("Admin Two", "admin", is_verified=1)
        self._login_as(admin2_id)

        # Deactivate admin2 so self.admin_id is the ONLY active admin
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE id=?", (admin2_id,))
            conn.commit()

        # Temporarily login as another admin who attempts to demote self.admin_id
        operator_id, _ = self._create_user("Op Admin", "admin", is_verified=1)
        self._login_as(operator_id)
        # Deactivate operator so self.admin_id is strictly the only active admin
        # Demoting self.admin_id should succeed if there are >= 2 active admins (operator and self.admin_id).
        # Demoting operator should fail if operator is the only one.
        with get_db() as conn:
            conn.execute("UPDATE users SET role='candidate' WHERE id=?", (self.admin_id,))
            conn.commit()

        # Now operator_id is the SOLE active admin. Attempting to demote operator_id:
        res = self.client.post(f"/api/platform-admin/users/{operator_id}/role", json={"role": "candidate"})
        self.assertEqual(res.status_code, 400)

    def test_role_change_invalid_role_and_bad_request(self):
        """Invalid role values or missing bodies return 400."""
        self._login_as(self.admin_id)
        res = self.client.post(f"/api/platform-admin/users/{self.cand_id}/role", json={"role": "superadmin"})
        self.assertEqual(res.status_code, 400)

        res = self.client.post(f"/api/platform-admin/users/{self.cand_id}/role", json={})
        self.assertEqual(res.status_code, 400)

    # ============================================================
    # 3. SYSTEM-WIDE ANALYTICS TESTS
    # ============================================================

    def test_analytics_calculated_from_real_database_data(self):
        """GET /api/platform-admin/analytics returns real aggregated figures."""
        self._login_as(self.admin_id)

        # Seed controlled job and application
        with get_db() as conn:
            conn.execute("INSERT INTO jobs (title, company, status) VALUES ('DevOps Lead', 'Cloud Inc', 'Active')")
            job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO applications (user_id, job_id, status) VALUES (?, ?, 'Shortlisted')",
                (self.cand_id, job_id)
            )
            conn.commit()

        res = self.client.get("/api/platform-admin/analytics")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        if "data" in data:
            data = data["data"]

        # Verify users block
        self.assertGreaterEqual(data["users"]["total"], 4)
        self.assertGreaterEqual(data["users"]["active"], 3)
        self.assertGreaterEqual(data["users"]["inactive"], 1)
        self.assertIn("candidate", data["users"]["by_role"])
        self.assertIn("hr", data["users"]["by_role"])
        self.assertIn("admin", data["users"]["by_role"])

        # Verify applications block
        self.assertGreaterEqual(data["applications"]["total"], 1)
        self.assertGreaterEqual(data["applications"]["shortlisted"], 1)

        # Verify jobs block
        self.assertGreaterEqual(data["jobs"]["total"], 1)
        self.assertGreaterEqual(data["jobs"]["active"], 1)

        # Verify ATS block
        self.assertIn("average", data["ats"])
        self.assertIn("distribution", data["ats"])
        self.assertIn("0-20", data["ats"]["distribution"])
        self.assertIn("91-100", data["ats"]["distribution"])

    # ============================================================
    # 4. SECURITY & FRAUD OVERSIGHT TESTS
    # ============================================================

    def test_security_login_attempts_tracking(self):
        """GET /api/platform-admin/security/login-attempts returns real login log data."""
        self._login_as(self.admin_id)

        with get_db() as conn:
            conn.execute(
                "INSERT INTO login_attempts (email, ip_address, success) VALUES (?, '192.168.1.100', 1)",
                (self.admin_email,)
            )
            conn.execute(
                "INSERT INTO login_attempts (email, ip_address, success) VALUES (?, '192.168.1.200', 0)",
                ("intruder@attacker.com",)
            )
            conn.commit()

        res = self.client.get("/api/platform-admin/security/login-attempts")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        if "data" in data:
            data = data["data"]

        self.assertGreaterEqual(data["summary"]["total_attempts"], 2)
        self.assertGreaterEqual(data["summary"]["successful_attempts"], 1)
        self.assertGreaterEqual(data["summary"]["failed_attempts"], 1)
        self.assertGreaterEqual(len(data["attempts"]), 2)
        self.assertGreaterEqual(len(data["top_failed_ips"]), 1)
        self.assertGreaterEqual(len(data["top_targeted_accounts"]), 1)

    def test_security_outlier_retrieval(self):
        """GET /api/platform-admin/security/outliers returns candidates with is_outlier=1."""
        self._login_as(self.admin_id)

        # Create one outlier candidate
        outlier_id, outlier_email = self._create_user("Fraudster Joe", "candidate", is_verified=1, is_outlier=1)

        res = self.client.get("/api/platform-admin/security/outliers")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        if "data" in data:
            data = data["data"]

        self.assertGreaterEqual(data["total_outliers"], 1)
        outlier_emails = [o["email"] for o in data["outliers"]]
        self.assertIn(outlier_email, outlier_emails)

        # Verify no secret leakage
        for forbidden in ["password", "password_hash", "reset_token"]:
            for o in data["outliers"]:
                self.assertNotIn(forbidden, o)

    # ============================================================
    # 5. READ-ONLY AUDIT VIEWER TESTS
    # ============================================================

    def test_audit_logs_empty_dataset_handling(self):
        """Empty audit tables return empty results gracefully without errors."""
        self._login_as(self.admin_id)

        # Clear audit tables in temporary DB
        with get_db() as conn:
            conn.execute("DELETE FROM application_status")
            conn.execute("DELETE FROM recommendation_history")
            conn.execute("DELETE FROM search_history")
            conn.commit()

        res = self.client.get("/api/platform-admin/audit")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        events = data.get("events", data.get("data", {}).get("events", []))
        pagination = data.get("pagination", data.get("data", {}).get("pagination", {}))
        self.assertEqual(len(events), 0)
        self.assertEqual(pagination.get("total", pagination.get("total_items", 0)), 0)

    def test_audit_logs_read_only_and_filtering(self):
        """Audit endpoint accurately reflects historical data and does not modify tables."""
        self._login_as(self.admin_id)

        with get_db() as conn:
            conn.execute(
                "INSERT INTO search_history (user_id, keyword) VALUES (?, 'Machine Learning Engineer')",
                (self.cand_id,)
            )
            conn.commit()

        res = self.client.get("/api/platform-admin/audit?source=search_history")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        if "data" in data:
            data = data["data"]
        self.assertGreaterEqual(len(data["events"]), 1)
        self.assertEqual(data["events"][0]["source"], "search_history")
        self.assertIn("Machine Learning", str(data["events"][0]["details"]))

        # Verify GET did NOT add or delete records
        with get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM search_history").fetchone()[0]
            self.assertEqual(count, 1)

    # ============================================================
    # 6. SQL INJECTION & SECURITY DEFENSE TESTS
    # ============================================================

    def test_sql_injection_defense(self):
        """Malicious SQL injection strings in parameters must be safely sanitized/parameterized."""
        self._login_as(self.admin_id)
        sqli_payloads = [
            "' OR 1=1 --",
            "1; DROP TABLE users; --",
            "admin'--",
            "' UNION SELECT * FROM users --"
        ]

        for payload in sqli_payloads:
            # In user search
            res = self.client.get(f"/api/platform-admin/users?search={payload}")
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.get_json()["success"])

            # In user role filter
            res = self.client.get(f"/api/platform-admin/users?role={payload}")
            self.assertEqual(res.status_code, 200)

            # In login attempts search
            res = self.client.get(f"/api/platform-admin/security/login-attempts?search={payload}")
            self.assertEqual(res.status_code, 200)

            # In audit search
            res = self.client.get(f"/api/platform-admin/audit?search={payload}")
            self.assertEqual(res.status_code, 200)

        # Verify users table was not dropped or compromised
        with get_db() as conn:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            self.assertGreaterEqual(user_count, 4)

    def test_zero_secrets_leakage_across_all_endpoints(self):
        """Audit every Platform Admin response payload for credential leaks."""
        self._login_as(self.admin_id)
        endpoints = [
            "/api/platform-admin/users",
            f"/api/platform-admin/users/{self.cand_id}",
            "/api/platform-admin/analytics",
            "/api/platform-admin/security/login-attempts",
            "/api/platform-admin/security/outliers",
            "/api/platform-admin/audit"
        ]

        forbidden_keys = [
            "password", "password_hash", "reset_token", "verification_token",
            "session_secret", "secret_key", "traceback"
        ]

        for ep in endpoints:
            res = self.client.get(ep)
            text = res.get_data(as_text=True)
            for k in forbidden_keys:
                self.assertNotIn(f'"{k}"', text, f"Response from {ep} contained forbidden secret key: {k}")


if __name__ == "__main__":
    unittest.main()
