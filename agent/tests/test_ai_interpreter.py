"""Tests for Command Interpreter: prompt parsing, tool allowlist, schema enforcement."""

import pytest
from unittest.mock import MagicMock

from app.actions.registry import register_default_actions
from app.ai.interpreter import (
    CommandInterpreter,
    CommandInterpretationError,
    InvalidActionArgumentsError,
    UnsupportedActionError,
)
from app.ai.ollama_client import OllamaClient


@pytest.fixture(autouse=True)
def setup_actions():
    """Ensure standard actions are registered."""
    register_default_actions()


def test_valid_request_interpretation_grocery():
    """Verify interpretation of grocery list request."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.chat_json.return_value = {
        "intent": "Create a grocery checklist with requested items",
        "user_facing_explanation": "I have created your grocery list with milk, rice, and bananas.",
        "needs_confirmation": False,
        "actions": [
            {
                "action_name": "create_grocery_list",
                "parameters": {
                    "filename": "lists/groceries.md",
                    "title": "Grocery List",
                    "items": ["milk", "rice", "bananas"],
                },
                "requires_confirmation": False,
                "explanation": "Generate markdown checklist for groceries",
            }
        ],
    }

    interpreter = CommandInterpreter(client=mock_client)
    plan = interpreter.interpret("Make a grocery list with milk, rice and bananas.")

    assert plan.intent == "Create a grocery checklist with requested items"
    assert len(plan.actions) == 1
    assert plan.actions[0].action_name == "create_grocery_list"
    assert plan.actions[0].parameters["items"] == ["milk", "rice", "bananas"]
    assert plan.needs_confirmation is False


def test_valid_request_interpretation_spreadsheet():
    """Verify interpretation of spreadsheet creation request."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.chat_json.return_value = {
        "intent": "Generate a new Excel spreadsheet with specific column headers",
        "user_facing_explanation": "Building your Excel spreadsheet with Name, Item, Quantity, and Price.",
        "needs_confirmation": False,
        "actions": [
            {
                "action_name": "create_spreadsheet",
                "parameters": {
                    "filename": "spreadsheets/inventory.xlsx",
                    "headers": ["Name", "Item", "Quantity", "Price"],
                    "rows": [],
                    "sheet_name": "Inventory",
                },
                "requires_confirmation": False,
                "explanation": "Create formatted Excel workbook",
            }
        ],
    }

    interpreter = CommandInterpreter(client=mock_client)
    plan = interpreter.interpret("Create an Excel file with Name, Item, Quantity and Price as headers.")

    assert len(plan.actions) == 1
    assert plan.actions[0].action_name == "create_spreadsheet"
    assert plan.actions[0].parameters["headers"] == ["Name", "Item", "Quantity", "Price"]


def test_valid_request_interpretation_typing():
    """Verify interpretation of typing instruction into focused application."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.chat_json.return_value = {
        "intent": "Type provided text into the active window",
        "user_facing_explanation": "Typing your message into Notepad.",
        "needs_confirmation": False,
        "actions": [
            {
                "action_name": "type_text",
                "parameters": {
                    "text": "My project is ready.",
                    "press_return": True,
                },
                "requires_confirmation": False,
                "explanation": "Send keyboard input to active application",
            }
        ],
    }

    interpreter = CommandInterpreter(client=mock_client)
    plan = interpreter.interpret("Hey Flash, type this into Notepad: My project is ready.")

    assert plan.actions[0].action_name == "type_text"
    assert plan.actions[0].parameters["text"] == "My project is ready."


def test_valid_request_interpretation_open_url():
    """Verify interpretation of URL navigation request."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.chat_json.return_value = {
        "intent": "Open YouTube in default browser",
        "user_facing_explanation": "Opening YouTube for you.",
        "needs_confirmation": False,
        "actions": [
            {
                "action_name": "open_url",
                "parameters": {"url": "https://www.youtube.com"},
                "requires_confirmation": False,
                "explanation": "Launch default browser with YouTube URL",
            }
        ],
    }

    interpreter = CommandInterpreter(client=mock_client)
    plan = interpreter.interpret("Open YouTube.")

    assert plan.actions[0].action_name == "open_url"
    assert plan.actions[0].parameters["url"] == "https://www.youtube.com"


def test_unsupported_action_rejection():
    """Verify that hallucinated or malicious shell commands are strictly rejected."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.chat_json.return_value = {
        "intent": "Execute bash script",
        "user_facing_explanation": "Running a script...",
        "needs_confirmation": False,
        "actions": [
            {
                "action_name": "execute_bash_command",  # Not in allowlist!
                "parameters": {"command": "rm -rf /"},
                "requires_confirmation": False,
                "explanation": "Dangerous arbitrary execution",
            }
        ],
    }

    interpreter = CommandInterpreter(client=mock_client)
    with pytest.raises(UnsupportedActionError) as exc_info:
        interpreter.interpret("Run a shell command")

    assert "Unsupported action 'execute_bash_command'" in str(exc_info.value)
    assert exc_info.value.error_code == "UNSUPPORTED_ACTION"


def test_invalid_arguments_rejection():
    """Verify rejection when parameters violate action schema."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.chat_json.return_value = {
        "intent": "Open URL with invalid params",
        "user_facing_explanation": "Opening URL...",
        "needs_confirmation": False,
        "actions": [
            {
                "action_name": "open_url",
                "parameters": {"invalid_param": 123},
                "requires_confirmation": False,
                "explanation": "Missing url parameter",
            }
        ],
    }

    interpreter = CommandInterpreter(client=mock_client)
    with pytest.raises(InvalidActionArgumentsError) as exc_info:
        interpreter.interpret("Open website with bad parameters")

    assert "url" in str(exc_info.value).lower()
    assert exc_info.value.error_code == "INVALID_ACTION_ARGUMENTS"


def test_empty_action_plan_rejection():
    """Verify rejection when model returns zero actions."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.chat_json.return_value = {
        "intent": "Do nothing",
        "user_facing_explanation": "I cannot do that.",
        "needs_confirmation": False,
        "actions": [],
    }

    interpreter = CommandInterpreter(client=mock_client)
    with pytest.raises(CommandInterpretationError) as exc_info:
        interpreter.interpret("Do nothing")

    assert exc_info.value.error_code == "EMPTY_ACTION_PLAN"


def test_empty_prompt_rejection():
    """Verify rejection when user prompt is empty whitespace."""
    interpreter = CommandInterpreter()
    with pytest.raises(CommandInterpretationError) as exc_info:
        interpreter.interpret("   ")
    assert exc_info.value.error_code == "EMPTY_PROMPT"


def test_fast_path_typing():
    """Verify fast-path instantly produces valid plan for typing command."""
    interpreter = CommandInterpreter()
    plan = interpreter.try_fast_path("Hey Flash, type this into Notepad: Hello from Zootopia!")
    assert plan is not None
    assert len(plan.actions) == 1
    assert plan.actions[0].action_name == "type_text"
    assert plan.actions[0].parameters["text"] == "Hello from Zootopia!"


def test_fast_path_open_url():
    """Verify fast-path instantly produces valid plan for URL command."""
    interpreter = CommandInterpreter()
    plan = interpreter.try_fast_path("open https://github.com/google")
    assert plan is not None
    assert plan.actions[0].action_name == "open_url"
    assert plan.actions[0].parameters["url"] == "https://github.com/google"


def test_fast_path_grocery_list():
    """Verify fast-path instantly produces valid plan for grocery checklist."""
    interpreter = CommandInterpreter()
    plan = interpreter.try_fast_path("Make a grocery list with apples, bananas and oat milk")
    assert plan is not None
    assert plan.actions[0].action_name == "create_grocery_list"
    assert "apples" in plan.actions[0].parameters["items"]
    assert "bananas" in plan.actions[0].parameters["items"]
    assert "oat milk" in plan.actions[0].parameters["items"]


def test_fast_path_spreadsheet():
    """Verify fast-path instantly produces valid plan for Excel spreadsheet."""
    interpreter = CommandInterpreter()
    plan = interpreter.try_fast_path("Create an Excel file with Name, Quantity, Price as headers")
    assert plan is not None
    assert plan.actions[0].action_name == "create_spreadsheet"
    assert plan.actions[0].parameters["headers"] == ["Name", "Quantity", "Price"]


def test_fast_path_status():
    """Verify fast-path instantly handles status query."""
    interpreter = CommandInterpreter()
    plan = interpreter.try_fast_path("Hey Flash, what are you doing?")
    assert plan is not None
    assert plan.actions[0].action_name == "get_agent_status"


def test_fast_path_fallback_on_unrecognized():
    """Verify that arbitrary or complex prompts return None for LLM fallback."""
    interpreter = CommandInterpreter()
    plan = interpreter.try_fast_path("Analyze the financial trajectory of Q3 and summarize risks")
    assert plan is None


def test_fast_path_open_browser_and_search():
    """Regression test: fast path parses 'open browser and search for something' immediately."""
    interpreter = CommandInterpreter()

    # Exact user reported prompt
    plan = interpreter.try_fast_path("open browser and search for something")
    assert plan is not None
    assert len(plan.actions) == 1
    assert plan.actions[0].action_name == "open_url"
    assert plan.actions[0].parameters["url"] == "https://www.google.com/search?q=something"

    # With Hey Flash prefix
    plan2 = interpreter.try_fast_path("Hey Flash, open browser and search for python tutorial")
    assert plan2 is not None
    assert plan2.actions[0].parameters["url"] == "https://www.google.com/search?q=python+tutorial"

    # Search in browser variant
    plan3 = interpreter.try_fast_path("search for cute dogs in browser")
    assert plan3 is not None
    assert plan3.actions[0].parameters["url"] == "https://www.google.com/search?q=cute+dogs"

    # Search on google variant
    plan4 = interpreter.try_fast_path("search pizza on google")
    assert plan4 is not None
    assert plan4.actions[0].parameters["url"] == "https://www.google.com/search?q=pizza"


def test_fast_path_open_browser_generic():
    """Regression test: fast path parses 'open browser' or 'open google' without search query."""
    interpreter = CommandInterpreter()

    plan = interpreter.try_fast_path("open browser")
    assert plan is not None
    assert plan.actions[0].action_name == "open_url"
    assert plan.actions[0].parameters["url"] == "https://www.google.com"

    plan2 = interpreter.try_fast_path("open the browser")
    assert plan2 is not None
    assert plan2.actions[0].parameters["url"] == "https://www.google.com"

    plan3 = interpreter.try_fast_path("open google")
    assert plan3 is not None
    assert plan3.actions[0].parameters["url"] == "https://www.google.com"


