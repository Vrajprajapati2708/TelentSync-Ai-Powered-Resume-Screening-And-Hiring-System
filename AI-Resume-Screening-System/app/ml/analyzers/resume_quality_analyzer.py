# ============================================================
#  HireAI — Resume Quality & Completeness Analyzer (Task RI-07)
#
#  Single Responsibility:
#    Analyzes resume text, section data, contact entities, and metadata
#    to compute deterministic completeness, readability, formatting,
#    and quality metrics without mutating input data or overwriting ATS scores.
# ============================================================

import re
from typing import Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Standard RI-02 Expected Sections
_EXPECTED_SECTIONS = [
    "summary",
    "skills",
    "experience",
    "education",
    "projects",
    "certifications",
    "languages",
    "achievements"
]

# Contact Fields Evaluated for Completeness
_CONTACT_FIELDS = [
    "name",
    "email",
    "phone",
    "linkedin",
    "github",
    "portfolio"
]


def _evaluate_missing_and_coverage(sections: dict | None) -> tuple[list[str], dict[str, Any]]:
    """Determine missing sections and section coverage statistics."""
    if not sections or not isinstance(sections, dict):
        return _EXPECTED_SECTIONS.copy(), {
            "present": 0,
            "expected": len(_EXPECTED_SECTIONS),
            "percentage": 0.0
        }

    missing: list[str] = []
    present_count = 0

    for sec in _EXPECTED_SECTIONS:
        sec_val = sections.get(sec)
        if sec_val and str(sec_val).strip():
            present_count += 1
        else:
            missing.append(sec)

    pct = round((present_count / len(_EXPECTED_SECTIONS)) * 100.0, 1)
    coverage = {
        "present": present_count,
        "expected": len(_EXPECTED_SECTIONS),
        "percentage": pct
    }
    return missing, coverage


def _evaluate_length_status(word_count: int, page_count: int) -> str:
    """Categorize length status using deterministic thresholds."""
    if word_count < 150 or (page_count == 1 and word_count < 100):
        return "short"
    elif word_count > 1200 or page_count > 4:
        return "excessive"
    return "good"


def _evaluate_resume_length(text: str, metadata: dict | None) -> dict[str, Any]:
    """Calculate word, page, character counts and length status."""
    if not text:
        text = ""

    if metadata and isinstance(metadata, dict):
        word_count = metadata.get("word_count", len(text.split()))
        page_count = metadata.get("page_count", 1)
        char_count = metadata.get("character_count", len(text))
    else:
        word_count = len(text.split())
        page_count = 1
        char_count = len(text)

    status = _evaluate_length_status(word_count, page_count)

    return {
        "word_count": word_count,
        "page_count": page_count,
        "character_count": char_count,
        "length_status": status
    }


def _evaluate_contact_completeness(contact: dict | None) -> dict[str, Any]:
    """Calculate contact completeness score and identify missing contact fields."""
    if not contact or not isinstance(contact, dict):
        return {
            "score": 0,
            "missing_fields": _CONTACT_FIELDS.copy()
        }

    missing: list[str] = []
    present_count = 0

    for field in _CONTACT_FIELDS:
        val = contact.get(field)
        # Support both plain values and RI-03 entity dicts {"value": "..."}
        if isinstance(val, dict):
            field_val = val.get("value")
        else:
            field_val = val

        if field_val and str(field_val).strip():
            present_count += 1
        else:
            missing.append(field)

    score = round((present_count / len(_CONTACT_FIELDS)) * 100)
    return {
        "score": score,
        "missing_fields": missing
    }


def _evaluate_readability(text: str) -> dict[str, Any]:
    """Analyze sentence length, line density, and readability score."""
    if not text or not text.strip():
        return {
            "score": 0,
            "average_sentence_words": 0.0,
            "long_sentence_count": 0,
            "very_long_line_count": 0
        }

    # Sentence splitting
    sentences = [s.strip() for s in re.split(r'[\.\!\?\n]+', text) if s.strip()]
    total_words = len(text.split())
    sentence_count = len(sentences) or 1
    avg_sentence_words = round(total_words / sentence_count, 1)

    long_sentence_count = sum(1 for s in sentences if len(s.split()) > 30)

    # Line analysis
    lines = text.splitlines()
    very_long_line_count = sum(1 for l in lines if len(l) > 120)

    # Base readability score calculation
    readability_pts = 100
    if avg_sentence_words > 25:
        readability_pts -= 15
    if long_sentence_count > 3:
        readability_pts -= 10
    if very_long_line_count > 2:
        readability_pts -= 10

    score = max(0, min(100, readability_pts))

    return {
        "score": score,
        "average_sentence_words": avg_sentence_words,
        "long_sentence_count": long_sentence_count,
        "very_long_line_count": very_long_line_count
    }


def _evaluate_formatting_indicators(text: str, sections: dict | None) -> dict[str, bool]:
    """Identify text-level formatting indicators."""
    if not text:
        return {
            "excessive_blank_lines": False,
            "excessive_whitespace": False,
            "long_lines_detected": False,
            "section_structure_detected": False
        }

    excessive_blank_lines = bool(re.search(r'\n{4,}', text))
    excessive_whitespace = bool(re.search(r'[ \t]{5,}', text))
    long_lines_detected = any(len(l) > 120 for l in text.splitlines())
    section_structure_detected = bool(sections and any(v for v in sections.values() if v))

    return {
        "excessive_blank_lines": excessive_blank_lines,
        "excessive_whitespace": excessive_whitespace,
        "long_lines_detected": long_lines_detected,
        "section_structure_detected": section_structure_detected
    }


def analyze_resume_quality(
    text: str,
    sections: dict | None = None,
    contact: dict | None = None,
    metadata: dict | None = None
) -> dict[str, Any]:
    """
    Main entry point for RI-07 Resume Quality & Completeness Analyzer.
    Analyzes completeness, length, contact info, section coverage, readability, and formatting.
    Returns a deterministic, non-mutating report dictionary with quality_score (0-100).
    """
    if text is None:
        text = ""

    missing_sections, section_coverage = _evaluate_missing_and_coverage(sections)
    resume_length = _evaluate_resume_length(text, metadata)
    contact_completeness = _evaluate_contact_completeness(contact)
    readability = _evaluate_readability(text)
    formatting_indicators = _evaluate_formatting_indicators(text, sections)

    # ── Weighted Quality Score Calculation ───────────────────
    # Weights:
    #   Section Coverage      : 35%
    #   Contact Completeness  : 25%
    #   Readability           : 20%
    #   Length Status         : 10%
    #   Formatting Structure  : 10%

    cov_score = section_coverage["percentage"]
    cont_score = contact_completeness["score"]
    read_score = readability["score"]

    length_pts = 100 if resume_length["length_status"] == "good" else (50 if resume_length["length_status"] == "short" else 40)
    format_pts = 100 if formatting_indicators["section_structure_detected"] and not formatting_indicators["excessive_blank_lines"] else 60

    if not text.strip():
        overall_score = 0
    else:
        weighted = (
            (cov_score * 0.35) +
            (cont_score * 0.25) +
            (read_score * 0.20) +
            (length_pts * 0.10) +
            (format_pts * 0.10)
        )
        overall_score = max(0, min(100, round(weighted)))

    result = {
        "quality_score": overall_score,
        "missing_sections": missing_sections,
        "resume_length": resume_length,
        "contact_completeness": contact_completeness,
        "section_coverage": section_coverage,
        "readability": readability,
        "formatting_indicators": formatting_indicators
    }

    logger.info(f"analyze_resume_quality complete: quality_score={overall_score}/100")
    return result
