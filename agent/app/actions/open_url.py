import os
import sys
import webbrowser
from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.security import validate_safe_url
from app.logging_config import get_logger

logger = get_logger("flash.action.open_url")


class OpenUrlAction(BaseAction):
    name = "open_url"
    description = "Opens a validated HTTP or HTTPS web address in the user's default web browser."
    requires_confirmation = False
    parameters_schema = {
        "url": {
            "type": "string",
            "required": True,
            "description": "The destination HTTP or HTTPS address to open.",
        }
    }
    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        raw_url = parameters.get("url")
        if not raw_url or not isinstance(raw_url, str):
            for alt in ("query", "search", "search_query"):
                if parameters.get(alt) and isinstance(parameters[alt], str):
                    import urllib.parse
                    raw_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(parameters[alt].strip())}"
                    break
        if not raw_url or not isinstance(raw_url, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'url' is required and must be a string.",
                error="MISSING_PARAMETER",
            )

        clean_url = raw_url.strip()
        if clean_url.startswith("www.") or ("://" not in clean_url and ":" not in clean_url):
            clean_url = f"https://{clean_url}"

        is_safe, error_msg = validate_safe_url(clean_url)
        if not is_safe:
            logger.warning("Rejected unsafe URL '%s': %s", clean_url, error_msg)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Security check failed: {error_msg}",
                error="UNSAFE_URL",
                data={"url": clean_url},
            )

        try:
            logger.info("Opening validated URL: %s", clean_url)
            opened = webbrowser.open(clean_url)
            if not opened and sys.platform == "win32":
                try:
                    os.startfile(clean_url)
                    opened = True
                except Exception as ex:
                    logger.debug("os.startfile failed: %s", ex)

            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Successfully opened '{clean_url}' in the default browser.",
                data={"url": clean_url},
            )
        except Exception as e:
            logger.error("Failed to open URL '%s': %s", clean_url, e, exc_info=True)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Failed to open URL: {e}",
                error=str(e),
                data={"url": clean_url},
            )
