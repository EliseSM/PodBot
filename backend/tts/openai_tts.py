from openai import OpenAI
from .base import TTSProvider, HostName


# Voice assignments for each host.
# OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
HOST_VOICES: dict[str, str] = {
    "ALEX": "alloy",   # Neutral, clear, analytical
    "SAM": "echo",     # Slightly warmer, distinct from ALEX
}


class OpenAITTSProvider(TTSProvider):
    """
    TTS provider backed by the OpenAI audio.speech API.

    Uses .content to retrieve raw MP3 bytes in memory per the SDK docs
    for openai==1.109.1 (BinaryAPIResponse).
    """

    def __init__(self, api_key: str, model: str = "tts-1", speed: float = 1.0):
        self._client = OpenAI(api_key=api_key)
        self._model = model      # "tts-1" or "tts-1-hd" for higher quality
        self._speed = speed

    def synthesize(self, text: str, voice_id: str) -> bytes:
        response = self._client.audio.speech.create(
            model=self._model,
            voice=voice_id,
            input=text,
            response_format="mp3",
            speed=self._speed,
        )
        return response.content  # Raw MP3 bytes (BinaryAPIResponse.content)

    def get_voice_for_host(self, host: HostName) -> str:
        return HOST_VOICES[host]
