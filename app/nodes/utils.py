"""Shared node utilities: error-handling wrapper and routing helpers."""

from __future__ import annotations

import functools
import logging
from typing import Callable

from langgraph.errors import GraphInterrupt

from app.state import PipelineState

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def safe_node(node_name: str) -> Callable:
    """Decorator that catches exceptions raised by a node and converts them
    into an `error` state update instead of crashing the graph run.

    Args:
        node_name: Human-readable name of the node, used in log messages.
    """

    def decorator(func: Callable[[PipelineState], dict]) -> Callable[[PipelineState], dict]:
        @functools.wraps(func)
        def wrapper(state: PipelineState) -> dict:
            try:
                result = func(state)
                # Clear any previous error once a node succeeds.
                result.setdefault("error", None)
                return result
            except GraphInterrupt:
                # Not a real failure - propagate so LangGraph can pause/resume.
                raise
            except Exception as exc:  # noqa: BLE001 - intentionally broad at node boundary
                logger.exception("Node '%s' failed", node_name)
                return {"error": f"{node_name}: {exc}"}

        return wrapper

    return decorator


def log_edge(source_node: str, edge_label: str, target_node: str) -> None:
    """Log a single graph transition as `source -> edge -> target`."""
    logger.info("EDGE: %s -> (%s) -> %s", source_node, edge_label, target_node)


def route_on_error(next_node: str, source_node: str = "<unknown>") -> Callable[[PipelineState], str]:
    """Build a conditional-edge router that sends the run to `error_handler`
    if the previous node set `state['error']`, otherwise continues to
    `next_node`.

    Args:
        next_node: Node (or END) to route to on success.
        source_node: Name of the node this router is attached to, used only
            for the `node -> edge -> target` log line.
    """

    def router(state: PipelineState) -> str:
        if state.get("error"):
            log_edge(source_node, "error", "error_handler")
            return "error_handler"
        log_edge(source_node, "success", str(next_node))
        return next_node

    return router
