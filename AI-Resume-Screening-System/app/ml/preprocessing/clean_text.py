# ============================================================
#  TalentSync — Text Preprocessing
#  Cleans raw resume / job-description text before NLP.
# ============================================================

import re
import string


# Common English stopwords (no NLTK dependency required)
STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
    'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were',
    'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
    'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this',
    'that', 'these', 'those', 'i', 'we', 'you', 'he', 'she', 'they',
    'it', 'my', 'our', 'your', 'his', 'her', 'their', 'its', 'as',
    'if', 'not', 'no', 'so', 'than', 'then', 'when', 'where', 'who',
    'which', 'what', 'how', 'all', 'each', 'also', 'into', 'about',
    'up', 'out', 'more', 'such', 'only', 'after', 'before', 'while',
    'through', 'over', 'between', 'both', 'during', 'without', 'within'
}


def clean_text(text: str) -> str:
    """
    Full text cleaning pipeline:
    1. Lowercase
    2. Remove URLs
    3. Remove email addresses
    4. Remove special characters (keep hyphens inside words)
    5. Remove extra whitespace
    """
    if not text:
        return ""

    text = text.lower()

    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)

    # Remove emails
    text = re.sub(r'\S+@\S+\.\S+', ' ', text)

    # Remove punctuation except hyphens between word characters
    text = re.sub(r'(?<!\w)-(?!\w)', ' ', text)     # isolated hyphens → space
    text = re.sub(r'[^\w\s\-\+\#\.]', ' ', text)   # keep + # . (for C++, C#, Node.js)

    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def tokenize(text: str) -> list[str]:
    """Split cleaned text into a list of tokens."""
    return text.split()


def remove_stopwords(tokens: list[str]) -> list[str]:
    """Filter out common English stopwords."""
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def preprocess(text: str) -> list[str]:
    """
    Full preprocessing pipeline:
    clean → tokenize → remove stopwords
    Returns a list of meaningful tokens.
    """
    cleaned  = clean_text(text)
    tokens   = tokenize(cleaned)
    filtered = remove_stopwords(tokens)
    return filtered


def preprocess_to_string(text: str) -> str:
    """Same as preprocess() but returns a single joined string (useful for TF-IDF)."""
    return ' '.join(preprocess(text))
