from app.database.connection import get_db

class JobsRepository:
    """
    Repository for managing jobs in the database.
    Abstracts SQL queries away from the service layer.
    """
    
    @staticmethod
    def save_external_job(job_dict):
        """Saves a normalized external job to the database."""
        with get_db() as conn:
            # Check if exists
            exists = conn.execute("SELECT id FROM external_jobs WHERE external_id=?", (job_dict.get('external_id'),)).fetchone()
            if exists:
                return exists['id']
            
            cursor = conn.execute('''
                INSERT INTO external_jobs (
                    external_id, provider, title, company, company_id, company_logo, 
                    industry, location, country, latitude, longitude, salary_min, salary_max, 
                    currency, employment_type, experience, remote, description, skills, 
                    benefits, education, posted_date, expires_date, apply_url, source_url, 
                    language, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_dict.get('external_id', ''), job_dict.get('provider', ''), job_dict.get('title', ''), 
                job_dict.get('company', ''), job_dict.get('company_id', ''), job_dict.get('company_logo', ''),
                job_dict.get('industry', ''), job_dict.get('location', ''), job_dict.get('country', ''), 
                job_dict.get('latitude', 0.0), job_dict.get('longitude', 0.0), 
                job_dict.get('salary_min', 0.0), job_dict.get('salary_max', 0.0), 
                job_dict.get('currency', ''), job_dict.get('employment_type', ''), 
                job_dict.get('experience', ''), 1 if job_dict.get('remote') else 0, 
                job_dict.get('description', ''), job_dict.get('skills', ''), 
                job_dict.get('benefits', ''), job_dict.get('education', ''), 
                job_dict.get('posted_date', ''), job_dict.get('expires_date', ''), 
                job_dict.get('apply_url', ''), job_dict.get('source_url', ''), 
                job_dict.get('language', 'en'), 'Active'
            ))
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def get_internal_jobs(limit=50):
        """Fetches internal jobs for fallback."""
        with get_db() as conn:
            jobs = conn.execute("SELECT * FROM jobs WHERE status='Active' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(j) for j in jobs]
