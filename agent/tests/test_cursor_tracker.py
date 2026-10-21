"""Tests for cursor gaze tracking and normalization."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.testclient import TestClient

from app.auth import token_manager
from app.cursor_tracker import CursorTracker
from app.main import app


@pytest.fixture
def mock_tracker():
    """Create isolated cursor tracker with mock screen querying."""
    tracker = CursorTracker(sample_interval=0.01, move_threshold=0.01)
    tracker._get_raw_pos_and_dims = MagicMock(return_value=(960, 540, 1920, 1080))
    return tracker


def test_cursor_normalization_exact_center(mock_tracker):
    """Test cursor coordinate normalization to 0.0 - 1.0 range."""
    raw_x, raw_y, screen_w, screen_h = mock_tracker._get_raw_pos_and_dims()
    norm_x = raw_x / screen_w
    norm_y = raw_y / screen_h
    assert norm_x == 0.5
    assert norm_y == 0.5


def test_cursor_clamp_out_of_bounds(mock_tracker):
    """Test coordinates outside screen bounds are safely clamped between 0 and 1."""
    mock_tracker._get_raw_pos_and_dims = MagicMock(return_value=(-50, 2500, 1920, 1080))
    raw_x, raw_y, screen_w, screen_h = mock_tracker._get_raw_pos_and_dims()
    norm_x = max(0.0, min(1.0, raw_x / screen_w))
    norm_y = max(0.0, min(1.0, raw_y / screen_h))
    assert norm_x == 0.0
    assert norm_y == 1.0


def test_client_registration_and_disable():
    """Test adding, disabling, and removing clients."""
    tracker = CursorTracker()
    ws1 = MagicMock()
    ws2 = MagicMock()

    tracker.add_client(ws1)
    tracker.add_client(ws2)
    assert len(tracker._active_sockets) == 2

    # Disable gaze on ws1
    tracker.set_client_gaze_enabled(ws1, False)
    assert ws1 in tracker._disabled_sockets

    # Eligible list should only include ws2
    eligible = [ws for ws in tracker._active_sockets if ws not in tracker._disabled_sockets]
    assert eligible == [ws2]

    # Re-enable ws1
    tracker.set_client_gaze_enabled(ws1, True)
    assert ws1 not in tracker._disabled_sockets

    # Remove ws2
    tracker.remove_client(ws2)
    assert ws2 not in tracker._active_sockets


def test_websocket_set_gaze_enabled_toggle():
    """Test enabling and disabling cursor gaze via WebSocket messages."""
    token = token_manager.issue_token("Test Gaze Phone")
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/v1/companion?token={token}") as ws:
            ws.receive_json()  # connection_established

            # Send toggle off
            ws.send_json({"type": "set_gaze_enabled", "enabled": False})
            res_off = ws.receive_json()
            assert res_off["type"] == "gaze_status"
            assert res_off["enabled"] is False

            # Send toggle on
            ws.send_json({"type": "set_gaze_enabled", "enabled": True})
            res_on = ws.receive_json()
            assert res_on["type"] == "gaze_status"
            assert res_on["enabled"] is True
