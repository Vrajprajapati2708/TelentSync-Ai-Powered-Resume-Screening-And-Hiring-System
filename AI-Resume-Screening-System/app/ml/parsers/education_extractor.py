# ============================================================
#  HireAI — Candidate Education Intelligence (Task RI-06)
#
#  Single Responsibility:
#    Extracts structured education history records (Degree, Institution,
#    Passing Year, CGPA, Percentage) and Certifications from resume text.
# ============================================================

import re
from typing import Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Degree Canonical Mapping
_DEGREE_CANONICAL_MAP: dict[str, str] = {
    "b.tech": "B.Tech",
    "b tech": "B.Tech",
    "btech": "B.Tech",
    "b.e.": "B.E.",
    "b.e": "B.E.",
    "be": "B.E.",
    "bachelor of technology": "B.Tech",
    "bachelor of engineering": "B.E.",
    "m.tech": "M.Tech",
    "m tech": "M.Tech",
    "mtech": "M.Tech",
    "m.e.": "M.E.",
    "m.e": "M.E.",
    "master of technology": "M.Tech",
    "master of engineering": "M.E.",
    "bca": "BCA",
    "bachelor of computer applications": "BCA",
    "mca": "MCA",
    "master of computer applications": "MCA",
    "b.sc": "B.Sc",
    "bsc": "B.Sc",
    "bachelor of science": "B.Sc",
    "m.sc": "M.Sc",
    "msc": "M.Sc",
    "master of science": "M.Sc",
    "bba": "BBA",
    "bachelor of business administration": "BBA",
    "mba": "MBA",
    "master of business administration": "MBA",
    "b.com": "B.Com",
    "bcom": "B.Com",
    "bachelor of commerce": "B.Com",
    "m.com": "M.Com",
    "mcom": "M.Com",
    "master of commerce": "M.Com",
    "phd": "PhD",
    "ph.d": "PhD",
    "doctor of philosophy": "PhD",
    "diploma": "Diploma",
    "12th": "12th",
    "higher secondary": "12th",
    "hsc": "12th",
    "10th": "10th",
    "secondary": "10th",
    "ssc": "10th"
}

# Regex for Institution Recognition (including French/international spelling)
_INSTITUTION_INDICATORS = re.compile(
    r'\b(?:university|université|universite|college|institute|institut|school|academy|iit|nit|iiit)\b',
    re.IGNORECASE
)

# Regex for CGPA & Percentage
_CGPA_RE = re.compile(
    r'\b(?:cgpa|gpa)[\s:]*([0-9]\.[0-9]{1,2})\b|\b([0-9]\.[0-9]{1,2})\s*(?:\/\s*10|\/\s*4\.0|cgpa|gpa)\b',
    re.IGNORECASE
)
_PERCENTAGE_RE = re.compile(
    r'\b(\d{2}(?:\.\d{1,2})?)\s*%|\bpercentage[\s:]*(\d{2}(?:\.\d{1,2})?)\b',
    re.IGNORECASE
)

# Regex for Passing Year
_YEAR_RE = re.compile(r'\b(19[89]\d|20[0-3]\d)\b')
_ONGOING_RE = re.compile(r'\b(?:present|ongoing|pursuing|current)\b', re.IGNORECASE)

# Certification Keywords
_CERT_KEYWORDS = re.compile(
    r'\b(?:certified|certification|certificate|aws|azure|google|nielit|coursera|udemy|oracle|cisco)\b',
    re.IGNORECASE
)


def _canonicalize_degree(raw_degree: str) -> str:
    """Normalize raw degree string into canonical degree name."""
    cleaned = raw_degree.strip().lower()
    if cleaned in _DEGREE_CANONICAL_MAP:
        return _DEGREE_CANONICAL_MAP[cleaned]
    return raw_degree.strip().title()


def _format_institution_name(raw_name: str) -> str:
    """Format institution name while preserving acronyms (e.g. JG, ABC, IIT)."""
    tokens = raw_name.strip().split()
    formatted = []
    for t in tokens:
        if t.isupper() and len(t) <= 4:
            formatted.append(t)
        elif t.lower() in ("of", "and", "de", "des", "the", "for", "in"):
            formatted.append(t.lower())
        else:
            formatted.append(t.capitalize())
    return " ".join(formatted)


def _extract_institution(line: str) -> str | None:
    """Extract university/college/institution name from line if present."""
    line_clean = line.strip().rstrip('.,;')
    from_match = re.search(r'\b(?:from|at)\s+(.+)', line_clean, re.IGNORECASE)
    if from_match:
        line_clean = from_match.group(1).strip()

    if _INSTITUTION_INDICATORS.search(line_clean):
        tokens = line_clean.split(',')
        for t in tokens:
            if _INSTITUTION_INDICATORS.search(t):
                cand = t.strip()
                if 4 <= len(cand) <= 60 and not any(kw in cand.lower() for kw in ("b.tech", "m.tech", "bca", "mca")):
                    return _format_institution_name(cand)
        return _format_institution_name(line_clean)
    return None


def _extract_cgpa(line: str) -> str | None:
    """Extract normalized CGPA string (e.g. '8.3') from line."""
    match = _CGPA_RE.search(line)
    if match:
        val = match.group(1) or match.group(2)
        if val:
            return val.strip()
    return None


def _extract_percentage(line: str) -> str | None:
    """Extract normalized Percentage string (e.g. '85%') from line."""
    match = _PERCENTAGE_RE.search(line)
    if match:
        val = match.group(1) or match.group(2)
        if val:
            return f"{val.strip()}%"
    return None


def _extract_passing_year(line: str) -> str | None:
    """Extract passing year string (e.g. '2026') or None if ongoing/pursuing."""
    if _ONGOING_RE.search(line):
        return None
    matches = _YEAR_RE.findall(line)
    if matches:
        return matches[-1]
    return None


def extract_certifications(text: str, section_dict: dict | None = None) -> list[str]:
    """Extract list of explicit certification titles."""
    cert_text = text
    if section_dict and isinstance(section_dict, dict) and section_dict.get("certifications"):
        cert_text = str(section_dict["certifications"])

    certs: list[str] = []
    lines = [l.strip() for l in cert_text.splitlines() if l.strip()]

    for line in lines:
        if line.lower() in ("certifications", "certification", "licenses & certifications"):
            continue
        if _CERT_KEYWORDS.search(line) or "certificate" in line.lower():
            clean_cert = line.strip("•-* ").strip()
            if 5 <= len(clean_cert) <= 80 and not any(d in clean_cert.lower() for d in ("b.tech", "m.tech", "bca", "mca")):
                certs.append(clean_cert)

    return sorted(list(dict.fromkeys(certs)))


def _find_degree_in_line(line: str) -> str | None:
    for deg_key in _DEGREE_CANONICAL_MAP:
        pattern = r'\b' + re.escape(deg_key) + r'\b'
        if re.search(pattern, line, re.IGNORECASE):
            return _canonicalize_degree(deg_key)
    return None


def extract_education(text: str, section_dict: dict | None = None) -> dict[str, Any]:
    """
    Main entry point for RI-06 Candidate Education Intelligence.
    Accepts raw resume text and optional RI-02 section dictionary.
    Returns structured list of education records and list of certifications.
    """
    if not text:
        text = ""

    edu_text = text
    if section_dict and isinstance(section_dict, dict) and section_dict.get("education"):
        edu_text = str(section_dict["education"])

    lines = [l.strip() for l in edu_text.splitlines() if l.strip()]

    education_entries: list[dict[str, Any]] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.lower() in ("education", "academic background", "qualifications", "academics"):
            i += 1
            continue

        found_degree = _find_degree_in_line(line)
        inst = _extract_institution(line)
        year = _extract_passing_year(line)
        cgpa = _extract_cgpa(line)
        pct = _extract_percentage(line)

        j = i + 1
        while j < len(lines) and j <= i + 2:
            next_line = lines[j]
            next_degree = _find_degree_in_line(next_line)
            if next_degree:
                break

            next_inst = _extract_institution(next_line)
            next_year = _extract_passing_year(next_line)
            next_cgpa = _extract_cgpa(next_line)
            next_pct = _extract_percentage(next_line)

            if next_inst or next_year or next_cgpa or next_pct:
                inst = inst or next_inst
                year = year or next_year
                cgpa = cgpa or next_cgpa
                pct = pct or next_pct
                i = j
            j += 1

        if found_degree or inst or year or cgpa or pct:
            entry = {
                "degree": found_degree,
                "institution": inst,
                "passing_year": year,
                "cgpa": cgpa,
                "percentage": pct
            }
            education_entries.append(entry)

        i += 1

    certifications_list = extract_certifications(text, section_dict)

    result = {
        "education": education_entries,
        "certifications": certifications_list
    }

    logger.info(
        f"extract_education complete: {len(education_entries)} education records, "
        f"{len(certifications_list)} certifications found."
    )
    return result
