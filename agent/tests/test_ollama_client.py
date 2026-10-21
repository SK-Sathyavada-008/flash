"""Tests for Ollama client: health check, model detection, timeouts, and error handling."""

import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.ai.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    OllamaMalformedResponseError,
)


def test_ollama_status_reporting():
    """Verify status inspection when Ollama is running."""
    client = OllamaClient()
    status = client.get_status()
    # On this workstation, Ollama is running and has gemma2:latest installed
    assert status.configured_model == client.model
    if status.is_running:
        assert isinstance(status.available_models, list)
        assert len(status.available_models) > 0


def test_ollama_status_not_running():
    """Verify clear error guidance when Ollama daemon is unreachable."""
    client = OllamaClient(base_url="http://127.0.0.1:19999")  # Unused port
    status = client.get_status()
    assert status.is_running is False
    assert status.setup_instructions is not None
    assert "ollama serve" in status.setup_instructions.lower() or "download" in status.setup_instructions.lower()


def test_ollama_client_timeout():
    """Verify OllamaTimeoutError when request exceeds timeout."""
    client = OllamaClient()

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(OllamaTimeoutError) as exc_info:
            client.chat_json([{"role": "user", "content": "hi"}], custom_timeout=0.01)
        assert "timed out" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "OLLAMA_TIMEOUT"


def test_ollama_client_connection_error():
    """Verify OllamaConnectionError when server rejects connection."""
    client = OllamaClient()

    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(OllamaConnectionError) as exc_info:
            client.chat_json([{"role": "user", "content": "hi"}])
        assert "Cannot connect to Ollama" in str(exc_info.value)
        assert exc_info.value.error_code == "OLLAMA_NOT_RUNNING"


def test_ollama_client_malformed_json():
    """Verify OllamaMalformedResponseError when model returns invalid JSON."""
    client = OllamaClient()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": "This is plain text, not JSON at all!"}
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(OllamaMalformedResponseError) as exc_info:
            client.chat_json([{"role": "user", "content": "hi"}])
        assert "invalid or malformed json" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "MALFORMED_MODEL_RESPONSE"


def test_ollama_client_missing_model_404():
    """Verify OllamaModelNotFoundError when Ollama returns HTTP 404 for model."""
    client = OllamaClient(model="nonexistent-model:99b")

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "model not found"

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(OllamaModelNotFoundError) as exc_info:
            client.chat_json([{"role": "user", "content": "hi"}])
        assert "nonexistent-model:99b" in str(exc_info.value)
        assert exc_info.value.error_code == "MODEL_NOT_FOUND"
