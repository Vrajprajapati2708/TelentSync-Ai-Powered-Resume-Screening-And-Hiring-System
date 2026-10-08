# ============================================================
#  TalentSync — Job Recommendation Engine (v2 — Real ML)
#
#  Two-Stage Recommendation Pipeline:
#
#  Stage 1 — Semantic TF-IDF Matching (sklearn, vectorized):
#    - Transform resume + all jobs into TF-IDF feature space.
#    - Compute cosine similarity using C++ optimized sklearn.
#    - Score = semantic content similarity (0–1).
#
#  Stage 2 — Skill Overlap Matching (interpretable):
#    - Direct set-intersection of extracted skills vs job skills.
#    - Score = fraction of required skills the candidate has.
#
#  Final Score = (semantic_weight × TF-IDF_cos) +
#                (skill_weight   × skill_overlap)
#    Default: 40% TF-IDF + 60% Skill Overlap
#
#  Why hybrid?  TF-IDF captures overall text similarity,
#  skill overlap is directly interpretable to the recruiter.
# ============================================================

from app.ml.recommendation.tfidf_model import TFIDFVectorizer, get_vectorizer
from app.ml.recommendation.cosine_similarity import (
    cosine_similarity, cosine_similarity_matrix,
    skill_overlap_score, rank_by_similarity
)
from app.ml.preprocessing.clean_text import preprocess_to_string
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Recommendation Weights ────────────────────────────────────
SEMANTIC_WEIGHT = 0.40   # TF-IDF cosine similarity
SKILL_WEIGHT    = 0.60   # Direct skill overlap


def recommend_jobs(candidate_skills: list[str],
                   jobs: list[dict],
                   top_n: int = 10,
                   candidate_resume_text: str | None = None) -> list[dict]:
    """
    Recommend the top N jobs for a candidate using two-stage matching.

    Stage 1 — TF-IDF Semantic Similarity (sklearn, fast):
        Vectorises resume text (or joined skill list) against all job
        descriptions in one matrix multiplication.

    Stage 2 — Skill Overlap Score (interpretable):
        Direct set-intersection of candidate skills vs job skills.

    Final score = SEMANTIC_WEIGHT × tfidf_cos + SKILL_WEIGHT × overlap

    Args:
        candidate_skills:      Extracted skills from the candidate's resume.
        jobs:                  List of job dicts (from DB) with 'skills', 'description'.
        top_n:                 Maximum number of recommendations to return.
        candidate_resume_text: Full resume text (preferred over skills alone).

    Returns:
        List of job dicts with extra keys:
            - 'match_percentage' (int 0–100)
            - 'matched_skills'   (list[str])
            - 'missing_skills'   (list[str])
            - 'semantic_score'   (float 0–1)
            - 'skill_score'      (float 0–1)
    """
    if not jobs:
        return []

    # ── Candidate text ────────────────────────────────────────
    if candidate_resume_text:
        candidate_text = preprocess_to_string(candidate_resume_text)
    else:
        candidate_text = preprocess_to_string(' '.join(candidate_skills))

    # ── Job texts ─────────────────────────────────────────────
    job_texts = [
        preprocess_to_string(
            f"{j.get('title', '')} {j.get('skills', '')} {j.get('description', '')}"
        )
        for j in jobs
    ]

    # ── Get the shared production vectorizer ──────────────────
    vectorizer = get_vectorizer()

    if vectorizer.is_sklearn:
        # ── Fast sklearn path: single matrix transform ────────
        from typing import Any, cast
        from sklearn.metrics.pairwise import cosine_similarity as sk_cos
        cand_vec   = vectorizer.transform(candidate_text)
        job_matrix = vectorizer.transform_many(job_texts)
        sim_scores = sk_cos(cast(Any, cand_vec), cast(Any, job_matrix)).flatten()

    else:
        # ── Pure-Python fallback: fit on fly ──────────────────
        all_texts  = [candidate_text] + job_texts
        all_vecs   = vectorizer.fit_transform(all_texts)       # list[dict]
        cand_vec   = all_vecs[0]
        sim_scores = [cosine_similarity(cand_vec, v) for v in all_vecs[1:]]

    # ── Build Results ─────────────────────────────────────────
    results = []
    for i, job in enumerate(jobs):
        job_skills   = [s.strip() for s in job.get('skills', '').split(',') if s.strip()]
        overlap      = skill_overlap_score(candidate_skills, job_skills)

        try:
            semantic   = float(sim_scores[i])
        except (IndexError, TypeError):
            semantic   = 0.0

        final_score = (SEMANTIC_WEIGHT * semantic) + (SKILL_WEIGHT * overlap)
        match_pct   = min(int(final_score * 100), 100)

        if match_pct <= 0:
            continue

        cand_lower  = {s.lower() for s in candidate_skills}
        matched     = [s for s in job_skills if s.lower() in cand_lower]
        missing     = [s for s in job_skills if s.lower() not in cand_lower]

        enriched = dict(job)
        enriched['match_percentage'] = match_pct
        enriched['score']            = round(final_score, 4)
        enriched['hybrid_score']     = round(final_score, 4)
        enriched['tfidf_score']      = round(semantic, 4)
        enriched['matched_skills']   = matched
        enriched['missing_skills']   = missing
        enriched['semantic_score']   = round(semantic, 4)
        enriched['skill_score']      = round(overlap,  4)
        results.append(enriched)

    results.sort(key=lambda x: x['match_percentage'], reverse=True)
    logger.info(
        f"recommend_jobs: {len(results)} matches from {len(jobs)} jobs "
        f"(sklearn={vectorizer.is_sklearn})."
    )
    return results[:top_n]
