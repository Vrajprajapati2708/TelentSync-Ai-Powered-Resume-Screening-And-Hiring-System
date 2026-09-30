# ============================================================
#  TalentSync — ATS Score Checker
#  Computes an Applicant Tracking System compatibility score.
#
#  Scoring breakdown (total = 100):
#    Skills detected        : 40 pts  (max)
#    Contact info present   : 15 pts
#    Education section      : 15 pts
#    Experience section     : 15 pts
#    Resume length / content: 15 pts
# ============================================================

import re
from app.ml.skill_extraction.extract_skills import extract_skills
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ATS section keywords
_CONTACT_PATTERNS  = [r'@', r'\+?\d{10,}', r'linkedin\.com', r'github\.com']
_EDUCATION_WORDS   = ['education', 'degree', 'university', 'college', 'b.tech', 'bachelor', 'master', 'cgpa', 'gpa']
_EXPERIENCE_WORDS  = ['experience', 'work', 'internship', 'project', 'employment', 'company', 'organisation']
_SUMMARY_WORDS     = ['summary', 'objective', 'profile', 'about', 'overview']


def compute_ats_score(text: str, job_skills: list[str] | None = None) -> dict:
    """
    Calculate ATS score for a resume text.

    Args:
        text:       Raw resume text (lowercased).
        job_skills: Optional list of required job skills for keyword boost.

    Returns:
        {
            'score':       int  (0–100),
            'grade':       str  ('Excellent'|'Good'|'Average'|'Poor'),
            'breakdown':   dict  (sub-scores per section),
            'suggestions': list[str]  (improvement tips),
            'skills':      list[str]  (extracted skills),
        }
    """
    if not text:
        return _empty_ats()

    text_lower = text.lower()
    suggestions = []
    breakdown   = {}

    # ── 1. Skills score (40 pts) ─────────────────────────────
    skills     = extract_skills(text)
    skill_pts  = min(len(skills) * 4, 40)    # 4 pts per skill, max 40
    breakdown['skills'] = skill_pts

    if skill_pts < 20:
        suggestions.append("Add more technical skills — aim for at least 10 relevant skills.")

    # ── 2. Contact info (15 pts) ─────────────────────────────
    contact_pts = 0
    for pat in _CONTACT_PATTERNS:
        if re.search(pat, text_lower):
            contact_pts += 4                 # +4 per found contact field
    contact_pts = min(contact_pts, 15)
    breakdown['contact_info'] = contact_pts

    if contact_pts < 8:
        suggestions.append("Include your email, phone, LinkedIn, and GitHub links.")

    # ── 3. Education section (15 pts) ────────────────────────
    edu_pts = 0
    for kw in _EDUCATION_WORDS:
        if kw in text_lower:
            edu_pts += 3
    edu_pts = min(edu_pts, 15)
    breakdown['education'] = edu_pts

    if edu_pts < 9:
        suggestions.append("Add a clear Education section with degree, university, and CGPA.")

    # ── 4. Experience section (15 pts) ───────────────────────
    exp_pts = 0
    for kw in _EXPERIENCE_WORDS:
        if kw in text_lower:
            exp_pts += 3
    exp_pts = min(exp_pts, 15)
    breakdown['experience'] = exp_pts

    if exp_pts < 9:
        suggestions.append("Add an Experience / Internship section with company names and roles.")

    # ── 5. Content length (15 pts) ───────────────────────────
    word_count  = len(text.split())
    length_pts  = min(int(word_count / 20), 15)   # 1 pt per 20 words, max 15
    breakdown['content_length'] = length_pts

    if word_count < 150:
        suggestions.append("Resume seems short — add project descriptions and achievements.")

    # ── Final score ──────────────────────────────────────────
    total = sum(breakdown.values())
    total = max(min(total, 100), 0)

    # Keyword boost: if job_skills provided and matches found
    if job_skills:
        cand_lower = {s.lower() for s in skills}
        job_lower  = {s.lower() for s in job_skills}
        match_ratio = len(cand_lower & job_lower) / len(job_lower) if job_lower else 0
        missing = [s for s in job_skills if s.lower() not in cand_lower]
        if missing:
            suggestions.append(f"Add missing keywords: {', '.join(missing[:5])}")
    else:
        match_ratio = None

    grade = _grade(total)

    logger.info(f"ATS score computed: {total}/100 ({grade}), {len(skills)} skills found.")

    return {
        'score':        total,
        'grade':        grade,
        'breakdown':    breakdown,
        'suggestions':  suggestions,
        'skills':       skills,
        'keyword_match': round(match_ratio * 100) if match_ratio is not None else None,
    }


def _grade(score: int) -> str:
    if score >= 85:  return 'Excellent'
    if score >= 70:  return 'Good'
    if score >= 50:  return 'Average'
    return 'Poor'


def _empty_ats() -> dict:
    return {
        'score': 0, 'grade': 'Poor', 'breakdown': {},
        'suggestions': ['Upload a valid text-based PDF resume.'],
        'skills': [], 'keyword_match': None
    }
