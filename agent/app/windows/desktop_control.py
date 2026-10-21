"""Windows Desktop Control for Flash Agent.

Provides genuine Windows desktop interaction using Win32 API via ctypes:
- Read active window title, process name, and geometry.
- Mouse click (single, double, right) with user cursor position save & restore.
- Mouse drag & drop.
- Mouse scroll (vertical & horizontal).
- Keyboard shortcut synthesizer (Ctrl, Alt, Shift, Win + keys).
- Unicode text typing via SendInput.
"""

import ctypes
import ctypes.wintypes
import time
from typing import Optional, Union

# Win32 Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x00010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_ABSOLUTE = 0x8000

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

WHEEL_DELTA = 120

# Virtual Key Codes
VK_MAP = {
    # Modifiers
    "ctrl": 0x11, "control": 0x11, "lctrl": 0xA2, "rctrl": 0xA3,
    "alt": 0x12, "menu": 0x12, "lalt": 0xA4, "ralt": 0xA5,
    "shift": 0x10, "lshift": 0xA0, "rshift": 0xA1,
    "win": 0x5B, "windows": 0x5B, "cmd": 0x5B, "super": 0x5B,
    # Navigation & control
    "enter": 0x0D, "return": 0x0D,
    "tab": 0x09,
    "space": 0x20, "spacebar": 0x20,
    "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "escape": 0x1B, "esc": 0x1B,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "insert": 0x2D,
    # Letters
    **{chr(c): ord(chr(c).upper()) for c in range(ord('a'), ord('z') + 1)},
    # Digits
    **{str(i): ord(str(i)) for i in range(10)},
    # Function keys
    **{f"f{i}": 0x70 + (i - 1) for i in range(1, 25)},
}

# Structures for SendInput
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort),
    ]

class _INPUTunion(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("_input", _INPUTunion),
    ]


def _user32():
    return ctypes.windll.user32 if hasattr(ctypes, "windll") else None


class WindowsDesktopControl:
    """Provides native Windows mouse, keyboard, and window control."""

    @staticmethod
    def get_screen_size() -> tuple[int, int]:
        """Return (width, height) in pixels of primary display."""
        u32 = _user32()
        if not u32:
            return (1920, 1080)
        w = u32.GetSystemMetrics(0)  # SM_CXSCREEN
        h = u32.GetSystemMetrics(1)  # SM_CYSCREEN
        return (w, h)

    @staticmethod
    def get_cursor_position() -> tuple[int, int]:
        """Return current mouse pointer (x, y) coordinates."""
        u32 = _user32()
        if not u32:
            return (0, 0)
        pt = ctypes.wintypes.POINT()
        u32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    @staticmethod
    def set_cursor_position(x: int, y: int) -> bool:
        """Position the mouse cursor at (x, y)."""
        u32 = _user32()
        if not u32:
            return False
        return bool(u32.SetCursorPos(int(x), int(y)))

    @staticmethod
    def get_active_window_info() -> dict[str, Union[str, int, dict]]:
        """Get information about the currently focused/active window."""
        u32 = _user32()
        if not u32:
            return {"title": "Unknown", "hwnd": 0, "rect": {}}

        hwnd = u32.GetForegroundWindow()
        if not hwnd:
            return {"title": "None", "hwnd": 0, "rect": {}}

        length = u32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        u32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value

        rect = ctypes.wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(rect))

        pid = ctypes.wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        return {
            "title": title,
            "hwnd": int(hwnd),
            "pid": int(pid.value),
            "rect": {
                "left": rect.left,
                "top": rect.top,
                "right": rect.right,
                "bottom": rect.bottom,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top,
            },
        }

    @staticmethod
    def click(
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        double: bool = False,
        restore_cursor: bool = True,
    ) -> tuple[int, int]:
        """Perform a mouse click.
        
        If x and y are provided, moves to (x, y) to click.
        If restore_cursor is True, moves the mouse cursor back to the user's
        previous position after clicking (matching original Bluey UX!).
        """
        u32 = _user32()
        orig_x, orig_y = WindowsDesktopControl.get_cursor_position()

        target_x = x if x is not None else orig_x
        target_y = y if y is not None else orig_y

        if u32:
            WindowsDesktopControl.set_cursor_position(target_x, target_y)
            time.sleep(0.03)

            is_right = button.lower() in ("right", "r")
            down_flag = MOUSEEVENTF_RIGHTDOWN if is_right else MOUSEEVENTF_LEFTDOWN
            up_flag = MOUSEEVENTF_RIGHTUP if is_right else MOUSEEVENTF_LEFTUP

            clicks = 2 if double else 1
            for i in range(clicks):
                u32.mouse_event(down_flag, 0, 0, 0, 0)
                time.sleep(0.04)
                u32.mouse_event(up_flag, 0, 0, 0, 0)
                if i < clicks - 1:
                    time.sleep(0.08)

            if restore_cursor and (x is not None or y is not None):
                time.sleep(0.05)
                WindowsDesktopControl.set_cursor_position(orig_x, orig_y)

        return (target_x, target_y)

    @staticmethod
    def drag_and_drop(start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 15) -> None:
        """Drag from (start_x, start_y) to (end_x, end_y)."""
        u32 = _user32()
        if not u32:
            return

        WindowsDesktopControl.set_cursor_position(start_x, start_y)
        time.sleep(0.04)
        u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.04)

        for step in range(1, steps + 1):
            curr_x = int(start_x + (end_x - start_x) * (step / steps))
            curr_y = int(start_y + (end_y - start_y) * (step / steps))
            WindowsDesktopControl.set_cursor_position(curr_x, curr_y)
            time.sleep(0.015)

        time.sleep(0.05)
        u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    @staticmethod
    def scroll(dx: int = 0, dy: int = 0, at_x: Optional[int] = None, at_y: Optional[int] = None) -> None:
        """Smoothly scroll at (at_x, at_y) or current cursor location.
        
        Positive dy scrolls down, negative dy scrolls up.
        Positive dx scrolls right, negative dx scrolls left.
        """
        u32 = _user32()
        if not u32:
            return

        if at_x is not None and at_y is not None:
            WindowsDesktopControl.set_cursor_position(at_x, at_y)
            time.sleep(0.02)

        # In Windows mouse_event, positive WHEEL_DELTA scrolls up/forward, negative scrolls down.
        # We align with user expectation: dy > 0 scrolls content down (wheel down = negative delta).
        steps = 6
        step_dy = int((-dy * WHEEL_DELTA) / steps) if dy else 0
        step_dx = int((dx * WHEEL_DELTA) / steps) if dx else 0

        for _ in range(steps):
            if step_dy:
                u32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, step_dy, 0)
            if step_dx:
                u32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, step_dx, 0)
            time.sleep(0.015)

    @staticmethod
    def press_shortcut(combo_str: str) -> str:
        """Parse and press a keyboard shortcut combo (e.g. 'ctrl+c', 'alt+tab', 'win+r', 'ctrl+shift+s')."""
        u32 = _user32()
        if not u32:
            return combo_str

        # Clean string
        tokens = [t.strip().lower() for t in combo_str.replace(" ", "").split("+") if t.strip()]
        if not tokens:
            raise ValueError("Shortcut string cannot be empty.")

        # Safety Guardrails: Refuse system lock/shutdown combos without explicit bypass
        blocked_combos = {"win+l", "ctrl+alt+del", "ctrl+alt+delete"}
        normalized_str = "+".join(sorted(tokens))
        for blocked in blocked_combos:
            if "+".join(sorted(blocked.split("+"))) == normalized_str:
                raise PermissionError(f"Shortcut '{combo_str}' is blocked by security guardrails.")

        vk_codes: list[int] = []
        for token in tokens:
            code = VK_MAP.get(token)
            if code is None:
                raise ValueError(f"Unrecognized key token in shortcut: '{token}'")
            vk_codes.append(code)

        # Press down in order
        for code in vk_codes:
            u32.keybd_event(code, 0, 0, 0)
            time.sleep(0.01)

        time.sleep(0.03)

        # Release in reverse order
        for code in reversed(vk_codes):
            u32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)

        return "+".join(t.upper() for t in tokens)

    @staticmethod
    def type_text(text: str, press_return: bool = False, interval_ms: int = 15) -> int:
        """Type unicode text directly into the focused window using SendInput."""
        u32 = _user32()
        if not u32:
            return 0

        typed_chars = 0
        pause_sec = max(0.005, interval_ms / 1000.0)

        for char in text:
            if char == "\n" or char == "\r":
                u32.keybd_event(VK_MAP["enter"], 0, 0, 0)
                time.sleep(0.01)
                u32.keybd_event(VK_MAP["enter"], 0, KEYEVENTF_KEYUP, 0)
                time.sleep(pause_sec)
                typed_chars += 1
                continue
            elif char == "\t":
                u32.keybd_event(VK_MAP["tab"], 0, 0, 0)
                time.sleep(0.01)
                u32.keybd_event(VK_MAP["tab"], 0, KEYEVENTF_KEYUP, 0)
                time.sleep(pause_sec)
                typed_chars += 1
                continue

            char_code = ord(char)
            # SendInput unicode event
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.ki = KEYBDINPUT(wVk=0, wScan=char_code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=None)

            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.ki = KEYBDINPUT(wVk=0, wScan=char_code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)

            inputs = (INPUT * 2)(inp_down, inp_up)
            u32.SendInput(2, inputs, ctypes.sizeof(INPUT))
            typed_chars += 1
            time.sleep(pause_sec)

        if press_return:
            time.sleep(0.02)
            u32.keybd_event(VK_MAP["enter"], 0, 0, 0)
            time.sleep(0.01)
            u32.keybd_event(VK_MAP["enter"], 0, KEYEVENTF_KEYUP, 0)

        return typed_chars


desktop_control = WindowsDesktopControl()
