"""Action: capture_screen - Captures a screenshot of the display to the approved workspace."""

from datetime import datetime
from pathlib import Path
from typing import Any
import mss
import mss.tools

from app.actions.base import BaseAction
from app.models import ActionResponse
from app.security import resolve_safe_path
from app.config import settings
from app.logging_config import get_logger

logger = get_logger("flash.action.capture_screen")


class CaptureScreenAction(BaseAction):
    name = "capture_screen"
    description = "Captures an explicit screenshot of the desktop display and saves it to the sandboxed Flash workspace."
    requires_confirmation = True
    parameters_schema = {
        "permission_granted": {
            "type": "boolean",
            "required": True,
            "description": "Explicit user acknowledgement and consent to capture desktop pixels per privacy policy.",
        },
        "filename": {
            "type": "string",
            "required": False,
            "description": "Relative filename ending in .png to save screenshot (default: 'screenshots/screen_YYYYMMDD_HHMMSS.png').",
        },
        "monitor_index": {
            "type": "integer",
            "required": False,
            "default": 1,
            "description": "Monitor index (1 = primary display).",
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        if not parameters.get("permission_granted", False) and not confirmed:
            return ActionResponse(
                success=False,
                action=self.name,
                message="Screenshot capture requires explicit user permission per privacy policy.",
                error="PERMISSION_DENIED",
            )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"screenshots/screen_{timestamp}.png"
        filename = str(parameters.get("filename") or default_filename).strip()
        monitor_idx = int(parameters.get("monitor_index", 1))

        if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            filename += ".png"

        is_safe, resolved_path, error_msg = resolve_safe_path(
            filename,
            must_exist=False,
            create_parent=True,
            allowed_extensions={".png", ".jpg", ".jpeg"},
        )

        if not is_safe or resolved_path is None:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Access denied: {error_msg}",
                error="PATH_ACCESS_DENIED",
            )

        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                if monitor_idx >= len(monitors):
                    monitor_idx = 1
                mon = monitors[monitor_idx]
                sct_img = sct.grab(mon)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(resolved_path))

            rel_path = str(resolved_path.relative_to(settings.workspace_dir))
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Captured display screenshot to '{rel_path}'.",
                output_path=str(resolved_path),
                data={"filename": rel_path, "width": sct_img.width, "height": sct_img.height},
            )
        except Exception as e:
            logger.error("Failed to capture screenshot: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Screenshot capture failed: {e}",
                error=str(e),
            )
