# ============================================================
#  TalentSync — Candidate Ranking Engine
#
#  Weighted scoring formula:
#    Skills Match  : 40 %  (Evidence-Weighted: Exp 1.0, Proj 0.7, List 0.2, Verified 1.0)
#    Experience    : 25 %
#    ATS Score     : 20 %
#    Education     : 15 %
# ============================================================

import re
import json
from typing import Optional, Union, Any, Dict, List, Set
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Ranking weights (must sum to 100)
WEIGHTS = {
    'skills_match': 40,
    'ats_score':    20,
    'experience':   25,
    'education':    15,
}

# Evidence hierarchy weights for skill matching (P0 Anti-Gaming Rule)
EVIDENCE_WEIGHTS = {
    'verified':      1.0,  # Quiz-verified skills
    'experience':    1.0,  # Work experience narrative / bullet points
    'project':       0.7,  # Project descriptions
    'list':          0.2,  # Bare keyword list / profile tags
    'self_declared': 0.2,  # Blind self-declared skills (Step 6)
    'missing':       0.0,  # Skill not found
}


def match_skill_in_text(skill: str, text: str) -> bool:
    """
    Check if a skill appears in text using symbol-safe boundary matching.
    Avoids naive \\b failures on C++, C#, .NET, Node.js.
    """
    if not skill or not text:
        return False
    s_clean = skill.strip().lower()
    t_clean = text.lower()
    if not s_clean or not t_clean:
        return False

    # Disambiguate single-letter 'c' from 'c++' or 'c#'
    if s_clean == 'c':
        pattern = r'(?<![a-zA-Z0-9_])c(?![a-zA-Z0-9_+#])'
        return bool(re.search(pattern, t_clean))

    # Regex boundary: (?<![a-zA-Z0-9_])<escaped_skill>(?![a-zA-Z0-9_])
    pattern = rf'(?<![a-zA-Z0-9_]){re.escape(s_clean)}(?![a-zA-Z0-9_])'
    return bool(re.search(pattern, t_clean))


def extract_candidate_evidence(candidate: dict) -> dict:
    """
    Extract work experience text, project text, bare skills, self-declared skills,
    and verified skills from any candidate dict representation (flat, nested, or structured_json).
    """
    exp_parts: List[str] = []
    proj_parts: List[str] = []
    bare_skills: List[str] = []
    self_declared_skills: Set[str] = set()
    verified_skills: Set[str] = set()

    # 1. Direct verified skills
    if candidate.get('verified_skills'):
        v = candidate['verified_skills']
        if isinstance(v, (set, list, tuple)):
            verified_skills.update(s.strip().lower() for s in v if isinstance(s, str) and s.strip())

    # Step 6: Direct self-declared / candidate_skills
    if candidate.get('self_declared_skills'):
        s_decl = candidate['self_declared_skills']
        if isinstance(s_decl, (list, set, tuple)):
            for s in s_decl:
                if isinstance(s, str) and s.strip():
                    self_declared_skills.add(s.strip().lower())
                    bare_skills.append(s.strip())

    if candidate.get('declared_skills'):
        s_decl = candidate['declared_skills']
        if isinstance(s_decl, (list, set, tuple)):
            for s in s_decl:
                if isinstance(s, str) and s.strip():
                    self_declared_skills.add(s.strip().lower())
                    bare_skills.append(s.strip())

    if candidate.get('candidate_skills'):
        c_skills = candidate['candidate_skills']
        if isinstance(c_skills, (list, tuple)):
            for item in c_skills:
                if isinstance(item, dict):
                    sk_name = item.get('skill', '')
                    src = item.get('source', '')
                    conf = float(item.get('confidence', 0.2))
                    if sk_name:
                        if conf >= 1.0 or src in ('quiz_verified', 'verified'):
                            verified_skills.add(sk_name.strip().lower())
                        elif src == 'self_declared':
                            self_declared_skills.add(sk_name.strip().lower())
                            bare_skills.append(sk_name.strip())
                        else:
                            bare_skills.append(sk_name.strip())
                elif isinstance(item, str) and item.strip():
                    bare_skills.append(item.strip())

    # 2. Parse structured_json if present
    s_json = candidate.get('structured_json')
    intel = None
    if s_json:
        if isinstance(s_json, dict):
            intel = s_json
        elif isinstance(s_json, str) and s_json.strip():
            try:
                intel = json.loads(s_json)
            except Exception:
                intel = None

    if intel and isinstance(intel, dict):
        sections = intel.get('sections') or {}
        if isinstance(sections, dict):
            if sections.get('experience'):
                exp_parts.append(str(sections['experience']))
            if sections.get('projects'):
                proj_parts.append(str(sections['projects']))
            if sections.get('skills'):
                bare_skills.append(str(sections['skills']))

        for item in intel.get('experience') or []:
            if isinstance(item, dict):
                for k in ('responsibilities', 'description', 'role', 'title', 'company'):
                    val = item.get(k)
                    if isinstance(val, list):
                        exp_parts.extend(str(x) for x in val if x)
                    elif isinstance(val, str) and val:
                        exp_parts.append(val)
            elif isinstance(item, str) and item:
                exp_parts.append(item)

        for item in intel.get('projects') or []:
            if isinstance(item, dict):
                for k in ('description', 'name', 'technologies', 'summary'):
                    val = item.get(k)
                    if isinstance(val, list):
                        proj_parts.extend(str(x) for x in val if x)
                    elif isinstance(val, str) and val:
                        proj_parts.append(val)
            elif isinstance(item, str) and item:
                proj_parts.append(item)

        for s in intel.get('skills') or []:
            if isinstance(s, dict) and s.get('name'):
                bare_skills.append(str(s['name']))
            elif isinstance(s, str) and s:
                bare_skills.append(s)

        if intel.get('verified_skills'):
            v = intel['verified_skills']
            if isinstance(v, (set, list, tuple)):
                verified_skills.update(s.strip().lower() for s in v if isinstance(s, str) and s.strip())

    # 3. Direct candidate fields
    if candidate.get('experience_lines'):
        lines = candidate['experience_lines']
        if isinstance(lines, list):
            exp_parts.extend(str(x) for x in lines if x)
        elif isinstance(lines, str):
            exp_parts.append(lines)

    if candidate.get('experience'):
        exp = candidate['experience']
        if isinstance(exp, list):
            for item in exp:
                if isinstance(item, dict):
                    exp_parts.extend(str(v) for v in item.values() if v and isinstance(v, str))
                elif isinstance(item, str) and item:
                    exp_parts.append(item)
        elif isinstance(exp, str) and exp:
            exp_parts.append(exp)

    if candidate.get('projects'):
        projs = candidate['projects']
        if isinstance(projs, list):
            for item in projs:
                if isinstance(item, dict):
                    proj_parts.extend(str(v) for v in item.values() if v and isinstance(v, str))
                elif isinstance(item, str) and item:
                    proj_parts.append(item)
        elif isinstance(projs, str) and projs:
            proj_parts.append(projs)

    if candidate.get('project_lines'):
        lines = candidate['project_lines']
        if isinstance(lines, list):
            proj_parts.extend(str(x) for x in lines if x)
        elif isinstance(lines, str):
            proj_parts.append(lines)

    if isinstance(candidate.get('sections'), dict):
        sec = candidate['sections']
        if sec.get('experience'):
            exp_parts.append(str(sec['experience']))
        if sec.get('projects'):
            proj_parts.append(str(sec['projects']))
        if sec.get('skills'):
            bare_skills.append(str(sec['skills']))

    if candidate.get('skills'):
        sk = candidate['skills']
        if isinstance(sk, list):
            bare_skills.extend(str(x) for x in sk if x)
        elif isinstance(sk, str):
            bare_skills.extend([s.strip() for s in sk.split(',') if s.strip()])

    return {
        'experience_text': " \n ".join(exp_parts),
        'projects_text': " \n ".join(proj_parts),
        'bare_skills': bare_skills,
        'self_declared_skills': self_declared_skills,
        'verified_skills': verified_skills
    }


def compute_candidate_score(
    candidate: dict,
    job_skills: list[str],
    verified_skills: Optional[Union[set[str], list[str]]] = None
) -> dict:
    """
    Compute a composite ranking score for one candidate against a job using
    Evidence-Weighted Skill Matching:
      - 1.0 weight: Experience bullet points / work narrative
      - 0.7 weight: Project descriptions / portfolio items
      - 0.2 weight: Bare skills list / profile tags
      - 0.2 weight: Blind self-declared skills (Step 6)
      - 1.0 weight: Quiz-verified skills

    Args:
        candidate: Dict with keys: skills, ats_score, experience_lines,
                   education, projects, structured_json, verified_skills, etc.
        job_skills: Required skills for the target job.
        verified_skills: Optional set/list of verified skills for this candidate.

    Returns:
        Dict with 'total_score', per-dimension sub-scores, and skill evidence breakdown.
    """
    evidence = extract_candidate_evidence(candidate)

    # Merge explicitly passed verified_skills
    active_verified = set(evidence['verified_skills'])
    if verified_skills:
        active_verified.update(s.strip().lower() for s in verified_skills if isinstance(s, str) and s.strip())

    exp_text = evidence['experience_text']
    proj_text = evidence['projects_text']
    self_decl_set = set(evidence.get('self_declared_skills', set()))
    bare_skills_set = {s.strip().lower() for s in evidence['bare_skills'] if s.strip()}
    bare_skills_text = " , ".join(evidence['bare_skills'])

    # ── Skills Match (40% weight with Evidence Tiers)
    clean_job_skills = [s.strip() for s in job_skills if s.strip()]
    skill_evidence: Dict[str, Dict[str, Any]] = {}
    evidence_counts = {'verified': 0, 'experience': 0, 'project': 0, 'self_declared': 0, 'list': 0, 'missing': 0}
    total_evidence_weight = 0.0

    if clean_job_skills:
        for skill in clean_job_skills:
            s_lower = skill.lower()

            # Tier 1: Quiz Verified (1.0)
            if s_lower in active_verified:
                w = EVIDENCE_WEIGHTS['verified']
                src = 'verified'
            # Tier 1: Work Experience Narrative (1.0)
            elif match_skill_in_text(skill, exp_text):
                w = EVIDENCE_WEIGHTS['experience']
                src = 'experience'
            # Tier 2: Project Narrative (0.7)
            elif match_skill_in_text(skill, proj_text):
                w = EVIDENCE_WEIGHTS['project']
                src = 'project'
            # Tier 3: Blind Self-Declared Skill (0.2)
            elif s_lower in self_decl_set:
                w = EVIDENCE_WEIGHTS['self_declared']
                src = 'self_declared'
            # Tier 3: Bare Skill List (0.2)
            elif s_lower in bare_skills_set or match_skill_in_text(skill, bare_skills_text):
                w = EVIDENCE_WEIGHTS['list']
                src = 'list'
            # Tier 4: Missing (0.0)
            else:
                w = EVIDENCE_WEIGHTS['missing']
                src = 'missing'

            skill_evidence[skill] = {'weight': w, 'source': src}
            evidence_counts[src] += 1
            total_evidence_weight += w

        overlap_ratio = total_evidence_weight / len(clean_job_skills)
        skills_score = round(overlap_ratio * WEIGHTS['skills_match'])
    else:
        overlap_ratio = 0.0
        skills_score = 0

    # ── ATS score (20%)
    ats_raw   = min(int(candidate.get('ats_score', 0)), 100)
    ats_score = round((ats_raw / 100) * WEIGHTS['ats_score'])

    # ── Experience (25%)
    exp_lines = candidate.get('experience_lines', [])
    exp_count = len(exp_lines) if isinstance(exp_lines, list) else 0
    total_years = candidate.get('total_experience_years') or candidate.get('exp_years') or 0
    effective_exp = max(exp_count, float(total_years))
    # Normalise: 5+ experience lines or 5+ years → full score
    exp_score = round(min(effective_exp / 5.0, 1.0) * WEIGHTS['experience'])

    # ── Education (15%)
    education = (candidate.get('education') or '').lower()
    edu_score = 0
    if any(kw in education for kw in ['phd', 'master', 'm.tech', 'm.sc']):
        edu_score = WEIGHTS['education']
    elif any(kw in education for kw in ['bachelor', 'b.tech', 'b.sc', 'bca', 'b.e']):
        edu_score = round(WEIGHTS['education'] * 0.80)
    elif any(kw in education for kw in ['diploma', 'hsc']):
        edu_score = round(WEIGHTS['education'] * 0.50)
    else:
        edu_score = round(WEIGHTS['education'] * 0.30)

    total = skills_score + ats_score + exp_score + edu_score

    return {
        'total_score':        min(total, 100),
        'skills_score':       skills_score,
        'ats_score':          ats_score,
        'exp_score':          exp_score,
        'edu_score':          edu_score,
        'breakdown': {
            'skills_score': skills_score,
            'ats_score':    ats_score,
            'exp_score':    exp_score,
            'edu_score':    edu_score
        },
        'skill_evidence':     skill_evidence,
        'evidence_breakdown': evidence_counts,
        'evidence_counts':    evidence_counts,
        'weighted_overlap':   round(overlap_ratio, 4),
    }


def rank_candidates(
    candidates: list[dict],
    job_skills: list[str],
    verified_skills: Optional[Union[set[str], list[str]]] = None
) -> list[dict]:
    """
    Rank a list of candidate dicts by composite evidence-weighted score.

    Args:
        candidates: List of candidate dicts.
        job_skills: Required job skills for the position.
        verified_skills: Optional global or per-session verified skills.

    Returns:
        Sorted list (highest score first) with 'rank' and 'rank_score' fields added.
    """
    scored = []
    for cand in candidates:
        cand_verified = cand.get('verified_skills') or verified_skills
        scores = compute_candidate_score(cand, job_skills, verified_skills=cand_verified)
        c = dict(cand)
        c['rank_score']   = scores['total_score']
        c['score_detail'] = scores
        scored.append(c)

    scored.sort(key=lambda x: x['rank_score'], reverse=True)

    for i, c in enumerate(scored):
        c['rank'] = i + 1

    logger.info(f"rank_candidates: ranked {len(scored)} candidates.")
    return scored

