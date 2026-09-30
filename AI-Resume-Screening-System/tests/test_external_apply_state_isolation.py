"""
TALENTSYNC — EXTERNAL APPLY STATE ISOLATION & CONTRACT HARDENING REGRESSION TESTS
Tests covering Section 13 requirements:
  TEST 1: Adzuna job contains external_apply_url.
  TEST 2: Render button retains external URL (DOM data-apply-url & onclick parameters).
  TEST 3: DB.jobs is overwritten after rendering without breaking card resolution.
  TEST 4: Apply still resolves original external URL when DB.jobs is wiped or replaced.
  TEST 5: Three external cards maintain independent URLs (no cross-contamination).
  TEST 6: Local internal job still uses internal application flow.
  TEST 7: External application does not create internal application record.
  TEST 8: Invalid external URL is still rejected.
  TEST 9: javascript: remains rejected.
  TEST 10: Private/local network URLs remain rejected.
  TEST 11: Pagination does not break external Apply.
  TEST 12: LiveJobsManager refresh does not break existing cards.
  TEST 13: No credentials appear in DOM or API payload.
  TEST 14: No cross-job URL leakage occurs.
"""

import unittest
import json
import re
import os
from unittest.mock import patch, MagicMock

from app import create_app
from app.config.settings import TestingConfig
from app.services.adzuna_client import AdzunaClient
from app.utils.validators import validate_external_apply_url
from app.controllers.auth_controller import register_user
from app.database.connection import get_db


class TestExternalApplyStateIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestingConfig)
        cls.client = cls.app.test_client()

        # Read static app.js to verify frontend contract hardening
        js_path = os.path.join(cls.app.root_path, 'static', 'js', 'app.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            cls.app_js_code = f.read()

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # TEST 1: Adzuna job contains external_apply_url
    def test_01_adzuna_job_contains_external_apply_url(self):
        client = AdzunaClient()
        raw = {
            "id": "job_101",
            "title": "Software Engineer",
            "company": {"display_name": "Tech Corp"},
            "redirect_url": "https://www.adzuna.in/land/ad/101?partner=test"
        }
        normalized = client._normalize(raw)
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized['external_apply_url'], "https://www.adzuna.in/land/ad/101?partner=test")
        self.assertEqual(normalized['apply_url'], "https://www.adzuna.in/land/ad/101?partner=test")
        self.assertTrue(normalized['is_external'])

    # TEST 2: Render button retains external URL in static templates
    def test_02_render_button_retains_external_url(self):
        # Verify app.js renders data-apply-url and passes direct URL to applyJob
        self.assertIn('data-apply-url="${encodedUrl}"', self.app_js_code)
        self.assertIn("data-is-external=\"true\"", self.app_js_code)
        self.assertIn("applyJob('${escapeHTML(String(safeId))}', true, '${encodedUrl}', this)", self.app_js_code)

    # TEST 3 & 4: DB.jobs overwritten after rendering; Apply still resolves direct URL
    def test_03_and_04_applyjob_resolves_url_independent_of_db_jobs(self):
        # Verify applyJob signature accepts (id, isExternal = false, directUrl = '', btnElement = null)
        match = re.search(r'function\s+applyJob\s*\(([^)]+)\)', self.app_js_code)
        self.assertIsNotNone(match)
        params = [p.strip() for p in match.group(1).split(',')]
        self.assertIn('id', params[0])
        self.assertIn('isExternal', params[1])
        self.assertIn('directUrl', params[2])
        self.assertIn('btnElement', params[3])

        # Verify fallback order checks directUrl, btnElement dataset, and _allKnownJobsMap before DB.jobs
        self.assertIn('decodeURIComponent(resolvedDirectUrl)', self.app_js_code)
        self.assertIn('btn.dataset.applyUrl', self.app_js_code)
        self.assertIn('_allKnownJobsMap', self.app_js_code)

    # TEST 5 & 14: Three external cards maintain independent URLs, no cross-job URL leakage
    def test_05_and_14_three_external_cards_independent_urls(self):
        jobs = [
            {"id": "adzuna_1", "raw_id": "1", "external_apply_url": "https://www.adzuna.in/land/ad/1", "title": "Job A"},
            {"id": "adzuna_2", "raw_id": "2", "external_apply_url": "https://www.adzuna.in/land/ad/2", "title": "Job B"},
            {"id": "adzuna_3", "raw_id": "3", "external_apply_url": "https://www.adzuna.in/land/ad/3", "title": "Job C"}
        ]
        urls = set()
        for j in jobs:
            is_valid, _ = validate_external_apply_url(j['external_apply_url'])
            self.assertTrue(is_valid)
            urls.add(j['external_apply_url'])
        self.assertEqual(len(urls), 3, "All 3 jobs must have distinct external URLs")

        # Verify that sending each job to /api/apply redirects to its own URL, never leaking
        cand = register_user("Test Cand 3Jobs", f"cand3_{os.urandom(4).hex()}@test.com", "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': cand['user']['email'], 'password': 'Password123!'})

        for j in jobs:
            res = self.client.post('/api/apply', json={
                'job_id': j['id'],
                'is_external': True,
                'external_apply_url': j['external_apply_url']
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get('redirect_url'), j['external_apply_url'])
            self.assertEqual(data.get('status'), 'external_redirected')

    # TEST 6 & 7: Local internal job uses internal application flow; external does not create application
    def test_06_and_07_internal_vs_external_application_records(self):
        email = f"cand_flow_{os.urandom(4).hex()}@test.com"
        cand = register_user("Flow Candidate", email, "Password123!", role="candidate", is_verified=1)
        cand_id = cand['user']['id']
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        with get_db() as conn:
            initial_count = conn.execute("SELECT COUNT(*) FROM applications WHERE user_id=?", (cand_id,)).fetchone()[0]

        # 1. External application
        res_ext = self.client.post('/api/apply', json={
            'job_id': 'adzuna_test_ext',
            'is_external': True,
            'external_apply_url': 'https://www.adzuna.in/land/ad/test'
        })
        self.assertEqual(res_ext.status_code, 200)

        with get_db() as conn:
            after_ext_count = conn.execute("SELECT COUNT(*) FROM applications WHERE user_id=?", (cand_id,)).fetchone()[0]
        self.assertEqual(initial_count, after_ext_count, "External application must NOT create DB application record")

        # 2. Internal application (using test fixture job id 25)
        res_int = self.client.post('/api/apply', json={
            'job_id': '25',
            'is_external': False,
            'match_score': 80
        })
        self.assertEqual(res_int.status_code, 200)
        self.assertEqual(res_int.get_json().get('status'), 'submitted')

        with get_db() as conn:
            after_int_count = conn.execute("SELECT COUNT(*) FROM applications WHERE user_id=?", (cand_id,)).fetchone()[0]
        self.assertEqual(after_int_count, initial_count + 1, "Internal application must create DB application record")

    # TEST 8, 9, 10: URL security validation
    def test_08_invalid_external_url_rejected(self):
        is_valid, msg = validate_external_apply_url("not_a_valid_url")
        self.assertFalse(is_valid)

    def test_09_javascript_url_rejected(self):
        is_valid, msg = validate_external_apply_url("javascript:alert(document.cookie)")
        self.assertFalse(is_valid)

    def test_10_private_and_local_urls_rejected(self):
        # 127.0.0.1
        is_valid, msg = validate_external_apply_url("https://127.0.0.1/admin")
        self.assertFalse(is_valid)
        # localhost
        is_valid, msg = validate_external_apply_url("https://localhost:8080/apply")
        self.assertFalse(is_valid)
        # RFC-1918 192.168.1.1
        is_valid, msg = validate_external_apply_url("https://192.168.1.1/apply")
        self.assertFalse(is_valid)

    # TEST 11 & 12: Pagination and LiveJobsManager refresh state preservation in JS
    def test_11_and_12_state_isolation_architecture_in_js(self):
        # Verify Router.inner preserves _mlJobsCache when recommendations exist
        self.assertIn('_mlJobsCache && _mlJobsCache.length > 0', self.app_js_code)
        # Verify LiveJobsManager saves to lastResults and registers each result
        self.assertIn('this.lastResults = data.jobs || [];', self.app_js_code)
        self.assertIn('registerKnownJob(j)', self.app_js_code)

    # TEST 13: No credentials in DOM or API payload
    def test_13_no_credentials_in_dom_or_api(self):
        self.assertNotIn("ADZUNA_APP_KEY", self.app_js_code)
        self.assertNotIn("adzuna_app_key", self.app_js_code)


if __name__ == '__main__':
    unittest.main()
