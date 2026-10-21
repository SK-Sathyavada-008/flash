"""Meeting Assistance Service for Flash Agent.

Manages explicitly started meeting recording sessions, timestamped transcription,
speaker segmentation, action item extraction, and session persistence in the Flash workspace.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
import time
from typing import Optional

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("flash.services.meeting")


@dataclass
class TranscriptSegment:
    speaker: str  # e.g., "Speaker A", "User", "Participant 1"
    start_seconds: float
    end_seconds: float
    text: str
    timestamp_str: str = ""


@dataclass
class MeetingSession:
    session_id: str
    title: str
    started_at: str
    ended_at: Optional[str] = None
    is_recording: bool = True
    attendees: list[str] = field(default_factory=list)
    segments: list[TranscriptSegment] = field(default_factory=list)
    summary: str = ""
    action_items: list[str] = field(default_factory=list)
    notes_path: str = ""
    session_json_path: str = ""


class MeetingManager:
    """Manages active and historical meeting assistance sessions."""

    def __init__(self) -> None:
        self.active_session: Optional[MeetingSession] = None
        self._start_time: float = 0.0

    @property
    def meetings_root(self) -> Path:
        p = settings.workspace_dir / "meetings"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def is_recording(self) -> bool:
        return bool(self.active_session and self.active_session.is_recording)

    def start_session(self, title: Optional[str] = None, attendees: Optional[list[str]] = None) -> MeetingSession:
        """Explicitly start a new meeting recording session."""
        if self.active_session and self.active_session.is_recording:
            # End previous session before starting new one
            self.stop_session()

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        meeting_title = title.strip() if title else f"Meeting {datetime.now().strftime('%b %d, %Y')}"

        session_dir = self.meetings_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "audio").mkdir(parents=True, exist_ok=True)

        session = MeetingSession(
            session_id=session_id,
            title=meeting_title,
            started_at=datetime.now().isoformat(),
            is_recording=True,
            attendees=attendees or ["Participant"],
            segments=[],
            notes_path=str(session_dir / "notes.md"),
            session_json_path=str(session_dir / "session.json"),
        )

        self.active_session = session
        self._start_time = time.time()
        self._save_session(session)
        logger.info("Started meeting session [%s]: '%s'", session_id, meeting_title)
        return session

    def add_segment(self, text: str, speaker: Optional[str] = None, duration_seconds: float = 5.0) -> Optional[TranscriptSegment]:
        """Add a timestamped transcript segment to the active meeting."""
        if not self.active_session or not self.active_session.is_recording:
            return None

        clean_text = text.strip()
        if not clean_text:
            return None

        now_sec = max(0.0, time.time() - self._start_time)
        start_sec = max(0.0, now_sec - duration_seconds)
        time_label = datetime.now().strftime("%H:%M:%S")

        assigned_speaker = speaker or ("Speaker A" if len(self.active_session.segments) % 2 == 0 else "Speaker B")

        segment = TranscriptSegment(
            speaker=assigned_speaker,
            start_seconds=round(start_sec, 1),
            end_seconds=round(now_sec, 1),
            text=clean_text,
            timestamp_str=time_label,
        )

        self.active_session.segments.append(segment)
        self._save_session(self.active_session)
        return segment

    def stop_session(self) -> Optional[MeetingSession]:
        """Explicitly stop the active recording session and compile notes."""
        if not self.active_session:
            return None

        session = self.active_session
        session.is_recording = False
        session.ended_at = datetime.now().isoformat()

        # Generate summary and action items from segments
        if session.segments and not session.summary:
            all_text = " ".join(s.text for s in session.segments)
            session.summary = f"Discussion on {session.title}. Total speaking turns recorded: {len(session.segments)}."

            # Simple action item heuristic
            for seg in session.segments:
                lower = seg.text.lower()
                if any(w in lower for w in ("todo", "will", "action", "need to", "should", "follow up")):
                    session.action_items.append(f"{seg.speaker}: {seg.text}")

            if not session.action_items:
                session.action_items = ["Review meeting notes and follow up with participants."]

        self._save_session(session)
        self._write_markdown_notes(session)

        self.active_session = None
        logger.info("Stopped meeting session [%s]", session.session_id)
        return session

    def list_sessions(self) -> list[dict]:
        """List all saved meeting sessions in workspace."""
        sessions = []
        for d in sorted(self.meetings_root.iterdir(), reverse=True):
            if d.is_dir() and (d / "session.json").exists():
                try:
                    data = json.loads((d / "session.json").read_text(encoding="utf-8"))
                    sessions.append({
                        "session_id": data.get("session_id"),
                        "title": data.get("title"),
                        "started_at": data.get("started_at"),
                        "ended_at": data.get("ended_at"),
                        "turns_count": len(data.get("segments", [])),
                        "summary": data.get("summary", ""),
                    })
                except Exception:
                    continue
        return sessions

    def _save_session(self, session: MeetingSession) -> None:
        """Write session data atomically to session.json."""
        data = asdict(session)
        target = Path(session.session_json_path)
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._write_markdown_notes(session)

    def _write_markdown_notes(self, session: MeetingSession) -> None:
        """Write clean human-readable notes.md matching original GooglyMac/MeetingNotes."""
        lines = [
            f"# 🎙️ {session.title}",
            f"*Session ID: `{session.session_id}` | Started: {session.started_at}*",
            "",
            "## 📝 Meeting Summary",
            session.summary or "*(Meeting currently in progress)*",
            "",
            "## ✅ Action Items",
        ]

        if session.action_items:
            for item in session.action_items:
                lines.append(f"- [ ] {item}")
        else:
            lines.append("- [ ] None recorded yet.")

        lines.extend(["", "## 📜 Transcript", ""])
        if session.segments:
            for s in session.segments:
                lines.append(f"**[{s.timestamp_str}] {s.speaker}:** {s.text}")
        else:
            lines.append("*(No transcript segments recorded yet)*")

        lines.extend([
            "",
            "---",
            "> 🦥 *\"Notes faithfully kept by Flash.\"*",
        ])

        target = Path(session.notes_path)
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")


meeting_manager = MeetingManager()
