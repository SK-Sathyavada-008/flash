"""Action: inspect_screen - Reads the active window title and accessible UI controls."""

from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.windows.ui_automation import ui_automation
from app.logging_config import get_logger

logger = get_logger("flash.action.inspect_screen")


class InspectScreenAction(BaseAction):
    name = "inspect_screen"
    description = "Inspects the active foreground window, listing accessible controls (buttons, inputs, menus, tabs) and their positions."
    requires_confirmation = False
    parameters_schema = {
        "limit": {
            "type": "integer",
            "required": False,
            "default": 50,
            "description": "Maximum number of accessible controls to return.",
        }
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        limit = int(parameters.get("limit", 50))
        try:
            report = ui_automation.inspect_active_window(limit=limit)
            win_title = report.get("window_title") or "Active Window"
            count = report.get("controls_count", 0)

            msg = f"Inspected '{win_title}'. Found {count} interactive controls."
            if report.get("is_password_focused"):
                msg += " (Warning: Password field is currently focused)."

            return ActionResponse(
                success=True,
                action=self.name,
                message=msg,
                data=report,
            )
        except Exception as e:
            logger.error("Failed to inspect screen: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Failed to inspect screen controls: {e}",
                error=str(e),
            )
