"""Entrypoint for running the LangGraph test case generation pipeline.

Usage:
    python -m app.main --feature-id AHA-123

The graph pauses at `human_review` via LangGraph's `interrupt()`. This CLI
detects the pause, prompts the user for an approve/reject decision, and
resumes the graph with `Command(resume=...)` until it reaches END.

Console output/input is styled with `rich` (panels, tables, spinners,
prompts) for readability - see `app/console.py`.
"""

from __future__ import annotations

import argparse
import logging

# SSL verification uses Python's default CA bundle, which covers public
# certificates. The previous `truststore` injection (OS trust store for
# corporate SSL-inspecting proxies) was removed because truststore requires
# Python >= 3.10 and this project runs on 3.9. On Python 3.10+, re-add
# `truststore>=0.8.0` to requirements.txt and call
# `truststore.inject_into_ssl()` here, before importing httpx/requests.

from dotenv import load_dotenv
from langgraph.types import Command
from rich.logging import RichHandler

from app.console import (
    console,
    print_final_state,
    print_score_confirmation,
    print_test_case_review,
    prompt_score_confirmation,
    prompt_test_case_review,
)
from app.graph.build_graph import build_graph
from app.graph.progress import GraphProgressLogger

# Load OPENAI_API_KEY (and any other secrets) from a local .env file, if
# present, before anything else reads os.environ.
load_dotenv(override=False)

# INFO level so pattern_scoring's score log (and other node info logs) are
# visible on the console, not just warnings/errors. RichHandler gives
# colored, aligned log lines instead of the plain default formatter.
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, show_path=False, markup=True)],
)


def _prompt_for_interrupt(interrupt_payload) -> dict:
    """Dispatch to the right prompt based on the interrupt's declared type."""
    payload = interrupt_payload.value
    if payload.get("type") == "pattern_score_confirmation":
        print_score_confirmation(payload)
        return prompt_score_confirmation()

    print_test_case_review(payload)
    return prompt_test_case_review()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TestRail test cases from an Aha! feature.")
    parser.add_argument("--feature-id", required=True, help="Aha! feature identifier (e.g. PROJ-123)")
    args = parser.parse_args()

    graph = build_graph()

    # The progress logger renders a step-by-step visual of the run (→ node,
    # ✓ done, ⏸ paused, ▸ resumed, ✖ FAILED / ✓ PUBLISHED). It is reused
    # across the initial invoke and every resume so the timeline is continuous.
    progress = GraphProgressLogger()
    config = {"configurable": {"thread_id": args.feature_id}, "callbacks": [progress]}

    result = graph.invoke({"aha_feature_id": args.feature_id}, config=config)

    # Keep resuming while the graph is paused on any interrupt (test case
    # review or low pattern-score confirmation).
    while "__interrupt__" in result:
        decision = _prompt_for_interrupt(result["__interrupt__"][0])
        result = graph.invoke(Command(resume=decision), config=config)

    print_final_state(result)


if __name__ == "__main__":
    main()
