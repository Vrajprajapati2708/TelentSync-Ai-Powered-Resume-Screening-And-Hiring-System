# ============================================================
#  TalentSync — Platform Admin Security Remediation Tests
#  Validates Dual-Layer Remediation (Option C):
#  1. Login boundary enforcement for Candidate, HR, and Admin
#  2. Authorization boundary (@role_required) enforcement
#  3. Active session revocation upon deactivation
#  4. Session clearing on deactivated authorization failure
#  5. Account reactivation lifecycle
#  6. Regression protection for RBAC and Final-Admin safety
# ============================================================

import os
import unittest
import time
from werkzeug.security import generate_password_hash

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db


class PlatformAdminSecurityRemediationTests(unittest.TestCase):
    """Test suite verifying Dual-Layer Security Remediation for account deactivation."""

    def setUp(self):
        # Use isolated TestingConfig with active app context
        self.app = create_app(TestingConfig)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def _unique_email(self, prefix: str) -> str:
        return f"{prefix}_{int(time.time() * 1000)}_{id(self)}@test.com"

    def _create_user(self, name: str, role: str, is_verified: int = 1, password: str = "Password123!"):
        email = self._unique_email(role)
        hashed = generate_password_hash(password)
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, password, role, is_verified) VALUES (?, ?, ?, ?, ?)",
                (name, email, hashed, role, is_verified)
            )
            user_id = cur.lastrowid
            conn.commit()
        return user_id, email, password

    # ------------------------------------------------------------
    # 1. Active candidate login succeeds
    # ------------------------------------------------------------
    def test_01_active_candidate_login_succeeds(self):
        uid, email, pwd = self._create_user("Cand Active", "candidate", is_verified=1)
        r = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["success"])
        self.assertEqual(r.get_json()["user"]["role"], "candidate")

    # ------------------------------------------------------------
    # 2. Unverified candidate login remains blocked (SEC-02 contract)
    # ------------------------------------------------------------
    def test_02_unverified_candidate_login_blocked(self):
        uid, email, pwd = self._create_user("Cand Unverified", "candidate", is_verified=0)
        r = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r.status_code, 403)
        data = r.get_json()
        self.assertFalse(data["success"])
        self.assertTrue(data.get("not_verified"))
        self.assertIn("verify your email", data.get("message", "").lower())

    # ------------------------------------------------------------
    # 3. Active HR login succeeds
    # ------------------------------------------------------------
    def test_03_active_hr_login_succeeds(self):
        uid, email, pwd = self._create_user("HR Active", "hr", is_verified=1)
        r = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["success"])
        self.assertEqual(r.get_json()["user"]["role"], "hr")

    # ------------------------------------------------------------
    # 4. Active Admin login succeeds
    # ------------------------------------------------------------
    def test_04_active_admin_login_succeeds(self):
        uid, email, pwd = self._create_user("Admin Active", "admin", is_verified=1)
        r = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["success"])
        self.assertEqual(r.get_json()["user"]["role"], "admin")

    # ------------------------------------------------------------
    # 5. Deactivated candidate login blocked
    # ------------------------------------------------------------
    def test_05_deactivated_candidate_login_blocked(self):
        uid, email, pwd = self._create_user("Cand Deact", "candidate", is_verified=1)
        # Deactivate
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE id=?", (uid,))
            conn.commit()

        r = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r.status_code, 403)
        data = r.get_json()
        self.assertFalse(data["success"])
        self.assertTrue(data.get("not_verified"))

    # ------------------------------------------------------------
    # 6. Deactivated HR login blocked (Option C login boundary)
    # ------------------------------------------------------------
    def test_06_deactivated_hr_login_blocked(self):
        uid, email, pwd = self._create_user("HR Deact", "hr", is_verified=1)
        # Deactivate
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE id=?", (uid,))
            conn.commit()

        r = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r.status_code, 403)
        data = r.get_json()
        self.assertFalse(data["success"])
        self.assertTrue(data.get("is_deactivated"))
        self.assertIn("deactivated", data.get("message", "").lower())

    # ------------------------------------------------------------
    # 7. Deactivated Admin login blocked (Option C login boundary)
    # ------------------------------------------------------------
    def test_07_deactivated_admin_login_blocked(self):
        uid, email, pwd = self._create_user("Admin Deact", "admin", is_verified=1)
        # Deactivate
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE id=?", (uid,))
            conn.commit()

        r = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r.status_code, 403)
        data = r.get_json()
        self.assertFalse(data["success"])
        self.assertTrue(data.get("is_deactivated"))
        self.assertIn("deactivated", data.get("message", "").lower())

    # ------------------------------------------------------------
    # 8. Already-authenticated HR session becomes blocked after deactivation
    # ------------------------------------------------------------
    def test_08_authenticated_hr_session_revoked_on_deactivation(self):
        uid, email, pwd = self._create_user("HR Session User", "hr", is_verified=1)

        # Login while active
        login_res = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(login_res.status_code, 200)

        # Access HR protected endpoint
        stats_res1 = self.client.get("/api/admin/stats")
        self.assertEqual(stats_res1.status_code, 200)

        # Deactivate account while session is active
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE id=?", (uid,))
            conn.commit()

        # Next request must be blocked at @role_required boundary
        stats_res2 = self.client.get("/api/admin/stats")
        self.assertEqual(stats_res2.status_code, 403)
        data = stats_res2.get_json()
        self.assertFalse(data["success"])
        self.assertIn("deactivated", data.get("message", "").lower())

    # ------------------------------------------------------------
    # 9. Already-authenticated Admin session becomes blocked after deactivation
    # ------------------------------------------------------------
    def test_09_authenticated_admin_session_revoked_on_deactivation(self):
        uid, email, pwd = self._create_user("Admin Session User", "admin", is_verified=1)

        # Login while active
        login_res = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(login_res.status_code, 200)

        # Access Platform Admin endpoint
        overview_res1 = self.client.get("/api/platform-admin/analytics")
        self.assertEqual(overview_res1.status_code, 200)

        # Deactivate admin account while session is active
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE id=?", (uid,))
            conn.commit()

        # Next request must be blocked at @role_required boundary
        overview_res2 = self.client.get("/api/platform-admin/analytics")
        self.assertEqual(overview_res2.status_code, 403)
        data = overview_res2.get_json()
        self.assertFalse(data["success"])
        self.assertIn("deactivated", data.get("message", "").lower())

    # ------------------------------------------------------------
    # 10. Session is cleared after deactivated-user authorization failure
    # ------------------------------------------------------------
    def test_10_session_cleared_after_deactivation_failure(self):
        uid, email, pwd = self._create_user("HR Clear Session", "hr", is_verified=1)

        # Login
        self.client.post("/api/auth/login", json={"email": email, "password": pwd})

        # Deactivate
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE id=?", (uid,))
            conn.commit()

        # Request triggers role_required -> clears session and returns 403
        r1 = self.client.get("/api/admin/stats")
        self.assertEqual(r1.status_code, 403)

        # Subsequent call to /api/auth/me should return 401 because session was cleared
        r2 = self.client.get("/api/auth/me")
        self.assertEqual(r2.status_code, 401)

    # ------------------------------------------------------------
    # 11. Reactivated candidate can log in
    # ------------------------------------------------------------
    def test_11_reactivated_candidate_can_login(self):
        uid, email, pwd = self._create_user("Cand Reactivate", "candidate", is_verified=0)

        # Login fails when is_verified=0
        r_fail = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r_fail.status_code, 403)

        # Reactivate
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=1 WHERE id=?", (uid,))
            conn.commit()

        # Login succeeds
        r_ok = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r_ok.status_code, 200)
        self.assertTrue(r_ok.get_json()["success"])

    # ------------------------------------------------------------
    # 12. Reactivated HR can log in
    # ------------------------------------------------------------
    def test_12_reactivated_hr_can_login(self):
        uid, email, pwd = self._create_user("HR Reactivate", "hr", is_verified=1)

        # Deactivate
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE id=?", (uid,))
            conn.commit()

        r_fail = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r_fail.status_code, 403)

        # Reactivate
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=1 WHERE id=?", (uid,))
            conn.commit()

        r_ok = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r_ok.status_code, 200)
        self.assertTrue(r_ok.get_json()["success"])

    # ------------------------------------------------------------
    # 13. Reactivated Admin can log in
    # ------------------------------------------------------------
    def test_13_reactivated_admin_can_login(self):
        uid, email, pwd = self._create_user("Admin Reactivate", "admin", is_verified=1)

        # Deactivate
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE id=?", (uid,))
            conn.commit()

        r_fail = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r_fail.status_code, 403)

        # Reactivate
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=1 WHERE id=?", (uid,))
            conn.commit()

        r_ok = self.client.post("/api/auth/login", json={"email": email, "password": pwd})
        self.assertEqual(r_ok.status_code, 200)
        self.assertTrue(r_ok.get_json()["success"])

    # ------------------------------------------------------------
    # 14. Existing Platform Admin final-admin protection remains intact
    # ------------------------------------------------------------
    def test_14_final_admin_protection_remains_intact(self):
        super_admin_id, super_admin_email, super_admin_pwd = self._create_user("Sole Admin", "admin", is_verified=1)
        self.client.post("/api/auth/login", json={"email": super_admin_email, "password": super_admin_pwd})

        # Ensure no other active admins exist
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified=0 WHERE role='admin' AND id!=?", (super_admin_id,))
            conn.commit()

        # Attempt to deactivate sole active admin via Platform Admin API
        r = self.client.post(f"/api/platform-admin/users/{super_admin_id}/deactivate")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.get_json()["success"])

        # Attempt to demote sole active admin to hr
        r2 = self.client.post(f"/api/platform-admin/users/{super_admin_id}/role", json={"role": "hr"})
        self.assertEqual(r2.status_code, 400)
        self.assertFalse(r2.get_json()["success"])

    # ------------------------------------------------------------
    # 15. Candidate/HR/Admin RBAC behavior remains unchanged for active accounts
    # ------------------------------------------------------------
    def test_15_rbac_isolation_unchanged_for_active_accounts(self):
        cand_id, cand_email, cand_pwd = self._create_user("Active Cand RBAC", "candidate", is_verified=1)
        hr_id, hr_email, hr_pwd = self._create_user("Active HR RBAC", "hr", is_verified=1)

        # Candidate client
        c_cand = self.app.test_client()
        c_cand.post("/api/auth/login", json={"email": cand_email, "password": cand_pwd})
        # Candidate cannot access HR or Platform Admin
        self.assertEqual(c_cand.get("/api/admin/stats").status_code, 403)
        self.assertEqual(c_cand.get("/api/platform-admin/analytics").status_code, 403)

        # HR client
        c_hr = self.app.test_client()
        c_hr.post("/api/auth/login", json={"email": hr_email, "password": hr_pwd})
        # HR can access HR stats, but cannot access Platform Admin
        self.assertEqual(c_hr.get("/api/admin/stats").status_code, 200)
        self.assertEqual(c_hr.get("/api/platform-admin/analytics").status_code, 403)

    # ------------------------------------------------------------
    # 16. Existing /api/admin/* behavior remains functional
    # ------------------------------------------------------------
    def test_16_existing_admin_routes_remain_functional(self):
        hr_id, hr_email, hr_pwd = self._create_user("Active HR Functional", "hr", is_verified=1)
        self.client.post("/api/auth/login", json={"email": hr_email, "password": hr_pwd})

        r_stats = self.client.get("/api/admin/stats")
        self.assertEqual(r_stats.status_code, 200)

        r_jobs = self.client.get("/api/admin/jobs")
        self.assertEqual(r_jobs.status_code, 200)

    # ------------------------------------------------------------
    # 17. Existing /api/platform-admin/* authorization remains functional
    # ------------------------------------------------------------
    def test_17_existing_platform_admin_routes_remain_functional(self):
        admin_id, admin_email, admin_pwd = self._create_user("Active Admin Func", "admin", is_verified=1)
        self.client.post("/api/auth/login", json={"email": admin_email, "password": admin_pwd})

        r_users = self.client.get("/api/platform-admin/users")
        self.assertEqual(r_users.status_code, 200)
        self.assertTrue(r_users.get_json()["success"])

        r_analytics = self.client.get("/api/platform-admin/analytics")
        self.assertEqual(r_analytics.status_code, 200)
        self.assertTrue(r_analytics.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
