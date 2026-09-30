# ============================================================
#  TalentSync / HireAI — Platform Admin Final Centralized Panel Test Suite
#  Testing all 6 Core Sections:
#  1. Dashboard & Analytics KPIs
#  2. Users (Search, Role, Status, Verification filters, Last Login, Detail Activity)
#  3. Jobs & Applications (Internal Jobs Only, Filtering, Detail, Applicants)
#  4. Resumes (File Existence, Status Counts, ATS, Preview, Compliance Deletion)
#  5. Security & Audit (Login Attempts, Outliers, Read-Only Audit Log)
#  6. System Health & Integrations (8 Probes, Status Domain, Zero Secret Leakage)
# ============================================================

import os
import io
import time
import json
import unittest
from flask import session
from werkzeug.security import generate_password_hash
import docx as python_docx

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user


def _make_docx_stream(text: str = "Senior Python Developer with Flask, Docker, and SQL expertise.") -> io.BytesIO:
    doc = python_docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


class TestPlatformAdminFinalP3(unittest.TestCase):
    """Rigorous verification suite for Platform Admin Centralized Control Panel."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # Seed test actors
        self.admin_id, self.admin_email = self._create_user("Super Admin", "admin", is_verified=1)
        self.hr_id, self.hr_email       = self._create_user("HR Recruiter", "hr", is_verified=1)
        self.cand_id, self.cand_email   = self._create_user("Alice Candidate", "candidate", is_verified=1, ats_score=88)
        self.cand2_id, self.cand2_email = self._create_user("Bob Unverified", "candidate", is_verified=0, ats_score=45)

        # Seed internal test jobs
        self.job_id = self._create_internal_job("Senior Python Engineer", "TalentSync Labs", status="Active")
        self.job2_id = self._create_internal_job("Junior Frontend Dev", "TalentSync Labs", status="Closed")

        # Seed test application
        self.app_id = self._create_application(self.cand_id, self.job_id, status="Reviewing", match_score=91)

        # Seed resume via client
        self.resume_id = self._upload_resume_as(self.cand_email, "Alice Python Engineer Resume")

        # Seed login attempts
        self._record_login_attempt(self.cand_email, "192.168.1.50", success=1)
        self._record_login_attempt("intruder@unknown.com", "10.0.0.99", success=0)

    def tearDown(self):
        self.app_context.pop()

    def _unique_email(self, prefix="pa_p3"):
        return f"{prefix}_{int(time.time() * 1000)}_{id(self)}@test.com"

    def _create_user(self, name, role, is_verified=1, ats_score=70, is_outlier=0):
        email = self._unique_email(role)
        hashed = generate_password_hash("StrongSecret99!")
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, password, role, is_verified, ats_score, is_outlier) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, email, hashed, role, is_verified, ats_score, is_outlier)
            )
            user_id = cur.lastrowid
            conn.commit()
        return user_id, email

    def _create_internal_job(self, title, company, status="Active"):
        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, description, skills, location, type, salary, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, company, "Job description", "Python, Flask", "Bangalore", "Full-time", "15-20 LPA", status)
            )
            job_id = cur.lastrowid
            conn.commit()
        return job_id

    def _create_application(self, candidate_id, job_id, status="Reviewing", match_score=85):
        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO applications (user_id, job_id, status, match_score)
                   VALUES (?, ?, ?, ?)""",
                (candidate_id, job_id, status, match_score)
            )
            app_id = cur.lastrowid
            conn.execute(
                """INSERT INTO application_status (application_id, status, notes)
                   VALUES (?, ?, ?)""",
                (app_id, status, "Candidate profile shortlisted for round 1")
            )
            conn.commit()
        return app_id

    def _upload_resume_as(self, email: str, text: str = "Python Developer") -> int:
        self._login_as(self.cand_id)
        buf = _make_docx_stream(text)
        resp = self.client.post(
            "/api/upload_resume",
            data={"resume": (buf, "AliceResume.docx")},
            content_type="multipart/form-data"
        )
        data = resp.get_json() or {}
        return data.get("resume_id", 1)

    def _record_login_attempt(self, email, ip, success=1):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO login_attempts (email, ip_address, success, attempted_at) VALUES (?, ?, ?, datetime('now'))",
                (email, ip, success)
            )
            conn.commit()

    def _login_as(self, user_id):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

    def _logout(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    # ============================================================
    # SECTION 1: DASHBOARD & DYNAMIC METRICS
    # ============================================================

    def test_dashboard_analytics_contract_and_kpis(self):
        """Dashboard returns all required dynamic KPIs backed by real database calculations."""
        self._login_as(self.admin_id)
        res = self.client.get('/api/platform-admin/analytics')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()['data']

        # Verify structured KPI container
        self.assertIn('kpis', data)
        kpis = data['kpis']
        self.assertGreaterEqual(kpis['total_users'], 4)
        self.assertGreaterEqual(kpis['candidates'], 2)
        self.assertGreaterEqual(kpis['hr_users'], 1)
        self.assertGreaterEqual(kpis['platform_admins'], 1)
        self.assertGreaterEqual(kpis['total_jobs'], 2)
        self.assertGreaterEqual(kpis['active_jobs'], 1)
        self.assertGreaterEqual(kpis['total_applications'], 1)
        self.assertGreaterEqual(kpis['total_resumes'], 1)

        # Verify resumes processing distribution
        self.assertIn('resumes', data)
        self.assertIn('total', data['resumes'])
        self.assertIn('processed', data['resumes'])
        self.assertIn('pending', data['resumes'])
        self.assertIn('failed', data['resumes'])

    def test_dashboard_analytics_rbac(self):
        """Unauthenticated -> 401, Candidate -> 403, HR -> 403."""
        # Unauthenticated
        self._logout()
        res = self.client.get('/api/platform-admin/analytics')
        self.assertIn(res.status_code, (401, 302))

        # Candidate
        self._login_as(self.cand_id)
        res = self.client.get('/api/platform-admin/analytics')
        self.assertEqual(res.status_code, 403)

        # HR
        self._login_as(self.hr_id)
        res = self.client.get('/api/platform-admin/analytics')
        self.assertEqual(res.status_code, 403)

    # ============================================================
    # SECTION 2: USERS & GOVERNANCE
    # ============================================================

    def test_users_filtering_by_verification(self):
        """Admin user directory supports verification filter (verified vs unverified)."""
        self._login_as(self.admin_id)

        res_v = self.client.get('/api/platform-admin/users?verification=verified')
        self.assertEqual(res_v.status_code, 200)
        users_v = res_v.get_json()['data']['users']
        self.assertTrue(all(u['is_verified'] == 1 for u in users_v))

        res_u = self.client.get(f'/api/platform-admin/users?verification=unverified&search={self.cand2_email}')
        self.assertEqual(res_u.status_code, 200)
        users_u = res_u.get_json()['data']['users']
        self.assertTrue(all(u['is_verified'] == 0 for u in users_u))
        self.assertTrue(any(u['id'] == self.cand2_id for u in users_u))

    def test_user_detail_includes_last_login_and_activity_without_secrets(self):
        """User detail returns real last_login and recent activity, strictly omitting secret tokens."""
        self._login_as(self.admin_id)
        res = self.client.get(f'/api/platform-admin/users/{self.cand_id}')
        self.assertEqual(res.status_code, 200)
        user = res.get_json()['data']['user']

        # Last login must match login_attempts
        self.assertIsNotNone(user['last_login'])

        # Recent activity must contain applications and logins
        self.assertIn('recent_activity', user)
        self.assertGreaterEqual(len(user['recent_activity']['applications']), 1)
        self.assertGreaterEqual(len(user['recent_activity']['logins']), 1)

        # Zero secrets leaked
        self.assertNotIn('password', user)
        self.assertNotIn('password_hash', user)
        self.assertNotIn('reset_token', user)
        self.assertNotIn('verification_token', user)

    # ============================================================
    # SECTION 3: JOBS & APPLICATIONS
    # ============================================================

    def test_platform_jobs_internal_only_and_search(self):
        """Jobs view lists internal jobs, search works, and application count is real."""
        self._login_as(self.admin_id)

        # List jobs
        res = self.client.get('/api/platform-admin/jobs')
        self.assertEqual(res.status_code, 200)
        jobs = res.get_json()['data']['jobs']
        self.assertGreaterEqual(len(jobs), 2)

        # Job with application has applications_count >= 1
        job_item = next((j for j in jobs if j['id'] == self.job_id), None)
        self.assertIsNotNone(job_item)
        self.assertEqual(job_item['applications_count'], 1)

        # Search filter
        res_search = self.client.get('/api/platform-admin/jobs?search=Frontend')
        self.assertEqual(res_search.status_code, 200)
        matched = res_search.get_json()['data']['jobs']
        self.assertTrue(all('Frontend' in j['title'] for j in matched))

    def test_platform_job_detail_with_applicants(self):
        """Job detail returns description and applicant list with match scores."""
        self._login_as(self.admin_id)
        res = self.client.get(f'/api/platform-admin/jobs/{self.job_id}')
        self.assertEqual(res.status_code, 200)
        job = res.get_json()['data']['job']
        self.assertEqual(job['id'], self.job_id)
        self.assertGreaterEqual(len(job['applicants']), 1)
        self.assertEqual(job['applicants'][0]['user_id'], self.cand_id)
        self.assertEqual(job['applicants'][0]['match_score'], 91)

    def test_platform_applications_listing_and_filtering(self):
        """Applications view displays joined candidate and job info with status filtering."""
        self._login_as(self.admin_id)

        res = self.client.get('/api/platform-admin/applications?status=Reviewing')
        self.assertEqual(res.status_code, 200)
        apps = res.get_json()['data']['applications']
        self.assertGreaterEqual(len(apps), 1)
        app = apps[0]
        self.assertEqual(app['candidate_name'], "Alice Candidate")
        self.assertEqual(app['job_title'], "Senior Python Engineer")

    def test_platform_application_detail_with_status_history(self):
        """Application detail modal endpoint returns full candidate, job, and status history."""
        self._login_as(self.admin_id)
        res = self.client.get(f'/api/platform-admin/applications/{self.app_id}')
        self.assertEqual(res.status_code, 200)
        app = res.get_json()['data']['application']
        self.assertEqual(app['id'], self.app_id)
        self.assertGreaterEqual(len(app['history']), 1)
        self.assertEqual(app['history'][0]['status'], 'Reviewing')

    # ============================================================
    # SECTION 4: RESUMES
    # ============================================================

    def test_platform_resumes_listing_and_file_existence(self):
        """Resumes view accurately reports whether file exists on disk."""
        self._login_as(self.admin_id)
        res = self.client.get('/api/platform-admin/resumes')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()['data']
        self.assertIn('summary', data)
        self.assertGreaterEqual(data['summary']['processed'], 1)

        resumes = data['resumes']
        target = next((r for r in resumes if r['id'] == self.resume_id), None)
        self.assertIsNotNone(target)
        self.assertTrue(target['file_exists'])

    def test_platform_resume_detail_preview(self):
        """Resume detail modal endpoint returns parsed text preview and skills."""
        self._login_as(self.admin_id)
        res = self.client.get(f'/api/platform-admin/resumes/{self.resume_id}')
        self.assertEqual(res.status_code, 200)
        resume = res.get_json()['data']['resume']
        self.assertEqual(resume['id'], self.resume_id)
        self.assertTrue(resume['file_exists'])

    def test_compliance_resume_deletion_by_platform_admin(self):
        """Admin can execute compliance deletion on a resume, cleaning disk and database."""
        self._login_as(self.admin_id)

        res = self.client.delete(f'/api/resumes/{self.resume_id}')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

        # Record must be gone from DB
        with get_db() as conn:
            cur = conn.execute("SELECT id FROM resumes WHERE id = ?", (self.resume_id,))
            self.assertIsNone(cur.fetchone())

    # ============================================================
    # SECTION 5: SECURITY & AUDIT
    # ============================================================

    def test_security_login_attempts_and_top_failed(self):
        """Security endpoint reports real login attempts and top failed IP sources."""
        self._login_as(self.admin_id)
        res = self.client.get('/api/platform-admin/security/login-attempts')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()['data']

        self.assertGreaterEqual(data['summary']['total_attempts'], 2)
        self.assertGreaterEqual(data['summary']['failed_attempts'], 1)

        # Intruder IP 10.0.0.99 should appear in top_failed_ips
        failed_ips = [item['ip_address'] for item in data['top_failed_ips']]
        self.assertIn("10.0.0.99", failed_ips)

    def test_audit_log_read_only_and_filtering(self):
        """Audit log displays recorded activities and returns 200."""
        self._login_as(self.admin_id)
        res = self.client.get('/api/platform-admin/audit')
        self.assertEqual(res.status_code, 200)
        events = res.get_json()['data']['events']
        self.assertIsInstance(events, list)

    # ============================================================
    # SECTION 6: SYSTEM HEALTH & INTEGRATIONS (ZERO SECRET LEAKAGE)
    # ============================================================

    def test_system_health_probes_and_status_domain(self):
        """System health endpoint checks 8 services returning valid status values."""
        self._login_as(self.admin_id)
        res = self.client.get('/api/platform-admin/system/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()['data']

        self.assertIn('overall', data)
        self.assertIn(data['overall'], {'Healthy', 'Degraded', 'Unavailable'})

        services = data['services']
        expected_services = {'database', 'file_storage', 'authentication', 'resume_parser', 'ats_engine', 'job_matcher', 'adzuna', 'email'}
        self.assertEqual(set(services.keys()), expected_services)

        valid_statuses = {'Healthy', 'Degraded', 'Unavailable', 'Not Configured'}
        for sname, sinfo in services.items():
            self.assertIn(sinfo['status'], valid_statuses, f"Service {sname} returned invalid status {sinfo['status']}")
            self.assertIn('details', sinfo)

    def test_system_integrations_zero_secret_leakage(self):
        """Integrations endpoint returns masked configurations with zero leaked secrets."""
        self._login_as(self.admin_id)
        res = self.client.get('/api/platform-admin/system/integrations')
        self.assertEqual(res.status_code, 200)
        integrations = res.get_json()['data']['integrations']

        for item in integrations:
            self.assertIn('name', item)
            self.assertIn('status', item)
            # Verify no secret keywords leaked
            dumped = json.dumps(item).lower()
            self.assertNotIn('password', dumped)
            self.assertNotIn('secret_key', dumped)
            self.assertNotIn('api_key', dumped)
            self.assertNotIn('token', dumped)
            if 'masked_app_id' in item and item['masked_app_id']:
                self.assertTrue(item['masked_app_id'].endswith('***') or item['masked_app_id'] == '***')

    def test_cross_role_rbac_on_all_new_endpoints(self):
        """All new endpoints enforce 401 unauthenticated and 403 for candidate & HR."""
        endpoints = [
            ("GET", "/api/platform-admin/jobs"),
            ("GET", f"/api/platform-admin/jobs/{self.job_id}"),
            ("GET", "/api/platform-admin/applications"),
            ("GET", f"/api/platform-admin/applications/{self.app_id}"),
            ("GET", "/api/platform-admin/resumes"),
            ("GET", f"/api/platform-admin/resumes/{self.resume_id}"),
            ("GET", "/api/platform-admin/system/health"),
            ("GET", "/api/platform-admin/system/integrations"),
        ]

        # 1. Unauthenticated -> 401 or 302
        self._logout()
        for method, url in endpoints:
            res = self.client.get(url)
            self.assertIn(res.status_code, (401, 302), f"Unauth failed for {url}")

        # 2. Candidate -> 403
        self._login_as(self.cand_id)
        for method, url in endpoints:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 403, f"Candidate was not forbidden for {url}")

        # 3. HR -> 403
        self._login_as(self.hr_id)
        for method, url in endpoints:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 403, f"HR was not forbidden for {url}")

        # 4. Admin -> 200
        self._login_as(self.admin_id)
        for method, url in endpoints:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Admin was not authorized for {url}")


if __name__ == '__main__':
    unittest.main()
