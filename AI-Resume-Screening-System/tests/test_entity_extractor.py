# ============================================================
#  HireAI — Candidate Entity Extractor Test Suite (RI-03)
#  17 Comprehensive Enterprise Test Cases
# ============================================================

import unittest
from app.ml.parsers.entity_extractor import (
    extract_candidate_entities,
    extract_name,
    extract_email,
    extract_phone,
    extract_linkedin,
    extract_github,
    extract_portfolio,
    extract_address,
    extract_city,
    extract_country,
)


class TestCandidateEntityExtractorRI03(unittest.TestCase):
    """RI-03 Candidate Entity Extraction Test Suite."""

    def test_normal_candidate_extraction(self):
        """Extract all basic entities from a standard resume header."""
        sample = """
        John Doe
        john.doe@example.com | +91 9876543210
        https://www.linkedin.com/in/johndoe
        https://github.com/johndoe
        https://johndoe.dev

        SUMMARY
        Experienced software engineer.
        """
        res = extract_candidate_entities(sample)

        self.assertEqual(res["name"]["value"], "John Doe")
        self.assertEqual(res["name"]["confidence"], 0.95)

        self.assertEqual(res["email"]["value"], "john.doe@example.com")
        self.assertEqual(res["email"]["confidence"], 1.0)

        self.assertEqual(res["phone"]["value"], "+91 98765 43210")
        self.assertEqual(res["phone"]["confidence"], 0.95)

        self.assertEqual(res["linkedin"]["value"], "https://www.linkedin.com/in/johndoe")
        self.assertEqual(res["github"]["value"], "https://github.com/johndoe")
        self.assertEqual(res["portfolio"]["value"], "https://johndoe.dev")

    def test_missing_entities_return_none(self):
        """Resume with missing fields should return value=None, confidence=0.0."""
        sample = "Python developer with no contact info."
        res = extract_candidate_entities(sample)

        self.assertIsNone(res["email"]["value"])
        self.assertEqual(res["email"]["confidence"], 0.0)

        self.assertIsNone(res["phone"]["value"])
        self.assertEqual(res["phone"]["confidence"], 0.0)

        self.assertIsNone(res["linkedin"]["value"])
        self.assertIsNone(res["github"]["value"])
        self.assertIsNone(res["portfolio"]["value"])
        self.assertIsNone(res["address"]["value"])
        self.assertIsNone(res["city"]["value"])
        self.assertIsNone(res["country"]["value"])

    def test_unicode_candidate_name(self):
        """Support names with accents and international Unicode characters."""
        sample = """
        Jörgen Sjöberg
        jorgen@example.com
        """
        res = extract_name(sample)
        self.assertEqual(res["value"], "Jörgen Sjöberg")
        self.assertEqual(res["confidence"], 0.95)

    def test_name_heading_rejection(self):
        """Header lines matching resume section headers must NOT be inferred as candidate name."""
        sample = """
        CURRICULUM VITAE
        RESUME
        SOFTWARE ENGINEER
        Aarav Sharma
        aarav@example.com
        """
        res = extract_name(sample)
        self.assertEqual(res["value"], "Aarav Sharma")
        self.assertEqual(res["source"], "header_line")

    def test_indian_phone_number_formats(self):
        """Support Indian +91 phone numbers with spacing or hyphens."""
        sample1 = "Contact: +91-9876543210"
        res1 = extract_phone(sample1)
        self.assertEqual(res1["value"], "+91 98765 43210")
        self.assertEqual(res1["confidence"], 0.95)

        sample2 = "Call 9876543210 for details"
        res2 = extract_phone(sample2)
        self.assertEqual(res2["value"], "+91 98765 43210")

    def test_international_phone_number_formats(self):
        """Support international non-Indian phone formats."""
        sample = "Phone: +1 (555) 234-5678"
        res = extract_phone(sample)
        self.assertIn("+1", res["value"])
        self.assertEqual(res["confidence"], 0.90)

    def test_false_positive_phone_date_years_rejected(self):
        """Year ranges like 2018-2022 must NOT be misclassified as phone numbers."""
        sample = "Software Engineer 2018-2022 at Acme Corp"
        res = extract_phone(sample)
        self.assertIsNone(res["value"])

    def test_false_positive_phone_cgpa_rejected(self):
        """CGPA values like 9.5 or 3.8 must NOT be misclassified as phone numbers."""
        sample = "GPA: 3.8 / 4.0 | CGPA 9.5"
        res = extract_phone(sample)
        self.assertIsNone(res["value"])

    def test_linkedin_url_extraction_and_filtering(self):
        """Extract profile URL while ignoring /jobs or /company URLs."""
        sample = """
        Profile: https://www.linkedin.com/in/alice-smith
        Jobs: https://www.linkedin.com/jobs/view/12345
        """
        res = extract_linkedin(sample)
        self.assertEqual(res["value"], "https://www.linkedin.com/in/alice-smith")
        self.assertEqual(res["confidence"], 1.0)

    def test_github_url_extraction(self):
        """Extract GitHub user profile URL."""
        sample = "GitHub: github.com/bob-developer"
        res = extract_github(sample)
        self.assertEqual(res["value"], "https://github.com/bob-developer")
        self.assertEqual(res["confidence"], 1.0)

    def test_portfolio_distinction_from_social_and_email(self):
        """Portfolio URL must exclude LinkedIn, GitHub, and email provider domains."""
        sample = """
        Contact: user@gmail.com
        LinkedIn: https://linkedin.com/in/user
        Portfolio: https://alexdev.io
        """
        res = extract_portfolio(sample)
        self.assertEqual(res["value"], "https://alexdev.io")
        self.assertEqual(res["confidence"], 0.85)

    def test_multiple_email_addresses_header_prioritized(self):
        """If multiple emails exist, prioritize the one in top header."""
        sample = """
        Header Email: primary@candidate.com
        
        EXPERIENCE
        Contact team at work@company.com for inquiries.
        """
        res = extract_email(sample)
        self.assertEqual(res["value"], "primary@candidate.com")
        self.assertEqual(res["source"], "header_regex")

    def test_city_extraction(self):
        """Extract candidate city from header or text."""
        sample = """
        Jane Doe
        Bangalore, India
        jane@example.com
        """
        res = extract_city(sample)
        self.assertEqual(res["value"], "Bangalore")
        self.assertIn(res["source"], ("header_city_lookup", "body_city_lookup"))

    def test_country_extraction(self):
        """Extract candidate country from header or text."""
        sample = "Located in San Francisco, United States"
        res = extract_country(sample)
        self.assertEqual(res["value"], "United States")
        self.assertEqual(res["confidence"], 0.90)

    def test_address_pattern_extraction(self):
        """Extract street address pattern when present."""
        sample = """
        John Smith
        123 Tech Park Road, Suite 400
        john@example.com
        """
        res = extract_address(sample)
        self.assertIsNotNone(res["value"])
        self.assertIn("Road", res["value"])

    def test_malformed_input_handling(self):
        """None or empty string input must handle gracefully without exception."""
        res = extract_candidate_entities("")
        self.assertIsNone(res["name"]["value"])
        self.assertIsNone(res["email"]["value"])
        self.assertEqual(res["email"]["confidence"], 0.0)

    def test_deterministic_repeated_extraction(self):
        """Repeated calls with same input produce identical output."""
        sample = "Jane Doe\njane@example.com\n+91 9876543210"
        res1 = extract_candidate_entities(sample)
        res2 = extract_candidate_entities(sample)
        self.assertEqual(res1, res2)


if __name__ == "__main__":
    unittest.main()
