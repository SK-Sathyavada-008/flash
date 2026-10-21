"""Ollama HTTP Client for Flash Agent.

Handles local inference against Ollama server, health checks, model detection,
structured completion, and error classification.
"""

import json
import shutil
from typing import Any, Optional
import httpx

from app.config import settings, mask_sensitive_data
from app.logging_config import get_logger
from app.models import OllamaStatusResponse

logger = get_logger("flash.ai.ollama")


class OllamaError(Exception):
    """Base exception for Ollama interactions."""
    def __init__(self, message: str, error_code: str = "OLLAMA_ERROR"):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class OllamaNotInstalledError(OllamaError):
    """Ollama binary is not installed on this system."""
    def __init__(self, message: str = "Ollama is not installed on this system."):
        super().__init__(message, error_code="OLLAMA_NOT_INSTALLED")


class OllamaConnectionError(OllamaError):
    """Cannot connect to Ollama daemon (server is down)."""
    def __init__(self, message: str = "Cannot connect to Ollama server."):
        super().__init__(message, error_code="OLLAMA_NOT_RUNNING")


class OllamaModelNotFoundError(OllamaError):
    """Requested model is not downloaded in Ollama."""
    def __init__(self, model_name: str):
        super().__init__(
            f"Configured model '{model_name}' is not downloaded in Ollama. Run: 'ollama pull {model_name}'",
            error_code="MODEL_NOT_FOUND",
        )
        self.model_name = model_name


class OllamaTimeoutError(OllamaError):
    """Inference request exceeded timeout."""
    def __init__(self, timeout_seconds: float):
        super().__init__(
            f"Ollama inference timed out after {timeout_seconds:.1f}s. Try increasing FLASH_OLLAMA_TIMEOUT_SECONDS.",
            error_code="OLLAMA_TIMEOUT",
        )


class OllamaMalformedResponseError(OllamaError):
    """Model output could not be parsed as valid JSON."""
    def __init__(self, raw_content: str):
        super().__init__(
            f"Model returned invalid or malformed JSON: {raw_content[:200]}...",
            error_code="MALFORMED_MODEL_RESPONSE",
        )
        self.raw_content = raw_content


class OllamaClient:
    """Client for communicating with the local Ollama API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout if timeout is not None else settings.ollama_timeout_seconds
        self._last_verified: float = 0.0
        self._verification_ttl: float = 60.0

    def is_binary_installed(self) -> bool:
        """Check whether the ollama executable is located in PATH."""
        return shutil.which("ollama") is not None

    def get_status(self) -> OllamaStatusResponse:
        """Inspect Ollama installation, running daemon, and local model library."""
        is_installed = self.is_binary_installed()
        is_running = False
        available_models: list[str] = []
        is_model_available = False
        setup_instructions = None

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    is_running = True
                    data = res.json()
                    models_data = data.get("models", [])
                    available_models = [m.get("name", "") for m in models_data if "name" in m]
                    
                    # Normalize check: 'gemma2:latest' matches 'gemma2:latest' or 'gemma2'
                    model_target = self.model
                    prefix = model_target.split(":")[0]
                    is_model_available = (
                        model_target in available_models
                        or any(m.startswith(f"{prefix}:") or m == prefix for m in available_models)
                    )
        except Exception:
            is_running = False

        if not is_installed:
            setup_instructions = (
                "1. Download Ollama for Windows from https://ollama.com/download\n"
                "2. Install and launch Ollama\n"
                f"3. In PowerShell, pull the model: ollama pull {self.model}"
            )
        elif not is_running:
            setup_instructions = (
                "Ollama is installed but the server is not running.\n"
                "Start it by opening the Ollama application from the Start Menu, or run:\n"
                "ollama serve"
            )
        elif not is_model_available:
            setup_instructions = (
                f"Ollama is running, but model '{self.model}' is missing.\n"
                f"Download it in PowerShell: ollama pull {self.model}"
            )

        return OllamaStatusResponse(
            is_installed=is_installed,
            is_running=is_running,
            configured_model=self.model,
            is_model_available=is_model_available,
            available_models=available_models,
            setup_instructions=setup_instructions,
        )

    def verify_ready(self, force: bool = False) -> None:
        """Assert that Ollama is running and the model is available."""
        import time
        now = time.time()
        if not force and (now - self._last_verified < self._verification_ttl):
            return

        status = self.get_status()
        if not status.is_running:
            raise OllamaConnectionError(
                f"Ollama daemon not reachable at {self.base_url}. {status.setup_instructions or 'Start Ollama.'}"
            )
        if not status.is_model_available:
            raise OllamaModelNotFoundError(self.model)
        self._last_verified = now

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        custom_timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """Send a chat completion request expecting a structured JSON response."""
        import os
        timeout_val = custom_timeout if custom_timeout is not None else self.timeout
        temp = temperature if temperature is not None else settings.ollama_temperature
        num_predict = getattr(settings, "ollama_num_predict", 180)
        num_threads = max(1, (os.cpu_count() or 4) - 1)

        payload = {
            "model": self.model,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": num_predict,
                "num_thread": num_threads,
                "top_k": 20,
                "top_p": 0.9,
            },
        }

        logger.debug(
            "Calling Ollama chat API at %s/api/chat with model=%s, timeout=%.1fs",
            self.base_url,
            self.model,
            timeout_val,
        )

        try:
            with httpx.Client(timeout=timeout_val) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.ConnectError as e:
            logger.error("Connection failed to Ollama at %s: %s", self.base_url, e)
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. Ensure 'ollama serve' is active."
            ) from e
        except httpx.TimeoutException as e:
            logger.error("Ollama request timed out after %.1fs", timeout_val)
            raise OllamaTimeoutError(timeout_val) from e
        except Exception as e:
            logger.error("Unexpected error contacting Ollama: %s", e)
            raise OllamaError(f"Ollama communication failure: {e}") from e

        if response.status_code == 404:
            raise OllamaModelNotFoundError(self.model)
        elif response.status_code != 200:
            raise OllamaError(
                f"Ollama returned HTTP {response.status_code}: {response.text}",
                error_code="OLLAMA_HTTP_ERROR",
            )

        try:
            res_json = response.json()
            message_obj = res_json.get("message", {})
            content = message_obj.get("content", "")
            if not content.strip():
                raise OllamaMalformedResponseError("Empty response body from model.")

            # Parse JSON from model output
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise OllamaMalformedResponseError("Model returned JSON that is not an object/dict.")
            return parsed
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from model output: %s", e)
            raise OllamaMalformedResponseError(content) from e


# Global default Ollama client singleton
ollama_client = OllamaClient()
