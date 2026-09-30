from abc import ABC, abstractmethod

class BaseJobProvider(ABC):
    """
    Abstract Base Class for all Job Providers.
    Enforces the Strategy Pattern. Every provider MUST implement these methods.
    """
    
    @abstractmethod
    def search(self, filters: dict) -> list[dict]:
        """
        Executes a search against the provider.
        Must return a list of UNIFIED job dictionaries.
        """
        pass

    @abstractmethod
    def normalize(self, raw_job: dict) -> dict:
        """
        Converts a provider-specific job payload into the Unified Job Model.
        """
        pass

    @abstractmethod
    def health(self) -> bool:
        """
        Checks if the provider API is reachable and healthy.
        """
        pass
