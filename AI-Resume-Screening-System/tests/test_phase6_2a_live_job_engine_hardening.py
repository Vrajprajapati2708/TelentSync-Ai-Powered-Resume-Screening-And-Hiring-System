# ============================================================
#  HireAI / TalentSync — Phase 6.2A Regression Tests
#  Covers DEFECT A (Experience Matching) & DEFECT B (Frontend Flow)
# ============================================================

import os
import sys
import unittest

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from app import create_app
from app.config.settings import TestingConfig
from app.ai.job_matcher import JobMatcher
from app.controllers.auth_controller import register_user


class TestPhase62AExperienceMatching(unittest.TestCase):
    """DEFECT A: Unit tests for explainable experience parsing and scoring."""

    def setUp(self):
        self.matcher = JobMatcher()

    def test_01_candidate_experience_changes_score(self):
        job_desc = "Looking for a Senior Python Developer with 5+ years of experience."
        score_5yr = self.matcher._calc_experience(job_desc, "5 years")
        score_1yr = self.matcher._calc_experience(job_desc, "1 year")
        self.assertGreater(score_5yr, score_1yr)
        self.assertAlmostEqual(score_5yr, 1.0, places=2)
        self.assertLessEqual(score_1yr, 0.3)

    def test_02_job_requirement_changes_score(self):
        candidate_exp = "3 years"
        score_job_3yr = self.matcher._calc_experience("Requirement: 3 years experience", candidate_exp)
        score_job_7yr = self.matcher._calc_experience("Requirement: 7+ years of experience", candidate_exp)
        self.assertGreater(score_job_3yr, score_job_7yr)
        self.assertEqual(score_job_3yr, 1.0)

    def test_03_exact_match_higher_than_insufficient(self):
        job_desc = "Minimum 4 years required in React development."
        score_exact = self.matcher._calc_experience(job_desc, "4 years")
        score_insufficient = self.matcher._calc_experience(job_desc, "2 years")
        self.assertEqual(score_exact, 1.0)
        self.assertAlmostEqual(score_insufficient, 0.45, places=2)  # 0.9 * (2/4) = 0.45
        self.assertGreater(score_exact, score_insufficient)

    def test_04_excess_candidate_experience_handled_sensibly(self):
        job_desc = "Software Engineer with 2-4 years experience."
        score_in_range = self.matcher._calc_experience(job_desc, "4 years")
        score_excess_7yr = self.matcher._calc_experience(job_desc, "7 years")
        self.assertEqual(score_in_range, 1.0)
        self.assertGreaterEqual(score_excess_7yr, 0.85)
        self.assertLessEqual(score_excess_7yr, 1.0)

    def test_05_fresher_and_fresher_compatible_jobs(self):
        job_fresher = "Entry level Software Trainee. Freshers welcome to apply!"
        job_senior = "Senior Architect with 8+ years required."

        score_fresher_welcome = self.matcher._calc_experience(job_fresher, "Fresher")
        score_fresher_senior_job = self.matcher._calc_experience(job_senior, "Fresher")

        self.assertEqual(score_fresher_welcome, 1.0)
        self.assertLessEqual(score_fresher_senior_job, 0.1)

    def test_06_missing_experience_requirement_does_not_crash(self):
        job_desc = "Fast growing startup looking for enthusiastic developer to build features."
        score_cand_exp = self.matcher._calc_experience(job_desc, "3 years")
        score_no_info = self.matcher._calc_experience(job_desc, None)
        self.assertEqual(score_cand_exp, 0.80)
        self.assertEqual(score_no_info, 0.75)

    def test_07_malformed_experience_text_does_not_crash(self):
        malformed_cand = "Lots of passion and coffee! None numeric."
        malformed_job = "Experience is a plus but not explicitly quantified."
        score = self.matcher._calc_experience(malformed_job, malformed_cand)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_08_score_bounds_always_zero_to_one(self):
        test_inputs = [
            ("100 years", "1 year required"),
            ("0.1 years", "20 years required"),
            ("negative", "5 years"),
            ("", ""),
            (None, None),
            (10, "5 years"),
            (0, "freshers only")
        ]
        for c_exp, j_desc in test_inputs:
            sc = self.matcher._calc_experience(j_desc, c_exp)
            self.assertGreaterEqual(sc, 0.0, f"Failed for {c_exp}, {j_desc}")
            self.assertLessEqual(sc, 1.0, f"Failed for {c_exp}, {j_desc}")

    def test_09_final_match_percentage_changes_with_experience(self):
        test_job = [{
            'id': 'j1',
            'title': 'Python Developer',
            'company': 'Alpha Tech',
            'location': 'Bangalore',
            'description': 'Python developer position. Minimum 5 years of experience required.',
            'skills': 'Python, Django',
            'salary_min': 1200000,
            'posted_date': '2026-09-01'
        }]

        ranked_5yr = self.matcher.rank_jobs(['Python', 'Django'], list(test_job), user_prefs={'experience': '5 years'})
        ranked_1yr = self.matcher.rank_jobs(['Python', 'Django'], list(test_job), user_prefs={'experience': '1 year'})

        score_5 = ranked_5yr[0]['match_percentage']
        score_1 = ranked_1yr[0]['match_percentage']

        self.assertGreater(score_5, score_1)
        self.assertEqual(ranked_5yr[0]['experience_score'], 1.0)
        self.assertAlmostEqual(ranked_1yr[0]['experience_score'], 0.18, places=2)


class TestPhase62ACandidateFrontendContract(unittest.TestCase):
    """DEFECT B: Contract and API tests for candidate job fetching."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()

    def test_10_candidate_cannot_call_admin_jobs_endpoint(self):
        """Proves /api/admin/jobs rejects candidates with HTTP 403."""
        email = "cand_contract_403@test.com"
        register_user("Candidate User", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        res = self.client.get('/api/admin/jobs')
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data.get('success', True))
        self.assertIsInstance(data, dict)

    def test_11_candidate_uses_match_jobs_endpoint(self):
        """Proves candidates successfully access /api/match_jobs."""
        email = "cand_match_ok@test.com"
        register_user("Candidate Ok", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        mock_jobs = [{
            'id': 'adzuna_123',
            'title': 'Python Developer',
            'company': 'Tech Corp',
            'location': 'Bangalore',
            'description': 'Python Developer 3+ years experience with Django',
            'skills': 'Python, Django',
            'salary_min': 1000000,
            'posted_date': '2026-09-01',
            'apply_url': 'https://www.adzuna.in/details/123'
        }]

        from unittest.mock import patch
        with patch('app.services.adzuna_service.AdzunaService.fetch_live_jobs', return_value=mock_jobs):
            res = self.client.post('/api/match_jobs', json={'skills': ['Python', 'SQL'], 'experience': '3 years'})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get('success'))
            self.assertIn('jobs', data)
            self.assertIsInstance(data['jobs'], list)
            self.assertEqual(data.get('source'), 'adzuna')
            self.assertGreater(len(data['jobs']), 0)
            self.assertEqual(data['jobs'][0]['experience_score'], 1.0)

    def test_12_empty_skills_falls_back_to_local_without_crash(self):
        """Proves empty skills payload does not crash and returns local jobs."""
        email = "cand_empty_skills@test.com"
        register_user("Candidate Empty", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        res = self.client.post('/api/match_jobs', json={'skills': []})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIsInstance(data.get('jobs'), list)

    def test_13_apply_external_job_redirect_contract(self):
        """Proves Apply on external job returns redirect status and genuine URL."""
        email = "cand_apply_ext@test.com"
        register_user("Candidate Apply", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        ext_url = "https://www.adzuna.in/details/5867114856"
        res = self.client.post('/api/apply', json={
            'job_id': 'adzuna_5867114856',
            'is_external': True,
            'apply_url': ext_url,
            'match_score': 90
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('status'), 'external_redirected')
        self.assertEqual(data.get('redirect_url'), ext_url)

    def test_14_anonymous_match_jobs_returns_401_authentication_required(self):
        """Proves anonymous requests to /api/match_jobs are rejected with 401 (auth state, not network failure)."""
        res = self.client.post('/api/match_jobs', json={'skills': ['Python']})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data.get('success', True))
        self.assertIn('Authentication required', data.get('message', ''))

    def test_15_landing_page_and_public_stats_accessible_anonymously(self):
        """Proves public landing routes succeed without requiring authentication."""
        res_root = self.client.get('/')
        self.assertEqual(res_root.status_code, 200)

        res_stats = self.client.get('/api/auth/landing_stats')
        self.assertEqual(res_stats.status_code, 200)
        data = res_stats.get_json()
        self.assertIn('resumes_analyzed', data)
        self.assertIn('jobs_matched', data)

    def test_16_authenticated_candidate_resolves_profile_experience_automatically(self):
        """Proves candidate profile experience is utilized by match_jobs when omitted from request body."""
        email = "cand_auto_exp@test.com"
        register_user("Candidate Auto", email, "Password123!", role="candidate", is_verified=1)
        self.client.post('/api/auth/login', json={'email': email, 'password': 'Password123!'})

        # Attach structured resume intelligence with 4 years experience
        from app.database.connection import get_db
        import json
        import uuid
        with get_db() as conn:
            user = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            u_id = user['id']
            s_json = json.dumps({'total_experience_years': 4.0, 'experience': [{'duration': '4 years'}]})
            unique_key = uuid.uuid4().hex[:8]
            conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, word_count, ats_score, extracted_skills, structured_json, status, version)
                   VALUES (?, 'cv.pdf', ?, ?, ?, 100, 'application/pdf', 'Python Developer', 100, 80, 'Python, Django', ?, 'processed', 1)""",
                (u_id, f"cv_{u_id}_{unique_key}.pdf", f"/tmp/cv_{unique_key}.pdf", f"hash_{unique_key}", s_json)
            )
            conn.commit()

        mock_job = [{
            'id': 'adzuna_exp_test',
            'title': 'Python Developer',
            'company': 'Tech Corp',
            'location': 'Bangalore',
            'description': 'Python Developer minimum 4 years experience required',
            'skills': 'Python, Django',
            'salary_min': 1000000,
            'posted_date': '2026-09-01',
            'apply_url': 'https://www.adzuna.in/details/exp_test'
        }]

        from unittest.mock import patch
        with patch('app.services.adzuna_service.AdzunaService.fetch_live_jobs', return_value=mock_job):
            res = self.client.post('/api/match_jobs', json={'skills': ['Python', 'Django']})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get('success'))
            jobs = data.get('jobs', [])
            self.assertGreater(len(jobs), 0)
            # Automatic resolution should match 4 years to 4 years requirement -> 1.0 experience score
            self.assertEqual(jobs[0].get('experience_score'), 1.0)


if __name__ == '__main__':
    unittest.main()
