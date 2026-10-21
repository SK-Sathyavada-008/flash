"""Tests for agent service orchestration, confirmation gates, and error handling."""

from fastapi.testclient import TestClient
from app.actions.base import BaseAction
from app.actions.registry import registry
from app.models import ActionResponse


class MockConsequentialAction(BaseAction):
    name = "delete_database"
    description = "A dangerous test action requiring explicit user confirmation."
    requires_confirmation = True
    parameters_schema = {}

    def run(self, parameters: dict, confirmed: bool = False) -> ActionResponse:
        return ActionResponse(
            success=True,
            action=self.name,
            message="Confirmed operation succeeded.",
        )


def test_unknown_action_returns_404(client: TestClient) -> None:
    """Invoking an unregistered action name returns 404 with helpful error."""
    resp = client.post(
        "/api/v1/actions/execute",
        json={"action": "non_existent_action", "parameters": {}},
    )
    assert resp.status_code == 404
    assert "Unknown action" in resp.json()["detail"]


def test_confirmation_gate(client: TestClient) -> None:
    """Action tagged with requires_confirmation=True fails without confirmed=True."""
    registry.register(MockConsequentialAction())

    # 1. Unconfirmed attempt
    resp_unconfirmed = client.post(
        "/api/v1/actions/execute",
        json={"action": "delete_database", "parameters": {}, "confirmed": False},
    )
    assert resp_unconfirmed.status_code == 200
    data = resp_unconfirmed.json()
    assert data["success"] is False
    assert data["error"] == "CONFIRMATION_REQUIRED"

    # 2. Confirmed attempt
    resp_confirmed = client.post(
        "/api/v1/actions/execute",
        json={"action": "delete_database", "parameters": {}, "confirmed": True},
    )
    assert resp_confirmed.status_code == 200
    assert resp_confirmed.json()["success"] is True
