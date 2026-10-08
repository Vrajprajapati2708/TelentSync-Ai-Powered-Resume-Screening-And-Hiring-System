# ============================================================
#  TalentSync — TF-IDF Model (v2 — Real ML, scikit-learn)
#
#  Loads the trained scikit-learn TfidfVectorizer from disk.
#  Falls back to the pure-Python implementation if the model
#  file is not yet available (i.e., before training).
#
#  The vectorizer is loaded ONCE at module import time and
#  reused across all requests for maximum performance.
# ============================================================

import os
import math
import re
from pathlib import Path
from app.ml.preprocessing.clean_text import preprocess_to_string
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Model Path ────────────────────────────────────────────────
def _resolve_model_dir() -> Path:
    if os.getenv("MODEL_DIR"):
        p = Path(os.getenv("MODEL_DIR")).resolve()
        if p.is_dir():
            return p
    try:
        from app.config.settings import ActiveConfig
        if hasattr(ActiveConfig, "MODEL_DIR") and Path(ActiveConfig.MODEL_DIR).is_dir():
            return Path(ActiveConfig.MODEL_DIR).resolve()
    except Exception:
        pass
    curr = Path(__file__).resolve().parent
    for parent in [curr] + list(curr.parents):
        candidate = parent / "trained_models"
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parents[3] / "trained_models"


_MODEL_DIR  = _resolve_model_dir()
_MODEL_PATH = _MODEL_DIR / "tfidf_recommender" / "tfidf_vectorizer.pkl"

# ── Lazy Model State ──────────────────────────────────────────
_sklearn_vectorizer = None
_sklearn_available  = False


def _load_sklearn_model():
    """Load the trained scikit-learn TF-IDF vectorizer (once)."""
    global _sklearn_vectorizer, _sklearn_available

    if _sklearn_vectorizer is not None:
        return

    if not _MODEL_PATH.exists():
        logger.warning(
            f"TF-IDF model not found at '{_MODEL_PATH}'. "
            "Using pure-Python fallback. "
            "Run 'python -m app.ml.training.train_all' to train the model."
        )
        _sklearn_available = False
        return

    try:
        import joblib
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            _sklearn_vectorizer = joblib.load(str(_MODEL_PATH))
        _sklearn_available  = True
        vocab_size = len(_sklearn_vectorizer.vocabulary_)
        logger.info(f"[OK] Loaded sklearn TF-IDF model ({vocab_size:,} terms) from '{_MODEL_PATH}'")
    except Exception as e:
        logger.error(f"Failed to load TF-IDF model: {e}. Using pure-Python fallback.")
        _sklearn_available = False


def is_sklearn_available() -> bool:
    """Return whether the scikit-learn TF-IDF model is loaded and available."""
    _load_sklearn_model()
    return bool(_sklearn_available)


def clear_tfidf_cache():
    """Reset cached in-memory vectorizer to force fresh reload from disk."""
    global _sklearn_vectorizer, _sklearn_available
    _sklearn_vectorizer = None
    _sklearn_available  = False



# ── Pure-Python Fallback (used before training) ───────────────
class _PurePythonTFIDF:
    """
    Lightweight pure-Python TF-IDF vectorizer.
    Used as fallback when scikit-learn model is not yet trained.
    """

    def __init__(self):
        self.vocabulary: dict[str, int] = {}
        self.idf: dict[str, float]      = {}
        self._fitted = False

    def fit(self, documents: list[str]) -> '_PurePythonTFIDF':
        processed = [preprocess_to_string(d) for d in documents]
        doc_freq: dict[str, int] = {}
        all_tokens = set()

        for doc in processed:
            tokens = set(doc.split())
            all_tokens.update(tokens)
            for t in tokens:
                doc_freq[t] = doc_freq.get(t, 0) + 1

        self.vocabulary = {word: idx for idx, word in enumerate(sorted(all_tokens))}
        N = len(processed)
        self.idf = {
            word: math.log((N + 1) / (doc_freq.get(word, 0) + 1)) + 1
            for word in self.vocabulary
        }
        self._fitted = True
        return self

    def transform(self, text: str) -> dict[str, float]:
        from collections import Counter
        if not self._fitted:
            raise RuntimeError("Call fit() first.")
        processed = preprocess_to_string(text)
        tokens    = processed.split()
        tf        = Counter(tokens)
        total     = len(tokens) or 1
        return {
            word: (tf[word] / total) * self.idf.get(word, 1.0)
            for word in self.vocabulary if word in tf
        }

    def fit_transform(self, documents: list[str]) -> list[dict[str, float]]:
        self.fit(documents)
        return [self.transform(d) for d in documents]


# ── Public API ────────────────────────────────────────────────
class TFIDFVectorizer:
    """
    Production TF-IDF Vectorizer.

    Wraps the trained scikit-learn model transparently.
    Falls back to the pure-Python implementation if not trained.

    Usage:
        vectorizer = TFIDFVectorizer()
        vecs = vectorizer.fit_transform(["text1", "text2"])
        query_vec = vectorizer.transform("new text")
    """

    def __init__(self):
        self._fallback = _PurePythonTFIDF()

    def fit(self, documents: list[str]) -> 'TFIDFVectorizer':
        """Fit the vectorizer. No-op if the sklearn model is already loaded."""
        if not self.is_sklearn:
            self._fallback.fit(documents)
        return self

    def transform(self, text: str):
        """
        Transform text to a TF-IDF vector.

        Returns:
            scipy sparse matrix row (sklearn) or dict (fallback).
        """
        if self.is_sklearn:
            processed = preprocess_to_string(text)
            return _sklearn_vectorizer.transform([processed])
        return self._fallback.transform(text)

    def fit_transform(self, documents: list[str]):
        """Fit and transform all documents."""
        if self.is_sklearn:
            processed = [preprocess_to_string(d) for d in documents]
            return _sklearn_vectorizer.transform(processed)
        return self._fallback.fit_transform(documents)

    @property
    def is_sklearn(self) -> bool:
        return is_sklearn_available()

    @property
    def vocab_size(self) -> int:
        if self.is_sklearn:
            return len(_sklearn_vectorizer.vocabulary_)
        return len(self._fallback.vocabulary)


# ── Module-level singleton ─────────────────────────────────────
_vectorizer = TFIDFVectorizer()


def get_vectorizer() -> TFIDFVectorizer:
    """Return the shared, pre-loaded vectorizer instance."""
    return _vectorizer


def get_model_info() -> dict:
    """Return metadata about the active TF-IDF model."""
    if is_sklearn_available():
        import json
        meta_path = _MODEL_PATH.parent / "metadata.json"
        if meta_path.exists():
            with open(meta_path) as f:
                return json.load(f)
    return {"model": "pure_python_fallback", "status": "not_trained"}

