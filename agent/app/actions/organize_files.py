"""Action: organize_files - Previews and organizes files by category with required confirmation."""

import os
import shutil
from pathlib import Path
from typing import Any

from app.actions.base import BaseAction
from app.models import ActionResponse
from app.security import resolve_safe_path
from app.config import settings
from app.logging_config import get_logger

logger = get_logger("flash.action.organize_files")

EXTENSION_CATEGORIES = {
    "documents": {".docx", ".doc", ".pdf", ".txt", ".md", ".rtf"},
    "spreadsheets": {".xlsx", ".xls", ".csv"},
    "presentations": {".pptx", ".ppt"},
    "images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"},
    "audio": {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".webm"},
    "archives": {".zip", ".tar", ".gz", ".7z"},
}


class OrganizeFilesAction(BaseAction):
    name = "organize_files"
    description = "Organizes files in a workspace folder into subdirectories by type. Generates a preview and requires confirmation before moving files."
    requires_confirmation = True
    parameters_schema = {
        "folder": {
            "type": "string",
            "required": False,
            "default": ".",
            "description": "Relative folder path within the workspace to organize.",
        },
        "by": {
            "type": "string",
            "required": False,
            "default": "category",
            "description": "Organization strategy ('category' or 'extension').",
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        folder_str = str(parameters.get("folder_path") or parameters.get("folder") or ".").strip()
        strategy = str(parameters.get("by", "category")).lower()

        is_safe, resolved_folder, error_msg = resolve_safe_path(
            folder_str,
            must_exist=True,
            create_parent=False,
        )

        if not is_safe or resolved_folder is None or not resolved_folder.is_dir():
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Invalid folder path: {error_msg or 'Path is not a directory.'}",
                error="PATH_ACCESS_DENIED",
            )

        # Plan the proposed moves
        proposed_moves: list[dict[str, str]] = []

        for item in resolved_folder.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                target_subdir = "other"
                if strategy == "extension" and ext:
                    target_subdir = ext.lstrip(".")
                else:
                    for cat, extensions in EXTENSION_CATEGORIES.items():
                        if ext in extensions:
                            target_subdir = cat
                            break

                dest_dir = resolved_folder / target_subdir
                dest_file = dest_dir / item.name

                # Don't move if already in that subdir
                if item.parent == dest_dir:
                    continue

                proposed_moves.append({
                    "filename": item.name,
                    "source": str(item.relative_to(settings.workspace_dir)),
                    "destination": str(dest_file.relative_to(settings.workspace_dir)),
                    "category": target_subdir,
                })

        if not proposed_moves:
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"No unorganized files found in '{folder_str}'. Workspace is clean.",
                data={"proposed_moves": []},
            )

        # If not confirmed, return the plan for user review
        if not confirmed:
            return ActionResponse(
                success=False,
                action=self.name,
                message=(
                    f"Preview: Flash proposes moving {len(proposed_moves)} files into organized folders. "
                    "Please confirm to execute."
                ),
                error="CONFIRMATION_REQUIRED",
                data={"proposed_moves": proposed_moves},
            )

        # Execute confirmed moves
        moved_count = 0
        executed_moves: list[dict[str, str]] = []

        try:
            for move in proposed_moves:
                src_path = settings.workspace_dir / move["source"]
                dst_path = settings.workspace_dir / move["destination"]
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_path), str(dst_path))
                moved_count += 1
                executed_moves.append(move)

            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Successfully organized {moved_count} files in '{folder_str}'.",
                data={"moved_count": moved_count, "executed_moves": executed_moves},
            )
        except Exception as e:
            logger.error("Error executing file moves: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"File organization encountered an error: {e}",
                error=str(e),
                data={"moved_count": moved_count},
            )
