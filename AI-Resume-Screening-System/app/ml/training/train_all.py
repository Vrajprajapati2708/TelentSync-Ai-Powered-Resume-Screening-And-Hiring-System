# ============================================================
#  TalentSync — Master Training Script
#
#  Runs the full ML pipeline training sequence:
#    1. Generate synthetic training dataset (600 resumes, 200 JDs)
#    2. Train spaCy custom NER model (SKILL entity detection)
#    3. Train scikit-learn TF-IDF recommender
#    4. Print a final model health report
#
#  Run:  python -m app.ml.training.train_all
#        or from project root: python train_all.py
# ============================================================

import sys
import time
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(BASE_DIR))

from app.ml.training.generate_dataset import generate_dataset
from app.ml.training.train_skill_ner   import train_ner_model
from app.ml.training.train_recommender import train_tfidf_recommender
from app.utils.logger import get_logger

logger = get_logger(__name__)


def print_header(title: str):
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  {title}")
    print(f"{bar}\n")


def print_model_report():
    """Print a summary of all trained models."""
    model_base  = BASE_DIR / "trained_models"
    ner_meta    = model_base / "spacy_skill_ner"  / "training_history.json"
    tfidf_meta  = model_base / "tfidf_recommender" / "metadata.json"

    print_header("TalentSync ML Pipeline — Model Health Report")

    if ner_meta.exists():
        with open(ner_meta) as f:
            h = json.load(f)
        best = h.get("best_f1", "N/A")
        epochs = h.get("epochs", "N/A")
        print(f"  [OK] spaCy SKILL NER Model")
        print(f"    Epochs trained : {epochs}")
        print(f"    Best F1 score  : {best:.4f}" if isinstance(best, float) else f"    Best F1 score  : {best}")
        last = h["history"][-1] if h.get("history") else {}
        if last:
            print(f"    Final Loss     : {last.get('loss', 'N/A')}")
            print(f"    Final Precision: {last.get('precision', 'N/A')}")
            print(f"    Final Recall   : {last.get('recall', 'N/A')}")
    else:
        print("  [MISS] spaCy NER model not found.")

    print()

    if tfidf_meta.exists():
        with open(tfidf_meta) as f:
            m = json.load(f)
        ev = m.get("evaluation", {})
        print(f"  [OK] scikit-learn TF-IDF Recommender")
        print(f"    Vocabulary size : {m.get('vocab_size', 'N/A'):,}")
        print(f"    Corpus size     : {m.get('corpus_size', 'N/A'):,} documents")
        print(f"    n-gram range    : {m.get('ngram_range', 'N/A')}")
        print(f"    Train time      : {m.get('train_time_s', 'N/A')}s")
        print(f"    Hit-Rate @1     : {ev.get('hit_rate_top1', 'N/A'):.2%}" if ev else "")
        print(f"    Hit-Rate @3     : {ev.get('hit_rate_top3', 'N/A'):.2%}" if ev else "")
        print(f"    Hit-Rate @5     : {ev.get('hit_rate_top5', 'N/A'):.2%}" if ev else "")
    else:
        print("  [MISS] TF-IDF recommender model not found.")

    print()
    print("  Models ready for production inference.")
    print("  Restart the Flask server to load new models.")
    print("=" * 60)


def train_all(skip_ner: bool = False):
    """
    Master training pipeline.

    Args:
        skip_ner: If True, skip NER training (faster for testing).
    """
    total_start = time.time()

    print_header("TalentSync — Full ML Pipeline Training")
    print("  This will:")
    print("  1. Generate 600 synthetic resumes + 200 job descriptions")
    print("  2. Train a custom spaCy NER model for SKILL detection")
    print("  3. Train a scikit-learn TF-IDF recommender")
    print()

    # ── Step 1: Generate Dataset ──────────────────────────────
    print_header("Step 1/3 — Generating Training Dataset")
    t = time.time()
    dataset = generate_dataset(
        num_resumes=600,
        num_jobs=200,
        output_dir=str(BASE_DIR / "datasets")
    )
    print(f"  Done in {time.time() - t:.1f}s")
    print(f"  Resumes: {len(dataset['resumes'])}")
    print(f"  Jobs:    {len(dataset['jobs'])}")

    # ── Step 2: Train NER ─────────────────────────────────────
    if not skip_ner:
        print_header("Step 2/3 — Training spaCy SKILL NER Model")
        t = time.time()
        ner_path = train_ner_model(n_iter=30, dropout=0.3)
        print(f"\n  NER model saved to: {ner_path}")
        print(f"  Done in {time.time() - t:.1f}s")
    else:
        print_header("Step 2/3 — Skipping NER Training")
        print("  (pass skip_ner=False to train the NER model)")

    # ── Step 3: Train TF-IDF ──────────────────────────────────
    print_header("Step 3/3 — Training TF-IDF Recommender")
    t = time.time()
    tfidf_path = train_tfidf_recommender()
    print(f"\n  Recommender model saved to: {tfidf_path}")
    print(f"  Done in {time.time() - t:.1f}s")

    # ── Final Report ──────────────────────────────────────────
    total_elapsed = time.time() - total_start
    print(f"\n  Total training time: {total_elapsed:.1f}s")
    print_model_report()


if __name__ == "__main__":
    # Check for --skip-ner flag
    skip = "--skip-ner" in sys.argv
    train_all(skip_ner=skip)
