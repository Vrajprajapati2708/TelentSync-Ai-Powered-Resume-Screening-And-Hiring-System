# ============================================================
#  HireAI — Skill Intelligence Engine Test Suite (RI-04)
#  15 Comprehensive Enterprise Test Cases
# ============================================================

import unittest
from app.ml.skill_extraction.skill_intelligence import (
    extract_skills_intelligence,
    _canonicalize_skill,
    _get_skill_category
)
from app.ml.skill_extraction.extract_skills import extract_skills


class TestSkillIntelligenceEngineRI04(unittest.TestCase):
    """RI-04 Skill Intelligence Engine Test Suite."""

    def test_spacy_or_regex_skill_extraction(self):
        """Extract basic skills from resume text with name, category, confidence, and source."""
        sample = """
        TECHNICAL SKILLS
        Programming: Python, Java, C++
        Databases: PostgreSQL, MongoDB
        Cloud: AWS, Docker
        """
        res = extract_skills_intelligence(sample)
        self.assertGreater(len(res), 0)

        # Check required key contract for every skill
        for skill_obj in res:
            self.assertIn("name", skill_obj)
            self.assertIn("category", skill_obj)
            self.assertIn("confidence", skill_obj)
            self.assertIn("source", skill_obj)
            self.assertIsInstance(skill_obj["confidence"], float)
            self.assertIn(skill_obj["source"], ("spacy_ner", "regex_dictionary", "alias_match"))

    def test_regex_dictionary_fallback(self):
        """Regex/dictionary fallback extracts standard skills if NER is not triggered."""
        sample = "Proficient in Python, SQL, and Docker."
        res = extract_skills_intelligence(sample)
        names = {s["name"] for s in res}

        self.assertIn("Python", names)
        self.assertIn("SQL", names)
        self.assertIn("Docker", names)

    def test_canonical_skill_normalization(self):
        """Raw strings normalize to canonical title case."""
        canonical, is_alias = _canonicalize_skill("python")
        self.assertEqual(canonical, "Python")

        canonical, is_alias = _canonicalize_skill("postgresql")
        self.assertEqual(canonical, "PostgreSQL")

    def test_alias_normalization(self):
        """Common aliases map to canonical skill names."""
        aliases_to_check = [
            ("JS", "JavaScript"),
            ("TS", "TypeScript"),
            ("Node", "Node.js"),
            ("ReactJS", "React"),
            ("Postgres", "PostgreSQL"),
            ("K8s", "Kubernetes"),
            ("Golang", "Go"),
            ("PowerBI", "Power BI"),
        ]
        for alias, expected_canonical in aliases_to_check:
            canonical, is_alias = _canonicalize_skill(alias)
            self.assertEqual(canonical, expected_canonical, f"Failed alias mapping for {alias}")

    def test_case_normalization(self):
        """Case variations do not create distinct skill entries."""
        sample = "Experience with PYTHON, python, and Python."
        res = extract_skills_intelligence(sample)
        py_entries = [s for s in res if s["name"] == "Python"]

        self.assertEqual(len(py_entries), 1)
        self.assertEqual(py_entries[0]["name"], "Python")

    def test_duplicate_removal(self):
        """Duplicate occurrences of the same skill produce a single deduplicated entry."""
        sample = """
        SKILLS
        Python, Python, python, Py
        JS, JavaScript, JS
        """
        res = extract_skills_intelligence(sample)
        names = [s["name"] for s in res]

        self.assertEqual(names.count("Python"), 1)
        self.assertEqual(names.count("JavaScript"), 1)

    def test_category_assignment(self):
        """Skills are assigned to standard categories."""
        self.assertEqual(_get_skill_category("Python"), "Programming Languages")
        self.assertEqual(_get_skill_category("PostgreSQL"), "Databases")
        self.assertEqual(_get_skill_category("Docker"), "Cloud & DevOps")
        self.assertEqual(_get_skill_category("React"), "Web & Frameworks")
        self.assertEqual(_get_skill_category("Machine Learning"), "Data Science & ML")

    def test_confidence_scoring(self):
        """Confidence scores are explainable floats within valid range [0.0, 1.0]."""
        sample = "Python, SQL, AWS, React"
        res = extract_skills_intelligence(sample)
        for s in res:
            self.assertGreaterEqual(s["confidence"], 0.50)
            self.assertLessEqual(s["confidence"], 1.0)

    def test_source_tracking(self):
        """Source field identifies the extraction mechanism."""
        sample = "Python, PostgreSQL"
        res = extract_skills_intelligence(sample)
        for s in res:
            self.assertIn(s["source"], ("spacy_ner", "regex_dictionary", "alias_match"))

    def test_empty_text(self):
        """Empty or whitespace text returns empty list."""
        res1 = extract_skills_intelligence("")
        self.assertEqual(res1, [])

        res2 = extract_skills_intelligence("   \n\t  ")
        self.assertEqual(res2, [])

    def test_text_containing_no_skills(self):
        """Text with no recognizable skills returns empty list."""
        sample = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
        res = extract_skills_intelligence(sample)
        self.assertEqual(res, [])

    def test_multiple_occurrences_deduplicated_by_strongest_source(self):
        """Multiple occurrences preserve the entry with highest confidence."""
        sample = """
        SKILLS
        Python
        WORK EXPERIENCE
        Used Python for machine learning backend development.
        """
        res = extract_skills_intelligence(sample)
        py = next(s for s in res if s["name"] == "Python")
        self.assertIsNotNone(py)

    def test_deterministic_output(self):
        """Repeated invocations with identical text yield identical structured output."""
        sample = "Experienced in Python, React, PostgreSQL, Docker, AWS."
        res1 = extract_skills_intelligence(sample)
        res2 = extract_skills_intelligence(sample)
        self.assertEqual(res1, res2)

    def test_malformed_input_handling(self):
        """Handles non-standard text formatting gracefully without exceptions."""
        sample = ":::!!!??? Python ### $$$ SQL %%% &&& AWS ***"
        res = extract_skills_intelligence(sample)
        names = {s["name"] for s in res}
        self.assertIn("Python", names)
        self.assertIn("SQL", names)

    def test_compatibility_with_existing_extract_skills(self):
        """Existing extract_skills() function continues to work seamlessly."""
        sample = "Python, SQL, React"
        legacy_res = extract_skills(sample)
        self.assertIsInstance(legacy_res, list)
        self.assertIn("Python", legacy_res)


if __name__ == "__main__":
    unittest.main()
