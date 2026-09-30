"""
AdzunaService — Adapter maintaining full backwards compatibility for existing modules and tests.
Backed by the hardened AdzunaClient.
"""

from typing import List, Dict, Any
from app.services.adzuna_client import (
    AdzunaClient,
    adzuna_client,
    AdzunaError,
    AdzunaConfigError,
    AdzunaAuthError,
    AdzunaRateLimitError,
    AdzunaTimeoutError,
    AdzunaUpstreamError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AdzunaService:
    """
    Backwards-compatible service adapter for existing routes and regression tests.
    Delegates network calls, caching, and normalization to AdzunaClient.
    """

    def __init__(self):
        self.client = adzuna_client
        self.app_id = self.client.app_id
        self.app_key = self.client.app_key
        self.country = self.client.country
        self.base_url = self.client.base_url
        self.timeout = self.client.timeout
        self.session = self.client.session
        self._cache = self.client._cache

    def _infer_role(self, candidate_skills: List[str]) -> str:
        return self.client.infer_role(candidate_skills)

    def build_query(self, skills: List[str], experience: str = '', location: str = '') -> str:
        """
        Builds a concise, effective query. Avoids 4+ token chains that return 0 jobs in Adzuna India.
        """
        inferred = self.client.infer_role(skills)
        if inferred:
            return inferred
        if skills:
            return skills[0]
        return "Developer"

    def fetch_live_jobs(
        self,
        skills: List[str],
        experience: str = '',
        location: str = '',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fetches live jobs using AdzunaClient's personalized search.
        Returns a list of standardized job dictionaries.
        """
        try:
            return self.client.fetch_personalized_jobs(
                skills=skills,
                experience=experience,
                location=location,
                limit=limit
            )
        except (AdzunaConfigError, AdzunaAuthError, AdzunaRateLimitError, AdzunaTimeoutError, AdzunaUpstreamError) as e:
            logger.error(f"AdzunaService.fetch_live_jobs error: {e}")
            raise
        except Exception as e:
            logger.error(f"AdzunaService.fetch_live_jobs unexpected error: {e}")
            raise AdzunaUpstreamError(str(e))

    def _normalize(self, raw: dict) -> dict:
        parsed = self.client._normalize(raw)
        return parsed if parsed else {}
