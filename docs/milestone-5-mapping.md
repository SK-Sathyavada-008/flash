# Milestone 5: Feature-to-Implementation Mapping

## 1. Executive Overview
This document maps every original Bluey / GooglyMac feature and user-requested capability to its verified Windows desktop implementation in Flash.

---

## 2. Feature Mapping Matrix

| Original Feature / Requirement | Source File (Original) | Target Implementation (Flash Windows) | Implementation Mechanism | Status |
|---|---|---|---|---|
| **Mouse Click / Double / Right** | `Mac/ComputerControl.swift:51-64` | `app/actions/mouse_click.py`, `app/windows/desktop_control.py` | Win32 `SendInput` / `mouse_event` with cursor position restore | Ready to implement |
| **Mouse Drag & Drop** | `Mac/ComputerControl.swift:65-76` | `app/actions/mouse_drag.py`, `app/windows/desktop_control.py` | Win32 `SendInput` drag sequence (`MOUSEEVENTF_LEFTDOWN` -> `MOVE` -> `LEFTUP`) | Ready to implement |
| **Mouse Scroll** | `Mac/ComputerControl.swift:78-90` | `app/actions/mouse_scroll.py`, `app/windows/desktop_control.py` | Win32 `mouse_event(MOUSEEVENTF_WHEEL)` smooth increments | Ready to implement |
| **Keyboard Unicode Typing** | `Mac/ComputerControl.swift:101-143` | `app/actions/type_text.py`, `app/windows/desktop_control.py` | Win32 `SendInput` with `KEYEVENTF_UNICODE` | Implemented, enhanced |
| **Keyboard Shortcut Combos** | `Mac/ComputerControl.swift:155-216` | `app/actions/press_keys.py`, `app/windows/desktop_control.py` | Win32 `VK_*` virtual key mapper (`Ctrl`, `Alt`, `Shift`, `Win`, etc.) | Ready to implement |
| **Open Application** | `Mac/ComputerControl.swift:221-255` | `app/actions/open_application.py` | `psutil` process check, `SetForegroundWindow`, `os.startfile`, `Start-Process` | Ready to implement |
| **Accessible Controls Reader** | `Mac/ControlsReader.swift:1-134` | `app/windows/ui_automation.py`, `app/actions/inspect_screen.py` | Windows UI Automation (`uiautomation` / `CUIAutomation`) | Ready to implement |
| **Focused Field & Password Shield** | `Mac/ControlsReader.swift:76-84` | `app/windows/ui_automation.py` | `IsPassword` property check, blocks automated entry into password fields | Ready to implement |
| **Screen Reading & Targets** | `Mac/ScreenReader.swift:1-147` | `app/windows/screen_reader.py`, `app/actions/inspect_screen.py` | UI Automation control tree + screen bounding boxes `@x,y` normalized grid | Ready to implement |
| **Screen Pointing** | `Mac/CursorOverlay.swift:1-200` | `app/actions/point_to_element.py` | UI Automation element centroid resolution + mouse positioning | Ready to implement |
| **Screenshot with Privacy** | `Mac/ScreenReader.swift:76-98` | `app/actions/capture_screen.py` | `mss` display capture with explicit user confirmation and workspace storage | Ready to implement |
| **Web Research Engine** | `Mac/WebResearch.swift:1-88` | `app/actions/web_research.py` | DuckDuckGo / Provider search + content scraping + structured synthesis | Ready to implement |
| **Meeting Notes & Audio Chunks** | `Mac/MeetingNotes.swift:1-195` | `app/actions/meeting_assistance.py`, `app/services/meeting_manager.py` | 5-minute audio segments, timestamped transcripts, summaries, action items | Ready to implement |
| **Excel Spreadsheet (`.xlsx`)** | New Flash Capability | `app/actions/create_spreadsheet.py` | `openpyxl` with styled headers, auto-widths, formulas (`=SUM`, `=AVERAGE`) | Fix prompt routing & enhance |
| **Word Document (`.docx`)** | New Flash Capability | `app/actions/create_word_document.py` | `python-docx` with titles, headings, bullet lists, callout tables | Ready to implement |
| **PowerPoint Presentation (`.pptx`)** | New Flash Capability | `app/actions/create_presentation.py` | `python-pptx` with title slide, content slides, bullet items | Ready to implement |
| **Grocery List (Voice Split Fix)** | Bugfix & Enhancement | `app/actions/create_grocery_list.py`, `app/ai/interpreter.py` | Multi-token voice parsing (commas, 'and', spaces), prevents merging | Fix & test |
| **File Organization** | Natural-Language Task | `app/actions/organize_files.py` | Propose file categorization, preview changes, require user confirmation | Ready to implement |
| **Browser Automation** | Advanced Task | `app/actions/browser_automate.py` | `playwright` headless/headed browser navigation, fill, click, extract | Ready to implement |
| **Multi-step Workflow & Recovery**| Core Orchestrator | `app/ai/orchestrator.py` | Retry transient failures with exponential backoff, detailed step reporting | Ready to implement |
| **Safety & Emergency Stop** | System Guardrails | `app/security.py`, `app/service.py` | Global `emergency_stop`, destructive shortcut refusal, safe path sandbox | Existing & maintained |
