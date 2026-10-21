"""Flash Storage Engine factory."""

from typing import Optional
from app.config import settings
from app.storage.base import BaseStorage
from app.storage.local_storage import LocalFileStorage
from app.storage.mongo_atlas import MongoAtlasStorage

_storage_instance: Optional[BaseStorage] = None


def get_storage() -> BaseStorage:
    """Return the configured storage provider (MongoDB Atlas if URI is set, else Local JSON)."""
    global _storage_instance
    if _storage_instance is None:
        if settings.mongodb_uri:
            _storage_instance = MongoAtlasStorage()
        else:
            _storage_instance = LocalFileStorage()
    return _storage_instance


def reset_storage_for_tests() -> None:
    """Reset the singleton instance for testing."""
    global _storage_instance
    _storage_instance = None
