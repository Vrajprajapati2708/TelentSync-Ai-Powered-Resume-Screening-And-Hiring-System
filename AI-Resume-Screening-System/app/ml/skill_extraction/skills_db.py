# ============================================================
#  TalentSync — Skills Database
#  Central source-of-truth for all recognisable skills.
#  Extend this list to add new technologies.
# ============================================================

# ── Programming Languages ─────────────────────────────────
PROGRAMMING_LANGUAGES = [
    'python', 'java', 'c++', 'c', 'c#', 'javascript', 'typescript',
    'r', 'scala', 'kotlin', 'swift', 'go', 'rust', 'ruby', 'php',
    'matlab', 'julia', 'perl', 'bash', 'shell'
]

# ── Web & Frameworks ──────────────────────────────────────
WEB_FRAMEWORKS = [
    'html', 'css', 'react', 'angular', 'vue.js', 'node.js',
    'flask', 'django', 'fastapi', 'express', 'spring', 'laravel',
    'bootstrap', 'tailwind'
]

# ── Data Science & ML ─────────────────────────────────────
DATA_SCIENCE = [
    'machine learning', 'deep learning', 'nlp', 'natural language processing',
    'computer vision', 'data science', 'statistics', 'data analysis',
    'data mining', 'feature engineering', 'model deployment',
    'a/b testing', 'time series', 'reinforcement learning'
]

# ── ML Libraries ─────────────────────────────────────────
ML_LIBRARIES = [
    'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'keras',
    'xgboost', 'lightgbm', 'opencv', 'nltk', 'spacy', 'hugging face',
    'transformers', 'langchain', 'matplotlib', 'seaborn', 'plotly'
]

# ── Databases ─────────────────────────────────────────────
DATABASES = [
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'sqlite',
    'cassandra', 'elasticsearch', 'oracle', 'firebase', 'dynamodb'
]

# ── Cloud & DevOps ───────────────────────────────────────
CLOUD_DEVOPS = [
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
    'jenkins', 'ci/cd', 'github actions', 'ansible', 'linux', 'git'
]

# ── BI & Analytics ────────────────────────────────────────
BI_TOOLS = [
    'tableau', 'power bi', 'excel', 'looker', 'qlik', 'metabase',
    'google analytics', 'hadoop', 'spark', 'hive', 'kafka'
]

# ── Soft Skills ───────────────────────────────────────────
SOFT_SKILLS = [
    'communication', 'leadership', 'teamwork', 'problem solving',
    'critical thinking', 'time management', 'agile', 'scrum'
]

# ── Master Skill List ─────────────────────────────────────
ALL_SKILLS = (
    PROGRAMMING_LANGUAGES +
    WEB_FRAMEWORKS +
    DATA_SCIENCE +
    ML_LIBRARIES +
    DATABASES +
    CLOUD_DEVOPS +
    BI_TOOLS
)

# Skills by category (used for gap analysis)
SKILL_CATEGORIES = {
    'Programming Languages': PROGRAMMING_LANGUAGES,
    'Web & Frameworks':      WEB_FRAMEWORKS,
    'Data Science & ML':     DATA_SCIENCE,
    'ML Libraries':          ML_LIBRARIES,
    'Databases':             DATABASES,
    'Cloud & DevOps':        CLOUD_DEVOPS,
    'BI & Analytics':        BI_TOOLS,
    'Soft Skills':           SOFT_SKILLS,
}

# Role → required skills mapping (used for skill gap analysis)
JOB_ROLE_SKILLS = {
    'Data Scientist':   ['python', 'machine learning', 'pandas', 'sql', 'statistics', 'scikit-learn'],
    'ML Engineer':      ['python', 'tensorflow', 'pytorch', 'docker', 'deep learning', 'mlflow'],
    'Data Analyst':     ['sql', 'excel', 'tableau', 'power bi', 'statistics', 'python'],
    'NLP Engineer':     ['python', 'nlp', 'spacy', 'transformers', 'pytorch', 'tensorflow'],
    'Data Engineer':    ['python', 'sql', 'spark', 'hadoop', 'aws', 'docker'],
    'Python Developer': ['python', 'django', 'flask', 'postgresql', 'git', 'docker'],
    'Cloud Architect':  ['aws', 'azure', 'kubernetes', 'terraform', 'docker', 'linux'],
}
