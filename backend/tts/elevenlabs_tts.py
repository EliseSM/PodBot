from .base import TTSProvider, HostName


# Placeholder ElevenLabs voice IDs — replace with real ones from your account.
HOST_VOICES: dict[str, str] = {
    "ALEX": "21m00Tcm4TlvDq8ikWAM",  # Replace with chosen voice ID
    "SAM": "AZnzlk1XvdvUeBnXmlld",   # Replace with chosen voice ID
}


class ElevenLabsTTSProvider(TTSProvider):
    """
    TTS provider stub for ElevenLabs.

    To implement:
      1. pip install elevenlabs
      2. Replace NotImplementedError with actual API calls
      3. Swap instantiation in backend/main.py

    The interface is identical to OpenAITTSProvider — synthesize() returns
    raw MP3 bytes and get_voice_for_host() returns a voice ID string.
    """

    def __init__(self, api_key: str):
        self._api_key = api_key

    def synthesize(self, text: str, voice_id: str) -> bytes:
        raise NotImplementedError(
            "ElevenLabs TTS not yet implemented. "
            "See backend/tts/elevenlabs_tts.py for instructions."
        )

    def get_voice_for_host(self, host: HostName) -> str:
        return HOST_VOICES[host]
