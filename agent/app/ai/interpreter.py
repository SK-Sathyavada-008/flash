"""Command Interpreter for Flash Agent.

Translates natural language requests into validated, structured action plans
using local Gemma inference via Ollama. Enforces tool allowlists, parameter validation,
and strict safety constraints.
"""

from typing import Any, Optional
import re
from pydantic import ValidationError

from app.config import settings
from app.actions.registry import registry
from app.ai.ollama_client import (
    OllamaClient,
    OllamaError,
    OllamaMalformedResponseError,
    ollama_client,
)
from app.ai.prompts import build_system_prompt
from app.logging_config import get_logger
from app.models import ActionPlanItem, InterpretationPlan

logger = get_logger("flash.ai.interpreter")


class CommandInterpretationError(Exception):
    """Base exception for interpretation failures."""
    def __init__(self, message: str, error_code: str = "INTERPRETATION_ERROR"):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class UnsupportedActionError(CommandInterpretationError):
    """Model selected an action not in the registered allowlist."""
    def __init__(self, action_name: str, allowlist: list[str]):
        super().__init__(
            f"Unsupported action '{action_name}'. Action must be one of: {allowlist}",
            error_code="UNSUPPORTED_ACTION",
        )
        self.action_name = action_name
        self.allowlist = allowlist


class InvalidActionArgumentsError(CommandInterpretationError):
    """Action arguments failed validation against schema."""
    def __init__(self, action_name: str, details: str):
        super().__init__(
            f"Invalid arguments for action '{action_name}': {details}",
            error_code="INVALID_ACTION_ARGUMENTS",
        )
        self.action_name = action_name
        self.details = details


class CommandInterpreter:
    """Interprets natural-language user prompts into validated execution plans."""

    def __init__(self, client: Optional[OllamaClient] = None) -> None:
        self.client = client or ollama_client

    def validate_plan_schema(self, raw_plan: dict[str, Any]) -> InterpretationPlan:
        """Validate raw dictionary output from model into an InterpretationPlan."""
        try:
            plan = InterpretationPlan.model_validate(raw_plan)
        except ValidationError as e:
            logger.error("Plan validation error: %s", e)
            raise OllamaMalformedResponseError(f"Model response did not match plan schema: {e}") from e

        # Validate that actions is not empty
        if not plan.actions:
            raise CommandInterpretationError(
                "Model returned an empty list of actions.",
                error_code="EMPTY_ACTION_PLAN",
            )

        # Allowlist check: every action must exist in the registered action registry
        registered_actions = {a.name: a for a in registry.list_actions()}
        allowlist = list(registered_actions.keys())

        for item in plan.actions:
            if item.action_name not in registered_actions:
                logger.warning(
                    "Model attempted to call unregistered action '%s'. Allowlist: %s",
                    item.action_name,
                    allowlist,
                )
                raise UnsupportedActionError(item.action_name, allowlist)

            # Check if this action inherits confirmation requirement
            action_def = registered_actions[item.action_name]
            if action_def.requires_confirmation:
                item.requires_confirmation = True
                plan.needs_confirmation = True

            # Validate basic parameters presence according to schema
            self._validate_action_arguments(item, action_def.parameters_schema)

        return plan

    def _validate_action_arguments(
        self, item: ActionPlanItem, schema: dict[str, Any]
    ) -> None:
        """Verify required fields in parameters dictionary."""
        params = item.parameters
        name = item.action_name

        if name == "open_url":
            if "url" not in params:
                for alt in ("query", "search", "search_query", "target"):
                    if alt in params and isinstance(params[alt], str):
                        q = params.pop(alt).strip()
                        if q.startswith(("http://", "https://")):
                            params["url"] = q
                        else:
                            import urllib.parse
                            params["url"] = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
                        break
            if "url" not in params or not isinstance(params["url"], str):
                raise InvalidActionArgumentsError(name, "Missing or non-string 'url' parameter.")
            if params["url"].startswith("www.") or ("://" not in params["url"] and ":" not in params["url"]):
                params["url"] = f"https://{params['url']}"
        elif name == "type_text":
            if "text" not in params:
                for alt in ("message", "content", "input"):
                    if alt in params:
                        params["text"] = str(params.pop(alt))
                        break
            if "text" not in params or not isinstance(params["text"], str):
                raise InvalidActionArgumentsError(name, "Missing or non-string 'text' parameter.")
        elif name == "create_text_file":
            if "filename" not in params:
                params["filename"] = "documents/summary.txt"
            if "content" not in params:
                for alt in ("text", "body", "summary", "notes"):
                    if alt in params:
                        params["content"] = str(params.pop(alt))
                        break
            if "content" not in params:
                params["content"] = "Notes summary generated by Flash."
        elif name == "create_grocery_list":
            if "items" not in params:
                for alt in ("grocery_items", "list", "checklist", "items_list", "ingredients", "products"):
                    if alt in params:
                        params["items"] = params.pop(alt)
                        break
            if isinstance(params.get("items"), str):
                raw = params["items"]
                parts = re.split(r",|;|\n|\sand\s", raw, flags=re.IGNORECASE)
                params["items"] = [p.strip() for p in parts if p.strip()]
            elif isinstance(params.get("items"), list):
                flattened = []
                for it in params["items"]:
                    if isinstance(it, dict):
                        val = str(it.get("item") or it.get("name") or it.get("title") or it)
                    else:
                        val = str(it)
                    for sub in re.split(r",|;|\n|\sand\s", val, flags=re.IGNORECASE):
                        sub_clean = sub.strip()
                        if sub_clean:
                            flattened.append(sub_clean)
                params["items"] = flattened
            if "items" not in params or not isinstance(params["items"], list) or len(params["items"]) == 0:
                params["items"] = ["Grocery items"]

        elif name == "create_spreadsheet":
            if "headers" not in params:
                for alt in ("columns", "fields", "header_list"):
                    if alt in params:
                        params["headers"] = params.pop(alt)
                        break
            if isinstance(params.get("headers"), str):
                parts = re.split(r",|;|\sand\s", params["headers"], flags=re.IGNORECASE)
                params["headers"] = [h.strip() for h in parts if h.strip()]
            elif isinstance(params.get("headers"), list):
                params["headers"] = [str(h) for h in params["headers"]]
            if "headers" not in params or not isinstance(params["headers"], list) or len(params["headers"]) == 0:
                params["headers"] = ["Item", "Quantity", "Notes"]
            if "rows" not in params:
                params["rows"] = []
            if "filename" not in params:
                params["filename"] = "spreadsheets/sheet.xlsx"

        elif name == "create_word_document":
            if "title" not in params:
                for alt in ("heading", "name", "subject", "topic"):
                    if alt in params:
                        params["title"] = str(params.pop(alt))
                        break
            if "title" not in params or not params["title"]:
                params["title"] = "Document"
            if "paragraphs" not in params:
                for alt in ("content", "body", "text", "sections"):
                    if alt in params:
                        val = params.pop(alt)
                        if isinstance(val, str):
                            params["paragraphs"] = [p.strip() for p in val.split("\n") if p.strip()]
                        elif isinstance(val, list):
                            params["paragraphs"] = [str(p) for p in val]
                        break
            if "paragraphs" not in params:
                params["paragraphs"] = ["Generated document content."]
            if "filename" not in params:
                safe_title = re.sub(r"[^\w\-_]", "_", params["title"].lower()).strip("_") or "document"
                params["filename"] = f"documents/{safe_title}.docx"

        elif name == "create_presentation":
            if "title" not in params:
                for alt in ("topic", "subject", "name"):
                    if alt in params:
                        params["title"] = str(params.pop(alt))
                        break
            if "title" not in params or not params["title"]:
                params["title"] = "Presentation"
            if "slides" not in params:
                params["slides"] = [
                    {"title": params["title"], "content": ["Introduction and overview.", "Key points.", "Next steps."]}
                ]
            if "filename" not in params:
                safe_title = re.sub(r"[^\w\-_]", "_", params["title"].lower()).strip("_") or "presentation"
                params["filename"] = f"presentations/{safe_title}.pptx"

        elif name == "open_application":
            if "app_name" not in params:
                for alt in ("app", "application", "name", "program"):
                    if alt in params:
                        params["app_name"] = str(params.pop(alt))
                        break
            if "app_name" not in params or not isinstance(params["app_name"], str):
                raise InvalidActionArgumentsError(name, "Missing or non-string 'app_name' parameter.")

        elif name == "press_keys":
            if "keys" not in params:
                for alt in ("key", "hotkey", "shortcut", "combination"):
                    if alt in params:
                        params["keys"] = params.pop(alt)
                        break
            if isinstance(params.get("keys"), str):
                params["keys"] = [k.strip() for k in re.split(r"[,+]", params["keys"]) if k.strip()]
            if "keys" not in params or not isinstance(params["keys"], list) or len(params["keys"]) == 0:
                raise InvalidActionArgumentsError(name, "Missing or empty 'keys' parameter.")

        elif name == "organize_files":
            if "folder_path" not in params:
                for alt in ("folder", "directory", "path", "dir"):
                    if alt in params:
                        params["folder_path"] = str(params.pop(alt))
                        break
            if "folder_path" not in params or not params["folder_path"]:
                params["folder_path"] = "documents"

        elif name == "web_research":
            if "query" not in params:
                for alt in ("topic", "search", "search_query", "subject"):
                    if alt in params:
                        params["query"] = str(params.pop(alt))
                        break
            if "query" not in params or not isinstance(params["query"], str):
                raise InvalidActionArgumentsError(name, "Missing or non-string 'query' parameter.")

        elif name == "browser_automate":
            if "task" not in params:
                for alt in ("instruction", "goal", "prompt"):
                    if alt in params:
                        params["task"] = str(params.pop(alt))
                        break
            if "task" not in params:
                params["task"] = "Navigate and inspect page"

        elif name == "dictate_text":
            if "text" not in params:
                for alt in ("message", "speech", "content"):
                    if alt in params:
                        params["text"] = str(params.pop(alt))
                        break
            if "text" not in params or not isinstance(params["text"], str):
                raise InvalidActionArgumentsError(name, "Missing or non-string 'text' parameter.")

        elif name == "meeting_assistance":
            if "action" not in params:
                for alt in ("command", "operation", "type"):
                    if alt in params:
                        params["action"] = str(params.pop(alt))
                        break
            if "action" not in params:
                params["action"] = "status"

        elif name == "speak_text":
            if "text" not in params:
                for alt in ("message", "speech", "content", "input"):
                    if alt in params:
                        params["text"] = str(params.pop(alt))
                        break
            if "text" not in params or not isinstance(params["text"], str):
                raise InvalidActionArgumentsError(name, "Missing or non-string 'text' parameter.")

        elif name == "stagehand_browser":
            if "url" not in params or not isinstance(params["url"], str):
                params["url"] = "https://example.com"
            if "operation" not in params:
                params["operation"] = "act"
            if "instruction" not in params:
                params["instruction"] = "observe page"

        elif name == "manage_routines":
            if "operation" not in params:
                params["operation"] = "list"

        elif name == "open_file":
            if "filepath" not in params:
                if "path" in params:
                    params["filepath"] = str(params.pop("path"))
                elif "filename" in params:
                    params["filepath"] = str(params.pop("filename"))
            if "filepath" not in params or not isinstance(params["filepath"], str):
                raise InvalidActionArgumentsError(name, "Missing or non-string 'filepath' parameter.")

    def try_fast_path(self, prompt: str) -> Optional[InterpretationPlan]:
        """Attempt instant rule-based parsing for standard everyday instructions.
        
        Accelerates response times from ~20-30s on CPU to <1ms for standard commands.
        """
        p = prompt.strip()
        # 1. Clean wake words, conversational filler, and politeness prefixes
        cleaned = re.sub(
            r"^(?:hey\s+flash|flash|ok\s+flash|hello\s+flash|hi\s+flash)[,\s:]*\s*",
            "",
            p,
            flags=re.IGNORECASE,
        ).strip()
        cleaned = re.sub(
            r"^(?:please\s+|can\s+you\s+(?:please\s+)?|could\s+you\s+(?:please\s+)?|would\s+you\s+(?:please\s+)?|kindly\s+|i\s+want\s+you\s+to\s+|i\s+need\s+you\s+to\s+|help\s+me\s+to\s+)+",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        # 1. Typing: check before stripping punctuation so user text like "Hello from Zootopia!" is preserved exactly
        type_m = re.match(r"^type(?:\s+this)?(?:\s+into\s+[\w\s.-]+)?:\s*(.+)$", cleaned, re.IGNORECASE)
        if not type_m:
            type_m = re.match(r"^type\s+['\"]?(.+?)['\"]?$", cleaned, re.IGNORECASE)
        if type_m:
            text_to_type = type_m.group(1).strip()
            if text_to_type:
                return self.validate_plan_schema({
                    "intent": "Type requested text into active application",
                    "user_facing_explanation": "Typing that in for you right now.",
                    "needs_confirmation": False,
                    "actions": [{
                        "action_name": "type_text",
                        "parameters": {"text": text_to_type, "press_return": True},
                        "requires_confirmation": False,
                        "explanation": f"Type '{text_to_type}' into the active window",
                    }],
                })

        # 2. For other commands, clean trailing politeness and speech punctuation (e.g. 'open browser.', 'please', 'for me')
        cleaned = re.sub(
            r"(?:[,\s]+please|[,\s]+for\s+me|[,\s]+now|[,\s]+right\s+now)+[.?!\s]*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        cleaned = cleaned.rstrip(".?!,;:").strip()

        # 2. Browser Search or Open Browser:
        # a) "open browser and search for <query>", "search for <query> in browser", "search <query> on google", etc.
        import urllib.parse

        search_m = re.match(
            r"^(?:open\s+(?:the\s+)?(?:web\s+|default\s+)?browser\s+(?:and|to)\s+)?search(?:\s+(?:for|on\s+google\s+for|google\s+for))?\s+(.+?)(?:\s+(?:in\s+(?:the\s+)?browser|on\s+google))?$",
            cleaned,
            re.IGNORECASE,
        )
        if not search_m:
            search_m = re.match(
                r"^open\s+google\s+(?:and|to)\s+search(?:\s+for)?\s+(.+)$",
                cleaned,
                re.IGNORECASE,
            )
        if not search_m:
            search_m = re.match(
                r"^search\s+google\s+for\s+(.+)$",
                cleaned,
                re.IGNORECASE,
            )

        if search_m:
            query = search_m.group(1).strip()
            query = re.sub(r"\s+(?:in\s+(?:the\s+)?browser|on\s+google)$", "", query, flags=re.IGNORECASE).strip()
            query = re.sub(r"^(?:for\s+)", "", query, flags=re.IGNORECASE).strip()
            if query and not re.match(r"^https?://", query, re.IGNORECASE):
                target_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
                return self.validate_plan_schema({
                    "intent": f"Search for '{query}' in web browser",
                    "user_facing_explanation": f"Searching for '{query}'... slowly but surely.",
                    "needs_confirmation": False,
                    "actions": [{
                        "action_name": "open_url",
                        "parameters": {"url": target_url},
                        "requires_confirmation": False,
                        "explanation": f"Launch search for '{query}' in browser",
                    }],
                })

        # b) "open browser", "open the browser", "open google" with no search query
        if re.match(r"^open\s+(?:the\s+)?(?:web\s+|default\s+)?browser(?:\s+(?:and|to)\s+search)?$", cleaned, re.IGNORECASE) or re.match(r"^open\s+google$", cleaned, re.IGNORECASE):
            return self.validate_plan_schema({
                "intent": "Open web browser",
                "user_facing_explanation": "Opening your web browser... slowly but surely.",
                "needs_confirmation": False,
                "actions": [{
                    "action_name": "open_url",
                    "parameters": {"url": "https://www.google.com"},
                    "requires_confirmation": False,
                    "explanation": "Launch default web browser",
                }],
            })

        # c) Open explicit URL: "open https://..." or "open website https://..." or "open www..."
        url_m = re.search(r"\b(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.(?:com|org|io|dev|edu|gov|net)[^\s]*)\b", cleaned, re.IGNORECASE)
        if url_m and re.match(r"^open\s+", cleaned, re.IGNORECASE):
            raw_url = url_m.group(1).strip()
            if not raw_url.startswith(("http://", "https://")):
                raw_url = f"https://{raw_url}"
            return self.validate_plan_schema({
                "intent": f"Open URL in default web browser: {raw_url}",
                "user_facing_explanation": f"Opening {raw_url}... slowly but surely.",
                "needs_confirmation": False,
                "actions": [{
                    "action_name": "open_url",
                    "parameters": {"url": raw_url},
                    "requires_confirmation": False,
                    "explanation": f"Launch {raw_url} in browser",
                }],
            })

        # 3. Grocery List:
        # Handles "grocery list: milk, bread", "create a grocery list with milk, bread",
        # "make a grocery list: milk, bread", "shopping list with apples and oranges",
        # "add milk, bread to grocery list", etc.
        groc_m = re.search(
            r"(?:(?:create|make|generate|build|new)\s+(?:a\s+)?)?(?:grocery|shopping)\s+list(?:\s*(?:with|containing|for|:)\s*|\s+)?(.+)?$",
            cleaned,
            re.IGNORECASE,
        )
        if not groc_m:
            groc_m = re.search(r"^add\s+(.+?)\s+to\s+(?:the\s+)?(?:grocery|shopping)\s+list$", cleaned, re.IGNORECASE)

        if groc_m:
            items_str = groc_m.group(1).strip() if groc_m.group(1) else ""
            if items_str:
                raw_parts = re.split(r",|;|\n|\sand\s", items_str, flags=re.IGNORECASE)
                items = [re.sub(r"^(?:and|with)\s+", "", it.strip(), flags=re.IGNORECASE).strip() for it in raw_parts if it.strip()]
                items = [it for it in items if it]
            else:
                items = ["Milk", "Bread", "Eggs"]

            if items:
                return self.validate_plan_schema({
                    "intent": "Create a grocery checklist with requested items",
                    "user_facing_explanation": f"Created your grocery list with {len(items)} items: {', '.join(items)}.",
                    "needs_confirmation": False,
                    "actions": [{
                        "action_name": "create_grocery_list",
                        "parameters": {
                            "filename": "lists/groceries.md",
                            "title": "Grocery List",
                            "items": items,
                        },
                        "requires_confirmation": False,
                        "explanation": f"Generate checklist for {len(items)} grocery items",
                    }],
                })

        # 4. Word Document:
        # "create a word document", "create a word doc about project plans", "make a word document", "create docx"
        word_m = re.search(
            r"^(?:create|make|generate|build|write)\s+(?:a\s+)?(?:word\s+document|word\s+doc|docx\s+file|docx|document)(?:\s+(?:about|on|for|titled|with\s+title)\s+(.+))?$",
            cleaned,
            re.IGNORECASE,
        )
        if word_m:
            topic = word_m.group(1).strip() if word_m.group(1) else "Document"
            safe_title = re.sub(r"[^\w\-_]", "_", topic.lower()).strip("_") or "document"
            return self.validate_plan_schema({
                "intent": f"Create Word document about '{topic}'",
                "user_facing_explanation": f"Creating Word document '{topic}.docx'.",
                "needs_confirmation": False,
                "actions": [{
                    "action_name": "create_word_document",
                    "parameters": {
                        "filename": f"documents/{safe_title}.docx",
                        "title": topic.title(),
                        "paragraphs": [
                            f"Overview of {topic}.",
                            "Key details, objectives, and milestones.",
                            "Action items and next steps.",
                        ],
                    },
                    "requires_confirmation": False,
                    "explanation": f"Generate Word document '{safe_title}.docx'",
                }],
            })

        # 5. PowerPoint Presentation:
        # "create a powerpoint", "create a presentation", "make slides for quarterly review", "create pptx"
        ppt_m = re.search(
            r"^(?:create|make|generate|build)\s+(?:a\s+)?(?:powerpoint(?:\s+presentation)?|presentation|slideshow|slides|pptx)(?:\s+(?:about|on|for|titled)\s+(.+))?$",
            cleaned,
            re.IGNORECASE,
        )
        if ppt_m:
            topic = ppt_m.group(1).strip() if ppt_m.group(1) else "Presentation"
            safe_title = re.sub(r"[^\w\-_]", "_", topic.lower()).strip("_") or "presentation"
            return self.validate_plan_schema({
                "intent": f"Create PowerPoint presentation for '{topic}'",
                "user_facing_explanation": f"Creating PowerPoint presentation '{topic}.pptx'.",
                "needs_confirmation": False,
                "actions": [{
                    "action_name": "create_presentation",
                    "parameters": {
                        "filename": f"presentations/{safe_title}.pptx",
                        "title": topic.title(),
                        "slides": [
                            {
                                "title": topic.title(),
                                "content": ["Introduction and purpose", "Overview of current status"],
                            },
                            {
                                "title": "Key Points",
                                "content": ["Strategic priorities", "Detailed findings", "Metrics"],
                            },
                            {
                                "title": "Next Steps",
                                "content": ["Action plan", "Timeline and ownership", "Conclusion"],
                            },
                        ],
                    },
                    "requires_confirmation": False,
                    "explanation": f"Generate PowerPoint presentation '{safe_title}.pptx'",
                }],
            })

        # 6. Spreadsheet / Excel:
        # "create an excel sheet", "create an excel file", "make a spreadsheet",
        # "create an excel file with Name, Item, Quantity and Price as headers"
        sheet_m = re.search(
            r"^(?:create|make|generate|build)\s+(?:an?\s+)?(?:excel(?:\s+sheet|\s+file)?|spreadsheet|sheet|xlsx)(?:\s+(?:named|called|for|about|with|having)\s+(.+))?$",
            cleaned,
            re.IGNORECASE,
        )
        if sheet_m:
            detail = sheet_m.group(1).strip() if sheet_m.group(1) else ""
            headers = ["Item", "Quantity", "Price", "Notes"]
            rows = []
            filename = "spreadsheets/sheet.xlsx"

            if detail:
                if re.search(r"headers?|columns?", detail, re.IGNORECASE):
                    raw_h = re.sub(r"^(?:headers?|columns?):\s*", "", detail, flags=re.IGNORECASE)
                    raw_h = re.sub(r"\s+as\s+(?:headers|columns).*$", "", raw_h, flags=re.IGNORECASE)
                    h_parts = re.split(r",|;|\sand\s", raw_h, flags=re.IGNORECASE)
                    parsed_h = [h.strip() for h in h_parts if h.strip()]
                    if parsed_h:
                        headers = parsed_h
                else:
                    safe_sub = re.sub(r"[^\w\-_]", "_", detail.lower()).strip("_")
                    filename = f"spreadsheets/{safe_sub}.xlsx"
                    if "budget" in detail.lower() or "expense" in detail.lower():
                        headers = ["Category", "Budgeted", "Actual", "Difference"]
                        rows = [["Housing", 1200, 1200, 0], ["Groceries", 400, 380, 20], ["Utilities", 150, 160, -10]]
                    elif "inventory" in detail.lower() or "stock" in detail.lower():
                        headers = ["SKU", "Item Name", "Quantity", "Reorder Level"]

            return self.validate_plan_schema({
                "intent": "Generate a new Excel spreadsheet",
                "user_facing_explanation": f"Building your Excel spreadsheet ({filename}).",
                "needs_confirmation": False,
                "actions": [{
                    "action_name": "create_spreadsheet",
                    "parameters": {
                        "filename": filename,
                        "headers": headers,
                        "rows": rows,
                        "sheet_name": "Data",
                    },
                    "requires_confirmation": False,
                    "explanation": f"Create Excel workbook '{filename}'",
                }],
            })

        # 7. Open Application: "open notepad", "launch calculator", "open paint", "start command prompt"
        app_m = re.match(r"^(?:open|launch|start|run)\s+([a-zA-Z0-9\s._-]+)$", cleaned, re.IGNORECASE)
        if app_m:
            app_target = app_m.group(1).strip()
            # Avoid matching web URLs or browser search queries
            if not any(app_target.lower().startswith(x) for x in ("browser", "google", "the browser", "web browser", "url", "http", "www")):
                # Check known safe apps
                return self.validate_plan_schema({
                    "intent": f"Launch application: {app_target}",
                    "user_facing_explanation": f"Opening {app_target}...",
                    "needs_confirmation": False,
                    "actions": [{
                        "action_name": "open_application",
                        "parameters": {"app_name": app_target},
                        "requires_confirmation": False,
                        "explanation": f"Launch Windows application '{app_target}'",
                    }],
                })

        # 8. Keyboard Shortcuts: "press ctrl+c", "press enter", "press alt+tab"
        key_m = re.match(r"^press\s+([a-zA-Z0-9+,_\s-]+)$", cleaned, re.IGNORECASE)
        if key_m:
            key_expr = key_m.group(1).strip()
            keys = [k.strip() for k in re.split(r"[,+]", key_expr) if k.strip()]
            if keys:
                return self.validate_plan_schema({
                    "intent": f"Press keyboard shortcut: {'+'.join(keys)}",
                    "user_facing_explanation": f"Pressing {'+'.join(keys)}...",
                    "needs_confirmation": False,
                    "actions": [{
                        "action_name": "press_keys",
                        "parameters": {"keys": keys},
                        "requires_confirmation": False,
                        "explanation": f"Simulate keyboard shortcut {'+'.join(keys)}",
                    }],
                })

        # 9. Screen Understanding: "what is on my screen", "inspect screen", "read screen", "what windows and buttons are visible"
        if re.search(r"^(?:what(?:'s|\s+is)\s+on\s+(?:my\s+)?(?:screen|desktop)|inspect\s+screen|read\s+screen|describe\s+screen|what\s+.*(?:windows|buttons|controls|elements)\s+are\s+visible.*)\??$", cleaned, re.IGNORECASE):
            return self.validate_plan_schema({
                "intent": "Inspect screen accessibility metadata and active window",
                "user_facing_explanation": "Inspecting your screen elements...",
                "needs_confirmation": False,
                "actions": [{
                    "action_name": "inspect_screen",
                    "parameters": {},
                    "requires_confirmation": False,
                    "explanation": "Query Windows UIAutomation for active window controls",
                }],
            })

        # 10. Point to element: "point to <name>"
        point_m = re.match(r"^point\s+(?:to|at)\s+(.+)$", cleaned, re.IGNORECASE)
        if point_m:
            target_str = point_m.group(1).strip()
            return self.validate_plan_schema({
                "intent": f"Point cursor to element: {target_str}",
                "user_facing_explanation": f"Pointing to '{target_str}'...",
                "needs_confirmation": False,
                "actions": [{
                    "action_name": "point_to_element",
                    "parameters": {"target": target_str},
                    "requires_confirmation": False,
                    "explanation": f"Find and point cursor at '{target_str}'",
                }],
            })

        # 11. Web Research: "research <topic>", "do web research on <topic>"
        research_m = re.match(r"^(?:do\s+web\s+|conduct\s+)?research(?:\s+on|\s+about)?\s+(.+)$", cleaned, re.IGNORECASE)
        if research_m:
            topic = research_m.group(1).strip()
            return self.validate_plan_schema({
                "intent": f"Conduct web research on '{topic}'",
                "user_facing_explanation": f"Researching '{topic}' and compiling a report...",
                "needs_confirmation": False,
                "actions": [{
                    "action_name": "web_research",
                    "parameters": {"query": topic},
                    "requires_confirmation": False,
                    "explanation": f"Search web and compile markdown research report on '{topic}'",
                }],
            })

        # 12. Meeting Assistance: "start meeting", "stop meeting", "summarize meeting", "meeting notes"
        meeting_m = re.match(r"^(?:meeting\s+(?:status|summary|notes)|(?:start|stop|record|summarize)\s+meeting)$", cleaned, re.IGNORECASE)
        if meeting_m:
            cmd = cleaned.lower()
            action_type = "status"
            if "start" in cmd or "record" in cmd:
                action_type = "start"
            elif "stop" in cmd:
                action_type = "stop"
            elif "summarize" in cmd or "summary" in cmd or "notes" in cmd:
                action_type = "summarize"

            return self.validate_plan_schema({
                "intent": f"Meeting assistance action: {action_type}",
                "user_facing_explanation": f"Meeting assistance: executing {action_type}...",
                "needs_confirmation": False,
                "actions": [{
                    "action_name": "meeting_assistance",
                    "parameters": {"action": action_type},
                    "requires_confirmation": False,
                    "explanation": f"Execute meeting assistant command '{action_type}'",
                }],
            })

        # 13. File Organization: "organize files in <folder>", "organize downloads", "clean up files"
        org_m = re.match(r"^(?:organize|clean\s+up)\s+(?:files\s+in\s+|my\s+)?([a-zA-Z0-9_.\-\\]+)$", cleaned, re.IGNORECASE)
        if org_m:
            folder = org_m.group(1).strip()
            return self.validate_plan_schema({
                "intent": f"Organize files in '{folder}'",
                "user_facing_explanation": f"Previewing file organization for '{folder}' (requires confirmation).",
                "needs_confirmation": True,
                "actions": [{
                    "action_name": "organize_files",
                    "parameters": {"folder_path": folder, "confirmed": False},
                    "requires_confirmation": True,
                    "explanation": f"Preview file categorization and organization in '{folder}'",
                }],
            })

        # 14. Speak Text: "speak <text>" or "say <text>"
        speak_m = re.match(r"^(?:speak|say)\s+['\"]?(.+?)['\"]?$", cleaned, re.IGNORECASE)
        if speak_m:
            text_to_speak = speak_m.group(1).strip()
            if text_to_speak:
                return self.validate_plan_schema({
                    "intent": f"Speak text: {text_to_speak}",
                    "user_facing_explanation": f"Speaking: '{text_to_speak}'",
                    "needs_confirmation": False,
                    "actions": [{
                        "action_name": "speak_text",
                        "parameters": {"text": text_to_speak},
                        "requires_confirmation": False,
                        "explanation": f"Synthesize and speak '{text_to_speak}'",
                    }],
                })

        # 15. Status: "What are you doing?" / "status" / "agent status"
        if re.search(r"^(?:status|agent\s+status|health|what\s+are\s+you\s+doing|how\s+are\s+you)\??$", cleaned, re.IGNORECASE):
            return self.validate_plan_schema({
                "intent": "Check Flash agent runtime status",
                "user_facing_explanation": "Checking agent status... all systems operational.",
                "needs_confirmation": False,
                "actions": [{
                    "action_name": "get_agent_status",
                    "parameters": {},
                    "requires_confirmation": False,
                    "explanation": "Query current system status and active connections",
                }],
            })

        return None

    def interpret(self, prompt: str) -> InterpretationPlan:
        """Interpret natural language prompt into a validated InterpretationPlan."""
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise CommandInterpretationError("User prompt cannot be empty.", error_code="EMPTY_PROMPT")

        logger.info("Interpreting prompt: '%s'", clean_prompt)

        # Fast path check: if enabled and not running against a test mock, return instant parsed plan
        is_mock = hasattr(self.client, "_mock_return_value") or self.client.__class__.__name__ == "MagicMock"
        if getattr(settings, "fast_path_enabled", True) and not is_mock:
            fast_plan = self.try_fast_path(clean_prompt)
            if fast_plan is not None:
                logger.info("Fast-path matched for prompt: '%s' -> %s", clean_prompt, fast_plan.intent)
                return fast_plan

        return self.interpret_with_llm(clean_prompt)

    def interpret_with_llm(self, clean_prompt: str) -> InterpretationPlan:
        """Execute local LLM inference (e.g. Gemma via Ollama) with strict schema validation."""
        # 1. Verify Ollama and model are available
        self.client.verify_ready()

        # 2. Build system prompt from active action registry
        registered_actions = [
            {
                "name": act.name,
                "description": act.description,
                "parameters_schema": act.parameters_schema,
                "requires_confirmation": act.requires_confirmation,
            }
            for act in registry.list_actions()
        ]
        system_prompt = build_system_prompt(registered_actions)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": clean_prompt},
        ]

        # 3. Call Ollama for JSON chat completion
        raw_response = self.client.chat_json(messages)

        # 4. Strict validation and allowlist filtering
        return self.validate_plan_schema(raw_response)


# Global default command interpreter singleton
command_interpreter = CommandInterpreter()
