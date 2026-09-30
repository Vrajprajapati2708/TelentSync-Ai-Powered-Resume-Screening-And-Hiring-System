"""
Tests for /api/jobs/search endpoint
Covers:
- Unauthorized access (401)
- No params default search
- q only search
- Each filter alone (location, work_mode, min_salary, experience)
- All filters combined
- Invalid params (400)
- Adzuna failure fallback (graceful degradation)
- Pagination bounds
- SQL-injection attempt string
"""
import os
import sys
import unittest
from unittest.mock import patch
import requests

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from app import create_app
from app.config.settings import TestingConfig
from app.controllers.auth_controller import register_user
from app.database.connection import get_db
from app.database.migrations.jobs_search_migration import run_migration


class TestJobsSearchAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Run migration on testing database to ensure columns and indexes exist
        run_migration(TestingConfig.DB_FILE)

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.user_email = "cand_search_tester@test.com"
        self.password = "ValidPassword10!"

        # Register candidate in testing DB
        try:
            register_user("Search Tester", self.user_email, self.password, role="candidate", is_verified=1)
        except Exception:
            pass

        # Seed sample active jobs into testing DB if empty
        with get_db() as conn:
            cnt = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            if cnt == 0:
                conn.execute("""
                    INSERT INTO jobs (title, company, location, type, salary, skills, description, status, work_mode, salary_min, salary_max)
                    VALUES 
                    ('Python Developer', 'Alpha Tech', 'Bangalore', 'Full-time', '12-18 LPA', 'Python, Flask, SQL', 'Looking for Python developer with 3-5 years experience', 'Active', 'onsite', 1200000, 1800000),
                    ('Senior React Engineer', 'Beta Labs', 'Remote', 'Full-time', '20-30 LPA', 'React, TypeScript, Redux', 'Remote React role with 5+ years experience required', 'Active', 'remote', 2000000, 3000000),
                    ('Junior QA Engineer', 'Gamma Soft', 'Pune', 'Full-time', '4-6 LPA', 'Manual Testing, Selenium', 'Fresher or entry level QA welcome to apply', 'Active', 'onsite', 400000, 600000),
                    ('Data Scientist', 'Delta AI', 'Hyderabad', 'Full-time', '15-22 LPA', 'Python, Machine Learning', 'Data Scientist 2-4 years experience', 'Active', 'hybrid', 1500000, 2200000)
                """)
                conn.commit()

    def _login(self):
        return self.client.post('/api/auth/login', json={
            'email': self.user_email,
            'password': self.password
        })

    def test_01_unauthorized_access(self):
        """GET /api/jobs/search without login returns 401."""
        res = self.client.get('/api/jobs/search')
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data.get('success', True))

    def test_02_search_no_params(self):
        """Default search returns status 200 with structured response."""
        self._login()
        res = self.client.get('/api/jobs/search')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('jobs', data)
        self.assertIn('total', data)
        self.assertIn('page', data)
        self.assertIn('per_page', data)
        self.assertIn('total_pages', data)
        self.assertIn('applied_filters', data)
        self.assertIn('warnings', data)
        self.assertIsInstance(data['jobs'], list)
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['per_page'], 10)

    def test_03_search_q_only(self):
        """Search query 'Python' returns matching jobs."""
        self._login()
        res = self.client.get('/api/jobs/search?q=Python')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        for job in data['jobs']:
            text = f"{job['title']} {job['company']} {' '.join(job['skills'])} {job['description_snippet']}".lower()
            self.assertTrue('python' in text or 'developer' in text or job['source'] == 'adzuna')

    def test_04_each_filter_alone(self):
        """Test location, work_mode, min_salary, and experience filters individually."""
        self._login()

        # 1. Location filter
        res_loc = self.client.get('/api/jobs/search?location=Bangalore&source=internal')
        self.assertEqual(res_loc.status_code, 200)
        data_loc = res_loc.get_json()
        for j in data_loc['jobs']:
            self.assertIn('bangalore', j['location'].lower())

        # 2. Work mode filter: remote
        res_remote = self.client.get('/api/jobs/search?work_mode=remote&source=internal')
        self.assertEqual(res_remote.status_code, 200)
        data_remote = res_remote.get_json()
        for j in data_remote['jobs']:
            self.assertEqual(j['work_mode'], 'remote')

        # 3. Min salary filter: 1000000 (10L+)
        res_sal = self.client.get('/api/jobs/search?min_salary=1000000&source=internal')
        self.assertEqual(res_sal.status_code, 200)
        data_sal = res_sal.get_json()
        for j in data_sal['jobs']:
            self.assertGreaterEqual(j['salary_max'], 1000000)

        # 4. Experience filter: 0-1 (freshers / entry level)
        res_exp = self.client.get('/api/jobs/search?experience=0-1&source=internal')
        self.assertEqual(res_exp.status_code, 200)
        data_exp = res_exp.get_json()
        for j in data_exp['jobs']:
            if j['experience_min'] is not None:
                self.assertLessEqual(j['experience_min'], 1.0)

    def test_05_all_filters_combined(self):
        """Combine q, location, work_mode, min_salary, experience, and sort."""
        self._login()
        res = self.client.get('/api/jobs/search?q=React&location=Remote&work_mode=remote&min_salary=500000&experience=5-8&sort=salary')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data['applied_filters']['work_mode'], 'remote')
        self.assertEqual(data['applied_filters']['min_salary'], 500000)
        self.assertEqual(data['applied_filters']['experience'], '5-8')
        self.assertEqual(data['applied_filters']['sort'], 'salary')

    def test_06_invalid_params_return_400(self):
        """Validate error hierarchy for invalid params."""
        self._login()

        # Invalid work_mode
        res1 = self.client.get('/api/jobs/search?work_mode=invalid_mode')
        self.assertEqual(res1.status_code, 400)
        self.assertIn('Invalid work_mode', res1.get_json()['message'])

        # Invalid experience
        res2 = self.client.get('/api/jobs/search?experience=99-100')
        self.assertEqual(res2.status_code, 400)
        self.assertIn('Invalid experience', res2.get_json()['message'])

        # Negative min_salary
        res3 = self.client.get('/api/jobs/search?min_salary=-500')
        self.assertEqual(res3.status_code, 400)
        self.assertIn('min_salary', res3.get_json()['message'])

        # Non-numeric min_salary
        res4 = self.client.get('/api/jobs/search?min_salary=abc')
        self.assertEqual(res4.status_code, 400)

        # Non-numeric page
        res5 = self.client.get('/api/jobs/search?page=zero')
        self.assertEqual(res5.status_code, 400)

        # Invalid sort
        res6 = self.client.get('/api/jobs/search?sort=invalid_sort')
        self.assertEqual(res6.status_code, 400)

    def test_07_adzuna_failure_fallback(self):
        """If Adzuna fails or times out, return internal jobs gracefully with warning."""
        from app.services.jobs_search_service import _ADZUNA_CACHE
        _ADZUNA_CACHE.clear()
        self._login()
        with patch('requests.Session.get', side_effect=requests.exceptions.Timeout("Connection timed out")):
            res = self.client.get('/api/jobs/search?source=all&q=UncachedQueryTest')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get('success'))
            self.assertTrue(any('unavailable' in w.lower() or 'timed out' in w.lower() for w in data.get('warnings', [])))

    def test_08_pagination_bounds(self):
        """Verify page bounds and per_page clamping."""
        self._login()
        res = self.client.get('/api/jobs/search?page=1&per_page=2')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['per_page'], 2)
        self.assertLessEqual(len(data['jobs']), 2)

        # Test per_page clamping (max 50)
        res_clamp = self.client.get('/api/jobs/search?per_page=100')
        self.assertEqual(res_clamp.status_code, 200)
        data_clamp = res_clamp.get_json()
        self.assertEqual(data_clamp['per_page'], 50)

    def test_09_sql_injection_attempt_string(self):
        """SQL injection attempt strings must be sanitized and harmless."""
        self._login()
        malicious_strings = [
            "' OR 1=1 --",
            "'; DROP TABLE jobs; --",
            "' UNION SELECT * FROM users --",
            "admin' --"
        ]
        for injection in malicious_strings:
            res = self.client.get(f'/api/jobs/search?q={injection}&location={injection}')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get('success'))

        # Verify jobs table was not dropped
        with get_db() as conn:
            cnt = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            self.assertGreater(cnt, 0)


if __name__ == '__main__':
    unittest.main()
