from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


HostName = Literal["ALEX", "SAM"]


@dataclass
class DialogueLine:
    host: HostName
    text: str


class TTSProvider(ABC):
    """
    Abstract base class for TTS providers.

    To add a new provider (e.g. ElevenLabs):
      1. Subclass TTSProvider
      2. Implement synthesize() and get_voice_for_host()
      3. Swap the instantiation in backend/main.py
    """

    @abstractmethod
    def synthesize(self, text: str, voice_id: str) -> bytes:
        """
        Synthesize text to audio.

        Returns raw MP3 bytes.
        voice_id is provider-specific (e.g. "alloy" for OpenAI, a UUID for ElevenLabs).
        """
        ...

    @abstractmethod
    def get_voice_for_host(self, host: HostName) -> str:
        """
        Returns the provider-specific voice ID for a given host name.
        """
        ...
