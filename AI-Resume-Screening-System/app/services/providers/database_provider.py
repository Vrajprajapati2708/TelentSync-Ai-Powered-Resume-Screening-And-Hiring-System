from app.services.providers.base_provider import BaseJobProvider
from app.repositories.jobs_repository import JobsRepository
from datetime import datetime

class DatabaseProvider(BaseJobProvider):
    """
    Fallback Provider. Fetches mocked jobs from the existing internal DB.
    """
    
    def search(self, filters: dict) -> list[dict]:
        limit = filters.get('limit', 20)
        raw_jobs = JobsRepository.get_internal_jobs(limit=limit)
        
        # Simple keyword filtering since it's a fallback
        keyword = filters.get('keyword', '').lower()
        if keyword:
            raw_jobs = [j for j in raw_jobs if keyword in j.get('title', '').lower() or keyword in j.get('skills', '').lower()]
            
        return [self.normalize(job) for job in raw_jobs]

    def normalize(self, raw_job: dict) -> dict:
        """Converts internal DB job to the Unified Job Model."""
        return {
            'external_id': f"internal_{raw_job.get('id')}",
            'provider': 'TalentSync_Internal',
            'title': raw_job.get('title', ''),
            'company': raw_job.get('company', ''),
            'location': raw_job.get('location', ''),
            'description': raw_job.get('description', ''),
            'skills': raw_job.get('skills', ''),
            'salary_min': 0, # Could parse from raw_job.get('salary')
            'salary_max': 0,
            'currency': 'INR',
            'apply_url': '',
            'remote': 1 if 'remote' in raw_job.get('location', '').lower() else 0,
            'posted_date': raw_job.get('created_at', datetime.now().isoformat())
        }
        
    def health(self) -> bool:
        # DB Provider is always healthy as long as SQLite is there
        return True
