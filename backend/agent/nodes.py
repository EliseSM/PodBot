from functools import partial
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from .state import PodcastState
from .prompts import OUTLINE_PROMPT, DRAFT_PROMPT, CRITIQUE_PROMPT, REVISE_PROMPT

# Truncation limits — keeps token usage manageable while preserving key content.
# GPT-4o and Claude Sonnet both support 128k context; these are conservative.
SOURCE_LIMIT_FULL = 15_000   # chars — used where source is the primary input
SOURCE_LIMIT_SHORT = 5_000   # chars — used as accuracy reference in critique/revise


def create_outline(state: PodcastState, llm: BaseChatModel) -> dict:
    """Creates a structured episode outline from the source content."""
    messages = [
        SystemMessage(content=OUTLINE_PROMPT),
        HumanMessage(content=(
            f"Topic: {state['original_prompt']}\n\n"
            f"Source material:\n{state['source_content'][:SOURCE_LIMIT_FULL]}"
        )),
    ]
    response = llm.invoke(messages)
    return {"outline": response.content}


def create_draft(state: PodcastState, llm: BaseChatModel) -> dict:
    """Writes the first ALEX:/SAM: formatted podcast script from the outline."""
    messages = [
        SystemMessage(content=DRAFT_PROMPT),
        HumanMessage(content=(
            f"Outline:\n{state['outline']}\n\n"
            f"Source material:\n{state['source_content'][:SOURCE_LIMIT_FULL]}"
        )),
    ]
    response = llm.invoke(messages)
    return {"draft": response.content}


def critique_draft(state: PodcastState, llm: BaseChatModel) -> dict:
    """Critiques the current draft for format, accuracy, dialogue quality, and engagement."""
    messages = [
        SystemMessage(content=CRITIQUE_PROMPT),
        HumanMessage(content=(
            f"Script to critique:\n{state['draft']}\n\n"
            f"Source material (for accuracy check):\n{state['source_content'][:SOURCE_LIMIT_SHORT]}"
        )),
    ]
    response = llm.invoke(messages)
    return {"critique": response.content}


def revise_draft(state: PodcastState, llm: BaseChatModel) -> dict:
    """Rewrites the draft applying all critique feedback. Increments the rewrite counter."""
    messages = [
        SystemMessage(content=REVISE_PROMPT),
        HumanMessage(content=(
            f"Original script:\n{state['draft']}\n\n"
            f"Editorial feedback:\n{state['critique']}\n\n"
            f"Source material (for accuracy):\n{state['source_content'][:SOURCE_LIMIT_SHORT]}"
        )),
    ]
    response = llm.invoke(messages)
    return {"draft": response.content, "rewrites": state["rewrites"] + 1}


def finalize(state: PodcastState) -> dict:
    """Copies the current draft to final_script, ending the agent loop."""
    return {"final_script": state["draft"]}


def should_continue(state: PodcastState) -> str:
    """
    Conditional edge function.
    Returns "critique" if more rewrites are allowed, "finalize" otherwise.
    """
    if state["rewrites"] < state["max_rewrites"]:
        return "critique"
    return "finalize"
