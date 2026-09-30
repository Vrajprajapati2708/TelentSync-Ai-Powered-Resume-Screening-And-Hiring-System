# ============================================================
#  TalentSync — Cosine Similarity (v2 — Real ML, scikit-learn)
#
#  Uses sklearn.metrics.pairwise.cosine_similarity for
#  fast, matrix-optimized vectorized computations.
#
#  Supports both:
#    - scipy sparse matrices (sklearn TF-IDF output)
#    - plain dicts (pure-Python fallback)
# ============================================================

import math
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)


def cosine_similarity(vec_a, vec_b) -> float:
    """
    Compute cosine similarity between two vectors.

    Accepts either:
        - scipy sparse matrix rows (from sklearn TF-IDF) → uses sklearn
        - dict[str, float]                               → pure-Python math

    Returns:
        float in [0, 1] — 1 means identical, 0 means no overlap.
    """
    # ── Sparse matrix (sklearn path) ─────────────────────────
    try:
        from scipy.sparse import issparse
        if issparse(vec_a) or issparse(vec_b):
            from sklearn.metrics.pairwise import cosine_similarity as sk_cos
            result = sk_cos(vec_a, vec_b)
            return float(result[0][0])
    except ImportError:
        pass

    # ── Dict fallback (pure-Python path) ─────────────────────
    if isinstance(vec_a, dict) and isinstance(vec_b, dict):
        if not vec_a or not vec_b:
            return 0.0
        common_terms = set(vec_a.keys()) & set(vec_b.keys())
        dot_product  = sum(vec_a[t] * vec_b[t] for t in common_terms)
        mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
        mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot_product / (mag_a * mag_b)

    return 0.0


def cosine_similarity_matrix(query_vec, doc_matrix) -> np.ndarray:
    """
    Compute cosine similarity between a single query vector and a matrix of documents.

    This is the fast, vectorized path used by the recommender engine.

    Args:
        query_vec:  scipy sparse row (1 x vocab) or numpy array (1 x vocab).
        doc_matrix: scipy sparse matrix (n_docs x vocab).

    Returns:
        numpy array of shape (n_docs,) with similarity scores.
    """
    try:
        from sklearn.metrics.pairwise import cosine_similarity as sk_cos
        scores = sk_cos(query_vec, doc_matrix)
        return scores.flatten()
    except Exception as e:
        logger.error(f"cosine_similarity_matrix failed: {e}")
        return np.zeros(doc_matrix.shape[0])


def skill_overlap_score(candidate_skills: list[str], job_skills: list[str]) -> float:
    """
    Simple set-intersection skill match score.

    Formula: |candidate ∩ job| / |job|

    Returns:
        float in [0, 1]
    """
    if not job_skills:
        return 0.0
    cand_lower = {s.lower() for s in candidate_skills}
    job_lower  = {s.lower() for s in job_skills}
    intersection = cand_lower & job_lower
    return len(intersection) / len(job_lower)


def rank_by_similarity(query_vec, document_vecs) -> list[tuple[int, float]]:
    """
    Rank documents by cosine similarity to a query vector.

    Handles both:
        - New sklearn path: query_vec = sparse row,
          document_vecs = list of (id, sparse_row)
        - Legacy dict path: query_vec = dict,
          document_vecs = list of (id, dict)

    Returns:
        List of (doc_id, similarity_score) sorted descending.
    """
    if not document_vecs:
        return []

    # ── Try fast sklearn batch path ───────────────────────────
    try:
        from scipy.sparse import issparse, vstack as sp_vstack
        if issparse(query_vec):
            ids       = [d[0] for d in document_vecs]
            doc_rows  = [d[1] for d in document_vecs]
            doc_mat   = sp_vstack(doc_rows)
            scores_arr = cosine_similarity_matrix(query_vec, doc_mat)
            scored = list(zip(ids, scores_arr.tolist()))
            return sorted(scored, key=lambda x: x[1], reverse=True)
    except Exception:
        pass

    # ── Legacy dict path ──────────────────────────────────────
    scores = [
        (doc_id, cosine_similarity(query_vec, doc_vec))
        for doc_id, doc_vec in document_vecs
    ]
    return sorted(scores, key=lambda x: x[1], reverse=True)
