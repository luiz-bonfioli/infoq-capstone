"""Node: Error Handler.

Terminal node reached whenever a previous node sets `state["error"]` or the
retry budget in `human_review` is exhausted. Centralizes error logging /
reporting instead of letting each node fail silently or crash the graph.
"""

from __future__ import annotations

import logging

from app.state import PipelineState

logger = logging.getLogger(__name__)


def error_handler(state: PipelineState) -> dict:
    """Log and finalize the pipeline run when an unrecoverable error occurred.

    Args:
        state: Current pipeline state. Expected to have `error` set.

    Returns:
        Partial state update marking the run as not published.
    """
    error = state.get("error", "Unknown error")
    logger.error("Pipeline failed for feature %s: %s", state.get("aha_feature_id"), error)

    # TODO: notify QA/engineering (Slack, email, ticket) about the failure
    return {"published": False}
