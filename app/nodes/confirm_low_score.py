"""Node: Confirm Low Pattern Score.

Reached whenever `pattern_scoring` determines the feature ticket is not
fully "conformant" (i.e. it's "partial" or "divergent" - often meaning the
feature is incomplete: missing description, thin/absent acceptance
criteria, etc.). Pauses the graph via `interrupt()` and asks a human
whether to proceed anyway, since generating test cases from an incomplete
ticket may produce low-quality or speculative results.
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.nodes.utils import safe_node
from app.state import PipelineState


@safe_node("confirm_low_score")
def confirm_low_score(state: PipelineState) -> dict:
    """Pause for human confirmation before proceeding with a low-scoring ticket.

    Args:
        state: Current pipeline state. Requires `pattern_conformance` and
            `pattern_score_rationale`.

    Returns:
        Partial state update with `score_review_decision` ("continue" or
        "abort"), and `error` set when the human chooses to abort.
    """
    conformance = state.get("pattern_conformance", "divergent")
    rationale = state.get("pattern_score_rationale", "")

    decision = interrupt(
        {
            "type": "pattern_score_confirmation",
            "message": (
                f"Feature ticket scored '{conformance}' against company patterns "
                f"(not fully conformant). Do you want to continue generating test "
                f"cases anyway?"
            ),
            "pattern_conformance": conformance,
            "pattern_score_rationale": rationale,
        }
    )

    # Expected shape: {"continue": True | False}
    if decision.get("continue", False):
        return {"score_review_decision": "continue"}

    return {
        "score_review_decision": "abort",
        "error": (
            f"User chose not to continue: feature ticket pattern conformance is "
            f"'{conformance}' ({rationale})"
        ),
    }


def route_after_score_confirmation(state: PipelineState) -> str:
    """Conditional edge: route based on the human's continue/abort decision.

    On "continue", defers to `decide_rag_usage`, which sends every weak
    (non-conformant) ticket - "partial" or "divergent" - through
    `rag_retrieval` so RAG supplies the company knowledge about the
    ticket's problem that the weak ticket is missing.
    """
    from app.nodes.pattern_scoring import decide_rag_usage
    from app.nodes.utils import log_edge

    if state.get("score_review_decision") == "abort":
        log_edge("confirm_low_score", "abort", "error_handler")
        return "error_handler"
    return decide_rag_usage(state)
