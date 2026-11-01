"""
TalentSync — Learning Timeline Engine & Velocity Anomaly Detection (Step 7)
Analyzes resume version diffs to detect impossible learning velocities and rapid skill acquisition gaming.

Canonical Learning Times:
- Tier 1 (Foundational / Tools): 3 - 7 days (HTML, CSS, Git, Markdown, JSON)
- Tier 2 (Languages & Standard Frameworks): 21 - 45 days (Python, JS, SQL, React, Node, Django)
- Tier 3 (Deep Systems, Cloud & Advanced Architecture): 45 - 90 days (Kubernetes, AWS, Distributed Systems, ML)

Formula:
  Multi-skill required learning days = max(T_skills) + 0.5 * sum(remaining)
  Velocity Ratio = Elapsed Days / Required Learning Days
  If Elapsed Days < Threshold and Required Days is high -> Trigger Velocity Anomaly.
"""

from typing import List, Dict, Any, Tuple, Optional, Set
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Canonical baseline days required for an engineer to gain proficient working knowledge
CANONICAL_LEARNING_DAYS: Dict[str, float] = {
    # Tier 1: Lightweight Tools & Markup (3 - 7 days)
    'markdown': 3.0,
    'json': 3.0,
    'xml': 3.0,
    'yaml': 3.0,
    'html': 5.0,
    'html5': 5.0,
    'css': 7.0,
    'css3': 7.0,
    'git': 7.0,
    'github': 5.0,
    'gitlab': 5.0,
    'jira': 3.0,
    'trello': 2.0,
    'bash': 7.0,
    'shell': 7.0,
    'postman': 5.0,
    'bootstrap': 7.0,
    'tailwind': 7.0,
    'tailwindcss': 7.0,

    # Tier 2: Languages, Frameworks & Core DBs (21 - 45 days)
    'sql': 21.0,
    'mysql': 21.0,
    'postgresql': 25.0,
    'postgres': 25.0,
    'sqlite': 14.0,
    'mongodb': 21.0,
    'redis': 14.0,
    'python': 30.0,
    'javascript': 30.0,
    'typescript': 30.0,
    'php': 25.0,
    'ruby': 30.0,
    'c': 45.0,
    'c#': 40.0,
    'csharp': 40.0,
    'java': 45.0,
    'react': 30.0,
    'reactjs': 30.0,
    'vue': 25.0,
    'vuejs': 25.0,
    'angular': 35.0,
    'svelte': 21.0,
    'node.js': 30.0,
    'nodejs': 30.0,
    'express': 21.0,
    'expressjs': 21.0,
    'flask': 21.0,
    'fastapi': 21.0,
    'django': 35.0,
    'spring': 45.0,
    'springboot': 45.0,
    'rest api': 14.0,
    'restful': 14.0,
    'graphql': 21.0,
    'docker': 25.0,
    'linux': 21.0,

    # Tier 3: Deep Systems, Advanced Cloud, DevOps & AI (45 - 90 days)
    'kubernetes': 60.0,
    'k8s': 60.0,
    'aws': 60.0,
    'amazon web services': 60.0,
    'azure': 60.0,
    'gcp': 60.0,
    'google cloud': 60.0,
    'terraform': 45.0,
    'ansible': 30.0,
    'kafka': 45.0,
    'rabbitmq': 30.0,
    'rust': 60.0,
    'go': 45.0,
    'golang': 45.0,
    'c++': 60.0,
    'cpp': 60.0,
    'microservices': 45.0,
    'distributed systems': 75.0,
    'system design': 60.0,
    'ci/cd': 30.0,
    'elasticsearch': 30.0,
    'spark': 45.0,
    'hadoop': 45.0,
    'machine learning': 75.0,
    'deep learning': 90.0,
    'pytorch': 60.0,
    'tensorflow': 60.0,
    'nlp': 60.0,
    'computer vision': 75.0,
    'llm': 60.0,
    'genai': 60.0,
    'penetration testing': 75.0,
    'cryptography': 75.0
}

DEFAULT_SKILL_LEARNING_DAYS = 14.0


def get_skill_learning_time(skill: str) -> float:
    """Return estimated minimum learning days for a single skill."""
    if not skill or not isinstance(skill, str):
        return 0.0
    s_clean = skill.strip().lower()
    return CANONICAL_LEARNING_DAYS.get(s_clean, DEFAULT_SKILL_LEARNING_DAYS)


def compute_required_learning_time(skills: List[str]) -> float:
    """
    Calculate realistic combined learning time for multiple newly added skills.
    Formula: max(T) + 0.5 * sum(remaining)
    Reflects cognitive multitasking limits.
    """
    if not skills:
        return 0.0

    times = [get_skill_learning_time(s) for s in skills if s and s.strip()]
    if not times:
        return 0.0

    times.sort(reverse=True)
    primary = times[0]
    secondary = sum(times[1:]) * 0.5
    return round(primary + secondary, 1)


def diff_resume_skillsets(
    prev_skills: List[str],
    curr_skills: List[str]
) -> Tuple[List[str], List[str], List[str]]:
    """
    Compare previous resume skills against current resume skills.
    Returns: (added_skills, retained_skills, removed_skills)
    """
    prev_map = {s.strip().lower(): s.strip() for s in prev_skills if s and s.strip()}
    curr_map = {s.strip().lower(): s.strip() for s in curr_skills if s and s.strip()}

    added = [curr_map[k] for k in curr_map if k not in prev_map]
    retained = [curr_map[k] for k in curr_map if k in prev_map]
    removed = [prev_map[k] for k in prev_map if k not in curr_map]

    return added, retained, removed


def detect_velocity_anomaly(
    prev_skills: List[str],
    curr_skills: List[str],
    elapsed_days: float,
    user_prior_skills: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Detect impossible skill velocity across consecutive resume uploads.

    Args:
        prev_skills: Skills parsed from candidate's previous resume.
        curr_skills: Skills parsed from candidate's new resume.
        elapsed_days: Elapsed calendar time in days (e.g. 1.0 = 24 hours, 0.5 = 12 hours).
        user_prior_skills: Optional set of already verified or pre-existing skills for this user.

    Returns:
        Dict detailing anomaly status, severity ('high', 'medium', 'low', 'none'),
        estimated required days, velocity ratio, and actionable flag reason.
    """
    added, retained, removed = diff_resume_skillsets(prev_skills, curr_skills)

    # Exclude skills the user already possessed or confirmed earlier
    if user_prior_skills:
        prior_lower = {s.strip().lower() for s in user_prior_skills if s and s.strip()}
        added = [s for s in added if s.lower() not in prior_lower]

    if not added:
        return {
            'is_anomaly': False,
            'severity': 'none',
            'added_skills': [],
            'elapsed_days': round(elapsed_days, 2),
            'estimated_learning_days': 0.0,
            'velocity_ratio': 1.0,
            'reason': 'No new skills added.'
        }

    required_days = compute_required_learning_time(added)
    safe_elapsed = max(elapsed_days, 0.01)
    velocity_ratio = round(safe_elapsed / required_days, 4)

    is_anomaly = False
    severity = 'none'
    reason = ''

    # Criteria 1: Critical High Anomaly
    # e.g., Added >= 25 days of skills in <= 3 calendar days (72 hours)
    # or velocity ratio < 0.15 for high learning requirement (>= 30 days)
    if (safe_elapsed <= 3.0 and required_days >= 25.0) or (velocity_ratio < 0.15 and required_days >= 30.0):
        is_anomaly = True
        severity = 'high'
        reason = (
            f"Unrealistic Skill Acquisition Anomaly: Added {len(added)} new skill(s) "
            f"({', '.join(added[:5])}{'...' if len(added) > 5 else ''}) in {round(safe_elapsed, 1)} days. "
            f"Estimated realistic learning time is {required_days} days (Velocity Ratio: {velocity_ratio})."
        )
    # Criteria 2: Moderate Anomaly
    # e.g., Added >= 35 days of skills in <= 7 calendar days
    elif (safe_elapsed <= 7.0 and required_days >= 35.0) or (velocity_ratio < 0.30 and required_days >= 40.0):
        is_anomaly = True
        severity = 'medium'
        reason = (
            f"High Learning Velocity Warning: Added {len(added)} skill(s) "
            f"({', '.join(added[:4])}) in {round(safe_elapsed, 1)} days. "
            f"Expected acquisition timeline is {required_days} days."
        )

    return {
        'is_anomaly': is_anomaly,
        'severity': severity,
        'added_skills': added,
        'elapsed_days': round(safe_elapsed, 2),
        'estimated_learning_days': required_days,
        'velocity_ratio': velocity_ratio,
        'flag_reason': reason if is_anomaly else ''
    }
