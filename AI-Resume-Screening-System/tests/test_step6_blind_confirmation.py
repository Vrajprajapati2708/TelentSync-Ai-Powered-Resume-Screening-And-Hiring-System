import os
import time
import json
import unittest
from flask import session

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.services.candidate_skills_service import (
    get_candidate_skills,
    declare_blind_skills,
    remove_candidate_skill,
    sync_resume_extracted_skills
)
from app.ml.ranking.ranking_engine import (
    compute_candidate_score,
    rank_candidates,
    EVIDENCE_WEIGHTS
)
from app.services.jobs_search_service import JobsSearchService


class TestStep6BlindSkillConfirmation(unittest.TestCase):
    """
    Test Step 6: Blind Skill Confirmation.
    Verifies that:
    1. Unauthenticated users cannot view or declare candidate skills (HTTP 401).
    2. Candidates can declare skills blindly before viewing job gaps or recommendation feedback.
    3. Blind self-declared skills receive an evidence weight of 0.2 (unverified self-claim).
    4. Non-degradation rule: Declaring an existing high-confidence skill (1.0 or 0.7) does not downgrade it to 0.2.
    5. Duplicate skill entries and case variations are deduplicated safely.
    6. Empty or invalid skill inputs return validation errors (HTTP 400).
    7. Candidates can remove a self-declared skill from their profile.
    8. Ranking engine recognizes 'self_declared' skills with 0.2 weight in candidate scoring.
    9. Jobs search service seamlessly integrates confirmed skills from candidate_skills.
    10. HR recruiters can inspect candidate skill provenance (experience vs self-declared vs verified) via admin endpoint.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_unauthenticated_request_rejected(self):
        """Anonymous requests to view or declare skills return HTTP 401."""
        res_get = self.client.get('/api/user/skills')
        self.assertEqual(res_get.status_code, 401)

        res_post = self.client.post('/api/user/skills/confirm', json={'skills': ['Docker']})
        self.assertEqual(res_post.status_code, 401)

    def test_get_candidate_skills_for_new_candidate(self):
        """Authenticated candidate can query their skills."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_get_{ts}@test.com"
        cand_id = register_user("New Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        res = self.client.get('/api/user/skills')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user_id'], cand_id)
        self.assertIsInstance(data['skills'], list)

    def test_blind_skill_declaration_adds_skills_with_02_weight(self):
        """Candidate can declare skills blindly, receiving 0.2 evidence weight."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_blind_{ts}@test.com"
        cand_id = register_user("Blind Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        # Candidate declares Docker and Kubernetes blindly
        res = self.client.post('/api/user/skills/confirm', json={'skills': ['Docker', 'Kubernetes']})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('Docker', data['added'])
        self.assertIn('Kubernetes', data['added'])

        # Verify DB records in candidate_skills
        with get_db() as conn:
            rows = conn.execute(
                "SELECT skill, source, confidence FROM candidate_skills WHERE user_id=? ORDER BY skill ASC",
                (cand_id,)
            ).fetchall()

            skill_dict = {r['skill']: (r['source'], r['confidence']) for r in rows}
            self.assertIn('Docker', skill_dict)
            self.assertIn('Kubernetes', skill_dict)
            self.assertEqual(skill_dict['Docker'], ('self_declared', 0.2))
            self.assertEqual(skill_dict['Kubernetes'], ('self_declared', 0.2))

            # Verify users.skills is synced
            u_row = conn.execute("SELECT skills FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertIn('Docker', u_row['skills'])
            self.assertIn('Kubernetes', u_row['skills'])

    def test_non_degradation_rule_preserves_high_confidence(self):
        """Existing 1.0 or 0.7 confidence skills are never downgraded to 0.2 when blindly declared."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_degrade_{ts}@test.com"
        cand_id = register_user("Degrade Test", cand_email, "Password123!", "candidate")["user"]["id"]

        # Insert a skill with 1.0 confidence (from experience)
        with get_db() as conn:
            conn.execute(
                """INSERT INTO candidate_skills (user_id, skill, source, confidence, confirmed_at)
                   VALUES (?, 'Python', 'experience', 1.0, datetime('now'))""",
                (cand_id,)
            )
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        # Candidate blindly declares 'Python' and 'Docker'
        res = self.client.post('/api/user/skills/confirm', json={'skills': ['Python', 'Docker']})
        self.assertEqual(res.status_code, 200)

        # Check DB
        with get_db() as conn:
            rows = conn.execute(
                "SELECT skill, source, confidence FROM candidate_skills WHERE user_id=? ORDER BY skill ASC",
                (cand_id,)
            ).fetchall()

            res_map = {r['skill']: (r['source'], r['confidence']) for r in rows}
            # Python MUST retain confidence=1.0 and source='experience'
            self.assertEqual(res_map['Python'], ('experience', 1.0))
            # Docker is newly self_declared with 0.2
            self.assertEqual(res_map['Docker'], ('self_declared', 0.2))

    def test_case_insensitive_deduplication(self):
        """Submitting duplicate skill names with differing casing creates only one row."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_dedup_{ts}@test.com"
        cand_id = register_user("Dedup Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        res = self.client.post('/api/user/skills/confirm', json={'skills': ['redis', 'Redis', 'REDIS']})
        self.assertEqual(res.status_code, 200)

        with get_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM candidate_skills WHERE user_id=? AND LOWER(skill)='redis'",
                (cand_id,)
            ).fetchone()[0]
            self.assertEqual(count, 1)

    def test_validation_rejects_empty_or_invalid_skills(self):
        """Empty array, empty strings, or missing parameters return HTTP 400."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_val_{ts}@test.com"
        cand_id = register_user("Val Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        # Missing payload
        res1 = self.client.post('/api/user/skills/confirm', json={})
        self.assertEqual(res1.status_code, 400)

        # Empty list
        res2 = self.client.post('/api/user/skills/confirm', json={'skills': []})
        self.assertEqual(res2.status_code, 400)

        # List of only blank spaces
        res3 = self.client.post('/api/user/skills/confirm', json={'skills': ['   ', '']})
        self.assertEqual(res3.status_code, 400)

    def test_remove_candidate_skill(self):
        """Candidate can remove a self-declared skill."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_del_{ts}@test.com"
        cand_id = register_user("Del Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        # Add Docker and Terraform
        self.client.post('/api/user/skills/confirm', json={'skills': ['Docker', 'Terraform']})

        # Remove Docker
        del_res = self.client.delete('/api/user/skills/Docker')
        self.assertEqual(del_res.status_code, 200)

        with get_db() as conn:
            skills = [r[0] for r in conn.execute("SELECT skill FROM candidate_skills WHERE user_id=?", (cand_id,)).fetchall()]
            self.assertNotIn('Docker', skills)
            self.assertIn('Terraform', skills)

            # Check users.skills synced
            u_row = conn.execute("SELECT skills FROM users WHERE id=?", (cand_id,)).fetchone()
            self.assertNotIn('Docker', u_row['skills'])
            self.assertIn('Terraform', u_row['skills'])

        # Deleting a non-existent skill returns 404
        bad_del = self.client.delete('/api/user/skills/NonExistentSkill')
        self.assertEqual(bad_del.status_code, 404)

    def test_ranking_engine_evidence_weight_for_blind_confirmed_skill(self):
        """Ranking engine gives 0.2 weight to blind self-declared skills and marks source as 'self_declared'."""
        job_skills = ["Python", "Docker", "AWS"]

        cand = {
            "name": "Hybrid Evidence Candidate",
            "ats_score": 80,
            "education": "B.Tech",
            "experience_lines": [
                "Built core data engineering pipelines in Python with high performance."
            ],
            "self_declared_skills": ["Docker"]
        }

        score = compute_candidate_score(cand, job_skills)

        # Python: Matched in experience narrative -> 1.0 weight
        self.assertEqual(score["skill_evidence"]["Python"]["weight"], 1.0)
        self.assertEqual(score["skill_evidence"]["Python"]["source"], "experience")

        # Docker: Blind self-declared -> 0.2 weight
        self.assertEqual(score["skill_evidence"]["Docker"]["weight"], 0.2)
        self.assertEqual(score["skill_evidence"]["Docker"]["source"], "self_declared")

        # AWS: Missing -> 0.0 weight
        self.assertEqual(score["skill_evidence"]["AWS"]["weight"], 0.0)
        self.assertEqual(score["skill_evidence"]["AWS"]["source"], "missing")

        # Overlap ratio = (1.0 + 0.2 + 0.0) / 3 = 1.2 / 3 = 0.40 -> 16 points out of 40
        self.assertEqual(score["skills_score"], 16)
        self.assertEqual(score["evidence_counts"]["experience"], 1)
        self.assertEqual(score["evidence_counts"]["self_declared"], 1)
        self.assertEqual(score["evidence_counts"]["missing"], 1)

    def test_jobs_search_incorporates_blind_confirmed_skills(self):
        """Jobs search service resolves candidate profile including blind confirmed skills."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_search_{ts}@test.com"
        cand_id = register_user("Search Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        # Declare blind skills directly via service
        declare_blind_skills(cand_id, ['FastAPI', 'PostgreSQL'])

        search_service = JobsSearchService()
        skills, exp, loc, has_resume = search_service.resolve_candidate_profile(cand_id)

        self.assertIn('FastAPI', skills)
        self.assertIn('PostgreSQL', skills)

    def test_hr_candidate_skills_provenance_view(self):
        """HR recruiter can inspect candidate skill provenance, while non-HR users are blocked."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_target_{ts}@test.com"
        cand_id = register_user("Target Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        # Declare skills
        declare_blind_skills(cand_id, ['Docker', 'Kubernetes'])

        # Create HR user
        hr_email = f"hr_prov_{ts}@test.com"
        hr_id = register_user("HR Reviewer", hr_email, "Password123!", "hr", allow_privileged=True, is_verified=1)["user"]["id"]

        # Candidate cannot access HR candidate endpoint
        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        cand_access = self.client.get(f'/api/admin/candidate/{cand_id}/skills')
        self.assertEqual(cand_access.status_code, 403)

        # HR can access endpoint and see skill provenance breakdown
        with self.client.session_transaction() as sess:
            sess["user_id"] = hr_id
            sess["role"] = "hr"

        hr_res = self.client.get(f'/api/admin/candidate/{cand_id}/skills')
        self.assertEqual(hr_res.status_code, 200)
        hr_data = hr_res.get_json()
        self.assertTrue(hr_data['success'])
        self.assertEqual(hr_data['user_id'], cand_id)
        self.assertGreaterEqual(hr_data['total_count'], 2)

        skill_names = [s['skill'] for s in hr_data['skills']]
        self.assertIn('Docker', skill_names)
        self.assertIn('Kubernetes', skill_names)
        docker_entry = next(s for s in hr_data['skills'] if s['skill'] == 'Docker')
        self.assertEqual(docker_entry['source'], 'self_declared')
        self.assertEqual(docker_entry['confidence'], 0.2)


if __name__ == "__main__":
    unittest.main()
