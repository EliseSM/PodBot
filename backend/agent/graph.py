from functools import partial

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.language_models import BaseChatModel

from .state import PodcastState
from .nodes import create_outline, create_draft, critique_draft, revise_draft, finalize, should_continue


def build_graph(llm: BaseChatModel):
    """
    Builds and compiles the LangGraph podcast generation graph.

    Graph flow:
        create_outline → create_draft → [should_continue]
                              ↑               │              │
                              │         < max_rewrites  >= max_rewrites
                              │               │              │
                         revise_draft ← critique_draft    finalize → END

    The LLM is injected via functools.partial so node functions remain pure
    and testable without a graph context.

    Each job should create its own graph instance (and thus its own
    InMemorySaver) to keep state isolated between concurrent requests.
    """
    bind = lambda fn: partial(fn, llm=llm)

    graph = StateGraph(PodcastState)

    graph.add_node("create_outline", bind(create_outline))
    graph.add_node("create_draft",   bind(create_draft))
    graph.add_node("critique_draft", bind(critique_draft))
    graph.add_node("revise_draft",   bind(revise_draft))
    graph.add_node("finalize",       finalize)

    graph.set_entry_point("create_outline")
    graph.add_edge("create_outline", "create_draft")

    # After create_draft: critique if rewrites remain, else finalize
    graph.add_conditional_edges(
        "create_draft",
        should_continue,
        {"critique": "critique_draft", "finalize": "finalize"},
    )

    graph.add_edge("critique_draft", "revise_draft")

    # After revise_draft: critique again if rewrites remain, else finalize
    graph.add_conditional_edges(
        "revise_draft",
        should_continue,
        {"critique": "critique_draft", "finalize": "finalize"},
    )

    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=InMemorySaver())
