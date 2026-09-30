# TalentSync — AI Resume Screening & Job Recommendation System

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![NLP](https://img.shields.io/badge/NLP-spaCy%20%7C%20NLTK-green)
![ML](https://img.shields.io/badge/ML-Scikit--learn-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

> An AI-powered recruitment platform that automates resume parsing, skill extraction, candidate ranking, ATS scoring, and intelligent job recommendations using NLP, TF-IDF, and Cosine Similarity.

---

## 🚀 Live Demo

| Role      | Email              | Password  |
|-----------|--------------------|-----------|
| Candidate | rahul@demo.com     | demo123   |
| HR Admin  | priya@demo.com     | demo123   |

---

## 📌 Project Overview

**Domain:** Data Science · Artificial Intelligence · NLP · Recommendation Systems

This system solves the real-world problem of manual resume screening by:
- 📄 Parsing resumes and extracting structured data using NLP
- 🧠 Matching candidates to jobs using TF-IDF + Cosine Similarity
- 🏆 Ranking applicants using a weighted multi-factor algorithm
- 📊 Providing HR analytics dashboards with hiring insights
- ✅ Scoring resumes for ATS (Applicant Tracking System) compatibility

---

## 🗂️ Project Structure

```
AI-Resume-Screening-System/
├── run.py                          # Entry point
├── .env                            # Environment variables
├── requirements.txt                # Dependencies
│
├── app/
│   ├── __init__.py                 # Flask App Factory
│   ├── config/
│   │   └── settings.py             # Centralised configuration
│   ├── database/
│   │   ├── connection.py           # SQLite connection helper
│   │   └── schema.sql              # Database schema
│   │
│   ├── ml/                         # ⭐ Core Data Science Layer
│   │   ├── preprocessing/
│   │   │   └── clean_text.py       # Text cleaning pipeline
│   │   ├── parsers/
│   │   │   ├── pdf_parser.py       # PDF text extraction
│   │   │   └── resume_parser.py    # Structured data extraction
│   │   ├── skill_extraction/
│   │   │   ├── skills_db.py        # Skills taxonomy (80+ skills)
│   │   │   └── extract_skills.py   # NLP skill matching + gap analysis
│   │   ├── recommendation/
│   │   │   ├── tfidf_model.py      # TF-IDF vectorizer
│   │   │   ├── cosine_similarity.py# Similarity math
│   │   │   └── recommend_jobs.py   # 2-stage recommendation engine
│   │   ├── ranking/
│   │   │   └── ranking_engine.py   # Weighted candidate scoring
│   │   └── ats/
│   │       └── ats_checker.py      # ATS compatibility scorer
│   │
│   ├── routes/                     # Flask Blueprints (API endpoints)
│   │   ├── auth_routes.py          # /api/auth/*
│   │   ├── resume_routes.py        # /api/upload_resume, /api/match_jobs
│   │   ├── user_routes.py          # /api/candidate/*, /api/notifications/*
│   │   └── admin_routes.py         # /api/admin/*
│   │
│   ├── controllers/                # Business Logic Layer
│   │   ├── auth_controller.py
│   │   └── resume_controller.py
│   │
│   ├── utils/
│   │   ├── logger.py               # Centralised logging
│   │   ├── validators.py           # Input validation
│   │   └── pdf_generator.py        # Export reports as PDF
│   │
│   ├── templates/
│   │   ├── index.html              # Main SPA (all pages)
│   │   └── errors/404.html
│   │
│   └── static/
│       ├── css/style.css           # Full UI stylesheet
│       ├── js/
│       │   ├── main.js             # Core app logic
│       │   ├── charts.js           # Chart.js dashboard charts
│       │   ├── upload.js           # Resume drag-and-drop upload
│       │   └── dashboard.js        # Dashboard data rendering
│       └── uploads/resumes/        # Uploaded resume files
│
├── datasets/                       # Training & sample data
├── trained_models/                 # Saved ML model pickles
├── notebooks/                      # Jupyter EDA & training notebooks
│   └── eda.ipynb
└── tests/                          # Unit tests (9/9 passing)
    ├── test_resume_parser.py
    └── test_recommendation.py
```

---

## 🧠 Machine Learning Workflow

```
Resume Upload (PDF)
       ↓
PDF Text Extraction  [PyPDF2]
       ↓
Text Preprocessing   [clean_text.py — lowercase, URL removal, tokenization]
       ↓
Skill Extraction     [extract_skills.py — regex NER against 80+ skill DB]
       ↓
ATS Scoring          [ats_checker.py — 5-factor: skills/contact/edu/exp/length]
       ↓
TF-IDF Vectorization [tfidf_model.py — text → numerical vectors]
       ↓
Cosine Similarity    [cosine_similarity.py — resume ↔ job description]
       ↓
Job Recommendation   [recommend_jobs.py — 70% skill overlap + 30% cosine]
       ↓
Candidate Ranking    [ranking_engine.py — skills 40% + exp 25% + ATS 20% + edu 15%]
       ↓
Analytics Dashboard  [Chart.js — bar, pie, trend charts]
```
---

## ⚙️ Technology Stack

| Layer            | Technology                              |
|------------------|-----------------------------------------|
| **Editor**       | Visual Studio Code                      |
| **Backend**      | Python 3.14, Flask 3.0                  |
| **ML / NLP**     | TF-IDF, Cosine Similarity, Regex NER    |
| **Libraries**    | PyPDF2, pandas, numpy, scikit-learn     |
| **Database**     | SQLite (upgrade to MySQL for production)|
| **Frontend**     | HTML5, CSS3, Bootstrap 5, JavaScript    |
| **Charts**       | Chart.js                                |
| **Auth**         | Flask Sessions                          |
| **Testing**      | Python unittest                         |
| **Version Ctrl** | Git + GitHub                            |

---

## 🔌 API Endpoints

| Method   | Endpoint                          | Description                        |
|----------|-----------------------------------|------------------------------------|
| `POST`   | `/api/auth/login`                 | Candidate / HR login               |
| `POST`   | `/api/auth/register`              | New account registration           |
| `POST`   | `/api/upload_resume`              | Upload & parse resume (NLP)        |
| `POST`   | `/api/match_jobs`                 | Get job recommendations            |
| `POST`   | `/api/apply`                      | Apply to a job                     |
| `GET`    | `/api/candidate/stats/<id>`       | Candidate dashboard stats          |
| `GET`    | `/api/users/<id>/profile`         | Get user profile                   |
| `PUT`    | `/api/users/<id>/profile`         | Update profile                     |
| `GET`    | `/api/notifications/<id>`         | Get notifications                  |
| `GET`    | `/api/admin/stats`                | HR dashboard KPIs + chart data     |
| `GET`    | `/api/admin/candidates`           | All applicants ranked by score     |
| `POST`   | `/api/admin/update_status`        | Update application status          |
| `GET/POST`| `/api/admin/jobs`                | List / create job postings         |
| `DELETE` | `/api/admin/delete_job/<id>`      | Remove a job posting               |

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/AI-Resume-Screening-System.git
cd AI-Resume-Screening-System
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the application
```bash
py run.py
```

### 4. Open in browser
```
http://127.0.0.1:5000
```

### 5. Run tests
```bash
py tests/test_resume_parser.py
py tests/test_recommendation.py
```

---

## 📊 Data Science Concepts Used

| Concept                | Usage                                    |
|------------------------|------------------------------------------|
| **NLP**                | Resume text parsing and entity extraction|
| **TF-IDF**             | Resume & job description vectorization   |
| **Cosine Similarity**  | Resume-job matching score                |
| **Recommendation**     | Content-based job filtering              |
| **Text Mining**        | Skill and keyword extraction             |
| **Classification**     | Candidate ranking algorithm              |
| **Data Visualization** | Dashboard charts and hiring analytics    |

---

## 📈 ATS Scoring System

The ATS (Applicant Tracking System) checker scores resumes out of 100:

| Factor           | Max Points | Description                         |
|------------------|-----------|--------------------------------------|
| Skills Detected  | 40 pts    | 4 pts per recognised skill           |
| Contact Info     | 15 pts    | Email, phone, LinkedIn, GitHub       |
| Education        | 15 pts    | Degree, university, CGPA keywords    |
| Experience       | 15 pts    | Company, internship, role keywords   |
| Content Length   | 15 pts    | Minimum 150+ words recommended       |

---

## 🏆 Candidate Ranking Formula

```
Final Score = (Skills Match × 40%) + (ATS Score × 20%) +
              (Experience × 25%) + (Education × 15%)
```

---

## 📁 Demo Data

The system seeds 12 demo candidates, 10 job postings, and 18 applications automatically on first run.

---

## 🔒 Security Notes

- Passwords stored as plain text in demo mode — integrate `bcrypt` for production
- Use environment variables (`.env`) for all secrets
- Never commit `talentsync.db` or `uploads/` to Git

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👤 Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [linkedin.com/in/yourprofile](https://linkedin.com/in/yourprofile)

---

> ⭐ If this project helped you, please give it a star on GitHub!
