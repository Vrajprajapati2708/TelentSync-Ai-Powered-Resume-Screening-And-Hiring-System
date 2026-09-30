import requests
from datetime import datetime
from app.services.providers.base_provider import BaseJobProvider
from app.config.settings import ActiveConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

class AdzunaProvider(BaseJobProvider):
    """
    Adzuna Job Provider Implementation.
    """
    
    def __init__(self):
        self.app_id = ActiveConfig.ADZUNA_APP_ID
        self.app_key = ActiveConfig.ADZUNA_APP_KEY
        self.country = ActiveConfig.ADZUNA_COUNTRY
        self.base_url = f"https://api.adzuna.com/v1/api/jobs/{self.country}/search"
        self.timeout = ActiveConfig.PROVIDER_TIMEOUT
        
    def search(self, filters: dict) -> list[dict]:
        if not self.app_id or not self.app_key:
            logger.error("Adzuna API keys missing. Skipping Adzuna.")
            return []
            
        page = filters.get('page', 1)
        params = {
            'app_id': self.app_id,
            'app_key': self.app_key,
            'results_per_page': filters.get('limit', 20),
            'what': filters.get('keyword', ''),
            'where': filters.get('location', ''),
            'content-type': 'application/json'
        }
        
        try:
            logger.info(f"Adzuna searching for: {params['what']} in {params['where']}")
            response = requests.get(f"{self.base_url}/{page}", params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            raw_jobs = data.get('results', [])
            return [self.normalize(job) for job in raw_jobs]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Adzuna API Error: {str(e)}")
            return []

    def normalize(self, raw_job: dict) -> dict:
        """Converts Adzuna payload into unified Job dict."""
        return {
            'external_id': f"adzuna_{raw_job.get('id', '')}",
            'provider': 'Adzuna',
            'title': raw_job.get('title', 'Unknown Title'),
            'company': raw_job.get('company', {}).get('display_name', 'Unknown Company'),
            'location': raw_job.get('location', {}).get('display_name', ''),
            'description': raw_job.get('description', ''),
            'salary_min': raw_job.get('salary_min', 0),
            'salary_max': raw_job.get('salary_max', 0),
            'currency': 'INR', # Assumed from ADZUNA_COUNTRY=in
            'apply_url': raw_job.get('redirect_url', ''),
            'remote': 1 if 'remote' in raw_job.get('title', '').lower() else 0, # Best effort for Adzuna
            'posted_date': raw_job.get('created', datetime.now().isoformat())
        }
        
    def health(self) -> bool:
        if not self.app_id or not self.app_key:
            return False
        try:
            # Send a fast 1-result query to check health
            res = requests.get(f"{self.base_url}/1", params={'app_id': self.app_id, 'app_key': self.app_key, 'results_per_page': 1}, timeout=5)
            return res.status_code == 200
        except Exception:
            return False
