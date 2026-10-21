"""Action: mouse_scroll - Scrolls page content vertically or horizontally."""

from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.windows.desktop_control import desktop_control
from app.logging_config import get_logger

logger = get_logger("flash.action.mouse_scroll")


class MouseScrollAction(BaseAction):
    name = "mouse_scroll"
    description = "Scrolls the page or active window. Positive dy scrolls down, negative dy scrolls up."
    requires_confirmation = False
    parameters_schema = {
        "dy": {"type": "integer", "required": False, "default": 3, "description": "Vertical scroll units (positive = down, negative = up)."},
        "dx": {"type": "integer", "required": False, "default": 0, "description": "Horizontal scroll units (positive = right, negative = left)."},
        "x": {"type": "integer", "required": False, "description": "Optional X coordinate to hover over before scrolling."},
        "y": {"type": "integer", "required": False, "description": "Optional Y coordinate to hover over before scrolling."},
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        dy = int(parameters.get("dy", 3))
        dx = int(parameters.get("dx", 0))
        at_x = int(parameters["x"]) if "x" in parameters and parameters["x"] is not None else None
        at_y = int(parameters["y"]) if "y" in parameters and parameters["y"] is not None else None

        try:
            desktop_control.scroll(dx=dx, dy=dy, at_x=at_x, at_y=at_y)
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Scrolled window (dx={dx}, dy={dy}).",
                data={"dx": dx, "dy": dy, "x": at_x, "y": at_y},
            )
        except Exception as e:
            logger.error("Failed to scroll: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Scroll failed: {e}",
                error=str(e),
            )
