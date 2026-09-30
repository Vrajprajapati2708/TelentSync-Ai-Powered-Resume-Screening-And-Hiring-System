# ============================================================
#  TalentSync — scikit-learn TF-IDF Recommender Training Script
#
#  Trains a production-grade scikit-learn TfidfVectorizer on
#  a large corpus of resume + job description texts.
#
#  Architecture:
#    - sklearn TfidfVectorizer (word n-grams: 1–2)
#    - Cosine similarity via sklearn pairwise metrics
#    - Model persisted to disk with joblib
#    - Separate vectorizers for resumes and job descriptions
#
#  Run:  python -m app.ml.training.train_recommender
# ============================================================

import json
import time
from pathlib import Path

import joblib
import numpy as np
from typing import Any, cast
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split

from app.ml.preprocessing.clean_text import preprocess_to_string
from app.ml.training.generate_dataset import generate_dataset
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parents[4]
DATASET_DIR = BASE_DIR / "datasets"
MODEL_DIR   = BASE_DIR / "trained_models" / "tfidf_recommender"


def _load_or_generate_data() -> tuple:
    """Load existing dataset or generate fresh one."""
    resumes_path = DATASET_DIR / "resumes.json"
    jobs_path    = DATASET_DIR / "jobs.json"

    if resumes_path.exists() and jobs_path.exists():
        logger.info("Loading existing dataset...")
        with open(resumes_path, "r", encoding="utf-8") as f:
            resumes = json.load(f)
        with open(jobs_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
    else:
        logger.info("Generating fresh dataset...")
        dataset = generate_dataset(
            num_resumes=600, num_jobs=200, output_dir=str(DATASET_DIR)
        )
        resumes = dataset["resumes"]
        jobs    = dataset["jobs"]

    return resumes, jobs


def _evaluate_recommendations(vectorizer, resume_matrix, job_matrix,
                                resumes: list, jobs: list,
                                sample_size: int = 50) -> dict:
    """
    Evaluate recommendation quality by checking if the correct role
    appears in the top-5 recommendations for a sample of resumes.

    Returns:
        dict with top-1, top-3, top-5 hit rates.
    """
    sample_idx = np.random.choice(len(resumes), size=min(sample_size, len(resumes)),
                                   replace=False)

    top1_hits = 0
    top3_hits = 0
    top5_hits = 0

    for idx in sample_idx:
        resume     = resumes[idx]
        true_role  = resume["role"]

        # Compute similarities for this resume against all jobs
        sims       = cosine_similarity(resume_matrix[idx], job_matrix).flatten()
        top_k_idx  = sims.argsort()[::-1][:5]

        top_k_roles = [jobs[j]["role"] for j in top_k_idx if j < len(jobs)]

        if top_k_roles and top_k_roles[0] == true_role:
            top1_hits += 1
        if true_role in top_k_roles[:3]:
            top3_hits += 1
        if true_role in top_k_roles[:5]:
            top5_hits += 1

    n = len(sample_idx)
    return {
        "hit_rate_top1": round(top1_hits / n, 4),
        "hit_rate_top3": round(top3_hits / n, 4),
        "hit_rate_top5": round(top5_hits / n, 4),
        "sample_size":   n,
    }


def train_tfidf_recommender(
    max_features:    int   = 8000,
    ngram_range:     tuple = (1, 2),
    min_df:          int   = 2,
    max_df:          float = 0.90,
    sublinear_tf:    bool  = True,
) -> str:
    """
    Train a production-grade TF-IDF recommender.

    Args:
        max_features:  Max vocabulary size.
        ngram_range:   Unigrams + bigrams for richer matching.
        min_df:        Ignore terms appearing in fewer than N docs.
        max_df:        Ignore terms appearing in more than N% of docs.
        sublinear_tf:  Apply log normalization (reduces impact of freq terms).

    Returns:
        Path to the saved model directory.
    """
    logger.info("=" * 60)
    logger.info("TalentSync — TF-IDF Recommender Training")
    logger.info("=" * 60)

    start_time = time.time()

    # ── Step 1: Load Data ─────────────────────────────────────
    resumes, jobs = _load_or_generate_data()
    logger.info(f"Loaded {len(resumes)} resumes and {len(jobs)} job descriptions.")

    # ── Step 2: Preprocess Text ───────────────────────────────
    logger.info("Preprocessing text corpus...")
    resume_texts = [preprocess_to_string(r["text"]) for r in resumes]
    job_texts    = [preprocess_to_string(j["text"]) for j in jobs]

    # Combine for fitting the vocabulary
    all_texts = resume_texts + job_texts

    # ── Step 3: Fit TF-IDF Vectorizer ────────────────────────
    logger.info(f"Fitting TfidfVectorizer "
                f"(max_features={max_features}, ngram_range={ngram_range})...")

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        min_df=min_df,
        max_df=max_df,
        sublinear_tf=sublinear_tf,
        analyzer="word",
        token_pattern=r"(?u)\b\w[\w\+\#\.]*\b",   # capture C++, C#, Node.js
        strip_accents="unicode",
        decode_error="replace",
    )
    vectorizer.fit(all_texts)

    vocab_size = len(vectorizer.vocabulary_)
    logger.info(f"Vocabulary size: {vocab_size:,} terms")

    # ── Step 4: Transform Corpora ─────────────────────────────
    logger.info("Transforming resume and job description matrices...")
    resume_matrix = cast(Any, vectorizer.transform(resume_texts))
    job_matrix    = cast(Any, vectorizer.transform(job_texts))

    logger.info(f"Resume matrix shape:  {resume_matrix.shape}")
    logger.info(f"Job matrix shape:     {job_matrix.shape}")
    logger.info(f"Matrix density:       {resume_matrix.nnz / np.prod(resume_matrix.shape):.4%}")

    # ── Step 5: Evaluate ──────────────────────────────────────
    logger.info("Evaluating recommendation quality on 100 sample resumes...")
    metrics = _evaluate_recommendations(
        vectorizer, resume_matrix, job_matrix, resumes, jobs, sample_size=100
    )
    logger.info(f"  Top-1 Hit Rate: {metrics['hit_rate_top1']:.2%}")
    logger.info(f"  Top-3 Hit Rate: {metrics['hit_rate_top3']:.2%}")
    logger.info(f"  Top-5 Hit Rate: {metrics['hit_rate_top5']:.2%}")

    # ── Step 6: Save Model ────────────────────────────────────
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    vectorizer_path = MODEL_DIR / "tfidf_vectorizer.pkl"
    joblib.dump(vectorizer, str(vectorizer_path), compress=3)

    # Save model metadata
    elapsed = time.time() - start_time
    metadata = {
        "model":          "tfidf_recommender",
        "vocab_size":     vocab_size,
        "max_features":   max_features,
        "ngram_range":    list(ngram_range),
        "min_df":         min_df,
        "max_df":         max_df,
        "sublinear_tf":   sublinear_tf,
        "corpus_size":    len(all_texts),
        "resume_count":   len(resumes),
        "job_count":      len(jobs),
        "train_time_s":   round(elapsed, 2),
        "evaluation":     metrics,
    }

    import json
    meta_path = MODEL_DIR / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"\nModel saved  -> {vectorizer_path}")
    logger.info(f"Metadata     -> {meta_path}")
    logger.info(f"Training complete in {elapsed:.1f}s")

    return str(MODEL_DIR)


if __name__ == "__main__":
    train_tfidf_recommender()
