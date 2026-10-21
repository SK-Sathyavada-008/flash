"""Local agent service orchestrating state, actions, and emergency controls."""

import platform
import sys
from app.actions.registry import registry, register_default_actions
from app.config import settings
from app.models import ActionRequest, ActionResponse, AgentStatusResponse
from app.security import emergency_stop
from app.logging_config import get_logger

logger = get_logger("flash.service")


class AgentService:
    """Core local service coordinating the Flash Windows Desktop Agent."""

    def __init__(self) -> None:
        self._initialized = False

    def startup(self) -> None:
        """Run startup tasks: register actions, create directories, initialize state."""
        if self._initialized:
            return

        logger.info("Initializing %s v%s...", settings.app_name, settings.app_version)
        settings.ensure_directories()
        register_default_actions()
        self._initialized = True
        logger.info("Flash Agent startup complete. Workspace: %s", settings.workspace_dir)

    def shutdown(self) -> None:
        """Clean shutdown tasks."""
        logger.info("Shutting down Flash Agent...")
        self._initialized = False

    def execute_action(self, request: ActionRequest) -> ActionResponse:
        """Execute an action through the validated action registry."""
        return registry.execute(
            name=request.action,
            parameters=request.parameters,
            confirmed=request.confirmed,
        )

    def trigger_emergency_stop(self, reason: str = "User stop request") -> dict[str, str]:
        """Trigger the global emergency stop circuit."""
        emergency_stop.trigger(reason)
        return {"status": "stopped", "message": "Emergency stop has been triggered. Agent is halted."}

    def resume_from_emergency_stop(self) -> dict[str, str]:
        """Clear the emergency stop circuit and resume operations."""
        emergency_stop.resume()
        return {"status": "ready", "message": "Emergency stop cleared. Agent is operational."}

    def get_status(self) -> AgentStatusResponse:
        """Compile a comprehensive operational and diagnostics report."""
        is_stopped = emergency_stop.is_stopped
        status = "stopped" if is_stopped else "ready"
        action_details = registry.list_actions()
        action_names = [a.name for a in action_details]

        return AgentStatusResponse(
            status=status,
            character=settings.character_name,
            version=settings.app_version,
            emergency_stop_active=is_stopped,
            workspace_dir=str(settings.workspace_dir.resolve()),
            available_actions=action_names,
            action_details=action_details,
            system_info={
                "os": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "architecture": platform.machine(),
                "python": sys.version.split()[0],
                "hostname": platform.node(),
            },
        )

    def get_ollama_status(self):
        """Inspect local Ollama installation, daemon, and model availability."""
        from app.ai.ollama_client import ollama_client
        return ollama_client.get_status()

    def interpret_task(self, prompt: str):
        """Interpret natural language prompt without executing."""
        from app.ai.interpreter import command_interpreter
        return command_interpreter.interpret(prompt)

    def execute_task(self, request):
        """Orchestrate natural language task interpretation, validation, and execution."""
        from app.ai.orchestrator import task_orchestrator
        return task_orchestrator.execute_task(request)

    async def execute_task_stream(self, request):
        """Stream real-time events for an orchestrated natural language task."""
        from app.ai.orchestrator import task_orchestrator
        async for event in task_orchestrator.execute_task_stream(request):
            yield event




# Global service singleton
agent_service = AgentService()
