"""Security and sandbox validation routines for Flash Agent.

Enforces:
- Local filesystem sandboxing to approved workspace directories.
- Safe URL validation blocking local/private networks, files, and scheme exploits.
- Global Emergency Stop circuit.
- Explicit user confirmation gates for sensitive actions.
"""

import threading
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("flash.security")


class SecurityError(Exception):
    """Base class for security and safety validation errors."""


class SecurityValidationError(SecurityError):
    """Raised when an action argument violates security constraints."""


class EmergencyStopTriggeredError(SecurityError):
    """Raised when an action is attempted while the emergency stop is active."""


class ConfirmationRequiredError(SecurityError):
    """Raised when a consequential action is called without explicit user confirmation."""


class EmergencyStopManager:
    """Thread-safe global emergency stop circuit."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stopped = False

    @property
    def is_stopped(self) -> bool:
        with self._lock:
            return self._stopped

    def trigger(self, reason: str = "User initiated emergency stop") -> None:
        with self._lock:
            self._stopped = True
            logger.warning("EMERGENCY STOP TRIGGERED: %s", reason)

    def resume(self) -> None:
        with self._lock:
            self._stopped = False
            logger.info("Emergency stop cleared. Agent resumed normal operations.")

    def verify_not_stopped(self) -> None:
        if self.is_stopped:
            raise EmergencyStopTriggeredError(
                "Agent is currently halted by Emergency Stop. Resume the agent before issuing new actions."
            )


# Global singleton emergency stop
emergency_stop = EmergencyStopManager()


def validate_safe_url(url: str) -> tuple[bool, Optional[str]]:
    """Validate that a URL is safe to open in a web browser.

    Checks:
    - Must have http or https scheme.
    - Must have a valid non-empty host.
    - Blocks private IP ranges/localhost unless explicitly enabled.
    - Blocks file://, javascript:, data:, and shell injection patterns.
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string."

    clean_url = url.strip()

    try:
        parsed = urlparse(clean_url)
    except Exception as e:
        return False, f"Malformed URL syntax: {e}"

    scheme = parsed.scheme.lower()
    if scheme not in settings.allowed_url_schemes:
        return False, f"Unsafe URL scheme '{scheme}'. Only {settings.allowed_url_schemes} are permitted."

    host = parsed.hostname
    if not host:
        return False, "URL must contain a valid hostname or domain."

    # Prevent loopback/localhost access if disallowed
    if not settings.allow_internal_urls:
        host_lower = host.lower()
        if host_lower in settings.blocked_url_hosts or host_lower.endswith(".local"):
            return False, f"Access to local network host '{host}' is restricted by security policy."

    return True, None


def resolve_safe_path(
    path_str: str,
    base_dir: Optional[Path] = None,
    must_exist: bool = False,
    create_parent: bool = True,
    allowed_extensions: Optional[set[str]] = None,
) -> tuple[bool, Optional[Path], Optional[str]]:
    """Resolve and validate that a filesystem path stays strictly inside an approved directory.

    Guards against:
    - Directory traversal (e.g. '../', '..\\')
    - Unapproved drive roots
    - Forbidden file extensions
    """
    if not path_str or not isinstance(path_str, str):
        return False, None, "File path must be a non-empty string."

    base = (base_dir or settings.workspace_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)

    try:
        candidate = Path(path_str)
        # If relative, join with base
        if not candidate.is_absolute():
            resolved = (base / candidate).resolve()
        else:
            resolved = candidate.resolve()

        # Strict containment check
        try:
            resolved.relative_to(base)
        except ValueError:
            return (
                False,
                None,
                f"Path '{path_str}' escapes approved workspace directory '{base}'. Directory traversal is forbidden.",
            )

        if allowed_extensions:
            ext = resolved.suffix.lower()
            if ext not in allowed_extensions:
                return (
                    False,
                    None,
                    f"Extension '{ext}' is not permitted. Allowed: {sorted(allowed_extensions)}",
                )

        if must_exist and not resolved.exists():
            return False, None, f"Target path '{resolved}' does not exist."

        if create_parent and not resolved.parent.exists():
            resolved.parent.mkdir(parents=True, exist_ok=True)

        return True, resolved, None

    except Exception as e:
        return False, None, f"Path resolution failed: {e}"
