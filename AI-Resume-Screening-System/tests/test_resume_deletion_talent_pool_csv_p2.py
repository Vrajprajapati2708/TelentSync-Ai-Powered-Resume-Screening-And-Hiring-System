# ============================================================
#  HireAI / TalentSync — Phase 2 Resume Lifecycle & HR Talent Pool CSV Export Tests
#  Strict Isolation: Uses TestingConfig and isolated temporary test database
# ============================================================

import os
import io
import sys
import time
import csv
import json
import unittest
from unittest.mock import patch

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

import docx as python_docx
from reportlab.pdfgen import canvas  # type: ignore[import-untyped]
from werkzeug.datastructures import FileStorage

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.controllers.resume_controller import process_resume_upload, delete_resume_by_id
from app.routes.admin_routes import sanitize_csv_cell


def _ts() -> str:
    """Nanosecond-precision unique tag to avoid email collisions."""
    return str(int(time.time() * 1_000_000))


def _make_docx_stream(text: str = "Senior Software Engineer with Python Flask Docker and SQL experience") -> io.BytesIO:
    doc = python_docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def _make_pdf_stream(text: str = "Candidate PDF Resume with Python and Machine Learning.") -> io.BytesIO:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, text)
    c.save()
    buf.seek(0)
    return buf


class TestResumeDeletionLifecycle(unittest.TestCase):
    """
    Comprehensive tests for Part A: Secure Resume Lifecycle & Deletion.
    Covers RBAC, ownership, IDOR defense, path traversal, referential integrity,
    profile sync, and audit logging.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        ts = _ts()
        self.email_a = f"cand_a_{ts}@test.com"
        self.email_b = f"cand_b_{ts}@test.com"
        self.email_hr = f"hr_{ts}@test.com"
        self.email_admin = f"admin_{ts}@test.com"

        reg_a = register_user("Candidate A", self.email_a, "Password10!", "candidate", is_verified=1)
        reg_b = register_user("Candidate B", self.email_b, "Password10!", "candidate", is_verified=1)
        reg_hr = register_user("HR Recruiter", self.email_hr, "Password10!", "hr", allow_privileged=True, is_verified=1)
        reg_admin = register_user("Platform Admin", self.email_admin, "Password10!", "admin", allow_privileged=True, is_verified=1)

        self.user_a_id = reg_a["user"]["id"]
        self.user_b_id = reg_b["user"]["id"]
        self.user_hr_id = reg_hr["user"]["id"]
        self.user_admin_id = reg_admin["user"]["id"]

    def tearDown(self):
        self.app_context.pop()

    def _login(self, email: str):
        return self.client.post("/api/auth/login", json={"email": email, "password": "Password10!"})

    def _upload_resume_as(self, email: str, text: str = "Python Developer") -> int:
        self._login(email)
        buf = _make_docx_stream(text)
        resp = self.client.post(
            "/api/upload_resume",
            data={"resume": (buf, "Resume.docx")},
            content_type="multipart/form-data"
        )
        data = resp.get_json() or {}
        self.assertTrue(data.get("success"), f"Upload failed: {data}")
        return data["resume_id"]

    def test_unauthenticated_deletion_returns_401(self):
        """Unauthenticated resume deletion attempt must return 401."""
        resume_id = self._upload_resume_as(self.email_a)
        # Logout
        self.client.post("/api/auth/logout")

        resp = self.client.delete(f"/api/resume/{resume_id}")
        self.assertEqual(resp.status_code, 401)

    def test_candidate_owns_resume_deletion_succeeds(self):
        """Candidate can delete their own resume; DB and physical file are removed."""
        resume_id = self._upload_resume_as(self.email_a)

        # Verify DB and file exist
        with get_db() as conn:
            r = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
            self.assertIsNotNone(r)
            file_path = r["file_path"]
            self.assertTrue(os.path.exists(file_path))

        # Delete as owner
        self._login(self.email_a)
        resp = self.client.delete(f"/api/resume/{resume_id}")
        data = resp.get_json() or {}
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data.get("success"))

        # Verify DB record is removed
        with get_db() as conn:
            r_post = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
            self.assertIsNone(r_post)

        # Verify physical file is removed
        self.assertFalse(os.path.exists(file_path))

    def test_candidate_idor_cannot_delete_other_candidate_resume(self):
        """Candidate B cannot delete Candidate A's resume (IDOR defense returns 403)."""
        resume_id = self._upload_resume_as(self.email_a)

        # Log in as Candidate B and try to delete Candidate A's resume
        self._login(self.email_b)
        resp = self.client.delete(f"/api/resume/{resume_id}")
        self.assertEqual(resp.status_code, 403)

        # Verify resume still exists in DB and filesystem
        with get_db() as conn:
            r = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
            self.assertIsNotNone(r)
            self.assertTrue(os.path.exists(r["file_path"]))

    def test_hr_cannot_delete_candidate_resume(self):
        """HR recruiters cannot delete candidate resumes (returns 403)."""
        resume_id = self._upload_resume_as(self.email_a)

        self._login(self.email_hr)
        resp = self.client.delete(f"/api/resume/{resume_id}")
        self.assertEqual(resp.status_code, 403)

        with get_db() as conn:
            r = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
            self.assertIsNotNone(r)

    def test_admin_can_delete_candidate_resume(self):
        """Platform Admin has moderation authority to delete any resume."""
        resume_id = self._upload_resume_as(self.email_a)

        self._login(self.email_admin)
        resp = self.client.delete(f"/api/resume/{resume_id}")
        self.assertEqual(resp.status_code, 200)

        with get_db() as conn:
            r = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
            self.assertIsNone(r)

    def test_nonexistent_resume_returns_404(self):
        """Deleting a non-existent resume returns 404."""
        self._login(self.email_a)
        resp = self.client.delete("/api/resume/99999999")
        self.assertEqual(resp.status_code, 404)

    def test_already_deleted_resume_returns_404(self):
        """Deleting an already deleted resume returns 404 consistently without exceptions."""
        resume_id = self._upload_resume_as(self.email_a)

        self._login(self.email_a)
        resp1 = self.client.delete(f"/api/resume/{resume_id}")
        self.assertEqual(resp1.status_code, 200)

        # Second deletion attempt
        resp2 = self.client.delete(f"/api/resume/{resume_id}")
        self.assertEqual(resp2.status_code, 404)

    def test_missing_physical_file_handled_gracefully(self):
        """If physical file was manually deleted from disk, DB deletion still succeeds safely."""
        resume_id = self._upload_resume_as(self.email_a)

        with get_db() as conn:
            r = conn.execute("SELECT file_path FROM resumes WHERE id=?", (resume_id,)).fetchone()
            file_path = r["file_path"]

        # Prematurely remove file from disk
        if os.path.exists(file_path):
            os.remove(file_path)

        self._login(self.email_a)
        resp = self.client.delete(f"/api/resume/{resume_id}")
        self.assertEqual(resp.status_code, 200)

        with get_db() as conn:
            r_post = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
            self.assertIsNone(r_post)

    def test_path_traversal_stored_filename_rejected(self):
        """Path traversal patterns in stored_filename trigger a security error and are rejected."""
        resume_id = self._upload_resume_as(self.email_a)

        # Artificially inject path traversal into stored_filename in DB
        with get_db() as conn:
            conn.execute(
                f"UPDATE resumes SET stored_filename='../../etc/passwd_{_ts()}' WHERE id=?",
                (resume_id,)
            )
            conn.commit()

        # Direct controller call
        res = delete_resume_by_id(resume_id, self.user_a_id, "candidate")
        self.assertFalse(res["success"])
        self.assertEqual(res["status_code"], 400)
        self.assertIn("Security error", res["message"])

    def test_arbitrary_path_escape_rejected(self):
        """Absolute or escaped target paths are rejected by the jail check."""
        resume_id = self._upload_resume_as(self.email_a)

        # Artificially inject absolute path in stored_filename
        with get_db() as conn:
            conn.execute(
                f"UPDATE resumes SET stored_filename='C:\\\\Windows\\\\system32\\\\cmd_{_ts()}.exe' WHERE id=?",
                (resume_id,)
            )
            conn.commit()

        res = delete_resume_by_id(resume_id, self.user_a_id, "candidate")
        self.assertFalse(res["success"])
        self.assertEqual(res["status_code"], 400)

    def test_sql_injection_attempt_in_url_path(self):
        """SQL injection strings in resume endpoint are rejected safely by Flask URL routing."""
        self._login(self.email_a)
        resp = self.client.delete("/api/resume/1%20OR%201=1")
        self.assertEqual(resp.status_code, 404)

    def test_transaction_failure_handled_safely(self):
        """Database exception during deletion returns clean 500 without crashing."""
        resume_id = self._upload_resume_as(self.email_a)

        with patch("app.controllers.resume_controller.get_db", side_effect=Exception("Simulated DB lock error")):
            res = delete_resume_by_id(resume_id, self.user_a_id, "candidate")
            self.assertFalse(res["success"])
            self.assertEqual(res["status_code"], 500)

    def test_application_reference_integrity_preserved(self):
        """
        Deleting a resume must NEVER cascade delete or alter existing job application records.
        """
        resume_id = self._upload_resume_as(self.email_a, "Python Developer with SQL")

        # Create a job and an application for Candidate A
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO jobs (title, company, description, location) VALUES ('Backend Dev', 'TechCorp', 'Python role', 'Remote')"
            )
            job_id = cur.lastrowid
            conn.execute(
                "INSERT INTO applications (user_id, job_id, match_score, status, applied_at) VALUES (?, ?, 85, 'Pending', '2026-09-30 10:00')",
                (self.user_a_id, job_id)
            )
            conn.commit()

        # Delete resume
        self._login(self.email_a)
        resp = self.client.delete(f"/api/resume/{resume_id}")
        self.assertEqual(resp.status_code, 200)

        # Verify application record is preserved
        with get_db() as conn:
            app_rec = conn.execute(
                "SELECT * FROM applications WHERE user_id=? AND job_id=?",
                (self.user_a_id, job_id)
            ).fetchone()
            self.assertIsNotNone(app_rec)
            self.assertEqual(app_rec["status"], "Pending")
            self.assertEqual(app_rec["match_score"], 85)

    def test_candidate_profile_ats_synced_to_remaining_resume(self):
        """
        When candidate has multiple resumes and deletes one, user profile ats_score/skills
        syncs to the latest remaining resume. When all are deleted, resets to 0 / ''.
        """
        # Upload resume 1
        r1_id = self._upload_resume_as(self.email_a, "Junior Developer with HTML CSS")
        # Upload resume 2
        r2_id = self._upload_resume_as(self.email_a, "Senior Python Django Flask Engineer with AWS Docker Kubernetes")

        with get_db() as conn:
            u1 = conn.execute("SELECT ats_score, skills FROM users WHERE id=?", (self.user_a_id,)).fetchone()
            self.assertGreater(u1["ats_score"], 0)
            score_with_r2 = u1["ats_score"]

            r1_meta = conn.execute("SELECT ats_score, extracted_skills FROM resumes WHERE id=?", (r1_id,)).fetchone()
            r1_score = r1_meta["ats_score"]
            r1_skills = r1_meta["extracted_skills"]

        # Delete resume 2
        self._login(self.email_a)
        resp = self.client.delete(f"/api/resume/{r2_id}")
        self.assertEqual(resp.status_code, 200)

        # Profile should now reflect resume 1
        with get_db() as conn:
            u2 = conn.execute("SELECT ats_score, skills FROM users WHERE id=?", (self.user_a_id,)).fetchone()
            self.assertEqual(u2["ats_score"], r1_score)
            self.assertEqual(u2["skills"], r1_skills)

        # Delete resume 1
        resp2 = self.client.delete(f"/api/resume/{r1_id}")
        self.assertEqual(resp2.status_code, 200)

        # Profile should now reset to 0 / ''
        with get_db() as conn:
            u3 = conn.execute("SELECT ats_score, skills FROM users WHERE id=?", (self.user_a_id,)).fetchone()
            self.assertEqual(u3["ats_score"], 0)
            self.assertEqual(u3["skills"], "")

    def test_audit_notification_logged(self):
        """Deleting a resume logs an informational notification in notifications table."""
        resume_id = self._upload_resume_as(self.email_a)

        self._login(self.email_a)
        self.client.delete(f"/api/resume/{resume_id}")

        with get_db() as conn:
            notif = conn.execute(
                "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (self.user_a_id,)
            ).fetchone()
            self.assertIsNotNone(notif)
            self.assertIn("Resume Deleted", notif["title"])


class TestTalentPoolCSVExport(unittest.TestCase):
    """
    Comprehensive tests for Part B: HR Talent Pool CSV Export.
    Covers RBAC, CSV structure, formula injection protection, sensitive data exclusion,
    deterministic filter parity, and empty result handling.
    """

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        ts = _ts()
        self.email_hr = f"hr_pool_{ts}@test.com"
        self.email_cand = f"cand_pool_{ts}@test.com"
        self.email_admin = f"admin_pool_{ts}@test.com"

        reg_hr = register_user("HR Manager", self.email_hr, "Password10!", "hr", allow_privileged=True, is_verified=1)
        reg_cand = register_user("Alice Candidate", self.email_cand, "Password10!", "candidate", is_verified=1)
        reg_admin = register_user("Platform Admin", self.email_admin, "Password10!", "admin", allow_privileged=True, is_verified=1)

        self.user_hr_id = reg_hr["user"]["id"]
        self.user_cand_id = reg_cand["user"]["id"]
        self.user_admin_id = reg_admin["user"]["id"]

        # Create candidate 2 first
        ts2 = _ts()
        reg_cand2 = register_user("Bob Engineer", f"bob_{ts2}@test.com", "Password10!", "candidate", is_verified=1)
        self.user_cand2_id = reg_cand2["user"]["id"]

        # Populate candidate profiles with specific attributes for testing
        with get_db() as conn:
            conn.execute(
                """UPDATE users SET 
                   location='Ahmedabad',
                   education='B.Tech Computer Engineering',
                   skills='Python, Django, PostgreSQL, Docker',
                   ats_score=85,
                   phone='+91-9876543210'
                   WHERE id=?""",
                (self.user_cand_id,)
            )
            conn.execute(
                """UPDATE users SET 
                   location='Pune',
                   education='M.S. Data Science',
                   skills='Java, Spring Boot, AWS',
                   ats_score=65,
                   phone='+91-9876543211'
                   WHERE id=?""",
                (self.user_cand2_id,)
            )
            conn.commit()

    def tearDown(self):
        self.app_context.pop()

    def _login(self, email: str):
        return self.client.post("/api/auth/login", json={"email": email, "password": "Password10!"})

    def test_unauthenticated_export_returns_401(self):
        """Unauthenticated call to CSV export endpoint returns 401."""
        resp = self.client.get("/api/admin/talent_pool/export")
        self.assertEqual(resp.status_code, 401)

    def test_candidate_export_returns_403(self):
        """Candidate role attempting to export talent pool CSV returns 403."""
        self._login(self.email_cand)
        resp = self.client.get("/api/admin/talent_pool/export")
        self.assertEqual(resp.status_code, 403)

    def test_hr_export_returns_200_with_valid_csv(self):
        """HR role successfully downloads CSV with proper headers and MIME type."""
        self._login(self.email_hr)
        resp = self.client.get("/api/admin/talent_pool/export")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("Content-Type", ""))
        self.assertIn("attachment; filename=", resp.headers.get("Content-Disposition", ""))

    def test_admin_export_returns_200(self):
        """Admin role can export Talent Pool CSV."""
        self._login(self.email_admin)
        resp = self.client.get("/api/admin/talent_pool/export")
        self.assertEqual(resp.status_code, 200)

    def test_csv_headers_present_and_correct(self):
        """CSV output contains the standard required column headers."""
        self._login(self.email_hr)
        resp = self.client.get("/api/admin/talent_pool/export")
        decoded = resp.data.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(decoded)))
        self.assertGreater(len(reader), 0)
        headers = reader[0]

        expected_headers = [
            'Candidate ID', 'Name', 'Email', 'Phone', 'Location',
            'Degree / Education', 'Experience', 'ATS Score', 'Applications Count',
            'Skills', 'Registered Date'
        ]
        self.assertEqual(headers, expected_headers)

    def test_csv_row_correctness(self):
        """Exported CSV contains correct candidate details matching DB."""
        self._login(self.email_hr)
        resp = self.client.get("/api/admin/talent_pool/export")
        decoded = resp.data.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(decoded)))
        rows = reader[1:]  # Exclude header

        alice_row = None
        for r in rows:
            if r[2] == self.email_cand:
                alice_row = r
                break

        self.assertIsNotNone(alice_row, "Alice candidate row not found in CSV")
        self.assertEqual(alice_row[1], "Alice Candidate")
        self.assertEqual(alice_row[4], "Ahmedabad")
        self.assertEqual(alice_row[7], "85")  # ATS score
        self.assertIn("Python", alice_row[9])

    def test_sensitive_fields_strictly_excluded(self):
        """Passwords, password hashes, tokens, and session secrets are never in the CSV."""
        self._login(self.email_hr)
        resp = self.client.get("/api/admin/talent_pool/export")
        decoded = resp.data.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(decoded)))
        headers = [h.lower() for h in reader[0]]

        forbidden_headers = [
            "password", "password_hash", "hash", "secret_key",
            "token", "verification_token", "reset_token", "session_id"
        ]
        for fh in forbidden_headers:
            self.assertNotIn(fh, headers)

        # Ensure no cell exposes raw password hashes or authentication secret signatures
        for row in reader[1:]:
            for cell in row:
                cell_lower = cell.lower()
                self.assertNotIn("pbkdf2:sha256:", cell_lower)
                self.assertNotIn("scrypt:", cell_lower)
                self.assertFalse(cell.startswith("$2b$"))
                self.assertFalse(cell.startswith("$2a$"))


    def test_formula_injection_defense(self):
        """
        Fields starting with formula triggers (=, +, -, @, \\t, \\r) are sanitized with prefix '.
        OWASP CWE-1236 defense.
        """
        # Create a candidate whose name starts with '=' (formula injection attempt)
        ts_mal = _ts()
        email_mal = f"mal_{ts_mal}@test.com"
        reg_mal = register_user("=cmd|' /C calc'!A0", email_mal, "Password10!", "candidate", is_verified=1)
        mal_id = reg_mal["user"]["id"]

        with get_db() as conn:
            conn.execute(
                "UPDATE users SET location='+MaliciousLoc', skills='@DangerousSkill' WHERE id=?",
                (mal_id,)
            )
            conn.commit()

        self._login(self.email_hr)
        resp = self.client.get("/api/admin/talent_pool/export")
        decoded = resp.data.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(decoded)))

        mal_row = None
        for r in reader[1:]:
            if r[2] == email_mal:
                mal_row = r
                break

        self.assertIsNotNone(mal_row)
        # Verify sanitized with leading single quote
        self.assertTrue(mal_row[1].startswith("'="), f"Name was not sanitized: {mal_row[1]}")
        self.assertTrue(mal_row[4].startswith("'+"), f"Location was not sanitized: {mal_row[4]}")
        self.assertTrue(mal_row[9].startswith("'@"), f"Skills were not sanitized: {mal_row[9]}")

    def test_search_filter_parity(self):
        """Search filter ?q= matches the exact same candidates in both JSON API and CSV export."""
        self._login(self.email_hr)

        # JSON response (query unique email for test isolation)
        json_resp = self.client.get(f"/api/admin/talent_pool?q={self.email_cand}")
        self.assertEqual(json_resp.status_code, 200)
        json_data = json_resp.get_json()
        json_candidates = json_data["candidates"]
        json_ids = sorted([c["candidate_id"] for c in json_candidates])

        # CSV response
        csv_resp = self.client.get(f"/api/admin/talent_pool/export?q={self.email_cand}")
        self.assertEqual(csv_resp.status_code, 200)
        decoded = csv_resp.data.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(decoded)))
        csv_ids = sorted([int(r[0]) for r in reader[1:] if r[0].isdigit()])

        self.assertEqual(json_ids, csv_ids)
        self.assertIn(self.user_cand_id, csv_ids)
        self.assertNotIn(self.user_cand2_id, csv_ids)

    def test_location_filter_parity(self):
        """Location filter ?location=Ahmedabad filters accurately in CSV export."""
        self._login(self.email_hr)
        resp = self.client.get("/api/admin/talent_pool/export?location=Ahmedabad")
        decoded = resp.data.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(decoded)))
        csv_ids = [int(r[0]) for r in reader[1:] if r[0].isdigit()]

        self.assertIn(self.user_cand_id, csv_ids)
        self.assertNotIn(self.user_cand2_id, csv_ids)

    def test_skills_filter_parity(self):
        """Skills filter ?skills=Django filters accurately in CSV export."""
        self._login(self.email_hr)
        resp = self.client.get("/api/admin/talent_pool/export?skills=Django")
        decoded = resp.data.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(decoded)))
        csv_ids = [int(r[0]) for r in reader[1:] if r[0].isdigit()]

        self.assertIn(self.user_cand_id, csv_ids)
        self.assertNotIn(self.user_cand2_id, csv_ids)

    def test_min_ats_filter_parity(self):
        """ATS filter ?min_ats=80 filters out candidates with lower scores in CSV export."""
        self._login(self.email_hr)
        resp = self.client.get("/api/admin/talent_pool/export?min_ats=80")
        decoded = resp.data.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(decoded)))
        csv_ids = [int(r[0]) for r in reader[1:] if r[0].isdigit()]

        self.assertIn(self.user_cand_id, csv_ids)
        self.assertNotIn(self.user_cand2_id, csv_ids)

    def test_empty_results_returns_valid_csv_with_headers_only(self):
        """When query matches 0 candidates, returns valid CSV with header row and no data."""
        self._login(self.email_hr)
        resp = self.client.get("/api/admin/talent_pool/export?q=NonExistentCandidateNameXYZ123")
        self.assertEqual(resp.status_code, 200)
        decoded = resp.data.decode("utf-8-sig")
        reader = list(csv.reader(io.StringIO(decoded)))
        self.assertEqual(len(reader), 1, "Expected only the header row")
        self.assertEqual(reader[0][0], "Candidate ID")

    def test_utf8_data_and_bom_encoding(self):
        """Unicode characters (e.g. Gujarati text, accents) decode properly."""
        ts_uni = _ts()
        email_uni = f"uni_{ts_uni}@test.com"
        reg_uni = register_user("વ્રજ પટેલ (Vraj Patel)", email_uni, "Password10!", "candidate", is_verified=1)
        uni_id = reg_uni["user"]["id"]

        with get_db() as conn:
            conn.execute(
                "UPDATE users SET location='અમદાવાદ (Ahmedabad)' WHERE id=?",
                (uni_id,)
            )
            conn.commit()

        self._login(self.email_hr)
        resp = self.client.get(f"/api/admin/talent_pool/export?q={email_uni}")
        self.assertEqual(resp.status_code, 200)
        # Should be UTF-8 with BOM
        self.assertTrue(resp.data.startswith(b'\xef\xbb\xbf'), "Missing UTF-8 BOM")
        decoded = resp.data.decode("utf-8-sig")
        self.assertIn("વ્રજ પટેલ", decoded)
        self.assertIn("અમદાવાદ", decoded)


if __name__ == "__main__":
    unittest.main()
