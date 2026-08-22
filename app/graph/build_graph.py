"""Builds the LangGraph StateGraph for the AI test case generation pipeline.

Graph shape (mirrors the High-Level Architecture in project.md), with error
handling, pattern-score confirmation, optional RAG retrieval, and
retry-capped human review added on top:

    START -> aha_extractor -> preprocessing -> pattern_scoring
        --(conformant)---------------------------------> llm_generation
        --(partial/divergent)--> confirm_low_score
            --(user aborts)-----------------------------> error_handler -> END
            --(user continues)--------------------------> rag_retrieval -> llm_generation
        -> human_review --(approved)--------> testrail_publish -> END
                        --(rejected, retries left)--> llm_generation (retry loop)
                        --(rejected, retries exhausted)--> error_handler -> END
        (any node error at any point) --> error_handler -> END

`pattern_scoring` scores the preprocessed ticket against company patterns
and completeness (see `app/nodes/pattern_scoring.py`), logging the score
before the pipeline proceeds. Anything less than fully "conformant" pauses
at `confirm_low_score` (`app/nodes/confirm_low_score.py`) so a human can
decide whether to continue with a possibly incomplete feature ticket.
`decide_rag_usage` is the routing "tool" that makes `rag_retrieval` run for
every weak (non-conformant) ticket - "partial" or "divergent" - so RAG can
supply the company knowledge about the ticket's problem that the weak
ticket is missing; only a "conformant" ticket skips the retrieval hop.

A `MemorySaver` checkpointer is attached so that `human_review`'s and
`confirm_low_score`'s `interrupt()` calls can actually pause and later
resume execution - LangGraph requires a checkpointer for interrupts to
work.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.nodes.aha_extractor import aha_extractor
from app.nodes.confirm_low_score import confirm_low_score, route_after_score_confirmation
from app.nodes.error_handler import error_handler
from app.nodes.human_review import human_review, route_after_review
from app.nodes.llm_generation import llm_generation
from app.nodes.pattern_scoring import pattern_scoring, route_after_scoring
from app.nodes.preprocessing import preprocessing
from app.nodes.rag_retrieval import rag_retrieval
from app.nodes.testrail_publish import testrail_publish
from app.nodes.utils import route_on_error
from app.state import PipelineState


def build_graph():
    """Construct and compile the pipeline graph.

    Returns:
        A compiled LangGraph graph (with checkpointing enabled) ready to
        `.invoke()` / `.stream()`, and resumable via `Command(resume=...)`
        after a `human_review` or `confirm_low_score` interrupt.
    """
    graph = StateGraph(PipelineState)

    graph.add_node("aha_extractor", aha_extractor)
    graph.add_node("preprocessing", preprocessing)
    graph.add_node("pattern_scoring", pattern_scoring)
    graph.add_node("confirm_low_score", confirm_low_score)
    graph.add_node("rag_retrieval", rag_retrieval)
    graph.add_node("llm_generation", llm_generation)
    graph.add_node("human_review", human_review)
    graph.add_node("testrail_publish", testrail_publish)
    graph.add_node("error_handler", error_handler)

    graph.add_edge(START, "aha_extractor")

    # Each linear step is followed by a conditional edge: continue on
    # success, divert to error_handler if the node set state["error"].
    graph.add_conditional_edges(
        "aha_extractor", route_on_error("preprocessing", source_node="aha_extractor"),
        {"preprocessing": "preprocessing", "error_handler": "error_handler"},
    )
    graph.add_conditional_edges(
        "preprocessing", route_on_error("pattern_scoring", source_node="preprocessing"),
        {"pattern_scoring": "pattern_scoring", "error_handler": "error_handler"},
    )

    # pattern_scoring: "conformant" tickets skip straight to generation;
    # anything less pauses at confirm_low_score for a human decision.
    graph.add_conditional_edges(
        "pattern_scoring",
        route_after_scoring,
        {
            "llm_generation": "llm_generation",
            "confirm_low_score": "confirm_low_score",
            "error_handler": "error_handler",
        },
    )

    # confirm_low_score: user aborts -> error_handler; user continues ->
    # decide_rag_usage picks rag_retrieval (any weak ticket) or, defensively,
    # llm_generation (a ticket that somehow scored "conformant").
    graph.add_conditional_edges(
        "confirm_low_score",
        route_after_score_confirmation,
        {
            "rag_retrieval": "rag_retrieval",
            "llm_generation": "llm_generation",
            "error_handler": "error_handler",
        },
    )

    graph.add_conditional_edges(
        "rag_retrieval", route_on_error("llm_generation", source_node="rag_retrieval"),
        {"llm_generation": "llm_generation", "error_handler": "error_handler"},
    )
    graph.add_conditional_edges(
        "llm_generation", route_on_error("human_review", source_node="llm_generation"),
        {"human_review": "human_review", "error_handler": "error_handler"},
    )

    graph.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "testrail_publish": "testrail_publish",
            "llm_generation": "llm_generation",
            "error_handler": "error_handler",
        },
    )

    graph.add_conditional_edges(
        "testrail_publish", route_on_error(END, source_node="testrail_publish"),
        {END: END, "error_handler": "error_handler"},
    )

    graph.add_edge("error_handler", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)

