"""Integration tests for AI endpoints: /api/v1/ai/status, interpret, and execute."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    ActionPlanItem,
    InterpretationPlan,
    OllamaStatusResponse,
    TaskExecutionResponse,
    TaskStepResult,
    ActionResponse,
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_endpoint_ai_status(client):
    """Verify /api/v1/ai/status returns structured status."""
    res = client.get("/api/v1/ai/status")
    assert res.status_code == 200
    data = res.json()
    assert "is_installed" in data
    assert "is_running" in data
    assert "configured_model" in data
    assert "available_models" in data


def test_endpoint_ai_interpret_success(client):
    """Verify /api/v1/ai/interpret translates natural language to an execution plan."""
    mock_plan = InterpretationPlan(
        intent="Create a grocery list",
        user_facing_explanation="Grocery list ready.",
        needs_confirmation=False,
        actions=[
            ActionPlanItem(
                action_name="create_grocery_list",
                parameters={"filename": "lists/groceries.md", "items": ["Milk", "Bread"]},
                requires_confirmation=False,
                explanation="Create grocery checklist",
            )
        ],
    )

    with patch("app.service.agent_service.interpret_task", return_value=mock_plan):
        res = client.post("/api/v1/ai/interpret", json={"prompt": "Make a grocery list with milk and bread"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "Create a grocery list"
        assert len(data["actions"]) == 1
        assert data["actions"][0]["action_name"] == "create_grocery_list"


def test_endpoint_ai_interpret_error(client):
    """Verify /api/v1/ai/interpret returns HTTP 400 when interpreter throws."""
    from app.ai.interpreter import CommandInterpretationError

    with patch("app.service.agent_service.interpret_task", side_effect=CommandInterpretationError("Model failed", "TEST_ERROR")):
        res = client.post("/api/v1/ai/interpret", json={"prompt": "Do something strange"})
        assert res.status_code == 400
        assert "TEST_ERROR" in res.json()["detail"]


def test_endpoint_ai_execute(client):
    """Verify /api/v1/ai/execute processes task end-to-end."""
    mock_resp = TaskExecutionResponse(
        task_id="abc12345",
        prompt="Open Python website",
        intent="Open website",
        status="completed",
        success=True,
        explanation="Opened python website.",
        steps=[
            TaskStepResult(
                step_index=1,
                action_name="open_url",
                explanation="Open URL",
                success=True,
                result=ActionResponse(
                    success=True,
                    action="open_url",
                    message="Opened https://www.python.org",
                    output_path="https://www.python.org",
                ),
            )
        ],
    )

    with patch("app.service.agent_service.execute_task", return_value=mock_resp):
        res = client.post("/api/v1/ai/execute", json={"prompt": "Open Python website", "confirmed": False})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert data["success"] is True
        assert len(data["steps"]) == 1
