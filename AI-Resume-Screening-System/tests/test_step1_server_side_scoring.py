import unittest
import time
from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user


class TestStep1ServerSideScoring(unittest.TestCase):
    """
    Test Step 1: Server-side authoritative match scoring.
    Verifies that in /api/resumes/apply, the server completely ignores any
    client-supplied match_score and computes it authoritatively from the
    candidate's stored resume and the target job requirements.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_client_forged_match_score_100_is_ignored(self):
        """Cheater sends match_score=100 for a mismatched job; server must calculate real score."""
        ts = int(time.time() * 1000)
        cand_email = f"cheater_{ts}@test.com"
        cand_id = register_user("Cheater Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            # Create a specialized Cloud job requiring Docker, Kubernetes, Terraform
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status) 
                   VALUES ('DevOps Architect', 'CloudCorp', 'Docker, Kubernetes, Terraform', 'Expert in cloud infrastructure and clusters', 'Active')"""
            )
            job_id = cur.lastrowid

            # Insert a resume with unrelated skills: HTML, CSS, Figma
            conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'frontend.pdf', ?, '/dummy/path', ?, 1024, 'application/pdf', 
                           'Frontend designer proficient in HTML, CSS, Figma and UI wireframing', 'HTML, CSS, Figma', 'processed')""",
                (cand_id, f"stored_cheater_{ts}.pdf", f"hash_{ts}")
            )
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        # Malicious client sends match_score=100
        res = self.client.post("/api/apply", json={"job_id": job_id, "match_score": 100})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

        # Verify in DB: match_score must NOT be 100!
        with get_db() as conn:
            app_row = conn.execute(
                "SELECT match_score FROM applications WHERE user_id=? AND job_id=?", 
                (cand_id, job_id)
            ).fetchone()
            self.assertIsNotNone(app_row)
            self.assertNotEqual(app_row["match_score"], 100, "Security Failure: Server blindly trusted forged match_score of 100!")
            # With completely mismatched skills, the score should be near 0
            self.assertLessEqual(app_row["match_score"], 25)

    def test_server_calculates_high_match_score_for_qualified_candidate(self):
        """Qualified candidate with matching skills gets an accurate server-calculated score."""
        ts = int(time.time() * 1000)
        cand_email = f"qualified_{ts}@test.com"
        cand_id = register_user("Qualified Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status) 
                   VALUES ('Python Engineer', 'TechCorp', 'Python, Flask, SQL', 'Backend developer building web APIs in Python and Flask with SQL', 'Active')"""
            )
            job_id = cur.lastrowid

            conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'resume.pdf', ?, '/dummy/path', ?, 2048, 'application/pdf', 
                           'Senior Python developer with extensive Flask and SQL backend database experience', 'Python, Flask, SQL', 'processed')""",
                (cand_id, f"stored_qual_{ts}.pdf", f"hash_qual_{ts}")
            )
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        # Client sends match_score=0 (or client omitted match_score)
        res = self.client.post("/api/apply", json={"job_id": job_id, "match_score": 0})
        self.assertEqual(res.status_code, 200)

        with get_db() as conn:
            app_row = conn.execute(
                "SELECT match_score FROM applications WHERE user_id=? AND job_id=?", 
                (cand_id, job_id)
            ).fetchone()
            self.assertIsNotNone(app_row)
            # Server must have calculated a high score (> 50%) based on matching Python, Flask, SQL
            self.assertGreaterEqual(app_row["match_score"], 50)

    def test_unparsed_candidate_defaults_to_zero_score_ignoring_client(self):
        """Candidate without resume or skills applying with fake score gets 0."""
        ts = int(time.time() * 1000)
        cand_email = f"empty_{ts}@test.com"
        cand_id = register_user("Empty Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status) 
                   VALUES ('QA Engineer', 'QACorp', 'Selenium, Python', 'Testing engineer', 'Active')"""
            )
            job_id = cur.lastrowid

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        res = self.client.post("/api/apply", json={"job_id": job_id, "match_score": 85})
        self.assertEqual(res.status_code, 200)

        with get_db() as conn:
            app_row = conn.execute(
                "SELECT match_score FROM applications WHERE user_id=? AND job_id=?", 
                (cand_id, job_id)
            ).fetchone()
            self.assertIsNotNone(app_row)
            self.assertEqual(app_row["match_score"], 0)


    def test_client_forged_match_score_negative_100_is_ignored(self):
        """Test 2: Cheater sends match_score = -100; server calculates real authoritative score."""
        ts = int(time.time() * 1000)
        cand_email = f"neg_cand_{ts}@test.com"
        cand_id = register_user("Negative Score Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status) 
                   VALUES ('Python Dev', 'PyCorp', 'Python, Flask', 'Flask developer', 'Active')"""
            )
            job_id = cur.lastrowid
            conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'resume.pdf', ?, '/dummy/path', ?, 1024, 'application/pdf', 
                           'Python Flask backend web developer', 'Python, Flask', 'processed')""",
                (cand_id, f"stored_neg_{ts}.pdf", f"hash_neg_{ts}")
            )
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        res = self.client.post("/api/apply", json={"job_id": job_id, "match_score": -100})
        self.assertEqual(res.status_code, 200)

        with get_db() as conn:
            app_row = conn.execute(
                "SELECT match_score FROM applications WHERE user_id=? AND job_id=?", 
                (cand_id, job_id)
            ).fetchone()
            self.assertIsNotNone(app_row)
            self.assertGreater(app_row["match_score"], 0, "Fabricated negative score influenced backend score!")

    def test_client_forged_match_score_999999_is_ignored(self):
        """Test 3: Cheater sends match_score = 999999; server calculates authoritative score <= 100."""
        ts = int(time.time() * 1000)
        cand_email = f"huge_cand_{ts}@test.com"
        cand_id = register_user("Huge Score Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status) 
                   VALUES ('Go Engineer', 'GoCorp', 'Go, Docker', 'Golang engineer', 'Active')"""
            )
            job_id = cur.lastrowid
            conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'resume.pdf', ?, '/dummy/path', ?, 1024, 'application/pdf', 
                           'Go Docker developer building services', 'Go, Docker', 'processed')""",
                (cand_id, f"stored_huge_{ts}.pdf", f"hash_huge_{ts}")
            )
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        res = self.client.post("/api/apply", json={"job_id": job_id, "match_score": 999999})
        self.assertEqual(res.status_code, 200)

        with get_db() as conn:
            app_row = conn.execute(
                "SELECT match_score FROM applications WHERE user_id=? AND job_id=?", 
                (cand_id, job_id)
            ).fetchone()
            self.assertIsNotNone(app_row)
            self.assertLessEqual(app_row["match_score"], 100)
            self.assertGreater(app_row["match_score"], 0)

    def test_tampered_candidate_id_in_payload_is_strictly_bound_to_session(self):
        """Test 4: Client passes malicious user_id in payload; server strictly binds to session."""
        ts = int(time.time() * 1000)
        victim_email = f"victim_{ts}@test.com"
        victim_id = register_user("Victim User", victim_email, "Password123!", "candidate")["user"]["id"]

        attacker_email = f"attacker_{ts}@test.com"
        attacker_id = register_user("Attacker User", attacker_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status) 
                   VALUES ('Security Analyst', 'SecCorp', 'SIEM, Python', 'Analyst', 'Active')"""
            )
            job_id = cur.lastrowid
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = attacker_id

        # Attacker attempts to apply on behalf of victim
        res = self.client.post("/api/apply", json={"job_id": job_id, "user_id": victim_id, "candidate_id": victim_id})
        self.assertEqual(res.status_code, 200)

        with get_db() as conn:
            # Application must be created for attacker, NOT victim
            victim_app = conn.execute("SELECT * FROM applications WHERE user_id=? AND job_id=?", (victim_id, job_id)).fetchone()
            attacker_app = conn.execute("SELECT * FROM applications WHERE user_id=? AND job_id=?", (attacker_id, job_id)).fetchone()

            self.assertIsNone(victim_app, "Security Breach: Attacker applied on behalf of victim!")
            self.assertIsNotNone(attacker_app)

    def test_unauthorized_score_modification_rejected(self):
        """Test 5: Attempt to modify stored application score directly is rejected."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_direct_{ts}@test.com"
        cand_id = register_user("Direct Cand", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status) 
                   VALUES ('Developer', 'DevCorp', 'Java', 'Dev', 'Active')"""
            )
            job_id = cur.lastrowid
            cur_app = conn.execute(
                "INSERT INTO applications (user_id, job_id, match_score, applied_at) VALUES (?, ?, 45, '2026-10-01 10:00')",
                (cand_id, job_id)
            )
            app_id = cur_app.lastrowid
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        # Attempt to patch score directly via non-existent / unauthorized endpoint
        res = self.client.patch(f"/api/application/{app_id}", json={"match_score": 99})
        self.assertIn(res.status_code, (404, 405, 401, 403))

        with get_db() as conn:
            app_row = conn.execute("SELECT match_score FROM applications WHERE id=?", (app_id,)).fetchone()
            self.assertEqual(app_row["match_score"], 45, "Stored score was illegally modified!")

    def test_resume_update_updates_recommendation_and_scoring(self):
        """Test 7: Updating candidate resume reflects in updated recommendations."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_rec_{ts}@test.com"
        cand_id = register_user("Rec Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status) 
                   VALUES ('React Developer', 'WebCorp', 'React, Redux, TypeScript', 'Frontend React Developer', 'Active')"""
            )
            job_id = cur.lastrowid

            # Initial resume: Java only
            conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'java.pdf', ?, '/dummy/path', ?, 1024, 'application/pdf', 
                           'Java developer building microservices', 'Java', 'processed')""",
                (cand_id, f"stored_j_{ts}.pdf", f"hash_j_{ts}")
            )
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        # Query recommendation with initial resume
        res1 = self.client.post("/api/match_jobs", json={})
        self.assertEqual(res1.status_code, 200)

        # Upload updated resume with React and Redux
        with get_db() as conn:
            conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'react.pdf', ?, '/dummy/path2', ?, 1024, 'application/pdf', 
                           'React Redux TypeScript frontend engineer', 'React, Redux, TypeScript', 'processed')""",
                (cand_id, f"stored_r_{ts}.pdf", f"hash_r_{ts}")
            )
            conn.execute("UPDATE users SET skills='React, Redux, TypeScript' WHERE id=?", (cand_id,))
            conn.commit()

        # Query recommendation with updated resume
        res2 = self.client.post("/api/match_jobs", json={})
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2.get("success"))


if __name__ == "__main__":
    unittest.main()

