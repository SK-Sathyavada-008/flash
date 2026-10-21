"""Action: dictate_text - Dictates speech or text into the currently active or specified application."""

import time
from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.windows.desktop_control import desktop_control
from app.logging_config import get_logger

logger = get_logger("flash.action.dictate_text")


class DictateTextAction(BaseAction):
    name = "dictate_text"
    description = "Dictates transcribed speech or text directly into the focused application window."
    requires_confirmation = False
    parameters_schema = {
        "text": {
            "type": "string",
            "required": True,
            "description": "Text content to dictate/type into the window.",
        },
        "target_app": {
            "type": "string",
            "required": False,
            "description": "Optional application name to focus before typing (e.g. 'Notepad', 'Word').",
        },
        "press_return": {
            "type": "boolean",
            "required": False,
            "default": False,
            "description": "Whether to press Enter after typing.",
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        text = parameters.get("text")
        if not text or not isinstance(text, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'text' is required and must be a string.",
                error="MISSING_PARAMETER",
            )

        clean_text = text.strip()
        target_app = parameters.get("target_app")
        press_return = bool(parameters.get("press_return", False))

        if target_app:
            from app.actions.open_application import OpenApplicationAction
            app_act = OpenApplicationAction()
            app_act.run({"app_name": target_app})
            time.sleep(0.3)

        try:
            typed_count = desktop_control.type_text(clean_text, press_return=press_return)
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Dictated {typed_count} characters into active application.",
                data={"characters_typed": typed_count, "target_app": target_app},
            )
        except Exception as e:
            logger.error("Failed to dictate text: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Dictation failed: {e}",
                error=str(e),
            )
