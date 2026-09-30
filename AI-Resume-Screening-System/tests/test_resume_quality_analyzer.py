# ============================================================
#  HireAI — Resume Quality & Completeness Analyzer Test Suite (RI-07)
#  22 Comprehensive Enterprise Test Cases
# ============================================================

import unittest
from app.ml.analyzers.resume_quality_analyzer import analyze_resume_quality
from app.ml.ats.ats_checker import compute_ats_score


class TestResumeQualityAnalyzerRI07(unittest.TestCase):
    """RI-07 Resume Quality & Completeness Analyzer Test Suite."""

    def setUp(self):
        self.full_sections = {
            "summary": "Experienced Software Engineer",
            "skills": "Python, React, SQL",
            "experience": "Software Engineer at Google (2022-Present)",
            "education": "B.Tech in Computer Science, 2022",
            "projects": "AI Resume Parser System",
            "certifications": "AWS Certified Developer",
            "languages": "English, Hindi",
            "achievements": "Hackathon Winner 2023"
        }
        self.full_contact = {
            "name": {"value": "Jane Doe"},
            "email": {"value": "jane@example.com"},
            "phone": {"value": "+91 9876543210"},
            "linkedin": {"value": "https://linkedin.com/in/janedoe"},
            "github": {"value": "https://github.com/janedoe"},
            "portfolio": {"value": "https://janedoe.dev"}
        }

    def test_complete_resume(self):
        """Analyze a complete resume with all sections, contact, and metadata."""
        sample = "Jane Doe\njane@example.com\n" + ("Software engineer line with code and experience. " * 30)
        res = analyze_resume_quality(
            text=sample,
            sections=self.full_sections,
            contact=self.full_contact,
            metadata={"word_count": 500, "page_count": 2, "character_count": 3000}
        )

        self.assertEqual(res["quality_score"], 100)
        self.assertEqual(len(res["missing_sections"]), 0)
        self.assertEqual(res["section_coverage"]["percentage"], 100.0)
        self.assertEqual(res["contact_completeness"]["score"], 100)
        self.assertEqual(res["resume_length"]["length_status"], "good")

    def test_missing_sections(self):
        """Identify missing sections correctly."""
        partial_sections = {
            "summary": "Software Developer",
            "skills": "Python",
            "experience": "Google",
            "education": "B.Tech"
        }
        res = analyze_resume_quality(text="Sample resume text", sections=partial_sections)
        self.assertIn("projects", res["missing_sections"])
        self.assertIn("certifications", res["missing_sections"])
        self.assertEqual(res["section_coverage"]["present"], 4)

    def test_all_sections_missing(self):
        """All sections missing evaluates to 0% section coverage."""
        res = analyze_resume_quality(text="Plain text without sections", sections={})
        self.assertEqual(len(res["missing_sections"]), 8)
        self.assertEqual(res["section_coverage"]["percentage"], 0.0)

    def test_complete_contact_information(self):
        """Complete contact info yields 100 completeness score."""
        res = analyze_resume_quality(text="Contact test", contact=self.full_contact)
        self.assertEqual(res["contact_completeness"]["score"], 100)
        self.assertEqual(len(res["contact_completeness"]["missing_fields"]), 0)

    def test_missing_contact_information(self):
        """Missing contact info correctly lists missing fields."""
        partial_contact = {"name": "Jane", "email": "jane@example.com"}
        res = analyze_resume_quality(text="Contact test", contact=partial_contact)
        self.assertIn("phone", res["contact_completeness"]["missing_fields"])
        self.assertIn("linkedin", res["contact_completeness"]["missing_fields"])
        self.assertLess(res["contact_completeness"]["score"], 50)

    def test_partial_contact_information(self):
        """Handle mixed plain strings and entity dict objects in contact."""
        mixed_contact = {
            "name": "Jane Doe",
            "email": {"value": "jane@example.com"},
            "phone": None
        }
        res = analyze_resume_quality(text="Contact test", contact=mixed_contact)
        self.assertEqual(res["contact_completeness"]["missing_fields"].count("phone"), 1)

    def test_word_count(self):
        """Calculate word count accurately."""
        sample = "One two three four five six seven eight nine ten."
        res = analyze_resume_quality(sample)
        self.assertEqual(res["resume_length"]["word_count"], 10)

    def test_page_count_from_metadata(self):
        """Preserve page count from metadata."""
        meta = {"word_count": 400, "page_count": 3, "character_count": 2500}
        res = analyze_resume_quality("Sample text", metadata=meta)
        self.assertEqual(res["resume_length"]["page_count"], 3)

    def test_character_count(self):
        """Calculate character count."""
        sample = "Hello World"
        res = analyze_resume_quality(sample)
        self.assertEqual(res["resume_length"]["character_count"], 11)

    def test_short_resume(self):
        """Categorize short resumes."""
        sample = "Very short resume text."
        res = analyze_resume_quality(sample)
        self.assertEqual(res["resume_length"]["length_status"], "short")

    def test_extremely_long_resume(self):
        """Categorize excessive length resumes."""
        sample = "Word " * 1300
        res = analyze_resume_quality(sample)
        self.assertEqual(res["resume_length"]["length_status"], "excessive")

    def test_readability_calculation(self):
        """Compute readability score and average sentence words."""
        sample = "First sentence is concise. Second sentence is also short and clear."
        res = analyze_resume_quality(sample)
        self.assertGreaterEqual(res["readability"]["score"], 80)
        self.assertGreater(res["readability"]["average_sentence_words"], 0.0)

    def test_long_sentence_detection(self):
        """Detect long sentences exceeding word threshold."""
        long_sent = "Word " * 35 + ". "
        res = analyze_resume_quality(long_sent)
        self.assertEqual(res["readability"]["long_sentence_count"], 1)

    def test_long_line_detection(self):
        """Detect lines exceeding character length threshold."""
        long_line = "A" * 150 + "\nShort line"
        res = analyze_resume_quality(long_line)
        self.assertTrue(res["formatting_indicators"]["long_lines_detected"])

    def test_excessive_whitespace_detection(self):
        """Detect repeated spaces or tabs."""
        sample = "Word     " + " "*10 + "Word"
        res = analyze_resume_quality(sample)
        self.assertTrue(res["formatting_indicators"]["excessive_whitespace"])

    def test_section_coverage(self):
        """Verify present/expected section statistics."""
        sec = {"summary": "Profile", "skills": "Python", "experience": "Engineer"}
        res = analyze_resume_quality("Text", sections=sec)
        self.assertEqual(res["section_coverage"]["present"], 3)
        self.assertEqual(res["section_coverage"]["expected"], 8)
        self.assertEqual(res["section_coverage"]["percentage"], 37.5)

    def test_quality_score_boundaries(self):
        """Quality score stays bounded between 0 and 100."""
        res_empty = analyze_resume_quality("")
        self.assertGreaterEqual(res_empty["quality_score"], 0)
        self.assertLessEqual(res_empty["quality_score"], 100)

        res_full = analyze_resume_quality("Sample " * 100, sections=self.full_sections, contact=self.full_contact)
        self.assertGreaterEqual(res_full["quality_score"], 0)
        self.assertLessEqual(res_full["quality_score"], 100)

    def test_empty_resume(self):
        """Empty text handles cleanly without crash."""
        res = analyze_resume_quality("")
        self.assertEqual(res["quality_score"], 0)
        self.assertEqual(res["resume_length"]["word_count"], 0)

    def test_malformed_none_optional_inputs(self):
        """Handle None for sections, contact, and metadata."""
        res = analyze_resume_quality("Some resume text", sections=None, contact=None, metadata=None)
        self.assertIsNotNone(res["quality_score"])

    def test_deterministic_repeated_execution(self):
        """Repeated invocations yield identical results."""
        sample = "Software Engineer resume text with content."
        res1 = analyze_resume_quality(sample, sections=self.full_sections)
        res2 = analyze_resume_quality(sample, sections=self.full_sections)
        self.assertEqual(res1, res2)

    def test_non_mutating_behavior(self):
        """Analyzer does not mutate passed section or contact dicts."""
        sec_copy = self.full_sections.copy()
        cont_copy = self.full_contact.copy()

        analyze_resume_quality("Test", sections=sec_copy, contact=cont_copy)
        self.assertEqual(sec_copy, self.full_sections)
        self.assertEqual(cont_copy, self.full_contact)

    def test_existing_ats_score_remains_untouched(self):
        """ATS checker operates independently of quality analyzer."""
        sample = "Python, SQL, AWS, B.Tech, Google experience"
        ats_res = compute_ats_score(sample)
        quality_res = analyze_resume_quality(sample)

        self.assertIn("score", ats_res)
        self.assertIn("quality_score", quality_res)
        self.assertNotEqual(ats_res["score"], quality_res["quality_score"])


if __name__ == "__main__":
    unittest.main()

