"""Tests for Milestone 5: Windows desktop control, Office automation, grocery voice splitting,
meeting assistance, screen understanding, file organization, and safety guardrails.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.actions.create_word_document import CreateWordDocumentAction
from app.actions.create_presentation import CreatePresentationAction
from app.actions.create_spreadsheet import CreateSpreadsheetAction
from app.actions.create_grocery_list import CreateGroceryListAction
from app.actions.open_application import OpenApplicationAction
from app.actions.press_keys import PressKeysAction
from app.actions.mouse_click import MouseClickAction
from app.actions.mouse_drag import MouseDragAction
from app.actions.mouse_scroll import MouseScrollAction
from app.actions.point_to_element import PointToElementAction
from app.actions.inspect_screen import InspectScreenAction
from app.actions.capture_screen import CaptureScreenAction
from app.actions.organize_files import OrganizeFilesAction
from app.actions.web_research import WebResearchAction
from app.actions.dictate_text import DictateTextAction
from app.actions.meeting_assistance import MeetingAssistanceAction
from app.actions.registry import registry
from app.ai.interpreter import CommandInterpreter
from app.services.meeting_manager import meeting_manager


@pytest.fixture
def tmp_output_dir(tmp_path):
    with patch("app.config.settings.workspace_dir", tmp_path):
        yield tmp_path


# --- Office & Document Automation Tests ---

def test_create_word_document(tmp_output_dir):
    action = CreateWordDocumentAction()
    result = action.run({
        "filename": "documents/report.docx",
        "title": "Quarterly Progress",
        "paragraphs": ["First section overview.", "Second section details."],
    })
    assert result.success is True
    created_path = tmp_output_dir / "documents" / "report.docx"
    assert created_path.exists()
    assert result.data["paragraphs_count"] >= 2


def test_create_presentation(tmp_output_dir):
    action = CreatePresentationAction()
    result = action.run({
        "filename": "presentations/deck.pptx",
        "title": "Strategy Review",
        "slides": [
            {"title": "Slide 1", "content": ["Point A", "Point B"]},
            {"title": "Slide 2", "content": ["Action 1"]},
        ],
    })
    assert result.success is True
    created_path = tmp_output_dir / "presentations" / "deck.pptx"
    assert created_path.exists()
    assert result.data["slides_count"] == 3  # title slide + 2 content slides


def test_create_spreadsheet_lenient_and_formulas(tmp_output_dir):
    action = CreateSpreadsheetAction()
    # Test with comma-separated string headers & formula row
    result = action.run({
        "filename": "spreadsheets/finances.xlsx",
        "headers": "Item, Cost, Tax",
        "rows": [["Desk", 200, 20], ["Chair", 100, 10], ["Total", "=SUM(B2:B3)", "=SUM(C2:C3)"]],
        "sheet_name": "Ledger",
    })
    assert result.success is True
    created_path = tmp_output_dir / "spreadsheets" / "finances.xlsx"
    assert created_path.exists()
    assert result.data["headers"] == ["Item", "Cost", "Tax"]
    assert result.data["rows_count"] == 3


# --- Grocery List Voice Splitting Tests ---

def test_create_grocery_list_voice_item_splitting(tmp_output_dir):
    action = CreateGroceryListAction()
    # User says "milk, bread" in voice, passed as single merged string in list or string
    result = action.run({
        "filename": "lists/groceries.md",
        "title": "Weekly Shopping",
        "items": ["milk, bread and eggs"],
    })
    assert result.success is True
    created_path = tmp_output_dir / "lists" / "groceries.md"
    assert created_path.exists()
    content = created_path.read_text(encoding="utf-8")
    assert "- [ ] milk" in content
    assert "- [ ] bread" in content
    assert "- [ ] eggs" in content
    assert result.data["item_count"] == 3


# --- Windows Desktop Control & Safety Tests ---

def test_open_application_allowlist():
    action = OpenApplicationAction()
    # Non-allowed application should be blocked
    result = action.run({"app_name": "powershell_evil.exe"})
    assert result.success is False
    assert "not in the allowed applications list" in result.message


def test_press_keys_safety():
    action = PressKeysAction()
    # win+l must be blocked
    res_lock = action.run({"keys": ["win", "l"]})
    assert res_lock.success is False
    assert "blocked" in (res_lock.error or res_lock.message).lower()

    # alt+f4 requires confirmation
    res_close = action.run({"keys": ["alt", "f4"]}, confirmed=False)
    assert res_close.success is False
    assert "confirmation" in (res_close.error or res_close.message).lower()


def test_mouse_actions_validation():
    click_act = MouseClickAction()
    # Missing coordinates and element_id
    res = click_act.run({})
    assert res.success is False

    drag_act = MouseDragAction()
    # Out-of-bounds coordinates
    res_drag = drag_act.run({"start_x": -10, "start_y": 500, "end_x": 500, "end_y": 500})
    assert res_drag.success is False

    scroll_act = MouseScrollAction()
    # Scroll with valid clicks
    with patch("app.actions.mouse_scroll.desktop_control.scroll", return_value={"success": True}):
        res_scroll = scroll_act.run({"clicks": 3})
        assert res_scroll.success is True


def test_screen_inspection_and_pointing():
    inspect_act = InspectScreenAction()
    with patch("app.actions.inspect_screen.ui_automation.inspect_active_window", return_value={"window_title": "Test Window", "controls": []}):
        res = inspect_act.run({})
        assert res.success is True
        assert res.data["window_title"] == "Test Window"

    point_act = PointToElementAction()
    # Coordinate pointing
    with patch("app.actions.point_to_element.desktop_control.set_cursor_position") as mock_set:
        res_point = point_act.run({"x": 500, "y": 500})
        assert res_point.success is True
        mock_set.assert_called_once_with(500, 500)


def test_capture_screen_privacy_policy(tmp_output_dir):
    act = CaptureScreenAction()
    # Denied without permission
    res_denied = act.run({"permission_granted": False}, confirmed=False)
    assert res_denied.success is False
    assert "permission" in (res_denied.error or res_denied.message).lower()

    # Permitted
    with patch("app.actions.capture_screen.mss.mss") as mock_mss, \
         patch("app.actions.capture_screen.mss.tools.to_png") as mock_to_png:
        mock_sct = MagicMock()
        mock_sct.monitors = [{}, {"left": 0, "top": 0, "width": 100, "height": 100}]
        mock_shot = MagicMock()
        mock_shot.rgb = b"\x00" * (100 * 100 * 3)
        mock_shot.size = (100, 100)
        mock_shot.width = 100
        mock_shot.height = 100
        mock_sct.grab.return_value = mock_shot
        mock_mss.return_value.__enter__.return_value = mock_sct

        res_ok = act.run({"permission_granted": True, "filename": "screenshots/test.png"}, confirmed=True)
        assert res_ok.success is True


# --- File Organization Tests ---

def test_organize_files_confirmation_workflow(tmp_output_dir):
    # Setup files in documents folder
    doc_dir = tmp_output_dir / "docs_to_org"
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "notes.txt").write_text("notes", encoding="utf-8")
    (doc_dir / "budget.xlsx").write_text("data", encoding="utf-8")

    act = OrganizeFilesAction()
    # Step 1: Preview without confirmation
    res_preview = act.run({"folder_path": str(doc_dir)}, confirmed=False)
    assert res_preview.success is False
    assert res_preview.error == "CONFIRMATION_REQUIRED"
    assert "proposed_moves" in res_preview.data
    assert len(res_preview.data["proposed_moves"]) == 2

    # Step 2: Confirmed execution
    res_exec = act.run({"folder_path": str(doc_dir)}, confirmed=True)
    assert res_exec.success is True
    assert res_exec.data["moved_count"] == 2
    assert (doc_dir / "documents" / "notes.txt").exists()
    assert (doc_dir / "spreadsheets" / "budget.xlsx").exists()


# --- Web Research Tests ---

def test_web_research(tmp_output_dir):
    act = WebResearchAction()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '<a class="result__snippet" href="https://docs.python.org/3/whatsnew/3.12.html?utm_source=test">Key new features in Python 3.12.</a>'

    with patch("httpx.Client.get", return_value=mock_resp):
        res = act.run({"query": "Python 3.12 features", "save_report": True})
        assert res.success is True
        assert res.data["sources_count"] >= 1
        sources = [f["url"] for f in res.data["findings"]]
        assert any("utm_source" not in s for s in sources)
        assert res.output_path is not None
        assert Path(res.output_path).exists()


# --- Meeting Assistance Tests ---

def test_meeting_assistance_lifecycle(tmp_output_dir):
    act = MeetingAssistanceAction()
    # Start meeting session
    start_res = act.run({"action": "start", "title": "Sprint Planning"})
    assert start_res.success is True
    session_id = start_res.data["session_id"]
    assert meeting_manager.is_recording

    # Check status
    status_res = act.run({"action": "status"})
    assert status_res.success is True
    assert status_res.data["is_recording"] is True

    # Summarize / Stop
    sum_res = act.run({"action": "summarize"})
    assert sum_res.success is True
    assert not meeting_manager.is_recording


# --- Interpreter Fast-Path Tests for User Scenarios ---

def test_interpreter_fast_path_scenarios():
    interpreter = CommandInterpreter()

    # 1. Excel sheet creation
    plan_excel = interpreter.try_fast_path("create an excel sheet")
    assert plan_excel is not None
    assert plan_excel.actions[0].action_name == "create_spreadsheet"

    plan_budget = interpreter.try_fast_path("create an excel sheet for budget")
    assert plan_budget is not None
    assert plan_budget.actions[0].action_name == "create_spreadsheet"
    assert "Category" in plan_budget.actions[0].parameters["headers"]

    # 2. Word document creation
    plan_word = interpreter.try_fast_path("create a word document about quarterly goals")
    assert plan_word is not None
    assert plan_word.actions[0].action_name == "create_word_document"
    assert "quarterly goals" in plan_word.actions[0].parameters["title"].lower()

    # 3. PowerPoint presentation
    plan_ppt = interpreter.try_fast_path("create a powerpoint presentation about AI agents")
    assert plan_ppt is not None
    assert plan_ppt.actions[0].action_name == "create_presentation"
    assert len(plan_ppt.actions[0].parameters["slides"]) > 0

    # 4. Grocery list voice splitting: "milk, bread"
    plan_groc = interpreter.try_fast_path("grocery list: milk, bread")
    assert plan_groc is not None
    assert plan_groc.actions[0].action_name == "create_grocery_list"
    items = plan_groc.actions[0].parameters["items"]
    assert "milk" in items
    assert "bread" in items
    assert len(items) == 2

    # 5. Application launch
    plan_app = interpreter.try_fast_path("open notepad")
    assert plan_app is not None
    assert plan_app.actions[0].action_name == "open_application"
    assert plan_app.actions[0].parameters["app_name"] == "notepad"

    # 6. Key combo
    plan_keys = interpreter.try_fast_path("press ctrl+c")
    assert plan_keys is not None
    assert plan_keys.actions[0].action_name == "press_keys"
    assert plan_keys.actions[0].parameters["keys"] == ["ctrl", "c"]

    # 7. Screen inspection
    plan_screen = interpreter.try_fast_path("what is on my screen?")
    assert plan_screen is not None
    assert plan_screen.actions[0].action_name == "inspect_screen"
