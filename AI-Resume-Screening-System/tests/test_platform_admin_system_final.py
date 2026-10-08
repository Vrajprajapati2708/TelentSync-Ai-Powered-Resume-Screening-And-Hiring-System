import unittest
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from werkzeug.security import generate_password_hash


class PlatformAdminSystemFinalTestCase(unittest.TestCase):
    """
    Comprehensive verification of Platform Admin System Health, Integrations,
    Telemetric Latency Benchmarking, Master Exports, and Security Guardrails.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # Seed test actors
        self.admin_id, self.admin_email = self._create_user("Admin System", "admin", is_verified=1)
        self.recruiter_id, self.recruiter_email = self._create_user("HR System", "hr", is_verified=1)
        self.candidate_id, self.candidate_email = self._create_user("Candidate System", "candidate", is_verified=1, ats_score=85)

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

    def _login(self, user_id: int):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['_fresh'] = True

    # ─────────────────────────────────────────────────────────────
    # 1. System Health Probes & Telemetry
    # ─────────────────────────────────────────────────────────────

    def test_get_system_health_success(self):
        """Admin can probe system health and receive 8 core subsystems with latency telemetry."""
        self._login(self.admin_id)
        res = self.client.get('/api/platform-admin/system/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))

        payload = data.get('data') or data
        self.assertIn('overall', payload)
        self.assertIn(payload['overall'], {'Healthy', 'Degraded', 'Unavailable'})
        self.assertIn('healthy_count', payload)
        self.assertIn('total_services', payload)
        self.assertIn('timestamp', payload)

        services = payload.get('services', {})
        expected_keys = {'database', 'file_storage', 'authentication', 'resume_parser', 'ats_engine', 'job_matcher', 'adzuna', 'email'}
        self.assertEqual(set(services.keys()), expected_keys)

        for key, s in services.items():
            self.assertIn('name', s)
            self.assertIn('status', s)
            self.assertIn('details', s)
            self.assertIn(s['status'], {'Healthy', 'Degraded', 'Unavailable', 'Not Configured'})

        # Database latency probe check
        self.assertIsNotNone(services['database'].get('latency_ms'))
        self.assertGreaterEqual(services['database']['latency_ms'], 0.0)

    # ─────────────────────────────────────────────────────────────
    # 2. Integrations Inventory & Zero Secret Leakage
    # ─────────────────────────────────────────────────────────────

    def test_get_system_integrations_security(self):
        """Integrations endpoint lists operational status with strict secret masking."""
        self._login(self.admin_id)
        res = self.client.get('/api/platform-admin/system/integrations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))

        integrations = (data.get('data') and data['data'].get('integrations')) or data.get('integrations', [])
        self.assertGreaterEqual(len(integrations), 4)

        names = [item['name'] for item in integrations]
        self.assertTrue(any('Adzuna' in n for n in names))
        self.assertTrue(any('Email' in n for n in names))
        self.assertTrue(any('OCR' in n or 'Optical' in n for n in names))
        self.assertTrue(any('ML' in n or 'Intelligence' in n for n in names))

        # Check strict zero secrets
        for item in integrations:
            self.assertIn('configured', item)
            self.assertIn('status', item)
            dumped = json.dumps(item).lower()
            self.assertNotIn('secret_key', dumped)
            self.assertNotIn('api_key', dumped)
            self.assertNotIn('app_key', dumped)
            self.assertNotIn('password', dumped)

    # ─────────────────────────────────────────────────────────────
    # 3. Platform Data Exports (JSON & Multi-Type CSV)
    # ─────────────────────────────────────────────────────────────

    def test_export_platform_data_json(self):
        """Admin can export entire platform state in JSON format."""
        self._login(self.admin_id)
        res = self.client.get('/api/platform-admin/export?format=json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/json')
        self.assertIn('attachment', res.headers.get('Content-Disposition', ''))

    def test_export_platform_data_csv_types(self):
        """Admin can export specific entities (all, users, jobs, applications, audit) in CSV format."""
        self._login(self.admin_id)
        for exp_type in ('all', 'users', 'jobs', 'applications', 'audit'):
            res = self.client.get(f'/api/platform-admin/export?format=csv&type={exp_type}')
            self.assertEqual(res.status_code, 200, f"Export failed for type={exp_type}")
            self.assertEqual(res.mimetype, 'text/csv')
            self.assertIn(f'talentsync_platform_export_{exp_type}', res.headers.get('Content-Disposition', ''))
            content = res.get_data(as_text=True)
            self.assertTrue(len(content) > 0)

    def test_export_invalid_format_or_type(self):
        """Export rejects invalid formats or unrecognized types."""
        self._login(self.admin_id)
        res_bad_fmt = self.client.get('/api/platform-admin/export?format=xml')
        self.assertEqual(res_bad_fmt.status_code, 400)

        res_bad_type = self.client.get('/api/platform-admin/export?format=csv&type=hack')
        self.assertEqual(res_bad_type.status_code, 400)

    # ─────────────────────────────────────────────────────────────
    # 4. Security & Role-Based Access Control (RBAC)
    # ─────────────────────────────────────────────────────────────

    def test_unauthenticated_access_denied(self):
        """Unauthenticated requests are rejected."""
        with self.client.session_transaction() as sess:
            sess.clear()

        for endpoint in ('/api/platform-admin/system/health', '/api/platform-admin/system/integrations', '/api/platform-admin/export'):
            res = self.client.get(endpoint)
            self.assertIn(res.status_code, {302, 401, 403})

    def test_non_admin_roles_forbidden(self):
        """Recruiters and candidates are strictly forbidden from accessing system health and exports."""
        for uid in (self.recruiter_id, self.candidate_id):
            self._login(uid)
            res_h = self.client.get('/api/platform-admin/system/health')
            self.assertEqual(res_h.status_code, 403)

            res_i = self.client.get('/api/platform-admin/system/integrations')
            self.assertEqual(res_i.status_code, 403)

            res_e = self.client.get('/api/platform-admin/export')
            self.assertEqual(res_e.status_code, 403)


if __name__ == '__main__':
    unittest.main()
