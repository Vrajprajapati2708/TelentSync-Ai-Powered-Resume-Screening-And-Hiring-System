import unittest
import time
from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.ml.ats.ats_checker import compute_ats_score
from app.ml.recommendation.recommend_jobs import recommend_jobs


SAMPLE_JOBS = [
    {
        'id': 1,
        'title': 'Senior DevOps Engineer',
        'company': 'CloudOps',
        'skills': 'Docker, Kubernetes, AWS, Terraform',
        'description': 'Manage scalable Kubernetes clusters in AWS with Terraform and Docker',
        'status': 'Active'
    },
    {
        'id': 2,
        'title': 'Python Backend Engineer',
        'company': 'TechFlow',
        'skills': 'Python, Flask, PostgreSQL',
        'description': 'Develop backend web services using Python, Flask and SQL databases',
        'status': 'Active'
    }
]


class TestStep2HideAnswerSheet(unittest.TestCase):
    """
    Test Step 2: Information Hiding on Candidate-Facing Endpoints.
    Verifies that candidate-facing endpoints do not leak exact missing keywords
    or matching keyword answer sheets for target jobs, providing coarse bands
    and general hygiene tips only, while preserving full diagnostics on HR endpoints.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_ats_checker_candidate_view_does_not_leak_missing_keywords(self):
        """Candidate-facing ATS suggestions must NOT reveal exact missing keywords."""
        resume_text = """
        Rahul Sharma | rahul@test.com | +91 9876543210
        Education: B.Tech Computer Science
        Experience: 2 years building backend apps in Python and Flask
        Skills: Python, Flask, SQL, Git
        """
        target_job_skills = ['Docker', 'Kubernetes', 'AWS', 'Terraform']

        # Candidate view (is_hr=False by default)
        result = compute_ats_score(resume_text, job_skills=target_job_skills, is_hr=False)

        # Check suggestions: must NOT leak "Add missing keywords: Docker..."
        for s in result['suggestions']:
            self.assertNotIn("Add missing keywords", s, f"Leaked exact keywords: {s}")
            self.assertNotIn("Docker", s, f"Leaked specific skill 'Docker': {s}")
            self.assertNotIn("Kubernetes", s, f"Leaked specific skill 'Kubernetes': {s}")

        # Check structure: must provide coarse band and withhold missing_skills
        self.assertIn('match_band', result)
        self.assertIn(result['match_band'], ['Low Alignment', 'Moderate Alignment', 'High Alignment'])
        self.assertNotIn('missing_skills', result)

    def test_ats_checker_hr_view_preserves_exact_missing_skills(self):
        """HR recruiter view (is_hr=True) must preserve exact missing skills for inspection."""
        resume_text = "Skills: Python, Flask"
        target_job_skills = ['Docker', 'Kubernetes']

        hr_result = compute_ats_score(resume_text, job_skills=target_job_skills, is_hr=True)

        self.assertIn('missing_skills', hr_result)
        self.assertEqual(sorted(hr_result['missing_skills']), ['Docker', 'Kubernetes'])
        self.assertIn('matched_skills', hr_result)
        self.assertIn('keyword_match', hr_result)

    def test_recommend_jobs_candidate_view_hides_missing_skills(self):
        """Candidate-facing job recommendations must NOT return exact missing_skills or matched_skills."""
        cand_skills = ['Python', 'Flask']

        # Candidate view (for_hr=False by default)
        recs = recommend_jobs(cand_skills, SAMPLE_JOBS, for_hr=False)
        self.assertGreater(len(recs), 0)

        for job in recs:
            # Must NOT expose exact missing skills list
            self.assertEqual(job.get('missing_skills'), [], f"Leaked missing_skills to candidate: {job.get('missing_skills')}")
            self.assertEqual(job.get('matched_skills'), [], f"Leaked matched_skills to candidate: {job.get('matched_skills')}")
            # Must provide coarse match band and summary counts
            self.assertIn('match_band', job)
            self.assertIn(job['match_band'], ['High Match', 'Moderate Match', 'Potential Match'])
            self.assertIn('missing_skills_count', job)
            self.assertIn('matched_skills_count', job)

    def test_recommend_jobs_hr_view_preserves_exact_lists(self):
        """HR view (for_hr=True) of job recommendations preserves exact lists."""
        cand_skills = ['Python', 'Flask']

        hr_recs = recommend_jobs(cand_skills, SAMPLE_JOBS, for_hr=True)
        self.assertGreater(len(hr_recs), 0)

        python_job = next((j for j in hr_recs if 'Python' in j['title']), None)
        self.assertIsNotNone(python_job)
        self.assertIn('PostgreSQL', python_job['missing_skills'])
        self.assertIn('Python', python_job['matched_skills'])

    def test_candidate_job_search_endpoint_does_not_leak_matched_skills(self):
        """GET /api/jobs/search for candidates returns coarse match_band and empty matched_skills."""
        ts = int(time.time() * 1000)
        cand_email = f"search_cand_{ts}@test.com"
        register_user("Candidate Tester", cand_email, "Password123!", role="candidate", is_verified=1)

        with get_db() as conn:
            conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status) 
                   VALUES ('Kubernetes Lead', 'ScaleCorp', 'Kubernetes, Go, AWS', 'Lead Kubernetes infra', 'Active')"""
            )
            conn.commit()

        # Login as candidate
        login_res = self.client.post('/api/auth/login', json={'email': cand_email, 'password': 'Password123!'})
        self.assertEqual(login_res.status_code, 200)

        res = self.client.get('/api/jobs/search?q=Kubernetes')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))

        for j in data.get('jobs', []):
            self.assertEqual(j.get('matched_skills'), [], "Candidate search endpoint leaked matched_skills!")
            self.assertIn('match_band', j)


if __name__ == '__main__':
    unittest.main()
