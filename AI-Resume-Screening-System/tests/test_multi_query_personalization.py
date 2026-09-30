# ============================================================
#  HireAI / TalentSync — Multi-Query Personalization Tests
# ============================================================

import os
import sys
import time
import threading
import unittest
from unittest.mock import patch, MagicMock

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from app import create_app
from app.config.settings import TestingConfig
from app.services.adzuna_client import AdzunaClient, AdzunaRateLimitError
from app.services.adzuna_service import AdzunaService
from app.ai.job_matcher import JobMatcher
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.routes.resume_routes import _user_ranked_cache, invalidate_user_ranked_cache


class TestMultiQueryPersonalization(unittest.TestCase):
    """Unit and integration tests for multi-query personalization, experience ranking & caching."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.adzuna_client = AdzunaClient()
        self.adzuna_client.app_id = "test_id"
        self.adzuna_client.app_key = "test_key"
        self.adzuna_client._cache.clear()
        _user_ranked_cache.clear()

    def test_01_multi_query_build_and_dedupe(self):
        """Verifies multi-query execution builds focused queries and dedupes across raw_id and (title, company, city)."""
        skills = ['pandas', 'python', 'docker', 'sql']
        # Market relevance: python (6 roles), sql (3 roles), docker (3 roles), pandas (1 role)
        ranked_skills = self.adzuna_client.rank_skills_by_market_relevance(skills)
        self.assertEqual(ranked_skills[0], 'python')
        self.assertIn(ranked_skills[1], ['sql', 'docker'])

        mock_batch_1 = [
            {'id': 'adzuna_1', 'raw_id': '1', 'title': 'Python Developer', 'company': 'Tech Corp', 'location': 'Bengaluru', 'city': 'Bengaluru', 'salary_min': 1000000, 'posted_date': '2026-09-01'},
            {'id': 'adzuna_2', 'raw_id': '2', 'title': 'Data Scientist', 'company': 'AI Labs', 'location': 'Pune', 'city': 'Pune', 'salary_min': 1200000, 'posted_date': '2026-09-01'},
        ]
        # Duplicate of adzuna_1 by raw_id, and duplicate of adzuna_2 by normalized title+company+city
        mock_batch_2 = [
            {'id': 'adzuna_1', 'raw_id': '1', 'title': 'Python Developer', 'company': 'Tech Corp', 'location': 'Bengaluru', 'city': 'Bengaluru', 'salary_min': 1000000, 'posted_date': '2026-09-01'},
            {'id': 'adzuna_99', 'raw_id': '99', 'title': 'Data Scientist', 'company': 'AI Labs', 'location': 'Pune, Maharashtra', 'city': 'Pune', 'salary_min': 1200000, 'posted_date': '2026-09-01'},
            {'id': 'adzuna_3', 'raw_id': '3', 'title': 'Backend Engineer', 'company': 'Cloud Soft', 'location': 'Hyderabad', 'city': 'Hyderabad', 'salary_min': 900000, 'posted_date': '2026-09-01'},
        ]

        with patch.object(self.adzuna_client, 'search') as mock_search:
            mock_search.side_effect = [mock_batch_1, mock_batch_2, []]
            results = self.adzuna_client.fetch_personalized_jobs(
                skills=skills,
                location="Bengaluru",
                limit=10
            )

            # Proves raw_id duplicate ('1') and semantic duplicate ('Data Scientist' + 'AI Labs' + 'Pune') were eliminated
            self.assertEqual(len(results), 3)
            result_ids = {r['raw_id'] for r in results}
            self.assertIn('1', result_ids)
            self.assertIn('3', result_ids)
            # Either 2 or 99 was kept (thread completion order), but never both
            self.assertEqual(len(result_ids.intersection({'2', '99'})), 1)

    def test_02_one_subquery_fails_still_returns_results(self):
        """Verifies that if one of the sub-queries raises a network/timeout exception, remaining queries still merge."""
        skills = ['python', 'django']
        good_jobs = [
            {'id': 'adzuna_10', 'raw_id': '10', 'title': 'Python Dev', 'company': 'Acme', 'location': 'Delhi', 'city': 'Delhi'}
        ]

        with patch.object(self.adzuna_client, 'search') as mock_search:
            # First query fails with generic error, second succeeds
            mock_search.side_effect = [Exception("Upstream timeout on query"), good_jobs]
            results = self.adzuna_client.fetch_personalized_jobs(skills=skills, limit=10)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['raw_id'], '10')

    def test_03_no_skills_candidate_gets_needs_resume(self):
        """Verifies candidate with no parsed skills gets jobs: [] with needs_resume: True, NOT generic Software Developer."""
        email = "cand_no_skills@test.com"
        register_user("No Skill Cand", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        res = self.client.post('/api/match_jobs', json={'skills': []})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('jobs'), [])
        self.assertTrue(data.get('needs_resume'))
        self.assertIn("Upload your resume", data.get('message', ''))
        self.assertIn('popular_jobs', data)

    def test_04_different_candidates_get_different_ranked_lists(self):
        """Two candidates with different skills get distinct top-ranked jobs from the matcher."""
        cand_a_skills = ['python', 'pandas', 'machine learning', 'scikit-learn']
        cand_b_skills = ['react', 'javascript', 'html', 'css']

        mock_pool = [
            {'id': '1', 'title': 'Machine Learning Scientist', 'skills': 'Python, Machine Learning, Pandas, Scikit-learn', 'description': 'ML research role', 'salary_min': 1500000, 'posted_date': '2026-09-01'},
            {'id': '2', 'title': 'Frontend Web Developer', 'skills': 'React, JavaScript, HTML, CSS', 'description': 'Modern UI frontend engineering', 'salary_min': 1200000, 'posted_date': '2026-09-01'},
            {'id': '3', 'title': 'Python Backend Engineer', 'skills': 'Python, Django, SQL', 'description': 'Backend APIs', 'salary_min': 1100000, 'posted_date': '2026-09-01'},
        ]

        matcher = JobMatcher()
        ranked_a = matcher.rank_jobs(cand_a_skills, [dict(j) for j in mock_pool])
        ranked_b = matcher.rank_jobs(cand_b_skills, [dict(j) for j in mock_pool])

        # Candidate A must have ML role as #1
        self.assertEqual(ranked_a[0]['title'], 'Machine Learning Scientist')
        # Candidate B must have Frontend role as #1
        self.assertEqual(ranked_b[0]['title'], 'Frontend Web Developer')
        self.assertNotEqual(ranked_a[0]['id'], ranked_b[0]['id'])

    def test_05_experience_aware_ordering(self):
        """Fresher candidate pushes down 5+ yr jobs; Senior candidate pushes down intern/fresher jobs."""
        matcher = JobMatcher()
        jobs = [
            {
                'id': 'senior_role',
                'title': 'Senior Python Architect',
                'description': 'Minimum 5 years of production experience required. Senior leadership position.',
                'skills': 'Python, Django',
                'experience_min': 5.0,
                'experience_max': 10.0,
                'salary_min': 2000000,
                'posted_date': '2026-09-01'
            },
            {
                'id': 'junior_role',
                'title': 'Junior Python Developer',
                'description': '0-2 years of experience. Open to freshers and junior developers.',
                'skills': 'Python, Django',
                'experience_min': 0.0,
                'experience_max': 2.0,
                'salary_min': 600000,
                'posted_date': '2026-09-01'
            }
        ]

        # 1. Fresher candidate (0 years experience)
        ranked_fresher = matcher.rank_jobs(['Python', 'Django'], [dict(j) for j in jobs], user_prefs={'experience': '0 years'})
        self.assertEqual(ranked_fresher[0]['id'], 'junior_role')
        self.assertEqual(ranked_fresher[1]['id'], 'senior_role')

        # 2. Senior candidate (7 years experience)
        ranked_senior = matcher.rank_jobs(['Python', 'Django'], [dict(j) for j in jobs], user_prefs={'experience': '7 years'})
        self.assertEqual(ranked_senior[0]['id'], 'senior_role')
        self.assertEqual(ranked_senior[1]['id'], 'junior_role')

    def test_06_per_user_cache_isolation(self):
        """Verifies per-user cache isolates results between different users and invalidates cleanly."""
        email_1 = "cand_cache_1@test.com"
        register_user("Cand One", email_1, "Password123!", role="candidate", is_verified=1)
        with get_db() as conn:
            u1_id = conn.execute("SELECT id FROM users WHERE email=?", (email_1,)).fetchone()['id']
        self.client.post('/api/auth/login', json={'email': email_1, 'password': 'Password123!'})

        mock_jobs_1 = [
            {'id': 'adz_1', 'raw_id': '1', 'title': 'Python Lead', 'company': 'C1', 'location': 'Ahmedabad', 'city': 'Ahmedabad', 'skills': 'Python', 'salary_min': 10, 'posted_date': '2026-09-01'}
        ]

        with patch('app.services.adzuna_service.AdzunaService.fetch_live_jobs', return_value=mock_jobs_1):
            res1 = self.client.post('/api/match_jobs', json={'skills': ['Python'], 'location': 'Ahmedabad'})
            self.assertEqual(res1.status_code, 200)
            data1 = res1.get_json()
            self.assertIn("Personalized for", data1.get('personalization_summary', ''))

        # Proves cache was populated for user 1
        user1_keys = [k for k in _user_ranked_cache if k.startswith(f'{u1_id}:')]
        self.assertTrue(len(user1_keys) > 0)

        # Login as User 2 with different skills
        email_2 = "cand_cache_2@test.com"
        register_user("Cand Two", email_2, "Password123!", role="candidate", is_verified=1)
        with get_db() as conn:
            u2_id = conn.execute("SELECT id FROM users WHERE email=?", (email_2,)).fetchone()['id']
        self.client.post('/api/auth/login', json={'email': email_2, 'password': 'Password123!'})

        mock_jobs_2 = [
            {'id': 'adz_2', 'raw_id': '2', 'title': 'React Specialist', 'company': 'C2', 'location': 'Mumbai', 'city': 'Mumbai', 'skills': 'React', 'salary_min': 10, 'posted_date': '2026-09-01'}
        ]

        with patch('app.services.adzuna_service.AdzunaService.fetch_live_jobs', return_value=mock_jobs_2):
            res2 = self.client.post('/api/match_jobs', json={'skills': ['React'], 'location': 'Mumbai'})
            self.assertEqual(res2.status_code, 200)
            data2 = res2.get_json()
            self.assertEqual(data2['jobs'][0]['title'], 'React Specialist')

        # Invalidate User 1 cache
        invalidate_user_ranked_cache(u1_id)
        # User 1 cache must be empty, User 2 cache must still exist
        user1_after = [k for k in _user_ranked_cache if k.startswith(f'{u1_id}:')]
        self.assertEqual(len(user1_after), 0)
        user2_keys = [k for k in _user_ranked_cache if k.startswith(f'{u2_id}:')]
        self.assertTrue(len(user2_keys) > 0)

    def test_07_adzuna_global_cache_and_quota_two_users_one_http_call(self):
        """Verifies two candidates with the same raw query trigger only ONE Adzuna HTTP call but get different ranked lists."""
        client = AdzunaClient()
        client.app_id = "test_id"
        client.app_key = "test_key"
        client._cache.clear()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'count': 2,
            'results': [
                {
                    'id': 'j_sr', 'title': 'Senior Python Engineer', 'company': {'display_name': 'Alpha'},
                    'location': {'display_name': 'Delhi'}, 'description': '5+ years experience required',
                    'salary_min': 1800000, 'salary_max': 2400000, 'created': '2026-09-01T10:00:00Z',
                    'redirect_url': 'https://adzuna.in/details/1'
                },
                {
                    'id': 'j_jr', 'title': 'Junior Python Developer', 'company': {'display_name': 'Beta'},
                    'location': {'display_name': 'Delhi'}, 'description': '0-1 years experience, fresher welcome',
                    'salary_min': 500000, 'salary_max': 700000, 'created': '2026-09-01T10:00:00Z',
                    'redirect_url': 'https://adzuna.in/details/2'
                }
            ]
        }

        matcher = JobMatcher()

        with patch('requests.Session.get', return_value=mock_response) as mock_get:
            # Candidate 1 (Senior): fetches raw Adzuna query
            jobs_user_1 = client.search(q="Python", location="Delhi")
            self.assertEqual(mock_get.call_count, 1)

            # Candidate 2 (Fresher): same query -> MUST hit global Adzuna cache (no 2nd HTTP call!)
            jobs_user_2 = client.search(q="Python", location="Delhi")
            self.assertEqual(mock_get.call_count, 1)  # Quota saved!

            # Both candidates rank with their own experience preferences
            ranked_user_1 = matcher.rank_jobs(['Python'], [dict(j) for j in jobs_user_1], user_prefs={'experience': '6 years'})
            ranked_user_2 = matcher.rank_jobs(['Python'], [dict(j) for j in jobs_user_2], user_prefs={'experience': '0 years'})

            # User 1 gets Senior job first
            self.assertEqual(ranked_user_1[0]['id'], 'adzuna_j_sr')
            # User 2 gets Junior job first
            self.assertEqual(ranked_user_2[0]['id'], 'adzuna_j_jr')
            self.assertNotEqual(ranked_user_1[0]['id'], ranked_user_2[0]['id'])

    def test_08_stale_while_error_on_429(self):
        """Verifies that if Adzuna returns HTTP 429, client serves stale cached results instead of immediately failing."""
        client = AdzunaClient()
        client.app_id = "test_id"
        client.app_key = "test_key"
        client._cache.clear()

        # Seed the cache with a previous result
        stale_jobs = [{'id': 'adzuna_cached', 'raw_id': 'c1', 'title': 'Cached Role'}]
        cache_key = "in|python|bangalore|0|1|20|relevance"
        import hashlib
        key_hash = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
        # Set timestamp to 20 minutes ago (expired)
        client._cache[key_hash] = (time.time() - 1200, stale_jobs)

        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.text = "Rate limit exceeded"

        with patch('requests.Session.get', return_value=mock_resp_429):
            jobs = client.search(q="Python", location="Bangalore")
            # Should have returned stale cached jobs
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]['id'], 'adzuna_cached')

    def test_09_threadpool_timeout_keeps_completed_results(self):
        """Unit test: one mocked query sleeps longer than the timeout and the other two still return results."""
        skills = ['python', 'sql', 'docker']
        client = AdzunaClient()
        client.app_id = "test_id"
        client.app_key = "test_key"
        client.pool_timeout = 0.25

        def mock_search_impl(q="", location="", per_page=20):
            if location == 'Pune':
                # Slow query sleeps longer than timeout
                time.sleep(1.0)
                return [{'id': 'adz_slow', 'raw_id': 's1', 'title': 'Slow Role', 'company': 'Co C', 'location': 'Pune', 'city': 'Pune'}]
            # Fast queries return immediately
            return [{'id': f'adz_{q}', 'raw_id': f'raw_{q}', 'title': f'{q} Fast Role', 'company': 'Co A', 'location': 'Pune', 'city': 'Pune'}]

        with patch.object(client, 'search', side_effect=mock_search_impl):
            results = client.fetch_personalized_jobs(skills=skills, location="Pune", limit=10)

            # Results from fast queries must be kept
            self.assertGreaterEqual(len(results), 2)
            raw_ids = [r['raw_id'] for r in results]
            self.assertIn('raw_Data Engineer', raw_ids)
            self.assertIn('raw_python docker', raw_ids)
            # The slow query results were dropped due to timeout
            self.assertNotIn('s1', raw_ids)

    def test_10_real_retry_session_http_server_429_stale_cache_and_500_upstream(self):
        """Uses a real Retry-enabled session against a local mock HTTP server (NOT mocked session.get).
        Proves 429 returns stale cached jobs and 500 raises AdzunaUpstreamError."""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading
        from app.services.adzuna_client import AdzunaUpstreamError

        class MockAdzunaServerHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if 'status-429' in self.path:
                    self.send_response(429)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Too Many Requests"}')
                elif 'status-500' in self.path:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Internal Server Error"}')
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"results": []}')

            def log_message(self, format, *args):
                pass  # Suppress request logging in test stdout

        server = HTTPServer(('127.0.0.1', 0), MockAdzunaServerHandler)
        port = server.server_address[1]
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            client = AdzunaClient()
            client.app_id = "test_id"
            client.app_key = "test_key"
            client._cache.clear()

            # 1. Test 429: pre-populate cache with a stale entry
            import hashlib
            stale_jobs = [{'id': 'adzuna_stale_real', 'raw_id': 'real_stale_1', 'title': 'Stale Real Job'}]
            cache_key = hashlib.md5("in|rate_limit_test||0|1|20|relevance".encode('utf-8')).hexdigest()
            client._cache[cache_key] = (time.time() - 1000, stale_jobs)

            client.base_url = f"http://127.0.0.1:{port}/status-429"
            jobs_429 = client.search(q="rate_limit_test")
            self.assertEqual(len(jobs_429), 1)
            self.assertEqual(jobs_429[0]['id'], 'adzuna_stale_real')

            # 2. Test 500: empty cache -> raises AdzunaUpstreamError
            client.base_url = f"http://127.0.0.1:{port}/status-500"
            with self.assertRaises(AdzunaUpstreamError):
                client.search(q="server_error_test")
        finally:
            server.shutdown()
            server.server_close()

    def test_11_transparency_summary_uninferrable_role_uses_top_skill(self):
        """Verifies personalization_summary uses top-ranked skill when no role can be inferred, NOT 'Specialist'."""
        email = "cand_transparency@test.com"
        register_user("Cand Trans", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        # Skills that do not match any standard role in JOB_ROLE_SKILLS
        rare_skills = ['uniquecustomskill', 'anotherskill']
        mock_jobs = [
            {'id': 'adz_1', 'raw_id': '1', 'title': 'Role A', 'company': 'C1', 'location': 'Noida', 'city': 'Noida', 'skills': 'uniquecustomskill', 'salary_min': 10, 'posted_date': '2026-09-01'}
        ]

        with patch('app.services.adzuna_service.AdzunaService.fetch_live_jobs', return_value=mock_jobs):
            res = self.client.post('/api/match_jobs', json={'skills': rare_skills, 'location': 'Noida'})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            summary = data.get('personalization_summary', '')
            self.assertIn("Personalized for: uniquecustomskill", summary)
            self.assertNotIn("Specialist", summary)
            self.assertIn("uniquecustomskill, anotherskill", summary)
            self.assertIn("Noida", summary)

    def test_12_retry_after_header_429_returns_immediately(self):
        """Proves that a 429 with 'Retry-After: 30' header returns in under 2 seconds (not respecting header)."""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading
        import hashlib

        class Mock429RetryAfterHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(429)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Retry-After', '30')
                self.end_headers()
                self.wfile.write(b'{"error": "Too Many Requests"}')

            def log_message(self, format, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Mock429RetryAfterHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        try:
            client = AdzunaClient()
            client.app_id = "test_id"
            client.app_key = "test_key"
            client.base_url = f"http://127.0.0.1:{port}/search"
            client._cache.clear()

            # Pre-populate stale cache to test immediate return of stale results
            stale_jobs = [{'id': 'adz_stale_quick', 'title': 'Quick Return Stale'}]
            cache_key = hashlib.md5("in|fast_429||0|1|20|relevance".encode('utf-8')).hexdigest()
            client._cache[cache_key] = (time.time() - 900, stale_jobs)

            t0 = time.time()
            res = client.search(q="fast_429")
            elapsed = time.time() - t0

            # Must return in under 2 seconds (proves Retry-After: 30 was not slept on)
            self.assertLess(elapsed, 2.0)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]['id'], 'adz_stale_quick')
        finally:
            server.shutdown()
            server.server_close()

    def test_13_cache_size_cap_and_eviction_stale_preservation(self):
        """Tests that cache size cap evicts entries older than 1 hour first, preserves stale-while-error (< 1hr), and then evicts oldest."""
        client = AdzunaClient()
        client.cache_max = 3
        client._cache.clear()

        now = time.time()
        # Entry 1: 2 hours old (> 3600s, eligible for expired eviction)
        client._cache['key_expired_2h'] = (now - 7200, [{'id': 'job_2h'}])
        # Entry 2: 30 minutes old (1800s, stale-while-error window, MUST NOT be evicted in expired pass)
        client._cache['key_stale_30m'] = (now - 1800, [{'id': 'job_30m'}])
        # Entry 3: 2 minutes old (120s, fresh entry)
        client._cache['key_fresh_2m'] = (now - 120, [{'id': 'job_2m'}])

        # Cache is now at capacity (3 entries)
        self.assertEqual(len(client._cache), 3)

        # Evict to make room for a new entry
        with client._lock:
            client._evict_cache_locked(now, key_to_add='key_new_1')
            client._cache['key_new_1'] = (now, [{'id': 'job_new_1'}])

        # 1. key_expired_2h should have been evicted first because it is > 1 hour old
        self.assertNotIn('key_expired_2h', client._cache)
        # 2. key_stale_30m must NOT have been evicted because it is <= 1 hour old (stale-while-error protected)
        self.assertIn('key_stale_30m', client._cache)
        self.assertIn('key_fresh_2m', client._cache)
        self.assertIn('key_new_1', client._cache)
        self.assertEqual(len(client._cache), 3)

        # Now all entries are <= 1 hour old (30m, 2m, 0m).
        # Adding another entry forces Pass 2 (oldest entry eviction):
        with client._lock:
            client._evict_cache_locked(now + 1, key_to_add='key_new_2')
            client._cache['key_new_2'] = (now + 1, [{'id': 'job_new_2'}])

        # key_stale_30m was the oldest remaining, so now it is evicted
        self.assertNotIn('key_stale_30m', client._cache)
        self.assertIn('key_fresh_2m', client._cache)
        self.assertIn('key_new_1', client._cache)
        self.assertIn('key_new_2', client._cache)
        self.assertEqual(len(client._cache), 3)

    def test_14_cache_env_var_max_default(self):
        """Verifies ADZUNA_CACHE_MAX default is 500 and configurable."""
        client_def = AdzunaClient()
        self.assertEqual(client_def.cache_max, 500)

        with patch.dict(os.environ, {'ADZUNA_CACHE_MAX': '250'}):
            client_custom = AdzunaClient()
            self.assertEqual(client_custom.cache_max, 250)

    def test_15_single_flight_coalesces_concurrent_threads(self):
        """Tests that 5 concurrent threads requesting the same cache_key trigger exactly 1 HTTP call."""
        client = AdzunaClient()
        client.app_id = "test_id"
        client.app_key = "test_key"
        client._cache.clear()
        client._inflight.clear()

        http_calls = 0
        call_lock = threading.Lock()

        def slow_mock_get(*args, **kwargs):
            nonlocal http_calls
            with call_lock:
                http_calls += 1
            # Simulate latency so all 5 threads arrive while query is in-flight
            time.sleep(0.3)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                'count': 1,
                'results': [{
                    'id': 'sf_job_1',
                    'title': 'Coalesced Role',
                    'company': {'display_name': 'Test Co'},
                    'location': {'display_name': 'Delhi'},
                    'description': 'Single flight job test',
                    'created': '2026-09-01T10:00:00Z',
                    'redirect_url': 'https://adzuna.in/details/sf1'
                }]
            }
            return mock_resp

        results_list = []
        threads = []

        def worker():
            res = client.search(q="concurrent_python", location="Delhi")
            results_list.append(res)

        with patch.object(client.session, 'get', side_effect=slow_mock_get):
            for _ in range(5):
                t = threading.Thread(target=worker)
                threads.append(t)

            for t in threads:
                t.start()

            for t in threads:
                t.join(timeout=3.0)

        # All 5 threads must succeed and obtain the same result
        self.assertEqual(len(results_list), 5)
        for res in results_list:
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]['id'], 'adzuna_sf_job_1')

        # EXACTLY 1 HTTP call was made!
        self.assertEqual(http_calls, 1)

    def test_16_search_cache_mutation_isolation(self):
        """Mutating the result of search() does NOT affect the cache or subsequent search() calls."""
        client = AdzunaClient()
        client.app_id = "test_id"
        client.app_key = "test_key"
        client._cache.clear()

        with patch.object(client.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                'count': 1,
                'results': [{
                    'id': 'm1', 'title': 'Original Title', 'description': 'Python role',
                    'company': {'display_name': 'Corp'}, 'location': {'display_name': 'Pune'},
                    'created': '2026-09-01T10:00:00Z', 'redirect_url': 'https://example.com'
                }]
            }
            mock_get.return_value = mock_resp

            # First call
            res1 = client.search(q="mutation_test")
            self.assertEqual(len(res1), 1)
            self.assertEqual(res1[0]['title'], 'Original Title')

            # Mutate res1 in place!
            res1[0]['title'] = 'MUTATED TITLE'
            res1[0]['match_score'] = 999
            res1[0]['skills'] = 'HACKED'

            # Second call (hits cache)
            res2 = client.search(q="mutation_test")
            self.assertEqual(res2[0]['title'], 'Original Title')
            self.assertNotEqual(res2[0]['title'], 'MUTATED TITLE')
            self.assertEqual(res2[0]['match_score'], 50)
            self.assertNotEqual(res2[0]['skills'], 'HACKED')

            # Check cache directly
            cache_val = list(client._cache.values())[0][1]
            self.assertEqual(cache_val[0]['title'], 'Original Title')
            self.assertNotEqual(cache_val[0]['title'], 'MUTATED TITLE')

    def test_17_concurrent_rank_jobs_no_cross_contamination(self):
        """Concurrent rank_jobs calls for two different candidates on shared list do not cross-contaminate."""
        matcher = JobMatcher()
        base_jobs = [
            {'id': '1', 'title': 'Python Developer', 'skills': 'Python, Django, SQL', 'description': 'Python dev backend', 'location': 'Pune'},
            {'id': '2', 'title': 'React Frontend Developer', 'skills': 'React, JavaScript, HTML, CSS', 'description': 'Frontend UI engineer', 'location': 'Pune'},
        ]

        cand_py_skills = ['python', 'django']
        cand_react_skills = ['react', 'javascript']

        # Baseline single runs
        alone_py = matcher.rank_jobs(cand_py_skills, base_jobs)
        alone_react = matcher.rank_jobs(cand_react_skills, base_jobs)

        expected_py_score = alone_py[0]['match_percentage']
        expected_py_skills = alone_py[0]['matching_skills']
        expected_react_score = alone_react[0]['match_percentage']
        expected_react_skills = alone_react[0]['matching_skills']

        # Run 20 iterations concurrently with ThreadPoolExecutor
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for _ in range(20):
                f_py = executor.submit(matcher.rank_jobs, cand_py_skills, base_jobs)
                f_react = executor.submit(matcher.rank_jobs, cand_react_skills, base_jobs)
                futures.append(('py', f_py))
                futures.append(('react', f_react))

            for cand_type, fut in futures:
                res = fut.result()
                if cand_type == 'py':
                    self.assertEqual(res[0]['id'], '1')
                    self.assertEqual(res[0]['match_percentage'], expected_py_score)
                    self.assertEqual(res[0]['matching_skills'], expected_py_skills)
                else:
                    self.assertEqual(res[0]['id'], '2')
                    self.assertEqual(res[0]['match_percentage'], expected_react_score)
                    self.assertEqual(res[0]['matching_skills'], expected_react_skills)

    def test_18_leader_failure_before_http_fails_fast(self):
        """When leader fails before HTTP call, followers fail fast (under 1s) via safety net."""
        from app.services.adzuna_client import AdzunaUpstreamError

        client = AdzunaClient()
        client.app_id = "test_id"
        client.app_key = "test_key"
        client.timeout = 5.0
        client.single_flight_timeout = 5.0
        client._cache.clear()
        client._inflight.clear()

        leader_in_flight = threading.Event()
        follower_exc = None
        follower_elapsed = 0.0

        def failing_get(*args, **kwargs):
            leader_in_flight.set()
            time.sleep(0.05)
            raise RuntimeError("Leader crash before HTTP response")

        with patch.object(client.session, 'get', side_effect=failing_get):
            def leader_task():
                try:
                    client.search(q="fail_fast_test")
                except Exception:
                    pass

            def follower_task():
                nonlocal follower_exc, follower_elapsed
                leader_in_flight.wait(timeout=2.0)
                t0 = time.time()
                try:
                    client.search(q="fail_fast_test")
                except Exception as e:
                    follower_exc = e
                finally:
                    follower_elapsed = time.time() - t0

            t_leader = threading.Thread(target=leader_task)
            t_follower = threading.Thread(target=follower_task)

            t_leader.start()
            t_follower.start()

            t_leader.join(timeout=2.0)
            t_follower.join(timeout=2.0)

            # Follower must fail in under 1.0 second, NOT after the 5s timeout
            self.assertLess(follower_elapsed, 1.0)
            self.assertIsNotNone(follower_exc)
            self.assertIsInstance(follower_exc, AdzunaUpstreamError)


if __name__ == '__main__':
    unittest.main()
