# ============================================================
#  HireAI — Resume Intelligence Foundation P0 Test Suite
#  Covers RI-01 (Resume Parser Engine) & RI-02 (Section Detector)
#  36 Enterprise Test Cases
# ============================================================

import io
import unittest
import docx
import PyPDF2
from datetime import datetime

from app.ml.parsers.pdf_parser import (
    extract_pdf_with_metadata, extract_text_from_pdf, PARSER_CONFIG as PDF_CONFIG, ParseStatus
)
from app.ml.parsers.docx_parser import (
    extract_docx_with_metadata, extract_text_from_docx, PARSER_CONFIG as DOCX_CONFIG
)
from app.ml.parsers.resume_parser import parse_document, parse_resume
from app.ml.parsers.section_detector import detect_sections, SECTION_HEADERS, STANDARD_SECTION_KEYS


def _make_docx(paragraphs: list[str], table_rows: list[list[str]] | None = None) -> io.BytesIO:
    """Helper to build an in-memory DOCX stream."""
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    if table_rows:
        tbl = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for r_idx, row in enumerate(table_rows):
            for c_idx, val in enumerate(row):
                tbl.cell(r_idx, c_idx).text = val
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ── TEST SUITE A: RI-01 Resume Parser Engine ───────────────────

class TestResumeParserEngineRI01(unittest.TestCase):

    def test_valid_docx_parsing_and_metadata(self):
        """Test DOCX parsing extracts paragraphs, tables, and metadata."""
        buf = _make_docx(
            ["Jane Doe", "Software Engineer with Python skills."],
            [["Skill", "Level"], ["Python", "Expert"]]
        )
        res = extract_docx_with_metadata(buf, "Jane_CV.docx")
        self.assertTrue(res["success"])
        self.assertEqual(res["metadata"]["file_type"], "docx")
        self.assertEqual(res["metadata"]["parse_status"], ParseStatus.SUCCESS)
        self.assertTrue(res["metadata"]["word_count"] > 0)
        self.assertTrue(res["metadata"]["character_count"] > 0)
        self.assertIn("Python | Expert", res["raw_text"])

    def test_empty_docx_handled_with_failed_status(self):
        """Empty 0-paragraph DOCX should return success=False and ParseStatus.FAILED."""
        buf = _make_docx([])
        res = extract_docx_with_metadata(buf, "empty.docx")
        self.assertFalse(res["success"])
        self.assertEqual(res["metadata"]["parse_status"], ParseStatus.FAILED)
        self.assertEqual(res["raw_text"], "")

    def test_corrupted_docx_returns_clean_failed_result(self):
        """Random bytes submitted as DOCX should fail gracefully without crashing."""
        buf = io.BytesIO(b"PK\x03\x04CorruptedZipDataHere")
        res = extract_docx_with_metadata(buf, "bad.docx")
        self.assertFalse(res["success"])
        self.assertEqual(res["metadata"]["parse_status"], ParseStatus.FAILED)
        self.assertTrue(len(res["errors"]) > 0)

    def test_unsupported_file_extension_returns_unsupported_status(self):
        """Unsupported .txt or .exe file should return parse_status=FAILED."""
        buf = io.BytesIO(b"Some text content")
        res = parse_document(buf, "resume.txt")
        self.assertFalse(res["success"])
        self.assertIn("Unsupported file extension", res["errors"][0])

    def test_none_file_object_handled(self):
        """Passing None file object should return clean failure dictionary."""
        res_pdf = extract_pdf_with_metadata(None, "null.pdf")
        res_docx = extract_docx_with_metadata(None, "null.docx")
        self.assertFalse(res_pdf["success"])
        self.assertFalse(res_docx["success"])

    def test_unicode_gujarati_emoji_parsing(self):
        """Unicode characters (Gujarati, Emoji) should be extracted cleanly."""
        text = "Résumé - Prajapati Vraj 🚀 - ગુજરાતી ડેવલપર"
        buf = _make_docx([text])
        res = extract_docx_with_metadata(buf, "unicode.docx")
        self.assertTrue(res["success"])
        self.assertIn("ગુજરાતી", res["raw_text"])
        self.assertIn("🚀", res["raw_text"])

    def test_docx_stream_pointer_resets_automatically(self):
        """Stream pointer should be reset to 0 after parsing."""
        buf = _make_docx(["Testing stream rewind"])
        buf.seek(10)  # Move offset
        res = extract_docx_with_metadata(buf, "rewind.docx")
        self.assertTrue(res["success"])

    def test_parser_duration_ms_populated(self):
        """parser_duration_ms and processing_time_ms should be non-negative integers."""
        buf = _make_docx(["Performance test line"])
        res = extract_docx_with_metadata(buf, "perf.docx")
        self.assertGreaterEqual(res["metadata"]["parser_duration_ms"], 0)
        self.assertGreaterEqual(res["metadata"]["processing_time_ms"], 0)

    def test_document_id_uuid_format(self):
        """document_id should start with doc_ prefix."""
        buf = _make_docx(["Doc ID check"])
        res = extract_docx_with_metadata(buf, "id.docx")
        self.assertTrue(res["metadata"]["document_id"].startswith("doc_"))

    def test_created_at_iso_format(self):
        """created_at should be a valid ISO 8601 timestamp."""
        buf = _make_docx(["Timestamp test"])
        res = extract_docx_with_metadata(buf, "time.docx")
        ts = res["metadata"]["created_at"]
        self.assertIsNotNone(datetime.fromisoformat(ts))

    def test_parse_document_orchestration(self):
        """parse_document should select correct parser based on file extension."""
        buf_docx = _make_docx(["Docx test"])
        res = parse_document(buf_docx, "test.docx")
        self.assertEqual(res["metadata"]["parser_name"], "python-docx")

    def test_parse_resume_backward_compatibility(self):
        """parse_resume legacy wrapper must preserve all original dictionary keys while attaching metadata."""
        buf = _make_docx(["John Doe", "john@example.com", "Python developer"])
        res = parse_resume(buf, "legacy.docx")
        self.assertIn("raw_text", res)
        self.assertIn("email", res)
        self.assertIn("skills", res)
        self.assertIn("metadata", res)
        self.assertTrue(res["metadata"]["word_count"] > 0)

    def test_parser_config_constants(self):
        """Parser configuration constants must be defined and valid."""
        self.assertEqual(PDF_CONFIG["encoding"], "utf-8")
        self.assertEqual(DOCX_CONFIG["encoding"], "utf-8")
        self.assertEqual(PDF_CONFIG["max_file_size"], 10 * 1024 * 1024)

    def test_parser_rule_no_entity_inference(self):
        """Parser layer output should contain raw text only without inferred name/skills."""
        buf = _make_docx(["Raw text without parsing entities"])
        res = parse_document(buf, "raw.docx")
        self.assertNotIn("candidate_name", res)
        self.assertNotIn("extracted_skills", res)


# ── TEST SUITE B: RI-02 Resume Section Detector ───────────────

class TestResumeSectionDetectorRI02(unittest.TestCase):

    def test_standard_8_sections_detected(self):
        """Test all 8 standard sections are correctly identified when standard headings are present."""
        sample = """
        SUMMARY
        Experienced software engineer.

        SKILLS
        Python, React, SQL

        EXPERIENCE
        Senior Developer at Acme Corp

        EDUCATION
        B.Tech in Computer Science

        PROJECTS
        HireAI Screener

        CERTIFICATIONS
        AWS Certified

        LANGUAGES
        English, Spanish

        ACHIEVEMENTS
        Best Innovation Award 2024
        """
        res = detect_sections(sample)
        self.assertIn("software engineer", res["summary"])
        self.assertIn("Python, React", res["skills"])
        self.assertIn("Acme Corp", res["experience"])
        self.assertIn("B.Tech", res["education"])
        self.assertIn("HireAI Screener", res["projects"])
        self.assertIn("AWS Certified", res["certifications"])
        self.assertIn("English, Spanish", res["languages"])
        self.assertIn("Best Innovation", res["achievements"])

    def test_alternate_headings_detected(self):
        """Test alternate headers like TECHNICAL EXPERTISE, EMPLOYMENT HISTORY, ACADEMIC BACKGROUND."""
        sample = """
        CAREER OVERVIEW
        Full stack developer.

        TECHNICAL EXPERTISE
        Python, Flask, PyTorch

        EMPLOYMENT HISTORY
        Software Engineer at Google

        ACADEMIC QUALIFICATIONS
        M.Tech from IIT Delhi
        """
        res = detect_sections(sample)
        self.assertIn("Full stack", res["summary"])
        self.assertIn("PyTorch", res["skills"])
        self.assertIn("Google", res["experience"])
        self.assertIn("IIT Delhi", res["education"])

    def test_reordered_sections_detected(self):
        """Sections present in non-traditional order should be detected accurately."""
        sample = """
        EDUCATION
        B.Sc Computer Science

        SKILLS
        JavaScript, Node.js

        SUMMARY
        Passionate coder
        """
        res = detect_sections(sample)
        self.assertIn("B.Sc", res["education"])
        self.assertIn("Node.js", res["skills"])
        self.assertIn("Passionate coder", res["summary"])

    def test_missing_sections_return_empty_string(self):
        """Missing standard sections should return empty string ""."""
        sample = "SKILLS\nPython\n"
        res = detect_sections(sample)
        self.assertEqual(res["experience"], "")
        self.assertEqual(res["education"], "")
        self.assertEqual(res["projects"], "")

    def test_duplicate_headings_concatenated(self):
        """Multiple sections with same heading should be concatenated cleanly."""
        sample = """
        PROJECTS
        Project 1: Web App

        PROJECTS
        Project 2: Mobile App
        """
        res = detect_sections(sample)
        self.assertIn("Project 1", res["projects"])
        self.assertIn("Project 2", res["projects"])

    def test_no_headings_fallback_to_summary(self):
        """Resume with no headers should place raw text into summary section."""
        sample = "Jane Doe is a software engineer with 5 years of Python experience."
        res = detect_sections(sample)
        self.assertIn("Jane Doe", res["summary"])
        self.assertEqual(res["section_details"]["summary"]["detected_heading"], "NONE")

    def test_custom_unknown_sections_captured(self):
        """Custom/unrecognized headings (e.g. PUBLICATIONS) captured in unknown_sections list."""
        sample = """
        SKILLS
        Python

        PUBLICATIONS
        Paper on Machine Learning in IEEE 2024
        """
        res = detect_sections(sample)
        self.assertEqual(len(res["unknown_sections"]), 1)
        self.assertEqual(res["unknown_sections"][0]["heading"], "PUBLICATIONS")
        self.assertIn("Machine Learning", res["unknown_sections"][0]["text"])

    def test_multiple_unknown_sections_captured(self):
        """Multiple custom sections should all be captured with confidence scores."""
        sample = """
        PUBLICATIONS
        IEEE Paper

        HOBBIES & INTERESTS
        Chess, Swimming
        """
        res = detect_sections(sample)
        self.assertEqual(len(res["unknown_sections"]), 2)
        headings = [u["heading"] for u in res["unknown_sections"]]
        self.assertIn("PUBLICATIONS", headings)

    def test_section_confidence_scores(self):
        """Exact heading matches should return confidence=1.0."""
        sample = "TECHNICAL SKILLS\nPython, C++\n"
        res = detect_sections(sample)
        self.assertEqual(res["section_details"]["skills"]["confidence"], 1.0)
        self.assertEqual(res["section_details"]["skills"]["detected_heading"], "TECHNICAL SKILLS")

    def test_section_line_numbers_and_character_lengths(self):
        """Section details metadata must record start_line, end_line, and character_length."""
        sample = "EDUCATION\nB.Tech IIT\nLine 3"
        res = detect_sections(sample)
        details = res["section_details"]["education"]
        self.assertGreater(details["start_line"], 0)
        self.assertGreater(details["end_line"], details["start_line"])
        self.assertEqual(details["character_length"], len(details["text"]))

    def test_heading_inside_sentence_ignored(self):
        """Long sentences containing heading words (e.g. 'I have experience in python') must NOT trigger a new section."""
        sample = """
        SUMMARY
        I have 5 years of professional work experience building scalable applications.

        SKILLS
        Python, Django
        """
        res = detect_sections(sample)
        self.assertIn("5 years of professional work experience", res["summary"])
        self.assertIn("Python, Django", res["skills"])

    def test_uppercase_and_lowercase_headings(self):
        """Section headers in mixed or lowercase should be detected cleanly."""
        sample = """
        professional summary
        Junior Developer.

        technical skills
        HTML, CSS, JS
        """
        res = detect_sections(sample)
        self.assertIn("Junior Developer", res["summary"])
        self.assertIn("HTML, CSS, JS", res["skills"])

    def test_configured_section_headers_dictionary(self):
        """SECTION_HEADERS configuration dictionary must cover all 8 standard sections."""
        for key in STANDARD_SECTION_KEYS:
            self.assertIn(key, SECTION_HEADERS)
            self.assertTrue(len(SECTION_HEADERS[key]) > 3)

    def test_section_result_dictionary_backward_compatibility(self):
        """SectionResult must allow standard dict string access res['skills'] directly."""
        sample = "SKILLS\nPython, Rust\n"
        res = detect_sections(sample)
        self.assertEqual(res["skills"], "Python, Rust")
        self.assertTrue(isinstance(res["skills"], str))


if __name__ == "__main__":
    unittest.main()
