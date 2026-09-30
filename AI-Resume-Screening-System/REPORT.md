# TalentSync — System Analysis & Debugging Report

## 1. Project Architecture
The project is an AI Resume Screening System consisting of:
- **Web Layer**: Flask application (`app/routes`) providing endpoints for user, admin, and ML services.
- **AI/ML Layer**:
  - NLP parsing using PyPDF2 and `python-docx` (`app/ml/parsers`).
  - TF-IDF recommendation using `scikit-learn` (`app/ml/recommendation`).
  - Named Entity Recognition (NER) for skill extraction using `spaCy` (`app/ml/skill_extraction`).
  - KMeans clustering and Isolation Forests for Candidate Clustering and Anomaly Detection (`app/ml/clustering`, `app/ml/outlier`).
- **Data Layer**: SQLite database (`app/database`) with manual connection handling.

## 2. Folder Structure
```
+---app
|   +---ai
|   +---config
|   +---controllers
|   +---database
|   +---ml
|   +---models
|   +---repositories
|   +---routes
|   +---services
|   +---static
|   +---templates
|   +---utils
+---notebooks
+---tests
+---__pycache__
```

## 3. Frameworks & Versions
- **Flask**: 3.1.3
- **Scikit-learn**: 1.9.0
- **spaCy**: 3.8.13
- **PyPDF2**: 3.0.1
- **SQLite3**: Standard library

## 4. Environment
- **Python Version**: 3.14.6
- **Virtual Environment**: `.venv`
- **Pip Executable**: `.venv\Scripts\pip.exe` (Note: internal hardcoded path points to `(1)` due to workspace cloning)
- **Pytest Executable**: `.venv\Scripts\pytest.exe` (Installed during debug session)

## 5. Dependencies
### Installed Packages (pip freeze)
```
annotated-doc==0.0.5, anyio==4.14.2, Flask==3.1.3, Flask-Limiter==4.1.1, numpy==2.5.1, pandas==3.0.5, PyPDF2==3.0.1, python-docx==1.2.0, requests==2.34.2, scikit-learn==1.9.0, scipy==1.18.0, spacy==3.8.13, ...
```
### Missing Dependencies
- `pytest` was originally missing from the environment.
- No other runtime dependencies missing (previous Pyright analysis resolved `Flask-Limiter` and `urllib.error`).

## 6. Entry Points & Configurations
- **Entry Point**: `run.py`
- **Database Configuration**: SQLite3 file-based DB at `talentsync.db`.
- **Environment Variables**: Managed via `app/config/settings.py` (loads `.env`).

## 7. Status Checks
### Pyright Status
```
0 errors, 0 warnings, 0 informations
```
### Pytest Status
```
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
rootdir: V:\HireAI_Website-main (2)\AI-Resume-Screening-System
plugins: anyio-4.14.2
collected 11 items

tests\test_recommendation.py ......                                      [ 54%]
tests\test_resume_parser.py .....                                        [100%]

======================= 11 passed, 6 warnings in 47.43s =======================
```
### Flask Startup Status
SUCCESS: App launched successfully without crashing.
```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
```

## 8. Runtime Errors & Stack Traces
**None**. The application tests successfully pass, Pyright is clear, and the application initializes.

## 9. Warnings & Compatibility Issues
**Warning 1: NumPy 2.5 Deprecation**
```
.venv\Lib\site-packages\joblib\numpy_pickle.py:207: DeprecationWarning: Setting the shape on a NumPy array has been deprecated in NumPy 2.5.
```
**Warning 2: Scikit-learn Version Mismatch**
```
.venv\Lib\site-packages\sklearn\base.py:525: InconsistentVersionWarning: Trying to unpickle estimator TfidfVectorizer from version 1.4.0 when using version 1.9.0.
```
**Warning 3: spaCy Model Mismatch**
```
.venv\Lib\site-packages\spacy\util.py:971: UserWarning: [W095] Model 'en_pipeline' (0.0.0) was trained with spaCy v3.7.2 and may not be 100% compatible with the current version (3.8.13).
```
**Root Cause Analysis:** Models serialized to disk (`tfidf_vectorizer.pkl` and spaCy pipelines) were generated on an older version of the libraries (scikit-learn 1.4.0 and spaCy 3.7.2) than what is currently installed in the environment (1.9.0 and 3.8.13).

## 10. Code Review & Recommendations
### Bugs / Potential Bugs
- The unpickled models are currently running under a version mismatch. While scikit-learn and spaCy have forward compatibility protections, this "Use at your own risk" state poses a risk of degraded model accuracy or sudden faults.

### Type Issues
- 100% resolved. No Pyright type errors remain.

### Recommended Fixes
- **Retrain the Machine Learning Models**: Run `python -m app.ml.training.train_recommender` and `python -m app.ml.training.train_skill_ner` to regenerate the `.pkl` files and spaCy models natively on scikit-learn 1.9.0 and spaCy 3.8.13. This will eliminate all `InconsistentVersionWarning` outputs and maximize compatibility.
- **Update Joblib**: Update `joblib` via pip to a newer version to resolve the NumPy 2.5 `DeprecationWarning` regarding array reshaping.
- **Virtual Environment Re-initialization**: The virtual environment `.venv/Scripts/pip.exe` retains a reference to `V:\HireAI_Website-main (1)\`. If possible, recreating the `.venv` natively in this directory will prevent hardcoded path discrepancies.
