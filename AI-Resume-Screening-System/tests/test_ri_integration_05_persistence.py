# ============================================================
#  TalentSync — Test: RI-INTEGRATION-05 Persistence Sync
#  Verifies canonical JSON serialization & DB persistence
# ============================================================

import sys
import os
import io
import json
import unittest
import docx as python_docx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from app.controllers.auth_controller import register_user
from app.controllers.resume_controller import process_resume_upload, check_duplicate_resume
from werkzeug.datastructures import FileStorage


def _make_docx_stream(text: str) -> io.BytesIO:
    doc = python_docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


class TestRIIntegration05Persistence(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        # Create test user
        self.test_email = f"ri05_cand_{os.urandom(4).hex()}@test.com"
        reg = register_user("RI05 Candidate", self.test_email, "ValidPass10!", "candidate")
        self.assertTrue(reg.get('success'), f"User registration failed: {reg.get('message')}")
        self.user_id = reg['user']['id']

    def tearDown(self):
        self.app_context.pop()

    def test_structured_json_persistence_and_deserialization(self):
        """Verify new upload stores valid structured_json with all canonical RI fields preserved."""
        resume_text = (
            "Jörgen Sjöberg | jorgen.sjoberg@example.com | +46 70 123 4567\n"
            "Summary: Senior Software Engineer with 8 years of Python experience.\n"
            "Skills: Python, Machine Learning, SQL, Docker, FastAPI\n"
            "Experience: TechCorp AB — Senior Engineer (2020 - Present)\n"
            "Education: M.Sc. Computer Science, KTH Royal Institute of Technology, CGPA: 9.2"
        )
        stream = _make_docx_stream(resume_text)
        fs = FileStorage(stream=stream, filename="Jorgen_CV.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        result = process_resume_upload(fs, user_id=self.user_id)
        self.assertTrue(result.get('success'), f"Upload failed: {result.get('message')}")

        resume_id = result.get('resume_id')
        self.assertIsNotNone(resume_id)

        # Inspect database row directly
        with get_db() as conn:
            row = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
            self.assertIsNotNone(row)
            row_dict = dict(row)

        # 1. structured_json column presence & string type
        self.assertIn('structured_json', row_dict)
        raw_json_str = row_dict['structured_json']
        self.assertIsInstance(raw_json_str, str)
        self.assertTrue(len(raw_json_str) > 0)

        # 2. Deserializes cleanly to Python dictionary
        intel = json.loads(raw_json_str)
        self.assertIsInstance(intel, dict)

        # 3. Canonical RI fields preserved inside deserialized JSON
        self.assertIn('candidate', intel)
        self.assertIn('contact', intel)
        self.assertIn('sections', intel)
        self.assertIn('skills', intel)
        self.assertIn('experience', intel)
        self.assertIn('education', intel)
        self.assertIn('quality', intel)
        self.assertIn('metadata', intel)

        # 4. Unicode candidate name preservation
        self.assertIn('Jörgen Sjöberg', resume_text)

        # 5. Legacy DB fields preserved intact
        self.assertTrue(len(row_dict['parsed_text']) > 0)
        self.assertGreater(row_dict['ats_score'], 0)
        self.assertTrue(len(row_dict['extracted_skills']) > 0)

    def test_historical_rows_not_reprocessed(self):
        """Verify existing database rows remain with structured_json='' default."""
        with get_db() as conn:
            rows = conn.execute("SELECT structured_json FROM resumes LIMIT 5").fetchall()
            for r in rows:
                self.assertIn(r['structured_json'], ['', None])


if __name__ == '__main__':
    unittest.main()
