"""Sentry Telemetry and Error Tracing for Flash Sloth Agent.

Features:
- Configures Sentry SDK when SENTRY_DSN is set.
- Privacy scrubber (`before_send`) stripping user filepaths, auth tokens, passwords, and raw image/screen payloads.
- Detailed trace recording for:
  - Command interpretation (`flash.interpret`)
  - Tool execution (`flash.action_execution`)
  - Browser workflows (`flash.browser_workflow`)
  - External connection failures (`flash.connection_failure`)
- Latency measurement and outcome classification.
"""

import os
import re
import time
from typing import Any, Dict, Optional
from app.config import settings
from app.logging_config import get_logger

logger = get_logger("flash.telemetry.sentry")

_initialized = False


def scrub_sensitive_event(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Data scrubber: remove local user paths, tokens, authorization headers, and raw screenshot bytes."""
    # 1. Scrub user directory paths (e.g. C:\Users\<name>\...)
    def _scrub_string(val: str) -> str:
        val = re.sub(r"[A-Za-z]:\\[Uu]sers\\[^\\]+", r"[LOCAL_USER_PATH]", val)
        val = re.sub(r"/(?:home|Users)/[^/]+", r"[LOCAL_USER_PATH]", val)
        val = re.sub(r"bearer\s+[A-Za-z0-9\-._~+/]+=*", r"Bearer [REDACTED]", val, flags=re.IGNORECASE)
        val = re.sub(r"(?:api[_-]?key|token|secret|password)=[^&\s]+", r"[REDACTED]", val, flags=re.IGNORECASE)
        return val

    # Scrub breadcrumbs
    if "breadcrumbs" in event and "values" in event["breadcrumbs"]:
        for b in event["breadcrumbs"]["values"]:
            if "message" in b and isinstance(b["message"], str):
                b["message"] = _scrub_string(b["message"])
            if "data" in b and isinstance(b["data"], dict):
                # Remove screenshot base64 or large binary fields
                for k in list(b["data"].keys()):
                    if "screenshot" in k or "image" in k or "raw_bytes" in k:
                        b["data"][k] = "[REDACTED_IMAGE_BYTES]"

    # Scrub extra tags and context
    if "extra" in event and isinstance(event["extra"], dict):
        for k, v in list(event["extra"].items()):
            if any(term in k.lower() for term in ("screenshot", "image", "capture", "screen")):
                event["extra"][k] = "[REDACTED_IMAGE_BYTES]"
            elif isinstance(v, str):
                event["extra"][k] = _scrub_string(v)

    return event


def init_sentry() -> bool:
    """Initialize Sentry SDK with privacy safeguards."""
    global _initialized
    if _initialized:
        return True

    dsn = settings.sentry_dsn
    if not dsn:
        logger.info("SENTRY_DSN not configured; running with local telemetry logger.")
        _initialized = True
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            before_send=scrub_sensitive_event,
            integrations=[FastApiIntegration()],
            send_default_pii=False,  # Strict privacy: do NOT send PII
        )
        logger.info("Sentry initialized in environment: %s", settings.sentry_environment)
        _initialized = True
        return True
    except Exception as e:
        logger.warning("Failed to initialize Sentry: %s", e)
        _initialized = True
        return False


class FlashTracer:
    """Telemetry tracer recording spans for agent actions, interpretation, and browser workflows."""

    @staticmethod
    def record_interpretation(prompt: str, duration_ms: float, success: bool, action_name: Optional[str] = None):
        """Record interpretation latency and outcome."""
        try:
            import sentry_sdk
            with sentry_sdk.start_span(op="flash.interpret", name="Command Interpretation") as span:
                span.set_data("duration_ms", duration_ms)
                span.set_data("success", success)
                span.set_data("selected_action", action_name or "none")
                span.set_tag("interpretation_outcome", "success" if success else "failed")
        except Exception:
            pass
        logger.debug("Telemetry: interpret duration=%.2fms success=%s action=%s", duration_ms, success, action_name)

    @staticmethod
    def record_tool_execution(action_name: str, duration_ms: float, success: bool, error: Optional[str] = None):
        """Record action execution latency and success status."""
        try:
            import sentry_sdk
            with sentry_sdk.start_span(op="flash.action_execution", name=f"Execute {action_name}") as span:
                span.set_data("action_name", action_name)
                span.set_data("duration_ms", duration_ms)
                span.set_data("success", success)
                if error:
                    span.set_data("error_code", error)
                span.set_tag("tool_outcome", "success" if success else "failed")
        except Exception:
            pass
        logger.debug("Telemetry: tool=%s duration=%.2fms success=%s", action_name, duration_ms, success)

    @staticmethod
    def record_browser_workflow(url: str, operation: str, duration_ms: float, success: bool, backend: str = "playwright"):
        """Record browser automation workflow."""
        try:
            import sentry_sdk
            with sentry_sdk.start_span(op="flash.browser_workflow", name=f"Browser {operation}") as span:
                span.set_data("url_domain", url.split("/")[2] if "//" in url else url)
                span.set_data("operation", operation)
                span.set_data("duration_ms", duration_ms)
                span.set_data("success", success)
                span.set_data("backend", backend)
                span.set_tag("browser_outcome", "success" if success else "failed")
        except Exception:
            pass
        logger.debug("Telemetry: browser_workflow op=%s backend=%s success=%s", operation, backend, success)

    @staticmethod
    def record_connection_failure(service_name: str, error: Exception):
        """Capture external service connection failure."""
        try:
            import sentry_sdk
            sentry_sdk.set_tag("failed_service", service_name)
            sentry_sdk.capture_exception(error)
        except Exception:
            pass
        logger.warning("Telemetry: connection failure to %s: %s", service_name, error)


tracer = FlashTracer()
