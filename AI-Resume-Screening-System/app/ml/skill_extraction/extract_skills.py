# ============================================================
#  TalentSync — Skill Extraction Engine (v2 — Real ML)
#
#  Pipeline:
#    Primary  → Load trained spaCy NER model (SKILL entities)
#    Fallback → Regex-boundary matching against skills_db
#               (Used on first run before training, or if model
#                files are missing)
#
#  The NER model is loaded ONCE at module import time and
#  reused across all requests for maximum performance.
# ============================================================

import os
import re
from pathlib import Path
from functools import lru_cache
from app.ml.skill_extraction.skills_db import ALL_SKILLS, SKILL_CATEGORIES, JOB_ROLE_SKILLS
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
_NER_PATH   = _MODEL_DIR / "spacy_skill_ner"

# ── Lazy NER Model Loader ─────────────────────────────────────
_nlp = None
_ner_available = False


def _load_ner_model():
    """Load spaCy NER model once. Thread-safe via module-level flag."""
    global _nlp, _ner_available
    if _nlp is not None:
        return

    if not _NER_PATH.exists():
        logger.info(
            "spaCy NER model not found — using regex+sklearn hybrid. "
            "Run 'py -m app.ml.training.train_all' to train."
        )
        _ner_available = False
        return

    try:
        import spacy
        _nlp = spacy.load(str(_NER_PATH))
        _ner_available = True
        logger.info(f"[OK] Loaded spaCy SKILL NER model from '{_NER_PATH}'")
    except ImportError:
        logger.info(
            "spaCy not installed (Python 3.14+ compatibility issue). "
            "Using regex+sklearn hybrid extractor."
        )
        _ner_available = False
    except Exception as e:
        logger.error(f"Failed to load spaCy NER model: {e}. Using regex fallback.")
        _ner_available = False


def is_ner_available() -> bool:
    """Return whether the spaCy NER model is loaded and available."""
    _load_ner_model()
    return bool(_ner_available)





# ── Skills Section Extractor ──────────────────────────────
# These headings signal the start of a dedicated skills section
_SKILLS_SECTION_HEADERS = re.compile(
    r'(?:^|\n)\s*(?:technical\s+)?skills?'
    r'(?:\s+(?:summary|set|profile|&\s+abilities|and\s+abilities|/\s*competencies))?'
    r'\s*[:\-]?\s*\n',
    re.IGNORECASE
)

# These headings signal the END of the skills section (start of a new section)
_NEXT_SECTION_HEADER = re.compile(
    r'\n\s*(?:experience|education|projects?|work\s+history|employment|'
    r'certifications?|awards?|achievements?|languages?|interests?|'
    r'references?|hobbies?|publications?|summary|objective|profile)\s*[:\-]?\s*\n',
    re.IGNORECASE
)


def _extract_skills_section(text: str) -> str:
    """
    Try to isolate just the Skills section of a resume.
    Returns the skills section text, or empty string if not found.
    """
    match = _SKILLS_SECTION_HEADERS.search(text)
    if not match:
        return ''
    start = match.end()
    # Find the next section header after the skills section
    end_match = _NEXT_SECTION_HEADER.search(text, start)
    end = end_match.start() if end_match else min(start + 800, len(text))
    return text[start:end]


# ── Regex Fallback Extractor ──────────────────────────────
def _regex_extract(text: str) -> list:
    """
    Context-aware skill extractor.

    Strategy:
      1. Try to find a dedicated 'Skills' section and only scan that.
      2. If no skills section found, fall back to full-text scan BUT
         require the skill to appear at least twice OR appear as a
         standalone word (not buried inside a sentence > 10 words).
    This avoids picking up skills mentioned in project descriptions.
    """
    if not text:
        return []

    # ── Try skills section first (highest precision)
    skills_section = _extract_skills_section(text)
    if skills_section.strip():
        text_lower = skills_section.lower()
        found = set()
        for skill in ALL_SKILLS:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found.add(skill.title())
        return sorted(found)

    # ── Fallback: full-text scan with frequency filter
    text_lower = text.lower()
    found = set()
    for skill in ALL_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        matches = list(re.finditer(pattern, text_lower))
        if not matches:
            continue

        # Accept if skill appears 2+ times in the document
        if len(matches) >= 2:
            found.add(skill.title())
            continue

        # Accept if it appears in a short line (≤ 8 words) — likely a skill list
        for m in matches:
            # Find the line containing this match
            line_start = text_lower.rfind('\n', 0, m.start()) + 1
            line_end = text_lower.find('\n', m.end())
            if line_end == -1:
                line_end = len(text_lower)
            line = text_lower[line_start:line_end].strip()
            if len(line.split()) <= 8:
                found.add(skill.title())
                break

    return sorted(found)



# ── NER Extractor ─────────────────────────────────────────────
def _ner_extract(text: str) -> list:
    """
    Run the trained spaCy NER model to extract SKILL entities.
    Returns skills in Title Case, deduplicated, sorted.
    """
    if _nlp is None:
        raise RuntimeError("NER model not initialized")
    doc = _nlp(text)
    found = set()
    for ent in doc.ents:
        if ent.label_ == "SKILL":
            found.add(ent.text.strip().lower())

    # Also run regex to catch any skills the model might have missed
    # (hybrid approach = best accuracy)
    regex_skills = {s.lower() for s in _regex_extract(text)}
    all_skills   = found | regex_skills

    return sorted({s.title() for s in all_skills})


# ── Public API ────────────────────────────────────────────────
def extract_skills(text: str) -> list[str]:
    """
    Extract all recognisable skills from raw resume text.

    Uses the trained spaCy NER model as the primary extractor,
    with a regex-boundary fallback for robustness.

    Args:
        text: Raw resume text (any case).

    Returns:
        List of skill strings in Title Case, sorted alphabetically.
    """
    _load_ner_model()

    if _ner_available and _nlp is not None:
        result = _ner_extract(text)
        method = "NER"
    else:
        result = _regex_extract(text)
        method = "Regex"

    logger.info(f"extract_skills [{method}]: found {len(result)} skills.")
    return result


def extract_skills_with_categories(text: str) -> dict[str, list[str]]:
    """
    Same as extract_skills(), but groups results by category.

    Returns:
        {
            'Programming Languages': ['Python', 'Java'],
            'Data Science & ML':     ['Machine Learning', 'NLP'],
            ...
        }
    """
    all_found = set(s.lower() for s in extract_skills(text))
    result    = {}

    for category, skills in SKILL_CATEGORIES.items():
        matched = [s.title() for s in skills if s.lower() in all_found]
        if matched:
            result[category] = sorted(matched)

    return result


def get_skill_gaps(candidate_skills: list[str], target_role: str) -> dict:
    """
    Compare candidate skills against the required skills for a job role.

    Args:
        candidate_skills: List of skills the candidate has (any case).
        target_role: Role name matching a key in JOB_ROLE_SKILLS.

    Returns:
        {
            'matched':  ['Python', 'SQL'],
            'missing':  ['Docker', 'Kubernetes'],
            'match_pct': 67
        }
    """
    required = JOB_ROLE_SKILLS.get(target_role, [])
    if not required:
        return {'matched': [], 'missing': [], 'match_pct': 0}

    candidate_lower = {s.lower() for s in candidate_skills}
    matched = [r for r in required if r.lower() in candidate_lower]
    missing = [r for r in required if r.lower() not in candidate_lower]
    match_pct = round(len(matched) / len(required) * 100) if required else 0

    return {
        'matched':   [s.title() for s in matched],
        'missing':   [s.title() for s in missing],
        'match_pct': match_pct
    }


def get_extraction_method() -> str:
    """Return whether the NER model or regex fallback is active."""
    _load_ner_model()
    return "spaCy NER (Trained Model)" if _ner_available else "Regex Fallback (Model not trained)"
