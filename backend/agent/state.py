from typing import TypedDict


class PodcastState(TypedDict):
    original_prompt: str     # Topic label from user
    source_content: str      # Ingested text (URL/file/paste) — set before graph runs
    research_content: str    # Supplementary notes added during revision
    outline: str             # Episode structure
    draft: str               # Current ALEX:/SAM: formatted script
    critique: str            # Latest critique
    rewrites: int            # Revision counter (starts at 0, increments in revise_draft)
    max_rewrites: int        # User-set ceiling
    target_duration: int     # Target podcast length in minutes (2, 5, 10, or 15)
    tones: list              # One or more of: "briefing", "explainer", "conversational"
    final_script: str        # Approved script (set by finalize node)
    audio_path: str          # Optional local file path (unused in current impl)
