# ============================================================
#  TalentSync — Clustering Analysis Module
#  Groups candidates into skill-based clusters using K-Means.
#
#  Each candidate is represented by their skills string.
#  TF-IDF vectorizes the skills, K-Means finds groups.
#
#  Output cluster labels are mapped to human-readable names
#  so the HR dashboard shows "Python / Data Science" instead of "Cluster 2".
# ============================================================

import re

# Human-readable cluster names (HR-friendly labels)
# These are determined dynamically based on top keywords per cluster
FALLBACK_LABELS = [
    "Python / Data Science",
    "Frontend / UI Developer",
    "DevOps / Cloud Engineer",
    "Java / Backend Developer",
    "General / Mixed Skills"
]


def _get_dominant_label(terms: list[str]) -> str:
    """Map top TF-IDF terms to a readable HR label."""
    term_set = set(t.lower() for t in terms)

    if any(t in term_set for t in ['python', 'tensorflow', 'pytorch', 'pandas', 'ml', 'machine learning', 'data science', 'nlp']):
        return "🐍 Python / Data Science"
    if any(t in term_set for t in ['react', 'vue', 'angular', 'javascript', 'css', 'html', 'frontend', 'ui', 'ux']):
        return "🎨 Frontend / UI Developer"
    if any(t in term_set for t in ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform', 'devops', 'ci/cd', 'jenkins']):
        return "☁️ DevOps / Cloud Engineer"
    if any(t in term_set for t in ['java', 'spring', 'hibernate', 'backend', 'microservices', 'kafka', 'rest api']):
        return "☕ Java / Backend Developer"
    if any(t in term_set for t in ['sql', 'mysql', 'postgresql', 'mongodb', 'database', 'dba']):
        return "🗄️ Database / Data Engineer"
    if any(t in term_set for t in ['android', 'ios', 'flutter', 'react native', 'mobile', 'swift', 'kotlin']):
        return "📱 Mobile Developer"

    return "🔧 General / Mixed Skills"


def cluster_candidates(candidates: list[dict], n_clusters: int = 5) -> list[dict]:
    """
    Takes a list of candidate dicts (must have 'skills' key).
    Returns the same list with a new 'cluster_label' key added to each candidate.

    Falls back gracefully if sklearn is unavailable or candidates < n_clusters.

    Example input:
        [{'name': 'Rahul', 'skills': 'Python,ML,TensorFlow', ...}, ...]
    Example output:
        [{'name': 'Rahul', 'skills': '...', 'cluster_label': '🐍 Python / Data Science'}, ...]
    """
    if not candidates:
        return candidates

    # Extract skill strings; default to empty string if missing
    skill_texts = [c.get('skills') or '' for c in candidates]

    # If too few candidates for clustering, use label-matching directly
    if len(candidates) < n_clusters:
        for candidate in candidates:
            skills = candidate.get('skills') or ''
            terms  = re.split(r'[,\s]+', skills.lower())
            candidate['cluster_label'] = _get_dominant_label(terms)
        return candidates

    # --- K-Means Clustering ---
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import KMeans

        vectorizer  = TfidfVectorizer(max_features=200, stop_words='english')
        skill_matrix = vectorizer.fit_transform(skill_texts)

        actual_clusters = min(n_clusters, len(candidates))
        kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init='auto', max_iter=300)
        cluster_ids = kmeans.fit_predict(skill_matrix)

        # Get top terms per cluster center to determine HR-friendly label
        feature_names = vectorizer.get_feature_names_out()
        cluster_name_map = {}

        for cluster_id in range(actual_clusters):
            center     = kmeans.cluster_centers_[cluster_id]
            top_indices = center.argsort()[-5:][::-1]   # top 5 terms
            top_terms   = [str(feature_names[i]) for i in top_indices]
            cluster_name_map[cluster_id] = _get_dominant_label(top_terms)

        # Assign labels back to each candidate
        for i, candidate in enumerate(candidates):
            candidate['cluster_label'] = cluster_name_map.get(cluster_ids[i], "🔧 General / Mixed Skills")

    except Exception:
        # Graceful fallback — just use keyword matching
        for candidate in candidates:
            skills = candidate.get('skills') or ''
            terms  = re.split(r'[,\s]+', skills.lower())
            candidate['cluster_label'] = _get_dominant_label(terms)

    return candidates


def get_cluster_groups(candidates: list[dict]) -> dict:
    """
    After cluster_candidates() has been called, group them by cluster label.
    Returns a dict: { 'cluster_label': [list of candidates] }

    Useful for the Admin Dashboard 'View by Cluster' feature.
    """
    groups: dict = {}
    for c in candidates:
        label = c.get('cluster_label', '🔧 General / Mixed Skills')
        if label not in groups:
            groups[label] = []
        groups[label].append(c)

    # Sort each group by ATS score descending
    for label in groups:
        groups[label].sort(key=lambda x: x.get('ats_score') or 0, reverse=True)

    return groups
