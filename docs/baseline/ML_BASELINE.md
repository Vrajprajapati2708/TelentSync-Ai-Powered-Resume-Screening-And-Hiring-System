# HireAI / TalentSync — Machine Learning Baseline

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Audit  

---

## 1. Trained Model Inventory (`trained_models/`)

| Model Name | Directory Path | Architecture / Type | Serialized Format | Key Metadata |
| :--- | :--- | :--- | :--- | :--- |
| **`spacy_skill_ner`** | `V:\HireAI_Website-main (2)\trained_models\spacy_skill_ner` | Custom spaCy NER Pipeline (`ner` component) | spaCy model binary + `config.cfg` | Epochs: 30, Best F1: 0.9974, Label: `SKILL` |
| **`tfidf_recommender`**| `V:\HireAI_Website-main (2)\trained_models\tfidf_recommender` | Scikit-Learn `TfidfVectorizer` | Pickle binary (`tfidf_vectorizer.pkl`) | Vocab Size: 4,206, Max Features: 8,000, N-gram: (1, 2) |

---

## 2. Version Comparison & Compatibility Assessment

| Component | Training Version | Current Installed Version | Status & Compatibility |
| :--- | :--- | :--- | :--- |
| **`spacy`** | `v3.7.2` / `v3.8.x` | **`3.8.13`** | ✅ Functional, loads cleanly in runtime |
| **`scikit-learn`**| `1.4.0` | **`1.9.0`** | ⚠️ `InconsistentVersionWarning` on unpickling |
| **`numpy`** | NumPy 1.x | **`2.5.1`** | ⚠️ `DeprecationWarning` regarding array shape pickling |
| **`joblib`** | Older joblib | **`1.5.3`** | Functional |

---

## 3. Training Scripts & Datasets

- **Master Trainer**: `app/ml/training/train_all.py`
  - Runs dataset generation (`generate_dataset.py`)
  - Trains spaCy NER model (`train_skill_ner.py`)
  - Trains TF-IDF Recommender (`train_recommender.py`)
  - Outputs model health report
- **Synthetic Training Data**:
  - Resumes dataset: 600 synthetic resumes
  - Job descriptions: 200 synthetic job descriptions across 10 industry roles
- **Taxonomy Database**: `app/ml/skill_extraction/skills_db.py`
  - 500+ technical skills categorized into Backend, Frontend, Cloud/DevOps, Data/ML, Mobile, Database, and Core Engineering.
