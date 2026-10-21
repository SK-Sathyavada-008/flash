"""Action: open_application - Opens or activates a Windows application by name."""

import os
import shutil
import subprocess
from typing import Any
import ctypes

from app.actions.base import BaseAction
from app.models import ActionResponse
from app.logging_config import get_logger

logger = get_logger("flash.action.open_application")

COMMON_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "cmd": "cmd.exe",
}


def _find_window_by_title_substring(title_substr: str) -> int:
    """Find a top-level window handle matching substring in title."""
    u32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
    if not u32:
        return 0

    found_hwnd = 0

    def enum_cb(hwnd, lparam):
        nonlocal found_hwnd
        if u32.IsWindowVisible(hwnd):
            length = u32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                u32.GetWindowTextW(hwnd, buf, length + 1)
                if title_substr.lower() in buf.value.lower():
                    found_hwnd = hwnd
                    return False
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    u32.EnumWindows(EnumWindowsProc(enum_cb), 0)
    return found_hwnd


class OpenApplicationAction(BaseAction):
    name = "open_application"
    description = "Launches or switches to a Windows desktop application (e.g., 'Notepad', 'Calculator', 'Excel', 'Word')."
    requires_confirmation = False
    parameters_schema = {
        "app_name": {
            "type": "string",
            "required": True,
            "description": "Name or executable of the application to open (e.g. 'Notepad', 'Calculator', 'Excel').",
        }
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        app_name = parameters.get("app_name")
        if not app_name or not isinstance(app_name, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'app_name' is required and must be a string.",
                error="MISSING_PARAMETER",
            )

        clean_name = app_name.strip()
        name_lower = clean_name.lower().replace(".exe", "")

        ALLOWED_APPS = {
            "notepad", "calculator", "calc", "paint", "mspaint", "explorer", "file explorer",
            "word", "excel", "powerpoint", "chrome", "edge", "terminal", "powershell", "cmd"
        }
        if name_lower not in ALLOWED_APPS and not confirmed:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Application '{clean_name}' is not in the allowed applications list.",
                error="APPLICATION_NOT_ALLOWED",
            )

        # 1. Check if matching window is already running and bring to foreground
        u32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
        if u32:
            existing_hwnd = _find_window_by_title_substring(clean_name)
            if existing_hwnd:
                try:
                    u32.ShowWindow(existing_hwnd, 9)  # SW_RESTORE
                    u32.SetForegroundWindow(existing_hwnd)
                    return ActionResponse(
                        success=True,
                        action=self.name,
                        message=f"Switched to running application '{clean_name}'.",
                        data={"app_name": clean_name, "hwnd": existing_hwnd, "status": "activated"},
                    )
                except Exception as ex:
                    logger.debug("Failed to activate existing window: %s", ex)

        # 2. Determine executable or launch target
        target_exe = COMMON_APPS.get(name_lower, f"{clean_name}.exe")
        resolved_bin = shutil.which(target_exe) or shutil.which(clean_name)

        try:
            if resolved_bin:
                subprocess.Popen([resolved_bin], shell=False)
            elif name_lower in ("calculator", "calc"):
                os.system("start calc:")
            else:
                # Try opening via os.startfile
                os.startfile(target_exe)

            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Launched application '{clean_name}'.",
                data={"app_name": clean_name, "status": "launched"},
            )
        except Exception as e:
            logger.error("Failed to launch application '%s': %s", clean_name, e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Could not open application '{clean_name}': {e}",
                error=str(e),
                data={"app_name": clean_name},
            )
