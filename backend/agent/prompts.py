# Approximate spoken-word rate for conversational podcast dialogue.
_WORDS_PER_MINUTE = 130

# Per-tone style instructions injected into outline, draft, and revise prompts.
_TONE_GUIDANCE = {
    "briefing": (
        "Briefing (fast, factual): Get straight to the point — no small talk or filler. "
        "ALEX delivers facts clearly and efficiently; SAM asks sharp, clarifying questions that keep the pace up. "
        "Avoid lengthy analogies; prefer direct statements and concrete figures. "
        "Each exchange should cover one point, one challenge, then move on."
    ),
    "explainer": (
        "Explainer (clear, structured): Build understanding step by step — introduce concepts before applying them. "
        "Use analogies, real-world examples, and 'what this means in practice' moments. "
        "SAM's questions should deepen comprehension ('Can you break that down?', 'What's the mechanism here?'). "
        "Transitions should make the logical flow obvious to a first-time listener."
    ),
    "conversational": (
        "Conversational (casual, engaging): Sound like two people genuinely talking, not presenting. "
        "Use natural speech patterns — contractions, reactions, the occasional 'Wait, really?'. "
        "Both hosts can express opinions and surprise with personality. "
        "Light humor and brief tangents are welcome if they add energy."
    ),
}


def build_tone_guidance(tones: list[str]) -> str:
    """Return a 'Tone' section to embed in prompts based on the selected tones."""
    valid = [t for t in tones if t in _TONE_GUIDANCE]
    if not valid:
        valid = ["conversational"]

    if len(valid) == 1:
        header = "Tone:"
    else:
        header = "Tone (blend all of the following):"

    lines = [header] + [f"- {_TONE_GUIDANCE[t]}" for t in valid]
    return "\n".join(lines)


def _duration_params(target_minutes: int) -> dict:
    """Derive prompt parameters from the target length in minutes."""
    words = target_minutes * _WORDS_PER_MINUTE
    # Word-count range: ±15 %
    word_low  = round(words * 0.85 / 50) * 50
    word_high = round(words * 1.15 / 50) * 50

    if target_minutes <= 2:
        segments = "1-2"
    elif target_minutes <= 5:
        segments = "2-3"
    elif target_minutes <= 10:
        segments = "4-5"
    else:
        segments = "6-7"

    return {
        "minutes":   target_minutes,
        "word_low":  word_low,
        "word_high": word_high,
        "segments":  segments,
    }


def build_outline_prompt(target_minutes: int, tones: list[str]) -> str:
    p = _duration_params(target_minutes)
    tone_section = build_tone_guidance(tones)
    return f"""You are a podcast producer creating an outline for a conversational podcast episode.

The podcast has two hosts:
- ALEX: The analyst. Knowledgeable, enthusiastic, explains concepts clearly and with depth.
- SAM: The skeptic. Asks tough questions, challenges assumptions, and represents the curious listener.

{tone_section}

Based on the source material provided, create a structured outline for a {p['minutes']}-minute podcast episode.

The outline must include:
1. A compelling episode title
2. An opening hook that draws listeners in immediately
3. {p['segments']} main discussion segments, each with:
   - The key point to cover
   - Which host introduces the segment
   - A sharp question SAM challenges ALEX with
4. A closing takeaway or call-to-action

Keep the outline concise — it is a planning tool, not the script itself."""


def build_draft_prompt(target_minutes: int, tones: list[str]) -> str:
    p = _duration_params(target_minutes)
    tone_section = build_tone_guidance(tones)
    return f"""You are writing a podcast script for a conversational two-host show.

The hosts are:
- ALEX: The analyst. Knowledgeable, enthusiastic, explains concepts clearly.
- SAM: The skeptic. Asks tough questions, pushes back, represents the listener.

STRICT FORMAT RULES — every single line must follow this pattern:
ALEX: [dialogue here]
SAM: [dialogue here]

Absolutely no exceptions:
- No stage directions (e.g., [laughs], [pauses])
- No music cues or scene headers
- No narrator lines
- No blank speaker labels

{tone_section}

Length: {p['minutes']} minutes of spoken audio (~{p['word_low']}-{p['word_high']} words total). \
Neither host speaks more than 3 lines in a row before the other responds.

Base the script on the outline and source material provided."""


def build_revise_prompt(target_minutes: int, tones: list[str]) -> str:
    p = _duration_params(target_minutes)
    tone_section = build_tone_guidance(tones)
    return f"""You are rewriting a podcast script based on specific editorial feedback.

Apply ALL the feedback points to produce a meaningfully improved version.

STRICT FORMAT RULES — every single line must follow this pattern:
ALEX: [dialogue here]
SAM: [dialogue here]

Absolutely no exceptions:
- No stage directions
- No music cues or scene headers
- No narrator lines

{tone_section}

Length: {p['minutes']} minutes (~{p['word_low']}-{p['word_high']} words). \
Neither host speaks more than 3 lines in a row.

Do not just make cosmetic changes — address the specific issues raised in the feedback."""


# Critique prompt does not reference length or tone — it evaluates what's there.
CRITIQUE_PROMPT = """You are a podcast editor reviewing a script draft. Be honest and specific.

Evaluate the script on these five criteria:

1. FORMAT COMPLIANCE: Are ALL lines in "ALEX: ..." or "SAM: ..." format? Flag any violations.
2. ACCURACY: Does the content faithfully represent the source material? Note any errors or omissions.
3. DIALOGUE QUALITY: Does it sound natural and conversational, or stiff and lecture-like?
4. BALANCE: Does SAM ask genuinely challenging questions, or just softballs?
5. ENGAGEMENT: Are there clear moments of tension, surprise, or revelation?

For each issue, quote the specific problematic section and explain exactly what should change.
Be direct — vague feedback is useless. If a section is good, say so briefly and move on."""
