# ============================================================
#  HireAI — Canonical Resume JSON Builder & Subsystem Orchestrator (Task RI-08)
#
#  Single Responsibility:
#    Orchestrates RI-01 through RI-07 modules to assemble one stable,
#    deterministic, canonical Resume Intelligence JSON document.
# ============================================================

from typing import Any
from app.ml.parsers.resume_parser import parse_document
from app.ml.parsers.section_detector import detect_sections
from app.ml.parsers.entity_extractor import extract_candidate_entities
from app.ml.skill_extraction.skill_intelligence import extract_skills_intelligence
from app.ml.parsers.experience_extractor import extract_experience
from app.ml.parsers.education_extractor import extract_education
from app.ml.analyzers.resume_quality_analyzer import analyze_resume_quality
from app.utils.logger import get_logger

logger = get_logger(__name__)

BUILDER_VERSION = "v1.0"


def _empty_canonical_doc(filename: str, errors: list[str]) -> dict[str, Any]:
    """Return a clean, schema-compliant canonical JSON document for failed parses."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
    return {
        "raw_text": "",
        "candidate": {
            "name": None
        },
        "contact": {
            "email": None,
            "phone": None,
            "linkedin": None,
            "github": None,
            "portfolio": None,
            "address": None,
            "city": None,
            "country": None
        },
        "sections": {
            "summary": "",
            "skills": "",
            "experience": "",
            "education": "",
            "projects": "",
            "certifications": "",
            "languages": "",
            "achievements": "",
            "unknown_sections": []
        },
        "skills": [],
        "experience": [],
        "total_experience_years": 0.0,
        "education": [],
        "certifications": [],
        "languages": [],
        "projects": [],
        "quality": {
            "quality_score": 0,
            "missing_sections": [
                "summary", "skills", "experience", "education",
                "projects", "certifications", "languages", "achievements"
            ],
            "resume_length": {
                "word_count": 0,
                "page_count": 0,
                "character_count": 0,
                "length_status": "short"
            },
            "contact_completeness": {
                "score": 0,
                "missing_fields": ["name", "email", "phone", "linkedin", "github", "portfolio"]
            },
            "section_coverage": {
                "present": 0,
                "expected": 8,
                "percentage": 0.0
            },
            "readability": {
                "score": 0,
                "average_sentence_words": 0.0,
                "long_sentence_count": 0,
                "very_long_line_count": 0
            },
            "formatting_indicators": {
                "excessive_blank_lines": False,
                "excessive_whitespace": False,
                "long_lines_detected": False,
                "section_structure_detected": False
            }
        },
        "metadata": {
            "parser_version": "v1.0",
            "file_type": ext,
            "parse_status": "failed",
            "parse_errors": errors,
            "builder_version": BUILDER_VERSION
        }
    }


def build_resume_intelligence(file_stream: Any, filename: str) -> dict[str, Any]:
    """
    Main orchestration entry point for Resume Intelligence v1.0.

    Pipeline:
      RI-01 (parse_document)
        ↓
      RI-02 (detect_sections)
        ↓
      RI-03 (extract_candidate_entities)
        ↓
      RI-04 (extract_skills_intelligence)
        ↓
      RI-05 (extract_experience)
        ↓
      RI-06 (extract_education)
        ↓
      RI-07 (analyze_resume_quality)
        ↓
      RI-08 (Canonical JSON Assembly)

    Returns:
        Structured canonical Resume Intelligence JSON dictionary matching contract.
    """
    if not filename:
        filename = "unknown.pdf"

    # ── Step 1: Document Parsing (RI-01)
    parsed_doc = parse_document(file_stream, filename)

    if not parsed_doc or not parsed_doc.get("success") or not parsed_doc.get("raw_text", "").strip():
        err_msg = parsed_doc.get("errors", ["Failed to extract text from file"]) if parsed_doc else ["Failed to parse file stream"]
        logger.warning(f"build_resume_intelligence: RI-01 parse failed for '{filename}'. Errors: {err_msg}")
        return _empty_canonical_doc(filename, err_msg)

    raw_text = parsed_doc["raw_text"]
    meta = parsed_doc.get("metadata", {})

    # ── Step 2: Section Detection (RI-02)
    sections_res = detect_sections(raw_text)
    sections_dict = {
        "summary": sections_res.get("summary", ""),
        "skills": sections_res.get("skills", ""),
        "experience": sections_res.get("experience", ""),
        "education": sections_res.get("education", ""),
        "projects": sections_res.get("projects", ""),
        "certifications": sections_res.get("certifications", ""),
        "languages": sections_res.get("languages", ""),
        "achievements": sections_res.get("achievements", ""),
        "unknown_sections": sections_res.get("unknown_sections", [])
    }

    # ── Step 3: Entity Extraction (RI-03)
    entities = extract_candidate_entities(raw_text, sections_dict)

    # ── Step 4: Skill Intelligence (RI-04)
    skills = extract_skills_intelligence(raw_text)

    # ── Step 5: Experience Intelligence (RI-05)
    exp_res = extract_experience(raw_text, sections_dict)

    # ── Step 6: Education Intelligence (RI-06)
    edu_res = extract_education(raw_text, sections_dict)

    # ── Step 7: Quality Analyzer (RI-07)
    quality_res = analyze_resume_quality(raw_text, sections_dict, entities, meta)

    # ── Step 8: Canonical JSON Assembly (RI-08)
    canonical = {
        "raw_text": raw_text,
        "candidate": {
            "name": entities["name"]["value"]
        },
        "contact": {
            "email": entities["email"]["value"],
            "phone": entities["phone"]["value"],
            "linkedin": entities["linkedin"]["value"],
            "github": entities["github"]["value"],
            "portfolio": entities["portfolio"]["value"],
            "address": entities["address"]["value"],
            "city": entities["city"]["value"],
            "country": entities["country"]["value"]
        },
        "sections": sections_dict,
        "skills": skills,
        "experience": exp_res.get("entries", []),
        "total_experience_years": exp_res.get("total_experience_years", 0.0),
        "education": edu_res.get("education", []),
        "certifications": edu_res.get("certifications", []),
        "languages": [],
        "projects": [],
        "quality": quality_res,
        "metadata": {
            "parser_name": meta.get("parser_name", "standard"),
            "parser_version": meta.get("parser_version", "v1.0"),
            "ocr_applied": meta.get("ocr_applied", False),
            "file_type": filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown",
            "parse_status": "success",
            "parse_errors": meta.get("parse_errors", []),
            "builder_version": BUILDER_VERSION
        }
    }

    logger.info(f"build_resume_intelligence complete for '{filename}': quality_score={quality_res['quality_score']}")
    return canonical
