"""Tests for Task Orchestrator: single/multi-step flow, error policies, confirmation, and sandbox safety."""

import pytest
from unittest.mock import MagicMock

from app.actions.registry import register_default_actions
from app.ai.interpreter import CommandInterpreter
from app.ai.ollama_client import OllamaTimeoutError
from app.ai.orchestrator import TaskOrchestrator
from app.models import (
    ActionPlanItem,
    InterpretationPlan,
    UserTaskRequest,
)
from app.security import emergency_stop


@pytest.fixture(autouse=True)
def setup_actions():
    """Ensure standard actions and clear emergency stop."""
    register_default_actions()
    emergency_stop.resume()
    yield
    emergency_stop.resume()


def test_orchestrator_valid_single_step():
    """Verify single-step task executes successfully and returns structured output."""
    mock_interpreter = MagicMock(spec=CommandInterpreter)
    mock_interpreter.interpret.return_value = InterpretationPlan(
        intent="Create a grocery checklist",
        user_facing_explanation="Grocery list ready.",
        needs_confirmation=False,
        actions=[
            ActionPlanItem(
                action_name="create_grocery_list",
                parameters={
                    "filename": "lists/orch_groceries.md",
                    "title": "Orchestrator Test List",
                    "items": ["Apples", "Bananas"],
                },
                requires_confirmation=False,
                explanation="Create grocery checklist",
            )
        ],
    )

    orchestrator = TaskOrchestrator(interpreter=mock_interpreter)
    req = UserTaskRequest(prompt="Make a grocery list with apples and bananas", confirmed=False)
    resp = orchestrator.execute_task(req)

    assert resp.success is True
    assert resp.status == "completed"
    assert len(resp.steps) == 1
    assert resp.steps[0].action_name == "create_grocery_list"
    assert resp.steps[0].result.success is True


def test_orchestrator_valid_multi_step():
    """Verify multi-step task executes sequential actions in order."""
    mock_interpreter = MagicMock(spec=CommandInterpreter)
    mock_interpreter.interpret.return_value = InterpretationPlan(
        intent="Create note then open it",
        user_facing_explanation="Note created and opened.",
        needs_confirmation=False,
        actions=[
            ActionPlanItem(
                action_name="create_text_file",
                parameters={
                    "filename": "documents/multi_step_note.txt",
                    "content": "Step 1 complete.",
                    "overwrite": True,
                },
                requires_confirmation=False,
                explanation="Create text file",
            ),
            ActionPlanItem(
                action_name="get_agent_status",
                parameters={},
                requires_confirmation=False,
                explanation="Query status",
            ),
        ],
    )

    orchestrator = TaskOrchestrator(interpreter=mock_interpreter)
    req = UserTaskRequest(prompt="Create a note and check status", confirmed=False)
    resp = orchestrator.execute_task(req)

    assert resp.success is True
    assert resp.status == "completed"
    assert len(resp.steps) == 2
    assert resp.steps[0].action_name == "create_text_file"
    assert resp.steps[1].action_name == "get_agent_status"
    assert resp.steps[0].result.success is True
    assert resp.steps[1].result.success is True


def test_orchestrator_denied_action_confirmation():
    """Verify that unconfirmed tasks requiring confirmation pause with awaiting_confirmation."""
    mock_interpreter = MagicMock(spec=CommandInterpreter)
    mock_interpreter.interpret.return_value = InterpretationPlan(
        intent="Destructive operation",
        user_facing_explanation="Delete or overwrite important records.",
        needs_confirmation=True,
        actions=[
            ActionPlanItem(
                action_name="create_text_file",
                parameters={"filename": "documents/important.txt", "content": "Overwriting"},
                requires_confirmation=True,
                explanation="Overwrite sensitive document",
            )
        ],
    )

    orchestrator = TaskOrchestrator(interpreter=mock_interpreter)
    req = UserTaskRequest(prompt="Overwrite important document", confirmed=False)
    resp = orchestrator.execute_task(req)

    assert resp.success is False
    assert resp.status == "awaiting_confirmation"
    assert resp.error == "CONFIRMATION_REQUIRED"
    assert len(resp.steps) == 0  # No action should have been run!


def test_orchestrator_emergency_stop_denial():
    """Verify emergency stop denies task execution immediately."""
    emergency_stop.trigger("Test stop initiated")

    mock_interpreter = MagicMock(spec=CommandInterpreter)
    orchestrator = TaskOrchestrator(interpreter=mock_interpreter)

    req = UserTaskRequest(prompt="Open YouTube", confirmed=True)
    resp = orchestrator.execute_task(req)

    assert resp.success is False
    assert resp.status == "halted"
    assert resp.error == "EMERGENCY_STOP_ACTIVE"
    # Interpreter should not even be called when stopped
    mock_interpreter.interpret.assert_not_called()


def test_orchestrator_invalid_path_sandbox_failure():
    """Verify path traversal attempts inside task parameters are blocked."""
    mock_interpreter = MagicMock(spec=CommandInterpreter)
    mock_interpreter.interpret.return_value = InterpretationPlan(
        intent="Malicious traversal",
        user_facing_explanation="Attempting to write outside workspace.",
        needs_confirmation=False,
        actions=[
            ActionPlanItem(
                action_name="create_text_file",
                parameters={
                    "filename": "../../../Windows/System32/evil.txt",
                    "content": "hacked",
                    "overwrite": True,
                },
                requires_confirmation=False,
                explanation="Malicious write attempt",
            )
        ],
    )

    orchestrator = TaskOrchestrator(interpreter=mock_interpreter)
    req = UserTaskRequest(prompt="Write to system directory", confirmed=True)
    resp = orchestrator.execute_task(req)

    assert resp.success is False
    assert resp.status == "failed"
    assert len(resp.steps) == 1
    assert resp.steps[0].result.success is False
    assert resp.steps[0].result.error == "PATH_ACCESS_DENIED"


def test_orchestrator_multi_step_stop_on_error():
    """Verify multi-step policy 'stop_on_error' stops sequence when a step fails."""
    mock_interpreter = MagicMock(spec=CommandInterpreter)
    mock_interpreter.interpret.return_value = InterpretationPlan(
        intent="Fail step 1 then step 2",
        user_facing_explanation="First step will fail.",
        needs_confirmation=False,
        actions=[
            ActionPlanItem(
                action_name="open_file",
                parameters={"filepath": "documents/nonexistent_file_9999.txt"},
                requires_confirmation=False,
                explanation="Try to open non-existent file",
            ),
            ActionPlanItem(
                action_name="get_agent_status",
                parameters={},
                requires_confirmation=False,
                explanation="This step should never execute",
            ),
        ],
    )

    orchestrator = TaskOrchestrator(interpreter=mock_interpreter)
    req = UserTaskRequest(prompt="Open missing file and check status", confirmed=False)
    resp = orchestrator.execute_task(req)

    assert resp.success is False
    assert resp.status == "failed"
    # Step 1 ran and failed
    assert len(resp.steps) == 1
    assert resp.steps[0].action_name == "open_file"
    assert resp.steps[0].result.success is False
    assert resp.steps[0].result.error == "PATH_ACCESS_DENIED"



def test_orchestrator_timeout_handling():
    """Verify orchestrator returns clear error when model inference times out."""
    mock_interpreter = MagicMock(spec=CommandInterpreter)
    mock_interpreter.interpret.side_effect = OllamaTimeoutError(45.0)

    orchestrator = TaskOrchestrator(interpreter=mock_interpreter)
    req = UserTaskRequest(prompt="Research quantum computing", confirmed=False)
    resp = orchestrator.execute_task(req)

    assert resp.success is False
    assert resp.status == "failed"
    assert resp.error == "OLLAMA_TIMEOUT"
    assert "timed out" in resp.explanation.lower()
