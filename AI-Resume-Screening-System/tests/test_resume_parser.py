# ============================================================
#  TalentSync — Test: Resume Parser
# ============================================================

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.ml.skill_extraction.extract_skills import extract_skills, get_skill_gaps
from app.ml.preprocessing.clean_text import clean_text, preprocess


def test_clean_text():
    text = "  Hello WORLD!  Visit https://example.com and email test@test.com  "
    result = clean_text(text)
    assert 'https' not in result
    assert 'test@test.com' not in result
    assert result == result.lower()
    print("OK test_clean_text passed")


def test_extract_skills_basic():
    text = "Experienced in Python, Machine Learning, SQL and Tableau."
    skills = extract_skills(text)
    assert 'Python' in skills
    assert 'Sql' in skills or 'SQL' in skills
    print(f"✅ test_extract_skills_basic passed → {skills}")


def test_extract_skills_empty():
    skills = extract_skills("")
    assert skills == []
    print("✅ test_extract_skills_empty passed")


def test_skill_gaps():
    candidate_skills = ['Python', 'SQL', 'Machine Learning']
    result = get_skill_gaps(candidate_skills, 'Data Scientist')
    assert 'matched' in result
    assert 'missing' in result
    assert result['match_pct'] > 0
    print(f"✅ test_skill_gaps passed → match={result['match_pct']}%")


def test_preprocess():
    tokens = preprocess("I am a python developer with AWS experience")
    assert 'python' in tokens
    assert 'i' not in tokens   # stopword removed
    print(f"OK test_preprocess passed -> {tokens}")


if __name__ == '__main__':
    print("\n=== TalentSync Resume Parser Tests ===\n")
    test_clean_text()
    test_extract_skills_basic()
    test_extract_skills_empty()
    test_skill_gaps()
    test_preprocess()
    print("\n✅ All tests passed!\n")
