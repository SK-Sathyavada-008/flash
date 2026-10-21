"""Local File Storage Provider for Flash (Default, Zero-Cloud, 100% Private)."""

import json
import os
import time
from typing import Any, Dict, List, Optional
from app.config import settings
from app.storage.base import BaseStorage
from app.logging_config import get_logger

logger = get_logger("flash.storage.local")


class LocalFileStorage(BaseStorage):
    """Local JSON file storage engine."""

    def __init__(self, file_path: Optional[str] = None) -> None:
        if file_path:
            self.file_path = file_path
        else:
            root = settings.storage_base_dir if settings.storage_base_dir else str(settings.workspace_dir)
            base_dir = os.path.join(root, "data")
            os.makedirs(base_dir, exist_ok=True)
            self.file_path = os.path.join(base_dir, "flash_storage.json")
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not os.path.exists(self.file_path):
            initial = {
                "routines": {},
                "preferences": {
                    "sloth_mode": True,
                    "voice_enabled": True,
                    "speech_speed": 1.0,
                    "theme": "dark",
                },
                "task_history": [],
            }
            try:
                os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(initial, f, indent=2)
            except Exception as e:
                logger.error("Failed to initialize storage file: %s", e)

    def _read_data(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"routines": {}, "preferences": {}, "task_history": []}

    def _write_data(self, data: Dict[str, Any]) -> bool:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error("Failed to write storage file: %s", e)
            return False

    def get_provider_name(self) -> str:
        return "local_json"

    def is_cloud_enabled(self) -> bool:
        return False

    def save_routine(self, name: str, steps: List[Dict[str, Any]], description: str = "") -> bool:
        data = self._read_data()
        data.setdefault("routines", {})[name] = {
            "name": name,
            "description": description,
            "steps": steps,
            "updated_at": time.time(),
        }
        return self._write_data(data)

    def get_routine(self, name: str) -> Optional[Dict[str, Any]]:
        data = self._read_data()
        return data.get("routines", {}).get(name)

    def list_routines(self) -> List[Dict[str, Any]]:
        data = self._read_data()
        return list(data.get("routines", {}).values())

    def delete_routine(self, name: str) -> bool:
        data = self._read_data()
        routines = data.get("routines", {})
        if name in routines:
            del routines[name]
            return self._write_data(data)
        return False

    def save_preferences(self, preferences: Dict[str, Any]) -> bool:
        data = self._read_data()
        data.setdefault("preferences", {}).update(preferences)
        return self._write_data(data)

    def get_preferences(self) -> Dict[str, Any]:
        data = self._read_data()
        return data.get("preferences", {})

    def record_task_history(self, task_record: Dict[str, Any]) -> bool:
        data = self._read_data()
        history = data.setdefault("task_history", [])
        # Sanitize: ensure no raw images, screen bytes, or sensitive tokens
        sanitized = {
            "task_id": task_record.get("task_id", f"task_{int(time.time()*1000)}"),
            "intent": task_record.get("intent", ""),
            "success": task_record.get("success", True),
            "execution_time_ms": task_record.get("execution_time_ms", 0),
            "timestamp": time.time(),
        }
        history.insert(0, sanitized)
        # Keep latest 100
        data["task_history"] = history[:100]
        return self._write_data(data)

    def get_task_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        data = self._read_data()
        return data.get("task_history", [])[:limit]

    def clear_all_data(self) -> bool:
        return self._write_data({"routines": {}, "preferences": {}, "task_history": []})
