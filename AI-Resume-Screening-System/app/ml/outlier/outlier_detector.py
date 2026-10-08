# ============================================================
#  TalentSync — Outlier Detection Module
#  Detects suspicious ATS scores in the candidate pool.
#
#  Logic:
#    - Score < 15  → Likely spam / empty resume
#    - Score > 95  → Likely keyword-stuffed resume
#    - Otherwise   → Normal
#
#  Uses IsolationForest (sklearn) when >= 10 candidates exist.
#  Falls back to simple threshold logic for small datasets.
# ============================================================

import numpy as np

def detect_outliers(candidates: list[dict]) -> list[dict]:
    """
    Takes a list of candidate dicts (must have 'ats_score' key).
    Returns the same list with a new 'outlier_flag' and 'outlier_reason' key added.

    Example input:
        [{'name': 'Rahul', 'ats_score': 78, ...}, ...]
    Example output:
        [{'name': 'Rahul', 'ats_score': 78, 'outlier_flag': False, 'outlier_reason': ''}, ...]
    """
    if not candidates:
        return candidates

    scores = [c.get('ats_score') or 0 for c in candidates]

    # Filter non-zero scores for ML modeling
    valid_indices = [i for i, s in enumerate(scores) if s > 0]
    is_outlier_ml = [False] * len(scores)

    # --- Method 1: IsolationForest (only on candidates who actually have uploaded resumes) ---
    if len(valid_indices) >= 20:
        try:
            from sklearn.ensemble import IsolationForest
            valid_scores = np.array([scores[i] for i in valid_indices]).reshape(-1, 1)
            model = IsolationForest(contamination=0.02, random_state=42)
            preds = model.fit_predict(valid_scores)
            for idx_in_valid, orig_idx in enumerate(valid_indices):
                if preds[idx_in_valid] == -1:
                    is_outlier_ml[orig_idx] = True
        except Exception:
            pass

    # --- Method 2: Threshold rules ---
    # Score == 0 means candidate has not uploaded a resume yet -> NOT suspicious.
    # 0 < Score <= 8 with empty/spam text -> Suspicious spam/corrupted resume.
    # Score >= 99 -> Keyword stuffing.
    for i, candidate in enumerate(candidates):
        score = scores[i]
        db_outlier = candidate.get('is_outlier') == 1

        if score == 0:
            # Not uploaded yet -> Clean state
            candidate['outlier_flag'] = False
            candidate['outlier_reason'] = ''
        elif 0 < score <= 8:
            candidate['outlier_flag'] = True
            candidate['outlier_reason'] = '⚠️ Suspicious: Corrupted or unreadable resume text (<8 score)'
        elif score >= 99:
            candidate['outlier_flag'] = True
            candidate['outlier_reason'] = '⚠️ Suspicious: Extremely high score (>98) - possible keyword stuffing'
        elif db_outlier:
            candidate['outlier_flag'] = True
            candidate['outlier_reason'] = '⚠️ Flagged outlier in candidate profile'
        elif is_outlier_ml[i] and (score < 12 or score > 96):
            candidate['outlier_flag'] = True
            candidate['outlier_reason'] = '⚠️ Statistical anomaly detected by AI model'
        else:
            candidate['outlier_flag'] = False
            candidate['outlier_reason'] = ''

    return candidates
