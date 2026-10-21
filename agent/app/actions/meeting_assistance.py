"""Action: meeting_assistance - Starts/stops meeting recording, adds notes, and reviews history."""

from typing import Any
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.services.meeting_manager import meeting_manager
from app.logging_config import get_logger

logger = get_logger("flash.action.meeting_assistance")


class MeetingAssistanceAction(BaseAction):
    name = "meeting_assistance"
    description = "Controls meeting recording assistance, transcript capture, summary generation, and notes history."
    requires_confirmation = False
    parameters_schema = {
        "command": {
            "type": "string",
            "required": True,
            "description": "One of: 'start', 'stop', 'status', 'add_transcript', 'list'.",
        },
        "title": {
            "type": "string",
            "required": False,
            "description": "Meeting title for 'start' command.",
        },
        "text": {
            "type": "string",
            "required": False,
            "description": "Transcript text snippet for 'add_transcript'.",
        },
        "speaker": {
            "type": "string",
            "required": False,
            "description": "Speaker label (e.g. 'Speaker A', 'Alice') for 'add_transcript'.",
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        cmd = str(parameters.get("command") or parameters.get("action") or "status").strip().lower()

        if cmd in ("start", "record"):
            title = parameters.get("title")
            session = meeting_manager.start_session(title=title)
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Started meeting assistance session '{session.title}' [{session.session_id}]. Recording is active.",
                output_path=session.notes_path,
                data={"session_id": session.session_id, "title": session.title, "status": "recording"},
            )

        elif cmd in ("stop", "summarize"):
            session = meeting_manager.stop_session()
            if not session:
                return ActionResponse(
                    success=False,
                    action=self.name,
                    message="No active meeting session to stop.",
                    error="NO_ACTIVE_SESSION",
                )
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Stopped meeting session '{session.title}'. Notes saved to '{session.notes_path}'.",
                output_path=session.notes_path,
                data={
                    "session_id": session.session_id,
                    "title": session.title,
                    "turns_count": len(session.segments),
                    "summary": session.summary,
                    "action_items": session.action_items,
                },
            )

        elif cmd == "add_transcript":
            text = str(parameters.get("text", "")).strip()
            speaker = parameters.get("speaker")
            if not text:
                return ActionResponse(
                    success=False,
                    action=self.name,
                    message="Parameter 'text' is required for 'add_transcript'.",
                    error="MISSING_TEXT",
                )
            seg = meeting_manager.add_segment(text=text, speaker=speaker)
            if not seg:
                return ActionResponse(
                    success=False,
                    action=self.name,
                    message="Cannot add transcript segment: no active meeting session is running. Call start first.",
                    error="NO_ACTIVE_SESSION",
                )
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Added transcript turn from {seg.speaker}.",
                data={"speaker": seg.speaker, "text": seg.text, "time": seg.timestamp_str},
            )

        elif cmd == "list":
            sessions = meeting_manager.list_sessions()
            return ActionResponse(
                success=True,
                action=self.name,
                message=f"Retrieved {len(sessions)} recorded meeting sessions.",
                data={"sessions": sessions},
            )

        elif cmd == "status":
            act = meeting_manager.active_session
            if act and act.is_recording:
                return ActionResponse(
                    success=True,
                    action=self.name,
                    message=f"Meeting recording in progress: '{act.title}' ({len(act.segments)} turns).",
                    data={"is_recording": True, "session_id": act.session_id, "title": act.title},
                )
            else:
                return ActionResponse(
                    success=True,
                    action=self.name,
                    message="No active meeting recording currently running.",
                    data={"is_recording": False},
                )

        else:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Unknown meeting command '{cmd}'. Must be one of: start, stop, status, add_transcript, list.",
                error="UNKNOWN_COMMAND",
            )
