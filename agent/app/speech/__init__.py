"""Speech Synthesis package for Flash Agent."""

from app.speech.base import BaseSpeechProvider, SpeechResult
from app.speech.local_provider import LocalSpeechProvider
from app.speech.elevenlabs_provider import ElevenLabsSpeechProvider
from app.config import settings


def get_speech_provider() -> BaseSpeechProvider:
    """Return active speech synthesis provider based on settings."""
    if settings.elevenlabs_api_key and settings.speech_provider.lower() != "local_only":
        return ElevenLabsSpeechProvider()
    return LocalSpeechProvider()


__all__ = [
    "BaseSpeechProvider",
    "SpeechResult",
    "LocalSpeechProvider",
    "ElevenLabsSpeechProvider",
    "get_speech_provider",
]
