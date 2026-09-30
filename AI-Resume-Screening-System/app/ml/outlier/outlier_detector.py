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

    # --- Method 1: IsolationForest (for 10+ candidates, more accurate) ---
    if len(scores) >= 10:
        try:
            from sklearn.ensemble import IsolationForest
            score_array = np.array(scores).reshape(-1, 1)
            model = IsolationForest(contamination='auto', random_state=42)
            predictions = model.fit_predict(score_array)
            # IsolationForest: -1 = outlier, 1 = normal
            is_outlier_ml = [p == -1 for p in predictions]
        except ImportError:
            is_outlier_ml = [False] * len(scores)
    else:
        is_outlier_ml = [False] * len(scores)

    # --- Method 2: Hard threshold rules (always applied as safety net) ---
    LOW_THRESHOLD  = 15   # Below this = likely spam/bot
    HIGH_THRESHOLD = 95   # Above this = likely keyword-stuffed

    for i, candidate in enumerate(candidates):
        score = scores[i]
        flagged_by_ml = is_outlier_ml[i]

        if score < LOW_THRESHOLD:
            candidate['outlier_flag']   = True
            candidate['outlier_reason'] = '⚠️ Suspicious: Very low ATS score (possible spam resume)'
        elif score > HIGH_THRESHOLD:
            candidate['outlier_flag']   = True
            candidate['outlier_reason'] = '⚠️ Suspicious: Extremely high score (possible keyword stuffing)'
        elif flagged_by_ml:
            candidate['outlier_flag']   = True
            candidate['outlier_reason'] = '⚠️ Statistical anomaly detected by AI model'
        else:
            candidate['outlier_flag']   = False
            candidate['outlier_reason'] = ''

    return candidates
