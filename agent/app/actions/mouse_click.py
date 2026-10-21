"""Action: mouse_click - Clicks on screen coordinates or accessible UI elements."""

from typing import Any, Optional
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.windows.desktop_control import desktop_control
from app.windows.ui_automation import ui_automation
from app.logging_config import get_logger

logger = get_logger("flash.action.mouse_click")


class MouseClickAction(BaseAction):
    name = "mouse_click"
    description = "Clicks a specific coordinate (x, y) or an identified accessible UI element on the screen."
    requires_confirmation = False
    parameters_schema = {
        "x": {"type": "integer", "required": False, "description": "Target X screen pixel coordinate."},
        "y": {"type": "integer", "required": False, "description": "Target Y screen pixel coordinate."},
        "target": {"type": "string", "required": False, "description": "Accessible control ID (e.g. 'C1') or button name."},
        "button": {"type": "string", "required": False, "default": "left", "description": "'left' or 'right'."},
        "double": {"type": "boolean", "required": False, "default": False, "description": "Double-click if True."},
        "restore_cursor": {"type": "boolean", "required": False, "default": True, "description": "Restore cursor position after click."},
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        target = parameters.get("target")
        x = parameters.get("x")
        y = parameters.get("y")
        button = str(parameters.get("button", "left"))
        double = bool(parameters.get("double", False))
        restore_cursor = bool(parameters.get("restore_cursor", True))

        target_x: Optional[int] = int(x) if x is not None else None
        target_y: Optional[int] = int(y) if y is not None else None
        element_name = None

        if target and isinstance(target, str):
            ctrl = ui_automation.find_control(target)
            if ctrl:
                target_x = ctrl.rect["center_x"]
                target_y = ctrl.rect["center_y"]
                element_name = ctrl.name or ctrl.control_type
                if ctrl.is_password:
                    return ActionResponse(
                        success=False,
                        action=self.name,
                        message="Cannot interact with protected password field.",
                        error="PASSWORD_FIELD_BLOCKED",
                    )
            elif target_x is None or target_y is None:
                return ActionResponse(
                    success=False,
                    action=self.name,
                    message=f"Accessible element '{target}' could not be located on the active screen.",
                    error="ELEMENT_NOT_FOUND",
                )

        if target_x is None or target_y is None:
            if not target and (x is None or y is None):
                return ActionResponse(
                    success=False,
                    action=self.name,
                    message="Either 'target' element or both 'x' and 'y' coordinates must be specified.",
                    error="MISSING_PARAMETER",
                )
            target_x, target_y = desktop_control.get_cursor_position()

        try:
            actual_x, actual_y = desktop_control.click(
                x=target_x,
                y=target_y,
                button=button,
                double=double,
                restore_cursor=restore_cursor,
            )
            desc = f"Clicked {button} button at ({actual_x}, {actual_y})"
            if element_name:
                desc += f" on element '{element_name}'"

            return ActionResponse(
                success=True,
                action=self.name,
                message=desc,
                data={"x": actual_x, "y": actual_y, "button": button, "double": double, "target": target},
            )
        except Exception as e:
            logger.error("Failed to click: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Failed to perform click: {e}",
                error=str(e),
            )
