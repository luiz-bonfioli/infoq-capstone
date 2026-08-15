"""Rich-based console rendering and prompting helpers for the CLI.

Centralizes all `rich` usage (panels, tables, spinners, prompts) so
`app/main.py` stays focused on graph orchestration. Import `console` from
here anywhere else in the app that needs to print (e.g. custom log
handlers), so all output shares one `Console` instance/theme.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.theme import Theme

_THEME = Theme(
    {
        "score.conformant": "bold green",
        "score.partial": "bold yellow",
        "score.divergent": "bold red",
        "heading": "bold cyan",
    }
)

console = Console(theme=_THEME)


def _score_style(score: str | None) -> str:
    return f"score.{score}" if score in {"conformant", "partial", "divergent"} else "bold"


def print_score_confirmation(payload: dict) -> None:
    """Render the low pattern-score confirmation interrupt payload."""
    score = payload.get("pattern_conformance")
    body = (
        f"{payload.get('message')}\n\n"
        f"[bold]Pattern conformance:[/bold] [{_score_style(score)}]{score}[/{_score_style(score)}]\n"
        f"[bold]Rationale:[/bold] {payload.get('pattern_score_rationale')}"
    )
    console.print(Panel(body, title="Low Pattern Score Detected", border_style="yellow", expand=False))


def prompt_score_confirmation() -> dict:
    """Ask the user whether to proceed despite a low pattern-conformance score."""
    proceed = Confirm.ask("Continue generating test cases anyway?", default=False)
    return {"continue": proceed}


def _test_cases_table(test_cases: list[dict]) -> Table:
    table = Table(show_lines=True, expand=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold")
    table.add_column("Priority", width=8)
    table.add_column("Steps", overflow="fold")
    table.add_column("Expected Result", overflow="fold")

    priority_styles = {"High": "bold red", "Medium": "bold yellow", "Low": "green"}
    for i, tc in enumerate(test_cases, start=1):
        priority = tc.get("priority", "")
        steps = "\n".join(f"{j}. {s}" for j, s in enumerate(tc.get("steps", []), start=1))
        table.add_row(
            str(i),
            tc.get("title", ""),
            f"[{priority_styles.get(priority, '')}]{priority}[/]" if priority else "",
            steps,
            tc.get("expected_result", ""),
        )
    return table


def print_test_case_review(payload: dict) -> None:
    """Render the human_review interrupt payload (message + test case table)."""
    console.print(Panel(payload.get("message", ""), title="Human Review Requested", border_style="cyan", expand=False))
    test_cases = payload.get("generated_test_cases") or []
    if test_cases:
        console.print(_test_cases_table(test_cases))
    else:
        console.print("[dim]No test cases were generated.[/dim]")
    console.print(f"[dim]Attempt: {payload.get('retry_count')}[/dim]")


def prompt_test_case_review() -> dict:
    """Ask the user to approve/reject the generated test cases."""
    approved = Confirm.ask("Approve these test cases?", default=False)
    if approved:
        return {"decision": "approved", "feedback": ""}

    feedback = Prompt.ask("Feedback for regeneration (optional)", default="")
    return {"decision": "rejected", "feedback": feedback}


def _testrail_results_table(results: list[dict]) -> Table:
    """Render per-test-case TestRail publish outcomes (created vs. error)."""
    table = Table(title="TestRail Publish Results", show_lines=True, expand=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="bold")
    table.add_column("Status", width=10)
    table.add_column("TestRail Case ID")
    table.add_column("Error", overflow="fold")

    for i, r in enumerate(results, start=1):
        status = r.get("status", "")
        status_style = "bold green" if status == "created" else "bold red"
        table.add_row(
            str(i),
            r.get("title", ""),
            f"[{status_style}]{status}[/{status_style}]",
            r.get("testrail_case_id") or "-",
            r.get("error") or "",
        )
    return table


def print_final_state(result: dict) -> None:
    """Render the pipeline's final state as a summary panel plus result tables."""
    published = result.get("published")
    error = result.get("error")

    if error:
        status_line = "[bold red]FAILED[/bold red]"
    elif published:
        status_line = "[bold green]PUBLISHED[/bold green]"
    else:
        status_line = "[bold yellow]NOT PUBLISHED[/bold yellow]"

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Status:", status_line)
    summary.add_row("Feature:", str(result.get("aha_feature_id", "")))
    summary.add_row("Pattern conformance:", str(result.get("pattern_conformance", "")))
    summary.add_row("TestRail run:", str(result.get("testrail_run_id", "")))
    summary.add_row("Retry count:", str(result.get("retry_count", 0)))
    if error:
        summary.add_row("Error:", f"[red]{error}[/red]")

    console.print(Panel(summary, title="Final State", border_style="green" if published else "red"))

    test_cases = result.get("generated_test_cases") or []
    if test_cases:
        console.print(_test_cases_table(test_cases))

    testrail_results = result.get("testrail_results") or []
    if testrail_results:
        console.print(_testrail_results_table(testrail_results))
