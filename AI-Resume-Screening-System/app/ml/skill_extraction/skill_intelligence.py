# ============================================================
#  HireAI — Skill Intelligence Engine (Task RI-04)
#
#  Single Responsibility:
#    Extracts, normalizes, categorizes, deduplicates, and scores candidate
#    skills using spaCy NER, regex/dictionary matching, and deterministic alias mapping.
# ============================================================

import re
from typing import Any
from app.ml.skill_extraction.skills_db import SKILL_CATEGORIES, ALL_SKILLS
from app.ml.skill_extraction.extract_skills import _load_ner_model, _nlp, _ner_available, _regex_extract
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Alias Mapping to Canonical Skill Names
SKILL_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "reactjs": "React",
    "react.js": "React",
    "react": "React",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "vue": "Vue.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "py": "Python",
    "python": "Python",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "golang": "Go",
    "go": "Go",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "dl": "Deep Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "powerbi": "Power BI",
    "power bi": "Power BI",
    "sklearn": "Scikit-Learn",
    "scikit-learn": "Scikit-Learn",
    "scikit learn": "Scikit-Learn",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "html": "HTML",
    "css": "CSS",
    "sql": "SQL",
    "nosql": "MongoDB",
    "cpp": "C++",
    "c++": "C++",
    "c#": "C#",
    "c sharp": "C#",
}

# Category Lookup Table (Canonical Skill Name -> Category)
_SKILL_TO_CATEGORY: dict[str, str] = {}
for category_name, skill_list in SKILL_CATEGORIES.items():
    for s in skill_list:
        _SKILL_TO_CATEGORY[s.lower()] = category_name

# Add explicit category overrides for canonical aliases
_SKILL_TO_CATEGORY.update({
    "javascript": "Web & Frameworks",
    "typescript": "Web & Frameworks",
    "node.js": "Web & Frameworks",
    "react": "Web & Frameworks",
    "vue.js": "Web & Frameworks",
    "postgresql": "Databases",
    "python": "Programming Languages",
    "kubernetes": "Cloud & DevOps",
    "go": "Programming Languages",
    "machine learning": "Data Science & ML",
    "deep learning": "Data Science & ML",
    "nlp": "Data Science & ML",
    "power bi": "BI & Analytics",
    "scikit-learn": "ML Libraries",
    "aws": "Cloud & DevOps",
    "gcp": "Cloud & DevOps",
    "azure": "Cloud & DevOps",
    "html": "Web & Frameworks",
    "css": "Web & Frameworks",
    "sql": "Databases",
    "c++": "Programming Languages",
    "c#": "Programming Languages",
})


def _canonicalize_skill(raw_skill: str) -> tuple[str, bool]:
    """
    Map raw skill string to canonical skill name and return whether alias mapping was applied.
    Returns: (canonical_name, is_alias)
    """
    cleaned = raw_skill.strip().lower()
    if cleaned in SKILL_ALIASES:
        canonical = SKILL_ALIASES[cleaned]
        is_alias = (cleaned != canonical.lower())
        return canonical, is_alias
    
    # Try exact match against ALL_SKILLS
    for db_skill in ALL_SKILLS:
        if db_skill.lower() == cleaned:
            return db_skill.title(), False

    # Default title casing
    return raw_skill.strip().title(), False


def _get_skill_category(canonical_name: str) -> str:
    """Determine category for a canonical skill name."""
    name_lower = canonical_name.lower()
    if name_lower in _SKILL_TO_CATEGORY:
        return _SKILL_TO_CATEGORY[name_lower]
    return "Other Skills"


def extract_skills_intelligence(text: str) -> list[dict[str, Any]]:
    """
    Main entry point for RI-04 Skill Intelligence Engine.
    Extracts, normalizes, categorizes, deduplicates, and scores candidate skills.

    Returns list of normalized skill objects:
    [
        {
            "name": "Python",
            "category": "Programming Languages",
            "confidence": 0.95,
            "source": "spacy_ner"
        }
    ]
    """
    if not text or not text.strip():
        logger.info("extract_skills_intelligence: Empty text provided.")
        return []

    _load_ner_model()

    extracted_map: dict[str, dict[str, Any]] = {}

    def _add_or_update_skill(name: str, confidence: float, source: str):
        canonical, is_alias = _canonicalize_skill(name)
        if not canonical:
            return

        # Adjust confidence slightly for alias match
        effective_conf = round(confidence - 0.05 if is_alias else confidence, 2)
        category = _get_skill_category(canonical)

        if canonical not in extracted_map:
            extracted_map[canonical] = {
                "name": canonical,
                "category": category,
                "confidence": effective_conf,
                "source": source
            }
        else:
            # Deduplicate by keeping the entry with higher confidence / stronger source
            existing = extracted_map[canonical]
            if effective_conf > existing["confidence"]:
                extracted_map[canonical] = {
                    "name": canonical,
                    "category": category,
                    "confidence": effective_conf,
                    "source": source
                }

    # ── Phase 1: spaCy NER Extraction
    if _ner_available and _nlp is not None:
        try:
            doc = _nlp(text)
            for ent in doc.ents:
                if ent.label_ == "SKILL":
                    _add_or_update_skill(ent.text, confidence=0.95, source="spacy_ner")
        except Exception as e:
            logger.error(f"spaCy NER extraction error: {e}")

    # ── Phase 2: Regex / Dictionary Fallback Extraction
    regex_raw_skills = _regex_extract(text)
    for raw_s in regex_raw_skills:
        _add_or_update_skill(raw_s, confidence=0.85, source="regex_dictionary")

    # ── Phase 3: Explicit Alias Regex Scan (for JS, TS, K8s, Postgres, etc.)
    text_lower = text.lower()
    for alias_key, canonical_val in SKILL_ALIASES.items():
        if alias_key in ("c", "r"):  # skip single-letter false positive aliases unless bound
            continue
        pattern = r'\b' + re.escape(alias_key) + r'\b'
        if re.search(pattern, text_lower):
            _add_or_update_skill(alias_key, confidence=0.80, source="alias_match")

    # Sort results by category, then skill name deterministically
    sorted_skills = sorted(
        extracted_map.values(),
        key=lambda x: (x["category"], x["name"])
    )

    logger.info(f"extract_skills_intelligence complete: extracted {len(sorted_skills)} canonical skills.")
    return sorted_skills
