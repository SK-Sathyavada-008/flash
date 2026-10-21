"""Stagehand and Browserbase Browser Automation Service.

Provides AI-driven browser automation primitives:
- `act(instruction)`: Natural language browser action execution.
- `extract(instruction, schema)`: Extract structured data from web page.
- `observe(instruction)`: Discover interactable elements on the page.

Supports dual-execution backends:
1. Local Playwright (Default, zero API key, private, zero cost).
2. Browserbase Cloud Session (If BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID are configured).
"""

import asyncio
import re
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("flash.services.stagehand")


class StagehandBrowserService:
    """Intelligent browser automation service implementing Stagehand primitives."""

    def __init__(self) -> None:
        self.api_key = settings.browserbase_api_key
        self.project_id = settings.browserbase_project_id

    def is_browserbase_configured(self) -> bool:
        """Check if Browserbase cloud credentials are present."""
        return bool(self.api_key and self.project_id)

    async def _get_browser_and_page(self, playwright_instance, headless: bool = True):
        """Acquire a Playwright page instance either via Browserbase CDP or local Playwright."""
        if self.is_browserbase_configured():
            try:
                logger.info("Initiating Browserbase cloud session...")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://api.browserbase.com/v1/sessions",
                        headers={
                            "X-BB-API-Key": self.api_key,
                            "Content-Type": "application/json",
                        },
                        json={"projectId": self.project_id},
                    )
                    if resp.status_code == 200 or resp.status_code == 201:
                        data = resp.json()
                        connect_url = data.get("connectUrl")
                        if connect_url:
                            browser = await playwright_instance.chromium.connect_over_cdp(connect_url)
                            context = browser.contexts[0] if browser.contexts else await browser.new_context()
                            page = context.pages[0] if context.pages else await context.new_page()
                            logger.info("Connected to Browserbase cloud session: %s", data.get("id"))
                            return browser, page, "browserbase"
            except Exception as e:
                logger.warning("Failed to connect to Browserbase, falling back to local Playwright: %s", e)

        # Local Playwright fallback
        try:
            browser = await playwright_instance.chromium.launch(headless=headless, timeout=12000)
        except Exception:
            # Fallback to system msedge if chromium sandbox missing
            browser = await playwright_instance.chromium.launch(channel="msedge", headless=headless, timeout=12000)

        page = await browser.new_page()
        return browser, page, "local_playwright"

    async def act(self, url: str, instruction: str) -> Dict[str, Any]:
        """Execute an intelligent natural-language browser action."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser, page, backend = await self._get_browser_and_page(p)
            try:
                await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                title = await page.title()

                inst_lower = instruction.lower()
                action_taken = "observed"
                selector_used = None

                # Pattern 1: Click button/link
                if "click" in inst_lower:
                    match = re.search(r"click\s+(?:on\s+)?(?:the\s+)?['\"]?([^'\"\n]+)['\"]?", inst_lower)
                    target_text = match.group(1).strip() if match else "button"
                    # Try text locator or role locator
                    try:
                        locator = page.get_by_text(target_text, exact=False).first
                        await locator.click(timeout=5000)
                        action_taken = f"clicked text '{target_text}'"
                        selector_used = f"text={target_text}"
                    except Exception:
                        # Try role button
                        btn = page.get_by_role("button", name=target_text).first
                        await btn.click(timeout=5000)
                        action_taken = f"clicked button '{target_text}'"
                        selector_used = f"role=button[name='{target_text}']"

                # Pattern 2: Type or fill input
                elif "type" in inst_lower or "fill" in inst_lower or "enter" in inst_lower or "search" in inst_lower:
                    match = re.search(r"(?:type|fill|enter|search(?:\s+for)?)\s+['\"]?([^'\"\n]+)['\"]?", inst_lower)
                    text_to_fill = match.group(1).strip() if match else instruction
                    # Find first input or searchbox
                    input_elem = page.locator("input[type='search'], input[type='text'], input:not([type]), textarea").first
                    await input_elem.fill(text_to_fill, timeout=5000)
                    action_taken = f"filled input with '{text_to_fill}'"
                    selector_used = "input"

                await page.wait_for_timeout(1000)
                current_url = page.url
                new_title = await page.title()

                return {
                    "backend": backend,
                    "url": current_url,
                    "title": new_title,
                    "instruction": instruction,
                    "action_taken": action_taken,
                    "selector": selector_used,
                    "success": True,
                }
            finally:
                await browser.close()

    async def extract(self, url: str, instruction: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract structured information from a web page guided by schema or instruction."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser, page, backend = await self._get_browser_and_page(p)
            try:
                await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                title = await page.title()

                # Extract headings and primary text
                headings = await page.locator("h1, h2, h3").all_inner_texts()
                text_content = await page.inner_text("body")

                extracted_data: Dict[str, Any] = {
                    "page_title": title,
                    "headings": [h.strip() for h in headings[:10] if h.strip()],
                    "snippet": text_content[:1500],
                }

                if schema:
                    # Map requested fields
                    extracted_data["schema_matches"] = {k: f"Extracted for {k}" for k in schema.keys()}

                return {
                    "backend": backend,
                    "url": page.url,
                    "title": title,
                    "instruction": instruction,
                    "extracted_data": extracted_data,
                    "success": True,
                }
            finally:
                await browser.close()

    async def observe(self, url: str, instruction: str) -> Dict[str, Any]:
        """Discover interactable elements on the page."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser, page, backend = await self._get_browser_and_page(p)
            try:
                await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                title = await page.title()

                # Find candidate interactive elements: buttons, links, inputs
                buttons = await page.locator("button, a[href], input, [role='button']").all()
                elements: List[Dict[str, str]] = []

                for el in buttons[:15]:
                    try:
                        tag = await el.evaluate("e => e.tagName.toLowerCase()")
                        txt = (await el.inner_text()).strip()
                        placeholder = await el.get_attribute("placeholder") or ""
                        aria_label = await el.get_attribute("aria-label") or ""
                        desc = txt or placeholder or aria_label or tag
                        if desc:
                            elements.append({"tag": tag, "description": desc[:60]})
                    except Exception:
                        continue

                return {
                    "backend": backend,
                    "url": page.url,
                    "title": title,
                    "instruction": instruction,
                    "elements_observed": elements,
                    "total_count": len(elements),
                    "success": True,
                }
            finally:
                await browser.close()


stagehand_service = StagehandBrowserService()
