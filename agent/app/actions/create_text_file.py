"""Action 3: create_text_file - creates a text file in an approved Flash workspace directory."""

from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.security import resolve_safe_path
from app.logging_config import get_logger

logger = get_logger("flash.action.create_text_file")


class CreateTextFileAction(BaseAction):
    name = "create_text_file"
    description = "Creates a text file inside the approved Flash workspace directory."
    requires_confirmation = False
    parameters_schema = {
        "filename": {
            "type": "string",
            "required": True,
            "description": "Relative filename or path within the Flash workspace (e.g., 'notes.txt' or 'docs/summary.md').",
        },
        "content": {
            "type": "string",
            "required": True,
            "description": "The textual content to write into the file.",
        },
        "overwrite": {
            "type": "boolean",
            "required": False,
            "description": "Whether to overwrite an existing file (default True).",
            "default": True,
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        filename = parameters.get("filename")
        if not filename or not isinstance(filename, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'filename' is required and must be a string.",
                error="MISSING_PARAMETER",
            )

        content = parameters.get("content", "")
        if not isinstance(content, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'content' must be a string.",
                error="INVALID_PARAMETER",
            )

        overwrite = bool(parameters.get("overwrite", True))

        is_safe, resolved_path, error_msg = resolve_safe_path(
            filename,
            must_exist=False,
            create_parent=True,
        )

        if not is_safe or resolved_path is None:
            logger.warning("Path sandboxing blocked: %s", error_msg)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Access denied: {error_msg}",
                error="PATH_ACCESS_DENIED",
            )

        if resolved_path.exists() and not overwrite:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"File '{resolved_path.name}' already exists and overwrite is set to False.",
                output_path=str(resolved_path),
                error="FILE_EXISTS",
            )

        try:
            resolved_path.write_text(content, encoding="utf-8")
            byte_count = resolved_path.stat().st_size
            line_count = len(content.splitlines())
            logger.info("Created text file: %s (%d bytes, %d lines)", resolved_path, byte_count, line_count)

            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Successfully created '{resolved_path.name}' ({byte_count} bytes, {line_count} lines).",
                output_path=str(resolved_path),
                data={
                    "filename": resolved_path.name,
                    "path": str(resolved_path),
                    "bytes": byte_count,
                    "lines": line_count,
                },
            )
        except Exception as e:
            logger.error("Failed to write file '%s': %s", resolved_path, e, exc_info=True)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Failed to create file: {e}",
                output_path=str(resolved_path),
                error=str(e),
            )
