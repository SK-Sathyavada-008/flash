"""MongoDB Atlas Cloud Storage Provider for Flash (Optional Cloud Layer).

Provides synchronization of:
- User-defined automated routines
- Assistant preferences
- Cross-device task history

PRIVACY & DATA BOUNDARY:
- Screen captures, transcripts, and document files are NEVER uploaded to MongoDB Atlas.
- Operates on a dedicated database 'flash_agent'.
- If MongoDB Atlas is unavailable or credentials are omitted, seamlessly falls back
  to LocalFileStorage.
"""

import time
from typing import Any, Dict, List, Optional
from app.config import settings
from app.storage.base import BaseStorage
from app.storage.local_storage import LocalFileStorage
from app.logging_config import get_logger

logger = get_logger("flash.storage.mongodb")


class MongoAtlasStorage(BaseStorage):
    """MongoDB Atlas Cloud Storage implementation."""

    def __init__(self, uri: Optional[str] = None, database_name: Optional[str] = None) -> None:
        self.uri = uri if uri is not None else settings.mongodb_uri
        self.database_name = database_name or getattr(settings, "mongodb_database_name", "flash_agent")
        self.local_fallback = LocalFileStorage()
        self._client = None
        self._db = None
        self._connected = False
        self._init_connection()

    def _init_connection(self) -> None:
        if not self.uri:
            logger.info("No MongoDB URI configured. Using local JSON storage.")
            return

        try:
            import pymongo
            self._client = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=3000)
            # Ping database
            self._client.admin.command("ping")
            self._db = self._client[self.database_name]
            self._connected = True
            logger.info("Successfully connected to MongoDB Atlas database '%s'", self.database_name)
        except Exception as e:
            logger.warning("MongoDB Atlas connection failed: %s. Falling back to local storage.", e)
            self._connected = False

    def get_provider_name(self) -> str:
        return "mongodb_atlas" if self._connected else "local_json (fallback)"

    def is_cloud_enabled(self) -> bool:
        return self._connected

    def save_routine(self, name: str, steps: List[Dict[str, Any]], description: str = "") -> bool:
        # Always write to local fallback first for resilience
        self.local_fallback.save_routine(name, steps, description)
        if not self._connected or self._db is None:
            return True

        try:
            col = self._db["routines"]
            col.update_one(
                {"name": name},
                {"$set": {
                    "name": name,
                    "description": description,
                    "steps": steps,
                    "updated_at": time.time(),
                }},
                upsert=True,
            )
            return True
        except Exception as e:
            logger.error("MongoDB Atlas error in save_routine: %s", e)
            return False

    def get_routine(self, name: str) -> Optional[Dict[str, Any]]:
        if not self._connected or self._db is None:
            return self.local_fallback.get_routine(name)

        try:
            doc = self._db["routines"].find_one({"name": name}, {"_id": 0})
            if doc:
                return doc
        except Exception as e:
            logger.error("MongoDB Atlas error in get_routine: %s", e)
        return self.local_fallback.get_routine(name)

    def list_routines(self) -> List[Dict[str, Any]]:
        if not self._connected or self._db is None:
            return self.local_fallback.list_routines()

        try:
            cursor = self._db["routines"].find({}, {"_id": 0})
            items = list(cursor)
            return items if items else self.local_fallback.list_routines()
        except Exception as e:
            logger.error("MongoDB Atlas error in list_routines: %s", e)
            return self.local_fallback.list_routines()

    def delete_routine(self, name: str) -> bool:
        self.local_fallback.delete_routine(name)
        if not self._connected or self._db is None:
            return True

        try:
            self._db["routines"].delete_one({"name": name})
            return True
        except Exception as e:
            logger.error("MongoDB Atlas error in delete_routine: %s", e)
            return False

    def save_preferences(self, preferences: Dict[str, Any]) -> bool:
        self.local_fallback.save_preferences(preferences)
        if not self._connected or self._db is None:
            return True

        try:
            col = self._db["preferences"]
            col.update_one(
                {"id": "user_preferences"},
                {"$set": {"preferences": preferences, "updated_at": time.time()}},
                upsert=True,
            )
            return True
        except Exception as e:
            logger.error("MongoDB Atlas error in save_preferences: %s", e)
            return False

    def get_preferences(self) -> Dict[str, Any]:
        if not self._connected or self._db is None:
            return self.local_fallback.get_preferences()

        try:
            doc = self._db["preferences"].find_one({"id": "user_preferences"}, {"_id": 0})
            if doc and "preferences" in doc:
                return doc["preferences"]
        except Exception as e:
            logger.error("MongoDB Atlas error in get_preferences: %s", e)
        return self.local_fallback.get_preferences()

    def record_task_history(self, task_record: Dict[str, Any]) -> bool:
        self.local_fallback.record_task_history(task_record)
        if not self._connected or self._db is None:
            return True

        try:
            sanitized = {
                "task_id": task_record.get("task_id", f"task_{int(time.time()*1000)}"),
                "intent": task_record.get("intent", ""),
                "success": task_record.get("success", True),
                "execution_time_ms": task_record.get("execution_time_ms", 0),
                "timestamp": time.time(),
            }
            self._db["task_history"].insert_one(sanitized)
            return True
        except Exception as e:
            logger.error("MongoDB Atlas error in record_task_history: %s", e)
            return False

    def get_task_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self._connected or self._db is None:
            return self.local_fallback.get_task_history(limit)

        try:
            cursor = self._db["task_history"].find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
            items = list(cursor)
            return items if items else self.local_fallback.get_task_history(limit)
        except Exception as e:
            logger.error("MongoDB Atlas error in get_task_history: %s", e)
            return self.local_fallback.get_task_history(limit)

    def clear_all_data(self) -> bool:
        self.local_fallback.clear_all_data()
        if not self._connected or self._db is None:
            return True

        try:
            self._db["routines"].drop()
            self._db["preferences"].drop()
            self._db["task_history"].drop()
            return True
        except Exception as e:
            logger.error("MongoDB Atlas error in clear_all_data: %s", e)
            return False
