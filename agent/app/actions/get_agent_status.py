"""Action 7: get_agent_status - reports connection status, available actions and current activity."""

import platform
import sys
from typing import Any
from app.actions.base import BaseAction
from app.config import settings
from app.models import ActionResponse
from app.security import emergency_stop
from app.logging_config import get_logger

logger = get_logger("flash.action.get_agent_status")


class GetAgentStatusAction(BaseAction):
    name = "get_agent_status"
    description = "Reports the agent operational status, connection health, emergency stop state, and registered actions."
    requires_confirmation = False
    parameters_schema = {}

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        from app.actions.registry import registry

        is_stopped = emergency_stop.is_stopped
        current_status = "stopped" if is_stopped else "ready"

        workspace_path = settings.workspace_dir.resolve()
        workspace_exists = workspace_path.exists()

        file_count = 0
        if workspace_exists:
            try:
                file_count = sum(1 for _ in workspace_path.glob("**/*") if _.is_file())
            except Exception:
                file_count = -1

        available_actions = [info.name for info in registry.list_actions()]

        data = {
            "status": current_status,
            "character": settings.character_name,
            "version": settings.app_version,
            "emergency_stop_active": is_stopped,
            "workspace_dir": str(workspace_path),
            "workspace_files_count": file_count,
            "available_actions": available_actions,
            "action_count": len(available_actions),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "python_version": sys.version.split()[0],
                "node": platform.node(),
            },
        }

        return ActionResponse(
            success=True,
            action=self.name,
            message=f"Agent '{settings.character_name}' is {current_status}. {len(available_actions)} actions registered.",
            data=data,
        )
