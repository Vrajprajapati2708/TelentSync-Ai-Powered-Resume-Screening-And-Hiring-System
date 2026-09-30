from app.services.providers.adzuna_provider import AdzunaProvider
from app.services.providers.database_provider import DatabaseProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ProviderManager:
    """
    Manages provider registration, health checks, and failovers.
    """
    
    def __init__(self):
        self.providers = []
        self._register_providers()
        
    def _register_providers(self):
        """Register live providers, appending the fallback provider at the end."""
        self.providers.append(AdzunaProvider())
        # Add future providers here (Jooble, Remotive, etc.)
        
        self.fallback = DatabaseProvider()
        
    def get_healthy_providers(self) -> list:
        healthy = []
        for p in self.providers:
            if p.health():
                healthy.append(p)
            else:
                logger.warning(f"Provider {p.__class__.__name__} is unhealthy or missing credentials.")
        return healthy

    def execute_search(self, filters: dict) -> list[dict]:
        """
        Executes search across all healthy providers. 
        If all fail or none are healthy, falls back to the database.
        """
        healthy_providers = self.get_healthy_providers()
        
        if not healthy_providers:
            logger.info("No healthy external providers. Falling back to internal DB.")
            return self.fallback.search(filters)
            
        results = []
        for provider in healthy_providers:
            try:
                jobs = provider.search(filters)
                results.extend(jobs)
            except Exception as e:
                logger.error(f"Error fetching from {provider.__class__.__name__}: {str(e)}")
                
        # If external providers returned 0 jobs for some reason, fallback
        if not results:
            logger.info("External providers returned 0 results. Falling back to internal DB.")
            return self.fallback.search(filters)
            
        return results
