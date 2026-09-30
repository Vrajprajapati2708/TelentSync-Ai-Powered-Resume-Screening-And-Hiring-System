# HireAI / TalentSync — Python Environment Baseline

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Audit  

---

## 1. System & Runtime Environment

| Property | Value |
| :--- | :--- |
| **Operating System** | Windows 11 (Windows-11-10.0.26200-SP0) |
| **Architecture** | AMD64 (64-bit) |
| **Python Version** | Python 3.14.6 (`v3.14.6:c63aec6`, Jun 10 2026) |
| **Pip Version** | pip 26.1.2 |
| **Active Virtualenv** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\.venv` |
| **Active Python Executable** | `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\.venv\Scripts\python.exe` |
| **SQLite C-Library Version** | 3.50.4 |

---

## 2. Core Package Manifest & Exact Versions

| Category | Package Name | Installed Version | Role in HireAI / TalentSync |
| :--- | :--- | :--- | :--- |
| **Web Framework** | `Flask` | **3.1.3** | REST API routing and Blueprint application factory |
| **WSGI Utilities** | `Werkzeug` | **3.1.8** | Password hashing (PBKDF2/SHA256) and secure file upload helpers |
| **Rate Limiting** | `Flask-Limiter` | **4.1.1** | Endpoint rate-limiting (login, register, upload, reset) |
| **Rate Limit Backend** | `limits` | **5.8.0** | Memory-based rate limiter engine |
| **NLP Engine** | `spacy` | **3.8.13** | Named Entity Recognition (NER) for technical skills |
| **NLP Utilities** | `thinc`, `srsly`, `blis` | **8.3.13**, **2.5.3**, **1.3.3** | Cython/C optimizations for spaCy |
| **Machine Learning** | `scikit-learn` | **1.9.0** | TF-IDF vectorizer, Cosine Similarity, KMeans, IsolationForest |
| **Numerical Math** | `numpy` | **2.5.1** | Matrix math and feature array representations |
| **DataFrames** | `pandas` | **3.0.5** | Data filtering and metrics calculation |
| **Scientific Computing** | `scipy` | **1.18.0** | Sparse matrix cosine distance calculations |
| **Model Serialization** | `joblib` | **1.5.3** | Pickle persistence for TF-IDF recommender models |
| **Document Parsing (PDF)**| `PyPDF2` | **3.0.1** | Raw text extraction from PDF documents |
| **Document Parsing (DOCX)**| `python-docx` | **1.2.0** | XML-based paragraph and run extraction from `.docx` |
| **Configuration** | `python-dotenv` | **1.2.2** | Environment variable management (`.env`) |
| **Testing** | `pytest` | **9.1.1** | Test execution framework |
| **HTTP Client** | `requests` | **2.34.2** | External job API polling (Adzuna) |
| **Reporting / PDF** | `reportlab` | **5.0.0** | PDF report export |
| **Visualization** | `matplotlib`, `seaborn` | **3.11.1**, **0.13.2** | Static graph generation |
