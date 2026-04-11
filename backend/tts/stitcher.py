import io
import re
from pydub import AudioSegment  # requires ffmpeg on system PATH
from .base import TTSProvider, DialogueLine, HostName


def parse_script(script: str) -> list[DialogueLine]:
    """
    Parses a podcast script into an ordered list of DialogueLine objects.

    Expects lines formatted as:
        ALEX: some dialogue here
        SAM: some response here

    Lines that don't match are silently skipped.
    """
    pattern = re.compile(r"^(ALEX|SAM):\s+(.+)$", re.MULTILINE)
    return [
        DialogueLine(host=m.group(1), text=m.group(2).strip())
        for m in pattern.finditer(script)
    ]


def generate_audio(
    script: str,
    provider: TTSProvider,
    silence_ms: int = 400,
) -> bytes:
    """
    Full pipeline: script text → per-line TTS synthesis → stitched MP3 bytes.

    Each ALEX/SAM dialogue line is synthesized separately using the provider,
    then concatenated with silence_ms milliseconds of silence between turns.

    Returns raw MP3 bytes of the complete episode (no temp files written).

    Note: TTS calls are sequential. A 15-minute episode (~100 lines) may take
    several minutes depending on API latency.
    """
    lines = parse_script(script)
    if not lines:
        raise ValueError(
            "No parseable ALEX:/SAM: dialogue lines found in script. "
            "Check that the agent produced correctly formatted output."
        )

    combined = AudioSegment.empty()
    gap = AudioSegment.silent(duration=silence_ms)

    for i, line in enumerate(lines):
        voice_id = provider.get_voice_for_host(line.host)
        mp3_bytes = provider.synthesize(line.text, voice_id)
        segment = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
        combined += segment
        if i < len(lines) - 1:
            combined += gap

    buffer = io.BytesIO()
    combined.export(buffer, format="mp3")
    return buffer.getvalue()
