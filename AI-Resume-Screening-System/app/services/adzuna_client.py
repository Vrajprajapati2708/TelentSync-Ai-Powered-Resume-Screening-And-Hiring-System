"""
Adzuna Client — Resilient, Caching, and Normalized API Integration
TalentSync (HireAI) Live Jobs Aggregator
"""

import os
import re
import time
import copy
import html
import hashlib
import requests
import threading
import concurrent.futures
from typing import Dict, Any, List, Tuple, Optional, cast
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config.settings import ActiveConfig
from app.utils.logger import get_logger
from app.ml.skill_extraction.skills_db import JOB_ROLE_SKILLS

logger = get_logger(__name__)


# ── Custom Exceptions ───────────────────────────────────────────
class AdzunaError(Exception):
    """Base exception for all Adzuna integration errors."""
    pass


class AdzunaConfigError(AdzunaError):
    """Raised when Adzuna API credentials or configuration are missing/invalid."""
    pass


class AdzunaAuthError(AdzunaError):
    """Raised when Adzuna returns HTTP 401 or 403 (Invalid credentials)."""
    pass


class AdzunaRateLimitError(AdzunaError):
    """Raised when Adzuna returns HTTP 429 (Rate limit reached)."""
    pass


class AdzunaTimeoutError(AdzunaError):
    """Raised when Adzuna request times out."""
    pass


class AdzunaUpstreamError(AdzunaError):
    """Raised when Adzuna returns HTTP 5xx or bad gateway / malformed response."""
    pass


# ── Regex Heuristics ─────────────────────────────────────────────
EXP_RANGE_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(?:-|to|–|—)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)', re.I)
EXP_MIN_PATTERN = re.compile(r'(?:min(?:imum)?|at least|\b)\s*(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)', re.I)
EXP_REQ_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)(?:\s+(?:of\s+)?experience|\s+exp|\s+relevant|\s+required)', re.I)
FRESHER_PATTERN = re.compile(r'\b(fresher|freshers|entry[- ]?level|intern|internship|trainee|no experience)\b', re.I)

REMOTE_PATTERN = re.compile(r'\b(remote|work from home|wfh|telecommute)\b', re.I)
HYBRID_PATTERN = re.compile(r'\b(hybrid)\b', re.I)

from app.ml.skill_extraction.skills_db import ALL_SKILLS, JOB_ROLE_SKILLS

CANONICAL_SKILL_MAP: Dict[str, str] = {
    'python': 'Python', 'java': 'Java', 'c++': 'C++', 'c#': 'C#', 'c': 'C',
    'javascript': 'JavaScript', 'typescript': 'TypeScript', 'r': 'R', 'scala': 'Scala',
    'kotlin': 'Kotlin', 'swift': 'Swift', 'go': 'Go', 'rust': 'Rust', 'ruby': 'Ruby', 'php': 'PHP',
    'html': 'HTML', 'css': 'CSS', 'react': 'React', 'angular': 'Angular', 'vue.js': 'Vue.js',
    'node.js': 'Node.js', 'flask': 'Flask', 'django': 'Django', 'fastapi': 'FastAPI',
    'express': 'Express', 'spring': 'Spring', 'laravel': 'Laravel', 'bootstrap': 'Bootstrap',
    'tailwind': 'Tailwind', 'machine learning': 'Machine Learning', 'deep learning': 'Deep Learning',
    'nlp': 'NLP', 'natural language processing': 'Natural Language Processing',
    'computer vision': 'Computer Vision', 'data science': 'Data Science', 'statistics': 'Statistics',
    'data analysis': 'Data Analysis', 'data mining': 'Data Mining', 'feature engineering': 'Feature Engineering',
    'model deployment': 'Model Deployment', 'a/b testing': 'A/B Testing', 'time series': 'Time Series',
    'reinforcement learning': 'Reinforcement Learning', 'pandas': 'Pandas', 'numpy': 'NumPy',
    'scikit-learn': 'Scikit-learn', 'tensorflow': 'TensorFlow', 'pytorch': 'PyTorch', 'keras': 'Keras',
    'xgboost': 'XGBoost', 'lightgbm': 'LightGBM', 'opencv': 'OpenCV', 'nltk': 'NLTK', 'spacy': 'spaCy',
    'hugging face': 'Hugging Face', 'transformers': 'Transformers', 'langchain': 'LangChain',
    'matplotlib': 'Matplotlib', 'seaborn': 'Seaborn', 'plotly': 'Plotly', 'sql': 'SQL',
    'mysql': 'MySQL', 'postgresql': 'PostgreSQL', 'mongodb': 'MongoDB', 'redis': 'Redis',
    'sqlite': 'SQLite', 'cassandra': 'Cassandra', 'elasticsearch': 'Elasticsearch', 'oracle': 'Oracle',
    'firebase': 'Firebase', 'dynamodb': 'DynamoDB', 'aws': 'AWS', 'azure': 'Azure', 'gcp': 'GCP',
    'docker': 'Docker', 'kubernetes': 'Kubernetes', 'terraform': 'Terraform', 'jenkins': 'Jenkins',
    'ci/cd': 'CI/CD', 'github actions': 'GitHub Actions', 'ansible': 'Ansible', 'linux': 'Linux',
    'git': 'Git', 'tableau': 'Tableau', 'power bi': 'Power BI', 'excel': 'Excel', 'looker': 'Looker',
    'qlik': 'Qlik', 'metabase': 'Metabase', 'google analytics': 'Google Analytics', 'hadoop': 'Hadoop',
    'spark': 'Spark', 'hive': 'Hive', 'kafka': 'Kafka'
}

# Precompile skill word-boundary patterns sorted by descending length
_COMPILED_SKILL_PATTERNS: List[Tuple[str, re.Pattern]] = []
for _s in sorted(ALL_SKILLS, key=len, reverse=True):
    _s_clean = _s.strip()
    _canonical = CANONICAL_SKILL_MAP.get(_s_clean.lower(), _s_clean.title() if len(_s_clean) > 3 else _s_clean.upper())
    if _s_clean in ('c', 'r'):
        _p = re.compile(rf'\b{_s_clean}\b', re.IGNORECASE)
    else:
        _p = re.compile(rf'(?<![\w#+]){re.escape(_s_clean)}(?![\w#+])', re.IGNORECASE)
    _COMPILED_SKILL_PATTERNS.append((_canonical, _p))


class AdzunaClient:
    """
    Production-grade client for the Adzuna Jobs Search API (India endpoint).
    Provides in-memory TTL caching, automatic exponential backoff retries,
    safe dictionary parsing, experience/work-mode extraction, and structured diagnostics.
    """

    def __init__(self):
        # 1. Load configuration from settings / environment
        self.app_id = (os.getenv("ADZUNA_APP_ID") or getattr(ActiveConfig, 'ADZUNA_APP_ID', '') or '').strip()
        self.app_key = (os.getenv("ADZUNA_APP_KEY") or getattr(ActiveConfig, 'ADZUNA_APP_KEY', '') or '').strip()
        self.country = (os.getenv("ADZUNA_COUNTRY") or getattr(ActiveConfig, 'ADZUNA_COUNTRY', 'in') or 'in').strip().lower()
        
        # Timeout & TTL
        raw_timeout = os.getenv("ADZUNA_TIMEOUT") or getattr(ActiveConfig, 'PROVIDER_TIMEOUT', 8)
        try:
            self.timeout = float(raw_timeout)
        except (ValueError, TypeError):
            self.timeout = 8.0

        self.single_flight_timeout: Optional[float] = None
        self.pool_timeout: Optional[float] = None

        raw_ttl = os.getenv("ADZUNA_CACHE_TTL", "600")
        try:
            self.cache_ttl = int(raw_ttl)
        except (ValueError, TypeError):
            self.cache_ttl = 600

        raw_max = os.getenv("ADZUNA_CACHE_MAX", "500")
        try:
            self.cache_max = max(1, int(raw_max))
        except (ValueError, TypeError):
            self.cache_max = 500

        self.base_url = f"https://api.adzuna.com/v1/api/jobs/{self.country}/search"
        self._cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self._inflight: Dict[str, concurrent.futures.Future] = {}
        self._call_counter: Dict[str, Any] = {
            'total': 0,
            'hourly': {},
            'daily': {}
        }
        self._lock = threading.Lock()

        # 2. Check credentials on instantiation
        if not self.app_id or not self.app_key:
            logger.warning(
                "CRITICAL: Adzuna API credentials missing! ADZUNA_APP_ID or ADZUNA_APP_KEY not set. "
                "Live jobs will fall back to local database."
            )
        else:
            id_prefix = self.app_id[:3] + "..." if len(self.app_id) >= 3 else "***"
            key_prefix = self.app_key[:3] + "..." if len(self.app_key) >= 3 else "***"
            logger.info(f"AdzunaClient initialized (country={self.country}, app_id={id_prefix}, app_key={key_prefix}, timeout={self.timeout}s)")

        # 3. Setup requests.Session with connection pooling & retries
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TalentSync/2.0 (Live Job Aggregator; +https://talentsync.ai)",
            "Accept": "application/json"
        })
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
            respect_retry_after_header=False
        )
        adapter = HTTPAdapter(max_retries=cast(Any, retry_strategy))
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _evict_cache_locked(self, now: float, key_to_add: Optional[str] = None) -> None:
        """
        Enforces self.cache_max cap.
        Evicts expired entries first (older than 1 hour / 3600s),
        preserving entries needed for stale-while-error (up to 1 hour).
        If still full, evicts the oldest entries.
        Must be called while holding self._lock.
        """
        if key_to_add and key_to_add in self._cache:
            return
        if len(self._cache) < self.cache_max:
            return

        # 1. Evict expired entries older than 1 hour (3600s), oldest first
        expired = [k for k, (ts, _) in self._cache.items() if (now - ts) >= 3600]
        if expired:
            expired.sort(key=lambda k: self._cache[k][0])
            for k in expired:
                self._cache.pop(k, None)
                if len(self._cache) < self.cache_max:
                    return

        # 2. If still full, evict the oldest entries
        if len(self._cache) >= self.cache_max:
            sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])
            for k in sorted_keys:
                self._cache.pop(k, None)
                if len(self._cache) < self.cache_max:
                    break

    def evict_cache(self, now: Optional[float] = None) -> None:
        """Thread-safe public cache eviction."""
        if now is None:
            now = time.time()
        with self._lock:
            self._evict_cache_locked(now)

    def is_configured(self) -> bool:
        """Returns True if app_id and app_key are present."""
        return bool(self.app_id and self.app_key)

    def extract_experience_hint(self, text: str) -> Optional[str]:
        """Extract user-readable experience hint (e.g. '0-1 yrs', '3-5 yrs') or None."""
        if not text:
            return None
        if FRESHER_PATTERN.search(text):
            return "0-1 yrs"
        m_range = EXP_RANGE_PATTERN.search(text)
        if m_range:
            return f"{m_range.group(1)}-{m_range.group(2)} yrs"
        m_min = EXP_MIN_PATTERN.search(text)
        if m_min:
            return f"{m_min.group(1)}+ yrs"
        m_req = EXP_REQ_PATTERN.search(text)
        if m_req:
            return f"{m_req.group(1)}+ yrs"
        return None

    def detect_work_mode(self, text: str) -> str:
        """Detect remote, hybrid, or onsite from job text."""
        if not text:
            return "onsite"
        if REMOTE_PATTERN.search(text):
            return "remote"
        if HYBRID_PATTERN.search(text):
            return "hybrid"
        return "onsite"

    def format_salary_display(self, salary_min: int, salary_max: int) -> str:
        """Format salary nicely as INR or LPA."""
        if salary_min > 0 and salary_max > 0:
            if salary_min >= 100000:
                lpa_min = round(salary_min / 100000.0, 1)
                lpa_max = round(salary_max / 100000.0, 1)
                return f"₹{lpa_min:g} LPA" if lpa_min == lpa_max else f"₹{lpa_min:g} - ₹{lpa_max:g} LPA"
            return f"₹{salary_min:,} - ₹{salary_max:,}"
        elif salary_min > 0:
            if salary_min >= 100000:
                return f"₹{round(salary_min / 100000.0, 1):g}L+ PA"
            return f"₹{salary_min:,}+"
        return "Not disclosed"

    def extract_skills(self, text: str) -> List[str]:
        """
        Extract recognizable skills from title and description using word-boundary matching.
        Returns a sorted list of matched skills with canonical formatting.
        """
        if not text:
            return []
        found = set()
        for canonical_name, pattern in _COMPILED_SKILL_PATTERNS:
            if pattern.search(text):
                found.add(canonical_name)
        return sorted(found)

    @staticmethod
    def parse_structured_hints(text: str) -> Dict[str, Any]:
        """
        Parse structured hints from raw job text:
        - Job Role
        - YOE (Years of experience)
        - NP (Notice period)
        - Location
        - Work Model
        """
        if not text:
            return {}
        hints = {}

        # Job Role
        m_role = re.search(r'(?:Job Role|Job Title|Role)\s*:\s*([^:\n\r]+?)(?=(?:YOE|Years of Experience|Experience|Exp|NP|Notice Period|Location|Work Model|Work Mode|Job Description|Position Overview|\n|$))', text, re.I)
        if m_role:
            hints['job_role'] = m_role.group(1).strip()

        # YOE
        m_yoe = re.search(r'(?:YOE|Years of Experience|Experience|Exp)\s*:\s*([^:\n\r]+?)(?=(?:NP|Notice Period|Location|Work Model|Work Mode|Job Description|Position Overview|\n|$))', text, re.I)
        if m_yoe:
            hints['yoe'] = m_yoe.group(1).strip()

        # NP (Notice Period)
        m_np = re.search(r'(?:NP|Notice Period)\s*:\s*([^:\n\r]+?)(?=(?:Location|Work Model|Work Mode|Job Description|Position Overview|YOE|Years of Experience|\n|$))', text, re.I)
        if m_np:
            hints['np'] = m_np.group(1).strip()

        # Location
        m_loc = re.search(r'(?:Location)\s*:\s*([^:\n\r]+?)(?=(?:Work Model|Work Mode|Job Description|Position Overview|YOE|NP|Notice Period|\n|$))', text, re.I)
        if m_loc:
            hints['location'] = m_loc.group(1).strip()

        # Work Model
        m_wm = re.search(r'(?:Work Model|Work Mode|Workplace Type)\s*:\s*([^:\n\r]+?)(?=(?:Job Description|Position Overview|Job Role|Job Title|YOE|NP|Location|\n|$))', text, re.I)
        if m_wm:
            hints['work_model'] = m_wm.group(1).strip()

        return hints

    @staticmethod
    def clean_description_snippet(text: str, max_chars: int = 220) -> str:
        """
        Clean display snippet:
        - Strip HTML entities and tags
        - Remove label noise like 'Job Role:', 'YOE:', 'NP:', 'Location:', 'Job Title:', etc.
        - Collapse whitespace
        - Cut at word boundary (~220 chars) with '…'
        """
        if not text:
            return ""

        # 1. Unescape HTML entities & strip HTML tags
        clean = html.unescape(text)
        clean = re.sub(r'<[^>]+>', ' ', clean)

        # 2. Remove label noise
        noise_pattern = re.compile(
            r'\b(?:Job Role|Job Title|YOE|NP|Notice Period|Location|Work Model|Work Mode|Job Description|Position Overview)\s*:\s*',
            re.I
        )
        clean = noise_pattern.sub(' ', clean)

        # 3. Collapse whitespace
        clean = ' '.join(clean.split()).strip()

        # 4. Cut at word boundary (~220 chars) with '…'
        if len(clean) <= max_chars:
            return clean

        truncated = clean[:max_chars]
        if ' ' in truncated:
            truncated = truncated.rsplit(' ', 1)[0]
        return truncated.rstrip('.,;:- ') + '…'

    @staticmethod
    def clean_full_description(text: str) -> str:
        """Strip HTML tags and unescape entities for safe full display."""
        if not text:
            return ""
        clean = html.unescape(text)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        return ' '.join(clean.split()).strip()

    @staticmethod
    def parse_experience_years(text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Parse numeric min/max experience years and formatted hint string.
        Returns (min_years, max_years, hint_str).
        """
        if not text:
            return None, None, None

        if FRESHER_PATTERN.search(text):
            return 0.0, 1.0, "0-1 yrs"

        m_range = EXP_RANGE_PATTERN.search(text)
        if m_range:
            y1 = float(m_range.group(1))
            y2 = float(m_range.group(2))
            min_y = min(y1, y2)
            max_y = max(y1, y2)
            fmt_min = int(min_y) if min_y.is_integer() else min_y
            fmt_max = int(max_y) if max_y.is_integer() else max_y
            return min_y, max_y, f"{fmt_min}-{fmt_max} yrs"

        m_min = EXP_MIN_PATTERN.search(text)
        if m_min:
            y = float(m_min.group(1))
            fmt_y = int(y) if y.is_integer() else y
            return y, y + 2.0, f"{fmt_y}+ yrs"

        m_req = EXP_REQ_PATTERN.search(text)
        if m_req:
            y = float(m_req.group(1))
            fmt_y = int(y) if y.is_integer() else y
            return y, y + 2.0, f"{fmt_y}+ yrs"

        return None, None, None

    @staticmethod
    def parse_city_and_location(raw_loc: Any, text: str = "") -> Tuple[str, str]:
        """
        Extract normalized location and specific city:
        - Use Adzuna location.area array (most specific)
        - Fallback to city parsed from text ('Location: Bangalore', etc.)
        - Normalizes Bangalore -> Bengaluru
        - Stops showing just 'India' when a city is available.
        """
        CITY_NORMALIZE = {
            "bangalore": "Bengaluru",
            "bengaluru": "Bengaluru",
            "bombay": "Mumbai",
            "mumbai": "Mumbai",
            "calcutta": "Kolkata",
            "kolkata": "Kolkata",
            "madras": "Chennai",
            "chennai": "Chennai",
            "gurgaon": "Gurugram",
            "gurugram": "Gurugram",
            "hyderabad": "Hyderabad",
            "pune": "Pune",
            "delhi": "Delhi",
            "noida": "Noida",
            "ahmedabad": "Ahmedabad",
            "jaipur": "Jaipur",
            "kochi": "Kochi",
            "chandigarh": "Chandigarh",
            "indore": "Indore"
        }

        area = []
        display_name = ""
        if isinstance(raw_loc, dict):
            area = raw_loc.get('area') or []
            display_name = str(raw_loc.get('display_name') or '').strip()
        elif isinstance(raw_loc, str):
            display_name = raw_loc.strip()

        # Filter out generic country names from area
        specific_areas = [
            a.strip() for a in area
            if a and a.strip().lower() not in ('india', 'uk', 'us', 'usa', 'united states')
        ]

        city = ""
        location = ""

        if specific_areas:
            raw_city = specific_areas[-1]
            city = CITY_NORMALIZE.get(raw_city.lower(), raw_city)
            if len(specific_areas) >= 2:
                state = specific_areas[-2]
                location = f"{city}, {state}"
            else:
                location = city
        elif display_name and display_name.lower() != 'india':
            location = display_name
            for old_c, norm_c in CITY_NORMALIZE.items():
                if re.search(rf'\b{old_c}\b', display_name, re.I):
                    city = norm_c
                    break

        # Fallback to text parsing if location is empty or generic 'India'
        if not city or location.lower() in ('', 'india'):
            m_loc = re.search(r'(?:Location)\s*:\s*([^:\n\r,;]+)', text, re.I)
            if m_loc:
                raw_extracted = m_loc.group(1).strip()
                cities_found = []
                for part in re.split(r'[/,]', raw_extracted):
                    p_clean = part.strip()
                    if p_clean:
                        norm = CITY_NORMALIZE.get(p_clean.lower(), p_clean)
                        cities_found.append(norm)
                if cities_found:
                    city = cities_found[0]
                    location = " / ".join(cities_found)

            if not city:
                for old_c, norm_c in CITY_NORMALIZE.items():
                    if re.search(rf'\b{old_c}\b', text, re.I):
                        city = norm_c
                        location = norm_c
                        break

        if not location:
            location = "India"

        return location, city

    @staticmethod
    def format_relative_date(created_str: str) -> str:
        """Format ISO date string as relative time, e.g. 'Posted 3 days ago'."""
        if not created_str:
            return "Recently posted"
        try:
            dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
            diff = now - dt
            days = diff.days
            if days <= 0:
                return "Posted today"
            elif days == 1:
                return "Posted 1 day ago"
            elif days < 7:
                return f"Posted {days} days ago"
            elif days < 30:
                weeks = max(1, days // 7)
                return f"Posted {weeks} week{'s' if weeks > 1 else ''} ago"
            else:
                months = max(1, days // 30)
                return f"Posted {months} month{'s' if months > 1 else ''} ago"
        except Exception:
            return "Recently posted"

    def _normalize(self, raw: dict) -> Optional[Dict[str, Any]]:
        """Safely convert raw Adzuna job payload into standard schema."""
        if not isinstance(raw, dict):
            return None

        job_id = str(raw.get('id') or '').strip()
        if not job_id:
            return None

        apply_url = str(raw.get('redirect_url') or '').strip()
        if not apply_url:
            logger.warning(f"Adzuna job {job_id} has no redirect_url")

        title = str(raw.get('title') or 'Job Opening').strip()
        company_obj = raw.get('company') or {}
        company = (company_obj.get('display_name') or 'Confidential Company').strip() if isinstance(company_obj, dict) else 'Confidential Company'

        desc = str(raw.get('description') or '').strip()

        # Parse structured hints from description first
        structured_hints = self.parse_structured_hints(desc)
        combined_text = f"{title} {desc}"

        # Clean snippet (~220 chars with '…') & full description
        snippet = self.clean_description_snippet(desc, max_chars=220)
        clean_desc = self.clean_full_description(desc)

        # Location & City (stops showing just 'India' when city is available)
        loc_obj = raw.get('location') or {}
        location, city = self.parse_city_and_location(loc_obj, text=combined_text)

        # Work Mode
        work_mode = structured_hints.get('work_model')
        if work_mode:
            work_mode = self.detect_work_mode(work_mode)
        else:
            work_mode = self.detect_work_mode(f"{title} {location} {clean_desc}")

        # Experience parsing (numeric min/max + hint)
        exp_target_text = structured_hints.get('yoe') or combined_text
        e_min, e_max, exp_hint = self.parse_experience_years(exp_target_text)
        if not exp_hint:
            exp_hint = self.extract_experience_hint(combined_text)

        # Skills extraction
        extracted_skills = self.extract_skills(f"{title} {clean_desc}")
        skills_str = ", ".join(extracted_skills)

        # Salary display
        salary_min = int(raw.get('salary_min') or 0)
        salary_max = int(raw.get('salary_max') or salary_min)
        salary_display = self.format_salary_display(salary_min, salary_max)

        contract_time = str(raw.get('contract_time') or 'full_time').replace('_', ' ').title()
        posted_at = str(raw.get('created') or datetime.now().isoformat())
        posted_relative = self.format_relative_date(posted_at)

        return {
            'id': f"adzuna_{job_id}",
            'raw_id': job_id,
            'source_job_id': job_id,
            'title': title,
            'company': company,
            'location': location,
            'city': city,
            'work_mode': work_mode,
            'type': contract_time,
            'salary_min': salary_min,
            'salary_max': salary_max,
            'salary_display': salary_display,
            'experience_min': e_min,
            'experience_max': e_max,
            'experience_hint': exp_hint,
            'description_snippet': snippet,
            'description': clean_desc,
            'posted_at': posted_at,
            'posted_relative': posted_relative,
            'source': 'adzuna',
            'is_external': True,
            'external_apply_url': apply_url if apply_url else None,
            'apply_url': apply_url,
            'skills': skills_str,
            'match_score': 50,
            'matched_skills': []
        }

    def search(
        self,
        q: str = "",
        location: str = "",
        salary_min: int = 0,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "relevance"
    ) -> List[Dict[str, Any]]:
        """
        Executes a live Adzuna search with parameter validation, caching, and error mapping.
        """
        if not self.is_configured():
            logger.warning("Adzuna search requested but credentials not configured.")
            raise AdzunaConfigError("Adzuna credentials missing from environment.")

        # Clamp and sanitize
        q = (q or "").strip()[:100]
        location = (location or "").strip()[:100]
        page = max(1, page)
        per_page = min(50, max(1, per_page))
        salary_min = max(0, salary_min)
        
        # Sort mapping
        sort_map = {'relevance': 'relevance', 'newest': 'date', 'salary': 'salary'}
        adzuna_sort = sort_map.get(sort_by.lower(), 'relevance')

        # Cache key
        cache_key = hashlib.md5(
            f"{self.country}|{q.lower()}|{location.lower()}|{salary_min}|{page}|{per_page}|{adzuna_sort}".encode('utf-8')
        ).hexdigest()

        now = time.time()
        with self._lock:
            # 1. Fast path: fresh cache hit
            cached_entry = self._cache.get(cache_key)
            if cached_entry:
                ts, cached_jobs = cached_entry
                if now - ts < self.cache_ttl:
                    logger.info(f"Adzuna cache hit for key: {cache_key} ({len(cached_jobs)} jobs)")
                    return [copy.deepcopy(j) for j in cached_jobs]

            # 2. Single-flight: check if an identical query is already in-flight
            if cache_key in self._inflight:
                inflight_future = self._inflight[cache_key]
                is_leader = False
            else:
                inflight_future = concurrent.futures.Future()
                self._inflight[cache_key] = inflight_future
                is_leader = True

        # Follower thread waits for the leader thread
        if not is_leader:
            logger.info(f"Single-flight: coalescing with active request for key {cache_key}")
            try:
                sf_timeout = getattr(self, 'single_flight_timeout', None)
                if sf_timeout is None:
                    sf_timeout = self.timeout + 3.0
                follower_jobs = inflight_future.result(timeout=sf_timeout)
                return [copy.deepcopy(j) for j in follower_jobs]
            except (concurrent.futures.TimeoutError, TimeoutError):
                logger.warning(f"Single-flight wait timed out for key {cache_key}")
                with self._lock:
                    cached_entry = self._cache.get(cache_key)
                if cached_entry:
                    _, stale_jobs = cached_entry
                    return [copy.deepcopy(j) for j in stale_jobs]
                raise AdzunaTimeoutError(f"Single-flight wait timed out for query '{q}'")
            except Exception:
                raise

        # Leader thread executes the HTTP request
        def _resolve_inflight(res=None, exc=None):
            if not inflight_future.done():
                if exc is not None:
                    inflight_future.set_exception(exc)
                else:
                    inflight_future.set_result(res)

        try:
            # Call counter increment and logging for live HTTP calls (thread-safe)
            now_dt = datetime.now()
            hour_key = now_dt.strftime('%Y-%m-%d-%H')
            day_key = now_dt.strftime('%Y-%m-%d')
            with self._lock:
                self._call_counter['total'] += 1
                self._call_counter['hourly'][hour_key] = self._call_counter['hourly'].get(hour_key, 0) + 1
                self._call_counter['daily'][day_key] = self._call_counter['daily'].get(day_key, 0) + 1
                tot = self._call_counter['total']
                day_cnt = self._call_counter['daily'][day_key]
                hr_cnt = self._call_counter['hourly'][hour_key]

            logger.info(
                f"Adzuna API Call Counter: total={tot}, daily={day_cnt} (day={day_key}), hourly={hr_cnt} (hour={hour_key})"
            )

            # Build query parameters — OMIT empty values
            params: Dict[str, Any] = {
                'app_id': self.app_id,
                'app_key': self.app_key,
                'results_per_page': per_page,
                'sort_by': adzuna_sort
            }
            if q:
                params['what'] = q
            if location:
                params['where'] = location
            if salary_min > 0:
                params['salary_min'] = salary_min

            endpoint_url = f"{self.base_url}/{page}"
            logger.info(f"Adzuna Live Query -> url: {endpoint_url}, what: '{q}', where: '{location}', page: {page}")

            start_time = time.time()
            try:
                resp = self.session.get(endpoint_url, params=params, timeout=self.timeout)
                status = resp.status_code
                latency = (time.time() - start_time) * 1000

                if status == 401 or status == 403:
                    snippet = resp.text[:300]
                    logger.error(f"Adzuna Auth Failure (HTTP {status}): {snippet}")
                    err = AdzunaAuthError(f"Adzuna authentication failed (HTTP {status}). Check ADZUNA_APP_ID/KEY.")
                    _resolve_inflight(exc=err)
                    raise err

                if status == 429:
                    snippet = resp.text[:300]
                    logger.warning(f"Adzuna Rate Limit Exceeded (HTTP 429): {snippet}")
                    with self._lock:
                        cached_entry = self._cache.get(cache_key)
                    if cached_entry:
                        _, stale_jobs = cached_entry
                        logger.warning(
                            f"Serving stale-while-error cached results ({len(stale_jobs)} jobs) for key: {cache_key}"
                        )
                        fresh_stale = [copy.deepcopy(j) for j in stale_jobs]
                        _resolve_inflight(res=fresh_stale)
                        return [copy.deepcopy(j) for j in fresh_stale]
                    err = AdzunaRateLimitError("Adzuna API rate limit reached.")
                    _resolve_inflight(exc=err)
                    raise err

                if status >= 500:
                    snippet = resp.text[:300]
                    logger.error(f"Adzuna Upstream Server Error (HTTP {status}): {snippet}")
                    with self._lock:
                        cached_entry = self._cache.get(cache_key)
                    if cached_entry:
                        _, stale_jobs = cached_entry
                        logger.warning(
                            f"Serving stale cached results ({len(stale_jobs)} jobs) on HTTP {status} for key: {cache_key}"
                        )
                        fresh_stale = [copy.deepcopy(j) for j in stale_jobs]
                        _resolve_inflight(res=fresh_stale)
                        return [copy.deepcopy(j) for j in fresh_stale]
                    err = AdzunaUpstreamError(f"Adzuna upstream error (HTTP {status}).")
                    _resolve_inflight(exc=err)
                    raise err

                if status != 200:
                    snippet = resp.text[:300]
                    logger.error(f"Adzuna Unexpected Status (HTTP {status}): {snippet}")
                    err = AdzunaUpstreamError(f"Adzuna returned HTTP {status}: {snippet}")
                    _resolve_inflight(exc=err)
                    raise err

                data = resp.json()
                raw_results = data.get('results', [])
                total_count = data.get('count', len(raw_results))

                normalized: List[Dict[str, Any]] = []
                for item in raw_results:
                    parsed = self._normalize(item)
                    if parsed:
                        normalized.append(parsed)

                logger.info(
                    f"Adzuna API Success: {len(normalized)}/{total_count} jobs parsed in {latency:.1f}ms "
                    f"(query='{q}', where='{location}')"
                )

                # Save pristine list in memory cache (thread-safe with eviction cap)
                pristine_jobs = [copy.deepcopy(j) for j in normalized]
                with self._lock:
                    self._evict_cache_locked(now, key_to_add=cache_key)
                    self._cache[cache_key] = (now, pristine_jobs)
                _resolve_inflight(res=[copy.deepcopy(j) for j in pristine_jobs])
                return [copy.deepcopy(j) for j in pristine_jobs]

            except requests.exceptions.RetryError as e:
                logger.warning(f"Adzuna RetryError exhausted retries: {e}")
                err_str = str(e).lower()
                is_429 = "429" in err_str or "rate limit" in err_str or "too many requests" in err_str
                with self._lock:
                    cached_entry = self._cache.get(cache_key)
                if cached_entry:
                    _, stale_jobs = cached_entry
                    logger.warning(
                        f"Serving stale-while-error cached results ({len(stale_jobs)} jobs) on RetryError for key: {cache_key}"
                    )
                    fresh_stale = [copy.deepcopy(j) for j in stale_jobs]
                    _resolve_inflight(res=fresh_stale)
                    return [copy.deepcopy(j) for j in fresh_stale]
                if is_429:
                    err = AdzunaRateLimitError("Adzuna API rate limit reached after retries.")
                    _resolve_inflight(exc=err)
                    raise err
                err = AdzunaUpstreamError(f"Adzuna upstream error after retries: {e}")
                _resolve_inflight(exc=err)
                raise err
            except requests.exceptions.Timeout as e:
                logger.error(f"Adzuna Timeout after {self.timeout}s: {e}")
                err = AdzunaTimeoutError(f"Adzuna request timed out after {self.timeout}s.")
                _resolve_inflight(exc=err)
                raise err
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Adzuna Network Connection Error: {e}")
                err = AdzunaUpstreamError("Adzuna network connection failed.")
                _resolve_inflight(exc=err)
                raise err
            except (AdzunaAuthError, AdzunaRateLimitError, AdzunaTimeoutError, AdzunaUpstreamError) as e:
                _resolve_inflight(exc=e)
                raise
            except Exception as e:
                logger.error(f"Adzuna Unexpected Exception: {e}", exc_info=True)
                err = AdzunaUpstreamError(f"Failed to process Adzuna response: {str(e)}")
                _resolve_inflight(exc=err)
                raise err
        finally:
            if not inflight_future.done():
                inflight_future.set_exception(AdzunaUpstreamError("In-flight leader failed unexpectedly before resolving."))
            with self._lock:
                self._inflight.pop(cache_key, None)

    def infer_role(self, candidate_skills: List[str]) -> str:
        """Heuristically infers concise target job role from candidate skills."""
        if not candidate_skills:
            return ""
        candidate_skills_lower = set(s.lower() for s in candidate_skills)
        best_role = ""
        best_overlap = 0
        for role, required in JOB_ROLE_SKILLS.items():
            overlap = len(candidate_skills_lower.intersection(set(required)))
            if overlap > best_overlap:
                best_overlap = overlap
                best_role = role
        return best_role

    def rank_skills_by_market_relevance(self, candidate_skills: List[str]) -> List[str]:
        """
        Ranks candidate skills by job-market relevance using frequency across JOB_ROLE_SKILLS.
        Skills demanded across more industry target roles appear earlier.
        """
        if not candidate_skills:
            return []

        freq: Dict[str, int] = {}
        for role_skills in JOB_ROLE_SKILLS.values():
            for s in role_skills:
                s_lower = s.lower().strip()
                freq[s_lower] = freq.get(s_lower, 0) + 1

        def skill_key(sk: str) -> Tuple[int, int]:
            s_low = sk.lower().strip()
            return (freq.get(s_low, 0), len(sk))

        return sorted(candidate_skills, key=skill_key, reverse=True)

    def fetch_personalized_jobs(
        self,
        skills: List[str],
        experience: str = '',
        location: str = '',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Multi-Query Personalization:
        Builds up to 3 focused queries per candidate:
          (a) Inferred target role
          (b) Top 2 skills by job-market relevance (from JOB_ROLE_SKILLS frequency)
          (c) Role + City if location is set
        Runs queries concurrently with ThreadPoolExecutor with timeouts.
        If one query fails, results from other queries are merged and deduped
        by raw id and normalized (title + company + city).
        Returns empty list for candidates without parsed skills.
        """
        if not self.is_configured():
            logger.warning("Adzuna credentials missing; personalized jobs will fall back.")
            raise AdzunaConfigError("Adzuna credentials not configured.")

        # Candidate with no parsed skills: do NOT show generic list as if personalized
        if not skills:
            logger.info("Candidate has no skills; returning empty list (needs resume).")
            return []

        inferred_role = self.infer_role(skills)
        market_ranked_skills = self.rank_skills_by_market_relevance(skills)
        cand_loc = (location or '').strip()

        # (a) Target role
        q_role = inferred_role or (market_ranked_skills[0] if market_ranked_skills else "Developer")

        # (b) Top 2 market skills (short: 1-2 words, never 4+ skills)
        top_2_skills = market_ranked_skills[:2]
        q_skills = " ".join(top_2_skills) if top_2_skills else q_role

        query_tuples: List[Tuple[str, str]] = []
        # Query (a): Target role
        query_tuples.append((q_role, ""))

        # Query (b): Top 2 skills by market relevance
        if q_skills and q_skills.lower() != q_role.lower():
            query_tuples.append((q_skills, ""))

        # Query (c): Role + City if location is set
        if cand_loc:
            query_tuples.append((q_role, cand_loc))
        elif len(market_ranked_skills) >= 3:
            query_tuples.append((market_ranked_skills[2], ""))

        # Deduplicate query tuples and enforce max 3
        final_queries: List[Tuple[str, str]] = []
        seen_query_tuples = set()
        for q_val, loc_val in query_tuples:
            t_norm = (q_val.lower().strip(), loc_val.lower().strip())
            if t_norm not in seen_query_tuples:
                seen_query_tuples.add(t_norm)
                final_queries.append((q_val, loc_val))
            if len(final_queries) >= 3:
                break

        logger.info(f"Multi-query personalization running {len(final_queries)} queries: {final_queries}")

        all_results: List[Dict[str, Any]] = []
        auth_or_config_err = None
        rate_limit_err = None
        timed_out = False
        successful_queries = 0

        max_workers = min(3, len(final_queries)) or 1
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        future_to_q = {
            executor.submit(self.search, q=q, location=loc, per_page=limit): (q, loc)
            for q, loc in final_queries
        }

        subquery_timeout = getattr(self, 'pool_timeout', None)
        if subquery_timeout is None:
            subquery_timeout = max(0.1, self.timeout + 3.0)

        try:
            try:
                for future in concurrent.futures.as_completed(future_to_q, timeout=subquery_timeout):
                    q_text, loc_text = future_to_q[future]
                    try:
                        jobs = future.result()
                        if jobs:
                            all_results.extend(jobs)
                            successful_queries += 1
                    except (AdzunaAuthError, AdzunaConfigError) as e:
                        auth_or_config_err = e
                    except AdzunaRateLimitError as e:
                        rate_limit_err = e
                    except Exception as e:
                        logger.warning(f"Adzuna personalized sub-query failed for '{q_text}' ({loc_text}): {e}")
            except (concurrent.futures.TimeoutError, TimeoutError):
                timed_out = True
                logger.warning(
                    f"Personalized job search sub-queries timed out after {subquery_timeout}s. "
                    f"Proceeding with {successful_queries} completed queries."
                )
                for f in future_to_q:
                    if not f.done():
                        f.cancel()
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        # If every query failed due to fatal errors and produced zero results
        if successful_queries == 0:
            if auth_or_config_err:
                raise auth_or_config_err
            if rate_limit_err and not all_results:
                raise rate_limit_err
            if timed_out:
                raise AdzunaTimeoutError("Personalized job search sub-queries timed out.")

        # Deduplicate across queries by raw_id and (normalized title + company + city)
        merged_jobs: List[Dict[str, Any]] = []
        seen_raw_ids: Dict[str, Dict[str, Any]] = {}
        seen_normalized_keys: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

        for job in all_results:
            raw_id = str(job.get('raw_id') or job.get('source_job_id') or job.get('id') or '').strip()
            norm_title = re.sub(r'[^a-z0-9]', '', (job.get('title') or '').lower())
            norm_company = re.sub(r'[^a-z0-9]', '', (job.get('company') or '').lower())
            norm_city = re.sub(r'[^a-z0-9]', '', (job.get('city') or job.get('location') or '').lower())
            norm_key = (norm_title, norm_company, norm_city)

            existing_job = None
            if raw_id and raw_id in seen_raw_ids:
                existing_job = seen_raw_ids[raw_id]
            elif norm_title and norm_key in seen_normalized_keys:
                existing_job = seen_normalized_keys[norm_key]

            if existing_job is not None:
                # Merge safety: preserve valid external_apply_url from duplicate if existing lacks one
                cand_url = job.get('external_apply_url') or job.get('apply_url')
                curr_url = existing_job.get('external_apply_url') or existing_job.get('apply_url')
                if cand_url and not curr_url:
                    existing_job['external_apply_url'] = cand_url
                    existing_job['apply_url'] = cand_url
                continue

            if raw_id:
                seen_raw_ids[raw_id] = job
            if norm_title:
                seen_normalized_keys[norm_key] = job

            merged_jobs.append(job)

        logger.info(f"Multi-query personalization merged {len(merged_jobs)} unique jobs from {len(all_results)} raw results.")
        return [copy.deepcopy(j) for j in merged_jobs]

    def check_health(self, what: str = "python", where: str = "Ahmedabad", limit: int = 3) -> Dict[str, Any]:
        """
        Diagnostic probe executing a real Adzuna API request.
        Returns: { keys_loaded: bool, status_code, latency_ms, results_count, error_type, error_message }
        """
        keys_loaded = self.is_configured()
        if not keys_loaded:
            return {
                "keys_loaded": False,
                "status_code": None,
                "latency_ms": 0.0,
                "results_count": 0,
                "error_type": "AdzunaConfigError",
                "error_message": "ADZUNA_APP_ID or ADZUNA_APP_KEY is missing from environment"
            }

        start_time = time.time()
        params = {
            'app_id': self.app_id,
            'app_key': self.app_key,
            'results_per_page': limit,
            'what': what,
            'where': where
        }
        endpoint = f"{self.base_url}/1"

        try:
            resp = self.session.get(endpoint, params=params, timeout=self.timeout)
            latency_ms = round((time.time() - start_time) * 1000, 2)
            status = resp.status_code

            if status == 200:
                data = resp.json()
                results = data.get('results', [])
                return {
                    "keys_loaded": True,
                    "status_code": status,
                    "latency_ms": latency_ms,
                    "results_count": len(results),
                    "error_type": None,
                    "error_message": None
                }
            elif status in (401, 403):
                return {
                    "keys_loaded": True,
                    "status_code": status,
                    "latency_ms": latency_ms,
                    "results_count": 0,
                    "error_type": "AdzunaAuthError",
                    "error_message": f"Authentication failed (HTTP {status}): {resp.text[:200]}"
                }
            elif status == 429:
                return {
                    "keys_loaded": True,
                    "status_code": status,
                    "latency_ms": latency_ms,
                    "results_count": 0,
                    "error_type": "AdzunaRateLimitError",
                    "error_message": "Rate limit exceeded (HTTP 429)"
                }
            else:
                return {
                    "keys_loaded": True,
                    "status_code": status,
                    "latency_ms": latency_ms,
                    "results_count": 0,
                    "error_type": "AdzunaUpstreamError",
                    "error_message": f"Server error (HTTP {status}): {resp.text[:200]}"
                }

        except requests.exceptions.Timeout:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "keys_loaded": True,
                "status_code": None,
                "latency_ms": latency_ms,
                "results_count": 0,
                "error_type": "AdzunaTimeoutError",
                "error_message": f"Request timed out after {self.timeout}s"
            }
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "keys_loaded": True,
                "status_code": None,
                "latency_ms": latency_ms,
                "results_count": 0,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }


# Global singleton instance
adzuna_client = AdzunaClient()
