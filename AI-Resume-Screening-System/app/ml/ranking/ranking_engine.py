# ============================================================
#  TalentSync — Candidate Ranking Engine
#
#  Weighted scoring formula:
#    Skills Match  : 40 %
#    Experience    : 25 %
#    ATS Score     : 20 %
#    Education     : 15 %
# ============================================================

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Ranking weights (must sum to 100)
WEIGHTS = {
    'skills_match': 40,
    'ats_score':    20,
    'experience':   25,
    'education':    15,
}


def compute_candidate_score(candidate: dict, job_skills: list[str]) -> dict:
    """
    Compute a composite ranking score for one candidate against a job.

    Args:
        candidate:   Dict with keys: skills (str), ats_score (int),
                     experience_lines (list), education (str).
        job_skills:  Required skills for the target job.

    Returns:
        Dict with 'total_score' and per-dimension sub-scores.
    """
    # ── Skills match (40%)
    cand_skills  = [s.strip().lower() for s in (candidate.get('skills') or '').split(',') if s.strip()]
    job_lower    = {s.lower() for s in job_skills} if job_skills else set()
    overlap      = len(set(cand_skills) & job_lower) / len(job_lower) if job_lower else 0
    skills_score = round(overlap * WEIGHTS['skills_match'])

    # ── ATS score (20%)
    ats_raw      = min(int(candidate.get('ats_score', 0)), 100)
    ats_score    = round((ats_raw / 100) * WEIGHTS['ats_score'])

    # ── Experience (25%)
    exp_lines    = candidate.get('experience_lines', [])
    exp_count    = len(exp_lines) if isinstance(exp_lines, list) else 0
    # Normalise: 5+ experience lines → full score
    exp_score    = round(min(exp_count / 5, 1.0) * WEIGHTS['experience'])

    # ── Education (15%)
    education    = (candidate.get('education') or '').lower()
    edu_score    = 0
    if any(kw in education for kw in ['phd', 'master', 'm.tech', 'm.sc']):
        edu_score = WEIGHTS['education']
    elif any(kw in education for kw in ['bachelor', 'b.tech', 'b.sc', 'bca', 'b.e']):
        edu_score = round(WEIGHTS['education'] * 0.80)
    elif any(kw in education for kw in ['diploma', 'hsc']):
        edu_score = round(WEIGHTS['education'] * 0.50)
    else:
        edu_score = round(WEIGHTS['education'] * 0.30)

    total = skills_score + ats_score + exp_score + edu_score

    return {
        'total_score':   min(total, 100),
        'skills_score':  skills_score,
        'ats_score':     ats_score,
        'exp_score':     exp_score,
        'edu_score':     edu_score,
    }


def rank_candidates(candidates: list[dict], job_skills: list[str]) -> list[dict]:
    """
    Rank a list of candidate dicts by composite score.

    Args:
        candidates:  List of candidate dicts (from DB).
        job_skills:  Required job skills for the position.

    Returns:
        Sorted list (highest score first) with 'rank' and 'score' fields added.
    """
    scored = []
    for cand in candidates:
        scores = compute_candidate_score(cand, job_skills)
        c = dict(cand)
        c['rank_score']   = scores['total_score']
        c['score_detail'] = scores
        scored.append(c)

    scored.sort(key=lambda x: x['rank_score'], reverse=True)

    for i, c in enumerate(scored):
        c['rank'] = i + 1

    logger.info(f"rank_candidates: ranked {len(scored)} candidates.")
    return scored
