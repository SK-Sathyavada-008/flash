"""Action registry for Flash Agent.

Discovers, validates, and manages execution of all agent actions.
"""

import time
from typing import Optional
from app.actions.base import BaseAction
from app.models import ActionInfo, ActionResponse
from app.security import (
    ConfirmationRequiredError,
    EmergencyStopTriggeredError,
    emergency_stop,
)
from app.logging_config import get_logger

logger = get_logger("flash.registry")


class ActionRegistry:
    """Registry managing available actions and their validation."""

    def __init__(self) -> None:
        self._actions: dict[str, BaseAction] = {}

    def register(self, action: BaseAction) -> None:
        """Register an action instance."""
        if not action.name:
            raise ValueError(f"Action {action} must have a non-empty 'name'.")
        self._actions[action.name] = action
        logger.debug("Registered action: '%s'", action.name)

    def get(self, name: str) -> Optional[BaseAction]:
        """Retrieve an action by name."""
        return self._actions.get(name)

    def list_actions(self) -> list[ActionInfo]:
        """Return metadata for all registered actions."""
        return [
            ActionInfo(
                name=act.name,
                description=act.description,
                requires_confirmation=act.requires_confirmation,
                parameters_schema=act.parameters_schema,
            )
            for act in sorted(self._actions.values(), key=lambda a: a.name)
        ]

    def execute(self, name: str, parameters: dict, confirmed: bool = False) -> ActionResponse:
        """Execute an action with safety checks, error capture, and execution timing."""
        start_time = time.perf_counter()

        # 1. Global emergency stop verification
        try:
            emergency_stop.verify_not_stopped()
        except EmergencyStopTriggeredError as e:
            return ActionResponse(
                success=False,
                action=name,
                message=str(e),
                error="EMERGENCY_STOP_ACTIVE",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 2. Action existence check
        action = self.get(name)
        if not action:
            return ActionResponse(
                success=False,
                action=name,
                message=f"Unknown action '{name}'. Available actions: {list(self._actions.keys())}",
                error="UNKNOWN_ACTION",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 3. Confirmation check
        if action.requires_confirmation and not confirmed:
            return ActionResponse(
                success=False,
                action=name,
                message=f"Action '{name}' requires explicit user confirmation. Pass confirmed=True to proceed.",
                error="CONFIRMATION_REQUIRED",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 4. Action execution
        try:
            logger.info("Executing action '%s' with parameters %s", name, parameters)
            response = action.run(parameters or {}, confirmed=confirmed)
        except Exception as e:
            logger.error("Unhandled exception executing '%s': %s", name, e, exc_info=True)
            response = ActionResponse(
                success=False,
                action=name,
                message=f"Action execution raised an unexpected exception: {e}",
                error=str(e),
            )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.execution_time_ms = elapsed_ms

        try:
            from app.telemetry.sentry_tracer import tracer
            tracer.record_tool_execution(name, elapsed_ms, response.success, response.error)
        except Exception:
            pass

        return response


# Global registry singleton
registry = ActionRegistry()


def register_default_actions() -> None:
    """Register all Flash actions (Core Milestones 1-5)."""
    from app.actions.open_url import OpenUrlAction
    from app.actions.type_text import TypeTextAction
    from app.actions.create_text_file import CreateTextFileAction
    from app.actions.create_grocery_list import CreateGroceryListAction
    from app.actions.create_spreadsheet import CreateSpreadsheetAction
    from app.actions.open_file import OpenFileAction
    from app.actions.get_agent_status import GetAgentStatusAction
    from app.actions.create_word_document import CreateWordDocumentAction
    from app.actions.create_presentation import CreatePresentationAction
    from app.actions.mouse_click import MouseClickAction
    from app.actions.mouse_drag import MouseDragAction
    from app.actions.mouse_scroll import MouseScrollAction
    from app.actions.press_keys import PressKeysAction
    from app.actions.open_application import OpenApplicationAction
    from app.actions.inspect_screen import InspectScreenAction
    from app.actions.point_to_element import PointToElementAction
    from app.actions.capture_screen import CaptureScreenAction
    from app.actions.organize_files import OrganizeFilesAction
    from app.actions.web_research import WebResearchAction
    from app.actions.browser_automate import BrowserAutomateAction
    from app.actions.dictate_text import DictateTextAction
    from app.actions.meeting_assistance import MeetingAssistanceAction
    from app.actions.speak_text import SpeakTextAction
    from app.actions.stagehand_browser import StagehandBrowserAction
    from app.actions.manage_routines import ManageRoutinesAction

    registry.register(OpenUrlAction())
    registry.register(TypeTextAction())
    registry.register(CreateTextFileAction())
    registry.register(CreateGroceryListAction())
    registry.register(CreateSpreadsheetAction())
    registry.register(OpenFileAction())
    registry.register(GetAgentStatusAction())
    registry.register(CreateWordDocumentAction())
    registry.register(CreatePresentationAction())
    registry.register(MouseClickAction())
    registry.register(MouseDragAction())
    registry.register(MouseScrollAction())
    registry.register(PressKeysAction())
    registry.register(OpenApplicationAction())
    registry.register(InspectScreenAction())
    registry.register(PointToElementAction())
    registry.register(CaptureScreenAction())
    registry.register(OrganizeFilesAction())
    registry.register(WebResearchAction())
    registry.register(BrowserAutomateAction())
    registry.register(DictateTextAction())
    registry.register(MeetingAssistanceAction())
    registry.register(SpeakTextAction())
    registry.register(StagehandBrowserAction())
    registry.register(ManageRoutinesAction())

    logger.info("Registered %d Flash actions.", len(registry._actions))


# Initialize default actions
register_default_actions()
