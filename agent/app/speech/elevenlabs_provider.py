"""ElevenLabs Speech Provider for Flash Agent.

Integrates ElevenLabs official Text-to-Speech API for expressive, high-fidelity
sloth vocal responses. Requires ELEVENLABS_API_KEY. Falls back to LocalSpeechProvider
when unconfigured or offline.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import httpx

from app.speech.base import BaseSpeechProvider, SpeechResult
from app.speech.local_provider import LocalSpeechProvider
from app.config import settings
from app.security import resolve_safe_path
from app.logging_config import get_logger

logger = get_logger("flash.speech.elevenlabs")

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"


class ElevenLabsSpeechProvider(BaseSpeechProvider):
    name = "elevenlabs"

    def __init__(self, api_key: Optional[str] = None, default_voice_id: Optional[str] = None) -> None:
        self.api_key = api_key if api_key is not None else settings.elevenlabs_api_key
        self.default_voice_id = default_voice_id or settings.elevenlabs_voice_id
        self._fallback = LocalSpeechProvider()

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def get_provider_name(self) -> str:
        return self.name

    def requires_cloud(self) -> bool:
        return True

    def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_filename: Optional[str] = None,
    ) -> SpeechResult:
        return self.synthesize_speech(text, voice_id, output_filename)

    def synthesize_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_filename: Optional[str] = None,
    ) -> SpeechResult:
        clean_text = text.strip()
        if not clean_text:
            return SpeechResult(
                success=False,
                provider=self.name,
                message="Text to speak cannot be empty.",
                error="EMPTY_TEXT",
            )

        if not self.is_configured:
            logger.info("ElevenLabs API key not configured; falling back to local speech provider.")
            fallback_res = self._fallback.synthesize_speech(clean_text, voice_id, output_filename)
            fallback_res.message = f"[ElevenLabs unconfigured] {fallback_res.message}"
            return fallback_res

        voice = voice_id or self.default_voice_id
        endpoint = f"{ELEVENLABS_TTS_URL}/{voice}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

        payload = {
            "text": clean_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.65,
                "similarity_boost": 0.75,
            },
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_name = output_filename or f"audio/elevenlabs_{timestamp}.mp3"

        is_safe, resolved_path, err = resolve_safe_path(
            target_name,
            must_exist=False,
            create_parent=True,
            allowed_extensions={".mp3", ".wav"},
        )

        if not is_safe or not resolved_path:
            return SpeechResult(
                success=False,
                provider=self.name,
                message=f"Path denied: {err}",
                error="PATH_ACCESS_DENIED",
            )

        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(endpoint, json=payload, headers=headers)

                if resp.status_code == 200:
                    resolved_path.write_bytes(resp.content)
                    return SpeechResult(
                        success=True,
                        provider=self.name,
                        audio_path=str(resolved_path),
                        audio_format="mp3",
                        audio_bytes=resp.content,
                        character_count=len(clean_text),
                        message=f"Successfully synthesized audio using ElevenLabs voice '{voice}'.",
                    )
                else:
                    error_detail = resp.text[:200]
                    logger.warning("ElevenLabs API returned %d: %s. Using local fallback.", resp.status_code, error_detail)
                    fallback_res = self._fallback.synthesize_speech(clean_text, voice_id, output_filename)
                    fallback_res.message = f"[ElevenLabs HTTP {resp.status_code}] {fallback_res.message}"
                    return fallback_res

        except Exception as e:
            logger.error("ElevenLabs request failed: %s. Falling back to local.", e)
            fallback_res = self._fallback.synthesize_speech(clean_text, voice_id, output_filename)
            fallback_res.message = f"[ElevenLabs Error: {e}] {fallback_res.message}"
            return fallback_res

    def get_provider_info(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": self.is_configured,
            "voice_id": self.default_voice_id,
            "offline": False,
            "requires_api_key": True,
            "privacy": "Only explicit spoken responses are sent to ElevenLabs API over HTTPS. No mic streams.",
        }
