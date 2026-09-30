# ============================================================
#  TalentSync — Input Validators
# ============================================================

import re

# Whitelisted application statuses — prevents arbitrary strings in the DB
ALLOWED_STATUSES = {'Shortlisted', 'Reviewing', 'Pending', 'Rejected'}

# Whitelisted user roles — prevents privilege escalation
ALLOWED_ROLES = {'candidate', 'hr'}


def validate_email(email: str) -> bool:
    pattern = r'^[\w\.\-]+@[\w\-]+\.[a-z]{2,}$'
    return bool(re.match(pattern, email.strip(), re.I)) if email else False


MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128


def validate_password(password: str) -> tuple:
    """Returns (is_valid, error_message). Enforces configurable min/max lengths."""
    if not password:
        return False, "Password is required."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Password must not exceed {MAX_PASSWORD_LENGTH} characters."
    return True, ""


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
PDF_MAGIC_BYTES = b'%PDF-'
DOCX_MAGIC_BYTES = b'PK\x03\x04'


def validate_file_extension(filename: str, allowed: set | None = None) -> bool:
    """Check if filename extension is in the allowed whitelist (defaults to pdf, docx)."""
    if allowed is None:
        allowed = ALLOWED_EXTENSIONS
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in allowed


def validate_file_bytes(file_stream, filename: str) -> tuple:
    """
    Validate uploaded file stream for extension, 10MB size ceiling,
    empty file checks, and magic-byte header inspection.
    Returns (is_valid, error_message).
    """
    if not filename or not file_stream:
        return False, "File and filename are required."

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    # 1. Extension check
    if not validate_file_extension(filename):
        if ext == 'doc':
            return False, "Legacy binary .doc files are not supported. Please save your file as .docx or .pdf."
        return False, f"Unsupported file extension '.{ext}'. Allowed formats: .pdf, .docx"

    # 2. File size check
    file_stream.seek(0, 2)  # Seek to end
    size = file_stream.tell()
    file_stream.seek(0)     # Reset to beginning

    if size == 0:
        return False, "Uploaded file is empty (0 bytes)."

    if size > MAX_FILE_SIZE_BYTES:
        size_mb = round(size / (1024 * 1024), 1)
        return False, f"File size ({size_mb}MB) exceeds maximum allowed limit of 10MB."

    # 3. Magic-byte signature inspection
    header = file_stream.read(16)
    file_stream.seek(0)  # Reset pointer for parser

    if ext == 'pdf':
        if not header.startswith(b'%PDF-'):
            return False, "File header magic-bytes do not match PDF specification. File may be corrupted or spoofed."
    elif ext == 'docx':
        if not header.startswith(b'PK\x03\x04'):
            return False, "File header magic-bytes do not match Word DOCX specification. File may be corrupted or spoofed."

    return True, ""


def validate_required_fields(data: dict, required: list) -> tuple:
    """Check that all required keys are present and non-empty."""
    for field in required:
        if not data.get(field):
            return False, f"'{field}' is required."
    return True, ""


def validate_status(status: str) -> bool:
    """Check that a status value is in the allowed whitelist."""
    return status in ALLOWED_STATUSES


def validate_role(role: str) -> bool:
    """Check that a role value is in the allowed whitelist."""
    return role in ALLOWED_ROLES


def sanitize_text(value: str, max_length: int = 1000) -> str:
    """Trim and truncate a text field to prevent oversized payloads."""
    if not value:
        return ''
    return value.strip()[:max_length]


def validate_external_apply_url(url: str) -> tuple:
    """
    Validates external job application URL for security (GAP-07):
    - Must be a non-empty string.
    - Must use HTTPS scheme.
    - Must have a valid public domain name.
    - Rejects localhost, 127.0.0.1, private RFC-1918 IPs, IPv6 local addresses.
    - Rejects javascript:, data:, file:, vbscript:, and control/CRLF characters.
    Returns (is_valid, error_message).
    """
    import urllib.parse
    import ipaddress

    if not url or not isinstance(url, str):
        return False, "External application URL is required."

    if any(c in url for c in ['\r', '\n', '\t', '\0']):
        return False, "URL contains illegal whitespace or control characters."

    url = url.strip()
    if not url:
        return False, "External application URL is required."

    if ' ' in url:
        return False, "URL contains illegal whitespace or control characters."

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False, "Malformed URL."

    if parsed.scheme.lower() != 'https':
        return False, "External application URL must use secure HTTPS protocol."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must include a valid host name."

    hostname = hostname.lower().strip()

    # Reject localhost / loopbacks
    if hostname in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
        return False, "Localhost redirects are forbidden."

    # Check if host is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            return False, "Private network redirects are forbidden."
    except ValueError:
        pass

    # Must contain at least one dot and valid domain formatting
    if '.' not in hostname or hostname.startswith('.') or hostname.endswith('.'):
        return False, "Invalid domain name in URL."

    # Prevent disallowed URI schemes embedded in payload
    lowered_full = url.lower()
    if any(s in lowered_full for s in ['javascript:', 'data:', 'vbscript:', 'file:']):
        return False, "Disallowed URI scheme detected."

    return True, ""
