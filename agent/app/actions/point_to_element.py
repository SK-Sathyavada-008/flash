"""Action: point_to_element - Moves the mouse pointer to an accessible element or screen location."""

from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.windows.desktop_control import desktop_control
from app.windows.ui_automation import ui_automation
from app.logging_config import get_logger

logger = get_logger("flash.action.point_to_element")


class PointToElementAction(BaseAction):
    name = "point_to_element"
    description = "Points the mouse cursor directly at an accessible control (button, field, link) or screen coordinate (x, y)."
    requires_confirmation = False
    parameters_schema = {
        "target": {
            "type": "string",
            "required": False,
            "description": "Accessible control ID (e.g. 'C1') or element name.",
        },
        "x": {"type": "integer", "required": False, "description": "Target X screen coordinate."},
        "y": {"type": "integer", "required": False, "description": "Target Y screen coordinate."},
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        target = parameters.get("target")
        x = parameters.get("x")
        y = parameters.get("y")

        target_x = int(x) if x is not None else None
        target_y = int(y) if y is not None else None
        element_name = None

        if target and isinstance(target, str):
            ctrl = ui_automation.find_control(target)
            if ctrl:
                target_x = ctrl.rect["center_x"]
                target_y = ctrl.rect["center_y"]
                element_name = ctrl.name or ctrl.control_type
            elif target_x is None or target_y is None:
                return ActionResponse(
                    success=False,
                    action=self.name,
                    message=f"Could not find accessible element '{target}' to point to.",
                    error="ELEMENT_NOT_FOUND",
                )

        if target_x is None or target_y is None:
            return ActionResponse(
                success=False,
                action=self.name,
                message="Either 'target' element or (x, y) coordinates must be provided.",
                error="MISSING_TARGET",
            )

        try:
            desktop_control.set_cursor_position(target_x, target_y)
            desc = f"Pointed cursor at ({target_x}, {target_y})"
            if element_name:
                desc += f" ('{element_name}')"

            return ActionResponse(
                success=True,
                action=self.name,
                message=desc,
                data={"x": target_x, "y": target_y, "element": element_name, "target": target},
            )
        except Exception as e:
            logger.error("Failed to point to element: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Failed to point to element: {e}",
                error=str(e),
            )
