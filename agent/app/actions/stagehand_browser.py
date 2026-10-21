"""Action: stagehand_browser - High-level AI browser automation using Stagehand and Browserbase."""

import asyncio
from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.security import validate_safe_url
from app.services.browser_stagehand import stagehand_service
from app.logging_config import get_logger

logger = get_logger("flash.action.stagehand_browser")


class StagehandBrowserAction(BaseAction):
    name = "stagehand_browser"
    description = "Intelligent AI-driven browser automation using Stagehand primitives (act, extract, observe) with Browserbase/Playwright."
    requires_confirmation = False
    parameters_schema = {
        "url": {
            "type": "string",
            "required": True,
            "description": "Destination HTTP/HTTPS web address.",
        },
        "operation": {
            "type": "string",
            "required": True,
            "description": "Stagehand operation: 'act', 'extract', or 'observe'.",
        },
        "instruction": {
            "type": "string",
            "required": True,
            "description": "Natural language instruction for the browser action or data extraction.",
        },
        "schema": {
            "type": "object",
            "required": False,
            "description": "Optional JSON schema describing structured fields to extract.",
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        url = parameters.get("url")
        if not url or not isinstance(url, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'url' is required and must be a string.",
                error="MISSING_PARAMETER",
            )

        clean_url = url.strip()
        if "://" not in clean_url:
            clean_url = f"https://{clean_url}"

        is_safe, error_msg = validate_safe_url(clean_url)
        if not is_safe:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Security check failed: {error_msg}",
                error="UNSAFE_URL",
            )

        operation = str(parameters.get("operation", "act")).lower().strip()
        instruction = str(parameters.get("instruction", "observe page")).strip()
        schema = parameters.get("schema")

        try:
            if operation == "act":
                result = asyncio.run(stagehand_service.act(clean_url, instruction))
            elif operation == "extract":
                result = asyncio.run(stagehand_service.extract(clean_url, instruction, schema))
            elif operation == "observe":
                result = asyncio.run(stagehand_service.observe(clean_url, instruction))
            else:
                return ActionResponse(
                    success=False,
                    action=self.name,
                    message=f"Unsupported Stagehand operation '{operation}'. Must be 'act', 'extract', or 'observe'.",
                    error="INVALID_OPERATION",
                )

            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Stagehand {operation} completed on '{clean_url}' via {result.get('backend')}.",
                data=result,
            )
        except Exception as e:
            logger.error("Stagehand browser action error: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Stagehand browser execution failed: {e}",
                error=str(e),
                data={"url": clean_url, "operation": operation},
            )
