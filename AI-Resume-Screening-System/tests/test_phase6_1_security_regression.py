# ============================================================
#  TalentSync / HireAI — Phase 6.1 Security & Authorization Suite
#  Covers SEC-01, SEC-02, SEC-06, and SEC-07.
# ============================================================

import time
import datetime
import unittest
from flask import session

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import (
    register_user, login_user, verify_email_token,
    generate_password_reset_token, reset_password_with_token
)


class TestPhase61SecurityRegression(unittest.TestCase):
    """Rigorous regression tests for Phase 6.1 Security fixes."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def _unique_email(self, prefix="sec"):
        return f"{prefix}_{int(time.time() * 1000)}_{id(self)}@test.com"

    # ============================================================
    # SEC-01: PREVENT PUBLIC HR / PRIVILEGED SELF-REGISTRATION
    # ============================================================

    def test_01_candidate_registration_succeeds(self):
        """SEC-01: Public registration with role=candidate succeeds."""
        email = self._unique_email("cand_ok")
        res = self.client.post("/api/auth/register", json={
            "name": "Legit Candidate",
            "email": email,
            "password": "ValidPassword10!",
            "role": "candidate"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["user"]["role"], "candidate")

    def test_02_hr_self_registration_fails(self):
        """SEC-01: Public registration attempting role=hr returns HTTP 403."""
        email = self._unique_email("hr_bad")
        res = self.client.post("/api/auth/register", json={
            "name": "Attacker HR",
            "email": email,
            "password": "ValidPassword10!",
            "role": "hr"
        })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("privileged", data.get("message", "").lower())

    def test_03_admin_self_registration_fails(self):
        """SEC-01: Public registration attempting role=admin returns HTTP 403."""
        email = self._unique_email("admin_bad")
        res = self.client.post("/api/auth/register", json={
            "name": "Attacker Admin",
            "email": email,
            "password": "ValidPassword10!",
            "role": "admin"
        })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("privileged", data.get("message", "").lower())

    def test_04_unknown_role_cannot_create_privileged_account(self):
        """SEC-01: Public registration with arbitrary/unknown role returns HTTP 403."""
        email = self._unique_email("super_bad")
        res = self.client.post("/api/auth/register", json={
            "name": "Root Pretender",
            "email": email,
            "password": "ValidPassword10!",
            "role": "superadmin"
        })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data.get("success"))

    def test_05_existing_privileged_accounts_remain_intact(self):
        """SEC-01: Pre-existing HR accounts in database remain intact with role=hr."""
        with get_db() as conn:
            hr_user = conn.execute("SELECT id, email, role FROM users WHERE role='hr' LIMIT 1").fetchone()
            self.assertIsNotNone(hr_user)
            self.assertEqual(hr_user["role"], "hr")

    # ============================================================
    # SEC-02: ENFORCE EMAIL VERIFICATION ON CANDIDATE LOGIN
    # ============================================================

    def test_06_unverified_candidate_cannot_login(self):
        """SEC-02: Unverified candidate receives HTTP 403 on login attempt."""
        email = self._unique_email("unverified")
        reg_res = self.client.post("/api/auth/register", json={
            "name": "Unverified Candidate",
            "email": email,
            "password": "ValidPassword10!",
            "role": "candidate"
        })
        self.assertEqual(reg_res.status_code, 201)

        # Attempt to log in without verifying
        login_res = self.client.post("/api/auth/login", json={
            "email": email,
            "password": "ValidPassword10!"
        })
        self.assertEqual(login_res.status_code, 403)
        data = login_res.get_json()
        self.assertFalse(data.get("success"))
        self.assertTrue(data.get("not_verified"))
        self.assertIn("verify your email", data.get("message", "").lower())

    def test_07_unverified_candidate_creates_no_session(self):
        """SEC-02: Unverified candidate login does not establish a valid session."""
        email = self._unique_email("no_sess")
        register_user("No Session Candidate", email, "ValidPassword10!", "candidate")

        with self.client:
            res = self.client.post("/api/auth/login", json={
                "email": email,
                "password": "ValidPassword10!"
            })
            self.assertEqual(res.status_code, 403)
            # Session must NOT have user_id
            self.assertIsNone(session.get("user_id"))

    def test_08_verified_candidate_can_login(self):
        """SEC-02: Verified candidate successfully logs in with HTTP 200."""
        email = self._unique_email("verified_login")
        reg_res = self.client.post("/api/auth/register", json={
            "name": "Verified Candidate",
            "email": email,
            "password": "ValidPassword10!",
            "role": "candidate"
        })
        token = reg_res.get_json().get("dev_verification_token")
        self.assertIsNotNone(token)

        # Verify email token
        v_res = self.client.post("/api/auth/verify_email", json={"token": token})
        self.assertEqual(v_res.status_code, 200)

        # Now login must succeed
        login_res = self.client.post("/api/auth/login", json={
            "email": email,
            "password": "ValidPassword10!"
        })
        self.assertEqual(login_res.status_code, 200)
        data = login_res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["user"]["email"], email)

    def test_09_hr_account_bypasses_email_verification(self):
        """SEC-02 & Platform Admin Remediation:
        A. Active HR/Admin accounts bypass candidate-style email verification tokens and authenticate directly.
        B. Deactivated HR/Admin accounts (is_verified=0) are blocked from authenticating.
        """
        # A. Active HR account authenticates directly without token requirement
        email_active = self._unique_email("hr_active")
        register_user("HR Active", email_active, "ValidPassword10!", role="hr", allow_privileged=True, is_verified=1)

        login_res_active = self.client.post("/api/auth/login", json={
            "email": email_active,
            "password": "ValidPassword10!"
        })
        self.assertEqual(login_res_active.status_code, 200)
        self.assertTrue(login_res_active.get_json()["success"])

        # B. Deactivated HR account is rejected with 403 and is_deactivated=True
        email_deact = self._unique_email("hr_deactivated")
        register_user("HR Inactive", email_deact, "ValidPassword10!", role="hr", allow_privileged=True, is_verified=0)

        login_res_deact = self.client.post("/api/auth/login", json={
            "email": email_deact,
            "password": "ValidPassword10!"
        })
        self.assertEqual(login_res_deact.status_code, 403)
        self.assertFalse(login_res_deact.get_json()["success"])
        self.assertTrue(login_res_deact.get_json().get("is_deactivated"))

    # ============================================================
    # SEC-06: OPTIMIZE TOKEN LOOKUPS (DIRECT HASH QUERY)
    # ============================================================

    def test_10_valid_verification_token_succeeds(self):
        """SEC-06: Direct hash lookup verifies valid email token."""
        email = self._unique_email("tok_valid")
        reg = register_user("Token User", email, "ValidPassword10!", "candidate")
        token = reg["dev_verification_token"]

        res = verify_email_token(token)
        self.assertTrue(res["success"])

        # Check user is marked verified in DB
        with get_db() as conn:
            u = conn.execute("SELECT is_verified FROM users WHERE email=?", (email,)).fetchone()
            self.assertEqual(u["is_verified"], 1)

    def test_11_expired_verification_token_fails(self):
        """SEC-06: Direct hash lookup rejects expired verification token."""
        email = self._unique_email("tok_exp")
        reg = register_user("Expired Token User", email, "ValidPassword10!", "candidate")
        token = reg["dev_verification_token"]

        # Backdate token expiration
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
        with get_db() as conn:
            conn.execute("UPDATE email_verification_tokens SET expires_at=? WHERE user_id=?", (yesterday, reg["user"]["id"]))
            conn.commit()

        res = verify_email_token(token)
        self.assertFalse(res["success"])
        self.assertIn("invalid or expired", res["message"].lower())

    def test_12_used_verification_token_fails(self):
        """SEC-06: Direct hash lookup rejects already-used verification token."""
        email = self._unique_email("tok_used")
        reg = register_user("Used Token User", email, "ValidPassword10!", "candidate")
        token = reg["dev_verification_token"]

        # First use succeeds
        res1 = verify_email_token(token)
        self.assertTrue(res1["success"])

        # Second use fails
        res2 = verify_email_token(token)
        self.assertFalse(res2["success"])
        self.assertIn("invalid or expired", res2["message"].lower())

    def test_13_invalid_verification_token_fails(self):
        """SEC-06: Non-existent verification token fails immediately."""
        res = verify_email_token("completely_fake_token_that_does_not_exist_99999")
        self.assertFalse(res["success"])
        self.assertIn("invalid or expired", res["message"].lower())

    def test_14_valid_reset_token_succeeds(self):
        """SEC-06: Direct hash lookup verifies valid password reset token."""
        email = self._unique_email("reset_valid")
        register_user("Reset Valid User", email, "ValidPassword10!", "candidate")
        res_tok = generate_password_reset_token(email)
        token = res_tok["dev_reset_token"]

        res = reset_password_with_token(token, "BrandNewPassword10!")
        self.assertTrue(res["success"])

    def test_15_expired_reset_token_fails(self):
        """SEC-06: Direct hash lookup rejects expired password reset token."""
        email = self._unique_email("reset_exp")
        reg = register_user("Reset Exp User", email, "ValidPassword10!", "candidate")
        res_tok = generate_password_reset_token(email)
        token = res_tok["dev_reset_token"]

        # Backdate expiration
        past = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        with get_db() as conn:
            conn.execute("UPDATE password_reset_tokens SET expires_at=? WHERE user_id=?", (past, reg["user"]["id"]))
            conn.commit()

        res = reset_password_with_token(token, "BrandNewPassword10!")
        self.assertFalse(res["success"])
        self.assertIn("invalid or expired", res["message"].lower())

    def test_16_used_reset_token_fails(self):
        """SEC-06: Direct hash lookup rejects already-used password reset token."""
        email = self._unique_email("reset_used")
        register_user("Reset Used User", email, "ValidPassword10!", "candidate")
        res_tok = generate_password_reset_token(email)
        token = res_tok["dev_reset_token"]

        # First reset succeeds
        res1 = reset_password_with_token(token, "BrandNewPassword10!")
        self.assertTrue(res1["success"])

        # Second reset with same token fails
        res2 = reset_password_with_token(token, "AnotherPassword10!")
        self.assertFalse(res2["success"])
        self.assertIn("invalid or expired", res2["message"].lower())

    def test_17_token_indexes_exist_in_database(self):
        """SEC-06: Verifies that token_hash indexes exist in the active schema."""
        with get_db() as conn:
            indexes = [r[1] for r in conn.execute("SELECT type, name FROM sqlite_master WHERE type='index'").fetchall()]
            self.assertIn("idx_email_tokens_hash", indexes)
            self.assertIn("idx_reset_tokens_hash", indexes)

    def test_18_sqlite_compatibility_remains_intact(self):
        """SEC-06: Parameterized token queries execute cleanly on SQLite connection."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM email_verification_tokens WHERE token_hash=? AND is_used=0",
                ("dummy_hash",)
            ).fetchone()
            self.assertIsNone(row)

    # ============================================================
    # SEC-07: HTTP SECURITY HEADERS
    # ============================================================

    def test_19_x_frame_options_present(self):
        """SEC-07: X-Frame-Options: DENY is present on HTTP responses."""
        res = self.client.get("/")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")

    def test_20_x_content_type_options_present(self):
        """SEC-07: X-Content-Type-Options: nosniff is present on HTTP responses."""
        res = self.client.get("/")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")

    def test_21_referrer_policy_present(self):
        """SEC-07: Referrer-Policy: strict-origin-when-cross-origin is present on HTTP responses."""
        res = self.client.get("/")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

    def test_22_content_security_policy_present_and_safe(self):
        """SEC-07: Content-Security-Policy header is configured and permits required app CDNs."""
        res = self.client.get("/")
        csp = res.headers.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("https://cdnjs.cloudflare.com", csp)
        self.assertIn("https://fonts.googleapis.com", csp)
        self.assertIn("frame-ancestors 'none'", csp)


if __name__ == "__main__":
    unittest.main()
