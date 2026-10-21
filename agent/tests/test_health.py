"""Tests for health check, root, and basic service endpoints."""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    """Verify /health returns 200 OK and valid health payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Flash" in data["app"]
    assert "version" in data
    assert "timestamp" in data


def test_root_endpoint(client: TestClient) -> None:
    """Verify root / endpoint returns welcome information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Flash" in data["character"]
    assert data["docs_url"] == "/docs"


def test_list_actions_endpoint(client: TestClient) -> None:
    """Verify /api/v1/actions lists all 7 required actions."""
    response = client.get("/api/v1/actions")
    assert response.status_code == 200
    actions = response.json()
    action_names = {a["name"] for a in actions}

    expected_actions = {
        "open_url",
        "type_text",
        "create_text_file",
        "create_grocery_list",
        "create_spreadsheet",
        "open_file",
        "get_agent_status",
    }
    assert expected_actions.issubset(action_names)
