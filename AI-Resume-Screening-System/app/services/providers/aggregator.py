import hashlib
import json
from datetime import datetime, timedelta
from app.services.providers.provider_manager import ProviderManager
from app.repositories.provider_cache_repository import ProviderCacheRepository
from app.repositories.jobs_repository import JobsRepository
from app.ai.job_matcher import JobMatcher

class JobAggregator:
    """
    Coordinates searches, deduplicates, caches, and ranks jobs with AI.
    """
    
    def __init__(self):
        self.manager = ProviderManager()
        self.matcher = JobMatcher()

    def _generate_cache_key(self, filters: dict) -> str:
        # Create a stable hash for the search parameters
        f_str = json.dumps(filters, sort_keys=True)
        return hashlib.md5(f_str.encode()).hexdigest()

    def search_jobs(self, filters: dict, user_skills: list | None = None) -> dict:
        """
        End-to-end flow:
        1. Check Cache
        2. Fetch from Providers (or DB Fallback)
        3. Deduplicate
        4. Save to external_jobs
        5. Rank with AI (if user_skills provided)
        6. Paginate & Return
        """
        # 1. Check Cache (simplified for MVP: checking globally instead of per provider)
        cache_key = self._generate_cache_key(filters)
        cached_result = ProviderCacheRepository.get_cached_response('aggregator', cache_key)
        
        if cached_result:
            jobs = json.loads(cached_result)
        else:
            # 2. Fetch from Providers
            jobs = self.manager.execute_search(filters)
            
            # 3. Deduplicate
            jobs = self._deduplicate(jobs)
            
            # 4. Cache the raw result for 30 mins
            expires_at = (datetime.now() + timedelta(minutes=30)).isoformat()
            ProviderCacheRepository.set_cached_response('aggregator', cache_key, json.dumps(jobs), expires_at)
            
            # Asynchronously save to DB? For MVP, we can save synchronously
            for job in jobs:
                JobsRepository.save_external_job(job)

        # 5. AI Ranking
        if user_skills:
            jobs = self.matcher.rank_jobs(user_skills, jobs)

        # 6. Pagination (Simplified: limit slicing handled here or at provider)
        # Assuming providers return a page, we just truncate if needed.
        limit = filters.get('limit', 20)
        jobs = jobs[:limit]

        return {
            'jobs': jobs,
            'total_results': len(jobs),
            'providers': [p.__class__.__name__ for p in self.manager.providers],
            'execution_time': 0 # Could add timing wrapper
        }

    def _deduplicate(self, jobs: list[dict]) -> list[dict]:
        """
        Removes duplicate jobs by comparing Company + Title.
        (Future: fuzz string matching).
        """
        seen = set()
        deduped = []
        for job in jobs:
            sig = f"{job['company'].lower().strip()}_{job['title'].lower().strip()}"
            if sig not in seen:
                seen.add(sig)
                deduped.append(job)
        return deduped
