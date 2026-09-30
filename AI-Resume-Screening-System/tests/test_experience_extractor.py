# ============================================================
#  HireAI — Candidate Experience Extractor Test Suite (RI-05)
#  20 Comprehensive Enterprise Test Cases
# ============================================================

import unittest
from app.ml.parsers.experience_extractor import (
    extract_experience,
    _calculate_total_experience,
    _parse_month_year
)
from datetime import datetime


class TestCandidateExperienceExtractorRI05(unittest.TestCase):
    """RI-05 Candidate Experience Intelligence Test Suite."""

    def test_single_work_experience(self):
        """Extract a single standard work experience record."""
        sample = """
        EXPERIENCE
        Software Engineer at Google
        Jan 2022 - Dec 2023
        Built scalable microservices in Python.
        """
        res = extract_experience(sample)
        self.assertEqual(len(res["entries"]), 1)
        entry = res["entries"][0]

        self.assertEqual(entry["company"], "Google")
        self.assertEqual(entry["job_title"], "Software Engineer")
        self.assertIn("Jan 2022", entry["duration"])
        self.assertFalse(entry["is_current_role"])
        self.assertFalse(entry["is_internship"])
        self.assertEqual(res["total_experience_years"], 1.9)

    def test_multiple_work_experiences(self):
        """Extract multiple work experiences."""
        sample = """
        WORK HISTORY
        Senior Software Engineer at Microsoft (Jan 2023 - Present)
        Python Developer at TCS (Jan 2021 - Dec 2022)
        """
        res = extract_experience(sample)
        self.assertEqual(len(res["entries"]), 2)
        self.assertEqual(res["entries"][0]["company"], "Microsoft")
        self.assertEqual(res["entries"][1]["company"], "Tcs")

    def test_company_extraction(self):
        """Identify company name using indicator suffixes or known companies."""
        sample = "Software Developer at Acme Technologies"
        res = extract_experience(sample)
        self.assertEqual(res["entries"][0]["company"], "Acme Technologies")

    def test_job_title_extraction(self):
        """Extract job title from common title dictionary or at/@ pattern."""
        sample = "Data Scientist at Infosys"
        res = extract_experience(sample)
        self.assertEqual(res["entries"][0]["job_title"], "Data Scientist")

    def test_date_range_extraction(self):
        """Extract month-year date ranges."""
        sample = "Software Engineer at Wipro (Jun 2020 - May 2022)"
        res = extract_experience(sample)
        self.assertIsNotNone(res["entries"][0]["duration"])
        self.assertIn("Jun 2020", res["entries"][0]["duration"])

    def test_current_role_detection(self):
        """Mark is_current_role=True if date range ends with Present."""
        sample = "Full Stack Developer at Amazon (Jan 2023 - Present)"
        res = extract_experience(sample)
        self.assertTrue(res["entries"][0]["is_current_role"])

    def test_internship_detection(self):
        """Mark is_internship=True if title/line contains intern keywords."""
        sample = "Machine Learning Intern at Meta (Jun 2023 - Aug 2023)"
        res = extract_experience(sample)
        self.assertTrue(res["entries"][0]["is_internship"])
        self.assertEqual(res["entries"][0]["job_title"], "Machine Learning Intern")

    def test_total_experience_calculation(self):
        """Calculate total experience in years accurately."""
        sample = "Software Engineer at Google (Jan 2020 - Dec 2022)"
        res = extract_experience(sample)
        self.assertEqual(res["total_experience_years"], 2.9)

    def test_multiple_date_formats(self):
        """Support standalone year ranges (2021 - 2023)."""
        sample = "Backend Developer at IBM (2021 - 2023)"
        res = extract_experience(sample)
        self.assertIsNotNone(res["entries"][0]["duration"])
        self.assertEqual(res["total_experience_years"], 2.0)

    def test_present_current_role_handling(self):
        """Handle 'Till Present' keyword for current employment."""
        sample = "Python Developer at Apple (2022 - Till Present)"
        res = extract_experience(sample)
        self.assertTrue(res["entries"][0]["is_current_role"])

    def test_missing_company_returns_none(self):
        """If company name cannot be identified, company is None."""
        sample = "Software Engineer (Jan 2023 - Dec 2023)"
        res = extract_experience(sample)
        self.assertIsNone(res["entries"][0]["company"])

    def test_missing_job_title_returns_none(self):
        """If job title cannot be identified, job_title is None."""
        sample = "Worked at Acme Corp (Jan 2023 - Dec 2023)"
        res = extract_experience(sample)
        self.assertIsNone(res["entries"][0]["job_title"])

    def test_missing_dates_returns_none(self):
        """If duration cannot be identified, duration is None."""
        sample = "Python Developer at Netflix"
        res = extract_experience(sample)
        self.assertIsNone(res["entries"][0]["duration"])
        self.assertFalse(res["entries"][0]["is_current_role"])

    def test_invalid_date_range_handling(self):
        """Invalid or reversed date ranges handled gracefully without crash."""
        intervals = [(datetime(2025, 1, 1), datetime(2020, 1, 1))]
        total = _calculate_total_experience(intervals)
        self.assertEqual(total, 0.0)

    def test_overlapping_employment_periods(self):
        """Overlapping employment periods are merged to prevent double-counting."""
        intervals = [
            (datetime(2020, 1, 1), datetime(2022, 1, 1)), # 2 years
            (datetime(2021, 1, 1), datetime(2023, 1, 1)), # 2 years (1 year overlap)
        ]
        total = _calculate_total_experience(intervals)
        # Total duration from Jan 2020 to Jan 2023 = 3 years
        self.assertEqual(total, 3.0)

    def test_empty_experience_section(self):
        """Empty text returns empty entries list and 0.0 total experience."""
        res = extract_experience("")
        self.assertEqual(res["entries"], [])
        self.assertEqual(res["total_experience_years"], 0.0)

    def test_deterministic_output(self):
        """Repeated calls with identical text return identical structured outputs."""
        sample = "Software Engineer at Google (Jan 2021 - Dec 2022)"
        res1 = extract_experience(sample)
        res2 = extract_experience(sample)
        self.assertEqual(res1, res2)

    def test_unicode_company_and_title(self):
        """Handle company/title strings with Unicode characters."""
        sample = "Software Developer at Café Tech Ltd (2022 - 2023)"
        res = extract_experience(sample)
        self.assertEqual(res["entries"][0]["company"], "Café Tech Ltd")

    def test_internship_and_normal_employment_together(self):
        """Differentiate internship and full-time employment entries in same text."""
        sample = """
        Software Engineering Intern at Google (Jun 2021 - Aug 2021)
        Software Engineer at Google (Jan 2022 - Present)
        """
        res = extract_experience(sample)
        self.assertEqual(len(res["entries"]), 2)
        self.assertTrue(res["entries"][0]["is_internship"])
        self.assertFalse(res["entries"][1]["is_internship"])
        self.assertTrue(res["entries"][1]["is_current_role"])

    def test_regression_with_section_dict(self):
        """Accept RI-02 section dictionary input format cleanly."""
        section_dict = {"experience": "Python Developer at TCS (2021 - 2023)"}
        res = extract_experience("", section_dict=section_dict)
        self.assertEqual(res["entries"][0]["company"], "Tcs")
        self.assertEqual(res["entries"][0]["job_title"], "Python Developer")


if __name__ == "__main__":
    unittest.main()
