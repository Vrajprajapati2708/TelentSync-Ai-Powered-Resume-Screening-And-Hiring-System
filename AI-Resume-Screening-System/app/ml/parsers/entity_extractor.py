# ============================================================
#  HireAI — Candidate Entity Extractor (Task RI-03)
#
#  Single Responsibility:
#    Extracts 9 structured candidate entities (Name, Email, Phone,
#    LinkedIn, GitHub, Portfolio, Address, City, Country) from text
#    with deterministic output, explicit confidence levels, and source tracking.
# ============================================================

import re
from typing import Any
from urllib.parse import urlparse
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Bounded Regex Patterns for Contact Extraction
_EMAIL_RE = re.compile(r'[\w\.\-+]+@[\w\-]+\.[a-z]{2,}', re.IGNORECASE)

# Phone Regexes (Indian +91, International formats)
_INDIAN_PHONE_RE = re.compile(
    r'(?:\+91[\-\s]?)?(?:[6-9]\d{9}|[6-9]\d{4}[\-\s]\d{5}|[6-9]\d{2}[\-\s]\d{3}[\-\s]\d{4})'
)
_INTL_PHONE_RE = re.compile(
    r'\+(?:[1-9]\d{0,2})[\-\s]?(?:\(\d{1,4}\)[\-\s]?)?\d{3,4}[\-\s]?\d{3,4}'
)
_STANDARD_US_PHONE_RE = re.compile(
    r'(?:\(\d{3}\)\s*|\d{3}[\-\.\s])\d{3}[\-\.\s]\d{4}'
)

# Social & Web Profile Regexes
_LINKEDIN_RE = re.compile(
    r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9\-_%]+)/?', re.IGNORECASE
)
_GITHUB_RE = re.compile(
    r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9\-_]+)/?', re.IGNORECASE
)
_URL_RE = re.compile(
    r'https?://[^\s<>"]+|www\.[^\s<>"]+|[a-zA-Z0-9\-]+\.(?:dev|io|me|site|tech|portfolio|app)(?:/[^\s<>"]*)?',
    re.IGNORECASE
)

# Non-Name Line Keywords (Section headers, titles, boilerplate to ignore in header name extraction)
_HEADER_TITLE_KEYWORDS = {
    "resume", "curriculum vitae", "cv", "software engineer", "developer",
    "senior developer", "full stack developer", "backend engineer",
    "frontend engineer", "data scientist", "machine learning engineer",
    "page 1", "page 2", "contact information", "profile", "summary",
    "experience", "work experience", "education", "skills", "projects",
    "certifications", "languages", "achievements", "personal details",
    "bio", "about me", "objective", "career summary"
}

# Known Common Cities Dictionary
_KNOWN_CITIES = {
    "bangalore", "bengaluru", "mumbai", "delhi", "new delhi", "hyderabad",
    "pune", "chennai", "kolkata", "ahmedabad", "gurgaon", "gurugram",
    "noida", "san francisco", "new york", "london", "seattle", "austin",
    "chicago", "boston", "toronto", "vancouver", "berlin", "paris",
    "singapore", "sydney", "melbourne", "tokyo", "dubai"
}

# Known Common Countries Dictionary
_KNOWN_COUNTRIES = {
    "india": "India",
    "united states": "United States",
    "usa": "United States",
    "us": "United States",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "canada": "Canada",
    "germany": "Germany",
    "france": "France",
    "australia": "Australia",
    "singapore": "Singapore",
    "japan": "Japan",
    "united arab emirates": "United Arab Emirates",
    "uae": "United Arab Emirates"
}

# Common Street Suffixes for Address Extraction
_ADDRESS_PATTERNS = re.compile(
    r'\b(?:\d{1,5}\s+[\w\s\.\-]{3,30}\s+(?:street|st|road|rd|avenue|ave|drive|dr|boulevard|blvd|lane|ln|way|court|ct|apartment|apt|suite|ste|block|sector|nagar|colony))\b',
    re.IGNORECASE
)

_GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
    "protonmail.com", "aol.com", "mail.com", "zoho.com"
}


def _make_entity(value: Any = None, source: str | None = None, confidence: float = 0.0) -> dict[str, Any]:
    """Helper to return standardized entity dict."""
    return {
        "value": value,
        "source": source,
        "confidence": confidence if value is not None else 0.0
    }


def extract_email(text: str) -> dict[str, Any]:
    """Extract candidate primary email address with whitespace & casing normalization."""
    if not text:
        return _make_entity()

    matches = _EMAIL_RE.findall(text)
    if not matches:
        return _make_entity()

    # Prioritize email found in top 15 lines (contact header)
    lines = text.splitlines()[:15]
    header_text = "\n".join(lines)
    header_matches = _EMAIL_RE.findall(header_text)

    if header_matches:
        raw_email = header_matches[0].strip().lower()
        return _make_entity(value=raw_email, source="header_regex", confidence=1.0)
    else:
        raw_email = matches[0].strip().lower()
        return _make_entity(value=raw_email, source="body_regex", confidence=0.90)


def extract_phone(text: str) -> dict[str, Any]:
    """
    Extract candidate phone number.
    Supports Indian +91 and International formats while avoiding dates, year ranges, ZIP codes, and CGPA values.
    """
    if not text:
        return _make_entity()

    lines = text.splitlines()[:20]
    header_text = "\n".join(lines)

    # Helper validator to reject dates/year ranges/CGPA
    def _is_valid_phone(p_str: str) -> bool:
        cleaned = re.sub(r'[^\d]', '', p_str)
        # Length check
        if len(cleaned) < 10 or len(cleaned) > 15:
            return False
        # False positive filtering: check year ranges e.g. 20182022
        if len(cleaned) == 8 and (cleaned.startswith("19") or cleaned.startswith("20")):
            return False
        # Avoid single repeated digits (e.g. 0000000000)
        if len(set(cleaned)) == 1:
            return False
        return True

    # Check Indian +91 format first
    ind_match = _INDIAN_PHONE_RE.search(header_text) or _INDIAN_PHONE_RE.search(text)
    if ind_match and _is_valid_phone(ind_match.group()):
        raw = ind_match.group().strip()
        cleaned_digits = re.sub(r'[^\d]', '', raw)
        if len(cleaned_digits) == 10:
            formatted = f"+91 {cleaned_digits[:5]} {cleaned_digits[5:]}"
        elif len(cleaned_digits) == 12 and cleaned_digits.startswith("91"):
            formatted = f"+91 {cleaned_digits[2:7]} {cleaned_digits[7:]}"
        else:
            formatted = raw
        return _make_entity(value=formatted, source="indian_phone_regex", confidence=0.95)

    # Check International format
    intl_match = _INTL_PHONE_RE.search(header_text) or _INTL_PHONE_RE.search(text)
    if intl_match and _is_valid_phone(intl_match.group()):
        raw = intl_match.group().strip()
        return _make_entity(value=raw, source="intl_phone_regex", confidence=0.90)

    # Check Standard US/other format
    us_match = _STANDARD_US_PHONE_RE.search(header_text) or _STANDARD_US_PHONE_RE.search(text)
    if us_match and _is_valid_phone(us_match.group()):
        raw = us_match.group().strip()
        return _make_entity(value=raw, source="standard_phone_regex", confidence=0.85)

    return _make_entity()


def extract_linkedin(text: str) -> dict[str, Any]:
    """
    Extract candidate LinkedIn profile URL.
    Ignores non-profile URLs such as /jobs, /company, /school.
    """
    if not text:
        return _make_entity()

    for match in _LINKEDIN_RE.finditer(text):
        username = match.group(1).rstrip('/')
        # Exclude non-profile subpaths
        if username.lower() in ("jobs", "company", "school", "feed", "learning", "pub"):
            continue
        normalized_url = f"https://www.linkedin.com/in/{username}"
        return _make_entity(value=normalized_url, source="linkedin_url_regex", confidence=1.0)

    return _make_entity()


def extract_github(text: str) -> dict[str, Any]:
    """
    Extract candidate GitHub profile URL.
    Ignores non-profile URLs such as /features, /pricing, /about.
    """
    if not text:
        return _make_entity()

    for match in _GITHUB_RE.finditer(text):
        username = match.group(1).rstrip('/')
        if username.lower() in ("features", "pricing", "about", "topics", "collections", "trending", "explore", "enterprise", "orgs"):
            continue
        normalized_url = f"https://github.com/{username}"
        return _make_entity(value=normalized_url, source="github_url_regex", confidence=1.0)

    return _make_entity()


def extract_portfolio(text: str, linkedin_url: str | None = None, github_url: str | None = None) -> dict[str, Any]:
    """
    Extract candidate personal portfolio/website URL.
    Distinguishes portfolio URLs from LinkedIn, GitHub, and generic email domains.
    """
    if not text:
        return _make_entity()

    matches = _URL_RE.findall(text)
    for raw_url in matches:
        raw_url = raw_url.rstrip('.,;)!?')
        # Normalize protocol
        if not raw_url.startswith(("http://", "https://")):
            url_with_scheme = "https://" + raw_url
        else:
            url_with_scheme = raw_url

        try:
            parsed = urlparse(url_with_scheme)
            domain = parsed.netloc.lower()
        except Exception:
            continue

        # Skip LinkedIn & GitHub
        if "linkedin.com" in domain or "github.com" in domain:
            continue
        # Skip generic email domains
        if domain in _GENERIC_EMAIL_DOMAINS or domain.replace("www.", "") in _GENERIC_EMAIL_DOMAINS:
            continue

        return _make_entity(value=url_with_scheme, source="portfolio_url_regex", confidence=0.85)

    return _make_entity()


def extract_name(text: str, email_val: str | None = None) -> dict[str, Any]:
    """
    Infer candidate name conservatively.
    Prioritizes top header lines while rejecting titles, section headings, and contact details.
    Falls back to email username if header text is ambiguous.
    """
    if not text:
        return _make_entity()

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    header_lines = lines[:10]

    for line in header_lines:
        line_clean = re.sub(r'[^\w\s\.\-]', '', line).strip()
        line_lower = line_clean.lower()

        # Reject if line contains digits
        if any(char.isdigit() for char in line_clean):
            continue
        # Reject if line contains @ or URL
        if "@" in line or "http" in line or "www." in line or ".com" in line:
            continue
        # Reject known header keywords & titles
        if line_lower in _HEADER_TITLE_KEYWORDS or any(kw == line_lower for kw in _HEADER_TITLE_KEYWORDS):
            continue
        # Check token count (candidate names are typically 2 to 4 words)
        tokens = line_clean.split()
        if 2 <= len(tokens) <= 4:
            # Verify tokens start with letters and look like a proper name
            if all(t[0].isalpha() for t in tokens):
                candidate_name = " ".join(t.capitalize() for t in tokens)
                return _make_entity(value=candidate_name, source="header_line", confidence=0.95)

    # Fallback to inferring from email username if email is available
    if email_val and "@" in email_val:
        username = email_val.split("@")[0]
        cleaned_user = re.sub(r'[\d_\.\-]+', ' ', username).strip()
        tokens = cleaned_user.split()
        if 1 <= len(tokens) <= 3:
            inferred_name = " ".join(t.capitalize() for t in tokens)
            return _make_entity(value=inferred_name, source="email_username_fallback", confidence=0.60)

    return _make_entity()


def extract_address(text: str) -> dict[str, Any]:
    """
    Extract candidate physical street address if sufficient evidence exists.
    Avoids inventing addresses from city/country names alone.
    """
    if not text:
        return _make_entity()

    lines = text.splitlines()[:20]
    header_text = "\n".join(lines)

    match = _ADDRESS_PATTERNS.search(header_text) or _ADDRESS_PATTERNS.search(text)
    if match:
        addr = match.group().strip()
        return _make_entity(value=addr, source="address_pattern", confidence=0.80)

    return _make_entity()


def extract_city(text: str) -> dict[str, Any]:
    """Extract candidate city if explicitly identifiable in header or document."""
    if not text:
        return _make_entity()

    lines = text.splitlines()[:20]
    header_text = "\n".join(lines).lower()
    full_text_lower = text.lower()

    for city in _KNOWN_CITIES:
        pattern = r'\b' + re.escape(city) + r'\b'
        if re.search(pattern, header_text):
            return _make_entity(value=city.title(), source="header_city_lookup", confidence=0.85)
        elif re.search(pattern, full_text_lower):
            return _make_entity(value=city.title(), source="body_city_lookup", confidence=0.75)

    return _make_entity()


def extract_country(text: str) -> dict[str, Any]:
    """Extract candidate country if explicitly identifiable in header or document."""
    if not text:
        return _make_entity()

    lines = text.splitlines()[:20]
    header_text = "\n".join(lines).lower()
    full_text_lower = text.lower()

    for country_key, canonical_name in _KNOWN_COUNTRIES.items():
        pattern = r'\b' + re.escape(country_key) + r'\b'
        if re.search(pattern, header_text):
            return _make_entity(value=canonical_name, source="header_country_lookup", confidence=0.90)
        elif re.search(pattern, full_text_lower):
            return _make_entity(value=canonical_name, source="body_country_lookup", confidence=0.80)

    return _make_entity()


def extract_candidate_entities(text: str, sections: dict | None = None) -> dict[str, dict[str, Any]]:
    """
    Main entry point for RI-03 Candidate Entity Extraction.
    Accepts raw or normalized resume text and optional RI-02 section dict.
    Returns structured candidate entities dictionary with value, source, and confidence for all 9 entities.
    """
    if not text:
        text = ""

    email_entity = extract_email(text)
    phone_entity = extract_phone(text)
    linkedin_entity = extract_linkedin(text)
    github_entity = extract_github(text)
    portfolio_entity = extract_portfolio(text, linkedin_entity["value"], github_entity["value"])
    name_entity = extract_name(text, email_entity["value"])
    address_entity = extract_address(text)
    city_entity = extract_city(text)
    country_entity = extract_country(text)

    result = {
        "name": name_entity,
        "email": email_entity,
        "phone": phone_entity,
        "linkedin": linkedin_entity,
        "github": github_entity,
        "portfolio": portfolio_entity,
        "address": address_entity,
        "city": city_entity,
        "country": country_entity
    }

    logger.info(
        f"Entity extraction complete: name={name_entity['value']}, "
        f"email={email_entity['value']}, phone={phone_entity['value']}"
    )

    return result
