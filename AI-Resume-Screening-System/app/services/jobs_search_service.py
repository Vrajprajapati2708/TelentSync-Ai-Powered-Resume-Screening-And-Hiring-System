"""
Jobs Search Service — Unified Aggregation, Filtering, AI-Matching & Caching
Supports Adzuna Live Jobs + TalentSync Internal Jobs.
"""
import re
import time
import math
import hashlib
import requests
from typing import Dict, Any, List, Tuple, Optional, cast
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config.settings import ActiveConfig
from app.database.connection import get_db
from app.ai.job_matcher import JobMatcher
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global In-Memory Cache for Adzuna API (TTL: 10 minutes = 600 seconds)
_ADZUNA_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
ADZUNA_CACHE_TTL = 600

# Regex patterns for experience extraction
EXP_RANGE_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(?:-|to|–|—)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)', re.I)
EXP_MIN_PATTERN = re.compile(r'(?:min(?:imum)?|at least|\b)\s*(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)', re.I)
EXP_REQ_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)(?:\s+(?:of\s+)?experience|\s+exp|\s+relevant|\s+required)', re.I)
FRESHER_PATTERN = re.compile(r'\b(fresher|freshers|entry[- ]?level|intern|internship|trainee|no experience)\b', re.I)

REMOTE_PATTERN = re.compile(r'\b(remote|work from home|wfh|telecommute)\b', re.I)
HYBRID_PATTERN = re.compile(r'\b(hybrid)\b', re.I)


class JobsSearchService:
    def __init__(self):
        self.matcher = JobMatcher()
        self.app_id = getattr(ActiveConfig, 'ADZUNA_APP_ID', None)
        self.app_key = getattr(ActiveConfig, 'ADZUNA_APP_KEY', None)
        self.country = getattr(ActiveConfig, 'ADZUNA_COUNTRY', 'in')
        self.base_url = f"https://api.adzuna.com/v1/api/jobs/{self.country}/search"
        self.timeout = 5  # 5s timeout as specified
        
        # Requests session with 1 retry on 5xx / connection
        self.session = requests.Session()
        retries = Retry(
            total=1,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=cast(Any, retries))
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def extract_experience(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """Extract (exp_min, exp_max) in years from text, or (None, None) if unknown."""
        if not text:
            return None, None
            
        if FRESHER_PATTERN.search(text):
            return 0.0, 1.0
            
        m_range = EXP_RANGE_PATTERN.search(text)
        if m_range:
            y1, y2 = float(m_range.group(1)), float(m_range.group(2))
            return min(y1, y2), max(y1, y2)
            
        m_min = EXP_MIN_PATTERN.search(text)
        if m_min:
            y = float(m_min.group(1))
            return y, y + 2.0
            
        m_req = EXP_REQ_PATTERN.search(text)
        if m_req:
            y = float(m_req.group(1))
            return y, y + 2.0
            
        return None, None

    def detect_work_mode(self, text: str) -> str:
        """Classify work mode into 'remote', 'hybrid', or 'onsite'."""
        if REMOTE_PATTERN.search(text):
            return 'remote'
        if HYBRID_PATTERN.search(text):
            return 'hybrid'
        return 'onsite'

    def format_salary_display(self, salary_min: int, salary_max: int, original_text: str = '') -> str:
        """Format salary nicely as INR or LPA."""
        if salary_min > 0 and salary_max > 0:
            if salary_min >= 100000:
                lpa_min = round(salary_min / 100000.0, 1)
                lpa_max = round(salary_max / 100000.0, 1)
                if lpa_min == lpa_max:
                    return f"₹{lpa_min:g} LPA"
                return f"₹{lpa_min:g} - ₹{lpa_max:g} LPA"
            return f"₹{salary_min:,} - ₹{salary_max:,}"
        elif salary_min > 0:
            if salary_min >= 100000:
                return f"₹{salary_min/100000.0:.1f}L+ P.A."
            return f"₹{salary_min:,}+"
        elif original_text and any(c.isdigit() for c in original_text):
            return original_text
        return "Not disclosed"

    def fetch_internal_jobs(self, q: str, location: str, work_mode: str, min_salary: int) -> List[Dict[str, Any]]:
        """Fetch internal active jobs using parameterized SQL queries with SQLite indexes."""
        query_sql = "SELECT id, title, company, location, type, salary, skills, description, status, created_at, work_mode, salary_min, salary_max FROM jobs WHERE status = 'Active'"
        params: List[Any] = []

        if q:
            term = f"%{q}%"
            query_sql += " AND (title LIKE ? OR company LIKE ? OR skills LIKE ? OR description LIKE ?)"
            params.extend([term, term, term, term])

        if location:
            query_sql += " AND location LIKE ?"
            params.append(f"%{location}%")

        if work_mode and work_mode != 'any':
            query_sql += " AND work_mode = ?"
            params.append(work_mode)

        if min_salary > 0:
            query_sql += " AND (salary_min >= ? OR salary_max >= ?)"
            params.extend([min_salary, min_salary])

        results = []
        try:
            with get_db() as conn:
                rows = conn.execute(query_sql, params).fetchall()
                for r in rows:
                    desc = r['description'] or ''
                    title = r['title'] or ''
                    skills_raw = r['skills'] or ''
                    skills_list = [s.strip() for s in skills_raw.split(',') if s.strip()] if skills_raw else []
                    
                    e_min, e_max = self.extract_experience(f"{title} {desc}")
                    s_min = r['salary_min'] or 0
                    s_max = r['salary_max'] or s_min
                    sal_disp = self.format_salary_display(s_min, s_max, r['salary'] or '')
                    
                    clean_desc = re.sub(r'<[^>]+>', '', desc)
                    snippet = clean_desc[:180].strip() + ('...' if len(clean_desc) > 180 else '')

                    results.append({
                        'id': f"internal_{r['id']}",
                        'raw_id': r['id'],
                        'source_job_id': str(r['id']),
                        'title': title,
                        'company': r['company'] or 'TalentSync Partner',
                        'location': r['location'] or 'Remote/Office',
                        'work_mode': r['work_mode'] or 'onsite',
                        'salary_min': s_min,
                        'salary_max': s_max,
                        'salary_display': sal_disp,
                        'experience_min': e_min,
                        'experience_max': e_max,
                        'description_snippet': snippet,
                        'description': desc,
                        'skills': skills_list,
                        'posted_at': r['created_at'] or datetime.now().isoformat(),
                        'source': 'internal',
                        'is_external': False,
                        'external_apply_url': None,
                        'apply_url': '',
                        'match_score': 50,
                        'matched_skills': []
                    })
        except Exception as e:
            logger.error(f"Error fetching internal jobs: {e}")

        return results

    def fetch_adzuna_jobs(self, q: str, location: str, min_salary: int) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetch live external jobs from Adzuna API with in-memory caching."""
        if not self.app_id or not self.app_key:
            return [], "Adzuna credentials not configured; showing internal jobs."

        # Cache key based on normalized query parameters
        cache_key = hashlib.md5(f"{q.strip().lower()}_{location.strip().lower()}_{min_salary}".encode('utf-8')).hexdigest()
        now = time.time()

        if cache_key in _ADZUNA_CACHE:
            ts, cached_jobs = _ADZUNA_CACHE[cache_key]
            if now - ts < ADZUNA_CACHE_TTL:
                logger.info("Adzuna In-Memory Cache Hit")
                return cached_jobs, None

        params = {
            'app_id': self.app_id,
            'app_key': self.app_key,
            'results_per_page': 50,
            'what': q or 'Developer',
            'where': location or 'India',
            'content-type': 'application/json'
        }
        if min_salary > 0:
            params['salary_min'] = min_salary

        try:
            resp = self.session.get(f"{self.base_url}/1", params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            raw_results = data.get('results', [])

            jobs = []
            for item in raw_results:
                title = item.get('title', 'Software Engineer')
                company = (item.get('company') or {}).get('display_name', 'Tech Company')
                loc = (item.get('location') or {}).get('display_name', 'India')
                desc = item.get('description', '')
                
                # Detect work mode
                mode = self.detect_work_mode(f"{title} {loc} {desc}")
                e_min, e_max = self.extract_experience(f"{title} {desc}")
                
                s_min = int(item.get('salary_min') or 0)
                s_max = int(item.get('salary_max') or s_min)
                sal_disp = self.format_salary_display(s_min, s_max)

                clean_desc = re.sub(r'<[^>]+>', '', desc)
                snippet = clean_desc[:180].strip() + ('...' if len(clean_desc) > 180 else '')

                raw_apply_url = str(item.get('redirect_url') or '').strip()
                adzuna_job_id = str(item.get('id', ''))

                jobs.append({
                    'id': f"adzuna_{adzuna_job_id}",
                    'raw_id': adzuna_job_id,
                    'source_job_id': adzuna_job_id,
                    'title': title,
                    'company': company,
                    'location': loc,
                    'work_mode': mode,
                    'salary_min': s_min,
                    'salary_max': s_max,
                    'salary_display': sal_disp,
                    'experience_min': e_min,
                    'experience_max': e_max,
                    'description_snippet': snippet,
                    'description': desc,
                    'skills': [],
                    'posted_at': item.get('created', datetime.now().isoformat()),
                    'source': 'adzuna',
                    'is_external': True,
                    'external_apply_url': raw_apply_url if raw_apply_url else None,
                    'apply_url': raw_apply_url,
                    'match_score': 50,
                    'matched_skills': []
                })

            _ADZUNA_CACHE[cache_key] = (now, jobs)
            return jobs, None

        except requests.exceptions.Timeout:
            logger.warning("Adzuna API request timed out after 5s.")
            return [], "Adzuna API timed out. Displaying local jobs."
        except requests.exceptions.RequestException as e:
            logger.warning(f"Adzuna API request failed: {e}")
            return [], "Live external jobs temporarily unavailable. Showing internal jobs."
        except Exception as e:
            logger.error(f"Unexpected error in fetch_adzuna_jobs: {e}")
            return [], "Live external jobs temporarily unavailable."

    def post_filter_jobs(self, jobs: List[Dict[str, Any]], work_mode: str, min_salary: int, experience: str) -> List[Dict[str, Any]]:
        """Filter in-memory merged jobs according to work_mode, min_salary, and experience bracket."""
        filtered = []
        for j in jobs:
            # 1. Work Mode filter
            if work_mode and work_mode != 'any':
                if j['work_mode'] != work_mode:
                    continue

            # 2. Min Salary filter
            if min_salary > 0:
                # If salary is known, must be >= min_salary
                if j['salary_max'] > 0 and j['salary_max'] < min_salary:
                    continue
                # If salary is unknown (0), user selected min_salary -> exclude
                if j['salary_min'] == 0 and j['salary_max'] == 0:
                    continue

            # 3. Experience filter
            if experience and experience != 'any':
                e_min = j['experience_min']
                e_max = j['experience_max']
                
                # If experience is detectable, enforce bracket
                if e_min is not None:
                    if experience == '0-1':
                        if not (e_min <= 1.0):
                            continue
                    elif experience == '1-3':
                        if not (e_min <= 3.0 and (e_max is None or e_max >= 1.0)):
                            continue
                    elif experience == '3-5':
                        if not (e_min <= 5.0 and (e_max is None or e_max >= 3.0)):
                            continue
                    elif experience == '5-8':
                        if not (e_min <= 8.0 and (e_max is None or e_max >= 5.0)):
                            continue
                    elif experience == '8+':
                        if not ((e_max is not None and e_max >= 8.0) or e_min >= 8.0):
                            continue
                # Note: if experience is unknown (None), we retain the job as specified

            filtered.append(j)
        return filtered

    def deduplicate(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate jobs by normalized (title + company + location)."""
        seen = set()
        deduped = []
        for j in jobs:
            clean_title = re.sub(r'[^a-z0-9]', '', j['title'].lower())
            clean_company = re.sub(r'[^a-z0-9]', '', j['company'].lower())
            clean_loc = re.sub(r'[^a-z0-9]', '', j['location'].lower())
            key = f"{clean_title}|{clean_company}|{clean_loc}"
            if key not in seen:
                seen.add(key)
                deduped.append(j)
        return deduped

    def resolve_candidate_profile(self, user_id: Optional[int]) -> Tuple[List[str], str, str, bool]:
        """Fetch candidate skills, experience, and location from DB."""
        skills = []
        experience = ""
        location = ""
        has_resume = False

        if not user_id:
            return skills, experience, location, has_resume

        try:
            with get_db() as conn:
                # 1. Check resumes table
                r_row = conn.execute(
                    "SELECT extracted_skills, structured_json FROM resumes WHERE user_id=? ORDER BY id DESC LIMIT 1",
                    (user_id,)
                ).fetchone()
                
                if r_row:
                    has_resume = True
                    raw_skills = r_row['extracted_skills'] or ''
                    if raw_skills:
                        skills = [s.strip() for s in raw_skills.split(',') if s.strip()]
                    
                    if r_row['structured_json']:
                        import json
                        try:
                            s_data = json.loads(r_row['structured_json'])
                            yrs = s_data.get('total_experience_years')
                            if yrs is not None and yrs > 0:
                                experience = f"{yrs} years"
                            elif yrs == 0:
                                experience = "fresher"
                        except Exception:
                            pass

                # 2. Check users profile
                u_row = conn.execute("SELECT skills, location FROM users WHERE id=?", (user_id,)).fetchone()
                if u_row:
                    if not skills and u_row['skills']:
                        skills = [s.strip() for s in u_row['skills'].split(',') if s.strip()]
                    if not location and u_row['location']:
                        location = u_row['location']

        except Exception as e:
            logger.error(f"Error resolving candidate profile: {e}")

        return skills, experience, location, has_resume

    def search(self, params: Dict[str, Any], user_id: Optional[int]) -> Dict[str, Any]:
        """
        Main execution flow:
        1. Fetch internal + external jobs
        2. Post-filter & deduplicate
        3. Score & rank with AI hybrid matcher
        4. Sort
        5. Paginate
        """
        q = params['q']
        location = params['location']
        work_mode = params['work_mode']
        min_salary = params['min_salary']
        experience = params['experience']
        source = params['source']
        sort_by = params['sort']
        page = params['page']
        per_page = params['per_page']

        warnings = []
        jobs_pool: List[Dict[str, Any]] = []

        # 1. Fetch internal jobs
        if source in ('all', 'internal'):
            internal_jobs = self.fetch_internal_jobs(q, location, work_mode, min_salary)
            jobs_pool.extend(internal_jobs)

        # 2. Fetch Adzuna jobs
        if source in ('all', 'adzuna'):
            adzuna_jobs, adzuna_warn = self.fetch_adzuna_jobs(q, location, min_salary)
            if adzuna_warn:
                warnings.append(adzuna_warn)
            jobs_pool.extend(adzuna_jobs)

        # 3. Post-filter
        filtered_jobs = self.post_filter_jobs(jobs_pool, work_mode, min_salary, experience)

        # 4. Deduplicate
        deduped_jobs = self.deduplicate(filtered_jobs)

        # 5. Resolve candidate profile & match with AI
        user_skills, user_exp, user_loc, has_resume = self.resolve_candidate_profile(user_id)
        
        scoring_skills = user_skills
        if not has_resume:
            warnings.append("Upload resume for personalized match scores")
            # If no resume skills, use search keywords as fallback for relevance scoring
            if q:
                scoring_skills = [s.strip() for s in re.split(r'[,| ]+', q) if len(s.strip()) > 1]

        user_prefs = {
            'experience': user_exp or '',
            'location': user_loc or location or ''
        }

        # Format jobs for JobMatcher
        matcher_input = []
        for j in deduped_jobs:
            matcher_input.append({
                **j,
                'skills': ', '.join(j.get('skills', [])),
                'salary_min': j.get('salary_min', 0)
            })

        if scoring_skills:
            ranked_jobs = self.matcher.rank_jobs(scoring_skills, matcher_input, user_prefs=user_prefs)
        else:
            # Neutral baseline match score
            ranked_jobs = []
            for j in matcher_input:
                j['match_percentage'] = 50
                j['matching_skills'] = []
                ranked_jobs.append(j)

        # 6. Apply final sorting
        if sort_by == 'newest':
            ranked_jobs.sort(key=lambda x: (x.get('posted_at') or '', x.get('match_percentage', 0)), reverse=True)
        elif sort_by == 'salary':
            ranked_jobs.sort(key=lambda x: (x.get('salary_min', 0), x.get('match_percentage', 0)), reverse=True)
        else:  # 'relevance'
            ranked_jobs.sort(key=lambda x: (x.get('match_percentage', 0), x.get('salary_min', 0), x.get('posted_at') or ''), reverse=True)

        # 7. Paginate
        total = len(ranked_jobs)
        total_pages = max(1, math.ceil(total / per_page)) if total > 0 else 1
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paged_jobs = ranked_jobs[start_idx:end_idx]

        # 8. Clean up response structures
        final_jobs = []
        for r in paged_jobs:
            final_jobs.append({
                'id': str(r.get('id', '')),
                'title': r.get('title', ''),
                'company': r.get('company', ''),
                'location': r.get('location', ''),
                'work_mode': r.get('work_mode', 'onsite'),
                'salary_min': int(r.get('salary_min') or 0),
                'salary_max': int(r.get('salary_max') or 0),
                'salary_display': r.get('salary_display', 'Not disclosed'),
                'experience_min': r.get('experience_min'),
                'experience_max': r.get('experience_max'),
                'description_snippet': r.get('description_snippet', ''),
                'skills': [s.strip() for s in r.get('skills', '').split(',') if s.strip()] if isinstance(r.get('skills'), str) else r.get('skills', []),
                'posted_at': r.get('posted_at', ''),
                'source': r.get('source', 'internal'),
                'source_job_id': str(r.get('source_job_id') or r.get('raw_id') or str(r.get('id', '')).replace('internal_', '').replace('adzuna_', '')),
                'is_external': bool(r.get('is_external', False) or r.get('source') == 'adzuna'),
                'external_apply_url': r.get('external_apply_url') or (r.get('apply_url') if (r.get('is_external') or r.get('source') == 'adzuna') else None),
                'apply_url': r.get('apply_url', ''),
                'match_score': int(r.get('match_percentage', 50)),
                'matched_skills': r.get('matching_skills', [])
            })

        return {
            'success': True,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'jobs': final_jobs,
            'applied_filters': {
                'q': q,
                'location': location,
                'work_mode': work_mode,
                'min_salary': min_salary,
                'experience': experience,
                'source': source,
                'sort': sort_by,
                'page': page,
                'per_page': per_page
            },
            'warnings': list(dict.fromkeys(warnings))  # Deduplicate warnings
        }
