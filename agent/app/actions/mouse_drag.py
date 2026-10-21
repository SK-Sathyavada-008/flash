"""Action: mouse_drag - Performs a smooth mouse drag and drop between coordinates."""

from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.windows.desktop_control import desktop_control
from app.logging_config import get_logger

logger = get_logger("flash.action.mouse_drag")


class MouseDragAction(BaseAction):
    name = "mouse_drag"
    description = "Drags the mouse cursor from a starting coordinate (start_x, start_y) to an ending coordinate (end_x, end_y)."
    requires_confirmation = False
    parameters_schema = {
        "start_x": {"type": "integer", "required": True, "description": "Starting X coordinate."},
        "start_y": {"type": "integer", "required": True, "description": "Starting Y coordinate."},
        "end_x": {"type": "integer", "required": True, "description": "Ending X coordinate."},
        "end_y": {"type": "integer", "required": True, "description": "Ending Y coordinate."},
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        try:
            start_x = int(parameters["start_x"])
            start_y = int(parameters["start_y"])
            end_x = int(parameters["end_x"])
            end_y = int(parameters["end_y"])
        except (KeyError, ValueError, TypeError) as e:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Missing or invalid coordinates for drag: {e}",
                error="INVALID_PARAMETERS",
            )

        if start_x < 0 or start_y < 0 or end_x < 0 or end_y < 0:
            return ActionResponse(
                success=False,
                action=self.name,
                message="Drag coordinates must be non-negative.",
                error="OUT_OF_BOUNDS",
            )

        try:
            desktop_control.drag_and_drop(start_x, start_y, end_x, end_y)
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y}).",
                data={"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y},
            )
        except Exception as e:
            logger.error("Failed to execute mouse drag: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Mouse drag failed: {e}",
                error=str(e),
            )
