"""Windows UI Automation for Flash Agent.

Inspects focused and active windows using Microsoft UIAutomation.
Enumerates buttons, text fields, menus, tabs, and checks for password fields.
"""

from dataclasses import dataclass
from typing import Optional
import uiautomation as auto

from app.logging_config import get_logger
from app.windows.desktop_control import desktop_control

logger = get_logger("flash.windows.ui_automation")


@dataclass
class AccessibleControl:
    id: str
    control_type: str
    name: str
    automation_id: str
    rect: dict[str, int]
    is_password: bool
    is_enabled: bool
    grid_coord: str  # e.g. "@450,210" on a 0-1000 grid


class WindowsUIAutomation:
    """Discovers and inspects accessible controls in the active Windows application."""

    @staticmethod
    def get_active_window_element() -> Optional[auto.WindowControl]:
        """Get the active foreground window as a UIAutomation element."""
        info = desktop_control.get_active_window_info()
        hwnd = info.get("hwnd")
        if not hwnd:
            return None
        try:
            return auto.ControlFromHandle(hwnd)
        except Exception as e:
            logger.debug("Failed to get ControlFromHandle for hwnd %s: %s", hwnd, e)
            return None

    @staticmethod
    def inspect_active_window(limit: int = 100) -> dict:
        """Inspect the active window and return a list of accessible controls and metadata."""
        win_info = desktop_control.get_active_window_info()
        screen_w, screen_h = desktop_control.get_screen_size()
        screen_w = max(1, screen_w)
        screen_h = max(1, screen_h)

        controls: list[AccessibleControl] = []
        is_password_focused = False

        win_ctrl = WindowsUIAutomation.get_active_window_element()
        if not win_ctrl:
            return {
                "window_title": win_info.get("title", "Unknown"),
                "hwnd": win_info.get("hwnd", 0),
                "controls": [],
                "controls_count": 0,
                "is_password_focused": False,
            }

        try:
            # Check currently focused element
            focused = auto.GetFocusedControl()
            if focused:
                try:
                    is_password_focused = bool(getattr(focused, "IsPassword", False))
                except Exception:
                    pass

            idx = 1
            # Walk top interactive children
            for element, depth in auto.WalkControl(win_ctrl, maxDepth=4):
                if idx > limit:
                    break
                try:
                    rect = element.BoundingRectangle
                    if not rect or rect.width() <= 3 or rect.height() <= 3:
                        continue

                    c_type = element.ControlTypeName
                    # Filter for interactive controls
                    interactive_types = {
                        "ButtonControl", "EditControl", "CheckBoxControl", "RadioButtonControl",
                        "ComboBoxControl", "MenuItemControl", "TabItemControl", "HyperlinkControl",
                        "DocumentControl", "ListControl", "ListItemControl", "TreeItemControl",
                    }
                    if c_type not in interactive_types:
                        continue

                    name = element.Name or ""
                    auto_id = getattr(element, "AutomationId", "") or ""
                    is_pwd = bool(getattr(element, "IsPassword", False))
                    is_enabled = bool(getattr(element, "IsEnabled", True))

                    mid_x = (rect.left + rect.right) // 2
                    mid_y = (rect.top + rect.bottom) // 2
                    grid_x = int((mid_x / screen_w) * 1000)
                    grid_y = int((mid_y / screen_h) * 1000)

                    control_obj = AccessibleControl(
                        id=f"C{idx}",
                        control_type=c_type.replace("Control", "").lower(),
                        name=name.strip(),
                        automation_id=auto_id,
                        rect={
                            "left": rect.left,
                            "top": rect.top,
                            "right": rect.right,
                            "bottom": rect.bottom,
                            "width": rect.width(),
                            "height": rect.height(),
                            "center_x": mid_x,
                            "center_y": mid_y,
                        },
                        is_password=is_pwd,
                        is_enabled=is_enabled,
                        grid_coord=f"@{grid_x},{grid_y}",
                    )
                    controls.append(control_obj)
                    idx += 1
                except Exception:
                    continue
        except Exception as e:
            logger.warning("Error inspecting window controls via UIAutomation: %s", e)

        return {
            "window_title": win_info.get("title", ""),
            "hwnd": win_info.get("hwnd", 0),
            "pid": win_info.get("pid", 0),
            "window_rect": win_info.get("rect", {}),
            "is_password_focused": is_password_focused,
            "controls_count": len(controls),
            "controls": [c.__dict__ for c in controls],
        }

    @staticmethod
    def find_control(query: str) -> Optional[AccessibleControl]:
        """Find an accessible control in the active window by ID, name, or role."""
        data = WindowsUIAutomation.inspect_active_window(limit=120)
        controls = data.get("controls", [])
        q_lower = query.strip().lower()

        # 1. Exact ID match (e.g. "C1", "C5")
        for c in controls:
            if c["id"].lower() == q_lower:
                return AccessibleControl(**c)

        # 2. Exact or substring name match
        for c in controls:
            if c["name"] and q_lower == c["name"].lower():
                return AccessibleControl(**c)

        for c in controls:
            if c["name"] and q_lower in c["name"].lower():
                return AccessibleControl(**c)

        # 3. Control type match (e.g. "button", "edit")
        for c in controls:
            if q_lower == c["control_type"].lower():
                return AccessibleControl(**c)

        return None


ui_automation = WindowsUIAutomation()
