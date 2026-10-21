"""Pytest test configuration and fixtures for Flash Agent."""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure app is in python path
current_dir = Path(__file__).resolve().parent
agent_dir = current_dir.parent
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

from app.config import settings
from app.main import app
from app.security import emergency_stop
from app.service import agent_service


@pytest.fixture(autouse=True)
def reset_state(tmp_path: Path):
    """Ensure clean isolated workspace and emergency stop state for every test."""
    # Point workspace to isolated pytest temporary directory
    original_workspace = settings.workspace_dir
    settings.workspace_dir = tmp_path / "Flash Workspace"
    settings.ensure_directories()

    # Ensure agent service is initialized
    agent_service.startup()

    # Reset emergency stop
    emergency_stop.resume()

    yield

    # Teardown
    emergency_stop.resume()
    settings.workspace_dir = original_workspace


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    with TestClient(app) as test_client:
        yield test_client
