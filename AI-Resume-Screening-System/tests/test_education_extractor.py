# ============================================================
#  HireAI — Candidate Education Extractor Test Suite (RI-06)
#  20 Comprehensive Enterprise Test Cases
# ============================================================

import unittest
from app.ml.parsers.education_extractor import (
    extract_education,
    extract_certifications,
    _canonicalize_degree,
    _extract_cgpa,
    _extract_percentage
)


class TestCandidateEducationExtractorRI06(unittest.TestCase):
    """RI-06 Candidate Education Intelligence Test Suite."""

    def test_single_degree_extraction(self):
        """Extract a single standard education record."""
        sample = """
        EDUCATION
        B.Tech in Computer Science
        JG University, 2026
        CGPA: 8.3/10
        """
        res = extract_education(sample)
        self.assertEqual(len(res["education"]), 1)
        entry = res["education"][0]

        self.assertEqual(entry["degree"], "B.Tech")
        self.assertIn("JG University", entry["institution"])
        self.assertEqual(entry["passing_year"], "2026")
        self.assertEqual(entry["cgpa"], "8.3")
        self.assertIsNone(entry["percentage"])

    def test_multiple_degrees(self):
        """Extract multiple education entries (MCA, BCA, 12th, 10th)."""
        sample = """
        ACADEMICS
        MCA, Gujarat University, 2026, CGPA: 8.5
        BCA, JG College of Computer Applications, 2024, CGPA: 8.1
        12th, Higher Secondary School, 2021, Percentage: 85%
        10th, Secondary School, 2019, Percentage: 90%
        """
        res = extract_education(sample)
        degrees = [e["degree"] for e in res["education"]]

        self.assertIn("MCA", degrees)
        self.assertIn("BCA", degrees)
        self.assertIn("12th", degrees)
        self.assertIn("10th", degrees)

    def test_degree_canonical_normalization(self):
        """Degree variations normalize to canonical names."""
        self.assertEqual(_canonicalize_degree("b tech"), "B.Tech")
        self.assertEqual(_canonicalize_degree("btech"), "B.Tech")
        self.assertEqual(_canonicalize_degree("bachelor of technology"), "B.Tech")
        self.assertEqual(_canonicalize_degree("mca"), "MCA")

    def test_university_extraction(self):
        """Extract university name using indicator keyword."""
        sample = "B.Tech from Gujarat University"
        res = extract_education(sample)
        self.assertIsNotNone(res["education"][0]["institution"])
        self.assertIn("Gujarat University", res["education"][0]["institution"])

    def test_college_institute_extraction(self):
        """Extract college/institute name."""
        sample = "BCA from ABC Institute of Technology"
        res = extract_education(sample)
        self.assertIsNotNone(res["education"][0]["institution"])
        self.assertIn("ABC Institute of Technology", res["education"][0]["institution"])

    def test_passing_year_extraction(self):
        """Extract passing year integer string."""
        sample = "B.Tech, JG University, Graduated: 2025"
        res = extract_education(sample)
        self.assertEqual(res["education"][0]["passing_year"], "2025")

    def test_cgpa_extraction(self):
        """Extract and normalize CGPA value."""
        sample = "B.Tech | CGPA: 8.3/10"
        res = extract_education(sample)
        self.assertEqual(res["education"][0]["cgpa"], "8.3")

    def test_percentage_extraction(self):
        """Extract and normalize percentage value."""
        sample = "12th Standard - Score: 85.5%"
        res = extract_education(sample)
        self.assertEqual(res["education"][0]["percentage"], "85.5%")

    def test_cgpa_vs_percentage_distinction(self):
        """Ensure CGPA is not confused with percentage or year values."""
        sample = "B.Tech, 2024, CGPA: 8.3, Percentage: 85%"
        res = extract_education(sample)
        self.assertEqual(res["education"][0]["cgpa"], "8.3")
        self.assertEqual(res["education"][0]["percentage"], "85%")
        self.assertEqual(res["education"][0]["passing_year"], "2024")

    def test_certification_extraction(self):
        """Extract explicit certification titles."""
        sample = """
        CERTIFICATIONS
        AWS Certified Cloud Practitioner
        Google Data Analytics Professional Certificate
        """
        res = extract_education(sample)
        self.assertEqual(len(res["certifications"]), 2)
        self.assertIn("AWS Certified Cloud Practitioner", res["certifications"])

    def test_multiple_certifications(self):
        """Extract multiple certifications cleanly."""
        sample = """
        Microsoft Azure Fundamentals
        Python for Beginners — NIELIT
        """
        certs = extract_certifications(sample)
        self.assertEqual(len(certs), 2)

    def test_ongoing_pursuing_education(self):
        """Passing year is None if degree is currently ongoing/pursuing."""
        sample = "B.Tech in Computer Science, JG University (Ongoing)"
        res = extract_education(sample)
        self.assertIsNone(res["education"][0]["passing_year"])

    def test_missing_institution_returns_none(self):
        """Missing institution safely returns None without hallucinating."""
        sample = "B.Tech, 2024, CGPA: 8.3"
        res = extract_education(sample)
        self.assertIsNone(res["education"][0]["institution"])

    def test_missing_year_returns_none(self):
        """Missing passing year returns None."""
        sample = "B.Tech, JG University"
        res = extract_education(sample)
        self.assertIsNone(res["education"][0]["passing_year"])

    def test_missing_cgpa_returns_none(self):
        """Missing CGPA returns None."""
        sample = "B.Tech, JG University, 2024"
        res = extract_education(sample)
        self.assertIsNone(res["education"][0]["cgpa"])

    def test_missing_percentage_returns_none(self):
        """Missing percentage returns None."""
        sample = "B.Tech, JG University, 2024, CGPA: 8.3"
        res = extract_education(sample)
        self.assertIsNone(res["education"][0]["percentage"])

    def test_empty_education_section(self):
        """Empty text returns empty lists."""
        res = extract_education("")
        self.assertEqual(res["education"], [])
        self.assertEqual(res["certifications"], [])

    def test_malformed_education_text(self):
        """Malformed text handles gracefully without crashing."""
        sample = ":::!!! B.Tech ??? JG University ### 8.3 CGPA $$$"
        res = extract_education(sample)
        self.assertEqual(res["education"][0]["degree"], "B.Tech")

    def test_unicode_institution_names(self):
        """Handle institution names containing Unicode characters."""
        sample = "B.Sc from Université de Montréal, 2022"
        res = extract_education(sample)
        self.assertIsNotNone(res["education"][0]["institution"])

    def test_deterministic_output(self):
        """Repeated invocations with identical text yield identical structured outputs."""
        sample = "B.Tech, JG University, 2026, CGPA: 8.3"
        res1 = extract_education(sample)
        res2 = extract_education(sample)
        self.assertEqual(res1, res2)


if __name__ == "__main__":
    unittest.main()
