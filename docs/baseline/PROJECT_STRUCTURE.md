# HireAI / TalentSync — Project Structure Baseline

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Audit  

---

## 1. Detected Roots

| Item | Path / Location | Classification |
| :--- | :--- | :--- |
| **Workspace Root** | `V:\HireAI_Website-main (2)` | Workspace Root / Outer Container |
| **Git Root** | **None** (No `.git` directory found anywhere in workspace) | Unversioned Directory Tree |
| **Application Root** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System` | Primary Execution Root |
| **Backend Code Root** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\app` | Flask Backend (`routes`, `controllers`, `ml`, `services`) |
| **Frontend / Static Root** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\app\static` | Vanilla JS SPA (`js/app.js`, `css/style.css`, `images/`) |
| **Templates Root** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\app\templates` | `index.html` Single-Page-App Template |
| **Active Database** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\talentsync.db` | Primary SQLite DB (1,306,624 bytes) |
| **Resume Upload Storage** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\uploads\resumes` | Persistent Disk Storage (172 `.docx` files) |
| **Trained ML Models** | `V:\HireAI_Website-main (2)\trained_models` | spaCy NER (`spacy_skill_ner`) & TF-IDF Vectorizer |
| **Test Suite Root** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\tests` | 13 test files (201 automated tests) |
| **Active Virtual Environment** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\.venv` | Python 3.14.6 64-bit Virtualenv |

---

## 2. Directory Layout & Anomaly Analysis (Nested Root Issue)

The repository exhibits a nested double-root structure:

```text
V:\HireAI_Website-main (2)\                    <-- Outer Root
│
├── .venv/                                      <-- Stale / Incomplete venv (missing pytest)
├── datasets/                                   <-- Dataset CSVs (archive)
├── trained_models/                             <-- Master ML models (spaCy NER + TF-IDF)
│   ├── spacy_skill_ner/
│   └── tfidf_recommender/
├── talentsync.db                               <-- Stale historical DB (151,552 bytes, mtime: 2026-08-03)
├── gaps.txt                                    <-- Previous technical audit
├── reporting_1.txt                             <-- Academic project report
├── about_HireAi.txt                            <-- System summary & viva guide
├── viva.txt                                    <-- 47-technology viva preparation manual
│
└── AI-Resume-Screening-System/                 <-- Inner Root (Active Application)
    ├── .venv/                                  <-- ACTIVE Virtualenv (Python 3.14.6 with all dependencies)
    ├── talentsync.db                           <-- ACTIVE Runtime Database (1,306,624 bytes)
    ├── run.py                                  <-- Main Application Entrypoint
    ├── requirements.txt                        <-- Dependency manifest
    ├── migrate_db.py                           <-- DB migration script
    ├── seed_real_jobs.py                       <-- Job descriptions seeder
    ├── uploads/                                <-- ACTIVE Resume persistent storage
    │   └── resumes/                            <-- 172 saved candidate resume files
    ├── tests/                                  <-- Unit & integration tests
    └── app/                                    <-- Application Package
        ├── __init__.py                         <-- Flask App Factory & inline seeder
        ├── config/settings.py                  <-- Configuration settings
        ├── database/                           <-- SQLite connection & schema.sql
        ├── controllers/                        <-- Auth & Resume controllers
        ├── routes/                             <-- 6 Flask Blueprint route modules
        ├── services/                           <-- Adzuna & Job Aggregator services
        ├── repositories/                       <-- Job data repositories
        ├── ml/                                 <-- Resume Intelligence & ML Pipeline
        ├── utils/                              <-- Security, validators, logger
        ├── static/                             <-- Frontend SPA JS, CSS, images
        └── templates/                          <-- index.html
```

---

## 3. Entry Points

- **Flask Development Server**: `AI-Resume-Screening-System\run.py`
- **Application Factory**: `AI-Resume-Screening-System\app\__init__.py` -> `create_app()`
- **ML Master Trainer**: `AI-Resume-Screening-System\app\ml\training\train_all.py`
- **Database Seeder**: `AI-Resume-Screening-System\seed_real_jobs.py`
- **Database Migration**: `AI-Resume-Screening-System\migrate_db.py`

---

## 4. Configuration & Environment Locations

- `AI-Resume-Screening-System\app\config\settings.py`: Core configuration (Config, DevelopmentConfig, ProductionConfig).
- `AI-Resume-Screening-System\.env`: Local environment overrides.
- `AI-Resume-Screening-System\requirements.txt`: Python package manifest.
