-- ============================================================
--  TalentSync — Database Schema (SQLite)
--  Run once to create all tables.
--  Migrate to MySQL by changing data types (INTEGER→INT, etc.)
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    email       TEXT    UNIQUE NOT NULL,
    password    TEXT    NOT NULL,
    role        TEXT    NOT NULL DEFAULT 'candidate',  -- 'candidate' | 'hr'
    is_verified INTEGER DEFAULT 0,                     -- 0 = unverified, 1 = verified
    skills         TEXT    DEFAULT '',
    ats_score      INTEGER DEFAULT 0,
    phone          TEXT    DEFAULT '',
    location       TEXT    DEFAULT '',
    linkedin       TEXT    DEFAULT '',
    github         TEXT    DEFAULT '',
    summary        TEXT    DEFAULT '',
    education      TEXT    DEFAULT '',
    is_outlier     INTEGER DEFAULT 0,           -- 0 = normal, 1 = flagged suspicious
    cluster_label  TEXT    DEFAULT 'Unclustered', -- e.g. 'Python / Data Science'
    created_at     TEXT    DEFAULT (datetime('now'))
);

-- ── Tables for Phase 0 P0 Authentication & Security ──

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    token_hash  TEXT    UNIQUE NOT NULL,
    expires_at  TEXT    NOT NULL,
    is_used     INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_email_tokens_hash ON email_verification_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_email_tokens_user ON email_verification_tokens(user_id);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    token_hash  TEXT    UNIQUE NOT NULL,
    expires_at  TEXT    NOT NULL,
    is_used     INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reset_tokens_hash ON password_reset_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_user ON password_reset_tokens(user_id);

CREATE TABLE IF NOT EXISTS login_attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT    NOT NULL,
    ip_address  TEXT    NOT NULL,
    success     INTEGER NOT NULL, -- 1 = success, 0 = fail
    attempted_at TEXT   DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_email_ip ON login_attempts(email, ip_address, attempted_at);

-- ── Tables for Phase 1 P0 Resume Upload & Storage ──

CREATE TABLE IF NOT EXISTS resumes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    original_name   TEXT    NOT NULL,
    stored_filename TEXT    UNIQUE NOT NULL,
    file_path       TEXT    NOT NULL,
    file_hash       TEXT    NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    mime_type       TEXT    NOT NULL,
    parsed_text     TEXT    DEFAULT '',
    word_count      INTEGER DEFAULT 0,
    ats_score       INTEGER DEFAULT 0,
    extracted_skills TEXT   DEFAULT '',
    structured_json TEXT    DEFAULT '',
    status          TEXT    DEFAULT 'processed', -- 'uploaded'|'processing'|'processed'|'failed'
    version         INTEGER DEFAULT 1,
    uploaded_at     TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_hash ON resumes(file_hash);


CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    company     TEXT    NOT NULL,
    location    TEXT    DEFAULT '',
    type        TEXT    DEFAULT 'Full-time',
    salary      TEXT    DEFAULT '',
    skills      TEXT    DEFAULT '',
    description TEXT    DEFAULT '',
    status      TEXT    DEFAULT 'Active',
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    job_id      INTEGER NOT NULL,
    match_score INTEGER DEFAULT 0,
    status      TEXT    DEFAULT 'Reviewing',  -- Reviewing|Shortlisted|Pending|Rejected
    applied_at  TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(job_id)  REFERENCES jobs(id)  ON DELETE CASCADE,
    UNIQUE(user_id, job_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    title         TEXT    NOT NULL,
    message       TEXT    DEFAULT '',
    type          TEXT    DEFAULT 'info',  -- 'application'|'match'|'view'|'system'|'security'|'info'|'success'|'warning'|'error'
    is_read       INTEGER DEFAULT 0,
    action_type   TEXT    DEFAULT 'none',  -- 'view_application'|'view_jobs'|'view_ats'|'view_profile'|'none'
    action_target TEXT    DEFAULT '',      -- '#cand-applications'|'#cand-jobs'|'#cand-ats'|'#cand-profile'
    metadata      TEXT    DEFAULT '{}',
    created_at    TEXT    DEFAULT (datetime('now')),
    updated_at    TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ── Tables for Live Job Providers (Enterprise Upgrade v2.0) ──

CREATE TABLE IF NOT EXISTS external_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id     TEXT    UNIQUE NOT NULL,
    provider        TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    company         TEXT    NOT NULL,
    company_id      TEXT    DEFAULT '',
    company_logo    TEXT    DEFAULT '',
    industry        TEXT    DEFAULT '',
    location        TEXT    DEFAULT '',
    country         TEXT    DEFAULT '',
    latitude        REAL    DEFAULT 0.0,
    longitude       REAL    DEFAULT 0.0,
    salary_min      REAL    DEFAULT 0.0,
    salary_max      REAL    DEFAULT 0.0,
    currency        TEXT    DEFAULT '',
    employment_type TEXT    DEFAULT '',
    experience      TEXT    DEFAULT '',
    remote          INTEGER DEFAULT 0,
    description     TEXT    DEFAULT '',
    skills          TEXT    DEFAULT '',
    benefits        TEXT    DEFAULT '',
    education       TEXT    DEFAULT '',
    posted_date     TEXT    DEFAULT '',
    expires_date    TEXT    DEFAULT '',
    apply_url       TEXT    DEFAULT '',
    source_url      TEXT    DEFAULT '',
    language        TEXT    DEFAULT 'en',
    status          TEXT    DEFAULT 'Active',
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS companies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    UNIQUE NOT NULL,
    logo_url    TEXT    DEFAULT '',
    website     TEXT    DEFAULT '',
    industry    TEXT    DEFAULT '',
    description TEXT    DEFAULT '',
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS provider_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    provider    TEXT    NOT NULL,
    query_hash  TEXT    NOT NULL,
    response    TEXT    NOT NULL, -- JSON string
    expires_at  TEXT    NOT NULL,
    created_at  TEXT    DEFAULT (datetime('now')),
    UNIQUE(provider, query_hash)
);

CREATE TABLE IF NOT EXISTS provider_health (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    provider        TEXT    NOT NULL,
    status          TEXT    DEFAULT 'OK', -- 'OK', 'DOWN', 'RATE_LIMITED'
    latency_ms      INTEGER DEFAULT 0,
    error_message   TEXT    DEFAULT '',
    checked_at      TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS saved_jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    job_id      INTEGER,          -- Reference to internal jobs
    external_id TEXT,             -- Reference to external_jobs
    saved_at    TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS search_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    keyword     TEXT    DEFAULT '',
    location    TEXT    DEFAULT '',
    filters     TEXT    DEFAULT '', -- JSON string of extra filters
    searched_at TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS job_alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    keyword     TEXT    NOT NULL,
    location    TEXT    DEFAULT '',
    frequency   TEXT    DEFAULT 'daily', -- 'daily', 'weekly'
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS application_status (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  INTEGER NOT NULL,
    status          TEXT    NOT NULL,
    notes           TEXT    DEFAULT '',
    updated_at      TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recommendation_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    job_id          INTEGER,
    external_id     TEXT,
    match_score     INTEGER DEFAULT 0,
    matched_skills  TEXT    DEFAULT '',
    missing_skills  TEXT    DEFAULT '',
    recommended_at  TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
