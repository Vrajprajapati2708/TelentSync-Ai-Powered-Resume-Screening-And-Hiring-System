# ============================================================
#  TalentSync — Test: Recommendation Engine
# ============================================================

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.ml.recommendation.cosine_similarity import cosine_similarity, skill_overlap_score
from app.ml.recommendation.recommend_jobs import recommend_jobs
from app.ml.ats.ats_checker import compute_ats_score


SAMPLE_JOBS = [
    {'id': 1, 'title': 'Data Scientist',   'skills': 'Python,Machine Learning,Pandas,SQL,Tableau',    'description': 'Senior DS role.', 'company': 'TechCorp', 'location': 'Bangalore', 'type': 'Full-time', 'salary': '12-18 LPA', 'status': 'Active'},
    {'id': 2, 'title': 'ML Engineer',      'skills': 'Python,TensorFlow,PyTorch,Docker,Deep Learning','description': 'ML at scale.',    'company': 'AI Nexus',  'location': 'Mumbai',    'type': 'Full-time', 'salary': '15-22 LPA', 'status': 'Active'},
    {'id': 3, 'title': 'Frontend Dev',     'skills': 'React,JavaScript,HTML,CSS,Node.js',             'description': 'Build UIs.',      'company': 'UIWorks',   'location': 'Delhi',     'type': 'Full-time', 'salary': '6-11 LPA',  'status': 'Active'},
]


def test_cosine_similarity_identical():
    vec = {'python': 0.5, 'sql': 0.3}
    score = cosine_similarity(vec, vec)
    assert abs(score - 1.0) < 0.001, f"Expected ~1.0, got {score}"
    print("✅ test_cosine_similarity_identical passed")


def test_cosine_similarity_orthogonal():
    vec_a = {'python': 1.0}
    vec_b = {'java': 1.0}
    score = cosine_similarity(vec_a, vec_b)
    assert score == 0.0
    print("✅ test_cosine_similarity_orthogonal passed")


def test_skill_overlap():
    score = skill_overlap_score(['Python', 'SQL'], ['Python', 'SQL', 'Pandas'])
    assert round(score, 2) == 0.67, f"Got {score}"
    print("✅ test_skill_overlap passed")


def test_recommend_jobs_ds_candidate():
    skills = ['Python', 'Machine Learning', 'SQL', 'Pandas']
    results = recommend_jobs(skills, SAMPLE_JOBS)
    assert len(results) > 0
    # Data Scientist should be the top result
    assert results[0]['title'] == 'Data Scientist', f"Expected Data Scientist first, got {results[0]['title']}"
    # Frontend Dev should not rank above Data Scientist if present
    titles = [r['title'] for r in results]
    if 'Frontend Dev' in titles:
        assert titles.index('Data Scientist') < titles.index('Frontend Dev')
    print(f"OK test_recommend_jobs_ds_candidate passed -> {[(r['title'], r['match_percentage']) for r in results]}")


def test_ats_score_good_resume():
    text = """
    Rahul Sharma | rahul@example.com | +91 9876543210 | linkedin.com/in/rahul | github.com/rahul
    Education: B.Tech Computer Science, VIT Vellore, CGPA: 8.4
    Experience: Data Science Intern at Infosys (6 months)
    Skills: Python, Machine Learning, Pandas, SQL, TensorFlow, Scikit-learn, Flask
    Projects: Resume Screening System using NLP and TF-IDF cosine similarity
    """
    result = compute_ats_score(text)
    assert result['score'] > 50, f"Expected >50, got {result['score']}"
    assert result['grade'] in ('Excellent', 'Good', 'Average')
    print(f"✅ test_ats_score_good_resume passed → score={result['score']}, grade={result['grade']}")


def test_ats_score_empty():
    result = compute_ats_score('')
    assert result['score'] == 0
    print("✅ test_ats_score_empty passed")


if __name__ == '__main__':
    print("\n=== TalentSync Recommendation & ATS Tests ===\n")
    test_cosine_similarity_identical()
    test_cosine_similarity_orthogonal()
    test_skill_overlap()
    test_recommend_jobs_ds_candidate()
    test_ats_score_good_resume()
    test_ats_score_empty()
    print("\n✅ All tests passed!\n")
