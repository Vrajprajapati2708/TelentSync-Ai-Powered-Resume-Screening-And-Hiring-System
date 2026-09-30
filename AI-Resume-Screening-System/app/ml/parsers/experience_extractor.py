# ============================================================
#  HireAI — Candidate Experience Extractor (Task RI-05)
#
#  Single Responsibility:
#    Extracts structured work history records (Company, Job Title, Duration,
#    is_current_role, is_internship) and calculates non-overlapping
#    total experience years from resume text.
# ============================================================

import re
from datetime import datetime
from typing import Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Common Job Titles List (Sorted by length descending so longer titles match first)
_COMMON_JOB_TITLES = sorted([
    "software engineering intern", "data science intern", "machine learning intern",
    "senior software engineer", "principal software engineer", "full stack developer",
    "backend developer", "frontend developer", "software engineer",
    "python developer", "java developer", "data scientist", "data analyst",
    "machine learning engineer", "ml engineer", "nlp engineer",
    "data engineer", "devops engineer", "cloud architect",
    "system administrator", "product manager", "project manager",
    "tech lead", "technical lead", "engineering manager",
    "quality assurance engineer", "qa engineer", "software developer",
    "web developer", "intern", "trainee", "associate"
], key=len, reverse=True)

# Organization / Company Clues (Excluding general words like 'software')
_COMPANY_INDICATORS = re.compile(
    r'\b(?:inc|corp|corporation|ltd|limited|llc|pvt|private|technologies|tech|solutions|systems|services|labs|consulting)\b',
    re.IGNORECASE
)

_KNOWN_COMPANIES = {
    "google", "microsoft", "amazon", "apple", "meta", "facebook", "netflix",
    "tcs", "tata consultancy services", "infosys", "wipro", "cognizant",
    "accenture", "ibm", "oracle", "capgemini", "hcl", "tech mahindra",
    "uber", "airbnb", "adobe", "salesforce", "intel", "nvidia"
}

# Date Range Extraction Regex
_DATE_RANGE_RE = re.compile(
    r'\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2})[\/\s\.\-]*(\d{4}))\s*(?:\-|–|—|to)\s*((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2})[\/\s\.\-]*(\d{4})|Present|Current|Till Present|Now)\b',
    re.IGNORECASE
)

_YEAR_RANGE_RE = re.compile(
    r'\b(\d{4})\s*(?:\-|–|—|to)\s*(\d{4}|Present|Current|Till Present|Now)\b',
    re.IGNORECASE
)

_INTERNSHIP_RE = re.compile(r'\b(?:intern|internship|trainee|apprentice)\b', re.IGNORECASE)
_PRESENT_RE = re.compile(r'\b(?:present|current|till present|now)\b', re.IGNORECASE)

_MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12
}


def _parse_month_year(m_str: str, y_str: str) -> tuple[int, int]:
    """Parse month and year strings into (year, month)."""
    try:
        year = int(y_str)
    except ValueError:
        year = datetime.now().year

    month = 1
    if m_str:
        cleaned_m = m_str.strip().lower()
        if cleaned_m.isdigit():
            month = max(1, min(12, int(cleaned_m)))
        elif cleaned_m in _MONTH_MAP:
            month = _MONTH_MAP[cleaned_m]
    return year, month


def _extract_job_title(line: str) -> str | None:
    """Extract job title from text line using title dataset & regex patterns."""
    line_clean = re.sub(r'[\(\)]', ' ', line)
    line_lower = line_clean.lower()

    for title in _COMMON_JOB_TITLES:
        if re.search(r'\b' + re.escape(title) + r'\b', line_lower):
            return title.title()

    at_match = re.search(r'([a-zA-Z\s]{3,30})\s+(?:at|@)\s+', line_clean, re.IGNORECASE)
    if at_match:
        cand_title = at_match.group(1).strip()
        cand_lower = cand_title.lower()
        if cand_lower not in ("worked", "experience", "work history", "employment") and not any(c.isdigit() for c in cand_title):
            return cand_title.title()

    return None


def _extract_company_name(line: str) -> str | None:
    """Extract company name from text line using indicators or known company dataset."""
    # Strip parenthetical dates or text
    line_clean = re.sub(r'\([^\)]*\)', '', line)
    line_lower = line_clean.lower()

    # Pattern: Position title at/@ Company Name
    at_match = re.search(r'\b(?:at|@)\s+([^\n,;]{2,35})', line_clean, re.IGNORECASE)
    if at_match:
        comp_candidate = at_match.group(1).strip().rstrip('.,;')
        tokens = comp_candidate.split()
        if 1 <= len(tokens) <= 4:
            return comp_candidate.title()

    # Check known companies
    for known in _KNOWN_COMPANIES:
        if re.search(r'\b' + re.escape(known) + r'\b', line_lower):
            return known.title()

    # Check company indicator suffix (e.g. Acme Tech Inc)
    if _COMPANY_INDICATORS.search(line_clean):
        tokens = line_clean.split()
        for i, t in enumerate(tokens):
            if _COMPANY_INDICATORS.search(t):
                start_idx = max(0, i - 2)
                cand = " ".join(tokens[start_idx:i+1]).strip('.,;')
                cand_lower = cand.lower()
                if len(cand) >= 3 and cand_lower not in ("software engineer", "developer", "senior software engineer"):
                    return cand.title()

    return None


def _calculate_total_experience(intervals: list[tuple[datetime, datetime]]) -> float:
    """
    Calculate non-overlapping total experience years from date intervals.
    Merges overlapping time ranges to ensure experience is not double-counted.
    """
    if not intervals:
        return 0.0

    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged: list[tuple[datetime, datetime]] = []

    for current_start, current_end in sorted_intervals:
        if not merged:
            merged.append((current_start, current_end))
        else:
            prev_start, prev_end = merged[-1]
            if current_start <= prev_end:
                new_end = max(prev_end, current_end)
                merged[-1] = (prev_start, new_end)
            else:
                merged.append((current_start, current_end))

    total_days = sum((end - start).days for start, end in merged if end >= start)
    total_years = round(total_days / 365.25, 1)
    return max(0.0, total_years)


def extract_experience(text: str, section_dict: dict | None = None) -> dict[str, Any]:
    """
    Main entry point for RI-05 Candidate Experience Intelligence.
    Accepts raw resume text and optional RI-02 section dictionary.
    Returns structured list of experience entries and total experience years.
    """
    if not text:
        text = ""

    exp_text = text
    if section_dict and isinstance(section_dict, dict) and section_dict.get("experience"):
        exp_text = str(section_dict["experience"])

    lines = [l.strip() for l in exp_text.splitlines() if l.strip()]

    entries: list[dict[str, Any]] = []
    parsed_intervals: list[tuple[datetime, datetime]] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Ignore standard section header line if alone
        if line.lower() in ("experience", "work experience", "work history", "employment", "employment history"):
            i += 1
            continue

        date_match = _DATE_RANGE_RE.search(line) or _YEAR_RANGE_RE.search(line)
        job_title = _extract_job_title(line)
        company = _extract_company_name(line)
        is_intern = bool(_INTERNSHIP_RE.search(line))

        # Merge adjacent line if line 1 has title/company and line 2 has date range
        if not date_match and i + 1 < len(lines):
            next_line = lines[i+1]
            next_date = _DATE_RANGE_RE.search(next_line) or _YEAR_RANGE_RE.search(next_line)
            if next_date:
                date_match = next_date
                i += 1  # Consume next line date range

        duration_str = date_match.group(0).strip() if date_match else None
        is_current = bool(_PRESENT_RE.search(duration_str)) if duration_str else False

        # Parse interval for duration calculation
        if date_match:
            try:
                now = datetime.now()
                groups = date_match.groups()
                if len(groups) == 4:  # Month-Year format
                    y1, m1 = _parse_month_year(groups[0].split()[0] if ' ' in groups[0] else '', groups[1])
                    start_dt = datetime(y1, m1, 1)
                    if _PRESENT_RE.search(groups[2] or groups[3]):
                        end_dt = now
                    else:
                        y2, m2 = _parse_month_year(groups[2].split()[0] if ' ' in (groups[2] or '') else '', groups[3])
                        end_dt = datetime(y2, m2, 1)
                else:  # Standalone Year format
                    y1 = int(groups[0])
                    start_dt = datetime(y1, 1, 1)
                    if _PRESENT_RE.search(groups[1]):
                        end_dt = now
                    else:
                        y2 = int(groups[1])
                        end_dt = datetime(y2, 1, 1)

                if end_dt >= start_dt:
                    parsed_intervals.append((start_dt, end_dt))
            except Exception as e:
                logger.debug(f"Date interval parse error: {e}")

        if company or job_title or duration_str:
            entry = {
                "company": company,
                "job_title": job_title,
                "duration": duration_str,
                "is_current_role": is_current,
                "is_internship": is_intern
            }
            entries.append(entry)

        i += 1

    total_years = _calculate_total_experience(parsed_intervals)

    result = {
        "entries": entries,
        "total_experience_years": total_years
    }

    logger.info(f"extract_experience complete: {len(entries)} entries found, total_years={total_years}")
    return result
