# HireAI / TalentSync — Application Architecture Baseline

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Audit  

---

## 1. Application Startup Flow

The application follows the Flask Application Factory pattern:

```text
Command: python run.py
   │
   ▼
[run.py]
   │ Sets Windows stdout UTF-8 encoding wrapper
   │ Imports create_app() and ActiveConfig
   ▼
[app/__init__.py: create_app()]
   ├── 1. Instantiates Flask(static_folder='static', template_folder='templates')
   ├── 2. Loads configuration from ActiveConfig (or overrides)
   ├── 3. Attaches Limiter instance (storage_uri="memory://")
   ├── 4. Ensures upload directories exist (UPLOAD_FOLDER, TEMP_FOLDER)
   ├── 5. Registers 6 Blueprints:
   │      ├── auth_bp   (/api/auth)
   │      ├── resume_bp (/api)
   │      ├── user_bp   (/api)
   │      ├── admin_bp  (/api/admin)
   │      ├── ml_bp     (/api/ml)
   │      └── jobs_bp   (/api/v1/jobs)
   ├── 6. Configures Error Handlers (404, 429, 500)
   ├── 7. Runs _init_db(ActiveConfig.DB_FILE)
   │      ├── Executes schema.sql
   │      ├── Verifies column migrations (is_verified, structured_json)
   │      └── Seeds initial demo jobs & users if DB is empty
   ▼
[app.run()]
   Runs development WSGI server on 0.0.0.0:5000 (Debug mode: True)
```

---

## 2. Structural Layering & Separation of Concerns

1. **Presentation Tier (Frontend SPA)**:
   - Single-Page Application: `app/templates/index.html`
   - Client Controller & Router: `app/static/js/app.js` (Hash-based router `#cand`, `#admin`, `#login`)
   - Styling: `app/static/css/style.css` (Vanilla CSS with CSS variables, Glassmorphism, Dark mode)

2. **Routing & HTTP Tier**:
   - `app/routes/auth_routes.py`: Session management, registration, login, token resets.
   - `app/routes/resume_routes.py`: Upload, download, job matching, applications.
   - `app/routes/user_routes.py`: Candidate dashboard KPIs, trends, profile editing.
   - `app/routes/admin_routes.py`: HR stats, applicant ranking, status transitions, job CRUD.
   - `app/routes/ml_routes.py`: Model health status, training triggers, inference endpoints.
   - `app/routes/jobs_routes.py`: Unified live multi-provider job search (`/api/v1/jobs/search`).

3. **Controller & Business Logic Tier**:
   - `app/controllers/auth_controller.py`: Password validation, token hashing, lockout defense.
   - `app/controllers/resume_controller.py`: SHA-256 duplicate checking, magic-byte validation, disk persistence, DB profile sync.

4. **Machine Learning & NLP Pipeline Tier**:
   - Orchestrator: `app/ml/ml_pipeline.py`
   - Resume Intelligence: `app/ml/resume_intelligence/resume_json_builder.py`
   - Custom NER: `app/ml/skill_extraction/extract_skills.py` (spaCy)
   - ATS Scoring: `app/ml/ats/ats_checker.py`
   - Recommendation: `app/ml/recommendation/recommend_jobs.py` (TF-IDF + Cosine Similarity)
   - Unsupervised Learning: `app/ml/clustering/candidate_clusterer.py` (KMeans) & `app/ml/outlier/outlier_detector.py` (IsolationForest)

5. **Data Persistence Tier**:
   - SQLite 3: `app/database/connection.py` (Connection pooling via context manager, `sqlite3.Row` dictionary mapping).
   - Schema Definition: `app/database/schema.sql` (18 tables).
