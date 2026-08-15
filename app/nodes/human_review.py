"""Node: Human QA Review.

Uses LangGraph's `interrupt()` to pause graph execution and surface the
generated test cases to a human reviewer. The graph run halts here until
resumed with `Command(resume=<decision>)`; a checkpointer is required for
this to work (see `app/graph/build_graph.py`).

TODO: Replace the CLI-facing payload with a real UI/Slack/email
notification integration once available.
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.nodes.utils import MAX_RETRIES, log_edge, safe_node
from app.state import PipelineState


@safe_node("human_review")
def human_review(state: PipelineState) -> dict:
    """Pause for human approval of generated test cases.

    Args:
        state: Current pipeline state. Requires `generated_test_cases`.

    Returns:
        Partial state update with `review_decision` and `review_feedback`.
    """
    decision = interrupt(
        {
            "type": "test_case_review",
            "message": "Review the generated test cases and approve or reject.",
            "generated_test_cases": state.get("generated_test_cases", []),
            "retry_count": state.get("retry_count", 0),
        }
    )

    # `decision` is whatever value the caller passes via Command(resume=...).
    # Expected shape: {"decision": "approved" | "rejected", "feedback": str}
    review_decision = decision.get("decision", "rejected")
    review_feedback = decision.get("feedback", "")

    return {
        "review_decision": review_decision,
        "review_feedback": review_feedback,
    }


def route_after_review(state: PipelineState) -> str:
    """Conditional edge: route based on the reviewer's decision.

    Rejections loop back to `llm_generation` for regeneration, capped by
    `MAX_RETRIES` to avoid infinite loops; once the budget is exhausted the
    run is routed to `error_handler`.
    """
    if state.get("error"):
        log_edge("human_review", "error", "error_handler")
        return "error_handler"

    decision = state.get("review_decision", "rejected")
    if decision == "approved":
        log_edge("human_review", "approved", "testrail_publish")
        return "testrail_publish"

    if state.get("retry_count", 0) >= MAX_RETRIES:
        log_edge("human_review", "rejected+retries_exhausted", "error_handler")
        return "error_handler"
    log_edge("human_review", "rejected+retry", "llm_generation")
    return "llm_generation"
