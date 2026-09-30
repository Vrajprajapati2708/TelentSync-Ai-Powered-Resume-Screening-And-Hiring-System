# ============================================================
#  HireAI / TalentSync — Phase 1 Stability Regression Suite
#  Covers GAP-02, GAP-05, GAP-06, GAP-11
# ============================================================

import os
import io
import sys
import time
import unittest

_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

import docx as python_docx
from werkzeug.datastructures import FileStorage

from app import create_app
from app.config.settings import ActiveConfig, TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.controllers.resume_controller import process_resume_upload
from app.utils.validators import (
    validate_password,
    validate_file_extension,
    validate_file_bytes,
    MIN_PASSWORD_LENGTH,
)


def _make_docx_stream(text: str = "Senior Engineer with Python, Flask, SQL experience.") -> io.BytesIO:
    doc = python_docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


class TestPhase1StabilityRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestingConfig)

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    # ------------------------------------------------------------
    # GAP-06: Database Path Determinism & Integrity
    # ------------------------------------------------------------
    def test_gap06_db_file_is_absolute_path(self):
        """ActiveConfig.DB_FILE must resolve to an absolute path."""
        self.assertTrue(
            os.path.isabs(ActiveConfig.DB_FILE),
            f"DB_FILE '{ActiveConfig.DB_FILE}' should be an absolute path."
        )

    def test_gap06_db_file_points_to_canonical_active_db(self):
        """ActiveConfig.DB_FILE must point to the existing active database."""
        self.assertTrue(
            os.path.exists(ActiveConfig.DB_FILE),
            f"Database file does not exist at '{ActiveConfig.DB_FILE}'"
        )
        self.assertTrue(
            ActiveConfig.DB_FILE.endswith(os.path.join("AI-Resume-Screening-System", "talentsync.db")),
            f"DB_FILE must point to AI-Resume-Screening-System/talentsync.db, got: {ActiveConfig.DB_FILE}"
        )

    def test_gap06_database_connection_accesses_active_tables(self):
        """get_db() must query the active database containing seeded tables."""
        with get_db() as conn:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            job_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            self.assertGreater(user_count, 0, "Users table in active DB must not be empty.")
            self.assertGreater(job_count, 0, "Jobs table in active DB must not be empty.")

    # ------------------------------------------------------------
    # GAP-11: Supported vs Unsupported Extensions (.doc rejected)
    # ------------------------------------------------------------
    def test_gap11_allowed_extensions_excludes_doc(self):
        """ActiveConfig.ALLOWED_EXTENSIONS must strictly be {'pdf', 'docx'}."""
        self.assertEqual(ActiveConfig.ALLOWED_EXTENSIONS, {'pdf', 'docx'})
        self.assertNotIn('doc', ActiveConfig.ALLOWED_EXTENSIONS)

    def test_gap11_validate_file_extension_rejects_doc(self):
        """validate_file_extension must reject .doc and accept .pdf and .docx."""
        self.assertFalse(validate_file_extension("resume.doc"))
        self.assertFalse(validate_file_extension("MY_CV.DOC"))
        self.assertTrue(validate_file_extension("resume.docx"))
        self.assertTrue(validate_file_extension("resume.pdf"))

    def test_gap11_validate_file_bytes_explicit_doc_message(self):
        """validate_file_bytes must give a helpful rejection message for .doc files."""
        fake_stream = io.BytesIO(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1 legacy doc binary")
        is_valid, msg = validate_file_bytes(fake_stream, "my_resume.doc")
        self.assertFalse(is_valid)
        self.assertIn(".doc", msg)
        self.assertIn("not supported", msg)

    # ------------------------------------------------------------
    # GAP-05: Password Policy Consistency (Minimum 10 Characters)
    # ------------------------------------------------------------
    def test_gap05_password_length_rejection_under_10(self):
        """validate_password must reject passwords with length < 10."""
        self.assertEqual(MIN_PASSWORD_LENGTH, 10)
        is_empty_valid, empty_msg = validate_password("")
        self.assertFalse(is_empty_valid)
        self.assertIn("required", empty_msg.lower())

        for pw in ["Short1!", "Pass9!ab", "NineChars"]:
            is_valid, msg = validate_password(pw)
            self.assertFalse(is_valid, f"Password '{pw}' (len {len(pw)}) should be rejected.")
            self.assertIn("10", msg)

    def test_gap05_password_length_acceptance_at_10(self):
        """validate_password must accept valid 10-character passwords."""
        is_valid, msg = validate_password("ValidPass1!")
        self.assertTrue(is_valid, f"10-char password should pass, got error: {msg}")

    def test_gap05_register_rejects_9_char_password(self):
        """POST /api/auth/register must reject a 9-character password with HTTP 400."""
        res = self.client.post("/api/auth/register", json={
            "name": "Test ShortPass",
            "email": f"short_{int(time.time()*1000)}@test.com",
            "password": "Short9!ab",
            "role": "candidate"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("10", data.get("message", ""))

    # ------------------------------------------------------------
    # GAP-02: Resume Upload Error Handling & Response Contract
    # ------------------------------------------------------------
    def test_gap02_unsupported_doc_upload_returns_controlled_error(self):
        """Uploading a .doc file returns HTTP 400 with success=False and clear message."""
        stream = io.BytesIO(b"dummy binary content")
        fs = FileStorage(stream=stream, filename="my_resume.doc", content_type="application/msword")
        result = process_resume_upload(fs, user_id=None)
        self.assertFalse(result.get("success"))
        self.assertIn("message", result)
        self.assertNotIn("data", result)  # data.data is not created on error

    def test_gap02_empty_file_upload_returns_controlled_error(self):
        """Uploading an empty file returns HTTP 400 with success=False and clear message."""
        stream = io.BytesIO(b"")
        fs = FileStorage(stream=stream, filename="empty.pdf", content_type="application/pdf")
        result = process_resume_upload(fs, user_id=None)
        self.assertFalse(result.get("success"))
        self.assertIn("message", result)
        self.assertNotIn("data", result)

    def test_gap02_corrupt_pdf_returns_controlled_error(self):
        """Uploading a PDF with invalid magic-bytes returns HTTP 400 with success=False."""
        stream = io.BytesIO(b"This is not a PDF file header.")
        fs = FileStorage(stream=stream, filename="corrupt.pdf", content_type="application/pdf")
        result = process_resume_upload(fs, user_id=None)
        self.assertFalse(result.get("success"))
        self.assertIn("magic-byte", result.get("message", "").lower())
        self.assertNotIn("data", result)

    def test_gap02_valid_docx_upload_succeeds_with_contract(self):
        """Uploading a valid DOCX returns HTTP 200 with success=True and populated data."""
        test_email = f"p1_cand_{int(time.time()*1000)}@test.com"
        reg = register_user("Phase1 User", test_email, "ValidPassword10!", "candidate")
        self.assertTrue(reg.get("success"), f"Registration failed: {reg.get('message')}")
        user_id = reg["user"]["id"]

        stream = _make_docx_stream("Python Software Developer with Flask, SQL, Docker, and Git.")
        fs = FileStorage(
            stream=stream,
            filename="Valid_Candidate_Resume.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        result = process_resume_upload(fs, user_id=user_id)
        self.assertTrue(result.get("success"), f"Valid upload failed: {result.get('message')}")
        self.assertIn("data", result)
        self.assertIn("ats_score", result["data"])
        self.assertIsInstance(result["data"]["skills"], list)


if __name__ == "__main__":
    unittest.main()
