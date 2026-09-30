<div align="center">

```text
 ██╗  ██╗██╗██████╗ ███████╗ █████╗ ██╗
 ██║  ██║██║██╔══██╗██╔════╝██╔══██╗██║
 ███████║██║██████╔╝█████╗  ███████║██║
 ██╔══██║██║██╔══██╗██╔══╝  ██╔══██║██║
 ██║  ██║██║██║  ██║███████╗██║  ██║██║
 ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝
```

**T A L E N T S Y N C &nbsp;&nbsp;·&nbsp;&nbsp; A I - P O W E R E D &nbsp;&nbsp; R E C R U I T M E N T &nbsp;&nbsp; E N G I N E**

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&color=0:000000,100:051a11&height=150&section=header&text=NO%20COMPROMISE.%20PURE%20PERFORMANCE.&fontSize=24&fontColor=00ff88&fontAlignY=50&animation=twinkling&desc=100%25%20AUTOMATED%20RESUME%20SCREENING%20%7C%20LIVE%20JOB%20MATCHING%20%7C%20AI%20ANALYTICS&descAlignY=70&descSize=13"/>

<a href="https://github.com/prajapativraj/HireAI_Website">
  <img src="https://readme-typing-svg.demolab.com?font=Share+Tech+Mono&weight=800&size=22&pause=500&color=00FF88&center=true&vCenter=true&width=900&lines=INITIATING+NEURAL+NETWORK...;SPACY+NER+SKILL+MODELS+LOADED...;TF-IDF+JOB+MATCHING+ENGINE+READY...;502+PYTEST+TESTS+PASSING...;SYSTEM+READY.+WELCOME+TO+TALENTSYNC." alt="Typing SVG" />
</a>

<br/>

[![Python](https://img.shields.io/badge/Python_3.14+-000000?style=for-the-badge&logo=python&logoColor=00FF88&labelColor=000000)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask_3.1-000000?style=for-the-badge&logo=flask&logoColor=00FF88&labelColor=000000)](https://flask.palletsprojects.com)
[![spaCy](https://img.shields.io/badge/spaCy_NER-000000?style=for-the-badge&logo=spacy&logoColor=00FF88&labelColor=000000)](https://spacy.io/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-000000?style=for-the-badge&logo=scikit-learn&logoColor=00FF88&labelColor=000000)](https://scikit-learn.org)
[![SQLite](https://img.shields.io/badge/SQLite_WAL-000000?style=for-the-badge&logo=sqlite&logoColor=00FF88&labelColor=000000)](https://sqlite.org)
[![Docker](https://img.shields.io/badge/Docker_Ready-000000?style=for-the-badge&logo=docker&logoColor=00FF88&labelColor=000000)](https://docker.com)
[![Tests](https://img.shields.io/badge/502_Tests_Passing-000000?style=for-the-badge&logo=pytest&logoColor=00FF88&labelColor=000000)](#)

</div>

<br/>

> ⚡ **TalentSync (HireAI)** is an enterprise-grade, AI-powered recruitment platform. It eliminates manual resume screening by combining `spaCy` NLP, `scikit-learn` ML, and a dual-engine live job recommendation pipeline to parse, score, match, and rank candidates in milliseconds — no human bias, just data.

---

## 📸 UI Preview

<div align="center">
  <img src="https://raw.githubusercontent.com/hetvi-prajapati/HireAI_Website/main/AI-Resume-Screening-System/app/static/img/hero_img.png" width="90%" style="border: 3px solid #00FF88; border-radius: 6px; box-shadow: 0px 0px 30px rgba(0,255,136,0.4);"/>
</div>

---

## ⚡ Performance Metrics

| Subsystem | Processing Engine | Benchmark (Average) | Status |
| :--- | :--- | :--- | :---: |
| **PDF / DOCX Parsing** | `PyPDF2` + `python-docx` + `pytesseract` OCR | `< 40ms per document` | 🟢 **ACTIVE** |
| **Skill Recognition** | `spaCy` Custom NER (2,400+ skills taxonomy) | `~ 15ms / 500+ rules` | 🟢 **ACTIVE** |
| **ATS Scoring Algorithm** | Proprietary Keyword Density Weighting | `< 5ms per candidate` | 🟢 **ACTIVE** |
| **Job Vectorization** | `TF-IDF` Matrix (4,206 vocab, 109 jobs) | `< 25ms similarity calc` | 🟢 **ACTIVE** |
| **Live Jobs Feed** | Adzuna API (LRU cache, 5 min TTL) | `< 8s timeout / fallback` | 🟢 **ACTIVE** |
| **Test Suite** | `pytest` (unit + integration + security) | **502 passing, 0 failures** | 🟢 **ACTIVE** |

---

## 🛑 System Architecture (The Pipeline)

Data enters as unstructured binary and exits as actionable intelligence.

```mermaid
graph TD
    classDef terminal fill:#000000,stroke:#00FF88,stroke-width:2px,color:#00FF88,font-family:monospace,font-weight:bold;
    classDef core fill:#051a11,stroke:#00FF88,stroke-width:3px,color:#FFFFFF,font-family:monospace,font-weight:bold;
    classDef db fill:#000000,stroke:#00AA55,stroke-width:2px,color:#AAAAAA,font-family:monospace;
    classDef ext fill:#0a0a1a,stroke:#5599ff,stroke-width:2px,color:#aaaaff,font-family:monospace;

    A[RAW PDF / DOCX UPLOAD]:::terminal -->|PyPDF2 + python-docx| B{SPACY NER ENGINE}:::core
    B -->|Entity Recognition 2400+ Skills| C[NOISE FILTER AND NORMALIZER]:::terminal
    C -->|Sanitized Skill Profile| D{ATS SCORING MATRIX}:::core
    D -->|Keyword Density + Experience| E[CANDIDATE PROFILE]:::terminal

    E --> F{TF-IDF VECTORIZER}:::core
    G[(SQLITE 109 INTERNAL JOBS)]:::db --> F
    H[ADZUNA LIVE JOBS API]:::ext --> F

    F -->|Cosine Similarity Ranking| I[RANKED JOB MATCHES]:::terminal
    I --> J{K-MEANS CLUSTERING}:::core
    I --> K{ISOLATION FOREST}:::core
    J -->|Candidate Grouping| L[HR ANALYTICS DASHBOARD]:::terminal
    K -->|Fraud Detection| L
```

---

## 💀 Features

<details open>
<summary><kbd>►</kbd> <strong>NEURAL SKILL EXTRACTION</strong></summary>
<br>
A custom-trained <code>spaCy</code> Named Entity Recognition (NER) model (<code>trained_models/spacy_skill_ner</code>) contextually understands <strong>2,400+ canonical skills</strong> — tech stacks, soft skills, tools, and frameworks. Backed by <code>skill_intelligence.py</code> for categorization into Technical / Soft / Tools / Frameworks layers.
</details>

<details open>
<summary><kbd>►</kbd> <strong>UNFORGIVING ATS SCORING ENGINE</strong></summary>
<br>
Every uploaded resume is run through <code>ats_checker.py</code> — a multi-factor algorithm scoring <strong>keyword density</strong>, <strong>formatting structure</strong>, and <strong>experience overlap</strong> to produce a definitive <strong>0–100 ATS Score</strong>. No bias. Just data.
</details>

<details open>
<summary><kbd>►</kbd> <strong>DUAL-ENGINE JOB MATCHING</strong></summary>
<br>
Candidates are matched via <strong>two parallel engines</strong>: (1) Internal SQLite pool of 109 curated job postings, and (2) <strong>Adzuna Live Jobs API</strong> with multi-query parallel fetching, role inference, and location filtering — all vectorized using <code>scikit-learn</code> TF-IDF + Cosine Similarity.
</details>

<details open>
<summary><kbd>►</kbd> <strong>K-MEANS CANDIDATE CLUSTERING</strong></summary>
<br>
<code>MiniBatchKMeans (k=5)</code> groups candidates by extracted skill profiles into talent clusters for batch recruiter review and strategic hiring insights.
</details>

<details open>
<summary><kbd>►</kbd> <strong>ISOLATION FOREST FRAUD DETECTION</strong></summary>
<br>
<code>IsolationForest</code> scans for anomalous candidate profiles — inflated ATS scores, implausible skill densities, and fake resume patterns — flagging them for HR review before they reach a shortlist.
</details>

<details open>
<summary><kbd>►</kbd> <strong>ROLE-BASED ACCESS CONTROL (RBAC)</strong></summary>
<br>
Three hardened access tiers: <strong>Platform Administrator</strong> (full control), <strong>HR Recruiter</strong> (job CRUD, applicant ranking, shortlisting), and <strong>Candidate</strong> (upload, match, apply). All routes are Blueprint-guarded with session validation.
</details>

<details open>
<summary><kbd>►</kbd> <strong>FORTIFIED SECURITY PERIMETER</strong></summary>
<br>
<strong>Werkzeug</strong> <code>scrypt/pbkdf2</code> password hashing. <strong>Flask-Limiter</strong> rate limiting permanently bans brute-force attackers after threshold strikes. <strong>Parameterized Queries</strong> destroy SQL Injection at execution time. File upload validation with SHA-256 duplicate detection.
</details>

<details open>
<summary><kbd>►</kbd> <strong>SPA CANDIDATE & HR PORTALS</strong></summary>
<br>
A fully client-side <strong>Single Page Application</strong> (Vanilla JS hash Router, <code>Chart.js</code> analytics, Glassmorphism CSS) serving 7 dedicated Candidate sections and 7 HR Recruiter sections — zero page reloads, real-time DOM rendering.
</details>

---

## 💻 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Runtime** | Python 3.14+ |
| **Web Framework** | Flask 3.1 (Application Factory + Blueprints) |
| **Frontend** | HTML5 Semantic, Vanilla CSS (Design Tokens), Vanilla JS (SPA Router) |
| **UI Libraries** | Chart.js, FontAwesome 6, Google Fonts (Syne + Inter) |
| **NLP Engine** | spaCy 3.8 (Custom NER model — `trained_models/spacy_skill_ner`) |
| **ML / AI** | scikit-learn 1.9 (TF-IDF, Cosine Similarity, K-Means, IsolationForest) |
| **Resume Parsers** | PyPDF2, python-docx, pdfplumber, pytesseract (OCR fallback) |
| **Database** | SQLite 3 (WAL mode, composite indexes, parameterized queries) |
| **Security** | Werkzeug hashing (scrypt/pbkdf2), Flask-Limiter, SHA-256 file dedup |
| **External API** | Adzuna Jobs API (LRU cache, single-flight coalescing, graceful timeout) |
| **Production Server** | Gunicorn (Linux/Mac) / Waitress (Windows) |
| **Containerization** | Docker + docker-compose |
| **Testing** | pytest — 502 tests (unit + integration + security regression) |

---

## 📁 Project Structure

```
HireAI_Website/
└── AI-Resume-Screening-System/          # Root application package
    │
    ├── run.py                           # Local dev server entry point
    ├── wsgi.py                          # WSGI production entry (Gunicorn/uWSGI)
    ├── gunicorn.conf.py                 # Gunicorn worker configuration
    ├── Dockerfile                       # Container definition
    ├── docker-compose.yml               # Local container stack
    ├── requirements.txt                 # Production Python dependencies
    ├── requirements-dev.txt             # Dev / testing dependencies
    ├── talentsync.db                    # Active SQLite database
    ├── .env.example                     # Environment variables template
    │
    └── app/                             # Core Flask Application Package
        ├── __init__.py                  # App Factory: DB, Blueprints, Limiter, Session
        │
        ├── ai/
        │   └── job_matcher.py           # TF-IDF Cosine Similarity ranking engine
        │
        ├── config/
        │   └── settings.py              # Dev / Test / Production config classes
        │
        ├── controllers/
        │   ├── resume_controller.py     # Upload validation, SHA-256 dedup, orchestration
        │   └── platform_admin_controller.py  # Platform metrics, user deactivation
        │
        ├── database/
        │   ├── connection.py            # Thread-safe SQLite connection helper
        │   ├── schema.sql               # Core schema (users, jobs, applications, resumes)
        │   └── migrations/              # Incremental DB migration scripts
        │
        ├── ml/                          # Machine Learning & NLP Subsystems
        │   ├── ml_pipeline.py           # End-to-end ML orchestrator
        │   ├── ats/
        │   │   └── ats_checker.py       # ATS scoring algorithm (0–100)
        │   ├── clustering/
        │   │   └── candidate_clusterer.py  # K-Means candidate clustering
        │   ├── outlier_detection/
        │   │   └── outlier_detector.py  # IsolationForest fraud detection
        │   ├── recommendation/
        │   │   └── tfidf_model.py       # TF-IDF model + cosine similarity
        │   └── skill_extraction/
        │       ├── extract_skills.py    # spaCy NER + regex extractor
        │       ├── skill_intelligence.py # Skill categorization layer
        │       └── skills_db.py         # 2,400+ canonical skills taxonomy
        │
        ├── routes/                      # Flask Blueprint REST API
        │   ├── auth_routes.py           # Login, register, logout, session
        │   ├── resume_routes.py         # Upload, download, match_jobs, apply
        │   ├── jobs_routes.py           # Unified Live Jobs search
        │   ├── admin_routes.py          # HR: job CRUD, applicant rankings
        │   ├── platform_admin_routes.py # Platform owner: analytics, user roles
        │   ├── ml_routes.py             # ML health, model metadata, latency
        │   └── user_routes.py           # Profile, settings, notifications
        │
        ├── services/                    # External Service Integrations
        │   └── adzuna_service.py        # Adzuna API client (LRU cache, coalescing)
        │
        ├── templates/                   # Jinja2 / HTML Templates
        ├── static/                      # CSS, JS, Images, Fonts
        └── utils/                       # Shared utility helpers
```

---

## 🚀 Getting Started (Local Setup)

### Prerequisites

- Python **3.11+** (3.14 recommended)
- `pip` package manager
- Git

### Step-by-Step Installation

```bash
# [1] CLONE THE REPOSITORY
git clone https://github.com/prajapativraj/HireAI_Website.git
cd HireAI_Website/AI-Resume-Screening-System

# [2] CREATE A VIRTUAL ENVIRONMENT
python -m venv venv

# [3] ACTIVATE THE VIRTUAL ENVIRONMENT
# Windows:
venv\Scripts\activate
# Mac / Linux:
source venv/bin/activate

# [4] INSTALL ALL DEPENDENCIES
pip install -r requirements.txt

# [5] DOWNLOAD THE spaCy LANGUAGE MODEL
python -m spacy download en_core_web_sm

# [6] CONFIGURE ENVIRONMENT VARIABLES
copy .env.example .env
# Edit .env and fill in your SECRET_KEY, API keys, etc.

# [7] LAUNCH THE SERVER
python run.py
```

> **🟢 Server is live at:** `http://127.0.0.1:5000`

### Docker Setup (Alternative)

```bash
# Build and start all services (Flask + Redis)
docker-compose up --build

# Access at http://localhost:5000
```

---

## 🔐 Environment Variables

Copy `.env.example` to `.env` and configure the following. **Never commit real secrets to version control.**

| Variable | Description | Example |
| :--- | :--- | :--- |
| `FLASK_ENV` | Runtime environment | `production` / `development` |
| `SECRET_KEY` | Flask session signing key (min 32 chars) | `a-random-secure-string` |
| `DATABASE_URL` | PostgreSQL URL (production) | `postgresql://user:pass@host/db` |
| `REDIS_URL` | Redis for distributed rate limiting | `redis://localhost:6379/0` |
| `MAIL_HOST` | SMTP host for email subsystem | `smtp.sendgrid.net` |
| `MAIL_USERNAME` | SMTP username / API key label | `apikey` |
| `MAIL_PASSWORD` | SMTP API key / password | `your-smtp-api-key` |
| `MAIL_FROM` | Sender address | `noreply@talentsync.ai` |
| `APP_BASE_URL` | Public app base URL | `https://talentsync.ai` |
| `ADZUNA_APP_ID` | Adzuna Jobs API App ID | `your_app_id` |
| `ADZUNA_APP_KEY` | Adzuna Jobs API App Key | `your_app_key` |
| `ADZUNA_COUNTRY` | Country code for job search | `in` |
| `OCR_ENABLED` | Enable pytesseract OCR for scanned PDFs | `true` |
| `WEB_CONCURRENCY` | Gunicorn worker count | `2` |

---

## 🌐 API Reference

All endpoints use Flask Blueprint routes. Authentication is session-based.

### Authentication (`/auth`)

| Method | Endpoint | Auth | Description |
| :---: | :--- | :---: | :--- |
| `POST` | `/auth/register` | ❌ | Register a new candidate or HR account |
| `POST` | `/auth/login` | ❌ | Authenticate and create a session |
| `POST` | `/auth/logout` | ✅ | Destroy current session |
| `GET` | `/auth/me` | ✅ | Return current authenticated user profile |

### Resume (`/api/resume`)

| Method | Endpoint | Auth | Description |
| :---: | :--- | :---: | :--- |
| `POST` | `/api/resume/upload` | ✅ Candidate | Upload PDF/DOCX — triggers parse → ATS score → skill extraction |
| `GET` | `/api/resume/download` | ✅ Candidate | Download the candidate's stored resume file |
| `GET` | `/api/resume/status` | ✅ Candidate | Get parsed resume metadata and ATS score |

### Job Matching (`/api`)

| Method | Endpoint | Auth | Description |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/match_jobs` | ✅ Candidate | TF-IDF cosine similarity matches from internal job pool |
| `GET` | `/api/jobs/search` | ✅ | Unified search: internal + Adzuna live jobs |
| `POST` | `/api/apply` | ✅ Candidate | Apply to an internal job posting |
| `GET` | `/api/applications` | ✅ Candidate | List all of the candidate's job applications |

### HR Admin (`/admin`)

| Method | Endpoint | Auth | Description |
| :---: | :--- | :---: | :--- |
| `GET` | `/admin/applicants` | ✅ HR | List all applicants with ATS scores and match data |
| `POST` | `/admin/jobs` | ✅ HR | Create a new internal job posting |
| `PUT` | `/admin/jobs/<id>` | ✅ HR | Update an existing job posting |
| `DELETE` | `/admin/jobs/<id>` | ✅ HR | Delete a job posting |
| `POST` | `/admin/shortlist/<id>` | ✅ HR | Shortlist a candidate application |
| `POST` | `/admin/reject/<id>` | ✅ HR | Reject a candidate application |

### ML Pipeline (`/api/ml`)

| Method | Endpoint | Auth | Description |
| :---: | :--- | :---: | :--- |
| `GET` | `/api/ml/status` | ✅ Admin | ML subsystem health and model metadata |
| `GET` | `/api/ml/latency` | ✅ Admin | Pipeline latency benchmarks |
| `GET` | `/api/ml/clusters` | ✅ Admin | K-Means candidate cluster assignments |

### Platform Admin (`/platform-admin`)

| Method | Endpoint | Auth | Description |
| :---: | :--- | :---: | :--- |
| `GET` | `/platform-admin/stats` | ✅ Admin | Platform-wide analytics and KPI metrics |
| `POST` | `/platform-admin/users/<id>/deactivate` | ✅ Admin | Deactivate a user account |
| `POST` | `/platform-admin/users/<id>/role` | ✅ Admin | Change a user's role |

---

## 🔐 Clearance Levels (Default Credentials)

| Designation | Auth Email | Passkey | Access Level |
| :--- | :--- | :--- | :--- |
| **PLATFORM ADMIN** | `admin@talentsync.ai` | `admin123` | **MAXIMUM** — Analytics, user management, role control, full ML dashboard |
| **HR RECRUITER** | `[CREATE NEW ACCOUNT]` | `***` | **ELEVATED** — Job CRUD, applicant rankings, shortlist/reject, cluster view |
| **CANDIDATE** | `[CREATE NEW ACCOUNT]` | `***` | **STANDARD** — Upload resume, ATS score, job matching, apply |

> ⚠️ **Change the admin password immediately in any non-development environment.**

---

## 📊 Database Schema (Overview)

| Table | Purpose | Key Fields |
| :--- | :--- | :--- |
| `users` | All users (candidates, HR, admin) | `id, name, email, password, role, ats_score, skills` |
| `resumes` | Parsed resume records | `user_id, file_hash, ats_score, extracted_skills, structured_json` |
| `jobs` | Internal job postings | `title, company, description, required_skills, salary_range, job_type` |
| `applications` | Candidate–job applications | `user_id, job_id, match_score, status` |

---

## 🧪 Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run the full 502-test suite
pytest

# Run with verbose output
pytest -v

# Run a specific test module
pytest tests/test_ml_modules.py -v
```

---

<div align="center">
<br/>

```text
[ SYSTEM OPERATIONAL. END OF FILE. ]
```

**ARCHITECTED & DEVELOPED BY**

### [PRAJAPATI VRAJ](https://github.com/prajapativraj)

*Full-Stack Developer · AI/ML Integration · System Architecture*

[![GitHub](https://img.shields.io/badge/GitHub-prajapativraj-000000?style=for-the-badge&logo=github&logoColor=00FF88)](https://github.com/prajapativraj)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Prajapati_Vraj-000000?style=for-the-badge&logo=linkedin&logoColor=00FF88)](https://linkedin.com/in/prajapativraj)

<br/>

*TalentSync / HireAI — Built with 🧠 AI · ⚡ Performance · 🔐 Security*

</div>
