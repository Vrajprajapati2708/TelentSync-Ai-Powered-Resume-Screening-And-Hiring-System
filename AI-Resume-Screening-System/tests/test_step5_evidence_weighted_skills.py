import unittest
import json
from app.ml.ranking.ranking_engine import (
    compute_candidate_score,
    rank_candidates,
    match_skill_in_text,
    EVIDENCE_WEIGHTS
)


class TestStep5EvidenceWeightedSkills(unittest.TestCase):
    """
    Test Step 5: Evidence-Weighted Skills Matching.
    Verifies that:
    1. Skills matched in experience bullet points receive 1.0 weight.
    2. Skills matched in project descriptions receive 0.7 weight.
    3. Skills matched only in bare skill lists receive 0.2 weight (anti-keyword stuffing).
    4. Quiz-verified skills receive 1.0 weight even if only in the bare list.
    5. Symbol-safe regex matching properly handles C++, C#, .NET, Node.js.
    6. Disambiguation ensures 'C' does not match 'C++' or 'C#', and 'Java' does not match 'JavaScript'.
    7. Candidates with real work experience rank significantly higher than keyword stuffers.
    """

    def test_evidence_weight_tiers_experience_vs_project_vs_list(self):
        """Experience bullets (1.0) beat projects (0.7) which beat bare lists (0.2)."""
        job_skills = ["Python", "Docker"]

        # Candidate with skills in experience bullets
        cand_exp = {
            "name": "Experience Candidate",
            "ats_score": 80,
            "education": "Bachelor of Technology",
            "experience_lines": [
                "Developed scalable backend APIs in Python and containerized services using Docker."
            ]
        }

        # Candidate with skills in projects
        cand_proj = {
            "name": "Project Candidate",
            "ats_score": 80,
            "education": "Bachelor of Technology",
            "projects": [
                {"name": "App", "description": "Academic capstone project built using Python and Docker."}
            ]
        }

        # Candidate with skills only in bare skills list (keyword stuffer)
        cand_list = {
            "name": "List Candidate",
            "ats_score": 80,
            "education": "Bachelor of Technology",
            "skills": "Python, Docker",
            "experience_lines": [
                "Handled client calls and administrative documentation."
            ]
        }

        score_exp = compute_candidate_score(cand_exp, job_skills)
        score_proj = compute_candidate_score(cand_proj, job_skills)
        score_list = compute_candidate_score(cand_list, job_skills)

        # Experience: 1.0 + 1.0 = 2.0 / 2 = 100% -> 40 points
        self.assertEqual(score_exp["skills_score"], 40)
        self.assertEqual(score_exp["skill_evidence"]["Python"]["weight"], 1.0)
        self.assertEqual(score_exp["skill_evidence"]["Docker"]["weight"], 1.0)
        self.assertEqual(score_exp["skill_evidence"]["Python"]["source"], "experience")

        # Project: 0.7 + 0.7 = 1.4 / 2 = 70% -> 28 points
        self.assertEqual(score_proj["skills_score"], 28)
        self.assertEqual(score_proj["skill_evidence"]["Python"]["weight"], 0.7)
        self.assertEqual(score_proj["skill_evidence"]["Docker"]["weight"], 0.7)
        self.assertEqual(score_proj["skill_evidence"]["Python"]["source"], "project")

        # Bare list: 0.2 + 0.2 = 0.4 / 2 = 20% -> 8 points
        self.assertEqual(score_list["skills_score"], 8)
        self.assertEqual(score_list["skill_evidence"]["Python"]["weight"], 0.2)
        self.assertEqual(score_list["skill_evidence"]["Docker"]["weight"], 0.2)
        self.assertEqual(score_list["skill_evidence"]["Python"]["source"], "list")

        # Total scores must reflect the anti-gaming gap
        self.assertGreater(score_exp["total_score"], score_proj["total_score"])
        self.assertGreater(score_proj["total_score"], score_list["total_score"])

    def test_quiz_verified_skill_elevates_bare_list_to_full_weight(self):
        """A skill verified via technical quiz gets 1.0 weight even if only in bare list."""
        job_skills = ["Python", "Kubernetes"]

        # Candidate has Python and Kubernetes in bare list only, but Python is verified
        cand = {
            "skills": "Python, Kubernetes",
            "verified_skills": {"python"},
            "ats_score": 75,
            "education": "Bachelor"
        }

        score = compute_candidate_score(cand, job_skills)

        # Python is verified -> 1.0
        self.assertEqual(score["skill_evidence"]["Python"]["weight"], 1.0)
        self.assertEqual(score["skill_evidence"]["Python"]["source"], "verified")

        # Kubernetes is unverified list -> 0.2
        self.assertEqual(score["skill_evidence"]["Kubernetes"]["weight"], 0.2)
        self.assertEqual(score["skill_evidence"]["Kubernetes"]["source"], "list")

        # Total evidence: (1.0 + 0.2) / 2 = 0.60 -> 24 points
        self.assertEqual(score["skills_score"], 24)

    def test_explicit_verified_skills_parameter_in_compute_and_rank(self):
        """Passing verified_skills as an argument elevates skills appropriately."""
        job_skills = ["AWS", "Terraform"]
        cand = {
            "skills": "AWS, Terraform",
            "ats_score": 70,
            "education": "Master"
        }

        # Without verified skills: both in list -> 0.2 * 40 = 8
        unverified_score = compute_candidate_score(cand, job_skills)
        self.assertEqual(unverified_score["skills_score"], 8)

        # With verified skills passed explicitly
        verified_score = compute_candidate_score(cand, job_skills, verified_skills={"aws", "terraform"})
        self.assertEqual(verified_score["skills_score"], 40)
        self.assertEqual(verified_score["skill_evidence"]["AWS"]["weight"], 1.0)
        self.assertEqual(verified_score["skill_evidence"]["Terraform"]["weight"], 1.0)

    def test_symbol_safe_regex_matching_cpp_csharp_dotnet_nodejs(self):
        """Regex boundary matching properly handles C++, C#, .NET, Node.js without \\b failure."""
        text = "Experienced software engineer skilled in C++, C#, .NET Core, and Node.js microservices."

        self.assertTrue(match_skill_in_text("C++", text), "Failed to match C++")
        self.assertTrue(match_skill_in_text("c++", text), "Failed to match c++ case-insensitively")
        self.assertTrue(match_skill_in_text("C#", text), "Failed to match C#")
        self.assertTrue(match_skill_in_text("c#", text), "Failed to match c# case-insensitively")
        self.assertTrue(match_skill_in_text(".NET", text), "Failed to match .NET")
        self.assertTrue(match_skill_in_text(".net", text), "Failed to match .net case-insensitively")
        self.assertTrue(match_skill_in_text("Node.js", text), "Failed to match Node.js")
        self.assertTrue(match_skill_in_text("node.js", text), "Failed to match node.js case-insensitively")

    def test_regex_disambiguation_c_vs_cpp_csharp_and_java_vs_javascript(self):
        """Single-letter 'C' must not match 'C++' or 'C#', and 'Java' must not match 'JavaScript'."""
        cpp_only_text = "Proficient in C++ and C# development."
        self.assertFalse(match_skill_in_text("C", cpp_only_text), "'C' falsely matched in text containing only C++ and C#")

        c_valid_text = "Core embedded developer writing ANSI C systems."
        self.assertTrue(match_skill_in_text("C", c_valid_text), "'C' failed to match in valid C text")

        js_only_text = "Frontend engineer building UI in JavaScript and TypeScript."
        self.assertFalse(match_skill_in_text("Java", js_only_text), "'Java' falsely matched 'JavaScript'")

        java_valid_text = "Backend developer building Spring services in Java."
        self.assertTrue(match_skill_in_text("Java", java_valid_text), "'Java' failed to match valid Java text")

    def test_structured_json_evidence_extraction(self):
        """Structured JSON document extracts experience and projects seamlessly."""
        job_skills = ["Go", "Redis", "Kafka"]

        intel = {
            "sections": {
                "experience": "Architected Go backend services with high throughput.",
                "projects": "Implemented distributed caching with Redis.",
                "skills": "Go, Redis, Kafka"
            },
            "experience": [
                {"role": "Lead Go Dev", "description": "Built distributed services in Go"}
            ],
            "projects": [
                {"name": "Cache Layer", "description": "Distributed cache using Redis cluster"}
            ]
        }

        cand = {
            "name": "Structured Candidate",
            "structured_json": json.dumps(intel),
            "ats_score": 90,
            "education": "Master of Science"
        }

        score = compute_candidate_score(cand, job_skills)

        # Go: matched in experience -> 1.0
        self.assertEqual(score["skill_evidence"]["Go"]["weight"], 1.0)
        self.assertEqual(score["skill_evidence"]["Go"]["source"], "experience")

        # Redis: matched in projects -> 0.7
        self.assertEqual(score["skill_evidence"]["Redis"]["weight"], 0.7)
        self.assertEqual(score["skill_evidence"]["Redis"]["source"], "project")

        # Kafka: only in bare skills -> 0.2
        self.assertEqual(score["skill_evidence"]["Kafka"]["weight"], 0.2)
        self.assertEqual(score["skill_evidence"]["Kafka"]["source"], "list")

        # Total: (1.0 + 0.7 + 0.2) / 3 = 1.9 / 3 = 0.6333... -> 25 points
        self.assertEqual(score["skills_score"], 25)

    def test_rank_candidates_prioritizes_evidence_over_keyword_stuffing(self):
        """rank_candidates ranks candidates with verified/experience evidence above keyword stuffers."""
        job_skills = ["Python", "Docker", "AWS", "SQL"]

        # Cheater with all 4 skills in bare list, 0 experience evidence
        cand_cheater = {
            "name": "Cheater List",
            "skills": "Python, Docker, AWS, SQL",
            "ats_score": 80,
            "education": "Bachelor",
            "experience_lines": ["General admin tasks", "Answering queries"]
        }

        # Real engineer with 3 skills in experience bullets, 1 missing
        cand_real = {
            "name": "Real Engineer",
            "skills": "Python, Docker, SQL",
            "ats_score": 80,
            "education": "Bachelor",
            "experience_lines": [
                "Engineered Python microservices",
                "Containerized pipelines using Docker",
                "Managed relational SQL databases"
            ]
        }

        ranked = rank_candidates([cand_cheater, cand_real], job_skills)

        # Real Engineer must be Rank 1
        self.assertEqual(ranked[0]["name"], "Real Engineer")
        self.assertEqual(ranked[0]["rank"], 1)

        # Cheater must be Rank 2
        self.assertEqual(ranked[1]["name"], "Cheater List")
        self.assertEqual(ranked[1]["rank"], 2)

        # Real engineer skills score (3 * 1.0 + 0) / 4 = 75% -> 30/40
        # Cheater skills score (4 * 0.2) / 4 = 20% -> 8/40
        self.assertGreater(ranked[0]["rank_score"], ranked[1]["rank_score"])


if __name__ == "__main__":
    unittest.main()
