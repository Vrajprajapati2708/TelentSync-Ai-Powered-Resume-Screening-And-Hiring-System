-- ============================================================
--  TalentSync / HireAI — Production Database Schema (PostgreSQL)
--  Preserves all entity relationships, cascades, indexes, and constraints.
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255)    NOT NULL,
    email           VARCHAR(255)    UNIQUE NOT NULL,
    password        VARCHAR(255)    NOT NULL,
    role            VARCHAR(50)     NOT NULL DEFAULT 'candidate',
    is_verified     INTEGER         DEFAULT 0,
    skills          TEXT            DEFAULT '',
    ats_score       INTEGER         DEFAULT 0,
    phone           VARCHAR(50)     DEFAULT '',
    location        VARCHAR(255)    DEFAULT '',
    linkedin        VARCHAR(255)    DEFAULT '',
    github          VARCHAR(255)    DEFAULT '',
    summary         TEXT            DEFAULT '',
    education       TEXT            DEFAULT '',
    is_outlier      INTEGER         DEFAULT 0,
    cluster_label   VARCHAR(100)    DEFAULT 'Unclustered',
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) UNIQUE NOT NULL,
    expires_at  TIMESTAMP NOT NULL,
    is_used     INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_tokens_hash ON email_verification_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_email_tokens_user ON email_verification_tokens(user_id);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) UNIQUE NOT NULL,
    expires_at  TIMESTAMP NOT NULL,
    is_used     INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reset_tokens_hash ON password_reset_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_user ON password_reset_tokens(user_id);

CREATE TABLE IF NOT EXISTS login_attempts (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    ip_address  VARCHAR(100) NOT NULL,
    success     INTEGER NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_email_ip ON login_attempts(email, ip_address, attempted_at);

CREATE TABLE IF NOT EXISTS resumes (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_name   VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) UNIQUE NOT NULL,
    file_path       VARCHAR(500) NOT NULL,
    file_hash       VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type       VARCHAR(100) NOT NULL,
    parsed_text     TEXT DEFAULT '',
    word_count      INTEGER DEFAULT 0,
    ats_score       INTEGER DEFAULT 0,
    extracted_skills TEXT DEFAULT '',
    structured_json TEXT DEFAULT '',
    status          VARCHAR(50) DEFAULT 'processed',
    version         INTEGER DEFAULT 1,
    uploaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_hash ON resumes(file_hash);

-- Anti-Gaming: Log all resume upload events for 24-hour rate-limiting
CREATE TABLE IF NOT EXISTS resume_upload_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_hash   VARCHAR(64) DEFAULT '',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_resume_upload_logs_user_time ON resume_upload_logs(user_id, uploaded_at);

-- Anti-Gaming Step 6: Blind Skill Confirmation (Candidate confirmed skills with evidence weight & provenance)
CREATE TABLE IF NOT EXISTS candidate_skills (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill        VARCHAR(100) NOT NULL,
    source       VARCHAR(50) NOT NULL DEFAULT 'self_declared',
    confidence   DOUBLE PRECISION DEFAULT 0.2,
    confirmed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, skill)
);

CREATE INDEX IF NOT EXISTS idx_candidate_skills_user ON candidate_skills(user_id);
CREATE INDEX IF NOT EXISTS idx_candidate_skills_skill ON candidate_skills(skill);

-- Anti-Gaming Step 7: Learning Timeline Engine & Velocity Anomaly Detection
CREATE TABLE IF NOT EXISTS skill_velocity_anomalies (
    id                 SERIAL PRIMARY KEY,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    previous_resume_id INTEGER REFERENCES resumes(id) ON DELETE SET NULL,
    current_resume_id  INTEGER NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    elapsed_days       DOUBLE PRECISION NOT NULL,
    estimated_days     DOUBLE PRECISION NOT NULL,
    new_skills         TEXT NOT NULL,
    severity           VARCHAR(50) NOT NULL DEFAULT 'high',
    velocity_ratio     DOUBLE PRECISION NOT NULL,
    anomaly_reason     TEXT NOT NULL,
    status             VARCHAR(50) NOT NULL DEFAULT 'flagged',
    detected_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_velocity_anomalies_user ON skill_velocity_anomalies(user_id);
CREATE INDEX IF NOT EXISTS idx_velocity_anomalies_status ON skill_velocity_anomalies(status);

-- Anti-Gaming Step 8: Technical Quiz Gatekeeper for Disputed / Sudden Skills
CREATE TABLE IF NOT EXISTS quiz_questions (
    id             SERIAL PRIMARY KEY,
    skill          VARCHAR(100) NOT NULL,
    question       TEXT NOT NULL,
    options        TEXT NOT NULL,
    correct_option INTEGER NOT NULL,
    difficulty     VARCHAR(50) DEFAULT 'intermediate',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_skill ON quiz_questions(skill);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill           VARCHAR(100) NOT NULL,
    score           INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    passed          INTEGER NOT NULL,
    attempted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_skill ON quiz_attempts(user_id, skill);

CREATE TABLE IF NOT EXISTS jobs (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(255) NOT NULL,
    company     VARCHAR(255) NOT NULL,
    location    VARCHAR(255) DEFAULT '',
    type        VARCHAR(100) DEFAULT 'Full-time',
    salary      VARCHAR(100) DEFAULT '',
    skills      TEXT DEFAULT '',
    description TEXT DEFAULT '',
    status      VARCHAR(50) DEFAULT 'Active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    resume_id   INTEGER REFERENCES resumes(id) ON DELETE SET NULL,
    match_score INTEGER DEFAULT 0,
    status      VARCHAR(50) DEFAULT 'Reviewing',
    applied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_resume ON applications(resume_id);

CREATE TABLE IF NOT EXISTS notifications (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    message     TEXT DEFAULT '',
    type        VARCHAR(50) DEFAULT 'info',
    is_read     INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS external_jobs (
    id              SERIAL PRIMARY KEY,
    external_id     VARCHAR(255) UNIQUE NOT NULL,
    provider        VARCHAR(100) NOT NULL,
    title           VARCHAR(255) NOT NULL,
    company         VARCHAR(255) NOT NULL,
    company_id      VARCHAR(100) DEFAULT '',
    company_logo    VARCHAR(500) DEFAULT '',
    industry        VARCHAR(100) DEFAULT '',
    location        VARCHAR(255) DEFAULT '',
    country         VARCHAR(50) DEFAULT '',
    latitude        DOUBLE PRECISION DEFAULT 0.0,
    longitude       DOUBLE PRECISION DEFAULT 0.0,
    salary_min      DOUBLE PRECISION DEFAULT 0.0,
    salary_max      DOUBLE PRECISION DEFAULT 0.0,
    currency        VARCHAR(20) DEFAULT '',
    employment_type VARCHAR(100) DEFAULT '',
    experience      VARCHAR(100) DEFAULT '',
    remote          INTEGER DEFAULT 0,
    description     TEXT DEFAULT '',
    skills          TEXT DEFAULT '',
    benefits        TEXT DEFAULT '',
    education       TEXT DEFAULT '',
    posted_date     VARCHAR(100) DEFAULT '',
    expires_date    VARCHAR(100) DEFAULT '',
    apply_url       TEXT DEFAULT '',
    source_url      TEXT DEFAULT '',
    language        VARCHAR(50) DEFAULT 'en',
    status          VARCHAR(50) DEFAULT 'Active',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companies (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) UNIQUE NOT NULL,
    logo_url    VARCHAR(500) DEFAULT '',
    website     VARCHAR(500) DEFAULT '',
    industry    VARCHAR(100) DEFAULT '',
    description TEXT DEFAULT '',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS provider_cache (
    id          SERIAL PRIMARY KEY,
    provider    VARCHAR(100) NOT NULL,
    query_hash  VARCHAR(100) NOT NULL,
    response    TEXT NOT NULL,
    expires_at  TIMESTAMP NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, query_hash)
);

CREATE TABLE IF NOT EXISTS provider_health (
    id              SERIAL PRIMARY KEY,
    provider        VARCHAR(100) NOT NULL,
    status          VARCHAR(50) DEFAULT 'OK',
    latency_ms      INTEGER DEFAULT 0,
    error_message   TEXT DEFAULT '',
    checked_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS saved_jobs (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id      INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    saved_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS search_history (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    keyword     VARCHAR(255) DEFAULT '',
    location    VARCHAR(255) DEFAULT '',
    filters     TEXT DEFAULT '',
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_alerts (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    keyword     VARCHAR(255) NOT NULL,
    location    VARCHAR(255) DEFAULT '',
    frequency   VARCHAR(50) DEFAULT 'daily',
    is_active   INTEGER DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS application_status (
    id              SERIAL PRIMARY KEY,
    application_id  INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    status          VARCHAR(100) NOT NULL,
    notes           TEXT DEFAULT '',
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recommendation_history (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id          INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    external_id     VARCHAR(255),
    match_score     INTEGER DEFAULT 0,
    matched_skills  TEXT DEFAULT '',
    missing_skills  TEXT DEFAULT '',
    recommended_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
