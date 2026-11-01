"""
TalentSync — Candidate Skills Service (Step 6: Blind Skill Confirmation)
Handles candidate self-declared skills, resume-extracted skills, and skill provenance tracking.

Anti-Gaming Principles:
1. Accidental Omission Fix: Candidates can declare skills blindly before viewing job gap prompts.
2. Evidence Weighting:
   - Experience narrative: 1.0 (verified by work bullets)
   - Project narrative: 0.7 (verified by projects)
   - Self-declared blind: 0.2 (unverified self-claim, matching bare list weight)
   - Quiz verified: 1.0 (Step 8)
3. Non-Degradation: Declaring a skill blindly will never overwrite or downgrade a higher-tier
   confidence skill (e.g., from experience 1.0 or quiz 1.0 down to 0.2).
"""

import json
from typing import List, Dict, Any, Optional, Union
from app.database.connection import get_db
from app.ml.ranking.ranking_engine import match_skill_in_text, extract_candidate_evidence
from app.utils.logger import get_logger

logger = get_logger(__name__)


def normalize_skill(skill: str) -> str:
    """Normalize skill string: stripped, collapsed whitespace, clamped to 50 chars."""
    if not skill or not isinstance(skill, str):
        return ""
    clean = " ".join(skill.strip().split())
    return clean[:50]


def get_candidate_skills(user_id: int) -> List[Dict[str, Any]]:
    """
    Retrieve all confirmed skills for a candidate with source, confidence, and status.
    Ordered by confidence DESC, skill ASC.
    """
    if not user_id:
        return []

    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, skill, source, confidence, confirmed_at 
               FROM candidate_skills 
               WHERE user_id=? 
               ORDER BY confidence DESC, skill ASC""",
            (user_id,)
        ).fetchall()

        if not rows:
            # Fallback: check users table and backfill
            u_row = conn.execute("SELECT skills FROM users WHERE id=?", (user_id,)).fetchone()
            if u_row and u_row['skills']:
                skills_list = [s.strip() for s in u_row['skills'].split(',') if s.strip()]
                for s in skills_list:
                    try:
                        conn.execute(
                            """INSERT OR IGNORE INTO candidate_skills 
                               (user_id, skill, source, confidence) 
                               VALUES (?, ?, 'resume_extracted', 0.2)""",
                            (user_id, s)
                        )
                    except Exception:
                        pass
                conn.commit()

                rows = conn.execute(
                    """SELECT id, skill, source, confidence, confirmed_at 
                       FROM candidate_skills 
                       WHERE user_id=? 
                       ORDER BY confidence DESC, skill ASC""",
                    (user_id,)
                ).fetchall()

        results = []
        for r in rows:
            conf = float(r['confidence'] or 0.2)
            src = r['source'] or 'self_declared'
            if conf >= 1.0:
                status_label = "Verified (Experience / Assessment)" if src != 'quiz_verified' else "Quiz Verified (1.0)"
            elif conf >= 0.7:
                status_label = "Project Demonstrated (0.7)"
            else:
                status_label = "Self-Declared (0.2)"

            results.append({
                'id': r['id'],
                'skill': r['skill'],
                'skill_name': r['skill'],
                'source': src,
                'confidence': conf,
                'evidence_weight': conf,
                'confirmed_at': r['confirmed_at'],
                'status': status_label
            })

        return results


def declare_blind_skills(
    user_id: int,
    skills_input: Union[List[str], str],
    source: str = 'self_declared'
) -> Dict[str, Any]:
    """
    Candidate blindly confirms or declares skills they possess.
    - Input can be a list of skill strings or comma-separated string.
    - Automatically avoids duplicates case-insensitively.
    - Prevents downgrading existing high-confidence skills (1.0 or 0.7).
    - Syncs aggregate skills back to users.skills for platform consistency.
    """
    if not user_id:
        return {'success': False, 'message': 'Valid user_id is required.'}

    raw_items: List[str] = []
    if isinstance(skills_input, str):
        raw_items = [s.strip() for s in skills_input.split(',') if s.strip()]
    elif isinstance(skills_input, list):
        for item in skills_input:
            if isinstance(item, str):
                raw_items.append(item.strip())
            elif isinstance(item, dict) and item.get('skill'):
                raw_items.append(str(item['skill']).strip())

    cleaned_skills: List[str] = []
    seen_lower = set()
    for s in raw_items:
        norm = normalize_skill(s)
        if norm and len(norm) >= 2 and norm.lower() not in seen_lower:
            seen_lower.add(norm.lower())
            cleaned_skills.append(norm)

    if not cleaned_skills:
        return {'success': False, 'message': 'No valid skill names provided to confirm.'}

    added = []
    updated = []
    default_conf = 0.2 if source == 'self_declared' else 0.2

    with get_db() as conn:
        # Fetch current candidate skills to protect confidence tiers
        existing_rows = conn.execute(
            "SELECT skill, source, confidence FROM candidate_skills WHERE user_id=?",
            (user_id,)
        ).fetchall()
        existing_map = {r['skill'].lower(): (r['skill'], r['source'], float(r['confidence'] or 0.2)) for r in existing_rows}

        for sk in cleaned_skills:
            sk_lower = sk.lower()
            if sk_lower in existing_map:
                curr_name, curr_src, curr_conf = existing_map[sk_lower]
                # Non-degradation rule: If already present with >= 0.7, retain higher confidence
                if curr_conf >= 0.7:
                    # Update confirmed_at timestamp only
                    conn.execute(
                        "UPDATE candidate_skills SET confirmed_at=datetime('now') WHERE user_id=? AND LOWER(skill)=?",
                        (user_id, sk_lower)
                    )
                    updated.append(curr_name)
                else:
                    # Refresh confirmation
                    conn.execute(
                        """UPDATE candidate_skills 
                           SET source=?, confidence=?, confirmed_at=datetime('now') 
                           WHERE user_id=? AND LOWER(skill)=?""",
                        (source, default_conf, user_id, sk_lower)
                    )
                    updated.append(sk)
            else:
                # Insert new self-declared skill
                conn.execute(
                    """INSERT INTO candidate_skills (user_id, skill, source, confidence, confirmed_at)
                       VALUES (?, ?, ?, ?, datetime('now'))""",
                    (user_id, sk, source, default_conf)
                )
                added.append(sk)

        # Sync back to users table
        all_candidate_skills = conn.execute(
            "SELECT skill FROM candidate_skills WHERE user_id=? ORDER BY skill ASC",
            (user_id,)
        ).fetchall()
        merged_str = ", ".join(r['skill'] for r in all_candidate_skills)
        conn.execute("UPDATE users SET skills=? WHERE id=?", (merged_str, user_id))
        conn.commit()

    all_updated = get_candidate_skills(user_id)
    return {
        'success': True,
        'message': f"Confirmed {len(added)} new skill(s) blindly and updated {len(updated)} skill(s).",
        'added': added,
        'updated': updated,
        'total_count': len(all_updated),
        'skills': all_updated
    }


def remove_candidate_skill(user_id: int, skill_to_remove: str) -> Dict[str, Any]:
    """Remove a skill from the candidate's confirmed skills profile."""
    if not user_id or not skill_to_remove:
        return {'success': False, 'message': 'User ID and skill name are required.'}

    target = normalize_skill(skill_to_remove)
    with get_db() as conn:
        deleted = conn.execute(
            "DELETE FROM candidate_skills WHERE user_id=? AND LOWER(skill)=LOWER(?)",
            (user_id, target)
        ).rowcount

        if deleted > 0:
            all_candidate_skills = conn.execute(
                "SELECT skill FROM candidate_skills WHERE user_id=? ORDER BY skill ASC",
                (user_id,)
            ).fetchall()
            merged_str = ", ".join(r['skill'] for r in all_candidate_skills)
            conn.execute("UPDATE users SET skills=? WHERE id=?", (merged_str, user_id))
            conn.commit()
            return {'success': True, 'message': f"Skill '{target}' removed successfully."}
        else:
            return {'success': False, 'message': f"Skill '{target}' not found in candidate profile."}


def sync_resume_extracted_skills(
    user_id: int,
    extracted_skills: List[str],
    structured_json: Optional[Union[Dict[str, Any], str]] = None
) -> List[Dict[str, Any]]:
    """
    Sync skills parsed from a newly uploaded resume into `candidate_skills`.
    Assigns evidence tiers:
      - 1.0 if skill is found in work experience narrative
      - 0.7 if skill is found in project narrative
      - 0.2 if skill appears only in bare extracted list
    Does not downgrade any quiz-verified (1.0) skills.
    """
    if not user_id or not extracted_skills:
        return []

    # Prepare evidence context
    cand_proxy: Dict[str, Any] = {'skills': extracted_skills}
    if structured_json:
        cand_proxy['structured_json'] = structured_json

    evidence = extract_candidate_evidence(cand_proxy)
    exp_text = evidence['experience_text']
    proj_text = evidence['projects_text']

    with get_db() as conn:
        existing_rows = conn.execute(
            "SELECT skill, source, confidence FROM candidate_skills WHERE user_id=?",
            (user_id,)
        ).fetchall()
        existing_map = {r['skill'].lower(): (r['skill'], r['source'], float(r['confidence'] or 0.2)) for r in existing_rows}

        for sk in extracted_skills:
            norm = normalize_skill(sk)
            if not norm:
                continue

            # Determine appropriate evidence tier
            if match_skill_in_text(norm, exp_text):
                conf = 1.0
                src = 'experience'
            elif match_skill_in_text(norm, proj_text):
                conf = 0.7
                src = 'project'
            else:
                conf = 0.2
                src = 'resume_extracted'

            sk_lower = norm.lower()
            if sk_lower in existing_map:
                curr_name, curr_src, curr_conf = existing_map[sk_lower]
                # If existing is quiz_verified or has higher confidence, do not downgrade
                if curr_conf > conf:
                    continue
                conn.execute(
                    """UPDATE candidate_skills 
                       SET source=?, confidence=?, confirmed_at=datetime('now') 
                       WHERE user_id=? AND LOWER(skill)=?""",
                    (src, conf, user_id, sk_lower)
                )
            else:
                conn.execute(
                    """INSERT INTO candidate_skills (user_id, skill, source, confidence, confirmed_at) 
                       VALUES (?, ?, ?, ?, datetime('now'))""",
                    (user_id, norm, src, conf)
                )

        # Sync back to users table
        all_candidate_skills = conn.execute(
            "SELECT skill FROM candidate_skills WHERE user_id=? ORDER BY skill ASC",
            (user_id,)
        ).fetchall()
        merged_str = ", ".join(r['skill'] for r in all_candidate_skills)
        conn.execute("UPDATE users SET skills=? WHERE id=?", (merged_str, user_id))
        conn.commit()

    return get_candidate_skills(user_id)
