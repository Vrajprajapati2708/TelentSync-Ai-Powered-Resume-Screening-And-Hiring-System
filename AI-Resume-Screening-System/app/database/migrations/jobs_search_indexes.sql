-- ============================================================
-- TalentSync Migration: Jobs Search & Filtering Indexes
-- ============================================================

-- Add columns if not already present
ALTER TABLE jobs ADD COLUMN work_mode TEXT DEFAULT 'onsite';
ALTER TABLE jobs ADD COLUMN salary_min INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN salary_max INTEGER DEFAULT 0;

-- Populate work_mode
UPDATE jobs SET work_mode = 'remote'
WHERE LOWER(location) LIKE '%remote%'
   OR LOWER(type) LIKE '%remote%'
   OR LOWER(description) LIKE '%remote%'
   OR LOWER(description) LIKE '%work from home%'
   OR LOWER(description) LIKE '%wfh%';

UPDATE jobs SET work_mode = 'hybrid'
WHERE LOWER(location) LIKE '%hybrid%'
   OR LOWER(description) LIKE '%hybrid%';

-- Create SQLite indexes on internal jobs
CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location);
CREATE INDEX IF NOT EXISTS idx_jobs_work_mode ON jobs(work_mode);
CREATE INDEX IF NOT EXISTS idx_jobs_salary_min ON jobs(salary_min);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
