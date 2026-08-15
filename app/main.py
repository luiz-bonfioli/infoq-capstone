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

# Use the OS certificate trust store (Windows Certificate Store, etc.) for
# all SSL verification. This fixes "CERTIFICATE_VERIFY_FAILED: unable to
# get local issuer certificate" on corporate networks with an SSL-inspecting
# proxy, without disabling verification like OPENAI_SKIP_SSL_VERIFY does -
# it simply trusts the same corporate root CA your OS/browser already
# trusts. Must run before any ssl.create_default_context() calls (i.e.
# before importing/using requests, httpx, langsmith, etc.).
import truststore

truststore.inject_into_ssl()

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
    run_with_spinner,
)
from app.graph.build_graph import build_graph

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
    config = {"configurable": {"thread_id": args.feature_id}}

    result = run_with_spinner(
        f"Extracting and processing feature [bold]{args.feature_id}[/bold]...",
        lambda: graph.invoke({"aha_feature_id": args.feature_id}, config=config),
    )

    # Keep resuming while the graph is paused on any interrupt (test case
    # review or low pattern-score confirmation).
    while "__interrupt__" in result:
        decision = _prompt_for_interrupt(result["__interrupt__"][0])
        result = run_with_spinner(
            "Resuming pipeline...",
            lambda: graph.invoke(Command(resume=decision), config=config),
        )

    print_final_state(result)


if __name__ == "__main__":
    main()
