# ============================================================
#  TalentSync — Platform Admin ML Pipeline & Diagnostics Test Suite
#  Verifies:
#    - GET  /api/ml/status (telemetry, versions, models loaded)
#    - POST /api/ml/pipeline (live diagnostics playground inference & DB fallback)
#    - POST /api/ml/cache/flush (in-memory cache purges)
#    - POST /api/ml/train (background model retraining trigger)
#    - Role-based authorization & security isolation
# ============================================================

import json
import time
import unittest
from werkzeug.security import generate_password_hash

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db


class TestPlatformAdminMLPipeline(unittest.TestCase):
    """Test suite for AI/ML Pipeline management and Live Inference Diagnostics."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # Seed admin and candidate users with unique emails
        self.admin_id, self.admin_email = self._create_user("Admin Master", "admin")
        self.candidate_id, self.candidate_email = self._create_user("Candidate Jane", "candidate")

        # Seed sample active job in DB
        with get_db() as conn:
            conn.execute("""
                INSERT INTO jobs (title, company, description, skills, location, type, salary, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "Senior Python & ML Engineer",
                "TalentSync AI Labs",
                "Lead ML pipeline architecture, NER fine-tuning, and scalable inference microservices.",
                "Python, PyTorch, Scikit-learn, spaCy, Docker, FastAPI, PostgreSQL",
                "San Francisco, CA",
                "Full-time",
                "$160,000 - $190,000",
                "Active"
            ))
            conn.commit()

    def tearDown(self):
        self.app_context.pop()

    def _unique_email(self, prefix="ml_test"):
        return f"{prefix}_{int(time.time() * 1000000)}_{id(self)}@talentsync.io"

    def _create_user(self, name: str, role: str) -> tuple[int, str]:
        email = self._unique_email(role)
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, password, role, is_verified) VALUES (?, ?, ?, ?, 1)",
                (name, email, generate_password_hash("SecretPass123!"), role)
            )
            conn.commit()
            return cur.lastrowid, email

    def _login_as(self, email: str, role: str):
        with self.client.session_transaction() as sess:
            sess['user_email'] = email
            sess['user_role'] = role
            sess['user_id'] = self.admin_id if role == 'admin' else self.candidate_id

    def test_ml_status_endpoint_authorized(self):
        """GET /api/ml/status returns full model telemetry and runtime stack for admin."""
        self._login_as(self.admin_email, "admin")
        res = self.client.get("/api/ml/status")
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertIn("status", data)
        self.assertIn("models", data)
        self.assertIn("spacy_ner", data["models"])
        self.assertIn("tfidf_recommender", data["models"])
        self.assertIn("version_info", data)
        self.assertIn("python", data["version_info"])
        self.assertIn("models_loaded", data)

    def test_ml_status_unauthorized_for_candidate(self):
        """GET /api/ml/status rejects non-admin users."""
        self._login_as(self.candidate_email, "candidate")
        res = self.client.get("/api/ml/status")
        self.assertIn(res.status_code, [401, 403])

    def test_live_ml_inference_playground(self):
        """POST /api/ml/pipeline processes raw resume text and automatically recommends matching DB jobs."""
        self._login_as(self.admin_email, "admin")
        resume_payload = """
        DR. JANE DOE
        Machine Learning Engineer
        jane@example.com | 555-0199 | San Francisco, CA

        SUMMARY
        Expert ML Engineer with extensive experience in Python, PyTorch, Scikit-learn, and spaCy NER models.

        SKILLS
        Python, PyTorch, Scikit-learn, spaCy, Docker, FastAPI, PostgreSQL, SQL, Machine Learning, NLP

        EXPERIENCE
        Senior ML Scientist | AI Vanguard | 2021 - Present
        - Built scalable NLP pipelines and recommendation engines.

        EDUCATION
        B.S. in Computer Science | Stanford University (2016 - 2020)
        """

        res = self.client.post(
            "/api/ml/pipeline",
            data=json.dumps({"resume_text": resume_payload, "top_n": 5}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("skills", data)
        self.assertIn("ats", data)
        self.assertIn("recommendations", data)
        self.assertIn("pipeline_meta", data)

        # Verify extracted skills
        skills_upper = [s.lower() for s in data["skills"]]
        self.assertTrue(any("python" in s for s in skills_upper))

        # Verify ATS scoring structure
        self.assertIn("score", data["ats"])
        self.assertGreaterEqual(data["ats"]["score"], 50)

        # Verify recommendation was matched from active DB jobs
        self.assertGreaterEqual(len(data["recommendations"]), 1)
        top_job = data["recommendations"][0]
        self.assertIn("title", top_job)
        self.assertIn("score", top_job)
        self.assertGreater(top_job["score"], 0.2)

    def test_live_ml_inference_validation_error(self):
        """POST /api/ml/pipeline with empty payload returns 400 Bad Request."""
        self._login_as(self.admin_email, "admin")
        res = self.client.post(
            "/api/ml/pipeline",
            data=json.dumps({"resume_text": ""}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)

    def test_flush_ml_cache_endpoint(self):
        """POST /api/ml/cache/flush clears in-memory model caches and returns success."""
        self._login_as(self.admin_email, "admin")
        res = self.client.post("/api/ml/cache/flush", content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("flushed", data.get("message", "").lower())

    def test_trigger_ml_training_endpoint(self):
        """POST /api/ml/train starts background retraining worker."""
        self._login_as(self.admin_email, "admin")
        res = self.client.post(
            "/api/ml/train",
            data=json.dumps({"skip_ner": True}),
            content_type="application/json"
        )
        # Should return 200 (if already running) or 202 Accepted (when started)
        self.assertIn(res.status_code, [200, 202])
        data = res.get_json()
        self.assertTrue(data.get("running") is True or "Training" in data.get("message", "") or "started" in data.get("message", ""))


if __name__ == "__main__":
    unittest.main()
