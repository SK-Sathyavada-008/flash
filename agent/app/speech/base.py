"""Base interface for Flash Speech Synthesis and Audio Providers."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel


class SpeechResult(BaseModel):
    """Result of speech synthesis."""
    success: bool
    provider: str
    audio_path: Optional[str] = None
    audio_format: str = "mp3"
    audio_bytes: Optional[bytes] = None
    duration_seconds: Optional[float] = None
    character_count: int = 0
    message: str = ""
    error: Optional[str] = None


class BaseSpeechProvider(ABC):
    """Abstract base class for all speech synthesis providers."""

    name: str = "base"

    @abstractmethod
    def synthesize_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_filename: Optional[str] = None,
    ) -> SpeechResult:
        """Synthesize spoken audio for the given text.
        
        Args:
            text: Text to speak.
            voice_id: Optional voice ID.
            output_filename: Optional custom target filename.
            
        Returns:
            SpeechResult with audio path or stream metadata.
        """
        pass

    @abstractmethod
    def get_provider_info(self) -> dict[str, Any]:
        """Return provider capability metadata and operational status."""
        pass
