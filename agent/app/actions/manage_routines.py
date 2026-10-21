"""Action: manage_routines - Manage and execute multi-step automated routines via Flash Storage."""

from typing import Any, List
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.storage import get_storage
from app.logging_config import get_logger

logger = get_logger("flash.action.manage_routines")


class ManageRoutinesAction(BaseAction):
    name = "manage_routines"
    description = "Create, list, inspect, and execute saved routines stored in Local JSON / MongoDB Atlas."
    requires_confirmation = False
    parameters_schema = {
        "operation": {
            "type": "string",
            "required": True,
            "description": "Operation to perform: 'save', 'list', 'get', 'delete'.",
        },
        "name": {
            "type": "string",
            "required": False,
            "description": "Routine identifier name (e.g. 'morning_routine', 'work_focus').",
        },
        "description": {
            "type": "string",
            "required": False,
            "description": "Short explanation of what the routine does.",
        },
        "steps": {
            "type": "array",
            "required": False,
            "description": "List of action steps for the routine.",
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        storage = get_storage()
        op = str(parameters.get("operation", "list")).lower().strip()
        routine_name = parameters.get("name")

        if op == "list":
            routines = storage.list_routines()
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Retrieved {len(routines)} saved routines from {storage.get_provider_name()}.",
                data={"routines": routines, "storage_provider": storage.get_provider_name()},
            )

        if not routine_name or not isinstance(routine_name, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'name' is required for this operation.",
                error="MISSING_PARAMETER",
            )

        clean_name = routine_name.strip()

        if op == "get":
            routine = storage.get_routine(clean_name)
            if not routine:
                return ActionResponse(
                    success=False,
                    action=self.name,
                    message=f"Routine '{clean_name}' not found.",
                    error="NOT_FOUND",
                )
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Found routine '{clean_name}'.",
                data=routine,
            )

        elif op == "save":
            steps = parameters.get("steps") or []
            desc = parameters.get("description", "")
            ok = storage.save_routine(clean_name, steps, desc)
            return ActionResponse(
                success=ok,
                action=self.name,
                message=f"Routine '{clean_name}' saved successfully in {storage.get_provider_name()}.",
                data={"name": clean_name, "steps_count": len(steps), "cloud_sync": storage.is_cloud_enabled()},
            )

        elif op == "delete":
            ok = storage.delete_routine(clean_name)
            return ActionResponse(
                success=ok,
                action=self.name,
                message=f"Routine '{clean_name}' deleted.",
                data={"deleted": ok},
            )

        return ActionResponse(
            success=False,
            action=self.name,
            message=f"Unsupported routine operation '{op}'. Supported: 'save', 'list', 'get', 'delete'.",
            error="INVALID_OPERATION",
        )
