"""Action: browser_automate - Automated web interactions via Playwright."""

import asyncio
from typing import Any, Optional
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.security import validate_safe_url
from app.logging_config import get_logger

logger = get_logger("flash.action.browser_automate")


class BrowserAutomateAction(BaseAction):
    name = "browser_automate"
    description = "Automates browser navigation, element clicking, form filling, and text extraction using Playwright."
    requires_confirmation = False
    parameters_schema = {
        "url": {
            "type": "string",
            "required": True,
            "description": "Destination HTTP/HTTPS web address.",
        },
        "action": {
            "type": "string",
            "required": False,
            "default": "navigate",
            "description": "Automation action: 'navigate', 'click', 'fill', or 'extract_text'.",
        },
        "selector": {
            "type": "string",
            "required": False,
            "description": "CSS or text selector for click/fill/extract operations.",
        },
        "text": {
            "type": "string",
            "required": False,
            "description": "Text to fill into target input field.",
        },
        "headless": {
            "type": "boolean",
            "required": False,
            "default": True,
            "description": "Run browser in headless mode (default True).",
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
        if not clean_url.startswith(("http://", "https://")):
            clean_url = f"https://{clean_url}"

        is_safe, error_msg = validate_safe_url(clean_url)
        if not is_safe:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Security check failed: {error_msg}",
                error="UNSAFE_URL",
            )

        action_type = str(parameters.get("action", "navigate")).lower()
        selector = parameters.get("selector")
        text_val = parameters.get("text", "")
        headless = bool(parameters.get("headless", True))

        # Synchronously invoke playwright via asyncio
        try:
            return asyncio.run(self._execute_playwright(clean_url, action_type, selector, text_val, headless))
        except Exception as e:
            logger.error("Playwright automation failed: %s", e)
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Browser automation failed: {e}",
                error=str(e),
                data={"url": clean_url, "action": action_type},
            )

    async def _execute_playwright(
        self, url: str, action: str, selector: Optional[str], text: str, headless: bool
    ) -> ActionResponse:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=headless, timeout=12000)
            except Exception as ex:
                # If chromium binaries not downloaded yet, fallback to system edge
                try:
                    browser = await p.chromium.launch(channel="msedge", headless=headless, timeout=12000)
                except Exception:
                    raise ex

            page = await browser.new_page()
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            title = await page.title()

            result_data: dict[str, Any] = {"title": title, "url": page.url}

            if action == "click" and selector:
                await page.click(selector, timeout=8000)
                result_data["clicked_selector"] = selector
            elif action == "fill" and selector:
                await page.fill(selector, text, timeout=8000)
                result_data["filled_selector"] = selector
                result_data["text"] = text
            elif action == "extract_text":
                if selector:
                    elem = await page.query_selector(selector)
                    extracted = await elem.inner_text() if elem else ""
                else:
                    extracted = await page.inner_text("body")
                result_data["extracted_text"] = extracted[:1000]

            await browser.close()

            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Successfully automated {action} on '{url}' (Page Title: {title}).",
                data=result_data,
            )
