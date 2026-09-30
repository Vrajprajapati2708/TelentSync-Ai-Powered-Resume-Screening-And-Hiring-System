from app.database.connection import get_db
from datetime import datetime

class ProviderCacheRepository:
    """
    Repository for interacting with the provider_cache table.
    """

    @staticmethod
    def get_cached_response(provider: str, query_hash: str):
        """Returns cached JSON response if it hasn't expired."""
        with get_db() as conn:
            now = datetime.now().isoformat()
            row = conn.execute(
                "SELECT response FROM provider_cache WHERE provider=? AND query_hash=? AND expires_at > ?", 
                (provider, query_hash, now)
            ).fetchone()
            if row:
                return row['response']
        return None

    @staticmethod
    def set_cached_response(provider: str, query_hash: str, response: str, expires_at: str):
        """Saves a JSON response to cache."""
        with get_db() as conn:
            conn.execute('''
                INSERT INTO provider_cache (provider, query_hash, response, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(provider, query_hash) DO UPDATE SET 
                response=excluded.response, expires_at=excluded.expires_at
            ''', (provider, query_hash, response, expires_at))
            conn.commit()
