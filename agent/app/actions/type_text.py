"""Action 2: type_text - types text into the currently focused Windows application."""

import sys
import time
from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.logging_config import get_logger

logger = get_logger("flash.action.type_text")

# Windows Win32 ctypes structures for SendInput
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    VK_RETURN = 0x0D
    VK_TAB = 0x09

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_ulong),
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        _anonymous_ = ("_input",)
        _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]


def win32_send_unicode_char(char: str) -> None:
    """Send a single character or control key via SendInput."""
    if sys.platform != "win32":
        return

    user32 = ctypes.windll.user32

    if char == "\n":
        # Press and release Return
        down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_RETURN, wScan=0, dwFlags=0, time=0, dwExtraInfo=0))
        up = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(wVk=VK_RETURN, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0),
        )
        user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
        user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
    elif char == "\t":
        # Press and release Tab
        down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_TAB, wScan=0, dwFlags=0, time=0, dwExtraInfo=0))
        up = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(wVk=VK_TAB, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0),
        )
        user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
        user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
    else:
        # Unicode character injection
        code = ord(char)
        down = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0),
        )
        up = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0),
        )
        user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
        user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))


class TypeTextAction(BaseAction):
    name = "type_text"
    description = "Types text into the active Windows application using native SendInput automation."
    requires_confirmation = False
    parameters_schema = {
        "text": {
            "type": "string",
            "required": True,
            "description": "The string content to type into the focused window.",
        },
        "interval_ms": {
            "type": "integer",
            "required": False,
            "description": "Delay in milliseconds between characters (default 10ms).",
            "default": 10,
        },
        "press_return": {
            "type": "boolean",
            "required": False,
            "description": "Whether to press Return at the end of typing.",
            "default": False,
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        text = parameters.get("text")
        if text is None or not isinstance(text, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'text' is required and must be a string.",
                error="MISSING_PARAMETER",
            )

        interval_ms = parameters.get("interval_ms", 10)
        try:
            interval = max(0.0, float(interval_ms) / 1000.0)
        except (ValueError, TypeError):
            interval = 0.01

        press_return = bool(parameters.get("press_return", False))

        logger.info("Typing text (len=%d chars, press_return=%s)", len(text), press_return)

        try:
            count = 0
            for ch in text:
                win32_send_unicode_char(ch)
                count += 1
                if interval > 0:
                    time.sleep(interval)

            if press_return:
                time.sleep(0.05)
                win32_send_unicode_char("\n")

            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Typed {count} character(s) successfully into the focused application.",
                data={
                    "characters_typed": count,
                    "press_return": press_return,
                    "preview": text[:40] + ("..." if len(text) > 40 else ""),
                },
            )
        except Exception as e:
            logger.error("Failed to type text: %s", e, exc_info=True)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Typing automation failed: {e}",
                error=str(e),
            )
