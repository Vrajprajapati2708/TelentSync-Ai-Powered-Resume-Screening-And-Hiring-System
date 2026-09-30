import re
import copy
from typing import Any, Tuple, Optional
from datetime import datetime
from app.ml.recommendation.recommend_jobs import recommend_jobs

class JobMatcher:
    """
    Enterprise AI Layer that extends the existing ML Pipeline.
    Applies the newly requested weighted scoring model:
    - Role Match: 40% (Using TF-IDF Semantic similarity)
    - Skill Match: 40% (Using synonym-aware skill intersection)
    - Experience Match: 15% (Using deterministic, explainable experience matching)
    - Location: 5%
    """

    SYNONYMS = {
        'js': 'javascript',
        'ml': 'machine learning',
        'ai': 'artificial intelligence',
        'node': 'node.js',
        'py': 'python',
        'reactjs': 'react'
    }

    def _normalize_skill(self, skill: str) -> str:
        s = skill.strip().lower()
        return self.SYNONYMS.get(s, s)

    def _parse_candidate_experience(self, user_exp: Any) -> Tuple[Optional[float], bool]:
        """
        Parses candidate experience input into (years, is_fresher).
        Handles: "2 years", "3+ years", "5 years of experience", "Fresher",
        "Entry level", "2.5 years", floats, and integers.
        """
        if user_exp is None:
            return None, False

        if isinstance(user_exp, (int, float)):
            val = float(user_exp)
            return val, (val == 0.0)

        s = str(user_exp).strip().lower()
        if not s:
            return None, False

        # Check fresher / entry level keywords
        if re.search(r'\b(fresher|freshers|entry[- ]?level|intern|internship|trainee|no experience)\b', s):
            return 0.0, True

        # Check range pattern: "3-5 years" -> take average
        m_range = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to|–|—)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)', s)
        if m_range:
            y1 = float(m_range.group(1))
            y2 = float(m_range.group(2))
            avg_y = (y1 + y2) / 2.0
            return avg_y, (avg_y == 0.0)

        # Check standard pattern: "3+ years", "5 years of experience", "2.5 yrs"
        m_years = re.search(r'(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)', s)
        if m_years:
            val = float(m_years.group(1))
            return val, (val == 0.0)

        # Direct numeric string: "3" or "2.5"
        m_num = re.search(r'^(\d+(?:\.\d+)?)$', s)
        if m_num:
            val = float(m_num.group(1))
            return val, (val == 0.0)

        return None, False

    def _parse_job_experience(self, job_desc: Optional[str]) -> Tuple[Optional[float], Optional[float], bool]:
        """
        Extracts required experience from job description: (min_years, max_years, fresher_friendly).
        Handles: "2+ years", "3-5 years", "minimum 4 years", "5 years required",
        "freshers welcome", "entry level".
        """
        if not job_desc or not isinstance(job_desc, str):
            return None, None, False

        text = job_desc.lower()

        # Check fresher friendly keywords
        fresher_friendly = bool(re.search(
            r'\b(freshers?\s+(?:welcome|can apply|eligible)|no experience required|entry[- ]?level|internship|trainee)\b',
            text
        ))

        # Check experience range: "3-5 years", "2 to 4 yrs"
        m_range = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to|–|—)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)', text)
        if m_range:
            y1 = float(m_range.group(1))
            y2 = float(m_range.group(2))
            return min(y1, y2), max(y1, y2), fresher_friendly

        # Check minimum / plus patterns: "3+ years", "minimum 4 years", "at least 2 years"
        m_min = re.search(r'(?:min(?:imum)?|at least|\b)\s*(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)', text)
        if not m_min:
            m_min = re.search(r'(?:min(?:imum)?|at least)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', text)
        if not m_min:
            m_min = re.search(r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)(?:\s+(?:of\s+)?experience|\s+exp|\s+relevant|\s+required)', text)

        if m_min:
            val = float(m_min.group(1))
            return val, val, fresher_friendly

        if fresher_friendly:
            return 0.0, 0.0, True

        return None, None, False

    def _calc_experience(self, job_desc: Optional[str], user_exp: Any) -> float:
        """
        Deterministic, explainable experience matching algorithm.
        Returns a score in [0.0, 1.0].
        - Role Match: 40%
        - Skill Match: 40%
        - Experience Match: 15%
        - Location: 5%
        """
        cand_years, is_fresher_cand = self._parse_candidate_experience(user_exp)
        job_min, job_max, fresher_friendly_job = self._parse_job_experience(job_desc)

        # 1. Job specifies NO detectable experience requirement:
        if job_min is None and not fresher_friendly_job:
            # Neutral baseline: open role doesn't filter on experience
            return 0.75 if cand_years is None else 0.80

        # 2. Candidate experience unknown, but job has explicit requirement:
        if cand_years is None:
            return 0.50

        # 3. Candidate is Fresher:
        if is_fresher_cand or cand_years == 0.0:
            if fresher_friendly_job or (job_min is not None and job_min == 0.0):
                return 1.0  # Perfect entry-level match
            if job_min is not None and job_min > 0.0:
                # Weak match scaled by requirement difficulty
                score = max(0.05, min(0.30, 0.5 / (1.0 + job_min)))
                return round(score, 4)

        # 4. Experienced Candidate (cand_years > 0.0):
        if fresher_friendly_job and (job_min is None or job_min == 0.0):
            return 0.75  # Experienced candidate applying for fresher role

        if job_min is not None:
            if cand_years >= job_min:
                # Meets or exceeds minimum requirement
                if job_max is not None and cand_years > (job_max + 2.0):
                    # Slight decay for substantial over-qualification
                    score = max(0.85, 1.0 - 0.02 * (cand_years - (job_max + 2.0)))
                    return round(score, 4)
                return 1.0
            else:
                # Insufficient experience: proportional ratio
                ratio = cand_years / job_min
                score = max(0.10, 0.90 * ratio)
                return round(score, 4)

        return 0.75

    def _calc_location(self, job_loc: str, user_loc: str) -> float:
        """Heuristic for location match in [0.0, 1.0]."""
        if not user_loc or not job_loc: 
            return 0.5
        return 1.0 if user_loc.lower() in job_loc.lower() or job_loc.lower() in user_loc.lower() else 0.0

    def rank_jobs(self, user_skills: list[str], normalized_jobs: list[dict], user_prefs: dict | None = None) -> list[dict]:
        """
        Ranks normalized external/internal jobs using the exact weights:
        - Role Match: 40%
        - Skill Match: 40%
        - Experience Match: 15%
        - Location: 5%
        """
        if not normalized_jobs:
            return []
            
        if not user_prefs:
            user_prefs = {}

        # Work on deep copies so caller's job dicts are never mutated in place
        working_jobs = [copy.deepcopy(j) for j in normalized_jobs]

        # Normalize user skills
        norm_user_skills = [self._normalize_skill(s) for s in user_skills]

        # Normalize job skills for the ML engine
        for job in working_jobs:
            s_val = job.get('skills', '')
            if isinstance(s_val, list):
                raw_skills = [str(s).strip() for s in s_val if str(s).strip()]
            elif isinstance(s_val, str):
                raw_skills = [s.strip() for s in s_val.split(',') if s.strip()]
            else:
                raw_skills = []
            job['skills'] = ', '.join([self._normalize_skill(s) for s in raw_skills])

        # 1. Base semantic & skill scores via ML Pipeline
        ml_scored_jobs = recommend_jobs(norm_user_skills, working_jobs, top_n=len(working_jobs))
        
        # 2. Apply Strict Weights
        final_ranked = []
        for job in ml_scored_jobs:
            role_match = job.get('semantic_score', 0.0)
            skill_match = job.get('skill_score', 0.0)
            
            experience_match = self._calc_experience(job.get('description', ''), user_prefs.get('experience'))
            location_match = self._calc_location(job.get('location', ''), user_prefs.get('location', ''))
            
            final_score = (
                (0.40 * role_match) + 
                (0.40 * skill_match) + 
                (0.15 * experience_match) + 
                (0.05 * location_match)
            )

            # Experience-Aware Ranking Adjustment (Push down mismatched extremes)
            cand_years, is_fresher_cand = self._parse_candidate_experience(user_prefs.get('experience'))
            job_min = job.get('experience_min')
            job_max = job.get('experience_max')
            if job_min is None and job_max is None:
                p_min, p_max, _ = self._parse_job_experience(job.get('description', ''))
                job_min = p_min
                job_max = p_max

            job_title_lower = (job.get('title') or '').lower()
            is_senior_job = (
                (job_min is not None and job_min >= 5.0) or
                any(kw in job_title_lower for kw in ['senior', 'sr.', 'lead', 'principal', 'staff', 'architect'])
            )
            is_intern_or_fresher_job = (
                (job_max is not None and job_max <= 1.0) or
                any(kw in job_title_lower for kw in ['intern', 'internship', 'fresher', 'trainee', 'entry level', 'entry-level', 'junior'])
            )

            # 1. Fresher / 0-2 yrs candidate: push down jobs requiring 5+ yrs
            if (cand_years is not None and cand_years <= 2.0) or is_fresher_cand:
                if is_senior_job:
                    final_score *= 0.80

            # 2. Senior candidate (5+ yrs): push down fresher / intern roles
            elif cand_years is not None and cand_years >= 5.0:
                if is_intern_or_fresher_job:
                    final_score *= 0.80

            # 3. Unknown candidate experience or unspecified jobs = neutral
            
            job['match_percentage'] = min(int(round(final_score * 100)), 100)
            job['ai_match_score'] = job['match_percentage']  # alias for backwards compatibility
            job['match_score'] = job['match_percentage']     # alias for caller compatibility
            job['experience_score'] = round(experience_match, 4)
            job['location_score'] = round(location_match, 4)
            
            # Extract Matching Skills (for UI)
            js_raw = job.get('skills', '')
            if isinstance(js_raw, list):
                raw_s_list = [str(s) for s in js_raw]
            elif isinstance(js_raw, str):
                raw_s_list = [s.strip() for s in js_raw.split(',') if s.strip()]
            else:
                raw_s_list = []
            job_skills_set = set(self._normalize_skill(s) for s in raw_s_list if s)
            job['matching_skills'] = list(set(norm_user_skills).intersection(job_skills_set))
            
            final_ranked.append(job)
                
        # 3. Sort by: 1. Match %, 2. Salary (desc), 3. Date posted (desc)
        final_ranked.sort(key=lambda x: (
            x['match_percentage'],
            x.get('salary_min', 0),
            x.get('posted_date', '')
        ), reverse=True)
        
        return final_ranked
