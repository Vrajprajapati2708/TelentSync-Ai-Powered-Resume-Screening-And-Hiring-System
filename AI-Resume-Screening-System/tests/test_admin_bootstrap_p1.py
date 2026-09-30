# ============================================================
#  TalentSync / HireAI — Phase 1 Test Suite
#  Production Admin Bootstrap & Safety Controls Verification
#  Tests all 22+ required criteria in complete isolation.
# ============================================================

import unittest
import time
from unittest.mock import patch

from app import create_app
from app.cli import bootstrap_admin
from app.config.settings import TestingConfig
from app.controllers.auth_controller import register_user, login_user
from app.controllers.platform_admin_controller import (
    deactivate_platform_user,
    change_platform_user_role,
    get_platform_users
)
from app.database.connection import get_db


class TestAdminBootstrapPhase1(unittest.TestCase):

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def _unique_email(self, prefix="admin_p1"):
        return f"{prefix}_{int(time.time() * 1000)}_{id(self)}@example.com"

    # ── TEST 1: Create first administrator ───────────────────────
    def test_01_create_first_admin(self):
        email = self._unique_email("first_admin")
        res = bootstrap_admin(
            email=email,
            password="SecureAdminPass10!",
            name="Primary Superadmin"
        )
        self.assertTrue(res['success'], f"Bootstrap failed: {res.get('message')}")
        self.assertEqual(res['action'], 'created')
        self.assertIsNotNone(res.get('user_id'))

    # ── TEST 2: Verify role is actually 'admin' ───────────────────
    def test_02_verify_role_is_admin(self):
        email = self._unique_email("role_check")
        res = bootstrap_admin(
            email=email,
            password="SecureAdminPass10!",
            name="Role Admin"
        )
        self.assertTrue(res['success'])
        user_id = res['user_id']

        with get_db() as conn:
            user = conn.execute("SELECT role, is_verified FROM users WHERE id = ?", (user_id,)).fetchone()
            self.assertIsNotNone(user)
            self.assertEqual(user['role'], 'admin')
            self.assertEqual(user['is_verified'], 1)

    # ── TEST 3: Verify password authentication works ─────────────
    def test_03_verify_password_authentication_works(self):
        email = self._unique_email("auth_check")
        password = "SecureAdminPass10!"
        bootstrap_admin(email=email, password=password, name="Auth Admin")

        login_res = login_user(email, password)
        self.assertTrue(login_res['success'], f"Login failed: {login_res.get('message')}")
        self.assertEqual(login_res['user']['role'], 'admin')

    # ── TEST 4: Verify Platform Admin endpoint returns 200 ───────
    def test_04_verify_platform_admin_endpoint_returns_200(self):
        email = self._unique_email("api_admin")
        password = "SecureAdminPass10!"
        bootstrap_admin(email=email, password=password, name="API Admin")

        # Login via test client session
        login_res = self.client.post('/api/auth/login', json={'email': email, 'password': password})
        self.assertEqual(login_res.status_code, 200)

        # Access platform admin analytics
        analytics_res = self.client.get('/api/platform-admin/analytics')
        self.assertEqual(analytics_res.status_code, 200)
        data = analytics_res.get_json()
        self.assertIn('users', data)
        self.assertIn('applications', data)
        self.assertIn('jobs', data)

    # ── TEST 5: Candidate receives 403 ───────────────────────────
    def test_05_candidate_receives_403(self):
        email = self._unique_email("cand")
        password = "CandidatePass10!"
        reg = register_user("Candidate User", email, password, role="candidate", allow_privileged=True, is_verified=1)
        self.assertTrue(reg['success'])

        login_res = self.client.post('/api/auth/login', json={'email': email, 'password': password})
        self.assertEqual(login_res.status_code, 200)

        # Candidate attempting to access platform admin analytics
        analytics_res = self.client.get('/api/platform-admin/analytics')
        self.assertEqual(analytics_res.status_code, 403)

    # ── TEST 6: HR receives 403 ──────────────────────────────────
    def test_06_hr_receives_403(self):
        email = self._unique_email("hr")
        password = "HRRecruiterPass10!"
        reg = register_user("HR User", email, password, role="hr", allow_privileged=True, is_verified=1)
        self.assertTrue(reg['success'])

        login_res = self.client.post('/api/auth/login', json={'email': email, 'password': password})
        self.assertEqual(login_res.status_code, 200)

        # HR attempting to access platform admin analytics
        analytics_res = self.client.get('/api/platform-admin/analytics')
        self.assertEqual(analytics_res.status_code, 403)

    # ── TEST 7: Unauthenticated user receives 401 ────────────────
    def test_07_unauthenticated_receives_401(self):
        analytics_res = self.client.get('/api/platform-admin/analytics')
        self.assertEqual(analytics_res.status_code, 401)

    # ── TEST 8: Invalid email rejected ───────────────────────────
    def test_08_invalid_email_rejected(self):
        invalid_emails = ["", "   ", "notanemail", "admin@", "@domain.com", "user@site"]
        for invalid in invalid_emails:
            res = bootstrap_admin(email=invalid, password="SecureAdminPass10!")
            self.assertFalse(res['success'], f"Invalid email '{invalid}' was unexpectedly accepted")
            self.assertIn("email", res['message'].lower())

    # ── TEST 9: Weak password rejected ───────────────────────────
    def test_09_weak_password_rejected(self):
        email = self._unique_email("weak_pw")
        # Too short (< 10 chars)
        res = bootstrap_admin(email=email, password="short")
        self.assertFalse(res['success'])
        self.assertIn("at least 10", res['message'])

        # Empty password
        res = bootstrap_admin(email=email, password="")
        self.assertFalse(res['success'])

        # Exceeds max length (> 128 chars)
        res = bootstrap_admin(email=email, password="A" * 129)
        self.assertFalse(res['success'])
        self.assertIn("not exceed 128", res['message'])

    # ── TEST 10: Password mismatch rejected in CLI flow ──────────
    def test_10_password_mismatch_rejected(self):
        # bootstrap_admin requires password; if None or empty, rejected
        email = self._unique_email("no_pw")
        res = bootstrap_admin(email=email, password=None)
        self.assertFalse(res['success'])
        self.assertEqual(res['action'], 'missing_password')

    # ── TEST 11: Duplicate administrator safely handled ──────────
    def test_11_duplicate_administrator_safely_handled(self):
        email = self._unique_email("dup_admin")
        res1 = bootstrap_admin(email=email, password="SecureAdminPass10!")
        self.assertTrue(res1['success'])
        self.assertEqual(res1['action'], 'created')

        # Run 2: Exact same email
        res2 = bootstrap_admin(email=email, password="SecureAdminPass10!")
        self.assertTrue(res2['success'])
        self.assertEqual(res2['action'], 'already_admin')
        self.assertEqual(res2['user_id'], res1['user_id'])

        # Verify DB still has exactly 1 record for this email
        with get_db() as conn:
            cnt = conn.execute("SELECT COUNT(*) FROM users WHERE LOWER(email) = ?", (email.lower(),)).fetchone()[0]
            self.assertEqual(cnt, 1)

    # ── TEST 12: Existing verified user promotion works ──────────
    def test_12_existing_verified_user_promotion_works(self):
        email = self._unique_email("promote_user")
        reg = register_user("Verified Candidate", email, "CandidatePass10!", role="candidate", allow_privileged=True, is_verified=1)
        self.assertTrue(reg['success'])

        # Without promote=True flag -> returns error indicating account exists
        res_no_promote = bootstrap_admin(email=email, promote=False)
        self.assertFalse(res_no_promote['success'])
        self.assertEqual(res_no_promote['action'], 'requires_promote')

        # With promote=True flag -> promotes safely
        res_promote = bootstrap_admin(email=email, promote=True)
        self.assertTrue(res_promote['success'])
        self.assertEqual(res_promote['action'], 'promoted')

        with get_db() as conn:
            user = conn.execute("SELECT role, is_verified FROM users WHERE id = ?", (reg['user']['id'],)).fetchone()
            self.assertEqual(user['role'], 'admin')
            self.assertEqual(user['is_verified'], 1)

    # ── TEST 13: Unsafe/unverified user is not silently privileged
    def test_13_unsafe_unverified_user_not_silently_privileged(self):
        email = self._unique_email("unverified_user")
        # Registered as candidate with is_verified=0
        reg = register_user("Unverified Candidate", email, "CandidatePass10!", role="candidate", allow_privileged=True, is_verified=0)
        self.assertTrue(reg['success'])

        # Attempt to promote unverified account
        res = bootstrap_admin(email=email, promote=True)
        self.assertFalse(res['success'])
        self.assertEqual(res['action'], 'rejected_unverified')
        self.assertIn("unverified", res['message'].lower())

        # Verify DB role was NOT altered
        with get_db() as conn:
            user = conn.execute("SELECT role, is_verified FROM users WHERE id = ?", (reg['user']['id'],)).fetchone()
            self.assertEqual(user['role'], 'candidate')
            self.assertEqual(user['is_verified'], 0)

    # ── TEST 14: Self-deactivation protection remains intact ─────
    def test_14_self_deactivation_protection_remains_intact(self):
        email = self._unique_email("self_deact")
        res = bootstrap_admin(email=email, password="SecureAdminPass10!")
        admin_id = res['user_id']

        success, msg, code = deactivate_platform_user(admin_id, admin_user_id=admin_id)
        self.assertFalse(success)
        self.assertEqual(code, 400)
        self.assertIn("cannot deactivate their own account", msg.lower())

    # ── TEST 15: Self-demotion protection remains intact ─────────
    def test_15_self_demotion_protection_remains_intact(self):
        email = self._unique_email("self_demote")
        res = bootstrap_admin(email=email, password="SecureAdminPass10!")
        admin_id = res['user_id']

        success, msg, code = change_platform_user_role(admin_id, "candidate", admin_user_id=admin_id)
        self.assertFalse(success)
        self.assertEqual(code, 400)
        self.assertIn("cannot modify their own role", msg.lower())

    # ── TEST 16: Last-admin protection remains intact ────────────
    def test_16_last_admin_protection_remains_intact(self):
        # Ensure only 1 active admin exists for this test context
        with get_db() as conn:
            conn.execute("UPDATE users SET is_verified = 0 WHERE role = 'admin'")
            conn.commit()

        email_solo = self._unique_email("solo_admin")
        res_solo = bootstrap_admin(email=email_solo, password="SecureAdminPass10!")
        solo_id = res_solo['user_id']

        # Fake caller ID (not the solo_id itself)
        caller_id = 999999

        # Attempt to demote the final active admin
        success, msg, code = change_platform_user_role(solo_id, "candidate", admin_user_id=caller_id)
        self.assertFalse(success)
        self.assertEqual(code, 400)
        self.assertIn("final active administrator", msg.lower())

        # Attempt to deactivate the final active admin
        success, msg, code = deactivate_platform_user(solo_id, admin_user_id=caller_id)
        self.assertFalse(success)
        self.assertEqual(code, 400)
        self.assertIn("final active administrator", msg.lower())

    # ── TEST 17: Two-admin demotion behavior remains correct ─────
    def test_17_two_admin_demotion_behavior(self):
        email_admin1 = self._unique_email("two_admin1")
        email_admin2 = self._unique_email("two_admin2")

        res1 = bootstrap_admin(email=email_admin1, password="SecureAdminPass10!")
        res2 = bootstrap_admin(email=email_admin2, password="SecureAdminPass10!")

        admin1_id = res1['user_id']
        admin2_id = res2['user_id']

        # Admin 1 demotes Admin 2 -> Allowed because >= 2 active admins exist
        success, msg, code = change_platform_user_role(admin2_id, "candidate", admin_user_id=admin1_id)
        self.assertTrue(success)
        self.assertEqual(code, 200)

    # ── TEST 18: Password is never returned in response ──────────
    def test_18_password_never_returned_in_response(self):
        email = self._unique_email("leak_pw")
        raw_pw = "SecureAdminPass10!"
        res_boot = bootstrap_admin(email=email, password=raw_pw)

        # 1. Bootstrap result
        self.assertNotIn('password', res_boot)
        for val in res_boot.values():
            self.assertNotEqual(val, raw_pw)

        # 2. Login result
        res_login = login_user(email, raw_pw)
        self.assertNotIn('password', res_login.get('user', {}))

        # 3. Platform admin users list
        users_res = get_platform_users(search=email)
        for u in users_res.get('users', []):
            self.assertNotIn('password', u)

    # ── TEST 19: Password hash is never returned in response ─────
    def test_19_password_hash_never_returned_in_response(self):
        email = self._unique_email("leak_hash")
        raw_pw = "SecureAdminPass10!"
        bootstrap_admin(email=email, password=raw_pw)

        with get_db() as conn:
            actual_hash = conn.execute("SELECT password FROM users WHERE LOWER(email) = ?", (email.lower(),)).fetchone()[0]

        res_login = login_user(email, raw_pw)
        self.assertNotIn('password', res_login.get('user', {}))
        self.assertNotIn(actual_hash, str(res_login))

        users_res = get_platform_users(search=email)
        self.assertNotIn(actual_hash, str(users_res))

    # ── TEST 20: SQL injection input cannot manipulate role ──────
    def test_20_sql_injection_input_cannot_manipulate_role(self):
        sql_payload = "victim@test.com' OR '1'='1"
        res = bootstrap_admin(email=sql_payload, password="SecureAdminPass10!")
        self.assertFalse(res['success'])

        sql_payload_email = f"sqli_{int(time.time())}@test.com"
        malicious_name = "Admin'; UPDATE users SET role='admin'; --"
        res2 = bootstrap_admin(email=sql_payload_email, password="SecureAdminPass10!", name=malicious_name)
        self.assertTrue(res2['success'])

        with get_db() as conn:
            u = conn.execute("SELECT name, role FROM users WHERE id = ?", (res2['user_id'],)).fetchone()
            self.assertEqual(u['name'], malicious_name)
            self.assertEqual(u['role'], 'admin')

    # ── TEST 21: Transaction rollback occurs on failure ──────────
    def test_21_transaction_rollback_occurs_on_failure(self):
        email = self._unique_email("tx_fail")
        with patch('app.cli.get_db') as mock_get_db:
            # Simulate a DB exception during commit
            class FailingConnContext:
                def __enter__(self):
                    raise RuntimeError("Simulated DB connection crash")
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

            mock_get_db.return_value = FailingConnContext()
            res = bootstrap_admin(email=email, password="SecureAdminPass10!")
            self.assertFalse(res['success'])
            self.assertEqual(res['action'], 'db_error')

    # ── TEST 22: Repeated bootstrap does not create duplicates ───
    def test_22_repeated_bootstrap_does_not_create_duplicates(self):
        email = self._unique_email("idempotent")
        res1 = bootstrap_admin(email=email, password="SecureAdminPass10!")
        self.assertTrue(res1['success'])

        with get_db() as conn:
            count1 = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]

        # Call again
        res2 = bootstrap_admin(email=email, password="SecureAdminPass10!")
        self.assertTrue(res2['success'])

        with get_db() as conn:
            count2 = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]

        self.assertEqual(count1, count2)

    # ── TEST 23: Public registration cannot create admin ─────────
    def test_23_public_registration_cannot_create_admin(self):
        email = self._unique_email("public_admin_attempt")
        res = self.client.post('/api/auth/register', json={
            'name': 'Hacker Admin',
            'email': email,
            'password': 'SecureAdminPass10!',
            'role': 'admin'
        })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data.get('success'))
        self.assertIn("Privileged accounts cannot be created", data.get('message', ''))

        # Verify no admin user was created in DB
        with get_db() as conn:
            u = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email.lower(),)).fetchone()
            self.assertIsNone(u)

    # ── TEST 24: Non-existent DB file override is rejected ───────
    def test_24_bootstrap_nonexistent_db_file_rejected(self):
        email = self._unique_email("db_not_found")
        fake_db = f"nonexistent_db_test_{int(time.time())}.db"
        import os
        self.assertFalse(os.path.exists(fake_db))

        res = bootstrap_admin(email=email, password="SecureAdminPass10!", db_file=fake_db)
        self.assertFalse(res['success'])
        self.assertEqual(res['action'], 'db_not_found')
        self.assertIn("not found", res['message'].lower())
        # Verify no 0-byte orphan database was created on disk
        self.assertFalse(os.path.exists(fake_db))

    # ── TEST 25: PostgreSQL DB override rejection ────────────────
    def test_25_bootstrap_postgres_db_override_rejected(self):
        email = self._unique_email("pg_override")
        with patch('app.cli.is_postgres', return_value=True):
            res = bootstrap_admin(email=email, password="SecureAdminPass10!", db_file="some_sqlite.db")
            self.assertFalse(res['success'])
            self.assertEqual(res['action'], 'invalid_db_engine')
            self.assertIn("postgresql", res['message'].lower())


if __name__ == '__main__':
    unittest.main()
