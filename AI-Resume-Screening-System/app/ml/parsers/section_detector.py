# ============================================================
#  HireAI — Resume Section Detector  (Task RI-02)
#
#  Single Responsibility:
#    Detects and segments raw resume text into 8 standardized
#    sections and captures custom/unrecognized section headings.
#    Preserves raw body text without modifying or normalizing it.
# ============================================================

import re
from typing import Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Standard Output Keys Contract
STANDARD_SECTION_KEYS = (
    "summary",
    "skills",
    "experience",
    "education",
    "projects",
    "certifications",
    "languages",
    "achievements",
)

# Configurable Heading Dictionary (Extensible & Maintainable)
SECTION_HEADERS = {
    "summary": [
        "summary", "profile", "objective", "about me", "career summary",
        "professional summary", "executive summary", "personal profile", "background", "overview",
        "career overview"
    ],
    "skills": [
        "skills", "technical skills", "core competencies", "technical expertise",
        "skills & abilities", "skills summary", "technologies", "tech stack",
        "areas of expertise", "key skills", "competencies", "primary skills", "skill set"
    ],
    "experience": [
        "experience", "work experience", "professional experience", "work history",
        "employment", "employment history", "career history", "work background",
        "internships", "internship experience", "relevant experience"
    ],
    "education": [
        "education", "academic background", "academic qualifications",
        "educational background", "qualifications", "academic profile", "education & training"
    ],
    "projects": [
        "projects", "key projects", "academic projects", "personal projects",
        "technical projects", "relevant projects", "software projects"
    ],
    "certifications": [
        "certifications", "licenses & certifications", "courses & certifications",
        "certificates", "professional certifications", "training & certifications"
    ],
    "languages": [
        "languages", "language proficiency", "languages known", "spoken languages"
    ],
    "achievements": [
        "achievements", "awards", "honors", "key achievements",
        "awards & recognition", "accomplishments", "honors & awards"
    ],
}

# Compile REGEX patterns from SECTION_HEADERS configuration
_COMPILED_PATTERNS = {}
for _key, _headers in SECTION_HEADERS.items():
    _escaped = [re.escape(h) for h in _headers]
    _pattern_str = r'^\s*(?:' + '|'.join(_escaped) + r')\s*[:\-]?\s*$'
    _COMPILED_PATTERNS[_key] = re.compile(_pattern_str, re.IGNORECASE)

_GENERIC_HEADER = re.compile(r'^\s*([A-Z][A-Za-z0-9\s&/\-]{2,45})\s*[:\-]?\s*$')


class SectionResult(dict):
    """
    Custom dictionary wrapper providing backward-compatible string access
    (e.g., res['skills'] -> 'Python, SQL') while exposing rich section metadata
    under res.section_details['skills'] or res['section_details'].
    """
    section_details: dict

    def __init__(self, raw_sections: dict, section_details: dict, unknown_sections: list):
        super().__init__(raw_sections)
        self["unknown_sections"] = unknown_sections
        self["section_details"] = section_details
        self.section_details = section_details

    def __getattr__(self, item: str) -> Any:
        if item == "section_details":
            return self.section_details
        try:
            return self[item]
        except KeyError:
            raise AttributeError(f"'SectionResult' object has no attribute '{item}'")


def detect_sections(text: str) -> dict:
    """
    Detect and segment raw resume text into standard sections with metadata & confidence.
    """
    raw_sections: dict[str, Any] = {k: "" for k in STANDARD_SECTION_KEYS}
    section_details: dict[str, Any] = {
        k: {
            "text": "",
            "confidence": 0.0,
            "detected_heading": "",
            "start_line": 0,
            "end_line": 0,
            "character_length": 0
        }
        for k in STANDARD_SECTION_KEYS
    }
    unknown_sections: list[dict[str, Any]] = []

    if not text or not text.strip():
        logger.warning("detect_sections received empty text.")
        return SectionResult(raw_sections, section_details, unknown_sections)

    lines = text.splitlines()

    # Step 1: Scan lines and identify heading boundaries
    section_blocks: list[dict[str, Any]] = []
    current_key = None
    current_heading = None
    current_confidence = 0.0
    current_start_line = 1
    current_lines = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped:
            if current_lines:
                current_lines.append("")
            continue

        matched_key, conf = _identify_header(stripped) if len(stripped) < 60 else (None, 0.0)

        if matched_key is not None:
            # Flush previous section block
            if current_lines or current_key or current_heading:
                section_blocks.append({
                    "key": current_key,
                    "heading": current_heading or stripped,
                    "confidence": current_confidence,
                    "start_line": current_start_line,
                    "end_line": max(current_start_line, idx - 1),
                    "text": "\n".join(current_lines).strip()
                })

            current_key = matched_key if matched_key != "unknown" else None
            current_heading = stripped
            current_confidence = conf
            current_start_line = idx + 1
            current_lines = []
        else:
            current_lines.append(line)

    # Flush final section block
    if current_lines or current_key or current_heading:
        section_blocks.append({
            "key": current_key,
            "heading": current_heading or "SUMMARY",
            "confidence": current_confidence,
            "start_line": current_start_line,
            "end_line": len(lines),
            "text": "\n".join(current_lines).strip()
        })

    # Step 2: Fallback for resumes with no headers
    headers_found = any(b["key"] is not None or (b["heading"] and float(b["confidence"]) > 0) for b in section_blocks)
    if not headers_found:
        raw_text = text.strip()
        raw_sections["summary"] = raw_text
        section_details["summary"] = {
            "text": raw_text,
            "confidence": 0.50,
            "detected_heading": "NONE",
            "start_line": 1,
            "end_line": len(lines),
            "character_length": len(raw_text)
        }
        return SectionResult(raw_sections, section_details, unknown_sections)

    # Step 3: Populate section dictionaries
    for block in section_blocks:
        key = block["key"]
        block_text = str(block["text"])
        heading = str(block["heading"])
        conf = float(block["confidence"])
        start_line = int(block["start_line"])
        end_line = int(block["end_line"])

        if not block_text:
            continue

        if key in STANDARD_SECTION_KEYS:
            if raw_sections[key]:
                raw_sections[key] += "\n\n" + block_text
                section_details[key]["text"] += "\n\n" + block_text
                section_details[key]["end_line"] = end_line
                section_details[key]["character_length"] = len(section_details[key]["text"])
            else:
                raw_sections[key] = block_text
                section_details[key] = {
                    "text": block_text,
                    "confidence": conf,
                    "detected_heading": heading,
                    "start_line": start_line,
                    "end_line": end_line,
                    "character_length": len(block_text)
                }
        elif heading and key is None:
            unknown_sections.append({
                "heading": heading,
                "text": block_text,
                "confidence": conf if conf > 0 else 0.70,
                "start_line": start_line,
                "end_line": end_line,
                "character_length": len(block_text)
            })
        elif not raw_sections["summary"]:
            raw_sections["summary"] = block_text
            section_details["summary"] = {
                "text": block_text,
                "confidence": 0.60,
                "detected_heading": "SUMMARY_HEADER_LESS",
                "start_line": start_line,
                "end_line": end_line,
                "character_length": len(block_text)
            }

    logger.info(
        f"Section detection complete: {[k for k in STANDARD_SECTION_KEYS if raw_sections[k]]} detected, "
        f"{len(unknown_sections)} custom sections."
    )
    return SectionResult(raw_sections, section_details, unknown_sections)


def _identify_header(line: str) -> tuple[str | None, float]:
    """Check if a single line matches standard or custom section header patterns."""
    cleaned = line.rstrip(":-").strip()
    if len(cleaned) < 2 or len(cleaned) > 50:
        return None, 0.0

    # Match standard configured headers
    for key, pattern in _COMPILED_PATTERNS.items():
        if pattern.match(line) or pattern.match(cleaned):
            return key, 1.0

    # Upper case custom header match (e.g. "PUBLICATIONS")
    if line.isupper() and len(cleaned) < 40 and not any(char in line for char in ".,;!?"):
        return "unknown", 0.80

    if _GENERIC_HEADER.match(line) and cleaned.endswith(":"):
        return "unknown", 0.75

    return None, 0.0

