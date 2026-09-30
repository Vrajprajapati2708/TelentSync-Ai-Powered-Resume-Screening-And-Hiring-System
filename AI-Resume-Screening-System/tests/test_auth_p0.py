# ============================================================
#  TalentSync — P0 Authentication Verification Test Suite
#  Built-in unittest runner for zero-dependency execution
# ============================================================

import unittest
import time
from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import (
    register_user, login_user, verify_email_token,
    generate_password_reset_token, reset_password_with_token
)
from app.utils.validators import MIN_PASSWORD_LENGTH


class TestAuthP0(unittest.TestCase):

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def get_unique_email(self, prefix="user"):
        return f"{prefix}_{int(time.time() * 1000)}@example.com"

    # ── 1. REGISTRATION TESTS ────────────────────────────────────

    def test_registration_valid(self):
        """Test registration with valid data creates unverified account with token."""
        email = self.get_unique_email("reg_valid")
        res = register_user("Valid User", email, "ValidPass10!", "candidate")
        self.assertTrue(res['success'])
        self.assertEqual(res['user']['is_verified'], 0)
        self.assertIn('dev_verification_token', res)
        self.assertGreater(len(res['dev_verification_token']), 20)

    def test_registration_duplicate_email(self):
        """Test registering duplicate email returns error."""
        email = self.get_unique_email("reg_dup")
        register_user("User One", email, "ValidPass10!", "candidate")
        res = register_user("User Two", email, "ValidPass10!", "candidate")
        self.assertFalse(res['success'])
        self.assertIn("already registered", res['message'].lower())

    def test_registration_invalid_role(self):
        """Test registering with unwhitelisted role is rejected."""
        email = self.get_unique_email("reg_role")
        res = register_user("Admin Pretender", email, "ValidPass10!", "superadmin")
        self.assertFalse(res['success'])
        self.assertIn("invalid role", res['message'].lower())

    def test_registration_weak_password(self):
        """Test password shorter than 10 characters is rejected."""
        email = self.get_unique_email("reg_weak")
        res = register_user("Short Pass", email, "Pass123", "candidate")
        self.assertFalse(res['success'])
        self.assertIn(f"at least {MIN_PASSWORD_LENGTH} characters", res['message'])

    # ── 2. EMAIL VERIFICATION TESTS ──────────────────────────────

    def test_email_verification_success(self):
        """Test valid verification token elevates is_verified to 1."""
        email = self.get_unique_email("ver_succ")
        reg = register_user("Verify User", email, "ValidPass10!", "candidate")
        token = reg['dev_verification_token']

        res = verify_email_token(token)
        self.assertTrue(res['success'])
        self.assertIn("verified successfully", res['message'].lower())

        with get_db() as conn:
            user = conn.execute("SELECT is_verified FROM users WHERE email=?", (email,)).fetchone()
            self.assertEqual(user['is_verified'], 1)

    def test_email_verification_used_token(self):
        """Test using the same verification token twice fails."""
        email = self.get_unique_email("ver_reuse")
        reg = register_user("Reuse User", email, "ValidPass10!", "candidate")
        token = reg['dev_verification_token']

        # First attempt
        res1 = verify_email_token(token)
        self.assertTrue(res1['success'])

        # Second attempt
        res2 = verify_email_token(token)
        self.assertFalse(res2['success'])
        self.assertIn("invalid or expired", res2['message'].lower())

    def test_email_verification_invalid_token(self):
        """Test junk verification token is rejected."""
        res = verify_email_token("junk_random_token_12345")
        self.assertFalse(res['success'])
        self.assertIn("invalid or expired", res['message'].lower())

    # ── 3. LOGIN & LOCKOUT TESTS ─────────────────────────────────

    def test_login_success(self):
        """Test login with correct credentials returns HTTP 200 and user object."""
        email = self.get_unique_email("login_ok")
        register_user("Login User", email, "ValidPass10!", "candidate", is_verified=1)

        r = self.client.post('/api/auth/login', json={'email': email, 'password': 'ValidPass10!'})
        self.assertEqual(r.status_code, 200)
        assert r.json is not None
        self.assertTrue(r.json['success'])
        self.assertEqual(r.json['user']['email'], email)
        self.assertNotIn('password', r.json['user'])

    def test_login_invalid_password(self):
        """Test login with wrong password returns HTTP 400."""
        email = self.get_unique_email("login_wrong")
        register_user("Wrong User", email, "ValidPass10!", "candidate")

        r = self.client.post('/api/auth/login', json={'email': email, 'password': 'WrongPassword10!'})
        self.assertEqual(r.status_code, 400)
        assert r.json is not None
        self.assertFalse(r.json['success'])

    def test_account_lockout_after_5_failures(self):
        """Test 5 consecutive failed logins trigger HTTP 423 Locked on 6th attempt."""
        email = self.get_unique_email("lockout")
        register_user("Lockout User", email, "ValidPass10!", "candidate")

        # Fail 5 times
        for _ in range(5):
            r = self.client.post('/api/auth/login', json={'email': email, 'password': 'WrongPassword10!'})
            self.assertEqual(r.status_code, 400)

        # 6th attempt must return 423 Locked
        r_locked = self.client.post('/api/auth/login', json={'email': email, 'password': 'ValidPass10!'})
        self.assertEqual(r_locked.status_code, 423)
        assert r_locked.json is not None
        self.assertTrue(r_locked.json['is_locked'])
        self.assertIn("account temporarily locked", r_locked.json['message'].lower())

    # ── 4. PASSWORD RESET TESTS ──────────────────────────────────

    def test_password_reset_flow(self):
        """Test end-to-end forgot password and reset password with token."""
        email = self.get_unique_email("reset_flow")
        register_user("Reset User", email, "OldPassword10!", "candidate", is_verified=1)

        # 1. Forgot password
        r_forgot = self.client.post('/api/auth/forgot_password', json={'email': email})
        self.assertEqual(r_forgot.status_code, 200)
        assert r_forgot.json is not None
        reset_token = r_forgot.json['dev_reset_token']
        self.assertIsNotNone(reset_token)

        # 2. Reset password
        r_reset = self.client.post('/api/auth/reset_password', json={
            'token': reset_token,
            'new_password': 'NewPassword10!'
        })
        self.assertEqual(r_reset.status_code, 200)
        assert r_reset.json is not None
        self.assertTrue(r_reset.json['success'])

        # 3. Old password should fail
        r_old = self.client.post('/api/auth/login', json={'email': email, 'password': 'OldPassword10!'})
        self.assertEqual(r_old.status_code, 400)

        # 4. New password should succeed
        r_new = self.client.post('/api/auth/login', json={'email': email, 'password': 'NewPassword10!'})
        self.assertEqual(r_new.status_code, 200)

    def test_password_reset_token_single_use(self):
        """Test used password reset token cannot be reused."""
        email = self.get_unique_email("reset_reuse")
        register_user("Reuse Reset User", email, "OldPassword10!", "candidate")

        r_forgot = self.client.post('/api/auth/forgot_password', json={'email': email})
        assert r_forgot.json is not None
        reset_token = r_forgot.json['dev_reset_token']

        # Use once
        self.client.post('/api/auth/reset_password', json={'token': reset_token, 'new_password': 'NewPassword10!'})

        # Try using again
        r_reuse = self.client.post('/api/auth/reset_password', json={'token': reset_token, 'new_password': 'AnotherPassword10!'})
        self.assertEqual(r_reuse.status_code, 400)
        assert r_reuse.json is not None
        self.assertIn("invalid or expired", r_reuse.json['message'].lower())

    def test_password_reset_weak_new_password(self):
        """Test resetting password with less than 10 chars is rejected."""
        email = self.get_unique_email("reset_weak")
        register_user("Weak Reset User", email, "OldPassword10!", "candidate")

        r_forgot = self.client.post('/api/auth/forgot_password', json={'email': email})
        assert r_forgot.json is not None
        reset_token = r_forgot.json['dev_reset_token']

        r_weak = self.client.post('/api/auth/reset_password', json={'token': reset_token, 'new_password': 'Short7!'})
        self.assertEqual(r_weak.status_code, 400)
        assert r_weak.json is not None
        self.assertIn(f"at least {MIN_PASSWORD_LENGTH} characters", r_weak.json['message'])

    # ── 5. SESSION TESTS ─────────────────────────────────────────

    def test_session_logout(self):
        """Test logout clears user session."""
        email = self.get_unique_email("session_user")
        register_user("Session User", email, "ValidPass10!", "candidate", is_verified=1)

        # Login
        self.client.post('/api/auth/login', json={'email': email, 'password': 'ValidPass10!'})

        # Verify authenticated
        r_me = self.client.get('/api/auth/me')
        self.assertEqual(r_me.status_code, 200)

        # Logout
        r_out = self.client.post('/api/auth/logout')
        self.assertEqual(r_out.status_code, 200)

        # Verify unauthenticated
        r_me_after = self.client.get('/api/auth/me')
        self.assertEqual(r_me_after.status_code, 401)


if __name__ == '__main__':
    unittest.main()
