"""Action 6: open_file - opens an authorized file in its default Windows application."""

import os
import sys
from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.security import resolve_safe_path
from app.logging_config import get_logger

logger = get_logger("flash.action.open_file")


class OpenFileAction(BaseAction):
    name = "open_file"
    description = "Opens an authorized file located within the Flash workspace in its default Windows application."
    requires_confirmation = False
    parameters_schema = {
        "filepath": {
            "type": "string",
            "required": True,
            "description": "Relative filename or path within the Flash workspace (e.g., 'spreadsheets/budget.xlsx').",
        }
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        filepath = parameters.get("filepath")
        if not filepath or not isinstance(filepath, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'filepath' is required and must be a string.",
                error="MISSING_PARAMETER",
            )

        is_safe, resolved_path, error_msg = resolve_safe_path(
            filepath,
            must_exist=True,
            create_parent=False,
        )

        if not is_safe or resolved_path is None:
            logger.warning("Access denied opening file '%s': %s", filepath, error_msg)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Access denied: {error_msg}",
                error="PATH_ACCESS_DENIED",
            )

        if not resolved_path.is_file():
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Path '{resolved_path.name}' is a directory, not a file.",
                output_path=str(resolved_path),
                error="NOT_A_FILE",
            )

        try:
            logger.info("Opening authorized file: %s", resolved_path)
            if sys.platform == "win32":
                os.startfile(str(resolved_path))
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(resolved_path)])

            file_size = resolved_path.stat().st_size
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Opened '{resolved_path.name}' in its default application.",
                output_path=str(resolved_path),
                data={
                    "filename": resolved_path.name,
                    "extension": resolved_path.suffix.lower(),
                    "size_bytes": file_size,
                    "path": str(resolved_path),
                },
            )
        except Exception as e:
            logger.error("Failed to open file '%s': %s", resolved_path, e, exc_info=True)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Failed to open file: {e}",
                output_path=str(resolved_path),
                error=str(e),
            )
