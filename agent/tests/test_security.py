"""Tests for security validation, sandboxing, and emergency stop."""

from pathlib import Path
from fastapi.testclient import TestClient
from app.config import settings
from app.security import (
    emergency_stop,
    resolve_safe_path,
    validate_safe_url,
)


def test_url_validation_safe() -> None:
    """Verify safe public URLs are accepted."""
    safe_urls = [
        "https://example.com",
        "http://python.org/doc",
        "https://www.google.com/search?q=sloth",
    ]
    for url in safe_urls:
        valid, err = validate_safe_url(url)
        assert valid is True, f"Expected {url} to be valid, got: {err}"


def test_url_validation_blocks_unsafe() -> None:
    """Verify dangerous schemes and addresses are rejected."""
    unsafe_urls = [
        "file:///C:/Windows/System32",
        "javascript:alert(1)",
        "data:text/html,<html>",
        "ftp://example.com/file",
        "http://localhost:8000/secret",
        "http://127.0.0.1:9000",
        "",
        "not a url",
    ]
    for url in unsafe_urls:
        valid, err = validate_safe_url(url)
        assert valid is False, f"Expected {url} to be rejected, but it was accepted."


def test_path_sandboxing_enforced() -> None:
    """Verify directory traversal escapes are caught and blocked."""
    escapes = [
        "../../Windows/System32/cmd.exe",
        "../outside.txt",
        "..\\..\\sensitive.txt",
    ]
    for path in escapes:
        valid, resolved, err = resolve_safe_path(path)
        assert valid is False, f"Path traversal '{path}' was not blocked."
        assert "escapes approved workspace" in err.lower()


def test_path_sandboxing_valid_relative() -> None:
    """Verify safe relative paths resolve inside workspace."""
    valid, resolved, err = resolve_safe_path("documents/sub/test.txt")
    assert valid is True
    assert resolved is not None
    assert resolved.is_relative_to(settings.workspace_dir.resolve())


def test_emergency_stop_circuit(client: TestClient) -> None:
    """Verify emergency stop blocks execution and resume restores it."""
    # 1. Trigger emergency stop
    stop_resp = client.post("/api/v1/stop")
    assert stop_resp.status_code == 200
    assert emergency_stop.is_stopped is True

    # 2. Status should reflect stopped
    status_resp = client.get("/api/v1/status")
    assert status_resp.json()["status"] == "stopped"
    assert status_resp.json()["emergency_stop_active"] is True

    # 3. Attempting an action must be blocked
    action_resp = client.post(
        "/api/v1/actions/execute",
        json={"action": "create_text_file", "parameters": {"filename": "test.txt", "content": "blocked"}},
    )
    assert action_resp.status_code == 200
    result = action_resp.json()
    assert result["success"] is False
    assert result["error"] == "EMERGENCY_STOP_ACTIVE"

    # 4. Resume emergency stop
    resume_resp = client.post("/api/v1/resume")
    assert resume_resp.status_code == 200
    assert emergency_stop.is_stopped is False

    # 5. Action should now succeed
    action_resp2 = client.post(
        "/api/v1/actions/execute",
        json={"action": "create_text_file", "parameters": {"filename": "test.txt", "content": "allowed"}},
    )
    assert action_resp2.status_code == 200
    assert action_resp2.json()["success"] is True
