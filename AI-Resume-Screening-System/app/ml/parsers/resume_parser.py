# ============================================================
#  TalentSync — Resume Parser (Orchestrator)
#  Decides which parser to use based on file extension,
#  then extracts structured data (skills, email, name, etc.)
#  from the raw text.
# ============================================================

import re
from app.ml.parsers.pdf_parser import extract_pdf_with_metadata, extract_text_from_pdf
from app.ml.parsers.docx_parser import extract_docx_with_metadata, extract_text_from_docx
from app.ml.skill_extraction.extract_skills import extract_skills, extract_skills_with_categories
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Regex patterns for personal info extraction (legacy compat) ──
_EMAIL_RE    = re.compile(r'[\w\.\-]+@[\w\-]+\.[a-z]{2,}', re.I)
_PHONE_RE    = re.compile(r'(?:\+91[\-\s]?)?[6-9]\d{9}|(?:\(\d{3}\)\s*|\d{3}[\-\.])\d{3}[\-\.]\d{4}')
_LINKEDIN_RE = re.compile(r'linkedin\.com/in/[\w\-]+', re.I)
_GITHUB_RE   = re.compile(r'github\.com/[\w\-]+', re.I)
_CGPA_RE     = re.compile(r'(?:cgpa|gpa|grade)[:\s]*([0-9]\.[0-9]{1,2})', re.I)

_DEGREE_KEYWORDS = [
    'b.tech', 'b.e.', 'b.sc', 'bca', 'm.tech', 'm.e.', 'm.sc', 'mca',
    'mba', 'phd', 'bachelor', 'master', 'diploma', 'b.com', 'm.com'
]
_EXP_KEYWORDS = ['intern', 'engineer', 'analyst', 'developer', 'scientist', 'manager', 'associate']



def parse_document(file, filename: str) -> dict:
    """
    Standardized Resume Parser Engine (RI-01).
    Extracts text and metadata without inferring entities or candidate information.
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if hasattr(file, 'seek'):
        file.seek(0)

    try:
        if ext == 'pdf':
            return extract_pdf_with_metadata(file, filename=filename)
        elif ext == 'docx':
            return extract_docx_with_metadata(file, filename=filename)
        else:
            logger.warning(f"Unsupported file extension: .{ext}")
            return {
                'success': False,
                'raw_text': '',
                'metadata': {
                    'file_name': filename,
                    'file_size_bytes': 0,
                    'page_count': 0,
                    'word_count': 0,
                    'character_count': 0,
                    'language': 'en',
                    'parser_name': 'none',
                    'parser_version': 'v1.0',
                    'parse_status': 'failed',
                    'parse_errors': [f"Unsupported file extension '.{ext}'. Allowed formats: .pdf, .docx"]
                },
                'errors': [f"Unsupported file extension '.{ext}'. Allowed formats: .pdf, .docx"]
            }
    except Exception as e:
        logger.error(f"Parser exception in parse_document: {e}")
        return {
            'success': False,
            'raw_text': '',
            'metadata': {
                'file_name': filename,
                'file_size_bytes': 0,
                'page_count': 0,
                'word_count': 0,
                'character_count': 0,
                'language': 'en',
                'parser_name': 'none',
                'parser_version': 'v1.0',
                'parse_status': 'failed',
                'parse_errors': [str(e)]
            },
            'errors': [str(e)]
        }


def parse_resume(file, filename: str) -> dict:
    """
    Main entry point for resume parsing.
    Accepts a file object and filename, returns a structured dict with parse_error tracking.
    Backward-compatible with legacy structure while exposing RI-01 metadata.
    """
    parsed_doc = parse_document(file, filename)

    if not parsed_doc['success'] or not parsed_doc['raw_text'].strip():
        err_msg = parsed_doc['errors'][0] if parsed_doc['errors'] else "Could not extract text from resume."
        return _empty_result(error=err_msg, metadata=parsed_doc.get('metadata'))

    raw_text = parsed_doc['raw_text']

    # ── Step 2: Extract structured fields (legacy compat)
    result = {
        'raw_text':          raw_text,
        'email':             _extract_email(raw_text),
        'phone':             _extract_phone(raw_text),
        'linkedin':          _extract_linkedin(raw_text),
        'github':            _extract_github(raw_text),
        'cgpa':              _extract_cgpa(raw_text),
        'degree':            _extract_degree(raw_text),
        'skills':            extract_skills(raw_text),
        'skill_categories':  extract_skills_with_categories(raw_text),
        'experience_lines':  _extract_experience(raw_text),
        'parse_error':       '',
        'metadata':          parsed_doc['metadata']
    }

    logger.info(f"Resume parsed: {len(result['skills'])} skills, email={result['email']}")
    return result



# ── Private helper functions ──────────────────────────────────

def _extract_email(text: str) -> str:
    match = _EMAIL_RE.search(text)
    return match.group() if match else ''


def _extract_phone(text: str) -> str:
    match = _PHONE_RE.search(text)
    return match.group() if match else ''


def _extract_linkedin(text: str) -> str:
    match = _LINKEDIN_RE.search(text)
    return match.group() if match else ''


def _extract_github(text: str) -> str:
    match = _GITHUB_RE.search(text)
    return match.group() if match else ''


def _extract_cgpa(text: str) -> str:
    match = _CGPA_RE.search(text)
    return match.group(1) if match else ''


def _extract_degree(text: str) -> str:
    text_lower = text.lower()
    for degree in _DEGREE_KEYWORDS:
        if degree in text_lower:
            return degree.upper()
    return ''


def _extract_experience(text: str) -> list[str]:
    """Return lines that likely describe work experience."""
    lines = text.split('\n')
    exp_lines = []
    for line in lines:
        line = line.strip()
        if any(kw in line.lower() for kw in _EXP_KEYWORDS) and len(line) > 15:
            exp_lines.append(line)
    return exp_lines[:10]   # Return top 10 relevant lines


def _empty_result(error: str = "Parsing failed.", metadata: dict | None = None) -> dict:
    return {
        'raw_text': '', 'email': '', 'phone': '', 'linkedin': '',
        'github': '', 'cgpa': '', 'degree': '', 'skills': [],
        'skill_categories': {}, 'experience_lines': [],
        'parse_error': error,
        'metadata': metadata or {
            'file_name': '', 'file_size_bytes': 0, 'page_count': 0,
            'word_count': 0, 'character_count': 0, 'language': 'en',
            'parser_name': 'none', 'parser_version': 'v1.0',
            'parse_status': 'failed', 'parse_errors': [error]
        }
    }


