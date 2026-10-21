"""Automated tests for authenticated companion WebSocket protocol.
Tests connection establishment, authentication enforcement, ping/pong heartbeats,
task streaming, emergency stop controls, malformed message handling, and reconnection.
"""

from unittest.mock import MagicMock, patch
import pytest
from starlette.testclient import TestClient

from app.auth import token_manager
from app.main import app
from app.models import ActionPlanItem, InterpretationPlan


@pytest.fixture
def auth_token():
    """Generate a clean authorized token for companion testing."""
    return token_manager.issue_token("Test Redmi Phone")


def test_websocket_unauthorized_rejected():
    """Test that connecting without a valid token from a remote client is rejected."""
    remote_client = TestClient(app, client=("192.168.1.150", 43210))
    # Remote client without token
    with remote_client.websocket_connect("/ws/v1/companion") as ws:
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "UNAUTHORIZED"

    # Remote client with invalid token
    with remote_client.websocket_connect("/ws/v1/companion?token=bogus_token") as ws:
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "UNAUTHORIZED"


def test_websocket_connection_and_heartbeat(auth_token):
    """Test authorized connection and ping-pong heartbeat exchange."""
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/v1/companion?token={auth_token}") as ws:
            # 1. Verify initial greeting
            init_msg = ws.receive_json()
            assert init_msg["type"] == "connection_established"
            assert init_msg["agent_name"] == "Flash"

            # 2. Ping-pong heartbeat
            ws.send_json({"type": "ping", "timestamp": 123456789.0})
            pong = ws.receive_json()
            assert pong["type"] == "pong"
            assert pong["client_timestamp"] == 123456789.0
            assert "server_timestamp" in pong


def test_websocket_status_and_emergency_controls(auth_token):
    """Test querying status, triggering emergency stop, and resuming over WebSocket."""
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/v1/companion?token={auth_token}") as ws:
            ws.receive_json()  # Consume connection_established

            # 1. Get status
            ws.send_json({"type": "get_status"})
            status_msg = ws.receive_json()
            assert status_msg["type"] == "status_update"
            assert status_msg["status"] in ("ready", "stopped")

            # 2. Trigger stop
            ws.send_json({"type": "stop"})
            stop_msg = ws.receive_json()
            assert stop_msg["type"] == "stopped"
            assert stop_msg["status"] == "stopped"

            # 3. Resume
            ws.send_json({"type": "resume"})
            resume_msg = ws.receive_json()
            assert resume_msg["type"] == "resumed"
            assert resume_msg["status"] == "ready"


def test_websocket_task_execution_streaming(auth_token):
    """Test real-time streamed execution events for a natural language task."""
    mock_plan = InterpretationPlan(
        intent="Check agent system status",
        user_facing_explanation="Checking system diagnostics for you.",
        actions=[
            ActionPlanItem(
                action_name="get_agent_status",
                parameters={},
                explanation="Inspecting runtime environment",
            )
        ],
        needs_confirmation=False,
    )

    with patch("app.ai.interpreter.command_interpreter.interpret", return_value=mock_plan):
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/v1/companion?token={auth_token}") as ws:
                ws.receive_json()  # connection_established

                # Send command to execute
                ws.send_json({
                    "type": "execute_task",
                    "prompt": "Flash, report your status",
                })

                # Receive stream sequence:
                # 1. task_started
                msg1 = ws.receive_json()
                assert msg1["type"] == "task_started"
                assert msg1["prompt"] == "Flash, report your status"

                # 2. task_thinking
                msg2 = ws.receive_json()
                assert msg2["type"] == "task_thinking"

                # 3. task_planned
                msg3 = ws.receive_json()
                assert msg3["type"] == "task_planned"
                assert msg3["total_steps"] == 1

                # 4. task_step_progress
                msg4 = ws.receive_json()
                assert msg4["type"] == "task_step_progress"
                assert msg4["action"] == "get_agent_status"

                # 5. task_step_completed
                msg5 = ws.receive_json()
                assert msg5["type"] == "task_step_completed"
                assert msg5["success"] is True

                # 6. task_finished
                msg6 = ws.receive_json()
                assert msg6["type"] == "task_finished"
                assert msg6["success"] is True
                assert msg6["status"] == "completed"
                assert len(msg6["steps"]) == 1


def test_websocket_malformed_messages_handling(auth_token):
    """Test agent resilience against malformed JSON, missing types, and invalid requests."""
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/v1/companion?token={auth_token}") as ws:
            ws.receive_json()  # connection_established

            # 1. Invalid JSON string
            ws.send_text("this is definitely not valid json {{{")
            err1 = ws.receive_json()
            assert err1["type"] == "error"
            assert err1["code"] == "MALFORMED_JSON"

            # 2. Missing 'type' field
            ws.send_json({"some_random_key": "some_value"})
            err2 = ws.receive_json()
            assert err2["type"] == "error"
            assert err2["code"] == "MISSING_MESSAGE_TYPE"

            # 3. Unsupported message type
            ws.send_json({"type": "unknown_action_xyz"})
            err3 = ws.receive_json()
            assert err3["type"] == "error"
            assert err3["code"] == "UNSUPPORTED_MESSAGE_TYPE"

            # 4. execute_task without prompt
            ws.send_json({"type": "execute_task", "prompt": "   "})
            err4 = ws.receive_json()
            assert err4["type"] == "error"
            assert err4["code"] == "MISSING_PROMPT"


def test_websocket_reconnection_flow(auth_token):
    """Test disconnecting and reconnecting using the same token."""
    with TestClient(app) as client:
        # First session
        with client.websocket_connect(f"/ws/v1/companion?token={auth_token}") as ws1:
            init1 = ws1.receive_json()
            assert init1["type"] == "connection_established"
            ws1.send_json({"type": "ping"})
            assert ws1.receive_json()["type"] == "pong"
        # Connection closed after context manager exits

        # Reconnect with same valid token
        with client.websocket_connect(f"/ws/v1/companion?token={auth_token}") as ws2:
            init2 = ws2.receive_json()
            assert init2["type"] == "connection_established"
            ws2.send_json({"type": "ping"})
            assert ws2.receive_json()["type"] == "pong"
