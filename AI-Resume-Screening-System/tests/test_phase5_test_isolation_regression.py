# ============================================================
#  TalentSync / HireAI — Phase 5 Test Isolation Regression Suite
#  Strictly verifies that tests use isolated temporary storage
#  and NEVER mutate the production database or upload storage.
# ============================================================

import os
import io
import time
import hashlib
import tempfile
import unittest
import docx as python_docx
from werkzeug.datastructures import FileStorage

from app import create_app
from app.config.settings import Config, ProductionConfig, DevelopmentConfig, TestingConfig, ActiveConfig
from app.database.connection import get_db, execute_query
from app.controllers.auth_controller import register_user
from app.controllers.resume_controller import process_resume_upload


def _compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestPhase5TestIsolationRegression(unittest.TestCase):

    # ── Step 5: Configuration Separation Verification ────────────

    def test_configuration_separation(self):
        """Verify that TestingConfig paths are strictly distinct from persistent DB and uploads."""
        # Check against base Config
        self.assertNotEqual(TestingConfig.DB_FILE, Config.DB_FILE)
        self.assertNotEqual(TestingConfig.UPLOAD_FOLDER, Config.UPLOAD_FOLDER)

        # Check against DevelopmentConfig
        self.assertNotEqual(TestingConfig.DB_FILE, DevelopmentConfig.DB_FILE)
        self.assertNotEqual(TestingConfig.UPLOAD_FOLDER, DevelopmentConfig.UPLOAD_FOLDER)

        # Check against ProductionConfig
        self.assertNotEqual(TestingConfig.DB_FILE, ProductionConfig.DB_FILE)
        self.assertNotEqual(TestingConfig.UPLOAD_FOLDER, ProductionConfig.UPLOAD_FOLDER)

        # Verify TestingConfig paths point to temp directory
        temp_dir = tempfile.gettempdir().lower()
        self.assertIn(temp_dir, TestingConfig.DB_FILE.lower())
        self.assertIn(temp_dir, TestingConfig.UPLOAD_FOLDER.lower())

        # Verify production paths remain canonical and within application directory
        self.assertTrue(Config.DB_FILE.endswith("talentsync.db"))
        self.assertTrue(Config.UPLOAD_FOLDER.endswith(os.path.join("uploads", "resumes")))

    # ── Step 7: Upload Storage Isolation Verification ───────────

    def test_upload_isolation(self):
        """Uploading a resume in testing mode must write ONLY to test upload folder, NEVER production."""
        prod_upload_dir = os.path.abspath(Config.UPLOAD_FOLDER)
        prod_files_before = set(os.listdir(prod_upload_dir)) if os.path.isdir(prod_upload_dir) else set()

        test_app = create_app(TestingConfig)
        with test_app.app_context():
            # Create synthetic docx
            doc = python_docx.Document()
            doc.add_paragraph("Test Candidate Resume for Storage Isolation Verification")
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)

            unique_filename = f"iso_test_{int(time.time() * 1000)}.docx"
            fs = FileStorage(stream=buf, filename=unique_filename, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

            result = process_resume_upload(fs, user_id=999999)
            self.assertTrue(result.get("success"), f"Upload failed: {result.get('message')}")

            with get_db() as conn:
                resume_row = conn.execute("SELECT stored_filename, file_path FROM resumes WHERE id=?", (result["resume_id"],)).fetchone()
                self.assertIsNotNone(resume_row)
                stored_filename = resume_row["stored_filename"]
                test_file_path = resume_row["file_path"]

            prod_file_path = os.path.join(prod_upload_dir, stored_filename)

            # 1. File MUST exist in temporary test upload folder
            self.assertTrue(os.path.exists(test_file_path), f"File missing from test upload folder: {test_file_path}")

            # 2. File MUST NOT exist in production upload folder
            self.assertFalse(os.path.exists(prod_file_path), f"CRITICAL LEAK: File was written to production uploads: {prod_file_path}")

            # 3. Production directory file set must be 100% unchanged
            prod_files_after = set(os.listdir(prod_upload_dir)) if os.path.isdir(prod_upload_dir) else set()
            self.assertEqual(prod_files_before, prod_files_after, "Production uploads directory was modified by test upload!")

            # Clean up test file
            if os.path.exists(test_file_path):
                try:
                    os.remove(test_file_path)
                except Exception:
                    pass

    # ── Step 8: Database Isolation Verification ─────────────────

    def test_database_isolation(self):
        """Database writes in testing mode must write ONLY to test database, NEVER production database."""
        prod_db = os.path.abspath(Config.DB_FILE)
        self.assertTrue(os.path.exists(prod_db), f"Production DB missing at {prod_db}")
        prod_sha_before = _compute_sha256(prod_db)

        test_app = create_app(TestingConfig)
        with test_app.app_context():
            unique_email = f"iso_test_user_{int(time.time() * 1000)}@test.com"
            res = register_user("Isolation Tester", unique_email, "ValidPassword10!", "candidate")
            self.assertTrue(res.get("success"), f"User registration failed: {res.get('message')}")
            test_user_id = res["user"]["id"]

            # 1. Verify user exists in isolated test DB
            with get_db() as conn:
                row = conn.execute("SELECT id, email FROM users WHERE id=?", (test_user_id,)).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["email"], unique_email)

            # 2. Verify user DOES NOT exist in production DB
            import sqlite3
            with sqlite3.connect(f"file:{prod_db}?mode=ro", uri=True) as prod_conn:
                prod_row = prod_conn.execute("SELECT id FROM users WHERE email=?", (unique_email,)).fetchone()
                self.assertIsNone(prod_row, f"CRITICAL LEAK: Test user {unique_email} was written to production DB!")

            # 3. Verify production DB SHA-256 is 100% untouched
            prod_sha_after = _compute_sha256(prod_db)
            self.assertEqual(prod_sha_before, prod_sha_after, "CRITICAL LEAK: Production DB hash changed during test execution!")


if __name__ == "__main__":
    unittest.main()
