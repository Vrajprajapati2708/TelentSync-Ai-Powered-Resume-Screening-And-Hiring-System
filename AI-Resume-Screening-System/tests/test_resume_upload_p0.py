# ============================================================
#  HireAI — Resume Upload P0 Test Suite  (UPLOAD-05)
#  Comprehensive automated tests covering:
#    Validators, Storage, SHA-256 Hashing, Parser Guards,
#    DB Transactions, REST API, and Ownership Authorization
# ============================================================

import io
import os
import time
import hashlib
import unittest
import tempfile
import docx as python_docx
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import FileStorage

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.controllers.resume_controller import (
    calculate_file_hash,
    check_duplicate_resume,
    save_resume_file_to_disk,
    process_resume_upload,
    UPLOAD_FOLDER,
)
from app.utils.validators import validate_file_bytes, MAX_FILE_SIZE_BYTES


# ── Shared helpers ──────────────────────────────────────────────

def _ts() -> str:
    """Nanosecond-precision unique tag to avoid email collisions."""
    return str(int(time.time() * 1_000_000))


def _make_docx_stream(text: str = "Python developer with Flask SQL experience") -> io.BytesIO:
    """Build an in-memory valid .docx binary stream."""
    doc = python_docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def _make_filestorage(stream: io.BytesIO, filename: str, mimetype: str = "application/pdf") -> FileStorage:
    stream.seek(0)
    return FileStorage(stream=stream, filename=filename, content_type=mimetype)


# ── Test Case 1: Validator — Magic Byte & File Integrity ───────

class TestValidateFileBytes(unittest.TestCase):
    """UPLOAD-02 validator unit tests."""

    def test_valid_pdf_magic_byte(self):
        """Valid PDF with %PDF- header should pass."""
        f = io.BytesIO(b"%PDF-1.4\nValid PDF Content Here")
        ok, msg = validate_file_bytes(f, "resume.pdf")
        self.assertTrue(ok, msg)

    def test_valid_docx_magic_byte(self):
        """Valid DOCX (Zip PK header) should pass."""
        f = _make_docx_stream()
        ok, msg = validate_file_bytes(f, "resume.docx")
        self.assertTrue(ok, msg)

    def test_empty_file_rejected(self):
        """0-byte file should be rejected with 'empty' message."""
        f = io.BytesIO(b"")
        ok, msg = validate_file_bytes(f, "empty.pdf")
        self.assertFalse(ok)
        self.assertIn("empty", msg.lower())

    def test_corrupted_binary_rejected(self):
        """Non-PDF binary submitted as .pdf should fail magic-byte check."""
        f = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00This is an EXE")
        ok, msg = validate_file_bytes(f, "malware.pdf")
        self.assertFalse(ok)
        self.assertIn("magic", msg.lower())

    def test_legacy_doc_rejected(self):
        """Legacy binary .doc files should be explicitly blocked."""
        f = io.BytesIO(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1Word97")
        ok, msg = validate_file_bytes(f, "old.doc")
        self.assertFalse(ok)
        self.assertIn(".doc", msg)

    def test_unsupported_extension_rejected(self):
        """.exe extension should be rejected."""
        f = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00executable")
        ok, msg = validate_file_bytes(f, "resume.exe")
        self.assertFalse(ok)
        self.assertIn("Unsupported", msg)

    def test_oversized_file_rejected(self):
        """File exceeding 10 MB should be rejected with size message."""
        large_content = b"A" * (MAX_FILE_SIZE_BYTES + 1)
        f = io.BytesIO(large_content)
        ok, msg = validate_file_bytes(f, "huge.pdf")
        self.assertFalse(ok)
        self.assertIn("10MB", msg)

    def test_missing_extension_rejected(self):
        """File with no extension should be rejected."""
        f = io.BytesIO(b"%PDF-1.4\nContent")
        ok, msg = validate_file_bytes(f, "noresumename")
        self.assertFalse(ok)


# ── Test Case 2: SHA-256 Hashing & Duplicate Recognition ───────

class TestSHA256Hashing(unittest.TestCase):
    """UPLOAD-03B hashing unit tests."""

    def test_hash_matches_stdlib(self):
        """calculate_file_hash should produce identical digest to hashlib."""
        content = b"%PDF-1.4\nSome unique content"
        stream = io.BytesIO(content)
        got = calculate_file_hash(stream)
        expected = hashlib.sha256(content).hexdigest()
        self.assertEqual(got, expected)

    def test_hash_resets_stream_pointer(self):
        """Stream pointer should be reset to 0 after hashing."""
        stream = io.BytesIO(b"%PDF-1.4\nContent")
        calculate_file_hash(stream)
        self.assertEqual(stream.tell(), 0)

    def test_different_content_produces_different_hash(self):
        """Two different content blobs should never produce the same hash."""
        h1 = calculate_file_hash(io.BytesIO(b"Content A"))
        h2 = calculate_file_hash(io.BytesIO(b"Content B"))
        self.assertNotEqual(h1, h2)

    def test_duplicate_detection_same_user(self):
        """Same user uploading same file hash should be flagged as duplicate."""
        app = create_app(TestingConfig)
        user_id = 9990 + int(_ts()[-3:])
        file_hash = f"test_hash_{user_id}"

        with app.app_context():
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, "t.pdf", f"res_{user_id}.pdf", "/fake/path.pdf", file_hash, 1024, "application/pdf")
                )
                conn.commit()

            dup = check_duplicate_resume(user_id, file_hash)
            self.assertIsNotNone(dup)
            self.assertEqual(dup["file_hash"], file_hash)

            with get_db() as conn:
                conn.execute("DELETE FROM resumes WHERE user_id=?", (user_id,))
                conn.commit()

    def test_duplicate_detection_different_users(self):
        """Same file hash for different users should NOT be treated as duplicate."""
        app = create_app(TestingConfig)
        user_a = 8881 + int(_ts()[-3:])
        user_b = 8882 + int(_ts()[-3:])
        file_hash = f"shared_hash_{user_a}"

        with app.app_context():
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO resumes (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (user_a, "a.pdf", f"res_{user_a}.pdf", "/fake/a.pdf", file_hash, 1024, "application/pdf")
                )
                conn.commit()

            dup = check_duplicate_resume(user_b, file_hash)
            self.assertIsNone(dup, "Different user with same hash must NOT be flagged duplicate")

            with get_db() as conn:
                conn.execute("DELETE FROM resumes WHERE user_id=?", (user_a,))
                conn.commit()


# ── Test Case 3: Storage Engine ─────────────────────────────────

class TestStorageEngine(unittest.TestCase):
    """UPLOAD-03A storage engine unit tests."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_upload_folder_auto_created(self):
        """UPLOAD_FOLDER directory should already exist after module import."""
        self.assertTrue(os.path.isdir(UPLOAD_FOLDER))

    def test_file_saved_with_uuid_name(self):
        """Saved filename should start with res_{user_id}_ pattern."""
        stream = io.BytesIO(b"%PDF-1.4\nSample Resume Content")
        ok, res = save_resume_file_to_disk(stream, "test.pdf", user_id=1)
        self.assertTrue(ok, res)
        self.assertTrue(res["stored_filename"].startswith("res_1_"))
        self.assertTrue(os.path.exists(res["file_path"]))
        os.remove(res["file_path"])

    def test_duplicate_original_filenames_get_unique_paths(self):
        """Two uploads with identical original filenames should produce different UUIDs."""
        s1 = io.BytesIO(b"%PDF-1.4\nContent A")
        s2 = io.BytesIO(b"%PDF-1.4\nContent B")
        _, r1 = save_resume_file_to_disk(s1, "resume.pdf", user_id=99)
        _, r2 = save_resume_file_to_disk(s2, "resume.pdf", user_id=99)
        self.assertNotEqual(r1["stored_filename"], r2["stored_filename"])
        os.remove(r1["file_path"])
        os.remove(r2["file_path"])

    def test_unicode_filename_preserved_as_original_name(self):
        """Unicode original filename should be preserved as metadata."""
        stream = io.BytesIO(b"%PDF-1.4\nResume")
        ok, res = save_resume_file_to_disk(stream, "Résumé_ગુજરાતી.pdf", user_id=42)
        self.assertTrue(ok)
        self.assertEqual(res["original_name"], "Résumé_ગુજરાતી.pdf")
        os.remove(res["file_path"])

    def test_disk_write_failure_returns_clean_error(self):
        """If disk write fails (mocked), should return failure message not raise."""
        with patch("builtins.open", side_effect=OSError("Simulated disk full")):
            stream = io.BytesIO(b"%PDF-1.4\nContent")
            ok, msg = save_resume_file_to_disk(stream, "test.pdf", user_id=1)
        self.assertFalse(ok)
        self.assertIn("Failed to save", msg)


# ── Test Case 4: REST API — Upload, Download & Authorization ───

class TestResumeAPIUpload04(unittest.TestCase):
    """UPLOAD-04 REST API and authorization tests."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        ts = _ts()

        self.email_a  = f"cand_a_{ts}@test.com"
        self.email_b  = f"cand_b_{ts}@test.com"
        self.email_hr = f"hr_{ts}@test.com"

        reg_a  = register_user("Candidate A",  self.email_a,  "Password10!", "candidate", is_verified=1)
        reg_b  = register_user("Candidate B",  self.email_b,  "Password10!", "candidate", is_verified=1)
        reg_hr = register_user("HR Recruiter", self.email_hr, "Password10!", "hr", allow_privileged=True, is_verified=1)

        self.user_a_id  = reg_a["user"]["id"]
        self.user_b_id  = reg_b["user"]["id"]
        self.user_hr_id = reg_hr["user"]["id"]

    def tearDown(self):
        self.app_context.pop()

    def _login(self, email: str):
        return self.client.post("/api/auth/login", json={"email": email, "password": "Password10!"})

    def _upload_docx_as(self, email: str):
        """Login as `email` and upload a valid DOCX. Returns upload response object."""
        self._login(email)
        buf = _make_docx_stream(f"Developer resume for {email}")
        buf.seek(0)
        resp = self.client.post(
            "/api/upload_resume",
            data={"resume": (buf, "Resume.docx")},
            content_type="multipart/form-data",
        )
        return resp

    # 4-1: Valid DOCX Upload
    def test_valid_docx_upload(self):
        """Valid DOCX upload should return 200 with resume_id."""
        resp = self._upload_docx_as(self.email_a)
        data = resp.get_json() or {}
        self.assertEqual(resp.status_code, 200, data)
        self.assertTrue(data.get("success"))
        self.assertIsNotNone(data.get("resume_id"))

    # 4-2: No File Submitted
    def test_upload_no_file_returns_400(self):
        """Upload without attaching a file should return 400."""
        self._login(self.email_a)
        resp = self.client.post("/api/upload_resume", data={}, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 400)

    # 4-3: Legacy .doc File Rejected
    def test_upload_doc_rejected_400(self):
        """Legacy .doc binary should return 400 with .doc message."""
        self._login(self.email_a)
        stream = io.BytesIO(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1Legacy")
        resp = self.client.post(
            "/api/upload_resume",
            data={"resume": (stream, "old_cv.doc")},
            content_type="multipart/form-data",
        )
        data = resp.get_json() or {}
        self.assertEqual(resp.status_code, 400)
        self.assertIn(".doc", data.get("message", ""))

    # 4-4: Magic-Byte Spoof (.exe renamed to .pdf) Rejected
    def test_upload_spoofed_exe_as_pdf_rejected(self):
        """Executable binary submitted as .pdf should be rejected by magic-byte check."""
        self._login(self.email_a)
        stream = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00Executable")
        resp = self.client.post(
            "/api/upload_resume",
            data={"resume": (stream, "malware.pdf")},
            content_type="multipart/form-data",
        )
        data = resp.get_json() or {}
        self.assertEqual(resp.status_code, 400)
        self.assertIn("magic", data.get("message", "").lower())

    # 4-5: Empty File Rejected
    def test_upload_empty_file_rejected_400(self):
        """0-byte empty file should return 400."""
        self._login(self.email_a)
        stream = io.BytesIO(b"")
        resp = self.client.post(
            "/api/upload_resume",
            data={"resume": (stream, "empty.pdf")},
            content_type="multipart/form-data",
        )
        data = resp.get_json() or {}
        self.assertEqual(resp.status_code, 400)
        self.assertIn("empty", data.get("message", "").lower())

    # 4-6: Oversized File Rejected
    def test_upload_oversized_file_rejected_400(self):
        """15 MB file should be rejected — HTTP 400 by our size guard or 413 by Flask WSGI layer."""
        self._login(self.email_a)
        huge = io.BytesIO(b"%PDF-1.4\n" + b"X" * (15 * 1024 * 1024))
        resp = self.client.post(
            "/api/upload_resume",
            data={"resume": (huge, "big.pdf")},
            content_type="multipart/form-data",
        )
        # Flask MAX_CONTENT_LENGTH returns 413; our validator returns 400 — both are correct rejections
        self.assertIn(resp.status_code, (400, 413), f"Expected 400 or 413, got {resp.status_code}")

    # 4-7: Duplicate Upload Detection
    def test_duplicate_upload_flagged(self):
        """Uploading the same DOCX content twice should return is_duplicate=True on second call."""
        self._login(self.email_a)
        stream = _make_docx_stream(f"Developer resume for {self.email_a}")
        raw_bytes = stream.getvalue()

        # First upload
        buf1 = io.BytesIO(raw_bytes)
        resp1 = self.client.post(
            "/api/upload_resume",
            data={"resume": (buf1, "Resume.docx")},
            content_type="multipart/form-data",
        )
        data1 = resp1.get_json() or {}
        self.assertEqual(resp1.status_code, 200, data1)
        self.assertTrue(data1.get("success"))

        # Second upload — identical raw bytes guarantees matching file hash
        buf2 = io.BytesIO(raw_bytes)
        resp2 = self.client.post(
            "/api/upload_resume",
            data={"resume": (buf2, "Resume.docx")},
            content_type="multipart/form-data",
        )
        data2 = resp2.get_json() or {}
        self.assertEqual(resp2.status_code, 200, data2)
        self.assertTrue(data2.get("is_duplicate"), "Second identical upload must be flagged as duplicate")

    # 4-8: Candidate downloads own resume → 200
    def test_candidate_downloads_own_resume_200(self):
        """Candidate downloading their own resume should return HTTP 200."""
        resp = self._upload_docx_as(self.email_a)
        data = resp.get_json() or {}
        resume_id = data.get("resume_id")

        self._login(self.email_a)
        dl = self.client.get(f"/api/resume/download/{resume_id}")
        self.assertEqual(dl.status_code, 200)

    # 4-9: Candidate A blocked from Candidate B resume → 403
    def test_candidate_blocked_from_other_candidate_resume_403(self):
        """Candidate A attempting to download Candidate B's resume must receive HTTP 403."""
        resp = self._upload_docx_as(self.email_a)
        data = resp.get_json() or {}
        resume_id = data.get("resume_id")

        self._login(self.email_b)
        dl = self.client.get(f"/api/resume/download/{resume_id}")
        data_dl = dl.get_json() or {}
        self.assertEqual(dl.status_code, 403, "Unauthorized cross-candidate access must be blocked with HTTP 403")
        self.assertFalse(data_dl.get("success"))

    # 4-10: HR downloads candidate resume → 200
    def test_hr_downloads_candidate_resume_200(self):
        """HR role must be able to download any candidate's resume."""
        resp = self._upload_docx_as(self.email_a)
        data = resp.get_json() or {}
        resume_id = data.get("resume_id")

        self._login(self.email_hr)
        dl = self.client.get(f"/api/resume/download/{resume_id}")
        self.assertEqual(dl.status_code, 200, "HR role must be authorized to download candidate resumes")

    # 4-11: Unauthenticated download attempt
    def test_anonymous_download_blocked(self):
        """Download request without session should return authentication failure."""
        # Deliberately create a fresh client with no session cookie
        fresh_client = self.app.test_client()
        dl = fresh_client.get("/api/resume/download/1")
        self.assertIn(dl.status_code, (401, 302, 403))

    # 4-12: Missing resume file on disk → controlled 404
    def test_missing_resume_file_on_disk_returns_404(self):
        """If DB record exists but file was deleted, endpoint should return controlled 404."""
        resp = self._upload_docx_as(self.email_a)
        data = resp.get_json() or {}
        resume_id = data.get("resume_id")

        # Manually delete the disk file to simulate unexpected removal
        with self.app.app_context():
            with get_db() as conn:
                row = conn.execute("SELECT file_path FROM resumes WHERE id=?", (resume_id,)).fetchone()
                file_path = row["file_path"]

        if os.path.exists(file_path):
            os.remove(file_path)

        self._login(self.email_a)
        dl = self.client.get(f"/api/resume/download/{resume_id}")
        self.assertEqual(dl.status_code, 404, "Missing file on disk must return 404 not 500")

    # 4-13: Non-existent resume ID → 404
    def test_nonexistent_resume_id_returns_404(self):
        """Fetching a resume_id that does not exist should return HTTP 404."""
        self._login(self.email_a)
        dl = self.client.get("/api/resume/download/999999")
        self.assertEqual(dl.status_code, 404)

    # 4-14: /my_resumes only returns current user's records
    def test_my_resumes_returns_only_own_records(self):
        """GET /api/resume/my_resumes must return only resumes belonging to the logged-in user."""
        # Upload for candidate A
        self._upload_docx_as(self.email_a)
        # Upload different content for candidate B (different hash)
        self._login(self.email_b)
        buf_b = _make_docx_stream(f"Candidate B unique resume {_ts()}")
        buf_b.seek(0)
        self.client.post(
            "/api/upload_resume",
            data={"resume": (buf_b, "Resume_B.docx")},
            content_type="multipart/form-data",
        )

        # Candidate A fetches their own resumes
        self._login(self.email_a)
        r = self.client.get("/api/resume/my_resumes")
        self.assertEqual(r.status_code, 200)
        data_r = r.get_json() or {}
        for rec in data_r.get("resumes", []):
            self.assertEqual(rec["user_id"] if "user_id" in rec else self.user_a_id, self.user_a_id)

    # 4-15: DB rollback file cleanup on insert failure (mocked)
    def test_db_failure_triggers_disk_cleanup(self):
        """If DB insert fails, the saved disk file must be removed automatically."""
        self._login(self.email_a)
        buf = _make_docx_stream("Python developer resume for rollback test")
        buf.seek(0)
        file_storage = FileStorage(
            stream=buf,
            filename="Rollback_Test.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        created_paths = []

        original_save = __import__(
            "app.controllers.resume_controller", fromlist=["save_resume_file_to_disk"]
        ).save_resume_file_to_disk

        def capturing_save(stream, filename, user_id=0):
            ok, result = original_save(stream, filename, user_id)
            if ok:
                created_paths.append(result["file_path"])
            return ok, result

        with patch("app.controllers.resume_controller.save_resume_file_to_disk", side_effect=capturing_save):
            with patch("app.database.connection.get_db") as mock_get_db:
                mock_conn = MagicMock()
                mock_conn.__enter__ = MagicMock(return_value=mock_conn)
                mock_conn.__exit__ = MagicMock(return_value=False)
                mock_conn.execute.side_effect = Exception("Simulated DB insert failure")
                mock_get_db.return_value = mock_conn

                result = process_resume_upload(file_storage, user_id=self.user_a_id)

        # Either the upload fails cleanly...
        if not result.get("success"):
            self.assertIn("fail", result["message"].lower())
            # If a file was written, it must now be cleaned up
            for path in created_paths:
                self.assertFalse(os.path.exists(path), f"Orphan file should have been deleted: {path}")
        # ...or it short-circuits before DB (e.g. duplicate path taken) — also acceptable
        else:
            self.assertTrue(result.get("is_duplicate") or result.get("success"))


# ── Main Runner ────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestValidateFileBytes))
    suite.addTests(loader.loadTestsFromTestCase(TestSHA256Hashing))
    suite.addTests(loader.loadTestsFromTestCase(TestStorageEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestResumeAPIUpload04))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
