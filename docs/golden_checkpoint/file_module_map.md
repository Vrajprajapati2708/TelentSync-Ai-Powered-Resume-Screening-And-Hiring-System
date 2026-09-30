# ============================================================
# HIREAI / TALENTSYNC — FINAL FILE & MODULE MAP
# Phase 5 Golden Architecture Map (Viva-Ready Reference)
# ============================================================

This document provides an exhaustive, grouped reference of all functional modules across the HireAI / TalentSync platform as verified at the Phase 5 Golden Checkpoint.

---

## 1. Configuration & Application Factory

| File Path | Responsibility |
| :--- | :--- |
| `app/config/settings.py` | Central configuration defining `Config`, `DevelopmentConfig`, `ProductionConfig`, and `TestingConfig`. Implements canonical absolute paths (`BASE_DIR`, `DB_FILE`, `MODEL_DIR`, `UPLOAD_FOLDER`), rate limiting configuration (`RATELIMIT_STORAGE_URI`), secret key validation, and OCR/Email settings. |
| `app/__init__.py` | Canonical application factory (`create_app()`). Initializes Flask instance, binds `Flask-Limiter` with `in_memory_fallback_enabled=True`, configures upload directory creation, registers all blueprints, and binds global error handlers. |
| `run.py` | Development server entry point. |

---

## 2. Production Infrastructure (GAP-16, GAP-17, GAP-18)

| File Path | Responsibility |
| :--- | :--- |
| `wsgi.py` | Production WSGI entry point exposing the `app` instance for production web servers. |
| `gunicorn.conf.py` | Production Gunicorn multi-worker configuration (2 workers, 4 threads, `gthread` worker class, 120s timeout, container stdout/stderr logging). |
| `Dockerfile` | Minimal production Docker image definition based on `python:3.11-slim`, non-root user `appuser` (UID 10001), runtime Tesseract OCR, and automated `HEALTHCHECK`. |
| `.dockerignore` | Build hygiene exclusions preventing virtualenvs, caches, temporary uploads, and databases from polluting container images. |
| `docker-compose.yml` | Multi-container orchestration defining `web` (Flask/Gunicorn), `postgres` (PostgreSQL 16 Alpine), and `redis` (Redis 7 Alpine) on a dedicated bridge network with persistent named volumes. |
| `.env.example` | Safe production environment variable template omitting real secrets. |

---

## 3. Database Subsystem

| File Path | Responsibility |
| :--- | :--- |
| `app/database/connection.py` | Unified dual-engine database gateway. Supports SQLite for development and PostgreSQL for production via `psycopg 3` and `psycopg_pool.ConnectionPool` (min 2, max 5). Provides quote-aware SQL translation (`?` -> `%s`) and `lastrowid` compatibility via `RETURNING id`. |
| `app/database/schema.sql` | Canonical SQLite DDL defining all 17 core entity tables, relationships, foreign keys, and indexes. |
| `app/database/schema_postgres.sql` | Production PostgreSQL DDL defining identical schema with `SERIAL PRIMARY KEY`, `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`, and matching constraints. |
| `app/database/migration.py` | Standalone, atomic SQLite-to-PostgreSQL data migration utility. Ensures zero modification to source SQLite database, preserves foreign key order, advances sequences, and executes within a single transaction. |

---

## 4. Routes & Blueprints (Controllers)

| File Path | Responsibility |
| :--- | :--- |
| `app/routes/auth_routes.py` | User registration, login, logout, password reset, and email verification endpoints. Enforces strict rate limiting. |
| `app/routes/resume_routes.py` | Resume upload, download, preview, history retrieval, and intelligence analysis endpoints. |
| `app/routes/jobs_routes.py` | Internal job listings, external Adzuna job searching, job application workflow, and saved job management. |
| `app/routes/admin_routes.py` | Recruiter talent pool, candidate profile inspection, and administrative metrics. |
| `app/routes/ml_routes.py` | Diagnostic endpoints for ML pipeline status, health, and skill extraction testing. |
| `app/routes/health_routes.py` | Container and load-balancer health probe (`GET /api/health`). |

---

## 5. Controllers & Repositories

| File Path | Responsibility |
| :--- | :--- |
| `app/controllers/auth_controller.py` | Authentication business logic: password hashing (Werkzeug scrypt), token generation, user creation, and session management. |
| `app/controllers/resume_controller.py` | Resume upload ingestion, SHA-256 deduplication, file system storage, and database persistence. |
| `app/controllers/jobs_controller.py` | Job search, filtering, and application submission coordination. |
| `app/repositories/jobs_repository.py` | Data access layer for jobs and application records. |

---

## 6. Services

| File Path | Responsibility |
| :--- | :--- |
| `app/services/health_service.py` | Diagnostic service aggregating database query probe, Redis connection/ping check, and ML pipeline readiness without credential exposure. |
| `app/services/email_service.py` | Multi-provider email delivery engine supporting SMTP and in-memory test capture (`TestEmailProvider`). |
| `app/services/external_jobs_service.py` | External job aggregation engine querying Adzuna and RapidAPI providers with local caching and fallback. |

---

## 7. Machine Learning, NLP & OCR Subsystems

| File Path | Responsibility |
| :--- | :--- |
| `app/ml/recommendation/tfidf_model.py` | Sklearn TF-IDF vectorizer and cosine similarity job recommendation engine. Uses dynamic ancestor discovery (`_resolve_model_dir()`). |
| `app/ml/skill_extraction/extract_skills.py` | Custom spaCy NER model loader for technical skill recognition. Uses dynamic ancestor discovery. |
| `app/ml/skill_extraction/skill_intelligence.py` | Rule-based and canonical skill mapping dictionary aggregating extracted skills. |
| `app/ml/parsers/pdf_parser.py` | PyPDF2 text extraction with integrated fallback to Tesseract OCR for scanned documents. |
| `app/ml/parsers/docx_parser.py` | python-docx XML text and table extraction. |
| `app/ml/analyzers/resume_quality_analyzer.py` | Heuristic scoring assessing contact info, word count, section headers, and formatting quality. |
| `app/ml/ats/ats_checker.py` | ATS compatibility score generator combining quality heuristics and skill density. |
| `app/ml/ml_pipeline.py` | Unified ML orchestration pipeline coordinating parsing, entity extraction, skill intelligence, and quality analysis. |

---

## 8. Security & Utilities

| File Path | Responsibility |
| :--- | :--- |
| `app/utils/security.py` | Input sanitization, password complexity enforcement, token generation, and rate limiting decorators. |
| `app/utils/logger.py` | Structured application logging. |

---

## 9. Test Suites

| File Path | Responsibility |
| :--- | :--- |
| `tests/test_auth_p0.py` | Phase 0 baseline authentication tests. |
| `tests/test_phase1_stability_regression.py` | Phase 1 critical stability and data integrity tests (GAP-02, 05, 06, 11). |
| `tests/test_phase2_resume_intelligence_regression.py` | Phase 2 resume intelligence and UX tests (GAP-01, 03, 04). |
| `tests/test_phase3_jobs_talent_pool_regression.py` | Phase 3 external job applications and talent pool tests (GAP-07, 09, 10). |
| `tests/test_phase4_email_ml_ocr_regression.py` | Phase 4 email subsystem, ML compatibility, and OCR fallback tests (GAP-12, 13, 14). |
| `tests/test_phase5_production_regression.py` | Phase 5 production architecture tests (GAP-15, 16, 17, 18). |
