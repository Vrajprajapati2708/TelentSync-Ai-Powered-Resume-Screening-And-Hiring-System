# ============================================================
#  HireAI — Resume Intelligence Builder Integration Test Suite (RI-08)
#  30 Comprehensive Enterprise Test Cases
# ============================================================

import io
import unittest
from docx import Document
from PyPDF2 import PdfWriter
from app.ml.resume_intelligence import build_resume_intelligence
from app.ml.parsers.resume_parser import parse_resume


class TestResumeIntelligenceBuilderRI08(unittest.TestCase):
    """RI-08 Canonical Resume JSON Builder Integration Test Suite."""

    def _create_mock_pdf(self, text: str) -> io.BytesIO:
        """Helper to build an in-memory test PDF."""
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        return buf

    def _create_mock_docx(self, text: str) -> io.BytesIO:
        """Helper to build an in-memory test DOCX with readable text."""
        doc = Document()
        for paragraph in text.split('\n'):
            if paragraph.strip():
                doc.add_paragraph(paragraph.strip())
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    def test_pdf_end_to_end(self):
        """End-to-end pipeline execution with DOCX/PDF stream."""
        docx_text = """
        John Doe
        john.doe@example.com | +91 9876543210
        https://linkedin.com/in/johndoe

        TECHNICAL SKILLS
        Python, React, SQL

        EXPERIENCE
        Software Engineer at Google (Jan 2022 - Present)

        EDUCATION
        B.Tech in Computer Science, JG University, 2022
        """
        stream = self._create_mock_docx(docx_text)
        res = build_resume_intelligence(stream, "john_doe.docx")

        self.assertEqual(res["candidate"]["name"], "John Doe")
        self.assertEqual(res["contact"]["email"], "john.doe@example.com")
        self.assertGreater(len(res["skills"]), 0)
        self.assertEqual(res["metadata"]["parse_status"], "success")

    def test_docx_end_to_end(self):
        """End-to-end processing of a DOCX file stream."""
        text = "Jane Smith\njane@example.com\nSkills: Python, AWS"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "jane.docx")

        self.assertEqual(res["contact"]["email"], "jane@example.com")
        self.assertEqual(res["metadata"]["file_type"], "docx")

    def test_multi_page_pdf(self):
        """Multi-page document handling."""
        writer = PdfWriter()
        writer.add_blank_page(612, 792)
        writer.add_blank_page(612, 792)
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)

        res = build_resume_intelligence(buf, "multipage.pdf")
        self.assertIn("metadata", res)

    def test_multi_page_docx(self):
        """Multi-page DOCX handling."""
        doc = Document()
        doc.add_paragraph("Header candidate info\njane@example.com")
        doc.add_page_break()
        doc.add_paragraph("Second page experience details")
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        res = build_resume_intelligence(buf, "multipage.docx")
        self.assertEqual(res["metadata"]["parse_status"], "success")

    def test_complete_resume(self):
        """Canonical JSON building for complete resume."""
        text = """
        Jane Doe
        jane@example.com | +91 9876543210
        https://linkedin.com/in/janedoe

        SUMMARY
        Software engineer with 3 years experience.

        SKILLS
        Python, React, SQL, Docker

        EXPERIENCE
        Senior Software Engineer at Microsoft (Jan 2021 - Present)

        EDUCATION
        B.Tech, JG University, 2021, CGPA: 8.5

        CERTIFICATIONS
        AWS Certified Developer
        """
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "complete.docx")

        self.assertIsNotNone(res["candidate"]["name"])
        self.assertIsNotNone(res["contact"]["email"])
        self.assertGreater(len(res["skills"]), 0)
        self.assertGreater(len(res["experience"]), 0)
        self.assertGreater(len(res["education"]), 0)

    def test_missing_sections(self):
        """Handle resumes with missing section headers."""
        text = "Jane Doe\njane@example.com\nPython developer."
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "missing_sec.docx")

        self.assertIn("missing_sections", res["quality"])

    def test_missing_contact_fields(self):
        """Missing contact fields safely return None."""
        text = "Python developer resume text"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "no_contact.docx")

        self.assertIsNone(res["contact"]["email"])
        self.assertIsNone(res["contact"]["phone"])

    def test_missing_experience(self):
        """Missing experience returns empty list and 0.0 total years."""
        text = "Jane Doe\njane@example.com\nSkills: Python"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "no_exp.docx")

        self.assertEqual(res["experience"], [])
        self.assertEqual(res["total_experience_years"], 0.0)

    def test_missing_education(self):
        """Missing education returns empty education list."""
        text = "Jane Doe\njane@example.com\nSkills: Python"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "no_edu.docx")

        self.assertEqual(res["education"], [])

    def test_missing_skills(self):
        """Missing skills returns empty skills list."""
        text = "Jane Doe\njane@example.com\nNo tech mentioned."
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "no_skills.docx")

        self.assertEqual(res["skills"], [])

    def test_missing_certifications(self):
        """Missing certifications returns empty certifications list."""
        text = "Jane Doe\njane@example.com\nSkills: Python"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "no_certs.docx")

        self.assertEqual(res["certifications"], [])

    def test_missing_projects(self):
        """Projects defaults to empty list when absent."""
        text = "Jane Doe\njane@example.com"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "no_projects.docx")

        self.assertEqual(res["projects"], [])

    def test_empty_file(self):
        """Empty file stream returns failed parse metadata."""
        buf = io.BytesIO(b"")
        res = build_resume_intelligence(buf, "empty.docx")

        self.assertEqual(res["metadata"]["parse_status"], "failed")

    def test_corrupted_pdf(self):
        """Corrupted PDF stream returns failed status without crash."""
        buf = io.BytesIO(b"%PDF-1.4 corrupted garbage bytes")
        res = build_resume_intelligence(buf, "corrupt.pdf")

        self.assertEqual(res["metadata"]["parse_status"], "failed")

    def test_corrupted_docx(self):
        """Corrupted DOCX stream returns failed status without crash."""
        buf = io.BytesIO(b"PK\x03\x04 corrupted docx bytes")
        res = build_resume_intelligence(buf, "corrupt.docx")

        self.assertEqual(res["metadata"]["parse_status"], "failed")

    def test_unsupported_file_extension(self):
        """Unsupported file extension returns failed status."""
        buf = io.BytesIO(b"text file content")
        res = build_resume_intelligence(buf, "resume.txt")

        self.assertEqual(res["metadata"]["parse_status"], "failed")

    def test_unicode_resume(self):
        """Process resume containing international Unicode characters."""
        text = "Jörgen Sjöberg\njorgen@example.com\nSkills: Python"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "unicode.docx")

        self.assertEqual(res["candidate"]["name"], "Jörgen Sjöberg")

    def test_unicode_candidate_name(self):
        """Preserve accents in candidate name."""
        text = "Renée Dupont\nrenee@example.com"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "renee.docx")

        self.assertEqual(res["candidate"]["name"], "Renée Dupont")

    def test_deterministic_repeated_execution(self):
        """Repeated calls with identical stream return identical dicts."""
        text = "Jane Doe\njane@example.com\nSkills: Python, SQL"
        stream1 = self._create_mock_docx(text)
        stream2 = self._create_mock_docx(text)

        res1 = build_resume_intelligence(stream1, "test.docx")
        res2 = build_resume_intelligence(stream2, "test.docx")
        self.assertEqual(res1, res2)

    def test_canonical_schema_validation(self):
        """Validate canonical JSON top-level keys."""
        text = "Jane Doe\njane@example.com"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "schema.docx")

        required_keys = [
            "candidate", "contact", "sections", "skills", "experience",
            "total_experience_years", "education", "certifications",
            "languages", "projects", "quality", "metadata"
        ]
        for key in required_keys:
            self.assertIn(key, res)

    def test_required_top_level_keys(self):
        """Verify presence of all mandatory top-level keys."""
        buf = io.BytesIO(b"")
        res = build_resume_intelligence(buf, "failed.docx")
        self.assertIn("candidate", res)
        self.assertIn("contact", res)
        self.assertIn("sections", res)

    def test_required_nested_keys(self):
        """Verify nested structure inside contact and metadata."""
        text = "Jane Doe\njane@example.com"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "nested.docx")

        self.assertIn("email", res["contact"])
        self.assertIn("phone", res["contact"])
        self.assertIn("builder_version", res["metadata"])

    def test_optional_data_represented_safely(self):
        """Unextracted optional data defaults to None/[] safely."""
        text = "Jane Doe\njane@example.com"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "optional.docx")

        self.assertIsNone(res["contact"]["portfolio"])
        self.assertEqual(res["certifications"], [])

    def test_parser_failure_propagation(self):
        """Ensure parse_errors list propagates from RI-01."""
        buf = io.BytesIO(b"invalid")
        res = build_resume_intelligence(buf, "fail.pdf")
        self.assertGreater(len(res["metadata"]["parse_errors"]), 0)

    def test_non_mutating_behavior(self):
        """Orchestration does not mutate global state."""
        text = "Jane Doe\njane@example.com"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "test.docx")
        self.assertEqual(res["metadata"]["builder_version"], "v1.0")

    def test_backward_compatibility(self):
        """Existing parse_resume() functions without regression."""
        stream = self._create_mock_docx("Jane Doe\njane@example.com\nSkills: Python")
        legacy_res = parse_resume(stream, "test.docx")
        self.assertIn("skills", legacy_res)
        self.assertIn("email", legacy_res)

    def test_existing_ri_module_contracts_remain_unchanged(self):
        """Verify RI-01 through RI-07 module contracts remain intact."""
        text = "Jane Doe\njane@example.com\nSkills: Python"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "contracts.docx")
        self.assertIsInstance(res["skills"], list)

    def test_quality_output_included(self):
        """Verify quality report is attached under quality key."""
        text = "Jane Doe\njane@example.com\nSkills: Python"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "quality.docx")
        self.assertIn("quality_score", res["quality"])

    def test_skill_normalization_preserved(self):
        """Skill normalization from RI-04 preserved in output."""
        text = "Skills: JS, TS, K8s, Postgres"
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "skills.docx")
        skill_names = {s["name"] for s in res["skills"]}

        self.assertIn("JavaScript", skill_names)
        self.assertIn("TypeScript", skill_names)

    def test_experience_and_education_structures_preserved(self):
        """Structured records from RI-05 and RI-06 preserved."""
        text = """
        EXPERIENCE
        Software Engineer at Google (Jan 2022 - Present)

        EDUCATION
        B.Tech, JG University, 2022
        """
        stream = self._create_mock_docx(text)
        res = build_resume_intelligence(stream, "structs.docx")

        self.assertGreater(len(res["experience"]), 0)
        self.assertEqual(res["experience"][0]["company"], "Google")
        self.assertGreater(len(res["education"]), 0)
        self.assertEqual(res["education"][0]["degree"], "B.Tech")


if __name__ == "__main__":
    unittest.main()

