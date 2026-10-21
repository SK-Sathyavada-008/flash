"""Action: speak_text - Synthesizes spoken audio for text responses using active speech provider."""

from typing import Any, Optional
from app.actions.base import BaseAction
from app.models import ActionResponse
from app.speech import get_speech_provider
from app.logging_config import get_logger

logger = get_logger("flash.action.speak_text")


class SpeakTextAction(BaseAction):
    name = "speak_text"
    description = "Synthesizes spoken audio using ElevenLabs or offline local voice engine."
    requires_confirmation = False
    parameters_schema = {
        "text": {
            "type": "string",
            "required": True,
            "description": "Text to synthesize into speech.",
        },
        "voice_id": {
            "type": "string",
            "required": False,
            "description": "Optional voice ID.",
        },
    }

    def run(self, parameters: dict[str, Any], confirmed: bool = False) -> ActionResponse:
        text = parameters.get("text")
        if not text or not isinstance(text, str):
            return ActionResponse(
                success=False,
                action=self.name,
                message="Parameter 'text' is required and must be a string.",
                error="MISSING_PARAMETER",
            )

        clean_text = text.strip()
        voice_id = parameters.get("voice_id")

        provider = get_speech_provider()
        res = provider.synthesize_speech(clean_text, voice_id=voice_id)

        if not res.success:
            return ActionResponse(
                success=False,
                action=self.name,
                message=f"Speech synthesis failed: {res.message}",
                error=res.error or "SYNTHESIS_FAILED",
            )

        return ActionResponse(
            success=True,
            action=self.name,
            message=res.message,
            output_path=res.audio_path,
            data={
                "provider": res.provider,
                "character_count": res.character_count,
                "audio_format": res.audio_format,
            },
        )
