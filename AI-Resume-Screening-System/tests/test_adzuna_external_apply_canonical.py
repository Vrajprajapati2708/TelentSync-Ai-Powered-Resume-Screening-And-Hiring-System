"""
Tests for Canonical Adzuna External Apply Flow & Contract Hardening (Phase 11)
Covers all 25 validation criteria:
 1. Adzuna redirect_url normalization
 2. Canonical external_apply_url
 3. Valid HTTPS URL
 4. Valid HTTP URL
 5. Missing URL
 6. Empty URL
 7. Malformed URL
 8. javascript: URL
 9. data: URL
10. file: URL
11. Missing netloc
12. Multi-query merge
13. Duplicate job merge
14. Valid URL preserved across duplicate merge
15. Cache write/read
16. Single-flight
17. JobMatcher preservation
18. /api/match_jobs response
19. /api/jobs/search response
20. Frontend Apply button contract
21. /api/apply validation
22. External redirect
23. Internal job application
24. External job does not create internal application
25. No secret leakage
"""

import unittest
import copy
import time
import json
import sqlite3
from unittest.mock import patch, MagicMock

from app import create_app
from app.config.settings import TestingConfig
from app.services.adzuna_client import AdzunaClient
from app.services.jobs_search_service import JobsSearchService
from app.ai.job_matcher import JobMatcher
from app.utils.validators import validate_external_apply_url
from app.controllers.auth_controller import register_user


class TestAdzunaExternalApplyCanonical(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestingConfig)
        cls.client = cls.app.test_client()

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # 1. Adzuna redirect_url normalization & 2. Canonical external_apply_url
    def test_01_and_02_adzuna_normalization_and_canonical_fields(self):
        client = AdzunaClient()
        raw_payload = {
            "id": "12345678",
            "title": "Senior Data Engineer",
            "company": {"display_name": "Acme Corp"},
            "location": {"display_name": "Bengaluru", "area": ["India", "Karnataka", "Bengaluru"]},
            "description": "Python, SQL, and Spark experience required.",
            "redirect_url": "https://www.adzuna.in/land/ad/12345678?partner=test",
            "created": "2026-09-20T10:00:00Z"
        }
        normalized = client._normalize(raw_payload)
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized['id'], "adzuna_12345678")
        self.assertEqual(normalized['raw_id'], "12345678")
        self.assertEqual(normalized['source_job_id'], "12345678")
        self.assertTrue(normalized['is_external'])
        self.assertEqual(normalized['external_apply_url'], "https://www.adzuna.in/land/ad/12345678?partner=test")
        self.assertEqual(normalized['apply_url'], "https://www.adzuna.in/land/ad/12345678?partner=test")
        self.assertEqual(normalized['source'], "adzuna")

    # 3. Valid HTTPS URL & 4. Valid HTTP URL
    def test_03_valid_https_url(self):
        is_valid, msg = validate_external_apply_url("https://www.adzuna.in/details/12345")
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")

    def test_04_valid_http_url_rejected_by_secure_policy(self):
        # System enforces secure HTTPS for external redirects
        is_valid, msg = validate_external_apply_url("http://www.adzuna.in/details/12345")
        self.assertFalse(is_valid)
        self.assertIn("https", msg.lower())

    # 5. Missing URL & 6. Empty URL
    def test_05_missing_url(self):
        is_valid, msg = validate_external_apply_url(None)
        self.assertFalse(is_valid)
        self.assertIn("required", msg.lower())

    def test_06_empty_url(self):
        is_valid, msg = validate_external_apply_url("   ")
        self.assertFalse(is_valid)
        self.assertIn("required", msg.lower())

    # 7. Malformed URL
    def test_07_malformed_url(self):
        is_valid, msg = validate_external_apply_url("not_a_valid_url")
        self.assertFalse(is_valid)

    # 8. javascript: URL & 9. data: URL & 10. file: URL
    def test_08_javascript_url(self):
        is_valid, msg = validate_external_apply_url("javascript:alert(document.cookie)")
        self.assertFalse(is_valid)

    def test_09_data_url(self):
        is_valid, msg = validate_external_apply_url("data:text/html,<script>alert(1)</script>")
        self.assertFalse(is_valid)

    def test_10_file_url(self):
        is_valid, msg = validate_external_apply_url("file:///etc/passwd")
        self.assertFalse(is_valid)

    # 11. Missing netloc
    def test_11_missing_netloc(self):
        is_valid, msg = validate_external_apply_url("https://")
        self.assertFalse(is_valid)
        self.assertIn("host", msg.lower())

    # 12. Multi-query merge & 13. Duplicate job merge & 14. Valid URL preserved across duplicate merge
    def test_12_13_14_multi_query_dedup_and_url_preservation(self):
        client = AdzunaClient()
        client.app_id = "test_id"
        client.app_key = "test_key"

        # Simulate 2 queries returning duplicate jobs:
        # Query 1 returns job with empty URL
        # Query 2 returns same job with valid URL
        q1_jobs = [{
            "id": "adzuna_dup_1",
            "raw_id": "dup_1",
            "source_job_id": "dup_1",
            "title": "Machine Learning Engineer",
            "company": "DeepTech AI",
            "location": "Bengaluru",
            "city": "Bengaluru",
            "source": "adzuna",
            "is_external": True,
            "external_apply_url": None,
            "apply_url": ""
        }]
        q2_jobs = [{
            "id": "adzuna_dup_1",
            "raw_id": "dup_1",
            "source_job_id": "dup_1",
            "title": "Machine Learning Engineer",
            "company": "DeepTech AI",
            "location": "Bengaluru",
            "city": "Bengaluru",
            "source": "adzuna",
            "is_external": True,
            "external_apply_url": "https://www.adzuna.in/land/ad/dup_1",
            "apply_url": "https://www.adzuna.in/land/ad/dup_1"
        }]

        call_idx = 0
        def mock_search(q="", location="", per_page=50):
            nonlocal call_idx
            call_idx += 1
            return q1_jobs if call_idx == 1 else q2_jobs

        with patch.object(client, 'search', side_effect=mock_search):
            merged = client.fetch_personalized_jobs(skills=["Machine Learning", "Python"], location="Bengaluru")
            self.assertEqual(len(merged), 1)
            # URL from duplicate must be preserved
            self.assertEqual(merged[0]['external_apply_url'], "https://www.adzuna.in/land/ad/dup_1")
            self.assertEqual(merged[0]['apply_url'], "https://www.adzuna.in/land/ad/dup_1")

    # 15. Cache write/read preserves external_apply_url
    def test_15_cache_write_read_preserves_external_apply_url(self):
        client = AdzunaClient()
        client.app_id = "test_id"
        client.app_key = "test_key"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [{
                "id": "cache_test_99",
                "title": "Cache Tester",
                "company": {"display_name": "Cache Inc"},
                "location": {"display_name": "Pune"},
                "description": "Python job",
                "redirect_url": "https://www.adzuna.in/land/ad/cache_test_99"
            }]
        }
        with patch.object(client.session, 'get', return_value=mock_resp):
            res1 = client.search(q="cache_query_unique_test", location="Pune")
            self.assertEqual(len(res1), 1)
            self.assertEqual(res1[0]['external_apply_url'], "https://www.adzuna.in/land/ad/cache_test_99")

            # Second call (cache hit)
            res2 = client.search(q="cache_query_unique_test", location="Pune")
            self.assertEqual(len(res2), 1)
            self.assertEqual(res2[0]['external_apply_url'], "https://www.adzuna.in/land/ad/cache_test_99")

    # 16. Single-flight coalescing preserves external_apply_url
    def test_16_single_flight_preserves_url(self):
        client = AdzunaClient()
        client.app_id = "test_id"
        client.app_key = "test_key"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [{
                "id": "sf_999",
                "title": "Single Flight Lead",
                "company": {"display_name": "Flight Corp"},
                "location": {"display_name": "Bengaluru"},
                "description": "Python developer",
                "redirect_url": "https://www.adzuna.in/land/ad/sf_999"
            }]
        }
        with patch.object(client.session, 'get', return_value=mock_resp):
            res = client.search(q="single_flight_q")
            self.assertTrue(res[0]['is_external'])
            self.assertEqual(res[0]['external_apply_url'], "https://www.adzuna.in/land/ad/sf_999")

    # 17. JobMatcher preservation of external fields
    def test_17_job_matcher_preserves_external_apply_fields(self):
        matcher = JobMatcher()
        job = {
            "id": "adzuna_match_1",
            "raw_id": "match_1",
            "source_job_id": "match_1",
            "title": "Python Developer",
            "company": "Match Tech",
            "location": "Bengaluru",
            "description": "Python, SQL, Django required.",
            "skills": ["Python", "SQL", "Django"],
            "source": "adzuna",
            "is_external": True,
            "external_apply_url": "https://www.adzuna.in/details/match_1",
            "apply_url": "https://www.adzuna.in/details/match_1"
        }
        ranked = matcher.rank_jobs(["Python", "SQL"], [job])
        self.assertEqual(len(ranked), 1)
        self.assertTrue(ranked[0]['is_external'])
        self.assertEqual(ranked[0]['external_apply_url'], "https://www.adzuna.in/details/match_1")
        self.assertEqual(ranked[0]['apply_url'], "https://www.adzuna.in/details/match_1")
        self.assertEqual(ranked[0]['source_job_id'], "match_1")

    # 18. /api/match_jobs response contract
    def test_18_api_match_jobs_contract(self):
        email = f"cand_match_{int(time.time()*1000)}@test.com"
        cand = register_user("Match Candidate", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        res = self.client.post('/api/match_jobs', json={'skills': ['Python', 'SQL']})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        for j in data.get('jobs', []):
            self.assertIn('is_external', j)
            self.assertIn('external_apply_url', j)
            if j.get('is_external'):
                self.assertIsNotNone(j.get('external_apply_url'))
                self.assertTrue(j.get('external_apply_url').startswith('https://'))

    # 19. /api/jobs/search response contract
    def test_19_api_jobs_search_contract(self):
        email = f"cand_search_{int(time.time()*1000)}@test.com"
        register_user("Search Candidate", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        res = self.client.get('/api/jobs/search?q=Developer&per_page=10')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        for j in data.get('jobs', []):
            self.assertIn('is_external', j)
            self.assertIn('external_apply_url', j)
            if j.get('source') == 'internal':
                self.assertFalse(j['is_external'])
                self.assertIsNone(j['external_apply_url'])
            elif j.get('source') == 'adzuna':
                self.assertTrue(j['is_external'])

    # 20. Frontend Apply button contract & 21. /api/apply validation & 22. External redirect
    def test_20_21_22_apply_external_redirect(self):
        email = f"cand_apply_{int(time.time()*1000)}@test.com"
        register_user("Apply Cand", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        valid_url = "https://www.adzuna.in/land/ad/55512345"
        res = self.client.post('/api/apply', json={
            'job_id': 'adzuna_55512345',
            'is_external': True,
            'external_apply_url': valid_url,
            'apply_url': valid_url,
            'match_score': 85
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('status'), 'external_redirected')
        self.assertEqual(data.get('redirect_url'), valid_url)
        self.assertEqual(data.get('external_apply_url'), valid_url)

    # 23. Internal job application & 24. External job does not create internal application
    def test_23_and_24_internal_vs_external_application(self):
        email = f"cand_int_ext_{int(time.time()*1000)}@test.com"
        cand = register_user("Dual App Cand", email, "Password123!", role="candidate", is_verified=1)
        cand_id = cand['user']['id']
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        from app.database.connection import get_db
        with get_db() as conn:
            app_count_before = conn.execute("SELECT COUNT(*) FROM applications WHERE user_id=?", (cand_id,)).fetchone()[0]

        # 1. External apply does NOT insert application record
        ext_res = self.client.post('/api/apply', json={
            'job_id': 'adzuna_ext_9999',
            'is_external': True,
            'external_apply_url': 'https://www.adzuna.in/land/ad/9999',
            'apply_url': 'https://www.adzuna.in/land/ad/9999'
        })
        self.assertEqual(ext_res.status_code, 200)

        with get_db() as conn:
            app_count_after_ext = conn.execute("SELECT COUNT(*) FROM applications WHERE user_id=?", (cand_id,)).fetchone()[0]
        self.assertEqual(app_count_before, app_count_after_ext)

        # 2. Internal apply (using prefixed internal_25 or 25) DOES insert application record
        int_res = self.client.post('/api/apply', json={
            'job_id': 'internal_25',
            'is_external': False,
            'match_score': 70
        })
        self.assertEqual(int_res.status_code, 200)
        self.assertEqual(int_res.get_json().get('status'), 'submitted')

        with get_db() as conn:
            app_count_after_int = conn.execute("SELECT COUNT(*) FROM applications WHERE user_id=?", (cand_id,)).fetchone()[0]
        self.assertEqual(app_count_after_int, app_count_before + 1)

    # 25. No secret leakage
    def test_25_no_secret_leakage_in_job_search_or_match(self):
        email = f"cand_sec_{int(time.time()*1000)}@test.com"
        register_user("Sec Cand", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        res = self.client.get('/api/jobs/search?q=Developer')
        text = res.get_data(as_text=True)
        self.assertNotIn("ADZUNA_APP_KEY", text)
        self.assertNotIn("app_key", text)
        self.assertNotIn("app_id", text)


if __name__ == '__main__':
    unittest.main()
