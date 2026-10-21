"""Action: press_keys - Presses keyboard shortcuts and key combinations."""

from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.windows.desktop_control import desktop_control
from app.logging_config import get_logger

logger = get_logger("flash.action.press_keys")


class PressKeysAction(BaseAction):
    name = "press_keys"
    description = "Synthesizes a keyboard shortcut combo like 'ctrl+c', 'ctrl+v', 'ctrl+s', 'alt+tab', 'enter', 'esc'."
    requires_confirmation = False
    parameters_schema = {
        "combo": {
            "type": "string",
            "required": True,
            "description": "Shortcut combination string (e.g., 'ctrl+c', 'alt+f4', 'ctrl+shift+s').",
        }
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        combo_val = parameters.get("combo") or parameters.get("keys")
        if isinstance(combo_val, list):
            combo_val = "+".join(str(k).strip() for k in combo_val if str(k).strip())

        if not combo_val or not isinstance(combo_val, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'combo' or 'keys' is required.",
                error="MISSING_PARAMETER",
            )

        clean_combo = combo_val.strip().lower()

        # Check for destructive combos requiring confirmation (like Alt+F4)
        if clean_combo == "alt+f4" and not confirmed:
            return ActionResponse(
                success=False,
                action=self.name,
                message="Closing active window with Alt+F4 requires user confirmation.",
                error="CONFIRMATION_REQUIRED",
            )

        try:
            executed_combo = desktop_control.press_shortcut(clean_combo)
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Pressed keyboard shortcut '{executed_combo}'.",
                data={"combo": executed_combo},
            )
        except PermissionError as e:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Shortcut blocked by security guardrails: {e}",
                error="GUARDRAIL_BLOCKED",
            )
        except ValueError as e:
            return ActionResponse(
                success=False,
                action=self.name,
                message=str(e),
                error="INVALID_SHORTCUT",
            )
        except Exception as e:
            logger.error("Failed to press shortcut '%s': %s", clean_combo, e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Failed to press keys: {e}",
                error=str(e),
            )
