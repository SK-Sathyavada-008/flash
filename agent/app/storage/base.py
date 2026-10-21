"""Base Storage Interface for Flash Routines, Preferences, and Task History."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseStorage(ABC):
    """Abstract storage provider for Flash."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Name of storage provider (e.g. 'local_json', 'mongodb_atlas')."""
        pass

    @abstractmethod
    def is_cloud_enabled(self) -> bool:
        """Whether storage is syncing to cloud."""
        pass

    @abstractmethod
    def save_routine(self, name: str, steps: List[Dict[str, Any]], description: str = "") -> bool:
        """Save an automated routine."""
        pass

    @abstractmethod
    def get_routine(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a saved routine by name."""
        pass

    @abstractmethod
    def list_routines(self) -> List[Dict[str, Any]]:
        """List all saved routines."""
        pass

    @abstractmethod
    def delete_routine(self, name: str) -> bool:
        """Delete a saved routine."""
        pass

    @abstractmethod
    def save_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Save user preferences (e.g. speech rate, voice, sloth temperament)."""
        pass

    @abstractmethod
    def get_preferences(self) -> Dict[str, Any]:
        """Retrieve user preferences."""
        pass

    @abstractmethod
    def record_task_history(self, task_record: Dict[str, Any]) -> bool:
        """Record non-sensitive task execution metadata."""
        pass

    @abstractmethod
    def get_task_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent task history."""
        pass

    @abstractmethod
    def clear_all_data(self) -> bool:
        """GDPR/Privacy right-to-be-forgotten data deletion."""
        pass
