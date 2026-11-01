import unittest
import time
import json
from datetime import datetime, timedelta
from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user


class TestStep3SnapshotLock(unittest.TestCase):
    """
    Test Step 3: Snapshot Lock & 30-Day Cooldown.
    Verifies that:
    1. When an application is submitted, it permanently captures and locks the
       active resume_id at the moment of submission.
    2. Subsequent resume uploads do NOT mutate the resume linked to past applications.
    3. The HR candidates view displays the submitted resume snapshot, not newer profile uploads.
    4. Re-applying to the same job within 30 days is blocked by cooldown.
    5. Re-applying after 30 days has elapsed is permitted and updates the application snapshot.
    6. Applying without a resume safely records resume_id as NULL and match_score as 0.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_application_stores_active_resume_id_snapshot(self):
        """Application permanently locks the active resume_id at application time."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_snap_{ts}@test.com"
        cand_id = register_user("Snapshot Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            # Create a job
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status)
                   VALUES ('Backend Developer', 'Acme Corp', 'Python, Flask, SQL', 'Backend engineering', 'Active')"""
            )
            job_id = cur.lastrowid

            # Insert initial resume (Resume 1)
            cur_r1 = conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'resume_python_v1.pdf', ?, '/dummy/r1.pdf', ?, 1024, 'application/pdf',
                           'Python developer with experience in Flask and SQLite databases', 'Python, Flask', 'processed')""",
                (cand_id, f"stored_r1_{ts}.pdf", f"hash_r1_{ts}")
            )
            resume1_id = cur_r1.lastrowid
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        # Submit application
        res = self.client.post("/api/apply", json={"job_id": job_id})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

        # Verify application row has resume_id pointing to resume1_id
        with get_db() as conn:
            app_row = conn.execute(
                "SELECT id, resume_id, match_score, status FROM applications WHERE user_id=? AND job_id=?",
                (cand_id, job_id)
            ).fetchone()
            self.assertIsNotNone(app_row)
            self.assertEqual(app_row["resume_id"], resume1_id)
            self.assertGreater(app_row["match_score"], 0)

    def test_subsequent_resume_upload_does_not_mutate_application_snapshot(self):
        """When candidate uploads a 2nd resume, past application retains Resume 1 snapshot."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_multi_{ts}@test.com"
        cand_id = register_user("Multi Resume Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status)
                   VALUES ('Python Engineer', 'Acme Corp', 'Python, Django', 'Python role', 'Active')"""
            )
            job_id = cur.lastrowid

            # Resume 1: Python dev
            cur_r1 = conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'resume_python_v1.pdf', ?, '/dummy/r1.pdf', ?, 1024, 'application/pdf',
                           'Python and Django engineer', 'Python, Django', 'processed')""",
                (cand_id, f"stored_r1_{ts}.pdf", f"hash_r1_{ts}")
            )
            resume1_id = cur_r1.lastrowid
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        # Apply to job with Resume 1
        res = self.client.post("/api/apply", json={"job_id": job_id})
        self.assertTrue(res.get_json().get("success"))

        # Candidate now uploads Resume 2 (e.g. completely different skills: Java, Spring)
        with get_db() as conn:
            cur_r2 = conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'resume_java_v2.pdf', ?, '/dummy/r2.pdf', ?, 1024, 'application/pdf',
                           'Java and Spring Boot developer', 'Java, Spring', 'processed')""",
                (cand_id, f"stored_r2_{ts}.pdf", f"hash_r2_{ts}")
            )
            resume2_id = cur_r2.lastrowid
            conn.commit()

        self.assertNotEqual(resume1_id, resume2_id)

        # Verify application row STILL has resume1_id
        with get_db() as conn:
            app_row = conn.execute(
                "SELECT resume_id FROM applications WHERE user_id=? AND job_id=?",
                (cand_id, job_id)
            ).fetchone()
            self.assertEqual(app_row["resume_id"], resume1_id, "Application snapshot was mutated by new resume upload!")

    def test_hr_view_shows_frozen_resume_snapshot_not_new_upload(self):
        """HR /api/admin/candidates view returns the submitted resume snapshot."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_hr_{ts}@test.com"
        cand_id = register_user("HR Snapshot Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        hr_email = f"hr_auditor_{ts}@test.com"
        hr_id = register_user("HR Auditor", hr_email, "Password123!", "hr", allow_privileged=True, is_verified=1)["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status)
                   VALUES ('Data Scientist', 'AI Corp', 'Python, ML', 'Data role', 'Active')"""
            )
            job_id = cur.lastrowid

            # Resume 1
            cur_r1 = conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, structured_json, status)
                   VALUES (?, 'applied_data_resume.pdf', ?, '/dummy/r1.pdf', ?, 1024, 'application/pdf',
                           'Data Scientist specializing in ML', 'Python, ML', ?, 'processed')""",
                (cand_id, f"stored_hr_r1_{ts}.pdf", f"hash_hr_r1_{ts}", json.dumps({"total_experience_years": 3.0}))
            )
            resume1_id = cur_r1.lastrowid
            conn.commit()

        # Candidate applies
        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"
        self.client.post("/api/apply", json={"job_id": job_id})

        # Candidate later uploads Resume 2
        with get_db() as conn:
            conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, structured_json, status)
                   VALUES (?, 'later_devops_resume.pdf', ?, '/dummy/r2.pdf', ?, 1024, 'application/pdf',
                           'DevOps engineer specializing in Docker', 'Docker', ?, 'processed')""",
                (cand_id, f"stored_hr_r2_{ts}.pdf", f"hash_hr_r2_{ts}", json.dumps({"total_experience_years": 1.0}))
            )
            conn.commit()

        # Log in as HR and fetch candidates
        with self.client.session_transaction() as sess:
            sess["user_id"] = hr_id
            sess["role"] = "hr"

        res = self.client.get("/api/admin/candidates")
        self.assertEqual(res.status_code, 200)
        candidates = res.get_json()

        cand_entry = next((c for c in candidates if c.get("user_id") == cand_id), None)
        self.assertIsNotNone(cand_entry, "Applicant not found in HR candidates list.")
        self.assertEqual(cand_entry.get("resume_id"), resume1_id, "HR view did not return the frozen snapshot resume_id!")
        self.assertEqual(cand_entry.get("resume_name"), "applied_data_resume.pdf", "HR view showed updated resume filename instead of snapshot!")

    def test_reapply_within_30_days_blocked_by_cooldown(self):
        """Re-applying to the same job within 30 days is blocked by cooldown."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_cd_{ts}@test.com"
        cand_id = register_user("Cooldown Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status)
                   VALUES ('Security Analyst', 'SecureNet', 'Linux, SIEM', 'Security role', 'Active')"""
            )
            job_id = cur.lastrowid

            conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'sec_resume.pdf', ?, '/dummy/sec.pdf', ?, 1024, 'application/pdf',
                           'Security analyst', 'Linux, SIEM', 'processed')""",
                (cand_id, f"stored_sec_{ts}.pdf", f"hash_sec_{ts}")
            )
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        # First apply: succeeds
        res1 = self.client.post("/api/apply", json={"job_id": job_id})
        self.assertTrue(res1.get_json().get("success"))

        # Immediate re-apply: blocked
        res2 = self.client.post("/api/apply", json={"job_id": job_id})
        data2 = res2.get_json()
        self.assertFalse(data2.get("success"))
        self.assertTrue(data2.get("cooldown_active"))
        self.assertIn("Already applied", data2.get("message"))
        self.assertIn("30 days", data2.get("message"))
        self.assertEqual(data2.get("days_remaining"), 30)

    def test_reapply_after_30_days_allowed_and_updates_snapshot(self):
        """Re-applying after 30-day cooldown has passed succeeds and updates the snapshot."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_after30_{ts}@test.com"
        cand_id = register_user("Experienced Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status)
                   VALUES ('Senior Architect', 'ScaleCorp', 'Go, Microservices', 'Architecture role', 'Active')"""
            )
            job_id = cur.lastrowid

            # Resume 1
            cur_r1 = conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'old_resume.pdf', ?, '/dummy/old.pdf', ?, 1024, 'application/pdf',
                           'Software dev with basic Go', 'Go', 'processed')""",
                (cand_id, f"stored_old_{ts}.pdf", f"hash_old_{ts}")
            )
            resume1_id = cur_r1.lastrowid
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        # Apply initially
        self.client.post("/api/apply", json={"job_id": job_id})

        # Fast forward time: simulate that the application occurred 35 days ago
        past_time = (datetime.now() - timedelta(days=35)).strftime('%Y-%m-%d %H:%M')
        with get_db() as conn:
            conn.execute(
                "UPDATE applications SET applied_at=?, status='Rejected' WHERE user_id=? AND job_id=?",
                (past_time, cand_id, job_id)
            )

            # Candidate uploads upgraded Resume 2
            cur_r2 = conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'upgraded_architect.pdf', ?, '/dummy/upgraded.pdf', ?, 1024, 'application/pdf',
                           'Senior Architect with Go and Microservices expertise', 'Go, Microservices', 'processed')""",
                (cand_id, f"stored_upgraded_{ts}.pdf", f"hash_upgraded_{ts}")
            )
            resume2_id = cur_r2.lastrowid
            conn.commit()

        # Re-apply now that > 30 days have passed
        res_reapply = self.client.post("/api/apply", json={"job_id": job_id})
        self.assertEqual(res_reapply.status_code, 200)
        data_reapply = res_reapply.get_json()
        self.assertTrue(data_reapply.get("success"))
        self.assertTrue(data_reapply.get("reapplied"))

        # Verify application row is refreshed with new snapshot and Reviewing status
        with get_db() as conn:
            refreshed_app = conn.execute(
                "SELECT resume_id, status, match_score FROM applications WHERE user_id=? AND job_id=?",
                (cand_id, job_id)
            ).fetchone()
            self.assertEqual(refreshed_app["resume_id"], resume2_id, "Re-application did not update to new resume snapshot!")
            self.assertEqual(refreshed_app["status"], "Reviewing", "Re-application did not reset status to Reviewing!")
            self.assertGreater(refreshed_app["match_score"], 0)

    def test_candidate_with_no_resume_applies_with_null_resume_id(self):
        """Candidate applying without an uploaded resume safely records resume_id as NULL."""
        ts = int(time.time() * 1000)
        cand_email = f"cand_no_resume_{ts}@test.com"
        cand_id = register_user("No Resume Candidate", cand_email, "Password123!", "candidate")["user"]["id"]

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status)
                   VALUES ('General Assistant', 'Office Inc', 'Communication', 'Admin role', 'Active')"""
            )
            job_id = cur.lastrowid
            conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id

        res = self.client.post("/api/apply", json={"job_id": job_id})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

        with get_db() as conn:
            app_row = conn.execute(
                "SELECT resume_id, match_score FROM applications WHERE user_id=? AND job_id=?",
                (cand_id, job_id)
            ).fetchone()
            self.assertIsNone(app_row["resume_id"])
            self.assertEqual(app_row["match_score"], 0)

    def test_resume_deletion_preserves_historical_application_snapshot(self):
        """Active resume deletion by candidate preserves historical application snapshot and physical file for HR."""
        import os
        from app.controllers.resume_controller import delete_resume_by_id, get_upload_folder
        ts = int(time.time() * 1000)
        cand_email = f"cand_del_snap_{ts}@test.com"
        cand_id = register_user("Del Snapshot Cand", cand_email, "Password123!", "candidate", is_verified=1)["user"]["id"]
        hr_id = register_user("HR Reviewer", f"hr_del_{ts}@test.com", "Password123!", "hr", allow_privileged=True, is_verified=1)["user"]["id"]

        # Create physical dummy file in upload folder
        up_folder = get_upload_folder()
        os.makedirs(up_folder, exist_ok=True)
        fname = f"snap_test_{ts}.pdf"
        fpath = os.path.join(up_folder, fname)
        with open(fpath, "wb") as f:
            f.write(b"%PDF-1.4 dummy snapshot content")

        with get_db() as conn:
            cur_job = conn.execute(
                """INSERT INTO jobs (title, company, skills, description, status)
                   VALUES ('DevOps Lead', 'Cloud Inc', 'AWS, Terraform', 'DevOps role', 'Active')"""
            )
            job_id = cur_job.lastrowid

            cur_res = conn.execute(
                """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, extracted_skills, status)
                   VALUES (?, 'snapshot_resume.pdf', ?, ?, ?, 1024, 'application/pdf',
                           'AWS and Terraform lead architect', 'AWS, Terraform', 'processed')""",
                (cand_id, fname, fpath, f"hash_del_{ts}")
            )
            resume_id = cur_res.lastrowid
            conn.commit()

        # Apply for job using resume_id
        with self.client.session_transaction() as sess:
            sess["user_id"] = cand_id
            sess["role"] = "candidate"

        res_apply = self.client.post("/api/apply", json={"job_id": job_id})
        self.assertEqual(res_apply.status_code, 200)

        # Candidate now deletes their resume from their profile dashboard
        res_del = delete_resume_by_id(resume_id, current_user_id=cand_id, current_user_role="candidate")
        self.assertTrue(res_del["success"])
        self.assertTrue(res_del.get("archived", False))

        # 1. Candidate's active resume list does NOT return the deleted resume
        res_list = self.client.get("/api/resume/my_resumes")
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.get_json()["resumes"]), 0)

        # 2. Database row still exists with status='archived'
        with get_db() as conn:
            r_row = conn.execute("SELECT id, status FROM resumes WHERE id=?", (resume_id,)).fetchone()
            self.assertIsNotNone(r_row)
            self.assertEqual(r_row["status"], "archived")

        # 3. Physical file on disk is preserved
        self.assertTrue(os.path.exists(fpath), "Physical resume file was prematurely removed!")

        # 4. HR reviewer can view and download the exact submitted application snapshot
        with self.client.session_transaction() as sess:
            sess["user_id"] = hr_id
            sess["role"] = "hr"

        res_cands = self.client.get("/api/admin/candidates")
        self.assertEqual(res_cands.status_code, 200)
        cands_list = res_cands.get_json() if isinstance(res_cands.get_json(), list) else res_cands.get_json().get("candidates", [])
        cand_entry = next((c for c in cands_list if c["user_id"] == cand_id), None)
        self.assertIsNotNone(cand_entry)
        self.assertEqual(cand_entry["resume_id"], resume_id)
        self.assertEqual(cand_entry["resume_name"], "snapshot_resume.pdf")

        # 5. HR can download the resume snapshot
        res_dl = self.client.get(f"/api/resume/download/{resume_id}")
        self.assertEqual(res_dl.status_code, 200)
        self.assertEqual(res_dl.data, b"%PDF-1.4 dummy snapshot content")

        # Clean up test file
        try:
            if os.path.exists(fpath):
                os.remove(fpath)
        except Exception:
            pass


if __name__ == '__main__':
    unittest.main()
