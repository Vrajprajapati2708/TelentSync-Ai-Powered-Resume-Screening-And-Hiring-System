# HireAI / TalentSync — Baseline Manifest

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: System Freeze Snapshot  

---

## 1. PROJECT IDENTIFICATION
- **Project Name**: HireAI / TalentSync (AI-Powered Resume Screening & Recruitment System)
- **Version**: 2.0.0 (Phase 0 Frozen Baseline)
- **Execution Date**: 2026-09-02

## 2. GIT STATE
- **Version Control Status**: Unversioned directory clone (no `.git` repository directory)
- **Current Branch**: N/A
- **Commit SHA**: N/A
- **Working Tree**: Freeze snapshot locked at 2026-09-02

## 3. ENVIRONMENT & RUNTIME
- **Operating System**: Windows 11 (Windows-11-10.0.26200-SP0) 64-bit
- **Python Runtime**: Python 3.14.6
- **Package Manager**: pip 26.1.2
- **Virtual Environment**: `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\.venv`
- **SQLite Engine**: 3.50.4

## 4. PERSISTENCE & DATA ASSETS
- **Active Database**: `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\talentsync.db` (1,306,624 bytes)
- **Active DB SHA-256**: `f0695b8642437b2814f38499e7cb6be5706f05121d1e27e5123a437d621c3053`
- **Backup DB Path**: `V:\HireAI_Website-main (2)\docs\baseline\backups\talentsync_baseline_20260902_182512.db`
- **Backup DB SHA-256**: `f0695b8642437b2814f38499e7cb6be5706f05121d1e27e5123a437d621c3053`
- **Backup Verification**: `MATCH: True` (100% bit-for-bit cryptographic match)
- **Uploaded Resumes Directory**: `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\uploads\resumes`
- **Uploaded Files Count**: 172 `.docx` resume files (6,073,398 bytes)

## 5. APPLICATION & ENTRYPOINTS
- **Main Server Entrypoint**: `python run.py` (inside `AI-Resume-Screening-System`)
- **Factory Entrypoint**: `app/__init__.py:create_app()`
- **HTTP Server**: Flask 3.1.3 development server on `0.0.0.0:5000`

## 6. TEST RESULTS
- **Runner**: Python `unittest` discover
- **Total Tests**: 201
- **Passed**: 201 (100% pass rate)
- **Failed**: 0
- **Execution Duration**: 20.507 seconds

## 7. MACHINE LEARNING ASSETS
- **NER Model**: Custom spaCy `spacy_skill_ner` (Epochs: 30, F1: 0.9974)
- **Recommender Model**: Scikit-Learn `TfidfVectorizer` (4,206 terms, Max features: 8,000)
- **Model Path**: `V:\HireAI_Website-main (2)\trained_models\`

## 8. PREVIOUS AUDIT GAP STATUS
- **Total Gaps Tested**: 18
- **Confirmed Gaps**: 18
- **Partially Confirmed**: 0
- **Unresolved / Unknown**: 0
